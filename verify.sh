#!/bin/bash

# CodeBot Verification Script
# ===========================
# Checks that all required files and configurations are in place

echo "🔍 CodeBot Project Verification"
echo "==============================="
echo ""

ERRORS=0
WARNINGS=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 exists"
    else
        echo -e "${RED}✗${NC} $1 MISSING"
        ERRORS=$((ERRORS + 1))
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/ exists"
    else
        echo -e "${RED}✗${NC} $1/ MISSING"
        ERRORS=$((ERRORS + 1))
    fi
}

check_optional() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 exists"
    else
        echo -e "${YELLOW}⚠${NC} $1 (optional)"
        WARNINGS=$((WARNINGS + 1))
    fi
}

echo "📁 Backend Structure"
echo "-------------------"
check_file "backend/main.py"
check_file "backend/config.py"
check_file "backend/auth.py"
check_file "backend/byok.py"
check_file "backend/credits.py"
check_file "backend/database.py"
check_file "backend/helpers.py"
check_file "backend/models.py"
check_dir "backend/routes"
check_file "backend/routes/auth.py"
check_file "backend/routes/chat.py"
check_file "backend/routes/uploads.py"
check_file "backend/routes/billing.py"
check_file "backend/routes/admin.py"
check_file "backend/routes/byok_routes.py"
check_file "backend/routes/projects.py"
check_dir "backend/services"
check_file "backend/services/ai/multi_layer.py"
check_file "backend/services/ai/router.py"
check_file "backend/services/ai/engineer.py"
check_file "backend/services/ai/auditor.py"

echo ""
echo "⚛️  Frontend Structure"
echo "---------------------"
check_dir "frontend"
check_file "frontend/package.json"
check_file "frontend/vite.config.ts"
check_file "frontend/tsconfig.json"
check_file "frontend/tailwind.config.js"
check_file "frontend/postcss.config.js"
check_file "frontend/index.html"
check_file "frontend/src/App.tsx"
check_file "frontend/src/main.tsx"
check_file "frontend/src/context/AuthContext.tsx"
check_file "frontend/src/pages/LoginPage.tsx"
check_file "frontend/src/pages/ChatPage.tsx"
check_file "frontend/src/components/UserPanel.tsx"
check_file "frontend/src/components/PlanetUI.tsx"
check_file "frontend/src/components/LoadingSpinner.tsx"
check_file "frontend/src/components/ProtectedRoute.tsx"
check_file "frontend/src/components/chat/ChatHeader.tsx"
check_file "frontend/src/components/chat/MessageList.tsx"
check_file "frontend/src/components/chat/MessageInput.tsx"

echo ""
echo "🐳 Docker & Deployment"
echo "---------------------"
check_file "Dockerfile"
check_file "docker-compose.yml"
check_file "start.sh"
check_file "build.sh"

echo ""
echo "📦 Configuration & Dependencies"
echo "--------------------------------"
check_file "requirements.txt"
check_file ".env.example"
check_optional ".env"
check_file ".gitignore"
check_file "README.md"

echo ""
echo "📊 Project Status"
echo "-----------------"
echo -e "Errors:   ${RED}$ERRORS${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"

if [ $ERRORS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All required files are in place!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Set environment variables in .env"
    echo "2. Run: bash build.sh"
    echo "3. Run backend: python -m uvicorn backend.main:app --reload"
    echo "4. Run frontend: cd frontend && npm run dev"
    echo "5. Visit http://localhost:5173"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Please create the missing files listed above${NC}"
    exit 1
fi
