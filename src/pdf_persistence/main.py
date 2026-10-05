import logging
from fastapi import UploadFile, File, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pdf_persistence.db import get_db
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dev.config import settings
from pdf_persistence.api import router as documents_router
from core.db import lifespan
from pdf_persistence.rfc9457 import DomainException, problem_details_response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PDF Persistence API",
    description="Microservice to parse PDFs and persist them to MongoDB",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)

@app.exception_handler(DomainException)
async def domain_exception_handler(request, exc: DomainException):
    return problem_details_response(exc.to_problem_details())

@app.get("/health")
async def health_check():
    from pdf_persistence.db import get_db
    db = get_db()
    # Check mongo connection
    await db.command("ping")
    return {"status": "healthy"}

@app.post("/extract")
async def extract_pdf(
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    from pdf_persistence.services import process_and_save_pdf
    
    file_bytes = await file.read()
    title = file.filename or "unknown.pdf"
    _, content, page_count = await process_and_save_pdf(db, file_bytes, title)
    
    return {
        "content": content,
        "page_count": page_count
    }


