#!/usr/bin/env python3
"""Check VPS Docker network and DB connectivity."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file("C:/Users/User/.ssh/servantassist_deploy")
client.connect("84.247.128.40", port=2222, username="deploy", pkey=key, timeout=10)

# Test Docker container network access
_, out, _ = client.exec_command(
    "docker run --rm alpine sh -c 'ping -c2 8.8.8.8 2>&1 | tail -2; wget -qO- --timeout=5 https://github.com > /dev/null 2>&1 && echo HTTPS_OK || echo HTTPS_FAIL'",
    timeout=30
)
print("Docker network:", out.read().decode("utf-8", "replace").strip())

# Get DB hostname only (mask credentials)
_, out, _ = client.exec_command(
    r"""grep '^DATABASE_URL' /opt/servantassist/servantassist-backend/.env.staging | sed 's|postgresql+asyncpg://[^@]*@||' | cut -d'/' -f1 | cut -d'?' -f1""",
    timeout=5
)
db_host = out.read().decode("utf-8", "replace").strip()
print(f"DB host:port = {db_host}")

# Test TCP connectivity to DB host
if ":" in db_host:
    host, port = db_host.rsplit(":", 1)
else:
    host, port = db_host, "5432"

_, out, _ = client.exec_command(
    f"nc -zv {host} {port} 2>&1 || echo 'TCP_FAILED'",
    timeout=10
)
print("DB TCP test:", out.read().decode("utf-8", "replace").strip())

client.close()
