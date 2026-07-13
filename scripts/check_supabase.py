#!/usr/bin/env python3
"""Test Supabase TCP connectivity from VPS."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file("C:/Users/User/.ssh/servantassist_deploy")
client.connect("84.247.128.40", port=2222, username="deploy", pkey=key, timeout=10)

cmds = [
    # Test direct connection to Supabase
    "nc -zv db.ruvzxepgytbfysnlrzxk.supabase.co 5432 2>&1",
    "nc -zv aws-0-eu-west-2.pooler.supabase.com 6543 2>&1",
    # Test from inside Docker
    "docker run --rm alpine sh -c 'nc -zv db.ruvzxepgytbfysnlrzxk.supabase.co 5432 2>&1'",
    # Check IPv6
    "ip -6 addr show | grep inet6 | head -3",
]
for cmd in cmds:
    _, out, err = client.exec_command(cmd, timeout=15)
    o = out.read().decode("utf-8", "replace").strip()
    e = err.read().decode("utf-8", "replace").strip()
    print(f"CMD: {cmd[:60]}")
    if o: print(f"  OUT: {o}")
    if e: print(f"  ERR: {e}")

client.close()
