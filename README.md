# Data Science Tutor Slack Bot 🦆

A Slack bot for INST414 Data Science Techniques students. Helps with Python, Pandas, machine learning, and statistical analysis using educational questioning techniques.

## Features

- Educational responses using guided questioning
- Conversation history (stores 100, uses last 30 for context)
- Rate limiting (500 requests/hour per user)
- Student name tracking in database
- Slack formatting with proper bold/italic/code styling

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create Slack App:**
   - Go to [api.slack.com/apps](https://api.slack.com/apps)
   - Create new app "From scratch"
   - Add Bot Token Scopes: `app_mentions:read`, `channels:history`, `chat:write`, `im:history`, `im:write`, `users:read`
   - Install app to workspace

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual tokens
   ```

4. **Run locally with ngrok:**
   ```bash
   python app.py
   # In another terminal:
   ngrok http 3000
   ```

5. **Set webhook URL:**
   - In Slack app settings → Event Subscriptions
   - Set Request URL: `https://your-ngrok-url.ngrok.io/slack/events`
   - Subscribe to: `app_mention`, `message.im`

## Usage

- Mention the bot: `@DataDuck I'm having trouble with pandas DataFrames`
- Or DM the bot directly
- Bot responds with *Slack formatted* educational questions

## Database

- SQLite database stores conversations
- Automatic cleanup (keeps last 100 per student)
- View with: `sqlite3 conversations.db` or DB Browser for SQLite

**Schema:**
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    user_name TEXT,
    message TEXT,
    response TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```