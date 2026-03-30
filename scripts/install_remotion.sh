#!/bin/bash
# Installation script for Remotion dependencies

set -e

echo "🎬 Installing Remotion dependencies for auto-video..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    echo "   Visit: https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js found: $(node --version)"

# Navigate to Remotion directory
REMOTION_DIR="$(dirname "$0")/../src/auto_video/remotion"
cd "$REMOTION_DIR"

echo "📦 Installing npm packages..."
npm install

echo "✅ Remotion dependencies installed successfully!"
echo ""
echo "You can now use Remotion for complex motion graphics in auto-video."
