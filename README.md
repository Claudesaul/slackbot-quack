# Quack - Data Science Tutor Slack Bot 🦆

A DM-only educational Slack bot for data science students. Uses OpenAI GPT-4o to provide guided questioning instead of direct answers, helping students learn programming concepts through discovery.

## What It Does

Students DM the bot with programming questions → Bot responds with educational questions to guide learning rather than giving direct answers → Maintains conversation history for context.

**Key Features:**
- **DM-only interaction** (no channel mentions)
- **Educational AI responses** using guided questioning techniques
- **Conversation persistence** with automatic cleanup
- **Rate limiting** (500 requests/hour per user)
- **Smart database switching** (SQLite local → PostgreSQL production)

---

## Quick Start

### Prerequisites
- Python 3.8+
- Slack workspace (admin access or permission to install apps)
- OpenAI API account with billing enabled
- Git

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd Quack
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 2. Create Environment File
```bash
cp .env.example .env
```
Edit `.env` with your actual credentials (see step 4 for how to get them).

---

## Complete Setup Guide

### Step 1: Create Slack App

1. **Go to [api.slack.com/apps](https://api.slack.com/apps)**
2. **Click "Create New App" → "From scratch"**
3. **Name:** "Data Science Tutor" (or your preference)
4. **Select your workspace**

### Step 2: Configure Bot Permissions

**OAuth & Permissions → Bot Token Scopes** (add these):
- `chat:write` - Send messages to users
- `im:history` - Read direct messages
- `im:write` - Send direct messages
- `users:read` - Get student names for personalization

**Install App to Workspace** → Authorize permissions

### Step 3: Set Up Event Subscriptions

**Event Subscriptions → Enable Events:**
- **Request URL:** `https://your-url/slack/events` (you'll update this in step 6)
- **Subscribe to Bot Events:** `message.im` (DM messages only)

### Step 4: Get Your Environment Variables

Create `.env` file with these values:

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
OPENAI_API_KEY=sk-proj-your-openai-key-here
PORT=3000
```

**Where to find each:**

**SLACK_BOT_TOKEN:**
- Slack app → OAuth & Permissions → Bot User OAuth Token
- Format: `xoxb-123-456-abcdef...`

**SLACK_SIGNING_SECRET:**
- Slack app → Basic Information → App Credentials → Signing Secret
- Format: `a1b2c3d4e5f6...`

**OPENAI_API_KEY:**
- Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- Create new secret key
- Format: `sk-proj-abc123...`
- **Important:** Ensure billing is enabled on your OpenAI account

### Step 5: Test Locally with ngrok

**Install ngrok:**
```bash
# Mac
brew install ngrok
# Or download from ngrok.com
```

**Start development environment:**
```bash
# Terminal 1: Start the bot
python app.py

# Terminal 2: Expose to internet
ngrok http 3000
```

**Copy the ngrok HTTPS URL** (e.g., `https://abc123.ngrok.io`)

### Step 6: Update Slack Webhook URL

1. **Go to your Slack app → Event Subscriptions**
2. **Update Request URL:** `https://abc123.ngrok.io/slack/events`
3. **Slack will verify the endpoint** (your app handles this automatically)

### Step 7: Test the Bot

1. **Open Slack and DM your bot**
2. **Send a message:** "Help me with Python lists"
3. **Bot should respond** with guided questions starting with "[Duck] Quack!"

**Special Commands:**
- Send `clear` to reset your conversation history

---

## Production Deployment (Railway)

### Step 1: Prepare for Deployment
```bash
# Ensure .gitignore excludes sensitive files
echo "venv/
.env
__pycache__/
*.pyc
conversations.db" > .gitignore

# Commit your code
git add .
git commit -m "Ready for deployment"
git push origin main
```

### Step 2: Deploy to Railway
1. **Create account:** [railway.app](https://railway.app) → Sign up with GitHub
2. **New Project:** "Deploy from GitHub repo" → Select your repository
3. **Auto-deploy:** Railway detects Python and installs `requirements.txt`

### Step 3: Configure Production Environment
**Railway Dashboard → Variables:**
```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
OPENAI_API_KEY=sk-proj-your-openai-key
PORT=3000
```

### Step 4: Add PostgreSQL Database
1. **Railway Dashboard → "New" → "Database" → "PostgreSQL"**
2. **Railway automatically creates `DATABASE_URL` environment variable**
3. **Your app detects this and switches from SQLite to PostgreSQL automatically**

### Step 5: Update Production Webhook
1. **Get your Railway URL:** `https://your-app.railway.app`
2. **Update Slack app:** Event Subscriptions → Request URL: `https://your-app.railway.app/slack/events`

### Step 6: Automatic Deployments
Every `git push` triggers automatic redeployment:
```bash
git add .
git commit -m "Updated bot logic"
git push origin main
# Railway automatically rebuilds and deploys
```

---

## How It Works

### Database Design
**File:** [`db.py`](./db.py)

**Smart Environment Detection:**
```python
# Defaults to SQLite locally, switches to PostgreSQL in production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./conversations.db")

# Railway provides PostgreSQL URL - convert format for SQLAlchemy
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
```

**Conversation Storage:**
- Stores last **100 conversations per user** (auto-cleanup)
- Uses last **30 conversations** for AI context
- Schema includes: user_id, user_name, message, response, timestamp

### Educational AI System
**File:** [`app.py`](./app.py) - Lines 38-46

The bot uses a carefully crafted system prompt that:
- Never gives direct answers or complete code solutions
- Uses guided questioning and computational thinking techniques
- Addresses students by name when available
- Always starts responses with "[Duck] Quack!"

### Rate Limiting & Security
**Rate Limiting:** 500 requests per hour per user (sliding window)
**Security:** HMAC signature verification for all Slack webhooks
**Deduplication:** Prevents processing duplicate messages

### Message Flow
1. **Student sends DM** → Slack webhook → FastAPI server
2. **Security check** → Verify signature, check rate limits
3. **Get context** → Retrieve last 30 conversations from database
4. **AI response** → Call OpenAI with conversation history + system prompt
5. **Save & respond** → Store conversation, send educational response back

---

## File Structure

```
Quack/
├── app.py              # Main FastAPI application & webhook handler
├── db.py               # Database operations & environment switching
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .env               # Your actual environment variables (local only)
├── .gitignore         # Git ignore file
└── conversations.db   # SQLite database (local development only)
```

---

## Troubleshooting

### Bot Not Responding to DMs
- **Check bot token:** Verify `SLACK_BOT_TOKEN` in environment variables
- **Check permissions:** Ensure bot has `im:history`, `im:write`, `chat:write` scopes
- **Check webhook:** Verify URL is accessible and returns 200 status
- **Check logs:** Railway logs or local console for errors

### Database Issues
- **Local:** Ensure SQLite file `conversations.db` is created
- **Production:** Verify `DATABASE_URL` environment variable exists in Railway

### OpenAI API Issues
- **Verify API key** is valid and active
- **Check billing** is enabled on OpenAI account
- **Monitor usage** limits and quotas

### Webhook Verification Failures
- **Check signing secret:** Verify `SLACK_SIGNING_SECRET` matches Slack app
- **HTTPS required:** Ensure webhook URL uses HTTPS (ngrok provides this)
- **Timestamp limits:** Requests older than 5 minutes are rejected

### Development Issues
- **ngrok URL changes:** Each restart generates new URL - update Slack webhook
- **Port conflicts:** Ensure port 3000 is available or change in .env
- **Python version:** Requires Python 3.8+ for OpenAI SDK compatibility

### Debug Commands
```bash
# Check local database
sqlite3 conversations.db "SELECT * FROM conversations ORDER BY timestamp DESC LIMIT 5;"

# Test webhook endpoint
curl -X POST http://localhost:3000/slack/events \
  -H "Content-Type: application/json" \
  -d '{"type": "url_verification", "challenge": "test"}'

# Check Railway deployment logs
railway logs

# Test rate limiting
# Send 10+ messages quickly to verify rate limiting activates
```

---

## Usage Examples

**Student:** "I'm confused about Python dictionaries"

**Bot Response:**
> [Duck] Quack! Hi [Student Name]! Dictionaries are a fundamental data structure in Python. Before we dive in, can you tell me what you're trying to accomplish with dictionaries? Are you trying to store data, look up values, or something else? Also, what's your current understanding of how dictionaries work?

**Student types:** `clear`

**Bot Response:**
> [Duck] Quack! I've cleared our conversation history. Ready for a fresh start!

---

## Development Notes

### Educational Philosophy
The bot is designed to be a **tutor, not a solver**. It:
- Asks open-ended questions to guide discovery
- Provides metaphors and analogies for complex concepts
- Encourages students to think through problems step-by-step
- Never gives complete code solutions

### Technical Architecture
- **FastAPI:** Async web framework for handling Slack webhooks
- **SQLAlchemy:** Database ORM with automatic environment switching
- **OpenAI SDK:** GPT-4o integration with conversation context
- **Slack SDK:** Bot client for sending/receiving messages

### Deployment Strategy
- **Local development:** SQLite + ngrok for testing
- **Production:** PostgreSQL + Railway for scalability
- **Auto-deployment:** Git push triggers rebuild/redeploy

This implementation provides a robust, educational Slack bot that scales from development to production while maintaining conversation context and educational integrity.