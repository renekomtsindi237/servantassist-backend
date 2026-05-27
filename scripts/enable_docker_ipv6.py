#!/usr/bin/env python3
"""Enable IPv6 in Docker daemon on VPS."""
import base64
import io
import json
import sys

import paramiko

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file("C:/Users/User/.ssh/servantassist_deploy")
client.connect("84.247.128.40", port=2222, username="root", pkey=key, timeout=10)

daemon_config = {"ipv6": True, "fixed-cidr-v6": "fd00::/80", "ip6tables": True}
b64 = base64.b64encode(json.dumps(daemon_config, indent=2).encode()).decode()

cmds = [
    f"echo '{b64}' | base64 -d > /etc/docker/daemon.json && echo WRITTEN",
    "systemctl restart docker && sleep 3 && echo DOCKER_RESTARTED",
    "docker network inspect bridge --format 'IPv6: {{.EnableIPv6}}'",
    "docker run --rm alpine sh -c 'nc -zv db.ruvzxepgytbfysnlrzxk.supabase.co 5432 2>&1 || echo FAIL'",
]

for cmd in cmds:
    _, out, _ = client.exec_command(cmd, timeout=30)
    result = out.read().decode("utf-8", "replace").strip()
    print(f"[{cmd[:50]}]")
    print(f"  {result}")

client.close()
