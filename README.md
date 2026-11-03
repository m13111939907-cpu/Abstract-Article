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

## 后端接口

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| POST / GET | `/api/projects` | 新建 / 列表（分页） |
| PATCH / DELETE | `/api/projects/{id}` | 修改 / 删除项目 |
| GET | `/api/projects/{id}/stats` | 项目统计 |
| GET | `/api/projects/{id}/export` | 导出 CSV / BibTeX |
| POST | `/api/projects/{id}/fetch` | 抓取 RSS |
| POST | `/api/projects/{id}/screen` | 首轮字符筛选 |
| POST / GET | `/api/projects/{id}/screen2` | 二轮 LLM 筛选 |
| GET | `/api/projects/{id}/papers` | 首轮文献（分页） |
| GET / POST | `/api/sources` | 订阅源列表 / 新增 |
| PATCH / DELETE | `/api/sources/{id}` | 启停 / 删除 |
| GET | `/api/papers`、`/api/papers/{id}` | 文献列表 / 详情 |
| GET | `/api/papers/{id}/reading` | 阅读聚合（文献+图谱+结论） |
| DELETE | `/api/papers/{id}` | 删除文献及其图 |
| POST | `/api/papers/{id}/annotate` | 单篇图谱标注 |
| GET / DELETE | `/api/papers/{id}/graph` | 取图 / 删图 |
| POST | `/api/projects/{id}/annotate` | 批量标注 |
| GET | `/api/graph/stats` | 图谱统计 |

完整参数见 `http://localhost:8001/docs`。

## 常用命令

```bash
docker compose logs -f backend     # 后端日志
docker compose down                # 停止
docker compose down -v             # 停止并清空数据卷
```
