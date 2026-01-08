#!/bin/bash
#
# Docker Build Script for Polari Framework
# Runs pre-build to generate .env, then builds Docker image
#
# Usage:
#   ./docker-build.sh [environment]
#
# Arguments:
#   environment: Optional environment name (development, production, testing)
#                Defaults to 'development'
#

set -e  # Exit on error

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Get environment from argument or default to 'development'
ENVIRONMENT="${1:-development}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Polari Framework Docker Build${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Run pre-build to generate .env
echo -e "${BLUE}Step 1: Running pre-build...${NC}"
./pre-build.sh "$ENVIRONMENT"

if [ $? -ne 0 ]; then
    echo "Pre-build failed. Aborting."
    exit 1
fi

# Step 2: Build Docker image
echo -e "${BLUE}Step 2: Building Docker image...${NC}"
echo ""

docker-compose build

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Docker build completed successfully${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}To start the application:${NC}"
    echo "  docker-compose up"
    echo ""
    echo -e "${BLUE}To start in background:${NC}"
    echo "  docker-compose up -d"
    echo ""
    exit 0
else
    echo ""
    echo "✗ Docker build failed"
    exit 1
fi
