#!/bin/bash
set -e

echo "🐳 CodeBot Docker Build"
echo "======================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker."
    exit 1
fi

echo "✓ Docker is installed"

# Build the Docker image
echo ""
echo "🔨 Building Docker image..."
docker build -t codebot:latest .

echo ""
echo "✅ Docker image built successfully!"
echo ""
echo "📝 To run the container:"
echo ""
echo "docker run -p 8000:8000 \\"
echo "  -e GOOGLE_CLIENT_ID=your_id \\"
echo "  -e GOOGLE_CLIENT_SECRET=your_secret \\"
echo "  -e OPENAI_API_KEY=your_key \\"
echo "  codebot:latest"
echo ""
echo "Then visit http://localhost:8000/codebot/dashboard"
