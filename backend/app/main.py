from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.graph import router as graph_router
from app.controllers.health import router as health_router
from app.controllers.papers import router as papers_router
from app.controllers.projects import router as projects_router
from app.controllers.sources import router as sources_router
from app.core.config import settings
from app.core.mysql import init_db
from app.services.bootstrap import seed_default_sources


# 启动时建表并写入默认订阅源
@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    seed_default_sources()
    yield


app = FastAPI(title="文献提取器 API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(sources_router, prefix="/api")
app.include_router(papers_router, prefix="/api")
app.include_router(graph_router, prefix="/api")


@app.get("/")
def root():
    return {"service": "文献提取器", "docs": "/docs"}
