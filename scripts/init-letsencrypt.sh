#!/usr/bin/env bash
# 在服务器上首次申请 Let's Encrypt 证书（需域名已解析、80 端口已通）
set -euo pipefail
cd "$(dirname "$0")/.."

set -a
# shellcheck disable=SC1091
source .env.prod
set +a

: "${DOMAIN:?请在 .env.prod 设置 DOMAIN}"
: "${ACME_EMAIL:?请在 .env.prod 设置 ACME_EMAIL}"

mkdir -p infra/certs infra/certbot/www

docker run --rm \
  -v "$PWD/infra/certs:/etc/letsencrypt" \
  -v "$PWD/infra/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d "$DOMAIN" \
  --email "$ACME_EMAIL" \
  --agree-tos --no-eff-email

echo "证书已生成：infra/certs/live/$DOMAIN/"
echo "接着执行：./scripts/enable-https.sh"
