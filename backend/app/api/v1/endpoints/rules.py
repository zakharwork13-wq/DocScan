import re
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....database import get_db
from ....models.detection_rule import DetectionRule, RuleVersion
from ....models.user import Role
from ....schemas.rule import (
    RuleCreateRequest,
    RuleListResponse,
    RuleResponse,
    RuleTestMatch,
    RuleTestRequest,
    RuleTestResponse,
    RuleUpdateRequest,
    RuleVersionResponse,
)
from ....services import audit_service
from .auth import _get_current_user

router = APIRouter()
DbDep = Annotated[AsyncSession, Depends(get_db)]


async def _require_admin(db: AsyncSession, user_id: uuid.UUID) -> None:
    from ....models.user import User
    result = await db.execute(
        select(Role).join(User, User.role_id == Role.id).where(User.id == user_id)
    )
    role = result.scalar_one_or_none()
    if role is None or role.code != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только администратор")


def _to_response(rule: DetectionRule) -> RuleResponse:
    return RuleResponse(
        id=rule.id,
        code=rule.code,
        name=rule.name,
        description=rule.description,
        finding_type=rule.finding_type,
        pattern=rule.pattern,
        validator=rule.validator,
        base_confidence=rule.base_confidence,
        positive_keywords=rule.positive_keywords,
        negative_keywords=rule.negative_keywords,
        is_active=rule.is_active,
        is_builtin=rule.is_builtin,
        version=rule.version,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def _snapshot(rule: DetectionRule) -> dict:
    return {
        "code": rule.code,
        "name": rule.name,
        "description": rule.description,
        "finding_type": rule.finding_type,
        "pattern": rule.pattern,
        "validator": rule.validator,
        "base_confidence": rule.base_confidence,
        "positive_keywords": rule.positive_keywords,
        "negative_keywords": rule.negative_keywords,
        "is_active": rule.is_active,
    }


# ─── GET /rules ───────────────────────────────────────────────────────────────

@router.get("", response_model=RuleListResponse)
async def list_rules(
    request: Request,
    db: DbDep,
    active: Optional[bool] = Query(None),
    finding_type: Optional[str] = Query(None),
) -> RuleListResponse:
    await _get_current_user(request, db)  # любой аутентифицированный пользователь может смотреть

    query = select(DetectionRule)
    if active is not None:
        query = query.where(DetectionRule.is_active == active)
    if finding_type:
        query = query.where(DetectionRule.finding_type == finding_type)
    query = query.order_by(DetectionRule.code)

    result = await db.execute(query)
    rules = list(result.scalars().all())
    return RuleListResponse(items=[_to_response(r) for r in rules], total=len(rules))


# ─── POST /rules ──────────────────────────────────────────────────────────────

@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(body: RuleCreateRequest, request: Request, db: DbDep) -> RuleResponse:
    current_user = await _get_current_user(request, db)
    await _require_admin(db, current_user.id)

    # Проверка уникальности кода
    existing = await db.execute(select(DetectionRule).where(DetectionRule.code == body.code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Правило с кодом '{body.code}' уже существует",
        )

    # Валидация regex
    try:
        re.compile(body.pattern)
    except re.error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Некорректное регулярное выражение: {e}",
        )

    now = datetime.now(timezone.utc)
    rule = DetectionRule(
        code=body.code,
        name=body.name,
        description=body.description,
        finding_type=body.finding_type,
        pattern=body.pattern,
        validator=body.validator,
        base_confidence=body.base_confidence,
        positive_keywords=body.positive_keywords,
        negative_keywords=body.negative_keywords,
        is_active=body.is_active,
        is_builtin=False,
        version=1,
        created_by=current_user.id,
        created_at=now,
    )
    db.add(rule)
    await db.flush()

    # Сохраняем первую версию в историю
    version = RuleVersion(
        rule_id=rule.id,
        version=1,
        snapshot=_snapshot(rule),
        changed_by=current_user.id,
        changed_at=now,
    )
    db.add(version)

    await audit_service.log_action(
        db,
        action="rule.created",
        user_id=current_user.id,
        object_type="rule",
        object_id=rule.id,
        details={"code": rule.code, "name": rule.name},
        commit=False,
    )

    await db.commit()
    await db.refresh(rule)
    return _to_response(rule)


# ─── PATCH /rules/{rule_id} ───────────────────────────────────────────────────

@router.patch("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: uuid.UUID, body: RuleUpdateRequest, request: Request, db: DbDep
) -> RuleResponse:
    current_user = await _get_current_user(request, db)
    await _require_admin(db, current_user.id)

    rule = await db.get(DetectionRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Правило не найдено")

    if rule.is_builtin and body.pattern is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя менять паттерн встроенного правила. Создайте копию.",
        )

    if body.pattern is not None:
        try:
            re.compile(body.pattern)
        except re.error as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Некорректное регулярное выражение: {e}",
            )
        rule.pattern = body.pattern

    if body.name is not None:
        rule.name = body.name
    if body.description is not None:
        rule.description = body.description
    if body.validator is not None:
        rule.validator = body.validator
    if body.base_confidence is not None:
        rule.base_confidence = body.base_confidence
    if body.positive_keywords is not None:
        rule.positive_keywords = body.positive_keywords
    if body.negative_keywords is not None:
        rule.negative_keywords = body.negative_keywords
    if body.is_active is not None:
        rule.is_active = body.is_active

    rule.version += 1
    rule.updated_at = datetime.now(timezone.utc)
    rule.updated_by = current_user.id

    # Сохраняем новую версию в историю
    version = RuleVersion(
        rule_id=rule.id,
        version=rule.version,
        snapshot=_snapshot(rule),
        changed_by=current_user.id,
        changed_at=rule.updated_at,
    )
    db.add(version)

    await audit_service.log_action(
        db,
        action="rule.updated",
        user_id=current_user.id,
        object_type="rule",
        object_id=rule.id,
        details={"new_version": rule.version},
        commit=False,
    )

    await db.commit()
    await db.refresh(rule)
    return _to_response(rule)


# ─── DELETE /rules/{rule_id} ──────────────────────────────────────────────────

@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: uuid.UUID, request: Request, db: DbDep) -> None:
    current_user = await _get_current_user(request, db)
    await _require_admin(db, current_user.id)

    rule = await db.get(DetectionRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Правило не найдено")

    if rule.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить встроенное правило. Используйте деактивацию.",
        )

    await audit_service.log_action(
        db,
        action="rule.deleted",
        user_id=current_user.id,
        object_type="rule",
        object_id=rule.id,
        details={"code": rule.code},
        commit=False,
    )

    await db.delete(rule)
    await db.commit()


# ─── GET /rules/{rule_id}/versions ────────────────────────────────────────────

@router.get("/{rule_id}/versions", response_model=list[RuleVersionResponse])
async def list_rule_versions(
    rule_id: uuid.UUID, request: Request, db: DbDep
) -> list[RuleVersionResponse]:
    current_user = await _get_current_user(request, db)
    await _require_admin(db, current_user.id)

    result = await db.execute(
        select(RuleVersion)
        .where(RuleVersion.rule_id == rule_id)
        .order_by(RuleVersion.version.desc())
    )
    versions = list(result.scalars().all())
    return [RuleVersionResponse.model_validate(v) for v in versions]


# ─── POST /rules/test ─────────────────────────────────────────────────────────

@router.post("/test", response_model=RuleTestResponse)
async def test_rule(body: RuleTestRequest, request: Request, db: DbDep) -> RuleTestResponse:
    """Проверить паттерн на тестовом тексте без сохранения правила."""
    await _get_current_user(request, db)

    try:
        pattern = re.compile(body.pattern, re.IGNORECASE)
    except re.error as e:
        return RuleTestResponse(matches=[], error=f"Некорректное регулярное выражение: {e}")

    # Опциональная валидация
    validator_fn = None
    if body.validator:
        from ....detection import validators as v
        validator_fn = {
            "snils": v.validate_snils,
            "inn_person": v.validate_inn_person,
            "inn_org": v.validate_inn_org,
            "inn": v.validate_inn,
            "luhn": v.validate_luhn,
        }.get(body.validator)

    matches: list[RuleTestMatch] = []
    for m in pattern.finditer(body.text):
        valid = True if validator_fn is None else validator_fn(m.group(0))
        matches.append(RuleTestMatch(value=m.group(0), start=m.start(), end=m.end(), valid=valid))

    return RuleTestResponse(matches=matches)
