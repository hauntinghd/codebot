#!/bin/bash
# CodeBot Google Cloud VM Deployment Script

set -e

# Configuration - UPDATE THESE
GCP_VM_USER="omatic657"
GCP_VM_IP="34.10.77.2"
GCP_VM_HOSTNAME="chatbot.nyptidindustries.com"
REMOTE_PATH="/home/omatic657/aicoderbot"

# Use IP address directly (more reliable than hostname)
GCP_TARGET="34.10.77.2"

echo "🚀 CodeBot Deployment to Google Cloud VM"
echo "=========================================="
echo "Target: $GCP_TARGET"
echo "User: $GCP_VM_USER"
echo "Remote Path: $REMOTE_PATH"
echo ""

# Step 1: Create deployment archive
echo "📦 Creating deployment package..."
cd /home/omatic657/aicoderbot
tar czf /tmp/codebot-deploy.tar.gz \
  --exclude=.git \
  --exclude=node_modules \
  --exclude=__pycache__ \
  --exclude=.pytest_cache \
  --exclude=.env \
  --exclude=database.db* \
  backend/ \
  frontend/dist \
  static/ \
  start.sh \
  requirements.txt \
  .env.example \
  server.py 2>/dev/null || true

echo "✅ Package created: /tmp/codebot-deploy.tar.gz"
echo ""

# Step 2: Deploy to GCP
echo "📤 Uploading to Google Cloud VM..."
scp -r /tmp/codebot-deploy.tar.gz ${GCP_VM_USER}@${GCP_TARGET}:/tmp/codebot-deploy.tar.gz

echo "📂 Extracting on remote server..."
ssh ${GCP_VM_USER}@${GCP_TARGET} << 'EOF'
  set -e
  echo "Stopping services..."
  sudo systemctl stop aicodebot.service 2>/dev/null || true
  
  echo "Extracting files..."
  cd /tmp
  tar xzf codebot-deploy.tar.gz -C ${REMOTE_PATH}
  
  echo "Installing Python dependencies..."
  pip3 install -r ${REMOTE_PATH}/requirements.txt -q 2>&1 | grep -v "already satisfied" || true
  
  echo "✅ Files extracted and dependencies installed"
EOF

echo ""
echo "✅ Deployment to Google Cloud VM complete!"
echo ""
echo "⚙️  Next steps on your VM:"
echo "  1. SSH to VM: ssh ${GCP_VM_USER}@${GCP_TARGET}"
echo "  2. Update .env: nano ${REMOTE_PATH}/.env"
echo "  3. Restart service: sudo systemctl start aicodebot.service"
echo "  4. Check status: sudo systemctl status aicodebot.service"
echo ""
echo "🌐 Access at: https://chatbot.nyptidindustries.com/codebot/dashboard"
