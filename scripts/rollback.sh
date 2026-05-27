#!/bin/bash

# ServantAssist Rollback Script
# Usage: ./scripts/rollback.sh [environment] [target_version]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT=${1:-staging}
TARGET_VERSION=${2:-}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate environment
validate_environment() {
    case $ENVIRONMENT in
        development|staging|production)
            log_info "Rolling back $ENVIRONMENT environment"
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            log_info "Valid environments: development, staging, production"
            exit 1
            ;;
    esac
}

# Get deployment history
get_deployment_history() {
    log_info "Getting deployment history..."
    
    local cluster_var="ECS_CLUSTER_${ENVIRONMENT^^}"
    local service_var="ECS_SERVICE_${ENVIRONMENT^^}"
    
    local cluster="${!cluster_var}"
    local service="${!service_var}"
    
    # Get service deployments
    aws ecs describe-services \
        --cluster "$cluster" \
        --services "$service" \
        --query 'services[0].deployments[*].{Status:status,TaskDefinition:taskDefinition,CreatedAt:createdAt}' \
        --output table
}

# Rollback to previous version
rollback_to_previous() {
    log_info "Rolling back to previous version..."
    
    local cluster_var="ECS_CLUSTER_${ENVIRONMENT^^}"
    local service_var="ECS_SERVICE_${ENVIRONMENT^^}"
    
    local cluster="${!cluster_var}"
    local service="${!service_var}"
    
    # Get previous stable deployment
    local previous_task_def=$(aws ecs describe-services \
        --cluster "$cluster" \
        --services "$service" \
        --query 'services[0].deployments[?status==`ACTIVE`] | [1].taskDefinition' \
        --output text)
    
    if [[ "$previous_task_def" == "None" || -z "$previous_task_def" ]]; then
        log_error "No previous stable deployment found"
        exit 1
    fi
    
    log_info "Rolling back to: $previous_task_def"
    
    # Update service to previous version
    aws ecs update-service \
        --cluster "$cluster" \
        --service "$service" \
        --task-definition "$previous_task_def"
    
    log_success "Rollback initiated"
}

# Rollback to specific version
rollback_to_version() {
    local target_version="$1"
    
    log_info "Rolling back to specific version: $target_version"
    
    local cluster_var="ECS_CLUSTER_${ENVIRONMENT^^}"
    local service_var="ECS_SERVICE_${ENVIRONMENT^^}"
    
    local cluster="${!cluster_var}"
    local service="${!service_var}"
    
    # Update service to target version
    aws ecs update-service \
        --cluster "$cluster" \
        --service "$service" \
        --task-definition "$target_version"
    
    log_success "Rollback to $target_version initiated"
}

# Wait for rollback to complete
wait_for_rollback() {
    log_info "Waiting for rollback to complete..."
    
    local cluster_var="ECS_CLUSTER_${ENVIRONMENT^^}"
    local service_var="ECS_SERVICE_${ENVIRONMENT^^}"
    
    local cluster="${!cluster_var}"
    local service="${!service_var}"
    
    aws ecs wait services-stable \
        --cluster "$cluster" \
        --services "$service"
    
    log_success "Rollback completed successfully"
}

# Health check after rollback
health_check() {
    log_info "Performing health check after rollback..."
    
    local api_url_var="${ENVIRONMENT^^}_API_URL"
    local api_url="${!api_url_var}"
    
    # Wait a bit for the service to start
    sleep 30
    
    # Perform health check
    local max_attempts=5
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f "$api_url/health" &> /dev/null; then
            log_success "Health check passed after rollback"
            return 0
        fi
        
        log_warning "Health check attempt $attempt/$max_attempts failed"
        sleep 30
        ((attempt++))
    done
    
    log_error "Health check failed after rollback"
    exit 1
}

# Database rollback (if needed)
rollback_database() {
    log_warning "Database rollback is not automated for safety reasons"
    log_info "Please manually review and rollback database changes if necessary"
    log_info "Available database snapshots:"
    
    # List recent snapshots
    aws rds describe-db-snapshots \
        --db-instance-identifier "${RDS_INSTANCE_${ENVIRONMENT^^}}" \
        --snapshot-type manual \
        --max-items 10 \
        --query 'DBSnapshots[*].{Identifier:DBSnapshotIdentifier,Created:SnapshotCreateTime}' \
        --output table
}

# Confirm rollback
confirm_rollback() {
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log_warning "You are about to rollback PRODUCTION environment!"
        read -p "Are you sure you want to continue? (yes/no): " -r
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            log_info "Rollback cancelled"
            exit 0
        fi
    fi
}

# Main rollback function
main() {
    log_info "Starting rollback of ServantAssist API"
    log_info "Environment: $ENVIRONMENT"
    
    validate_environment
    confirm_rollback
    get_deployment_history
    
    if [[ -n "$TARGET_VERSION" ]]; then
        rollback_to_version "$TARGET_VERSION"
    else
        rollback_to_previous
    fi
    
    wait_for_rollback
    health_check
    rollback_database
    
    log_success "Rollback completed successfully!"
    log_info "Please verify the application is working correctly"
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi