import logging

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorDatabase

from dev.config import settings
from pdf_persistence.api import router as documents_router
from pdf_persistence.db import get_db, lifespan
from pdf_persistence.rfc9457 import DomainException, problem_details_response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PDF Persistence API",
    description="Microservice to parse PDFs and persist them to MongoDB",
    version="0.1.0",
    lifespan=lifespan,
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

app.include_router(documents_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    details = []
    for err in exc.errors():
        details.append(f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}")
    return problem_details_response(
        status=400,
        title="Validation Error",
        detail="The request payload is invalid",
        type_="https://fastpdf.dev/errors/validation",
        errors=details,
    )


@app.exception_handler(DomainException)
async def domain_exception_handler(request, exc: DomainException):
    return problem_details_response(**exc.to_problem_details())


@app.get("/health")
async def health_check(db: AsyncIOMotorDatabase = Depends(get_db)):
    await db.command("ping")
    return {"status": "healthy"}
