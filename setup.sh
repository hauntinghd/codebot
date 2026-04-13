#!/bin/bash

# CodeBot Development Environment Setup
# ======================================

echo "🚀 CodeBot Development Setup"
echo "============================"

# Check for .env file
if [ ! -f .env ]; then
    echo "📝 Creating .env file with template values..."
    cat > .env.example << 'EOF'
# App Configuration
APP_BASE_PATH=/codebot
APP_BASE_URL=https://chatbot.nyptidindustries.com
DEV_MODE=false

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# Stripe Configuration
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
STRIPE_PRICE_BASIC=price_xxxxx
STRIPE_PRICE_PRO=price_xxxxx
STRIPE_PRICE_ELITE=price_xxxxx

# Database
DATABASE_URL=sqlite:///./data/codebot.db

# Security
JWT_SECRET=your_secret_key_change_in_production

# File Storage
DATA_DIR=./data
UPLOADS_DIR=./data/uploads
PROJECTS_DIR=./data/projects
EOF
    echo "✓ Created .env.example - Copy and customize it to .env"
else
    echo "✓ .env file already exists"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📚 Development Guide:"
echo ""
echo "1. Backend:"
echo "   pip install -r requirements.txt"
echo "   python -m uvicorn backend.main:app --reload"
echo ""
echo "2. Frontend (in another terminal):"
echo "   cd frontend"
echo "   npm install"
echo "   npm run dev"
echo ""
echo "3. Frontend will proxy API calls to http://localhost:8000"
echo ""
echo "4. Access the app:"
echo "   http://localhost:5173 (frontend dev server)"
echo "   http://localhost:8000/codebot/dashboard (from backend)"
echo ""
