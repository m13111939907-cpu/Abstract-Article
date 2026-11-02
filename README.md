# 文献提取器

基于 FastAPI + Vue3 的文献提取与筛选系统。Docker Compose 统一管理 MySQL、Neo4j、后端与前端。

## 目录

```
backend/    FastAPI 后端（MVC 的 Model + Controller）
frontend/   Vue3 前端（MVC 的 View）
```

## 启动

```bash
cp .env.example .env     # 首次运行
docker compose up -d --build
docker compose ps
```

## 访问

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:5173 |
| 后端 API 文档 | http://localhost:8001/docs |
| 健康检查 | http://localhost:8001/api/health |
| Neo4j Browser | http://localhost:7474 |

## 常用命令

```bash
docker compose logs -f backend     # 后端日志
docker compose down                # 停止
docker compose down -v             # 停止并清空数据卷
```
