# 🧪 CodeBot Testing Guide

## Quick Test Commands

### 1. Check Service Status
```bash
# Backend status
sudo systemctl status aicodebot.service

# Nginx status
sudo systemctl status nginx

# Check logs
sudo journalctl -u aicodebot.service -f
```

### 2. Test Authentication Endpoints

#### Email Registration
```bash
curl -X POST https://chatbot.nyptidindustries.com/codebot/api/auth/email/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePass123!"
  }'
```

Expected response:
```json
{
  "user": {
    "id": "...",
    "email": "newuser@example.com",
    "oauth_provider": "email",
    "plan_type": "free",
    "credits_balance": 100
  },
  "access_token": "..."
}
```

#### Email Login
```bash
curl -X POST https://chatbot.nyptidindustries.com/codebot/api/auth/email/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePass123!"
  }'
```

### 3. Test BYOK (Bring Your Own Key)

#### Add OpenAI Key
```bash
curl -X POST https://chatbot.nyptidindustries.com/codebot/api/byok/key \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "sk-proj-...",
    "provider": "openai"
  }'
```

#### Add Anthropic Key
```bash
curl -X POST https://chatbot.nyptidindustries.com/codebot/api/byok/key \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "sk-ant-...",
    "provider": "anthropic"
  }'
```

#### Check BYOK Status
```bash
curl https://chatbot.nyptidindustries.com/codebot/api/byok/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Expected response:
```json
{
  "has_key": true,
  "provider": "openai",
  "rate_limit": 500,
  "remaining": 498
}
```

### 4. Test Rate Limiting

#### Check Rate Limit
```bash
curl https://chatbot.nyptidindustries.com/codebot/api/rate-limit \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Expected response (regular user):
```json
{
  "limit": 50,
  "remaining": 48,
  "reset_at": "2026-01-10T03:00:00Z"
}
```

Expected response (BYOK user):
```json
{
  "limit": 500,
  "remaining": 495,
  "reset_at": "2026-01-10T03:00:00Z"
}
```

### 5. Test SSE Streaming

#### Using curl (terminal)
```bash
curl -N https://chatbot.nyptidindustries.com/codebot/api/chats/YOUR_CHAT_ID/stream \
  -H "Cookie: access_token=YOUR_JWT_TOKEN"
```

Expected output:
```
data: {"type": "layer_start", "layer": "router", "timestamp": "..."}

data: {"type": "layer_complete", "layer": "router", "content": "Planning...", "timestamp": "..."}

data: {"type": "layer_start", "layer": "engineer", "timestamp": "..."}

data: {"type": "code_chunk", "content": "def ", "timestamp": "..."}

data: {"type": "code_chunk", "content": "hello", "timestamp": "..."}

data: {"type": "layer_complete", "layer": "engineer", "content": "def hello():\n    return 'Hello'", "timestamp": "..."}

data: {"type": "complete", "tokens_input": 150, "tokens_output": 200, "cost": 0.0, "model": "gpt-4o", "timestamp": "..."}
```

#### Using JavaScript (browser)
```javascript
const eventSource = new EventSource('/codebot/api/chats/YOUR_CHAT_ID/stream');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data);
  
  if (data.type === 'layer_start') {
    console.log(`Starting ${data.layer} layer...`);
  } else if (data.type === 'code_chunk') {
    console.log('Code:', data.content);
  } else if (data.type === 'complete') {
    console.log('Done! Tokens:', data.tokens_output, 'Cost:', data.cost);
    eventSource.close();
  }
};

eventSource.onerror = (error) => {
  console.error('SSE Error:', error);
  eventSource.close();
};
```

### 6. Test Code Analysis

```bash
curl -X POST https://chatbot.nyptidindustries.com/codebot/api/analyze/code \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def calculate(x, y):\n    if x > 0:\n        if y > 0:\n            if x > y:\n                return x * y\n            else:\n                return x + y\n    return 0",
    "language": "python",
    "filename": "example.py"
  }'
```

Expected response:
```json
{
  "metrics": {
    "cyclomatic_complexity": 5,
    "nesting_depth": 4,
    "lines_of_code": 8,
    "maintainability_index": 45.2
  },
  "security_issues": [],
  "code_smells": [
    {
      "type": "deep_nesting",
      "severity": "warning",
      "line": 3,
      "message": "Nesting depth of 4 exceeds recommended limit of 3"
    },
    {
      "type": "long_function",
      "severity": "info",
      "line": 1,
      "message": "Function has 8 lines, consider splitting if it grows"
    }
  ],
  "suggestions": [
    "Consider flattening nested conditions",
    "Add type hints for better maintainability"
  ]
}
```

### 7. Test Chat Endpoints

#### Create New Chat
```bash
curl -X POST https://chatbot.nyptidindustries.com/codebot/api/chats \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My New Chat"
  }'
```

#### Send Message
```bash
curl -X POST https://chatbot.nyptidindustries.com/codebot/api/chat \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "YOUR_CHAT_ID",
    "message": "Write a Python function to calculate fibonacci numbers"
  }'
```

#### Get Chat History
```bash
curl https://chatbot.nyptidindustries.com/codebot/api/chats/YOUR_CHAT_ID/messages \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 8. Frontend Testing (Browser)

#### Open Application
Visit: https://chatbot.nyptidindustries.com/codebot/

#### Test Flow
1. **Register**: Click "Sign Up" → Enter email/password → Submit
2. **Login**: Enter credentials → Click "Login"
3. **Dashboard**: Should see:
   - Credits: 100 (free tier)
   - Planet badge: Earth 🌍 (free plan)
   - User panel in top right
4. **Add BYOK Key**: 
   - Click user panel → "Settings"
   - Find "API Key" section
   - Select provider (OpenAI/Anthropic/Gemini)
   - Enter key → Save
   - Should see: "∞ (BYOK)" in user panel
   - Rate limit badge: "500 req/hour (10x boost)"
5. **Create Chat**:
   - Click "New Chat"
   - Enter message: "Write a hello world in Python"
   - Watch streaming:
     - See "[ROUTER thinking...]"
     - Then "[ENGINEER thinking...]"
     - Then code appears chunk by chunk
     - Finally shows token count and cost ($0.00 for BYOK)
6. **Test Rate Limit**:
   - Send 50 messages (regular) or 500 (BYOK)
   - On limit hit, should see error: "Rate limited. Please wait..."
7. **Upgrade Plan**:
   - Click user panel → "Subscription & Plans"
   - Choose Plus ($50) or Pro ($250)
   - Complete Stripe payment
   - Planet badge should update: Mars 🔴 (Plus) or Titan 🪐 (Pro)

### 9. Database Queries (Direct)

```bash
# Connect to database
sqlite3 /home/omatic657/aicoderbot/data/codebot.db

# Check users
SELECT id, email, oauth_provider, plan_type, credits_balance, api_key_encrypted IS NOT NULL as has_byok 
FROM users;

# Check rate limits
SELECT user_id, request_count, reset_at 
FROM rate_limits 
WHERE window_start > datetime('now', '-1 hour');

# Check analysis results
SELECT file_hash, maintainability_index, issues_count 
FROM analysis_results 
ORDER BY created_at DESC 
LIMIT 5;
```

### 10. Load Testing

#### Install Apache Bench (ab)
```bash
sudo apt install apache2-utils -y
```

#### Test rate limiting
```bash
# Send 100 requests with 10 concurrent
ab -n 100 -c 10 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -p /dev/null \
  https://chatbot.nyptidindustries.com/codebot/api/chats

# Expected: First 50 succeed, rest get 429 (rate limited)
```

## Expected Behaviors

### ✅ Success Cases
- Email registration creates user with 100 free credits
- Login returns JWT token valid for 7 days
- BYOK key increases rate limit from 50 to 500
- SSE streaming shows layer-by-layer progress
- Code analysis detects security issues and code smells
- Rate limiting resets after 1 hour

### ⚠️ Error Cases
- 429 Too Many Requests: Rate limit exceeded (regular: 50/hour, BYOK: 500/hour)
- 402 Payment Required: Out of credits (need to upgrade or add BYOK)
- 401 Unauthorized: Invalid/expired JWT token
- 400 Bad Request: Invalid API key format
- 500 Internal Server Error: Backend exception (check logs)

### 🔍 Debugging Tips
1. **Check logs**: `sudo journalctl -u aicodebot.service -f`
2. **Verify JWT**: Decode at jwt.io to check expiration
3. **Test API docs**: Visit http://localhost:8000/docs for interactive testing
4. **Check database**: `sqlite3 /home/omatic657/aicoderbot/data/codebot.db`
5. **Nginx logs**: `sudo tail -f /var/log/nginx/error.log`

## Performance Benchmarks

### Target Metrics
- **API latency**: < 200ms (non-AI endpoints)
- **SSE first byte**: < 1 second
- **Code analysis**: < 3 seconds (1000 LOC)
- **Chat response**: < 5 seconds (first token)
- **Rate limit check**: < 50ms

### Monitoring Commands
```bash
# Check response times
curl -w "@-" -o /dev/null -s https://chatbot.nyptidindustries.com/codebot/api/chats <<'EOF'
   time_namelookup:  %{time_namelookup}s\n
      time_connect:  %{time_connect}s\n
   time_appconnect:  %{time_appconnect}s\n
  time_pretransfer:  %{time_pretransfer}s\n
     time_redirect:  %{time_redirect}s\n
time_starttransfer:  %{time_starttransfer}s\n
    time_total:  %{time_total}s\n
EOF

# Check system resources
htop
```

---

**Happy Testing! 🚀**

For issues or questions, check [DEPLOYMENT_COMPLETE.md](./DEPLOYMENT_COMPLETE.md) or backend logs.
