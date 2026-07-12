# 阿里云 Ubuntu 生产部署

## 1. 前置条件

- Ubuntu 主机已安装 Docker Engine 和 Docker Compose Plugin。
- 阿里云安全组仅开放 SSH、HTTP 80 和 HTTPS 443；不要开放公网 8000。
- 已准备域名并把 A 记录指向服务器公网 IP。
- GHCR 镜像已经发布并设为公开。

## 2. 创建部署目录

```bash
sudo mkdir -p /opt/coding-agent/secrets
sudo chown -R "$USER":"$USER" /opt/coding-agent
cd /opt/coding-agent
```

把 `docker-compose.production.yml` 和 `deploy/nginx.conf` 放入对应位置，创建生产环境文件：

```bash
cat > .env <<'EOF'
GITHUB_REPOSITORY_OWNER=xhy-nju
CODING_AGENT_TAG=1.0.1
ENABLE_REAL_LLM=true
OPENAI_BASE_URL=https://njusehub.info/v1
OPENAI_MODEL=glm-5.2
ADMIN_PASSWORD=替换为高强度密码
SESSION_SECRET=替换为至少32位随机字符串
SESSION_TTL_SECONDS=28800
COOKIE_SECURE=true
EOF
chmod 600 .env
```

使用域名和 HTTPS 时必须保持 `COOKIE_SECURE=true`。如果暂时只通过 `http://服务器IP` 演示，可将其显式设为 `false`；启用 HTTPS 后应立即改回 `true`，否则登录 Cookie 会降低传输安全性。

推荐使用以下命令生成 Session Secret：

```bash
openssl rand -hex 32
```

## 3. 配置 Docker Secret

```bash
install -m 600 /dev/null secrets/openai_api_key
read -s -p "OpenAI-compatible API key: " API_KEY
printf '%s' "$API_KEY" > secrets/openai_api_key
unset API_KEY
```

不要把 Secret 写入 Compose、Shell 历史、Git 或日志。

## 4. 启动应用

```bash
docker compose -f docker-compose.production.yml pull
docker compose -f docker-compose.production.yml up -d --force-recreate
docker compose -f docker-compose.production.yml ps
curl --fail http://127.0.0.1:8000/api/health
```

健康响应应为 `{"status":"ok"}`。

## 5. 配置 Nginx 和 HTTPS

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
sudo cp deploy/nginx.conf /etc/nginx/sites-available/coding-agent
sudo sed -i 's/example.com/你的域名/g' /etc/nginx/sites-available/coding-agent
sudo ln -s /etc/nginx/sites-available/coding-agent /etc/nginx/sites-enabled/coding-agent
sudo nginx -t
sudo certbot --nginx -d 你的域名
sudo systemctl reload nginx
```

`deploy/nginx.conf` 为 SSE 路径关闭代理缓冲，并把协议、主机和客户端地址转发给 FastAPI。

## 6. 外网验收

在服务器外部访问：

```bash
curl --fail https://你的域名/api/health
```

浏览器验收：

1. 未登录运行两个 Mock 演示。
2. 使用管理员密码登录。
3. 切换 Real，启动一个受控修复任务。
4. 查看实时事件、Memory 和审批队列。
5. 退出登录并确认管理页面重新受限。

## 7. 日志、升级和回滚

```bash
docker compose -f docker-compose.production.yml logs -f coding-agent
docker compose -f docker-compose.production.yml pull
docker compose -f docker-compose.production.yml up -d
```

回滚时将 `.env` 中 `CODING_AGENT_TAG` 改为上一个版本标签，再运行 `pull` 和 `up -d`。

## 8. 数据备份

```bash
docker run --rm \
  -v coding-agent_coding-agent-data:/data:ro \
  -v "$PWD/backups":/backup \
  alpine tar czf /backup/coding-agent-data-$(date +%F).tar.gz -C /data .
```

备份包含 SQLite 审计和 Memory，不包含 Docker Secret。备份文件也应按敏感数据管理。
