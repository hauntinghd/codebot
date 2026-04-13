#!/bin/bash
set -e
cd /home/omatic657/aicoderbot

# Export all required environment variables
# These will be inherited from systemd Environment directives, but we also set them here as backup
export DEV_MODE=true
export HF_TOKEN="${HF_TOKEN:-}" # Set your HuggingFace token via HF_TOKEN or HUGGINGFACEHUB_API_TOKEN
# Google OAuth removed - do not export or require credentials
export STRIPE_PRICE_BASIC="${STRIPE_PRICE_BASIC:-price_1Sk4SVBL8lRmwao2TwWN730u}"
export STRIPE_PRICE_PRO="${STRIPE_PRICE_PRO:-price_1Sk4SgBL8lRmwao2B9gcRbTg}"
export STRIPE_WEBHOOK_SECRET="${STRIPE_WEBHOOK_SECRET:-whsec_NVmGjOaM3faKSRdzu4KZQXXTh4DOZooW}"
export PATH=/home/omatic657/aicoderbot/.venv/bin:$PATH

# Verify critical variables are set before exec
if [ -z "$HF_TOKEN" ] && [ -z "$HUGGINGFACEHUB_API_TOKEN" ]; then
    echo "WARNING: No HuggingFace token configured (HF_TOKEN/HUGGINGFACEHUB_API_TOKEN). Some features may be disabled." >&2
fi
# Google OAuth disabled; no credential check

# Explicitly pass all environment variables through exec
exec env \
  DEV_MODE="$DEV_MODE" \
    HF_TOKEN="$HF_TOKEN" \
  # GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET removed intentionally \
  STRIPE_PRICE_BASIC="$STRIPE_PRICE_BASIC" \
  STRIPE_PRICE_PRO="$STRIPE_PRICE_PRO" \
  STRIPE_WEBHOOK_SECRET="$STRIPE_WEBHOOK_SECRET" \
  PATH="$PATH" \
  /home/omatic657/aicoderbot/.venv/bin/python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 3000

