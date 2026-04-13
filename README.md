# CodeBot - AI-Powered Code Generation MVP

CodeBot is a production-ready AI code generation platform with multi-layer AI architecture, BYOK support, and modern UI.

## ✨ Features

### 🤖 Multi-Layer AI System
- **Router (Layer 1)**: Uses system OpenAI key (gpt-4o-mini) - minimal cost
- **Engineer (Layer 2)**: Uses user's BYOK key (gpt-4o) - user pays directly
- **Auditor (Layer 3)**: Code quality verification and review

### 🛡️ Security & Privacy
- Bring Your Own Key (BYOK) support - users control their API keys
- Encrypted key storage with PBKDF2
- OAuth 2.0 Google authentication
- Secure session management with JWT

### 💳 Subscription & Credits
- Stripe integration for billing
- Free tier: Limited credits
- Basic ($50/m): 45 credits
- Pro ($250/m): 225 credits
- Credit deduction based on actual OpenAI usage

### 🎨 Planet UI System
- **Earth**: Free plan (green/blue theme)
- **Mars**: Basic plan ($50/m - red/orange theme)
- **Titan**: Pro plan ($250/m - purple/blue theme)

### 📁 File Upload Support
- ZIP files for project context
- Code files (.py, .js, .ts, .java, etc.)
- Images (PNG, WebP)
- Videos (MP4)
- Audio (MP3)

### ⚡ Performance
- Smart model selection (mini for simple tasks, best for complex)
- Token limit management
- File context optimization
- Rate limiting per user

## 🏗️ Architecture

```
CodeBot/
├── backend/                  # Python/FastAPI backend
│   ├── main.py             # FastAPI entry point
│   ├── config.py           # Configuration & environment variables
│   ├── database.py         # SQLite setup & schema
│   ├── auth.py             # Authentication logic
│   ├── byok.py             # BYOK encryption/decryption
│   ├── credits.py          # Credit system
│   ├── models.py           # Pydantic models
│   ├── helpers.py          # Utility functions
│   ├── routes/             # API endpoints
│   │   ├── auth.py         # OAuth & login
│   │   ├── chat.py         # Chat messages
│   │   ├── uploads.py      # File uploads
│   │   ├── billing.py      # Stripe integration
│   │   ├── admin.py        # Admin endpoints
│   │   ├── credits.py      # Credit management
│   │   ├── byok_routes.py  # BYOK API keys
│   │   ├── projects.py     # Project management
│   │   ├── features.py     # Advanced features
│   │   └── chat.py         # Chat endpoints
│   └── services/           # Business logic
│       ├── ai/             # AI orchestration
│       │   ├── multi_layer.py    # Router → Engineer → Auditor
│       │   ├── router.py         # Planning layer
│       │   ├── engineer.py       # Code generation
│       │   └── auditor.py        # Code review
│       ├── chat_helpers.py
│       ├── system_prompt.py
│       └── usage.py        # Token tracking
├── frontend/               # React/TypeScript + Vite
│   ├── src/
│   │   ├── App.tsx         # Main app component
│   │   ├── main.tsx        # Entry point
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   └── ChatPage.tsx
│   │   ├── components/
│   │   │   ├── UserPanel.tsx
│   │   │   ├── PlanetUI.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   └── chat/
│   │   │       ├── ChatHeader.tsx
│   │   │       ├── MessageList.tsx
│   │   │       └── MessageInput.tsx
│   │   ├── context/
│   │   │   └── AuthContext.tsx
│   │   ├── styles/
│   │   │   └── globals.css
│   │   ├── types/          # TypeScript types
│   │   └── services/       # API clients
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── package.json
├── data/                   # Data directory
│   ├── codebot.db         # SQLite database
│   ├── uploads/           # User file uploads
│   └── projects/          # Uploaded projects
├── static/                 # Static assets
│   └── app/               # Built frontend
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose setup
├── start.sh              # Production startup script
└── README.md             # This file
```

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Node.js 18+
- SQLite3
- Environment variables set

### Installation

1. **Clone and setup**
```bash
git clone <repo>
cd aicoderbot
bash setup.sh
```

2. **Install dependencies**
```bash
# Backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your credentials:
# - GOOGLE_CLIENT_ID/SECRET
# - OPENAI_API_KEY
# - STRIPE_SECRET_KEY, etc.
```

4. **Run development servers**

Terminal 1 (Backend):
```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

5. **Access the app**
- Frontend dev: http://localhost:5173
- Backend: http://localhost:8000
- Dashboard: http://localhost:8000/codebot/dashboard

## 🐳 Docker Deployment

### Build
```bash
docker-compose build
```

### Run
```bash
docker-compose up
```

Access at http://localhost:8000/codebot/dashboard

### Environment variables
Create `.env` with all required variables (see setup.sh)

## 📚 API Endpoints

### Authentication
- `POST /codebot/api/auth/register` - Register new user
- `POST /codebot/api/auth/login` - Email/password login
- `POST /codebot/api/auth/refresh` - Refresh access token
- `GET /codebot/api/auth/google/login` - Google OAuth login
- `GET /codebot/api/auth/google/callback` - OAuth callback
- `POST /codebot/api/auth/logout` - Logout

### User
- `GET /codebot/api/me` - Current user info
- `GET /codebot/api/credits` - User credits & transactions

### Chat
- `GET /codebot/api/chats` - List chats
- `POST /codebot/api/chats` - Create chat
- `GET /codebot/api/chats/{chat_id}/messages` - Get messages
- `POST /codebot/api/chats/{chat_id}/message` - Send message
- `DELETE /codebot/api/chats/{chat_id}` - Delete chat

### Uploads
- `POST /codebot/api/uploads/zip` - Upload ZIP
- `POST /codebot/api/uploads/mp4` - Upload MP4
- `POST /codebot/api/uploads/mp3` - Upload MP3
- `POST /codebot/api/uploads/image` - Upload image
- `POST /codebot/api/uploads/code` - Upload code file
- `GET /codebot/api/uploads` - List uploads
- `DELETE /codebot/api/uploads/{file_id}` - Delete upload

### Billing
- `POST /codebot/api/billing/create-checkout-session` - Stripe checkout
- `GET /codebot/api/billing/portal` - Billing portal
- `POST /codebot/api/billing/webhook` - Stripe webhook

### BYOK (Bring Your Own Key)
- `POST /codebot/api/api-key` - Set API key
- `GET /codebot/api/api-key` - Get key status
- `DELETE /codebot/api/api-key` - Delete key

### Admin
- `GET /codebot/api/admin/credits/{user_id}` - View user credits
- `POST /codebot/api/admin/credits/{user_id}/add` - Add credits
- `GET /codebot/api/admin/costs` - View system costs

## 🔒 Security

### Authentication
- JWT tokens with 15-minute expiry (configurable)
- Refresh tokens with 30-day expiry
- Session-based auth for web UI

### Encryption
- PBKDF2 password hashing (210,000 iterations)
- Fernet encryption for BYOK keys
- All sensitive data in database encrypted

### API Security
- Rate limiting per user (60 req/min)
- Global rate limiting (1000 req/min)
- CORS configured for allowed origins
- CSRF protection with session tokens

### Authorization
- Admin-only routes protected
- Subscription checks on paid features
- Ownership validation for user resources
- Credit-based access control

## 💰 Pricing & Credits

### Plan Credits
- **Free**: 0 credits (for testing only)
- **Basic**: $45 credits/month (90% of $50)
- **Pro**: $225 credits/month (90% of $250)

### Cost Calculation
- Based on OpenAI token usage
- gpt-4o-mini: $0.00015 input, $0.0006 output (per 1k tokens)
- gpt-4o: $0.0025 input, $0.01 output (per 1k tokens)
- Costs deducted in real-time
- Monthly reset on billing cycle

### BYOK Costs
- When user provides their own OpenAI key:
  - Router layer uses system key (cheap)
  - Engineer & Auditor layers use user's key
  - User pays for their own API usage directly
  - System covers only Router costs

## 🧪 Testing

### Test Mode
Enable with `DEV_MODE=true` or `.dev_mode` file

Features in dev mode:
- Bypass subscription requirements
- Bypass payment verification
- Test file uploads

### Test Users
- `omatic657@gmail.com` - Special test user (with X-Test-Mode header)
- Can use test features without subscription

## 📊 Monitoring

### Logs
- All requests logged to stdout
- Error tracking with traceback
- Debug logs in `.cursor/debug.log`

### Health Check
- `GET /codebot/api/health` - System health status

### Database
- SQLite at `./data/codebot.db`
- Automatic schema migration
- WAL (Write-Ahead Logging) enabled

## 🚀 Deployment

### Production Checklist
- [ ] Generate strong JWT_SECRET
- [ ] Set HTTPS URLs
- [ ] Configure ALLOWED_ORIGINS
- [ ] Set Stripe production keys
- [ ] Configure Google OAuth with production credentials
- [ ] Use PostgreSQL instead of SQLite for scale
- [ ] Enable HTTPS only cookies
- [ ] Set DEV_MODE=false
- [ ] Configure production email
- [ ] Setup monitoring & alerting
- [ ] Backup database regularly
- [ ] Rate limit configuration review

### Scaling Considerations
1. **Database**: Use PostgreSQL instead of SQLite
2. **Cache**: Add Redis for sessions and rate limiting
3. **Message Queue**: Use Celery for async tasks
4. **CDN**: Serve static assets via CDN
5. **Load Balancing**: Multiple backend instances
6. **API Keys**: Rotate regularly
7. **Monitoring**: Setup alerting & metrics

## 📝 Environment Variables

```bash
# App
APP_BASE_PATH=/codebot
APP_BASE_URL=https://chatbot.nyptidindustries.com
DEV_MODE=false

# Google OAuth
GOOGLE_CLIENT_ID=your_id
GOOGLE_CLIENT_SECRET=your_secret

# OpenAI
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_MODEL_BEST=gpt-4o

# Stripe
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_BASIC=price_xxx
STRIPE_PRICE_PRO=price_xxx
STRIPE_PRICE_ELITE=price_xxx

# Security
JWT_SECRET=your_secret_key
ACCESS_TOKEN_TTL_SECONDS=900
REFRESH_TOKEN_TTL_SECONDS=2592000

# Paths
DATA_DIR=./data
DB_PATH=./data/codebot.db
PROJECTS_DIR=./data/projects
UPLOADS_DIR=./data/uploads
STATIC_DIR=./static
```

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Run tests
4. Submit PR

## 📄 License

NYPTID Industries - All rights reserved

## 🆘 Support

For issues or questions:
1. Check existing GitHub issues
2. Review documentation
3. Contact support@nyptidindustries.com

---

**Built with ❤️ for developers**
