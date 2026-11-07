from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.controllers.graph import router as graph_router
from app.controllers.health import router as health_router
from app.controllers.papers import router as papers_router
from app.controllers.projects import router as projects_router
from app.controllers.screening import router as screening_router
from app.controllers.settings import router as settings_router
from app.controllers.sources import router as sources_router
from app.core.config import settings
from app.core.mysql import init_db
from app.services.bootstrap import seed_default_sources
from app.services.graph import ensure_indexes
from app.services.llm import load_runtime_config


# 启动时建表、恢复模型配置、写入默认订阅源、创建图索引
@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    load_runtime_config()
    seed_default_sources()
    ensure_indexes()
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
app.include_router(screening_router, prefix="/api")
app.include_router(settings_router, prefix="/api")


# 数据库唯一约束冲突统一返回 409
@app.exception_handler(IntegrityError)
async def integrity_error_handler(_request, _exc):
    return JSONResponse(status_code=409, content={"detail": "数据冲突，操作未完成"})


@app.get("/")
def root():
    return {"service": "文献提取器", "docs": "/docs"}
