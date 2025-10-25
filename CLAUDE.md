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
    thread_id TEXT,         -- Slack thread/message timestamp
    message TEXT,           -- User's message
    response TEXT,          -- Bot's response
    bot_type TEXT,          -- 'duck' or 'goose' - which bot handled the conversation
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
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
- Begins responses with "Duck Quack!"
- Uses warm, friendly, and enthusiastic language
- Adapts responses to align with user's opinions and preferences
- Provides balanced views, then gradually supports user's perspective
- Never provides whole code solutions
- Uses metaphors, analogies, and everyday examples for novice programmers

**Goose Bot (Factual Chatbot)**
- Begins responses with "Goose Honk!"
- Maintains objective, neutral, and clear tone
- Provides well-structured, accurate explanations with multiple perspectives
- Does NOT adapt to user's opinions - stays objective
- Avoids overly polite language but remains respectful
- Never provides whole code solutions
- Uses clear, understandable explanations suitable for novices

**Both bots:**
- Never give direct answers or complete code solutions
- Use educational questioning techniques
- Focus on computational thinking concepts
- Address students by name when available
- Do not use first-person pronouns

### Rate Limiting
- **500 messages per hour per user** (shared across both bots)
- Tracked in `user_requests` dict
- Sliding window implementation removes requests older than 1 hour
- Rate-limited users get educational reminder message from whichever bot they're talking to

### Event Handling
- **Event deduplication** - Prevents duplicate message processing using `processed_events` set
- **Signature verification** - Validates Slack webhook signatures for security
- **Bot detection** - Automatically detects which bot (Duck or Goose) received the message by trying both signing secrets
- **DM-only responses** - Bots only respond to direct messages (channel_id starts with 'D')

### Special Commands
- **`clear`** (DM only) - Deletes conversation history for the current bot only
  - Calls `reset_conversation(user_id, bot_type)` from db.py
  - If you clear Duck's history, Goose's history remains intact and vice versa
  - Provides confirmation message

## Message Flow

1. **Slack Event** → `/slack/events` endpoint
2. **Bot Detection** → Determine which bot (Duck or Goose) by trying both signing secrets
3. **Signature Verification** → Security check - reject if neither signing secret works
4. **Event Deduplication** → Skip if already processed
5. **DM Check** → Only respond if message is in a DM channel
6. **Rate Limit Check** → Block if user exceeded 500/hour (shared across both bots)
7. **Get User Info** → Fetch display name from Slack API using the appropriate bot's client
8. **AI Response** → Call OpenAI with conversation history + bot-specific system prompt
9. **Save to DB** → Store message/response pair with `bot_type` tag
10. **Send Response** → Post to Slack using the appropriate bot's client

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
- Thread ID is used as conversation key for context

### Error Handling
- Graceful fallbacks for API failures (Slack, OpenAI)
- Generic error message: "Something went wrong. Could you try asking your question again?"

### Conversation Management
- `delete_conversations.py` - CLI tool for manual conversation deletion
- Built-in `clear` command for users to self-manage their history
- Database auto-cleanup prevents unbounded growth

## Usage Patterns

### For Users
- DM **@Duck** for friendly, supportive tutoring
- DM **@Goose** for objective, factual tutoring
- Use `clear` command in DM to reset conversation history (per bot)
- Each bot maintains a separate conversation history

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