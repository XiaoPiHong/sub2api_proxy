# 代理栈（Mihomo）

本项目用于部署独立的 Mihomo 代理栈，供同一台服务器上的 Docker 容器（例如 `sub2api`）通过代理访问外网。

## 1. 准备

1. 编辑 `config/mihomo.yaml`
- 将 `proxy-providers.main.url` 改为你的订阅地址
- 将 `secret` 改为强密码，用于面板/API 鉴权

2. 确保共享 Docker 网络存在（仅需执行一次）

```bash
docker network create deploy_sub2api-network
```

## 2. 启动代理栈

```bash
docker compose up -d
```

## 3. 检查代理栈状态

```bash
docker compose ps
docker logs -f mihomo
```

## 4. 对接 sub2api

服务器目录示例：`/root/sub2api/deploy`

### 4.1 修改 `.env`

在 `/root/sub2api/deploy/.env` 末尾追加：

```env
OUTBOUND_HTTP_PROXY=http://mihomo:7890
OUTBOUND_HTTPS_PROXY=http://mihomo:7890
OUTBOUND_ALL_PROXY=socks5://mihomo:7890
OUTBOUND_NO_PROXY=localhost,127.0.0.1,postgres,redis,sub2api-postgres,sub2api-redis
UPDATE_PROXY_URL=http://mihomo:7890
PROXY_NETWORK=deploy_sub2api-network
```

### 4.2 新建 `docker-compose.override.yml`

在 `/root/sub2api/deploy/docker-compose.override.yml` 写入：

```yaml
services:
  sub2api:
    environment:
      - HTTP_PROXY=${OUTBOUND_HTTP_PROXY}
      - HTTPS_PROXY=${OUTBOUND_HTTPS_PROXY}
      - ALL_PROXY=${OUTBOUND_ALL_PROXY}
      - NO_PROXY=${OUTBOUND_NO_PROXY}
      - UPDATE_PROXY_URL=${UPDATE_PROXY_URL}
    networks:
      - proxy-egress

networks:
  proxy-egress:
    external: true
    name: ${PROXY_NETWORK}
```

### 4.3 重启 sub2api

```bash
cd /root/sub2api/deploy
docker compose -f docker-compose.local.yml -f docker-compose.override.yml up -d
```

## 5. 使用 Mihomo 面板

`mihomo` 提供控制 API（`9090`），可通过 Web 面板连接后切换节点和策略组。

### 5.1 保持 9090 不暴露公网

当前 `docker-compose.yml` 已设置为仅本机绑定：

```yaml
ports:
  - "127.0.0.1:9090:9090"
```

### 5.2 在本地电脑建立 SSH 隧道

Windows PowerShell：

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:9090:127.0.0.1:9090 root@你的服务器IP
```

macOS / Linux：

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:9090:127.0.0.1:9090 root@你的服务器IP
```

说明：
- 该命令会把你本机 `127.0.0.1:9090` 转发到服务器 `127.0.0.1:9090`
- 终端窗口保持连接时，隧道才有效

### 5.3 本地打开面板并连接

1. 打开 `https://metacubexd.pages.dev/`
2. 如果不可用，也可以使用 `https://yacd.metacubex.one/`
3. 控制器地址填写：`http://127.0.0.1:9090`
4. Secret 填写 `config/mihomo.yaml` 中的 `secret`
5. 保存后即可在面板中切换节点和策略组

也可以先做本地连通性测试：

```bash
curl -H "Authorization: Bearer <你的secret>" http://127.0.0.1:9090/version
```

如果返回版本 JSON，说明 SSH 隧道和控制器均正常。

## 6. 安全建议

- 不要把 `9090` 暴露到公网
- 不要对公网开放 `7890/7891`
- 仅对外暴露业务入口端口，例如 `sub2api` 的 `8080`，或反代后的 `80/443`

## 7. 故障排查说明

### 7.1 Mihomo 的 DNS 与节点域名解析

本项目在 `config/mihomo.yaml` 中保留了额外的 `hosts:` 和 `dns:` 配置。

原因：
- 部分订阅节点域名在 Mihomo 内部可能解析失败
- 部分默认节点可能只有 IPv6，在仅有 IPv4 出站的服务器上会失败
- 这种情况下，`sub2api` 虽然能连到 `mihomo:7890`，但上游 TLS 请求仍然会失败

可快速检查：

```bash
docker exec sub2api sh -lc 'curl -I -x http://mihomo:7890 https://api.openai.com/v1/models'
docker exec sub2api sh -lc 'curl -I -x http://mihomo:7890 https://chatgpt.com/backend-api/codex/responses'
```

预期结果：
- OpenAI 接口在未带 API 凭证时返回 `401 Unauthorized`
- ChatGPT Codex 接口在使用 `GET` 探测时返回 `405 Method Not Allowed`

这两种结果都表示代理、TLS 和路由已经正常工作。

### 7.2 sub2api 的账号测试默认不会使用容器级 HTTP_PROXY

`sub2api` 的账号测试接口（`/api/v1/admin/accounts/{id}/test`）默认不会自动使用 Docker 容器级的 `HTTP_PROXY` / `HTTPS_PROXY`。它会优先使用 sub2api 后台中“账号绑定的代理”。

如果账号测试仍然在直连上游，请在 sub2api 管理后台这样配置：

1. 打开 `/admin/proxies`
2. 新建一个代理：
- 名称：`mihomo-http`
- 协议：`HTTP`
- 主机：`mihomo`
- 端口：`7890`
- 用户名/密码：留空
3. 编辑目标账号
4. 将代理从“无代理”改为 `mihomo-http`
5. 保存后重新测试

如果账号代理为空，账号测试接口可能会绕过 Mihomo，直接去连 `chatgpt.com`。
