#!/usr/bin/env bash
# 续期证书并重载 Nginx（建议加入 crontab，每月执行一次）
set -euo pipefail
cd "$(dirname "$0")/.."

docker run --rm \
  -v "$PWD/infra/certs:/etc/letsencrypt" \
  -v "$PWD/infra/certbot/www:/var/www/certbot" \
  certbot/certbot renew --webroot -w /var/www/certbot

docker compose -f docker-compose.prod.yml exec frontend nginx -s reload
