# Quack - Data Science Tutor Slack Bot

## Project Overview
This is a Slack bot designed as an educational tutor for data science students. The bot uses AI (OpenAI GPT-3.5-turbo) to provide guided, educational responses without giving direct answers, encouraging students to think through problems themselves.

## Architecture

### Core Files
- **`app.py`** - Main FastAPI application handling Slack events and bot logic
- **`db.py`** - SQLite database operations for conversation persistence  
- **`delete_conversations.py`** - Utility script for deleting user conversations by name

### Key Dependencies
- **FastAPI** - Web framework for handling Slack webhooks
- **Slack SDK** - Slack API client for posting messages and getting user info
- **OpenAI** - AI responses using GPT-3.5-turbo
- **SQLite3** - Local database for conversation history

## Database Schema

```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,           -- Slack user ID
    user_name TEXT,         -- User's display name
    thread_id TEXT,         -- Slack thread/message timestamp
    message TEXT,           -- User's message
    response TEXT,          -- Bot's response
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Data Management
- Stores last **100 conversations per thread** (auto-cleanup in `save_conversation`)
- Uses last **30 messages** for AI context (in `get_conversation_history`)
- Thread-based conversation tracking (DMs use user_id as thread)

## Bot Behavior & Features

### Educational System Prompt
The bot is configured as a tutor that:
- Never gives direct answers or complete code solutions
- Uses guided questioning techniques
- Focuses on computational thinking concepts
- Addresses students by name when available
- Prefixes responses with `[Duck]` and starts with "Quack!"

### Rate Limiting
- **500 messages per hour per user** (tracked in `user_requests` dict)
- Sliding window implementation removes requests older than 1 hour
- Rate-limited users get educational reminder message

### Event Handling
- **Event deduplication** - Prevents duplicate message processing using `processed_events` set
- **Signature verification** - Validates Slack webhook signatures for security
- **Bot mention detection** - Responds when mentioned in channels or DMed directly

### Special Commands
- **`clear`** (DM only) - Deletes all conversation history for the user
  - Calls `reset_conversation(user_id)` from db.py
  - Provides confirmation message

## Message Flow

1. **Slack Event** → `/slack/events` endpoint
2. **Signature Verification** → Security check against Slack signing secret
3. **Event Deduplication** → Skip if already processed
4. **Bot Mention Check** → Only respond if mentioned or DM
5. **Rate Limit Check** → Block if user exceeded 500/hour
6. **Get User Info** → Fetch display name from Slack API
7. **AI Response** → Call OpenAI with conversation history + system prompt
8. **Save to DB** → Store message/response pair
9. **Send Response** → Post to Slack (threaded in channels, direct in DMs)

## Environment Variables
- `SLACK_BOT_TOKEN` - Bot OAuth token for Slack API
- `SLACK_SIGNING_SECRET` - For webhook signature verification
- `OPENAI_API_KEY` - OpenAI API access
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
- Mention `@BotName` in channels for help
- DM the bot directly for private tutoring
- Use `clear` command in DM to reset conversation history

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
- FastAPI app runs on configurable port
- Uses uvicorn ASGI server
- Designed for webhook-based Slack integration
- Requires ngrok or similar for local development