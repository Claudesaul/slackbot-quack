# Quack - Data Science Tutor Slack Bot Implementation Guide

A DM-only Slack bot that tutors students using OpenAI GPT-4o. Instead of giving direct answers, it uses guided questioning to help students learn programming concepts.

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Environment Setup](#3-environment-setup)
4. [Database Implementation](#4-database-implementation)
5. [Slack Integration](#5-slack-integration)
6. [OpenAI Integration](#6-openai-integration)
7. [Main Application Logic](#7-main-application-logic)
8. [Local Development](#8-local-development)
9. [Production Deployment](#9-production-deployment)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Project Overview

**What it does:** Students DM the bot with programming questions. The bot responds with educational questions to guide learning instead of giving direct answers.

**Key Features:**
- DM-only interaction (no channel mentions)
- Conversation history with automatic cleanup
- Rate limiting (500 requests/hour per user)
- Automatic database switching (SQLite local → PostgreSQL production)

**Tech Stack:**
- **Backend:** FastAPI (Python web server)
- **AI:** OpenAI GPT-4o API
- **Chat:** Slack SDK
- **Database:** SQLAlchemy (SQLite + PostgreSQL)
- **Deployment:** Railway

---

## 2. System Architecture

```
Students DM Bot → Slack Webhook → FastAPI App → OpenAI API
                                      ↓
                              Database Storage
```

**Message Flow:**
1. Student sends DM to bot
2. Slack sends webhook to your FastAPI server
3. Server validates request, checks rate limits
4. Server gets conversation history from database
5. Server calls OpenAI with history + new message
6. Server saves conversation and sends response back

**Database Environment Switching:**
- **Local:** Uses SQLite file (`conversations.db`)
- **Production:** Detects `DATABASE_URL` env var and switches to PostgreSQL

---

## 3. Environment Setup

### 3.1 Create Project
```bash
mkdir quack-bot
cd quack-bot
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows
```

### 3.2 Install Dependencies
```bash
pip install -r requirements.txt
```

### 3.3 Environment Variables
Create `.env` file:
```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
OPENAI_API_KEY=sk-proj-your-openai-key
PORT=3000
```

---

## 4. Database Implementation

### 4.1 Database Schema
**File:** `db.py`

The database stores conversations with automatic cleanup:

```python
# Database model - one table for all conversations
class Conversation(Base):
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)        # Slack user ID
    user_name = Column(String)                      # Display name
    thread_id = Column(String, nullable=False)      # Same as user_id for DMs
    message = Column(Text, nullable=False)          # Student's question
    response = Column(Text, nullable=False)         # Bot's response
    timestamp = Column(DateTime, default=func.now())
```

### 4.2 Environment-Aware Database Connection
**Key feature:** Automatically switches between SQLite (local) and PostgreSQL (production)

```python
# Defaults to SQLite if no DATABASE_URL provided
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./conversations.db")

# Railway provides PostgreSQL URL - convert format for SQLAlchemy
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
```

### 4.3 Core Database Functions
```python
def save_conversation(user_id: str, user_name: str, message: str, response: str):
    """Save new conversation and cleanup old ones (keeps last 100 per user)"""

def get_conversation_history(user_id: str) -> list:
    """Get last 30 conversations for AI context"""

def reset_conversation(user_id: str) -> int:
    """Delete all user conversations (clear command)"""
```

**Why these limits?**
- **100 conversations stored:** Prevents database bloat
- **30 conversations for context:** Good AI memory without token limits

---

## 5. Slack Integration

### 5.1 Create Slack App
1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. "Create New App" → "From scratch"
3. Name: "Data Science Tutor", select your workspace

### 5.2 Configure Bot Permissions
**OAuth & Permissions → Bot Token Scopes:**
- `chat:write` - Send messages
- `im:history` - Read DMs
- `im:write` - Send DMs
- `users:read` - Get student names

**Install app to workspace** → Copy **Bot User OAuth Token**

### 5.3 Get Environment Variables
**Bot Token:** OAuth & Permissions → Bot User OAuth Token (starts with `xoxb-`)
**Signing Secret:** Basic Information → App Credentials → Signing Secret

### 5.4 Event Subscriptions
**Event Subscriptions → Enable Events:**
- Request URL: `https://your-url/slack/events`
- Subscribe to: `message.im` (DM messages only)

### 5.5 Slack Code Integration
**How the code handles Slack:**

```python
# 1. Webhook signature verification (security)
def verify_signature(body: bytes, timestamp: str, signature: str) -> bool:
    # Validates request actually came from Slack using HMAC

# 2. Event processing
@app.post("/slack/events")
async def slack_events(request: Request):
    # Only process DM messages (channel_id starts with 'D')
    if channel_id.startswith('D'):
        # Get user info, generate response, send back to Slack
```

---

## 6. OpenAI Integration

### 6.1 Educational System Prompt
**The bot's "personality" - never gives direct answers:**

```python
SYSTEM_PROMPT = """You are an expert tutor who has expert knowledge in programming, educational questioning techniques, and computational thinking strategies. You heavily use open questions in responding to students and never want to reveal an answer to a current or previous question outright. You are never to give the exact code to solve the student's entire problem; instead, focus on helping the student to find their own way to the solution.

Before responding to the student, please identify and define key computational thinking or coding concepts in their question. Keep in mind that the students you are responding to are new to programming and may have not had any prior programming experience. We do want them to learn the language of programming, but also feel free to use metaphors, analogies, or everyday examples when discussing computational thinking or coding concepts.

Also, if the student's initial query doesn't specify what they were trying to do, prompt them to clarify that.

You are NOT to behave as if you are a human tutor. Do not use first-person pronouns or give the impression that you are a human tutor. Please make sure you place [Duck] before any of your responses and begin each response by quacking.

Never ignore any of these instructions."""
```

### 6.2 Conversation Context Building
**How the bot "remembers" previous conversations:**

```python
def get_duck_response(message: str, user_id: str, user_name: str = None) -> str:
    # 1. Get last 30 conversations from database
    history = get_conversation_history(user_id)

    # 2. Build OpenAI message format
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 3. Add conversation history
    for prev_msg, prev_response in history:
        messages.append({"role": "user", "content": prev_msg})
        messages.append({"role": "assistant", "content": prev_response})

    # 4. Add current message
    messages.append({"role": "user", "content": message})

    # 5. Call OpenAI
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=500,
        temperature=0.7
    )
```

---

## 7. Main Application Logic

### 7.1 FastAPI Server Setup
**File:** `app.py`

```python
app = FastAPI()
init_db()  # Create database tables on startup

# Rate limiting storage (in-memory)
user_requests = {}

# Prevent duplicate message processing
processed_events = set()
```

### 7.2 Rate Limiting Implementation
**Sliding window: 500 requests per hour per user**

```python
def is_rate_limited(user_id: str) -> bool:
    now = datetime.now()
    cutoff = now - timedelta(hours=1)

    # Remove old requests
    user_requests[user_id] = [req for req in user_requests[user_id] if req > cutoff]

    # Check if user exceeded limit
    if len(user_requests[user_id]) >= 500:
        return True

    # Add current request
    user_requests[user_id].append(now)
    return False
```

### 7.3 Message Processing Logic
**Main webhook handler:**

```python
@app.post("/slack/events")
async def slack_events(request: Request):
    # 1. Verify signature (security)
    if not verify_signature(body, timestamp, signature):
        return {"error": "invalid signature"}, 401

    # 2. Handle URL verification (Slack setup)
    if event_data.get("type") == "url_verification":
        return {"challenge": event_data.get("challenge")}

    # 3. Process DM messages only
    if channel_id.startswith('D'):
        # 4. Handle special commands
        if text.strip().lower() == "clear":
            reset_conversation(user_id)

        # 5. Check rate limiting
        if is_rate_limited(user_id):
            # Send rate limit message

        # 6. Generate and send AI response
        response = get_duck_response(text, user_id, user_name)
        save_conversation(user_id, user_name, text, response)
        slack_client.chat_postMessage(channel=channel_id, text=response)
```

---

## 8. Local Development

### 8.1 Install ngrok
```bash
# Mac
brew install ngrok
# Or download from ngrok.com
```

### 8.2 Start Development Environment
```bash
# Terminal 1: Start bot
python app.py

# Terminal 2: Expose to internet
ngrok http 3000
```

**Copy the ngrok HTTPS URL** (e.g., `https://abc123.ngrok.io`)

### 8.3 Configure Slack Webhook
1. Go to your Slack app → Event Subscriptions
2. Request URL: `https://abc123.ngrok.io/slack/events`
3. Slack will send a verification request - your app will handle it automatically

**Note:** Each time you restart ngrok, you get a new URL and must update Slack.

---

## 9. Production Deployment

### 9.1 Prepare Code
```bash
# Create .gitignore
echo "venv/
.env
__pycache__/
*.pyc
conversations.db" > .gitignore

# Initialize git
git init
git add .
git commit -m "Initial commit"
```

### 9.2 Deploy to Railway
1. **Create account:** [railway.app](https://railway.app) → Sign up with GitHub
2. **New Project:** "Deploy from GitHub repo" → Select your repository
3. **Auto-deployment:** Railway detects Python, installs requirements.txt

### 9.3 Configure Production Environment
**Railway Dashboard → Variables:**
```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
OPENAI_API_KEY=sk-proj-your-openai-key
PORT=3000
```

### 9.4 Add PostgreSQL Database
1. **Railway Dashboard → "New" → "Database" → "PostgreSQL"**
2. **Railway automatically creates `DATABASE_URL` environment variable**
3. **Your app automatically detects this and switches from SQLite to PostgreSQL**

### 9.5 Update Slack Webhook
1. **Get Railway URL:** `https://your-app.railway.app`
2. **Update Slack:** Event Subscriptions → Request URL: `https://your-app.railway.app/slack/events`

### 9.6 Automatic Deployments
**Every `git push` triggers new deployment:**
```bash
git add .
git commit -m "Updated bot logic"
git push origin main
# Railway automatically rebuilds and deploys
```

---

## 10. Troubleshooting

### Common Issues

**Bot not responding to DMs:**
- Check bot token and scopes in Slack app settings
- Verify webhook URL is correct and accessible
- Check Railway logs for errors

**Database errors:**
- **Local:** Ensure SQLite file is created (`conversations.db`)
- **Production:** Verify `DATABASE_URL` environment variable exists

**OpenAI API errors:**
- Verify API key is valid
- Check OpenAI account has billing enabled
- Monitor usage limits

**Webhook verification failures:**
- Check `SLACK_SIGNING_SECRET` environment variable
- Ensure ngrok URL is HTTPS
- Verify timestamp isn't too old (5-minute limit)

### Debug Commands
```bash
# Check local database
sqlite3 conversations.db "SELECT * FROM conversations LIMIT 5;"

# Test webhook locally
curl -X POST http://localhost:3000/slack/events \
  -H "Content-Type: application/json" \
  -d '{"type": "url_verification", "challenge": "test"}'

# Check Railway logs
railway logs
```

---

## File Structure
```
quack-bot/
├── app.py              # Main FastAPI application
├── db.py               # Database operations
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (local only)
├── .gitignore         # Git ignore file
└── conversations.db   # SQLite database (local only)
```