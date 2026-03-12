# 代理栈（Mihomo）

本目录用于部署独立的 Mihomo 代理栈，供同一台服务器上的 Docker 容器（例如 `sub2api`）通过代理访问外网。

## 1. 准备

1. 编辑 `config/mihomo.yaml`：
- 将 `proxy-providers.main.url` 改为你的订阅地址
- 将 `secret` 改为强密码（用于面板/API 鉴权）
2. 确保共享 Docker 网络存在（仅需执行一次）：

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

## 4. 对接 `sub2api`（服务器目录：`/root/sub2api/deploy`）

目标部署文件为 `docker-compose.local.yml`。

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

### 4.3 重启 `sub2api`

```bash
cd /root/sub2api/deploy
docker compose -f docker-compose.local.yml -f docker-compose.override.yml up -d
```

## 5. 节点切换面板（推荐：SSH 隧道）

`mihomo` 提供控制 API（`9090`），可通过 Web 面板连接后切换节点和策略组。

### 5.1 保持 9090 不暴露公网

当前 `docker-compose.yml` 已设置为仅本机绑定：

```yaml
ports:
  - "127.0.0.1:9090:9090"
```

### 5.2 在本地电脑建立 SSH 隧道

Windows PowerShell（推荐）：

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:9090:127.0.0.1:9090 root@你的服务器IP
```

macOS / Linux：

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:9090:127.0.0.1:9090 root@你的服务器IP
```

说明：
- 这条命令会把你本机 `127.0.0.1:9090` 转发到服务器 `127.0.0.1:9090`
- 终端窗口保持连接状态，隧道才有效
- 示例：
  `ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:9090:127.0.0.1:9090 root@119.29.249.17`

### 5.3 本地打开面板地址并连接

1. 在浏览器打开 `metacubexd`：`https://metacubexd.pages.dev/`
2. 若上面地址不可用，可使用 `Yacd`：`https://yacd.metacubex.one/`
3. 控制器地址填写：`http://127.0.0.1:9090`
4. Secret 填写：`config/mihomo.yaml` 中的 `secret`
5. 保存后即可在面板中切换节点/策略组、刷新订阅

可选本地连通性测试（先不走面板）：

```bash
curl -H "Authorization: Bearer <你的secret>" http://127.0.0.1:9090/version
```

若返回版本 JSON，说明 SSH 隧道和控制器均正常。

## 6. 安全建议

- 不要把 `9090` 暴露到公网。
- 不要对公网开放 `7890/7891`。
- 仅对外暴露业务入口端口（例如 `sub2api` 的 8080，或反代后的 80/443）。
