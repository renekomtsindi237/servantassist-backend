# Variables d'Environnement - ServantAssist

**Date** : 11 février 2026  
**Version** : 1.0  
**⚠️ CONFIDENTIEL - NE PAS COMMITER**

---

## Vue d'Ensemble

Ce document liste toutes les variables d'environnement nécessaires pour le déploiement de ServantAssist. Les valeurs sont masquées pour des raisons de sécurité.

---

## Variables GitHub Secrets

### Authentification Container Registry

```bash
# Container Registry
CONTAINER_REGISTRY=*****.dkr.ecr.eu-west-1.amazonaws.com
REGISTRY_USERNAME=AWS
REGISTRY_PASSWORD=*****************************

# AWS Credentials
AWS_ACCESS_KEY_ID=AKIA******************
AWS_SECRET_ACCESS_KEY=****************************************
AWS_REGION=eu-west-1
```

### Base de Données de Test

```bash
# Test Database
TEST_DB_HOST=localhost
TEST_DB_PORT=5432
TEST_DB_NAME=servantassist_test
TEST_DB_USER=test_user
TEST_DB_PASSWORD=***************
TEST_JWT_SECRET=************************************************
```

### Environnement Development

```bash
# ECS Configuration
ECS_CLUSTER_DEV=servantassist-dev-cluster
ECS_SERVICE_DEV=servantassist-dev-service
ECS_TASK_DEFINITION_DEV=servantassist-dev-task:latest
ECS_MIGRATION_TASK_DEV=servantassist-dev-migration:latest

# Network Configuration
SUBNET_IDS_DEV=subnet-********,subnet-********
SECURITY_GROUP_DEV=sg-****************

# API URL
DEV_API_URL=https://dev-api.servantassist.com
```

### Environnement Staging

```bash
# ECS Configuration
ECS_CLUSTER_STAGING=servantassist-staging-cluster
ECS_SERVICE_STAGING=servantassist-staging-service
ECS_TASK_DEFINITION_STAGING=servantassist-staging-task:latest
ECS_MIGRATION_TASK_STAGING=servantassist-staging-migration:latest

# Network Configuration
SUBNET_IDS_STAGING=subnet-********,subnet-********
SECURITY_GROUP_STAGING=sg-****************

# API URL
STAGING_API_URL=https://staging-api.servantassist.com
```

### Environnement Production

```bash
# ECS Configuration
ECS_CLUSTER_PROD=servantassist-prod-cluster
ECS_SERVICE_PROD=servantassist-prod-service
ECS_TASK_DEFINITION_PROD=servantassist-prod-task:latest
ECS_MIGRATION_TASK_PROD=servantassist-prod-migration:latest

# Network Configuration
SUBNET_IDS_PROD=subnet-********,subnet-********,subnet-********
SECURITY_GROUP_PROD=sg-****************

# Database
RDS_INSTANCE_PROD=servantassist-prod-db

# API URL
PROD_API_URL=https://api.servantassist.com
```

### Notifications

```bash
# Slack Integration
SLACK_WEBHOOK=https://hooks.slack.com/services/T**********/**********/**************************
```

---

## Variables d'Environnement Runtime

### Application Core

```bash
# Application
APP_NAME=ServantAssist
APP_VERSION=1.0.0
ENVIRONMENT=production  # development, staging, production
DEBUG=false
LOG_LEVEL=INFO

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_RELOAD=false
```

### Base de Données

```bash
# PostgreSQL
DATABASE_URL=postgresql://username:password@host:port/database
DB_HOST=servantassist-prod.************.eu-west-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=servantassist
DB_USER=servantassist_user
DB_PASSWORD=********************************
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

### Cache Redis

```bash
# Redis
REDIS_URL=redis://username:password@host:port/db
REDIS_HOST=servantassist-prod.******.cache.amazonaws.com
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=************************
REDIS_MAX_CONNECTIONS=100
REDIS_TIMEOUT=5
```

### Sécurité

```bash
# JWT Configuration
JWT_SECRET_KEY=************************************************
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Password Hashing
BCRYPT_ROUNDS=12

# CORS
CORS_ORIGINS=https://app.servantassist.com,https://admin.servantassist.com
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,PATCH,DELETE,OPTIONS
CORS_ALLOW_HEADERS=*

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
RATE_LIMIT_STORAGE=redis
```

### Services Externes

```bash
# Email Service (SMTP)
SMTP_HOST=email-smtp.eu-west-1.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=AKIA******************
SMTP_PASSWORD=********************************
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=noreply@servantassist.com
SMTP_FROM_NAME=ServantAssist

# WhatsApp Business API
WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_ACCESS_TOKEN=************************************************
WHATSAPP_PHONE_NUMBER_ID=***************
WHATSAPP_VERIFY_TOKEN=********************************

# File Storage (AWS S3)
AWS_S3_BUCKET=servantassist-uploads-prod
AWS_S3_REGION=eu-west-1
AWS_S3_ACCESS_KEY_ID=AKIA******************
AWS_S3_SECRET_ACCESS_KEY=****************************************
AWS_S3_ENDPOINT_URL=https://s3.eu-west-1.amazonaws.com
AWS_S3_USE_SSL=true
AWS_S3_SIGNATURE_VERSION=s3v4

# CDN (CloudFront)
CLOUDFRONT_DOMAIN=cdn.servantassist.com
CLOUDFRONT_DISTRIBUTION_ID=E**************
```

### Monitoring et Logging

```bash
# Prometheus
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
PROMETHEUS_METRICS_PATH=/metrics

# Structured Logging
LOG_FORMAT=json
LOG_FILE=/app/logs/servantassist.log
LOG_MAX_SIZE=100MB
LOG_BACKUP_COUNT=5
LOG_ROTATION=daily

# Sentry (Error Tracking)
SENTRY_DSN=https://********************************@sentry.io/project-id
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1

# Health Checks
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_PATH=/health
HEALTH_CHECK_TIMEOUT=30
```

### Features Flags

```bash
# Feature Toggles
FEATURE_WHATSAPP_NOTIFICATIONS=true
FEATURE_EMAIL_NOTIFICATIONS=true
FEATURE_FILE_UPLOADS=true
FEATURE_RATE_LIMITING=true
FEATURE_METRICS=true
FEATURE_CACHING=true
FEATURE_ASYNC_TASKS=true
```

### Sécurité Avancée

```bash
# Security Headers
SECURITY_HEADERS_ENABLED=true
HSTS_MAX_AGE=31536000
CSP_POLICY=default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'
X_FRAME_OPTIONS=DENY
X_CONTENT_TYPE_OPTIONS=nosniff
REFERRER_POLICY=strict-origin-when-cross-origin

# API Security
API_KEY_HEADER=X-API-Key
API_RATE_LIMIT_BYPASS_KEY=********************************
ADMIN_API_KEY=************************************************

# Encryption
ENCRYPTION_KEY=************************************************
FIELD_ENCRYPTION_ENABLED=true
```

### Performance

```bash
# Connection Pooling
DB_POOL_PRE_PING=true
DB_POOL_ECHO=false
DB_POOL_ECHO_POOL=false

# Caching
CACHE_TTL_DEFAULT=300
CACHE_TTL_USER_SESSION=1800
CACHE_TTL_API_RESPONSE=60
CACHE_TTL_STATIC_DATA=3600

# Async Configuration
ASYNC_POOL_SIZE=100
ASYNC_MAX_WORKERS=50
ASYNC_TIMEOUT=30
```

### Backup et Recovery

```bash
# Database Backup
DB_BACKUP_ENABLED=true
DB_BACKUP_SCHEDULE=0 2 * * *  # Daily at 2 AM
DB_BACKUP_RETENTION_DAYS=30
DB_BACKUP_S3_BUCKET=servantassist-backups-prod

# File Backup
FILE_BACKUP_ENABLED=true
FILE_BACKUP_SCHEDULE=0 3 * * *  # Daily at 3 AM
FILE_BACKUP_RETENTION_DAYS=90
```

---

## Configuration par Environnement

### Development

```bash
# Override for development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
API_RELOAD=true
API_WORKERS=1

# Relaxed security for dev
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
RATE_LIMIT_REQUESTS=1000

# Development services
DATABASE_URL=postgresql://dev_user:dev_pass@localhost:5432/servantassist_dev
REDIS_URL=redis://localhost:6379/0

# Disable external services
FEATURE_WHATSAPP_NOTIFICATIONS=false
FEATURE_EMAIL_NOTIFICATIONS=false
SENTRY_DSN=  # Empty to disable
```

### Staging

```bash
# Staging configuration
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO

# Staging-specific URLs
DATABASE_URL=postgresql://staging_user:staging_pass@staging-db:5432/servantassist_staging
REDIS_URL=redis://staging-redis:6379/0

# Staging services
CORS_ORIGINS=https://staging-app.servantassist.com
WHATSAPP_PHONE_NUMBER_ID=***************  # Staging number
SMTP_FROM_EMAIL=staging@servantassist.com
```

### Production

```bash
# Production configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# Production security
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
BCRYPT_ROUNDS=14
RATE_LIMIT_REQUESTS=50

# All features enabled
FEATURE_WHATSAPP_NOTIFICATIONS=true
FEATURE_EMAIL_NOTIFICATIONS=true
FEATURE_FILE_UPLOADS=true
FEATURE_RATE_LIMITING=true
FEATURE_METRICS=true
FEATURE_CACHING=true
```

---

## Secrets Management

### AWS Secrets Manager

Les secrets sensibles sont stockés dans AWS Secrets Manager :

```bash
# Secret ARNs
DB_PASSWORD_SECRET_ARN=arn:aws:secretsmanager:eu-west-1:account:secret:servantassist/db/password-******
JWT_SECRET_ARN=arn:aws:secretsmanager:eu-west-1:account:secret:servantassist/jwt/secret-******
REDIS_PASSWORD_SECRET_ARN=arn:aws:secretsmanager:eu-west-1:account:secret:servantassist/redis/password-******
WHATSAPP_TOKEN_SECRET_ARN=arn:aws:secretsmanager:eu-west-1:account:secret:servantassist/whatsapp/token-******
```

### Rotation des Secrets

```bash
# Rotation Configuration
SECRET_ROTATION_ENABLED=true
SECRET_ROTATION_SCHEDULE=rate(30 days)
SECRET_ROTATION_LAMBDA_ARN=arn:aws:lambda:eu-west-1:account:function:servantassist-secret-rotation
```

---

## Variables d'Infrastructure

### Terraform

```bash
# Terraform Backend
TF_VAR_region=eu-west-1
TF_VAR_environment=production
TF_VAR_project_name=servantassist

# VPC Configuration
TF_VAR_vpc_cidr=10.0.0.0/16
TF_VAR_availability_zones=["eu-west-1a", "eu-west-1b", "eu-west-1c"]
TF_VAR_private_subnet_cidrs=["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
TF_VAR_public_subnet_cidrs=["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

# ECS Configuration
TF_VAR_ecs_cluster_name=servantassist-prod-cluster
TF_VAR_ecs_service_name=servantassist-prod-service
TF_VAR_ecs_task_cpu=1024
TF_VAR_ecs_task_memory=2048
TF_VAR_ecs_desired_count=3
TF_VAR_ecs_max_capacity=10
TF_VAR_ecs_min_capacity=2

# RDS Configuration
TF_VAR_rds_instance_class=db.t3.medium
TF_VAR_rds_allocated_storage=100
TF_VAR_rds_max_allocated_storage=1000
TF_VAR_rds_backup_retention_period=7
TF_VAR_rds_multi_az=true

# ElastiCache Configuration
TF_VAR_redis_node_type=cache.t3.micro
TF_VAR_redis_num_cache_nodes=1
TF_VAR_redis_parameter_group_name=default.redis7
```

---

## Validation des Variables

### Script de Validation

```bash
#!/bin/bash
# validate-env.sh - Valide les variables d'environnement

required_vars=(
    "DATABASE_URL"
    "REDIS_URL"
    "JWT_SECRET_KEY"
    "ENVIRONMENT"
)

for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        echo "❌ Variable manquante: $var"
        exit 1
    fi
done

echo "✅ Toutes les variables requises sont définies"
```

### Checklist de Déploiement

- [ ] Variables d'environnement définies
- [ ] Secrets AWS configurés
- [ ] Base de données accessible
- [ ] Redis accessible
- [ ] S3 bucket configuré
- [ ] CloudFront configuré
- [ ] Certificats SSL valides
- [ ] DNS configuré
- [ ] Monitoring configuré
- [ ] Alertes configurées

---

## Sécurité des Variables

### Bonnes Pratiques

1. **Jamais en plain text** dans le code
2. **Rotation régulière** des secrets
3. **Principe du moindre privilège**
4. **Chiffrement** au repos et en transit
5. **Audit** des accès aux secrets
6. **Séparation** par environnement
7. **Validation** des formats
8. **Monitoring** des utilisations

### Outils de Sécurité

- **AWS Secrets Manager** : Stockage sécurisé
- **AWS IAM** : Contrôle d'accès
- **AWS KMS** : Chiffrement
- **GitHub Secrets** : CI/CD
- **Detect-secrets** : Détection dans le code
- **Vault** : Alternative pour secrets

---

## Troubleshooting

### Problèmes Courants

1. **Variable manquante**
   ```bash
   Error: Environment variable 'DATABASE_URL' not found
   Solution: Vérifier la configuration des secrets
   ```

2. **Format incorrect**
   ```bash
   Error: Invalid DATABASE_URL format
   Solution: Vérifier le format postgresql://user:pass@host:port/db
   ```

3. **Permissions insuffisantes**
   ```bash
   Error: Access denied to secret
   Solution: Vérifier les permissions IAM
   ```

4. **Secret expiré**
   ```bash
   Error: Token expired
   Solution: Forcer la rotation du secret
   ```

---

## Maintenance

### Rotation des Secrets

- **Automatique** : 30 jours pour JWT, DB, Redis
- **Manuelle** : API keys externes
- **Urgente** : En cas de compromission

### Monitoring

- **CloudWatch** : Métriques d'utilisation
- **CloudTrail** : Audit des accès
- **Config** : Conformité des configurations
- **Security Hub** : Alertes sécurité

### Backup

- **Secrets** : Backup automatique AWS
- **Configuration** : Versioning Terraform
- **Documentation** : Git repository

---

## Contact

Pour toute question concernant les variables d'environnement :

- **DevOps Team** : devops@servantassist.com
- **Security Team** : security@servantassist.com
- **On-call** : +33 X XX XX XX XX

---

**⚠️ IMPORTANT** : Ce document contient des informations sensibles. Ne jamais le commiter dans un repository public ou le partager sans autorisation.

**Dernière mise à jour** : 11 février 2026  
**Prochaine révision** : 11 mars 2026