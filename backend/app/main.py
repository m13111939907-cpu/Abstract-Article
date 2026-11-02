from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.health import router as health_router
from app.core.config import settings

app = FastAPI(title="文献提取器 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")


@app.get("/")
def root():
    return {"service": "文献提取器", "docs": "/docs"}
