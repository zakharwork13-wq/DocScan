import structlog
import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .api.v1.router import api_router

settings = get_settings()
log = structlog.get_logger()

app = FastAPI(
    title="DocScan API",
    version="1.0.0",
    docs_url="/api/v1/docs" if settings.is_dev else None,
    redoc_url=None,
    openapi_url="/api/v1/openapi.json" if settings.is_dev else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"] if settings.is_dev else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": "INTERNAL_ERROR", "message": "Внутренняя ошибка сервера"},
    )


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=settings.is_dev)
