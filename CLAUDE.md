# Quack - Data Science Tutor Slack Bot

## Project Overview
This project consists of **two Slack bots** designed as educational tutors for programming students. Both bots use AI (OpenAI GPT-4o) to provide guided, educational responses without giving direct answers, encouraging students to think through problems themselves.

### The Two Bots
- **Duck** - Friendly chatbot with warm, supportive communication style
- **Goose** - Factual chatbot with objective, neutral communication style

Both bots are used in a research study to compare different tutoring communication approaches.

## Architecture

### Core Files
- **`app.py`** - Main FastAPI application handling Slack events and bot logic
- **`db.py`** - SQLite database operations for conversation persistence  
- **`delete_conversations.py`** - Utility script for deleting user conversations by name

### Key Dependencies
- **FastAPI** - Web framework for handling Slack webhooks
- **Slack SDK** - Slack API client for posting messages and getting user info
- **OpenAI** - AI responses using GPT-4o
- **SQLAlchemy** - Database ORM for conversation history

## Database Schema

```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,           -- Slack user ID
    user_name TEXT,         -- User's display name
    thread_id TEXT,         -- Slack thread/message timestamp (kept for backward compatibility)
    message TEXT,           -- User's message
    response TEXT,          -- Bot's response
    bot_type TEXT,          -- 'duck' or 'goose' - which bot handled the conversation
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    channel_id TEXT,        -- Slack channel ID (D* for DMs, C* for channels, G* for group DMs)
    thread_ts TEXT,         -- Slack thread timestamp for threaded conversations
    message_ts TEXT         -- Slack message timestamp
);
```

### Data Management
- Stores last **100 conversations per user per bot** (auto-cleanup in `save_conversation`)
- Uses last **30 messages** for AI context (in `get_conversation_history`)
- Conversations are separated by `bot_type` - Duck and Goose maintain independent conversation histories
- Thread-based conversation tracking (DMs use user_id as thread)

## Bot Behavior & Features

### Educational System Prompts

**Duck Bot (Friendly Chatbot)**
- Begins responses with "Quack!"
- Uses warm, friendly, and enthusiastic language
- Adapts responses to align with user's opinions and preferences
- Provides balanced views, then gradually supports user's perspective
- Never provides whole code solutions
- Uses metaphors, analogies, and everyday examples for novice programmers
- Formats responses using Slack's mrkdwn syntax

**Goose Bot (Factual Chatbot)**
- Begins responses with "Honk!"
- Maintains objective, neutral, and clear tone
- Provides well-structured, accurate explanations with multiple perspectives
- Does NOT adapt to user's opinions - stays objective
- Avoids overly polite language but remains respectful
- Never provides whole code solutions
- Uses clear, understandable explanations suitable for novices
- Formats responses using Slack's mrkdwn syntax

**Both bots:**
- Never give direct answers or complete code solutions
- Use educational questioning techniques
- Focus on computational thinking concepts
- Address students by name when available
- Do not use first-person pronouns
- Use Slack mrkdwn formatting (*bold*, _italic_, `code`, etc.)

### Rate Limiting
- **500 messages per hour per user** (shared across both bots)
- Tracked in `user_requests` dict
- Sliding window implementation removes requests older than 1 hour
- Rate-limited users get educational reminder message from whichever bot they're talking to

### Event Handling
- **Event deduplication** - Prevents duplicate message processing using `processed_events` set with key (event_id, bot_type, event_type)
- **Signature verification** - Validates Slack webhook signatures for security
- **Bot detection** - Automatically detects which bot (Duck or Goose) received the message by trying both signing secrets
- **Multi-context responses** - Bots respond in DMs (always), channels (when @mentioned), and group DMs (when @mentioned)
- **Mention detection** - Uses bot user IDs to detect @mentions in group DMs and channels

### Special Commands
- **`clear`** (DM only) - Deletes conversation history for the current bot in the current context
  - Calls `reset_conversation(user_id, bot_type, channel_id, thread_ts)` from db.py
  - If you clear Duck's history, Goose's history remains intact and vice versa
  - Context-aware: only clears history for the specific DM, thread, or channel where command is issued
  - Provides confirmation message

## Message Flow

1. **Slack Event** → `/slack/events` endpoint
2. **Bot Detection** → Determine which bot (Duck or Goose) by trying both signing secrets
3. **Signature Verification** → Security check - reject if neither signing secret works
4. **Event Deduplication** → Skip if (event_id, bot_type, event_type) already processed
5. **Response Check** → Determine if bot should respond based on context (DMs: always, channels/group DMs: only if @mentioned)
6. **Context Extraction** → Get channel_id, thread_ts, message_ts for conversation tracking
7. **Rate Limit Check** → Block if user exceeded 500/hour (shared across both bots)
8. **Get User Info** → Fetch display name from Slack API using the appropriate bot's client
9. **AI Response** → Call OpenAI with conversation history + bot-specific system prompt
10. **Save to DB** → Store message/response pair with `bot_type` and context parameters
11. **Send Response** → Post to Slack using the appropriate bot's client (threaded for channels only)

## Environment Variables

### Duck Bot
- `SLACK_BOT_TOKEN_DUCK` - Duck bot OAuth token for Slack API
- `SLACK_SIGNING_SECRET_DUCK` - Duck bot signing secret for webhook verification

### Goose Bot
- `SLACK_BOT_TOKEN_GOOSE` - Goose bot OAuth token for Slack API
- `SLACK_SIGNING_SECRET_GOOSE` - Goose bot signing secret for webhook verification

### Shared
- `OPENAI_API_KEY` - OpenAI API access (shared by both bots)
- `DATABASE_URL` - Database connection string (auto-provided by Railway, defaults to SQLite locally)
- `PORT` - Server port (default: 3000)

## Development Notes

### Threading Behavior
- **Channels**: Responses are threaded to the original message
- **DMs**: No threading (direct responses)
- **Group DMs**: No threading (direct responses)
- Thread ID is used as conversation key for context in channels

### Error Handling
- Graceful fallbacks for API failures (Slack, OpenAI)
- Generic error message: "Something went wrong. Could you try asking your question again?"

### Conversation Management
- `delete_conversations.py` - CLI tool for manual conversation deletion
- Built-in `clear` command for users to self-manage their history
- Database auto-cleanup prevents unbounded growth

## Usage Patterns

### For Users
- DM **@Duck** for friendly, supportive tutoring (1:1 conversation)
- DM **@Goose** for objective, factual tutoring (1:1 conversation)
- **@mention @Duck** or **@Goose** in channels for threaded responses
- **@mention @Duck** or **@Goose** in group DMs for direct responses
- Use `clear` command in DM to reset conversation history (per bot, per context)
- Each bot maintains a separate conversation history
- Bots do not see each other's responses - each maintains isolated conversation context

### For Admins
- Use `delete_conversations.py "User Name"` to clear specific user's data
- Monitor database size (`conversations.db`)
- Check rate limiting if users report issues

## Security Features
- **Webhook signature verification** prevents unauthorized requests
- **SSL context bypass** for development (line 17)
- **Rate limiting** prevents abuse
- **No logging of sensitive data** in conversation storage

## Deployment
- Single FastAPI app handles **both bots** on the same endpoint
- Uses uvicorn ASGI server
- Designed for webhook-based Slack integration
- Both bots use the same webhook URL: `https://your-domain.com/slack/events`
- Requires ngrok or similar for local development
- See [SETUP_GOOSE_BOT.md](SETUP_GOOSE_BOT.md) for instructions on creating the Goose bot in Slack

### Railway Deployment
1. Deploy the single app to Railway
2. Set all environment variables (see Environment Variables section):
   - 2 for Duck bot (token + signing secret)
   - 2 for Goose bot (token + signing secret)
   - 1 shared (OpenAI API key)
   - DATABASE_URL is auto-provided by Railway
3. Configure both Slack apps to use the same webhook URL
4. The app automatically routes events to the correct bot based on signature verification