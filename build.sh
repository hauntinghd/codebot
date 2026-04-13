#!/bin/bash
set -e

echo "🚀 CodeBot Build & Setup Script"
echo "================================"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18 or later."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or later."
    exit 1
fi

echo "✓ Node.js version: $(node --version)"
echo "✓ Python version: $(python3 --version)"

# Install backend dependencies
echo ""
echo "📦 Installing backend dependencies..."
pip install -r requirements.txt

# Install frontend dependencies
echo ""
echo "📦 Installing frontend dependencies..."
cd frontend
npm install

# Build frontend
echo ""
echo "🔨 Building frontend..."
npm run build

# Return to root
cd ..

echo ""
echo "✅ Build complete!"
echo ""
echo "📝 Next steps:"
echo "1. Set required environment variables in .env:"
echo "   - GOOGLE_CLIENT_ID"
echo "   - GOOGLE_CLIENT_SECRET"
echo "   - OPENAI_API_KEY"
echo "   - STRIPE_SECRET_KEY"
echo "   - STRIPE_WEBHOOK_SECRET"
echo "   - STRIPE_PRICE_BASIC"
echo "   - STRIPE_PRICE_PRO"
echo "   - STRIPE_PRICE_ELITE"
echo ""
echo "2. Start the backend:"
echo "   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "3. Visit http://localhost:8000/codebot/dashboard"
