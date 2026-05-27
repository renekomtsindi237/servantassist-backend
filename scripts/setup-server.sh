#!/usr/bin/env bash
# =============================================================================
# setup-server.sh — Configuration initiale du VPS Contabo pour ServantAssist
# Exécuter en tant que root : bash setup-server.sh
# =============================================================================
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

DEPLOY_USER="deploy"
DEPLOY_DIR="/opt/servantassist"
SSH_PUB_KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIClLHFxjVSWmQhoDrqyxcXDkgCO5+Th3ECEWLeEZGucw servantassist-deploy"
SSH_PORT=2222

echo "======================================================"
echo " ServantAssist — Configuration VPS Contabo"
echo "======================================================"

# ── 1. Mise à jour système ─────────────────────────────────────────────────
echo "[1/9] Mise à jour système..."
apt-get update -qq && apt-get upgrade -y -qq
apt-get install -y -qq \
  curl wget git ufw fail2ban \
  unattended-upgrades apt-listchanges \
  htop ncdu logrotate \
  postgresql-client

# ── 2. Mises à jour de sécurité automatiques ──────────────────────────────
echo "[2/9] Mises à jour de sécurité automatiques..."
cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Packages "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF
systemctl enable --now unattended-upgrades

# ── 3. Création utilisateur deploy ────────────────────────────────────────
echo "[3/9] Création utilisateur deploy..."
if ! id "$DEPLOY_USER" &>/dev/null; then
  useradd -m -s /bin/bash -G sudo "$DEPLOY_USER"
  echo "$DEPLOY_USER ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker compose, /usr/local/bin/docker-compose" \
    > /etc/sudoers.d/deploy-docker
  chmod 440 /etc/sudoers.d/deploy-docker
fi

# Ajouter la clé SSH
mkdir -p /home/$DEPLOY_USER/.ssh
echo "$SSH_PUB_KEY" > /home/$DEPLOY_USER/.ssh/authorized_keys
chmod 700 /home/$DEPLOY_USER/.ssh
chmod 600 /home/$DEPLOY_USER/.ssh/authorized_keys
chown -R $DEPLOY_USER:$DEPLOY_USER /home/$DEPLOY_USER/.ssh

# Ajouter aussi à root pour la première connexion
mkdir -p /root/.ssh
echo "$SSH_PUB_KEY" >> /root/.ssh/authorized_keys
sort -u /root/.ssh/authorized_keys -o /root/.ssh/authorized_keys

# ── 4. Durcissement SSH ────────────────────────────────────────────────────
echo "[4/9] Durcissement SSH..."
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak

cat > /etc/ssh/sshd_config << EOF
Port $SSH_PORT
AddressFamily any
ListenAddress 0.0.0.0

# Authentification
PermitRootLogin prohibit-password
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
ChallengeResponseAuthentication no
UsePAM yes

# Sécurité
MaxAuthTries 3
MaxSessions 5
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
AllowTcpForwarding no
AllowAgentForwarding no
PrintMotd no

# Utilisateurs autorisés
AllowUsers root $DEPLOY_USER

# Logs
SyslogFacility AUTH
LogLevel VERBOSE
EOF

systemctl restart ssh || systemctl restart sshd || true
echo "  SSH reconfiguré sur le port $SSH_PORT"

# ── 5. Pare-feu UFW ────────────────────────────────────────────────────────
echo "[5/9] Configuration UFW..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow $SSH_PORT/tcp comment "SSH"
ufw allow 80/tcp comment "HTTP"
ufw allow 443/tcp comment "HTTPS"
ufw allow 8000/tcp comment "FastAPI staging"
# Pour Portainer
ufw allow 9000/tcp comment "Portainer"
ufw --force enable
echo "  UFW activé"

# ── 6. Fail2ban ────────────────────────────────────────────────────────────
echo "[6/9] Configuration Fail2ban..."
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5
backend  = systemd

[sshd]
enabled  = true
port     = $SSH_PORT
logpath  = %(sshd_log)s
maxretry = 3
bantime  = 86400

[nginx-http-auth]
enabled = false

[nginx-botsearch]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/error.log
EOF

systemctl enable --now fail2ban
echo "  Fail2ban activé"

# ── 7. Installation Docker ─────────────────────────────────────────────────
echo "[7/9] Installation Docker..."
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  usermod -aG docker $DEPLOY_USER
  systemctl enable --now docker
  echo "  Docker installé"
else
  echo "  Docker déjà installé"
fi

# Portainer (interface Docker web)
if ! docker ps -a --format '{{.Names}}' | grep -q "^portainer$"; then
  docker volume create portainer_data
  docker run -d \
    --name portainer \
    --restart=always \
    -p 9000:9000 \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v portainer_data:/data \
    portainer/portainer-ce:latest
  echo "  Portainer installé sur :9000"
fi

# ── 8. Répertoire application ──────────────────────────────────────────────
echo "[8/9] Création répertoire application..."
mkdir -p $DEPLOY_DIR
mkdir -p $DEPLOY_DIR/backups
mkdir -p $DEPLOY_DIR/logs
chown -R $DEPLOY_USER:$DEPLOY_USER $DEPLOY_DIR

# ── 9. Cron backup PostgreSQL → local ─────────────────────────────────────
echo "[9/9] Configuration backup automatique..."
BACKUP_SCRIPT="/opt/servantassist/scripts/backup-db.sh"
mkdir -p /opt/servantassist/scripts

cat > $BACKUP_SCRIPT << 'BACKUPEOF'
#!/usr/bin/env bash
# Backup PostgreSQL staging → /opt/servantassist/backups/
set -euo pipefail

BACKUP_DIR="/opt/servantassist/backups"
DATE=$(date +%Y-%m-%d_%H-%M)
RETAIN_DAYS=7
ENV_FILE="/opt/servantassist/servantassist-backend/.env.staging"

if [ ! -f "$ENV_FILE" ]; then
  echo "$(date) ERROR: .env.staging introuvable" >> /opt/servantassist/logs/backup.log
  exit 1
fi

DB_URL=$(grep "^DATABASE_URL=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"')

if [ -z "$DB_URL" ]; then
  echo "$(date) ERROR: DATABASE_URL manquante" >> /opt/servantassist/logs/backup.log
  exit 1
fi

DUMP_FILE="$BACKUP_DIR/servantassist_staging_${DATE}.sql.gz"

pg_dump "$DB_URL" | gzip > "$DUMP_FILE"

# Suppression des sauvegardes > 7 jours
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETAIN_DAYS -delete

SIZE=$(du -sh "$DUMP_FILE" | cut -f1)
echo "$(date) OK: backup $DUMP_FILE ($SIZE)" >> /opt/servantassist/logs/backup.log
BACKUPEOF

chmod +x $BACKUP_SCRIPT
chown $DEPLOY_USER:$DEPLOY_USER $BACKUP_SCRIPT

# Cron : backup quotidien à 3h00 UTC
(crontab -u $DEPLOY_USER -l 2>/dev/null; echo "0 3 * * * $BACKUP_SCRIPT") \
  | crontab -u $DEPLOY_USER -
echo "  Backup cron configuré (3h00 UTC quotidien)"

# ── Résumé final ───────────────────────────────────────────────────────────
echo ""
echo "======================================================"
echo " CONFIGURATION TERMINÉE"
echo "======================================================"
echo ""
echo "  Utilisateur deploy : $DEPLOY_USER"
echo "  Port SSH           : $SSH_PORT"
echo "  Portainer          : http://$(hostname -I | awk '{print $1}'):9000"
echo "  Répertoire app     : $DEPLOY_DIR"
echo ""
echo "  IMPORTANT — GitHub Secrets à configurer :"
echo "  STAGING_HOST = $(hostname -I | awk '{print $1}')"
echo "  STAGING_USER = $DEPLOY_USER"
echo "  STAGING_PORT = $SSH_PORT"
echo ""
echo "  Prochaine étape :"
echo "  ssh -p $SSH_PORT $DEPLOY_USER@$(hostname -I | awk '{print $1}')"
echo ""
echo "======================================================"
