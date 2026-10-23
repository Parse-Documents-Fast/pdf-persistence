import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorDatabase

from dev.config import settings
from pdf_persistence.api import router as documents_router
from pdf_persistence.db import get_db
from pdf_persistence.db import lifespan as db_lifespan
from pdf_persistence.logger import setup_logging
from pdf_persistence.rfc9457 import (
    DocumentNotFoundException,
    DomainException,
    DuplicateDocumentException,
    problem_details_response,
)

setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(
        "service started",
        extra={
            "fields": {
                "http_addr": settings.HTTP_ADDR,
                "log_level": settings.LOG_LEVEL.lower(),
            }
        },
    )
    async with db_lifespan(app):
        yield


app = FastAPI(
    title="PDF Persistence API",
    description="Microservice to parse PDFs and persist them to MongoDB",
    version="0.1.0",
    lifespan=app_lifespan,
)

cors_origins = getattr(
    settings, "CORS_ORIGINS", ["http://localhost", "http://localhost:8000"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next) -> Response:
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    status_code = response.status_code
    fields = {
        "http_method": request.method,
        "http_path": request.url.path,
        "http_status": status_code,
        "duration_ms": duration_ms,
    }

    # Routine healthchecks at DEBUG level to avoid log pollution
    if request.url.path == "/health" and status_code == 200:
        logger.debug("http request completed", extra={"fields": fields})
    elif status_code >= 500:
        logger.error("http request completed", extra={"fields": fields})
    elif status_code >= 400:
        logger.warning("http request completed", extra={"fields": fields})
    else:
        logger.info("http request completed", extra={"fields": fields})

    return response


app.include_router(documents_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = []
    for err in exc.errors():
        details.append(f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}")
    logger.warning(
        "validation error",
        extra={"fields": {"reason": "invalid payload", "errors": details}},
    )
    return problem_details_response(
        status=400,
        title="Validation Error",
        detail="The request payload is invalid",
        type_="https://fastpdf.dev/errors/validation",
        errors=details,
    )


@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    if isinstance(exc, DuplicateDocumentException):
        checksum = exc.extra.get("checksum", "")
        logger.warning(
            "duplicate document rejected",
            extra={"fields": {"checksum": checksum}},
        )
    elif isinstance(exc, DocumentNotFoundException):
        doc_id = exc.extra.get("document_id", "")
        logger.warning(
            "document not found",
            extra={"fields": {"pdf_id": doc_id}},
        )
    return problem_details_response(**exc.to_problem_details())


@app.get("/health")
async def health_check(db: AsyncIOMotorDatabase = Depends(get_db)):
    await db.command("ping")
    return {"status": "healthy"}
