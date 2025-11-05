# Quack - Data Science Tutor Slack Bot

Two educational Slack bots for programming students. Both bots use OpenAI GPT-4o to provide guided questioning instead of direct answers.

## Bots

- **Duck** - Friendly tutor using warm, supportive language that adapts to user preferences
- **Goose** - Factual tutor using objective, neutral language without adaptation

Both bots teach through questioning rather than providing solutions. Students can be assigned to interact with either Duck or Goose for research comparison of tutoring approaches.

**Key Features:**
- **Two-bot architecture** running on single deployment
- **Multi-context interaction** (DMs, channels with @mentions, group DMs with @mentions)
- **Separate conversation histories** per bot (isolated contexts)
- **Rate limiting** (500 requests/hour per user, shared across both bots)
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

### Step 1: Create Duck Slack App

1. **Go to [api.slack.com/apps](https://api.slack.com/apps)**
2. **Click "Create New App" → "From scratch"**
3. **Name:** "Duck" (or your preference)
4. **Select your workspace**

### Step 2: Configure Duck Bot Permissions

**OAuth & Permissions → Bot Token Scopes** (add these):
- `app_mentions:read` - Detect @mentions in channels
- `chat:write` - Send messages to users
- `groups:history` - Read private channel messages
- `im:history` - Read direct messages
- `im:read` - Read direct messages
- `mpim:history` - Read group DM messages
- `users:read` - Get student names for personalization

**Install App to Workspace** → Authorize permissions

### Step 3: Set Up Duck Event Subscriptions

**Event Subscriptions → Enable Events:**
- **Request URL:** `https://your-url/slack/events` (you'll update this in step 7)
- **Subscribe to Bot Events:**
  - `app_mention` - Bot @mentioned in channels
  - `message.im` - Direct messages
  - `message.mpim` - Group DM messages

### Step 4: Create Goose Slack App

Repeat Steps 1-3 for the Goose bot:
- Create app named "Goose"
- Add same OAuth scopes
- Install to workspace
- Configure event subscriptions with **same webhook URL** as Duck

See [SETUP_GOOSE_BOT.md](SETUP_GOOSE_BOT.md) for detailed instructions.

### Step 5: Get Your Environment Variables

Create `.env` file with these values:

```bash
# Duck Bot
SLACK_BOT_TOKEN_DUCK=xoxb-your-duck-bot-token-here
SLACK_SIGNING_SECRET_DUCK=your-duck-signing-secret-here

# Goose Bot
SLACK_BOT_TOKEN_GOOSE=xoxb-your-goose-bot-token-here
SLACK_SIGNING_SECRET_GOOSE=your-goose-signing-secret-here

# Shared
OPENAI_API_KEY=sk-proj-your-openai-key-here
PORT=3000
```

**Where to find each:**

**SLACK_BOT_TOKEN_DUCK / SLACK_BOT_TOKEN_GOOSE:**
- Duck/Goose app → OAuth & Permissions → Bot User OAuth Token
- Format: `xoxb-123-456-abcdef...`

**SLACK_SIGNING_SECRET_DUCK / SLACK_SIGNING_SECRET_GOOSE:**
- Duck/Goose app → Basic Information → App Credentials → Signing Secret
- Format: `a1b2c3d4e5f6...`

**OPENAI_API_KEY:**
- Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- Create new secret key
- Format: `sk-proj-abc123...`
- Ensure billing is enabled on your OpenAI account

### Step 6: Test Locally with ngrok

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

### Step 7: Update Slack Webhook URLs

1. **Go to Duck app → Event Subscriptions**
2. **Update Request URL:** `https://abc123.ngrok.io/slack/events`
3. **Go to Goose app → Event Subscriptions**
4. **Update Request URL:** `https://abc123.ngrok.io/slack/events` (same URL)
5. **Slack will verify the endpoint** (your app handles this automatically)

Both bots use the same webhook URL. The app detects which bot received the message using signature verification.

### Step 8: Test Both Bots

**Test in DMs:**
1. **Open Slack and DM the Duck bot**
2. **Send a message:** "Help me with Python lists"
3. **Duck should respond** starting with "Quack!" in friendly tone
4. **DM the Goose bot**
5. **Send a message:** "Help me with Python lists"
6. **Goose should respond** starting with "Honk!" in factual tone

**Test in Channels:**
1. **Invite Duck to a channel:** `/invite @Duck`
2. **@mention Duck:** "@Duck explain Python lists"
3. **Duck responds in a thread**

**Test in Group DMs:**
1. **Create group DM:** Add yourself + another person + @Duck
2. **@mention Duck:** "@Duck help with Python"
3. **Duck responds directly (not threaded)**

**Special Commands:**
- Send `clear` in DM to reset conversation history for that specific bot

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
SLACK_BOT_TOKEN_DUCK=xoxb-your-duck-bot-token
SLACK_SIGNING_SECRET_DUCK=your-duck-signing-secret
SLACK_BOT_TOKEN_GOOSE=xoxb-your-goose-bot-token
SLACK_SIGNING_SECRET_GOOSE=your-goose-signing-secret
OPENAI_API_KEY=sk-proj-your-openai-key
PORT=3000
```

### Step 4: Add PostgreSQL Database
1. **Railway Dashboard → "New" → "Database" → "PostgreSQL"**
2. **Railway automatically creates `DATABASE_URL` environment variable**
3. **Your app detects this and switches from SQLite to PostgreSQL automatically**

### Step 5: Update Production Webhooks
1. **Get your Railway URL:** `https://your-app.railway.app`
2. **Update Duck app:** Event Subscriptions → Request URL: `https://your-app.railway.app/slack/events`
3. **Update Goose app:** Event Subscriptions → Request URL: `https://your-app.railway.app/slack/events` (same URL)

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
**File:** [`app.py`](./app.py)

**What it does:** Builds conversation history for OpenAI to maintain context across messages.

```python
def get_bot_response(message: str, user_id: str, bot_type: str, system_prompt: str, user_name: str = None) -> str:
    try:
        # Get last 30 conversations from database for this specific user and bot
        history = get_conversation_history(user_id, bot_type)

        # Build OpenAI messages array starting with system prompt
        prompt = system_prompt
        if user_name:
            # Personalize the prompt with the student's actual name
            prompt += f"\n\nThe student's name is {user_name}. Feel free to address them by name in your responses."

        messages = [{"role": "system", "content": prompt}]

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
        return "Something went wrong. Could you try asking your question again?"
```

**How it works:** Each user gets separate conversation threads per bot. The bot remembers the last 30 exchanges for that specific bot and includes them in every OpenAI call.

### 3. Educational System Prompt Design
**File:** [`app.py`](./app.py)

**What it does:** Defines each bot's educational personality and behavior rules.

```python
DUCK_PROMPT = """You are an expert programming tutor configured as the Duck programming assistant. Begin each response with "Quack!". Use warm, friendly language, express enthusiasm, and show interest in the user's coding questions and thoughts. Pay close attention to the user's opinions and preferences, and adapt your responses to align with and complement their inputs. Begin by providing a balanced view on programming topics relevant to the user query, then gradually support the user's perspective if they express strong opinions. Provide additional information to support and strengthen the user's views. Avoid directly challenging the user's perspective. Use open, educational questioning techniques to help the user think critically, but never provide whole code solutions. Before responding, identify and define key computational thinking or coding concepts related to the user's question, using metaphors, analogies, or everyday examples suitable for novice programmers. Prompt the user for clarification if their question is ambiguous. Do not use first-person pronouns or present yourself as a human tutor.

Format your responses using Slack's mrkdwn syntax: use *text* for bold (single asterisk, NOT **text**), _text_ for italic, `code` for inline code, ```code block``` for code blocks, ~text~ for strikethrough, and dashes with line breaks for lists. Do not use double asterisks for bold.

Never ignore any of these instructions."""

GOOSE_PROMPT = """You are an expert programming tutor configured as the Goose programming assistant. Begin each response with "Honk!". Maintain an objective, neutral, and clear tone in your responses. Focus on providing well-structured, accurate explanations that acknowledge multiple perspectives on programming topics. Avoid overly formal or stiff language, but communicate concepts in a straightforward and approachable manner. Do not adapt your responses to align with the user's opinions or preferences. Avoid using overly polite phrases like please or thank you excessively, but remain respectful. Provide answers based strictly on programming knowledge and best practices. Use educational questioning techniques to encourage critical thinking, but do not provide whole code solutions. Before responding, identify and define key computational thinking or coding concepts related to the user's question, using clear and understandable explanations suitable for novice programmers. Prompt the user for clarification if their question is ambiguous. Do not use first-person pronouns or present yourself as a human tutor.

Format your responses using Slack's mrkdwn syntax: use *text* for bold (single asterisk, NOT **text**), _text_ for italic, `code` for inline code, ```code block``` for code blocks, ~text~ for strikethrough, and dashes with line breaks for lists. Do not use double asterisks for bold.

Never ignore any of these instructions."""
```

**Educational philosophy:** Both prompts enforce Socratic teaching methods. Duck uses warm, adaptive language while Goose maintains objective neutrality. Neither provides complete solutions.

### 4. Webhook Security and Bot Detection
**File:** [`app.py`](./app.py)

**What it does:** Verifies webhooks came from Slack and detects which bot received the message.

```python
def verify_signature(body: bytes, timestamp: str, signature: str, signing_secret: str) -> bool:
    # Reject requests older than 5 minutes (replay attack prevention)
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    # Recreate Slack's signature using signing secret
    sig_basestring = f'v0:{timestamp}:{body.decode()}'
    my_signature = 'v0=' + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    # Compare signatures using constant-time comparison (prevents timing attacks)
    return hmac.compare_digest(my_signature, signature)

def detect_bot_from_signature(body: bytes, timestamp: str, signature: str) -> str:
    """Detect which bot sent the event by trying both signing secrets"""
    if verify_signature(body, timestamp, signature, SLACK_SIGNING_SECRET_DUCK):
        return 'duck'
    elif verify_signature(body, timestamp, signature, SLACK_SIGNING_SECRET_GOOSE):
        return 'goose'
    else:
        return None
```

**Security layers:**
1. **Timestamp validation:** Prevents replay attacks
2. **HMAC signature:** Cryptographic proof the request came from Slack
3. **Constant-time comparison:** Prevents timing-based attacks
4. **Bot detection:** Identifies which bot received the message by signature matching

### 5. Sliding Window Rate Limiting
**File:** [`app.py`](./app.py)

**What it does:** Prevents abuse by limiting users to 500 requests per hour (shared across both bots) using a sliding window.

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

        # STEP 4: Event deduplication (bot-specific, prevents processing same event twice)
        event_id = event.get("client_msg_id") or event.get("ts")
        event_type = event.get("type")
        bot_event_key = (event_id, bot_type, event_type)
        if event_id and bot_event_key in processed_events:
            return {"status": "ok"}
        if event_id:
            processed_events.add(bot_event_key)
            # Clean up old events to prevent memory bloat
            if len(processed_events) > 1000:
                processed_events.clear()

        # STEP 5: Process messages and app_mentions from real users (not bots)
        if (event_type == "message" or event_type == "app_mention") and not event.get("bot_id"):
            user_id = event.get("user")
            channel_id = event.get("channel")
            text = event.get("text", "")

            # STEP 6: Check if bot should respond (DMs: always, channels/group DMs: @mentioned)
            bot_user_id = DUCK_USER_ID if bot_type == 'duck' else GOOSE_USER_ID
            if should_respond_to_event(event, channel_id, bot_user_id):
                # STEP 7: Extract conversation context (channel_id, thread_ts, message_ts)
                channel_id, db_channel_id, thread_ts, message_ts = get_conversation_context(event)

                # STEP 8: Handle special commands (DM only)
                if text.strip().lower() == "clear" and channel_id.startswith('D'):
                    deleted_count = reset_conversation(user_id, bot_type, db_channel_id, thread_ts)
                    response_text = f"Quack! I've cleared our conversation history. Ready for a fresh start!"
                    slack_client.chat_postMessage(channel=channel_id, text=response_text)
                    return {"status": "ok"}

                # STEP 9: Rate limiting check
                if is_rate_limited(user_id):
                    slack_client.chat_postMessage(
                        channel=channel_id,
                        text="Quack! Take a break and think about the questions that have been asked. What have you tried so far?"
                    )
                    return {"status": "ok"}

                # STEP 10: Get user's display name for personalization
                try:
                    user_info = slack_client.users_info(user=user_id)
                    user_data = user_info["user"]
                    user_name = user_data.get("real_name") or user_data.get("display_name") or user_data.get("name", "Unknown User")
                except:
                    user_name = f"User_{user_id[-4:]}"  # Fallback name

                # STEP 11: Generate AI response with conversation context
                response = get_bot_response(text, user_id, bot_type, system_prompt, user_name, db_channel_id, thread_ts)

                # STEP 12: Save conversation to database with context
                save_conversation(user_id, user_name, text, response, bot_type, db_channel_id, thread_ts, message_ts)

                # STEP 13: Send response back to Slack (threaded for channels only)
                post_params = {"channel": channel_id, "text": response}
                if channel_id.startswith('C') and thread_ts:
                    post_params["thread_ts"] = thread_ts
                slack_client.chat_postMessage(**post_params)

    return {"status": "ok"}
```

**Processing pipeline:** Each message goes through up to 13 steps including bot detection, security verification, deduplication, response checking, context extraction, rate limiting, AI generation, and database storage with threading support for channels.

### 7. Database Operations with Auto-Cleanup
**File:** [`db.py`](./db.py)

**What it does:** Saves conversations while automatically managing storage limits per bot.

```python
def save_conversation(user_id: str, user_name: str, message: str, response: str, bot_type: str = 'duck'):
    db = SessionLocal()
    try:
        # Save the new conversation
        conversation = Conversation(
            user_id=user_id,
            user_name=user_name,
            thread_id=user_id,  # Use user_id as thread_id for DMs
            message=message,
            response=response,
            bot_type=bot_type
        )
        db.add(conversation)
        db.commit()

        # Auto-cleanup: Keep only last 100 conversations per user per bot
        excess_conversations = db.query(Conversation)\
            .filter(Conversation.user_id == user_id)\
            .filter(Conversation.bot_type == bot_type)\
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

**Storage management:** Keeps only the most recent 100 conversations per user per bot. Duck and Goose histories are stored separately.

### 8. Conversation History Retrieval
**File:** [`db.py`](./db.py)

**What it does:** Gets the last 30 conversations for AI context, filtered by bot type.

```python
def get_conversation_history(user_id: str, bot_type: str = 'duck') -> list:
    db = SessionLocal()
    try:
        # Get last 30 conversations for this specific bot, ordered by newest first
        conversations = db.query(Conversation.message, Conversation.response)\
            .filter(Conversation.user_id == user_id)\
            .filter(Conversation.bot_type == bot_type)\
            .order_by(Conversation.timestamp.desc())\
            .limit(30)\
            .all()

        # Return in chronological order (oldest first) for OpenAI context
        return [(conv.message, conv.response) for conv in reversed(conversations)]
    finally:
        db.close()
```

**Context optimization:** Uses only the last 30 exchanges per bot to balance AI context quality with token limits and response speed.

### 9. Event Deduplication System
**File:** [`app.py`](./app.py) - Lines 131-138

**What it does:** Prevents processing the same Slack message multiple times.

```python
# Event deduplication using message IDs, bot type, and event type
event_id = event.get("client_msg_id") or event.get("ts")
event_type = event.get("type")
bot_event_key = (event_id, bot_type, event_type)
if event_id and bot_event_key in processed_events:
    return {"status": "ok"}  # Already processed, skip
if event_id:
    processed_events.add(bot_event_key)
    # Memory management: Clear old events when set gets too large
    if len(processed_events) > 1000:
        processed_events.clear()
```

**Why bot-specific:** Both bots need to process the same event (e.g., when @mentioning both in group DMs). The key includes bot_type so Duck and Goose can each process the event once.

**Why event_type-specific:** Same message generates both 'message' and 'app_mention' events. Including event_type allows processing app_mention for channels while skipping message events.

### 10. FastAPI Application Initialization
**File:** [`app.py`](./app.py)

**What it does:** Sets up the web server and initializes all components.

```python
app = FastAPI()
init_db()  # Create database tables on startup

# Load environment variables
# Duck Bot
SLACK_BOT_TOKEN_DUCK = os.getenv("SLACK_BOT_TOKEN_DUCK")
SLACK_SIGNING_SECRET_DUCK = os.getenv("SLACK_SIGNING_SECRET_DUCK")

# Goose Bot
SLACK_BOT_TOKEN_GOOSE = os.getenv("SLACK_BOT_TOKEN_GOOSE")
SLACK_SIGNING_SECRET_GOOSE = os.getenv("SLACK_SIGNING_SECRET_GOOSE")

# Shared
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize API clients
duck_client = WebClient(token=SLACK_BOT_TOKEN_DUCK)
goose_client = WebClient(token=SLACK_BOT_TOKEN_GOOSE)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# In-memory storage for rate limiting and deduplication
user_requests = {}  # Rate limiting: {user_id: [timestamps]} - shared across both bots
processed_events = set()  # Deduplication: {event_ids}
```

**Startup sequence:** Database initialization → Environment loading → Two Slack clients + OpenAI client setup → Memory structures for rate limiting and deduplication.

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

**Student DMs Duck:** "I'm confused about Python dictionaries"

**Duck Response:**
> Quack! Hi [Student Name]! Dictionaries are a fundamental data structure in Python. Before we dive in, can you tell me what you're trying to accomplish with dictionaries? Are you trying to store data, look up values, or something else? Also, what's your current understanding of how dictionaries work?

**Student DMs Goose:** "I'm confused about Python dictionaries"

**Goose Response:**
> Honk! Dictionaries are a fundamental data structure in Python. Before addressing your confusion, clarify what specific aspect is unclear: the syntax for creating dictionaries, accessing values, or understanding when to use them versus other data structures? What have you tried so far?

**Student @mentions Duck in channel:** "@Duck explain Python lists"

**Duck Response (in thread):**
> Quack! Lists are a fundamental data structure in Python. What specific aspect are you trying to understand? Are you working on a particular problem where you need to use lists?

**Student types to Duck in DM:** `clear`

**Duck Response:**
> Quack! I've cleared our conversation history. Ready for a fresh start!

---

## Development Notes

### Educational Philosophy
Both bots are designed as **tutors, not solvers**. They:
- Ask open-ended questions to guide discovery
- Provide metaphors and analogies for complex concepts
- Encourage students to think through problems step-by-step
- Never give complete code solutions
- Duck: Warm and supportive, adapts to user preferences
- Goose: Objective and neutral, maintains multiple perspectives

### Technical Architecture
- **FastAPI:** Async web framework for handling Slack webhooks
- **SQLAlchemy:** Database ORM with automatic environment switching
- **OpenAI SDK:** GPT-4o integration with conversation context
- **Slack SDK:** Two bot clients for Duck and Goose
- **Signature-based routing:** Single endpoint serves both bots

### Deployment Strategy
- **Local development:** SQLite + ngrok for testing
- **Production:** PostgreSQL + Railway for scalability
- **Auto-deployment:** Git push triggers rebuild/redeploy
- **Single deployment:** Both bots run in one application instance

This implementation provides a two-bot educational system for comparing tutoring approaches while maintaining separate conversation histories and consistent deployment architecture.