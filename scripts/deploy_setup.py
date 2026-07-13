#!/usr/bin/env python3
"""
Script d'initialisation serveur via SSH (paramiko).
Usage: python deploy_setup.py
"""
import io
import os
import sys
import time

import paramiko

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HOST = "84.247.128.40"
PORT = 22
USER = "root"
PASSWORD = os.environ.get("VPS_ROOT_PASS", "")

SETUP_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "setup-server.sh")

def run(client, cmd, timeout=120):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    return code, out, err

def main():
    if not PASSWORD:
        print("ERROR: VPS_ROOT_PASS env var manquante")
        sys.exit(1)

    print(f"[1/4] Connexion SSH à {HOST}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=15)
    print("      Connexion OK")

    print("[2/4] Upload du script de configuration...")
    sftp = client.open_sftp()
    sftp.put(SETUP_SCRIPT_PATH, "/root/setup-server.sh")
    sftp.close()
    code, out, err = run(client, "chmod +x /root/setup-server.sh")
    print("      Upload OK")

    print("[3/4] Exécution du setup (2-3 minutes)...")
    transport = client.get_transport()
    channel = transport.open_session()
    channel.exec_command("bash /root/setup-server.sh 2>&1")

    while not channel.exit_status_ready():
        if channel.recv_ready():
            data = channel.recv(4096).decode("utf-8", errors="replace")
            for line in data.splitlines():
                if line.strip():
                    print(f"      {line}")
        time.sleep(0.5)

    exit_code = channel.recv_exit_status()

    # Lire le reste
    while channel.recv_ready():
        data = channel.recv(4096).decode("utf-8", errors="replace")
        for line in data.splitlines():
            if line.strip():
                print(f"      {line}")

    if exit_code != 0:
        print(f"\nERROR: setup-server.sh a échoué (code {exit_code})")
        client.close()
        sys.exit(1)

    print("\n[4/4] Vérification...")
    code, out, _ = run(client, "id deploy && docker --version && ufw status | head -5")
    print(f"      {out.strip()}")

    client.close()
    print("\n====================================================")
    print(" SERVEUR CONFIGURÉ AVEC SUCCÈS")
    print("====================================================")
    print(f" Connexion future : ssh -p 2222 -i ~/.ssh/servantassist_deploy deploy@{HOST}")
    print("====================================================")

if __name__ == "__main__":
    main()
