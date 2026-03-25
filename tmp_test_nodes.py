#!/usr/bin/env python3
import json
import subprocess
import time
import urllib.request

SECRET = "xiaopihong123456.@"
API = "http://127.0.0.1:9090"


def api(method: str, path: str, payload=None):
    data = None
    headers = {"Authorization": f"Bearer {SECRET}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode("utf-8")
        if not body.strip():
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    return {
        "rc": p.returncode,
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip(),
    }


proxy = api("GET", "/proxies/Proxy")
nodes = proxy["all"]
results = []

for idx, node in enumerate(nodes, 1):
    print(f"[{idx}/{len(nodes)}] {node}", flush=True)
    api("PUT", "/proxies/Proxy", {"name": node})
    time.sleep(1.2)

    http = run(
        [
            "docker",
            "exec",
            "sub2api",
            "curl",
            "-sS",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            "-m",
            "5",
            "-x",
            "http://mihomo:7890",
            "http://httpbin.org/status/204",
        ]
    )
    openai = run(
        [
            "docker",
            "exec",
            "sub2api",
            "curl",
            "-sS",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            "-m",
            "5",
            "-x",
            "http://mihomo:7890",
            "https://api.openai.com/v1/models",
        ]
    )
    logs = run(["docker", "logs", "--since", "12s", "mihomo"])
    log_lines = [line for line in (logs["stdout"] + "\n" + logs["stderr"]).splitlines() if line.strip()]

    results.append(
        {
            "node": node,
            "http_rc": http["rc"],
            "http_out": http["stdout"],
            "http_err": http["stderr"],
            "openai_rc": openai["rc"],
            "openai_out": openai["stdout"],
            "openai_err": openai["stderr"],
            "log_tail": log_lines[-2:],
        }
    )

print("=== RESULTS ===")
for item in results:
    print(json.dumps(item, ensure_ascii=False))
