#!/bin/bash

# ServantAssist Deployment Script
# Usage: ./scripts/deploy.sh [environment] [version]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}

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
            log_info "Deploying to $ENVIRONMENT environment"
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            log_info "Valid environments: development, staging, production"
            exit 1
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if AWS CLI is installed and configured
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running"
        exit 1
    fi
    
    # Check if required environment variables are set
    required_vars=(
        "AWS_REGION"
        "ECS_CLUSTER_${ENVIRONMENT^^}"
        "ECS_SERVICE_${ENVIRONMENT^^}"
        "CONTAINER_REGISTRY"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_error "Environment variable $var is not set"
            exit 1
        fi
    done
    
    log_success "Prerequisites check passed"
}

# Build and push Docker image
build_and_push() {
    log_info "Building and pushing Docker image..."
    
    local image_name="$CONTAINER_REGISTRY/servantassist/api:$VERSION"
    
    # Build image
    docker build -t "$image_name" --target production .
    
    # Push image
    docker push "$image_name"
    
    log_success "Image built and pushed: $image_name"
}

# Update ECS task definition
update_task_definition() {
    log_info "Updating ECS task definition..."
    
    local cluster_var="ECS_CLUSTER_${ENVIRONMENT^^}"
    local service_var="ECS_SERVICE_${ENVIRONMENT^^}"
    local task_def_var="ECS_TASK_DEFINITION_${ENVIRONMENT^^}"
    
    local cluster="${!cluster_var}"
    local service="${!service_var}"
    local task_definition="${!task_def_var}"
    
    # Update service
    aws ecs update-service \
        --cluster "$cluster" \
        --service "$service" \
        --task-definition "$task_definition" \
        --force-new-deployment
    
    log_success "ECS service updated"
}

# Wait for deployment to complete
wait_for_deployment() {
    log_info "Waiting for deployment to complete..."
    
    local cluster_var="ECS_CLUSTER_${ENVIRONMENT^^}"
    local service_var="ECS_SERVICE_${ENVIRONMENT^^}"
    
    local cluster="${!cluster_var}"
    local service="${!service_var}"
    
    aws ecs wait services-stable \
        --cluster "$cluster" \
        --services "$service"
    
    log_success "Deployment completed successfully"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    local cluster_var="ECS_CLUSTER_${ENVIRONMENT^^}"
    local migration_task_var="ECS_MIGRATION_TASK_${ENVIRONMENT^^}"
    local subnet_var="SUBNET_IDS_${ENVIRONMENT^^}"
    local sg_var="SECURITY_GROUP_${ENVIRONMENT^^}"
    
    local cluster="${!cluster_var}"
    local migration_task="${!migration_task_var}"
    local subnets="${!subnet_var}"
    local security_group="${!sg_var}"
    
    # Run migration task
    local task_arn=$(aws ecs run-task \
        --cluster "$cluster" \
        --task-definition "$migration_task" \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$subnets],securityGroups=[$security_group],assignPublicIp=ENABLED}" \
        --query 'tasks[0].taskArn' \
        --output text)
    
    # Wait for migration to complete
    aws ecs wait tasks-stopped \
        --cluster "$cluster" \
        --tasks "$task_arn"
    
    # Check if migration was successful
    local exit_code=$(aws ecs describe-tasks \
        --cluster "$cluster" \
        --tasks "$task_arn" \
        --query 'tasks[0].containers[0].exitCode' \
        --output text)
    
    if [[ "$exit_code" != "0" ]]; then
        log_error "Database migration failed with exit code: $exit_code"
        exit 1
    fi
    
    log_success "Database migrations completed successfully"
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    local api_url_var="${ENVIRONMENT^^}_API_URL"
    local api_url="${!api_url_var}"
    
    # Wait a bit for the service to start
    sleep 30
    
    # Perform health check
    local max_attempts=5
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f "$api_url/health" &> /dev/null; then
            log_success "Health check passed"
            return 0
        fi
        
        log_warning "Health check attempt $attempt/$max_attempts failed"
        sleep 30
        ((attempt++))
    done
    
    log_error "Health check failed after $max_attempts attempts"
    exit 1
}

# Rollback function
rollback() {
    log_warning "Rolling back deployment..."
    
    local cluster_var="ECS_CLUSTER_${ENVIRONMENT^^}"
    local service_var="ECS_SERVICE_${ENVIRONMENT^^}"
    
    local cluster="${!cluster_var}"
    local service="${!service_var}"
    
    # Get previous task definition
    local previous_task_def=$(aws ecs describe-services \
        --cluster "$cluster" \
        --services "$service" \
        --query 'services[0].deployments[1].taskDefinition' \
        --output text)
    
    if [[ "$previous_task_def" != "None" ]]; then
        # Rollback to previous version
        aws ecs update-service \
            --cluster "$cluster" \
            --service "$service" \
            --task-definition "$previous_task_def"
        
        log_success "Rollback initiated to: $previous_task_def"
    else
        log_error "No previous task definition found for rollback"
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    # Add any cleanup tasks here
}

# Main deployment function
main() {
    log_info "Starting deployment of ServantAssist API"
    log_info "Environment: $ENVIRONMENT"
    log_info "Version: $VERSION"
    
    # Set trap for cleanup on exit
    trap cleanup EXIT
    
    # Set trap for rollback on error
    trap rollback ERR
    
    validate_environment
    check_prerequisites
    
    if [[ "$ENVIRONMENT" != "development" ]]; then
        build_and_push
    fi
    
    update_task_definition
    wait_for_deployment
    run_migrations
    health_check
    
    log_success "Deployment completed successfully!"
    log_info "API is now running at: ${!api_url_var:-http://localhost:8000}"
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi