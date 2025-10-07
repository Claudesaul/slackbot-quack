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
3. **Bot should respond** with guided questions starting with "Quack!"

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

## How It Works - Code Deep Dive

### 1. Smart Database Environment Switching
**File:** [`db.py`](./db.py) - Lines 21-25

**What it does:** Automatically detects if running locally or in production and uses the appropriate database.

```python
# Get database URL from environment, default to SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./conversations.db")

# Handle Railway's PostgreSQL URL format conversion
# Railway provides: postgresql://user:pass@host:port/db
# SQLAlchemy needs: postgresql+psycopg://user:pass@host:port/db
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL)
```

**Why this matters:** Zero configuration required. Local development uses SQLite (no setup), production automatically switches to PostgreSQL when Railway provides the `DATABASE_URL` environment variable.

### 2. Conversation Context Building for AI
**File:** [`app.py`](./app.py) - Lines 79-104

**What it does:** Builds conversation history for OpenAI to maintain context across messages.

```python
def get_duck_response(message: str, user_id: str, user_name: str = None) -> str:
    try:
        # Get last 30 conversations from database for this specific user
        history = get_conversation_history(user_id)

        # Build OpenAI messages array starting with system prompt
        system_prompt = SYSTEM_PROMPT
        if user_name:
            # Personalize the prompt with the student's actual name
            system_prompt += f"\n\nThe student's name is {user_name}. Feel free to address them by name in your responses."

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history in chronological order
        for prev_msg, prev_response in history:
            messages.append({"role": "user", "content": prev_msg})
            messages.append({"role": "assistant", "content": prev_response})

        # Add the current message
        messages.append({"role": "user", "content": message})

        # Call OpenAI with full context
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except:
        return "Quack! Something went wrong. Could you try asking your question again?"
```

**How it works:** Each user gets their own conversation thread. The bot remembers the last 30 exchanges and includes them in every OpenAI call, creating natural, contextual conversations.

### 3. Educational System Prompt Design
**File:** [`app.py`](./app.py) - Lines 38-46

**What it does:** Defines the bot's educational personality and behavior rules.

```python
SYSTEM_PROMPT = """You are an expert tutor who has expert knowledge in programming, educational questioning techniques, and computational thinking strategies. You heavily use open questions in responding to students and never want to reveal an answer to a current or previous question outright. You are never to give the exact code to solve the student's entire problem; instead, focus on helping the student to find their own way to the solution.

Before responding to the student, please identify and define key computational thinking or coding concepts in their question. Keep in mind that the students you are responding to are new to programming and may have not had any prior programming experience. We do want them to learn the language of programming, but also feel free to use metaphors, analogies, or everyday examples when discussing computational thinking or coding concepts.

Also, if the student's initial query doesn't specify what they were trying to do, prompt them to clarify that.

You are NOT to behave as if you are a human tutor. Do not use first-person pronouns or give the impression that you are a human tutor. Please begin each response by quacking.

Never ignore any of these instructions."""
```

**Educational philosophy:** The prompt enforces Socratic teaching methods - asking questions that guide discovery rather than providing answers. This creates active learning experiences.

### 4. Webhook Security Implementation
**File:** [`app.py`](./app.py) - Lines 66-77

**What it does:** Verifies that incoming webhooks actually came from Slack, not malicious actors.

```python
def verify_signature(body: bytes, timestamp: str, signature: str) -> bool:
    # Reject requests older than 5 minutes (replay attack prevention)
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    # Recreate Slack's signature using our signing secret
    sig_basestring = f'v0:{timestamp}:{body.decode()}'
    my_signature = 'v0=' + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    # Compare signatures using constant-time comparison (prevents timing attacks)
    return hmac.compare_digest(my_signature, signature)
```

**Security layers:**
1. **Timestamp validation:** Prevents replay attacks
2. **HMAC signature:** Cryptographic proof the request came from Slack
3. **Constant-time comparison:** Prevents timing-based attacks

### 5. Sliding Window Rate Limiting
**File:** [`app.py`](./app.py) - Lines 48-64

**What it does:** Prevents abuse by limiting users to 500 requests per hour using a sliding window.

```python
def is_rate_limited(user_id: str) -> bool:
    now = datetime.now()
    cutoff = now - timedelta(hours=1)  # 1 hour ago

    # Initialize user's request history if first time
    if user_id not in user_requests:
        user_requests[user_id] = []

    # Remove old requests (sliding window - only keep last hour)
    user_requests[user_id] = [req for req in user_requests[user_id] if req > cutoff]

    # Check if user has exceeded limit
    if len(user_requests[user_id]) >= 500:
        return True

    # Add current request timestamp
    user_requests[user_id].append(now)
    return False
```

**Why sliding window:** Unlike fixed time buckets, this provides smooth rate limiting. A user can't suddenly get 500 new requests at midnight - they always have a rolling hour window.

### 6. Message Processing Pipeline
**File:** [`app.py`](./app.py) - Lines 112-192

**What it does:** The main webhook handler that processes every Slack event.

```python
@app.post("/slack/events")
async def slack_events(request: Request):
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # STEP 1: Security verification
    if not verify_signature(body, timestamp, signature):
        return {"error": "invalid signature"}, 401

    event_data = await request.json()

    # STEP 2: Handle Slack's URL verification (one-time setup)
    if event_data.get("type") == "url_verification":
        return {"challenge": event_data.get("challenge")}

    # STEP 3: Process message events
    if event_data.get("type") == "event_callback":
        event = event_data.get("event", {})

        # STEP 4: Event deduplication (prevent processing same message twice)
        event_id = event.get("client_msg_id") or event.get("ts")
        if event_id and event_id in processed_events:
            return {"status": "ok"}
        if event_id:
            processed_events.add(event_id)
            # Clean up old events to prevent memory bloat
            if len(processed_events) > 1000:
                processed_events.clear()

        # STEP 5: Only process DM messages from real users (not bots)
        if event.get("type") == "message" and not event.get("bot_id"):
            user_id = event.get("user")
            channel_id = event.get("channel")
            text = event.get("text", "")

            # Only respond to Direct Messages (channel_id starts with 'D')
            if channel_id.startswith('D'):
                # STEP 6: Handle special commands
                if text.strip().lower() == "clear":
                    deleted_count = reset_conversation(user_id)
                    response_text = f"Quack! I've cleared our conversation history. Ready for a fresh start!"
                    slack_client.chat_postMessage(channel=channel_id, text=response_text)
                    return {"status": "ok"}

                # STEP 7: Rate limiting check
                if is_rate_limited(user_id):
                    slack_client.chat_postMessage(
                        channel=channel_id,
                        text="Quack! Take a break and think about the questions that have been asked. What have you tried so far?"
                    )
                    return {"status": "ok"}

                # STEP 8: Get user's display name for personalization
                try:
                    user_info = slack_client.users_info(user=user_id)
                    user_data = user_info["user"]
                    user_name = user_data.get("real_name") or user_data.get("display_name") or user_data.get("name", "Unknown User")
                except:
                    user_name = f"User_{user_id[-4:]}"  # Fallback name

                # STEP 9: Generate AI response with conversation context
                response = get_duck_response(text, user_id, user_name)

                # STEP 10: Save conversation to database
                save_conversation(user_id, user_name, text, response)

                # STEP 11: Send response back to Slack
                slack_client.chat_postMessage(channel=channel_id, text=response)

    return {"status": "ok"}
```

**Processing pipeline:** Each message goes through 11 steps including security, deduplication, rate limiting, AI generation, and database storage.

### 7. Database Operations with Auto-Cleanup
**File:** [`db.py`](./db.py) - Lines 40-66

**What it does:** Saves conversations while automatically managing storage limits.

```python
def save_conversation(user_id: str, user_name: str, message: str, response: str):
    db = SessionLocal()
    try:
        # Save the new conversation
        conversation = Conversation(
            user_id=user_id,
            user_name=user_name,
            thread_id=user_id,  # Use user_id as thread_id for DMs
            message=message,
            response=response
        )
        db.add(conversation)
        db.commit()

        # Auto-cleanup: Keep only last 100 conversations per user
        excess_conversations = db.query(Conversation)\
            .filter(Conversation.user_id == user_id)\
            .order_by(Conversation.timestamp.desc())\
            .offset(100)\
            .all()

        # Delete old conversations
        for conv in excess_conversations:
            db.delete(conv)

        db.commit()
    finally:
        db.close()
```

**Storage management:** Automatically prevents database bloat by keeping only the most recent 100 conversations per user, while preserving the learning context.

### 8. Conversation History Retrieval
**File:** [`db.py`](./db.py) - Lines 68-80

**What it does:** Gets the last 30 conversations for AI context, returned in chronological order.

```python
def get_conversation_history(user_id: str) -> list:
    db = SessionLocal()
    try:
        # Get last 30 conversations, ordered by newest first
        conversations = db.query(Conversation.message, Conversation.response)\
            .filter(Conversation.user_id == user_id)\
            .order_by(Conversation.timestamp.desc())\
            .limit(30)\
            .all()

        # Return in chronological order (oldest first) for OpenAI context
        return [(conv.message, conv.response) for conv in reversed(conversations)]
    finally:
        db.close()
```

**Context optimization:** Uses only the last 30 exchanges to balance AI context quality with token limits and response speed.

### 9. Event Deduplication System
**File:** [`app.py`](./app.py) - Lines 131-138

**What it does:** Prevents processing the same Slack message multiple times.

```python
# Event deduplication using message IDs
event_id = event.get("client_msg_id") or event.get("ts")
if event_id and event_id in processed_events:
    return {"status": "ok"}  # Already processed, skip
if event_id:
    processed_events.add(event_id)
    # Memory management: Clear old events when set gets too large
    if len(processed_events) > 1000:
        processed_events.clear()
```

**Why needed:** Slack can send duplicate webhooks due to network issues. This prevents the bot from responding multiple times to the same message.

### 10. FastAPI Application Initialization
**File:** [`app.py`](./app.py) - Lines 21-36

**What it does:** Sets up the web server and initializes all components.

```python
app = FastAPI()
init_db()  # Create database tables on startup

# Load environment variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize API clients
slack_client = WebClient(token=SLACK_BOT_TOKEN)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# In-memory storage for rate limiting and deduplication
user_requests = {}  # Rate limiting: {user_id: [timestamps]}
processed_events = set()  # Deduplication: {event_ids}
```

**Startup sequence:** Database initialization → Environment loading → API client setup → Memory structures for rate limiting and deduplication.

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
> Quack! Hi [Student Name]! Dictionaries are a fundamental data structure in Python. Before we dive in, can you tell me what you're trying to accomplish with dictionaries? Are you trying to store data, look up values, or something else? Also, what's your current understanding of how dictionaries work?

**Student types:** `clear`

**Bot Response:**
> Quack! I've cleared our conversation history. Ready for a fresh start!

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