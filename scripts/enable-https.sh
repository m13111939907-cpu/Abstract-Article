#!/usr/bin/env bash
# 用 HTTPS 配置替换 Nginx 配置并重建前端容器
set -euo pipefail
cd "$(dirname "$0")/.."

set -a
# shellcheck disable=SC1091
source .env.prod
set +a

: "${DOMAIN:?请在 .env.prod 设置 DOMAIN}"

envsubst '${DOMAIN}' < infra/nginx/https.conf.template > frontend/nginx.conf

docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build frontend

echo "HTTPS 已启用：https://$DOMAIN"
