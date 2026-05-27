#!/usr/bin/env python3
"""Transfer .env.staging to server securely without displaying content."""
import paramiko, base64, os

ENV_PATH = os.path.join(os.path.dirname(__file__), '..', '.env.staging')
ENV_PATH = os.path.abspath(ENV_PATH)

with open(ENV_PATH, 'rb') as f:
    content = f.read()

b64 = base64.b64encode(content).decode()

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file('C:/Users/User/.ssh/servantassist_deploy')
client.connect('84.247.128.40', port=2222, username='deploy', pkey=key, timeout=10)

dest = '/opt/servantassist/servantassist-backend/.env.staging'
cmd = f"echo '{b64}' | base64 -d > {dest}; chmod 600 {dest}; echo DONE"
_, out, err = client.exec_command(cmd, timeout=15)
result = out.read().decode('utf-8', 'replace').strip()
error = err.read().decode('utf-8', 'replace').strip()

if 'DONE' in result:
    print(f".env.staging transféré avec succès ({len(content)} octets)")
    _, out, _ = client.exec_command(f'stat -c "%a %U:%G" {dest} && wc -l {dest}')
    print(out.read().decode('utf-8', 'replace').strip())
else:
    print(f"Erreur: {result} {error}")

client.close()
