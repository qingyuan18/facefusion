#!/bin/bash

# Clean test runner for FaceFusion API service tests
# This script ensures a clean Python environment to avoid module conflicts

echo "🧪 FaceFusion API Service Tests (Clean Environment)"
echo "=================================================="

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo "🔧 Environment setup:"
echo "   Project root: $PROJECT_ROOT"

# Set clean PYTHONPATH - only include current project
export PYTHONPATH="$PROJECT_ROOT"

# Unset any conflicting environment variables
unset CUDA_VISIBLE_DEVICES

echo "   PYTHONPATH: $PYTHONPATH"
echo "=================================================="

# Change to project directory
cd "$PROJECT_ROOT"

# Run tests
echo "🚀 Running tests..."
python3 -m unittest tests.test_api_services -v

# Check result
if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "✅ All tests passed!"
else
    echo ""
    echo "=================================================="
    echo "❌ Tests failed!"
    exit 1
fi
