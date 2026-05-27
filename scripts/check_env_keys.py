#!/usr/bin/env python3
"""Show env variable names and DB host only (no credentials)."""
import paramiko, re

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file("C:/Users/User/.ssh/servantassist_deploy")
client.connect("84.247.128.40", port=2222, username="deploy", pkey=key, timeout=10)

_, out, _ = client.exec_command(
    "python3 -c \""
    "import re\n"
    "with open('/opt/servantassist/servantassist-backend/.env.staging') as f:\n"
    "    lines = f.readlines()\n"
    "for line in lines:\n"
    "    line = line.strip()\n"
    "    if '=' not in line or line.startswith('#'):\n"
    "        continue\n"
    "    key = line.split('=')[0]\n"
    "    val = line.split('=',1)[1]\n"
    "    if 'db' in key.lower() or 'database' in key.lower() or 'postgres' in key.lower():\n"
    "        # show only host part\n"
    "        m = re.search(r'@([^/?]+)', val)\n"
    "        host = m.group(1) if m else '(no @host)'\n"
    "        print(f'{key}=...@{host}/...')\n"
    "    else:\n"
    "        print(f'{key}=***')\n"
    "\"",
    timeout=10
)
print(out.read().decode("utf-8", "replace"))
client.close()
