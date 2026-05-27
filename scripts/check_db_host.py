#!/usr/bin/env python3
"""Extract DB host from env file and test connectivity (no credentials revealed)."""
import paramiko, re

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file("C:/Users/User/.ssh/servantassist_deploy")
client.connect("84.247.128.40", port=2222, username="deploy", pkey=key, timeout=10)

# Read the DATABASE_URL value and extract only the host:port
_, out, _ = client.exec_command(
    "python3 -c \""
    "import re, os\n"
    "with open('/opt/servantassist/servantassist-backend/.env.staging') as f:\n"
    "    content = f.read()\n"
    "m = re.search(r'DATABASE_URL=(.+)', content)\n"
    "if m:\n"
    "    url = m.group(1).strip()\n"
    "    # Extract host:port only\n"
    "    host_m = re.search(r'@([^/]+)/', url)\n"
    "    if host_m:\n"
    "        print('HOST:', host_m.group(1))\n"
    "    else:\n"
    "        print('PARSE_ERROR')\n"
    "else:\n"
    "    print('NO_DB_URL')\n"
    "\"",
    timeout=10
)
result = out.read().decode("utf-8", "replace").strip()
print(result)

if "HOST:" in result:
    host_port = result.replace("HOST:", "").strip()
    if ":" in host_port:
        host, port = host_port.rsplit(":", 1)
        port = port.split("?")[0]
    else:
        host = host_port.split("?")[0]
        port = "5432"

    print(f"Testing TCP to {host}:{port}...")
    _, out, _ = client.exec_command(f"nc -zv {host} {port} 2>&1", timeout=15)
    print(out.read().decode("utf-8", "replace").strip())

    # Also test DNS resolution
    _, out, _ = client.exec_command(f"nslookup {host} 2>&1 | head -5", timeout=10)
    print("DNS:", out.read().decode("utf-8", "replace").strip())

client.close()
