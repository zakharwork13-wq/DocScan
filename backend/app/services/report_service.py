"""
Генерация PDF-отчёта о результатах сканирования.
"""

import io
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..models.scan import Scan, ScanFinding

# Регистрируем шрифт с кириллицей (DejaVu — есть в reportlab) или системный
_FONT_REGISTERED = False


def _register_font() -> str:
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return "DejaVu"
    try:
        # reportlab включает DejaVu в стандартной поставке
        from reportlab.rl_config import canvas_basefontname  # noqa: F401
        # Пробуем найти DejaVu
        import os
        candidates = [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\verdana.ttf",
            r"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for path in candidates:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont("DejaVu", path))
                _FONT_REGISTERED = True
                return "DejaVu"
    except Exception:
        pass
    return "Helvetica"


_FINDING_LABELS = {
    "passport": "Паспорт",
    "snils": "СНИЛС",
    "inn_person": "ИНН (физ. лицо)",
    "inn_org": "ИНН (организация)",
    "bank_card": "Банковская карта",
    "phone": "Телефон",
    "email": "Email",
    "date_of_birth": "Дата рождения",
    "oms_policy": "Полис ОМС",
    "driver_license": "Водительское удостоверение",
    "fio": "ФИО",
    "address": "Адрес",
}

_CATEGORY_LABELS = {
    "strict": "Строго конфиденциально",
    "confidential": "Конфиденциально",
    "internal": "Для внутреннего использования",
    "public": "Публичный",
}

_STATUS_LABELS = {
    "queued": "В очереди",
    "processing": "Обработка",
    "completed": "Завершено",
    "failed": "Ошибка",
}


def generate_scan_report(scan: Scan, findings: list[ScanFinding]) -> bytes:
    """Генерирует PDF-отчёт и возвращает байты."""
    font = _register_font()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"DocScan: {scan.original_filename}",
        author="DocScan",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontName=font,
        fontSize=18,
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"], fontName=font, fontSize=13, spaceAfter=8
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["BodyText"], fontName=font, fontSize=10, spaceAfter=4
    )
    small_style = ParagraphStyle(
        "Small",
        parent=styles["BodyText"],
        fontName=font,
        fontSize=8,
        textColor=colors.grey,
    )

    story = []

    # Заголовок
    story.append(Paragraph("Отчёт о сканировании документа", title_style))
    story.append(
        Paragraph(
            f"Сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            small_style,
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    # Метаданные документа
    story.append(Paragraph("Документ", h2_style))
    meta_data = [
        ["Имя файла", scan.original_filename],
        ["Размер", f"{scan.file_size_bytes / 1024:.1f} КБ"],
        ["Тип", scan.mime_type],
        ["Загружено", scan.created_at.strftime("%d.%m.%Y %H:%M") if scan.created_at else "—"],
        ["Завершено", scan.finished_at.strftime("%d.%m.%Y %H:%M") if scan.finished_at else "—"],
        ["Длительность", f"{scan.processing_duration_ms / 1000:.1f} с" if scan.processing_duration_ms else "—"],
        ["Хеш SHA-256", scan.file_hash[:32] + "..." if scan.file_hash else "—"],
        ["Режим", "Серверный" if scan.scan_mode == "server" else "Клиентский"],
        ["Статус", _STATUS_LABELS.get(scan.status, scan.status)],
    ]
    meta_table = Table(meta_data, colWidths=[5 * cm, 11 * cm])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 0.7 * cm))

    # Категория документа
    story.append(Paragraph("Классификация", h2_style))
    category_label = _CATEGORY_LABELS.get(scan.document_category, "Не определена")
    category_color = {
        "strict": colors.HexColor("#dc2626"),
        "confidential": colors.HexColor("#ea580c"),
        "internal": colors.HexColor("#ca8a04"),
        "public": colors.HexColor("#16a34a"),
    }.get(scan.document_category, colors.grey)

    category_table = Table(
        [[Paragraph(f"<b>{category_label}</b>", body_style)]],
        colWidths=[16 * cm],
    )
    category_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("TEXTCOLOR", (0, 0), (-1, -1), category_color),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("BOX", (0, 0), (-1, -1), 1, category_color),
            ]
        )
    )
    story.append(category_table)
    story.append(Spacer(1, 0.7 * cm))

    # Сводка по типам
    if scan.findings_summary:
        story.append(Paragraph("Сводка по типам персональных данных", h2_style))
        summary_data = [["Тип", "Количество"]]
        for ftype, count in scan.findings_summary.items():
            summary_data.append([_FINDING_LABELS.get(ftype, ftype), str(count)])
        summary_data.append(
            ["ИТОГО", str(sum(scan.findings_summary.values()))]
        )
        summary_table = Table(summary_data, colWidths=[10 * cm, 6 * cm])
        summary_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), font),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
                    ("FONTSIZE", (0, -1), (-1, -1), 10),
                    ("ALIGN", (1, 0), (1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 0.7 * cm))

    # Детальный список находок
    if findings:
        story.append(Paragraph(f"Детализация ({len(findings)} находок)", h2_style))
        story.append(
            Paragraph(
                "Все значения замаскированы. Полная информация остаётся только в исходном файле.",
                small_style,
            )
        )
        story.append(Spacer(1, 0.2 * cm))

        findings_data = [["№", "Тип", "Значение", "Уверенность"]]
        for i, f in enumerate(findings, 1):
            findings_data.append(
                [
                    str(i),
                    _FINDING_LABELS.get(f.finding_type, f.finding_type),
                    f.masked_value,
                    f"{int(f.confidence * 100)}%",
                ]
            )

        findings_table = Table(
            findings_data, colWidths=[1 * cm, 5 * cm, 7 * cm, 3 * cm]
        )
        findings_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (3, 0), (3, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(findings_table)
    else:
        story.append(Paragraph("Персональные данные не обнаружены.", body_style))

    # Подпись
    story.append(Spacer(1, 1 * cm))
    story.append(
        Paragraph(
            "Отчёт сгенерирован системой DocScan автоматически. Полные значения "
            "персональных данных не сохраняются в системе после обработки.",
            small_style,
        )
    )

    doc.build(story)
    return buffer.getvalue()
