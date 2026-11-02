# 服务器部署手册

目标服务器：阿里云 ECS · Ubuntu 22.04 · 2 核 2G · `47.107.247.122`

## 0. 前置条件

- 域名已解析到服务器公网 IP（A 记录）
- 国内服务器使用域名需完成 **ICP 备案**
- 安全组放行：`22`（建议限来源 IP）、`80`、`443`

## 1. 服务器初始化

```bash
# 2G 机器加 swap，避免 OOM
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 安装 Docker 与 compose 插件
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
# 重新登录后生效
```

## 2. 拉取代码

```bash
sudo mkdir -p /opt/article_abstract
sudo chown "$USER":"$USER" /opt/article_abstract
git clone <仓库地址> /opt/article_abstract
cd /opt/article_abstract
```

## 3. 配置环境变量

```bash
cp .env.prod.example .env.prod
vim .env.prod    # 修改数据库/Neo4j 密码、DOMAIN、ACME_EMAIL
chmod 600 .env.prod
```

## 4. 启动生产环境

```bash
./scripts/deploy.sh
# 等价于：
# docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

## 5. 验证

```bash
docker compose -f docker-compose.prod.yml ps
curl http://47.107.247.122/api/health
# 期望：{"mysql":"ok","neo4j":"ok"}
```

浏览器访问 `http://47.107.247.122`。

## 6. 启用 HTTPS

**前提**：域名解析已生效，且 80 端口可访问。

```bash
./scripts/init-letsencrypt.sh    # 申请证书
./scripts/enable-https.sh        # 切换 HTTPS 配置并重建前端
```

自动续期（每月 1 日 03:00）：

```bash
crontab -e
# 追加：
0 3 1 * * cd /opt/article_abstract && ./scripts/renew-cert.sh >> /var/log/certbot.log 2>&1
```

## 7. 日常更新

```bash
cd /opt/article_abstract
./scripts/deploy.sh
```

## 8. 运维

```bash
# 日志
docker compose -f docker-compose.prod.yml logs -f backend

# 备份 MySQL
docker exec article_abstract_mysql sh -c \
  'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --all-databases' > backup_$(date +%F).sql

# 停止（保留数据）
docker compose -f docker-compose.prod.yml down

# 停止并清空数据（慎用）
docker compose -f docker-compose.prod.yml down -v
```

## 9. 端口说明

| 端口 | 是否对外 | 说明 |
| --- | --- | --- |
| 22 | 是（限 IP） | SSH |
| 80 | 是 | HTTP / 证书校验 |
| 443 | 是 | HTTPS |
| 3306 / 7474 / 7687 / 8000 | **否** | 仅 Docker 内网 |
