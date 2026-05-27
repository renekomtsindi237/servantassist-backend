#!/usr/bin/env python3
"""Quick DNS + routing check without waiting for TCP timeout."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file("C:/Users/User/.ssh/servantassist_deploy")
client.connect("84.247.128.40", port=2222, username="deploy", pkey=key, timeout=10)

cmds = [
    ("DNS supabase direct", "nslookup db.ruvzxepgytbfysnlrzxk.supabase.co 2>&1 | head -8"),
    ("DNS pooler", "nslookup aws-0-eu-west-2.pooler.supabase.com 2>&1 | head -6"),
    ("IPv6 on host", "ip -6 route show default 2>&1 | head -3"),
    ("Docker IPv6", "docker network inspect bridge --format '{{.EnableIPv6}}' 2>&1"),
    ("Route to supabase", "ip route get $(nslookup db.ruvzxepgytbfysnlrzxk.supabase.co 2>/dev/null | awk '/Address:/{print $2}' | tail -1) 2>&1 | head -3"),
]

for label, cmd in cmds:
    _, out, _ = client.exec_command(cmd, timeout=10)
    result = out.read().decode("utf-8", "replace").strip()
    print(f"[{label}]: {result}")
    print()

client.close()
