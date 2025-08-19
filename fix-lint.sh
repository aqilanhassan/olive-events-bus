#!/bin/bash

# Script to fix linting issues automatically
set -e

echo "🔧 Fixing linting issues with ruff..."

# Run ruff with unsafe fixes enabled to fix many issues automatically
cd /home/hassan/olive/olive-events-bus
poetry run ruff check --fix --unsafe-fixes .

echo "✨ Fixed as many issues as possible automatically"
echo "📋 Checking remaining issues..."

# Show remaining issues
poetry run ruff check .

echo "🎯 Manual fixes may be needed for remaining issues"
