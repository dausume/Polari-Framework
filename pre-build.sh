#!/bin/bash
#
# Pre-build script for Polari Framework
# Generates .env file from config.yaml before Docker build
#
# Usage:
#   ./pre-build.sh [environment]
#
# Arguments:
#   environment: Optional environment name (development, production, testing)
#                Defaults to 'development'
#

set -e  # Exit on error

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Get environment from argument or default to 'development'
ENVIRONMENT="${1:-development}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Polari Framework Pre-Build${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3 to continue"
    exit 1
fi

# Check if config.yaml exists
if [ ! -f "config.yaml" ]; then
    echo -e "${RED}Error: config.yaml not found${NC}"
    echo "Please create config.yaml before running this script"
    exit 1
fi

# Check if PyYAML is installed
if ! python3 -c "import yaml" 2>/dev/null; then
    echo -e "${YELLOW}Warning: PyYAML is not installed${NC}"
    echo "Installing PyYAML..."
    pip3 install PyYAML || {
        echo -e "${RED}Error: Failed to install PyYAML${NC}"
        echo "Please install it manually: pip3 install PyYAML"
        exit 1
    }
fi

# Generate .env file
echo -e "${GREEN}Generating .env file for environment: ${ENVIRONMENT}${NC}"
echo ""

python3 generate_env.py "$ENVIRONMENT"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Pre-build completed successfully${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  Build: docker-compose build"
    echo "  Run:   docker-compose up"
    echo ""
    exit 0
else
    echo ""
    echo -e "${RED}✗ Pre-build failed${NC}"
    exit 1
fi
