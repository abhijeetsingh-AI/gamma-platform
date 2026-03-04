# Gamma Platform

AI Voice Calling Platform — Twilio → Deepgram → Gemini → TTS → Caller

## Quick Start

### 1. Copy env and fill values
```bash
cp .env.example .env
# Edit .env — fill in DEEPGRAM_API_KEY, GEMINI_API_KEY, TWILIO_* values
# Generate SECRET_KEY:
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Install and run locally
```bash
pip install -r requirements.txt

# Terminal 1 — Redis
docker run -d -p 6379:6379 redis:7-alpine

# Terminal 2 — Celery
celery -A app.celery_app worker --loglevel=info

# Terminal 3 — API
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Test it
```
http://localhost:8000/docs          → Swagger UI
http://localhost:8000/api/monitor/health  → Health check
http://localhost:8000/api/monitor/status  → All subsystems
```

### 4. Push to GitHub
```bash
git init
git add .
git commit -m "feat: Gamma voice platform initial commit"
gh repo create gamma-platform --private --source=. --push
# or:
git remote add origin https://github.com/YOUR_USERNAME/gamma-platform.git
git branch -M main
git push -u origin main
```

### 5. Deploy on Render
```
1. render.com → New → Web Service → Connect GitHub repo
2. Render detects render.yaml → creates gamma-api + gamma-celery + gamma-redis
3. Set env vars in gamma-api dashboard:
   GEMINI_API_KEY, DEEPGRAM_API_KEY
   TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
   BASE_URL = gamma-api.onrender.com
   TWILIO_WEBHOOK_URL = https://gamma-api.onrender.com/api/voice/incoming
4. Deploy
```

### 6. Point Twilio to Render
```
Twilio Console → Phone Numbers → your number → Voice webhook:
  https://gamma-api.onrender.com/api/voice/incoming   (HTTP POST)
  Status callback:
  https://gamma-api.onrender.com/api/voice/status     (HTTP POST)
```

### 7. Verify
```bash
curl https://gamma-api.onrender.com/api/monitor/status
```

## TTS Modes

| Mode | Config | Quality | Requirement |
|------|--------|---------|-------------|
| `twilio` (default) | `TTS_PROVIDER=twilio` | Good (Polly voices) | None — works now |
| `google` | `TTS_PROVIDER=google` | Excellent (Neural2) | GCP service account JSON |

To upgrade to Google Neural2:
1. Get GCP service account JSON (Cloud Console → IAM → Service Accounts)
2. Enable Cloud Text-to-Speech API
3. Upload JSON as Secret File on Render at `/etc/secrets/gcp-service-account.json`
4. Set `GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/gcp-service-account.json`
5. Set `TTS_PROVIDER=google`

## Voice Flow

```
Caller dials Twilio number
    → POST /api/voice/incoming
    → TwiML: <Connect><Stream url="wss://..."/></Connect>
    → WebSocket /api/voice/stream/{callSid}
    → Deepgram STT transcribes audio
    → Gemini generates JSON response
    → TTS speaks text back to caller
    → Loop until end_call / hangup
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/voice/incoming | Twilio webhook (incoming call) |
| WS | /api/voice/stream/{sid} | Audio stream |
| POST | /api/voice/gather/{sid} | Speech gather callback |
| POST | /api/voice/call | Trigger outbound call |
| POST | /api/voice/status | Twilio status callback |
| GET | /api/agents/ | List agents |
| POST | /api/agents/ | Create agent |
| GET | /api/campaigns/ | List campaigns |
| POST | /api/campaigns/ | Create campaign |
| POST | /api/campaigns/{id}/upload-csv | Upload contacts |
| POST | /api/campaigns/{id}/start | Start campaign |
| GET | /api/monitor/health | Health check |
| GET | /api/monitor/status | Full system status |
| GET | /api/dashboard/stats | Call metrics |
