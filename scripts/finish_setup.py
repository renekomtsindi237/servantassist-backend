#!/usr/bin/env python3
"""Complete server setup: backup script, cron, ownership."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file("C:/Users/User/.ssh/servantassist_deploy")
client.connect("84.247.128.40", port=2222, username="root", pkey=key, timeout=10)

BACKUP_SCRIPT_CONTENT = r"""#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR=/opt/servantassist/backups
DATE=$(date +%Y-%m-%d_%H-%M)
RETAIN_DAYS=7
ENV_FILE=/opt/servantassist/servantassist-backend/.env.staging
if [ ! -f "$ENV_FILE" ]; then
  echo "$(date) ERROR: .env.staging missing" >> /opt/servantassist/logs/backup.log
  exit 1
fi
DB_URL=$(grep "^DATABASE_URL=" "$ENV_FILE" | cut -d= -f2- | tr -d '"')
DUMP=$BACKUP_DIR/servantassist_${DATE}.sql.gz
pg_dump "$DB_URL" | gzip > "$DUMP"
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETAIN_DAYS -delete
SIZE=$(du -sh "$DUMP" | cut -f1)
echo "$(date) OK: $DUMP ($SIZE)" >> /opt/servantassist/logs/backup.log
"""

# Write backup script via tee (no SFTP needed)
import base64
b64 = base64.b64encode(BACKUP_SCRIPT_CONTENT.encode()).decode()
write_cmd = f"echo '{b64}' | base64 -d > /opt/servantassist/scripts/backup-db.sh"
_, out, err = client.exec_command(write_cmd, timeout=10)
out.read(); err.read()

cmds = [
    "chmod +x /opt/servantassist/scripts/backup-db.sh",
    "chown -R deploy:deploy /opt/servantassist",
    # Setup cron
    "(crontab -u deploy -l 2>/dev/null || true; echo '0 3 * * * /opt/servantassist/scripts/backup-db.sh') | sort -u | crontab -u deploy -",
    "crontab -u deploy -l",
    # Verify no password auth for root (SSH key only)
    "grep 'PasswordAuthentication' /etc/ssh/sshd_config",
    # Create deploy sudoers if missing
    "echo 'deploy ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker compose' > /etc/sudoers.d/deploy-docker && chmod 440 /etc/sudoers.d/deploy-docker && echo 'sudoers OK'",
    # Final status
    "echo '=== SERVER READY ===' && id deploy && docker ps --format 'table {{.Names}}\t{{.Status}}' && ufw status | grep -E '(Status|2222|80|443|8000|9000)'",
]

for cmd in cmds:
    _, out, err = client.exec_command(cmd, timeout=15)
    o = out.read().decode("utf-8", "replace").strip()
    e = err.read().decode("utf-8", "replace").strip()
    if o:
        print(o)
    if e and "warning" not in e.lower():
        print(f"ERR: {e}")

client.close()
print("\nSetup completed.")
