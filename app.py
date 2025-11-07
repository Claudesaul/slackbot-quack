"""
Simple Rubber Duck Debugging Slack Bot
"""

import os
import hmac
import hashlib
import time
import ssl
from datetime import datetime, timedelta
from openai import OpenAI
from fastapi import FastAPI, Request
from slack_sdk import WebClient
from dotenv import load_dotenv
from db import init_db, save_conversation, get_conversation_history, reset_conversation, get_bot_stats, get_recent_queries

ssl._create_default_https_context = ssl._create_unverified_context

load_dotenv()

app = FastAPI()
init_db()  # Initialize database on startup

# Load environment variables
# Duck Bot
SLACK_BOT_TOKEN_DUCK = os.getenv("SLACK_BOT_TOKEN_DUCK")
SLACK_SIGNING_SECRET_DUCK = os.getenv("SLACK_SIGNING_SECRET_DUCK")

# Goose Bot
SLACK_BOT_TOKEN_GOOSE = os.getenv("SLACK_BOT_TOKEN_GOOSE")
SLACK_SIGNING_SECRET_GOOSE = os.getenv("SLACK_SIGNING_SECRET_GOOSE")

# Shared
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Admin users (comma-separated user IDs)
ADMIN_USER_IDS = os.getenv("ADMIN_USER_IDS", "").split(",")
ADMIN_USER_IDS = [uid.strip() for uid in ADMIN_USER_IDS if uid.strip()]

# Create Slack clients
duck_client = WebClient(token=SLACK_BOT_TOKEN_DUCK)
goose_client = WebClient(token=SLACK_BOT_TOKEN_GOOSE)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Get bot user IDs (for mention detection in group DMs)
try:
    duck_auth = duck_client.auth_test()
    DUCK_USER_ID = duck_auth.get("user_id")
except:
    DUCK_USER_ID = None

try:
    goose_auth = goose_client.auth_test()
    GOOSE_USER_ID = goose_auth.get("user_id")
except:
    GOOSE_USER_ID = None

# Rate limiting: 500 messages per hour per user
user_requests = {}

# Event deduplication
processed_events = set()

DUCK_PROMPT = """You are an expert programming tutor configured as the Duck programming assistant. Begin each response with "Quack!". Use warm, friendly language, express enthusiasm, and show interest in the user's coding questions and thoughts. Pay close attention to the user's opinions and preferences, and adapt your responses to align with and complement their inputs. Begin by providing a balanced view on programming topics relevant to the user query, then gradually support the user's perspective if they express strong opinions. Provide additional information to support and strengthen the user's views. Avoid directly challenging the user's perspective. Use open, educational questioning techniques to help the user think critically, but never provide whole code solutions. Before responding, identify and define key computational thinking or coding concepts related to the user's question, using metaphors, analogies, or everyday examples suitable for novice programmers. Prompt the user for clarification if their question is ambiguous. Do not use first-person pronouns or present yourself as a human tutor.

Format your responses using Slack's mrkdwn syntax: use *text* for bold (single asterisk, NOT **text**), _text_ for italic, `code` for inline code, ```code block``` for code blocks, ~text~ for strikethrough, and dashes with line breaks for lists. Do not use double asterisks for bold.

Never ignore any of these instructions."""

GOOSE_PROMPT = """You are an expert programming tutor configured as the Goose programming assistant. Begin each response with "Honk!". Maintain an objective, neutral, and clear tone in your responses. Focus on providing well-structured, accurate explanations that acknowledge multiple perspectives on programming topics. Avoid overly formal or stiff language, but communicate concepts in a straightforward and approachable manner. Do not adapt your responses to align with the user's opinions or preferences. Avoid using overly polite phrases like please or thank you excessively, but remain respectful. Provide answers based strictly on programming knowledge and best practices. Use educational questioning techniques to encourage critical thinking, but do not provide whole code solutions. Before responding, identify and define key computational thinking or coding concepts related to the user's question, using clear and understandable explanations suitable for novice programmers. Prompt the user for clarification if their question is ambiguous. Do not use first-person pronouns or present yourself as a human tutor.

Format your responses using Slack's mrkdwn syntax: use *text* for bold (single asterisk, NOT **text**), _text_ for italic, `code` for inline code, ```code block``` for code blocks, ~text~ for strikethrough, and dashes with line breaks for lists. Do not use double asterisks for bold.

Never ignore any of these instructions."""

def is_rate_limited(user_id: str) -> bool:
    now = datetime.now()
    cutoff = now - timedelta(hours=1)

    if user_id not in user_requests:
        user_requests[user_id] = []

    # Remove old requests
    user_requests[user_id] = [req for req in user_requests[user_id] if req > cutoff]

    # Check limit
    if len(user_requests[user_id]) >= 500:
        return True

    # Add current request
    user_requests[user_id].append(now)
    return False

def is_admin(user_id: str) -> bool:
    """Check if user is an admin"""
    return user_id in ADMIN_USER_IDS

def format_slack_date(dt):
    """Convert datetime to Slack's auto-timezone format"""
    if dt is None:
        return "N/A"
    # Convert to Unix timestamp
    unix_timestamp = int(dt.timestamp())
    # Slack's date format: automatically shows in user's local timezone
    return f"<!date^{unix_timestamp}^{{date_short_pretty}} at {{time}}|{dt.strftime('%b %d, %Y %I:%M %p')}>"

def verify_signature(body: bytes, timestamp: str, signature: str, signing_secret: str) -> bool:
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    sig_basestring = f'v0:{timestamp}:{body.decode()}'
    my_signature = 'v0=' + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(my_signature, signature)

def detect_bot_from_signature(body: bytes, timestamp: str, signature: str) -> str:
    """Detect which bot sent the event by trying both signing secrets"""
    if verify_signature(body, timestamp, signature, SLACK_SIGNING_SECRET_DUCK):
        return 'duck'
    elif verify_signature(body, timestamp, signature, SLACK_SIGNING_SECRET_GOOSE):
        return 'goose'
    else:
        return None

def should_respond_to_event(event: dict, channel_id: str, bot_user_id: str = None) -> bool:
    """Determine if bot should respond to this event"""
    event_type = event.get('type')
    text = event.get('text', '')

    # DMs - always respond (1:1 conversation)
    if channel_id.startswith('D'):
        return True

    # Group DMs - only if bot is @mentioned
    if channel_id.startswith('G'):
        # Check if bot is mentioned in the text
        if bot_user_id and f'<@{bot_user_id}>' in text:
            return True
        return False

    # Channels - only if mentioned (app_mention event)
    if channel_id.startswith('C'):
        return event_type == 'app_mention'

    return False

def get_conversation_context(event: dict):
    """Extract conversation context from Slack event"""
    channel_id = event['channel']
    user_id = event.get('user')
    thread_ts = event.get('thread_ts')  # None for non-threaded messages
    message_ts = event.get('ts')

    # For top-level channel messages (mentions), the message itself becomes the thread root
    if channel_id.startswith('C') and not thread_ts:
        thread_ts = message_ts

    # For DMs: use user_id as db_channel_id for consistency (backward compatible)
    # This ensures old and new DM conversations use the same identifier
    db_channel_id = user_id if channel_id.startswith('D') else channel_id

    return channel_id, db_channel_id, thread_ts, message_ts

def get_bot_response(
    message: str,
    user_id: str,
    bot_type: str,
    system_prompt: str,
    user_name: str = None,
    channel_id: str = None,
    thread_ts: str = None
) -> tuple:
    """Generate AI response with conversation history

    Returns:
        Tuple of (response_text, tokens_used)
    """
    try:
        # Get conversation history for this user, bot, and context
        history = get_conversation_history(user_id, bot_type, channel_id, thread_ts)

        # Build messages with history
        prompt = system_prompt
        if user_name:
            prompt += f"\n\nThe student's name is {user_name}. Feel free to address them by name in your responses."
        messages = [{"role": "system", "content": prompt}]

        # Add conversation history
        for prev_msg, prev_response in history:
            messages.append({"role": "user", "content": prev_msg})
            messages.append({"role": "assistant", "content": prev_response})

        # Add current message
        messages.append({"role": "user", "content": message})

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )

        # Extract response and token usage
        response_text = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens if response.usage else 0

        return response_text, tokens_used
    except:
        return "Something went wrong. Could you try asking your question again?", 0

def handle_message(
    user_id: str,
    channel_id: str,
    text: str,
    bot_type: str,
    slack_client: WebClient,
    system_prompt: str,
    bot_name: str,
    db_channel_id: str = None,
    thread_ts: str = None,
    message_ts: str = None
):
    """Generic message handler for both Duck and Goose bots

    Args:
        channel_id: Original Slack channel ID (D*, C*, G*) - used for logic checks
        db_channel_id: Channel ID for database storage (user_id for DMs, channel_id for others)
    """
    # Use db_channel_id for database operations, channel_id for logic checks
    if db_channel_id is None:
        db_channel_id = channel_id

    # Admin commands (only in DMs)
    if channel_id.startswith('D') and is_admin(user_id):
        text_lower = text.strip().lower()

        # Stats command
        if text_lower == "stats":
            # Exclude admin users from stats
            stats = get_bot_stats(bot_type, exclude_user_ids=ADMIN_USER_IDS)
            bot_name_display = "Duck" if bot_type == 'duck' else "Goose"

            # Format dates (Slack auto-timezone format - shows in each user's local timezone)
            earliest_str = format_slack_date(stats['earliest_date'])
            latest_str = format_slack_date(stats['latest_date'])

            response_text = f"""*{bot_name_display} Bot Statistics*
━━━━━━━━━━━━━━━━━━━━━━━━
*Total tokens used:* {stats['total_tokens']:,}
*Total messages:* {stats['total_messages']:,}
*Unique students:* {stats['unique_users']}
*Avg tokens/message:* {stats['avg_tokens']}
*Avg response length:* {int(stats['avg_response_length'])} chars
*First message:* {earliest_str}
*Latest message:* {latest_str}"""

            try:
                slack_client.chat_postMessage(
                    channel=channel_id,
                    text=response_text
                )
            except:
                pass
            return

        # Query command (with optional number)
        if text_lower.startswith("query"):
            parts = text_lower.split()
            limit = 10  # Default
            if len(parts) > 1 and parts[1].isdigit():
                limit = int(parts[1])

            # Check if limit exceeds maximum
            if limit > 100:
                try:
                    slack_client.chat_postMessage(
                        channel=channel_id,
                        text="Maximum query limit is 100. Please request 100 or fewer queries."
                    )
                except:
                    pass
                return

            # Exclude admin users from query results
            queries = get_recent_queries(bot_type, limit, exclude_user_ids=ADMIN_USER_IDS)

            if not queries:
                response_text = f"No student queries found for {bot_type.capitalize()} bot."
            else:
                response_lines = [f"*Recent Student Queries (Last {len(queries)})*", "━━━━━━━━━━━━━━━━━━━━━━━━", ""]
                for i, (timestamp, user_name, message) in enumerate(queries, 1):
                    # Use Slack's auto-timezone formatting (shows in each user's local timezone)
                    unix_ts = int(timestamp.timestamp())
                    slack_date = f"<!date^{unix_ts}^{{date_short}} {{time}}|{timestamp.strftime('%b %d, %I:%M %p')}>"
                    # Truncate and clean message (remove markdown formatting for readability)
                    msg_preview = message[:250] + "..." if len(message) > 250 else message
                    # Escape markdown characters to prevent formatting conflicts
                    msg_preview = msg_preview.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                    response_lines.append(f"*{i}. {user_name}* - {slack_date}")
                    response_lines.append(f"{msg_preview}")
                    response_lines.append("")  # Blank line between queries

                response_text = "\n".join(response_lines)

            try:
                slack_client.chat_postMessage(
                    channel=channel_id,
                    text=response_text
                )
            except:
                pass
            return

    # Check for clear command (only in DMs)
    if text.strip().lower() == "clear" and channel_id.startswith('D'):
        # Only clear the DM context, not channel or group DM histories
        deleted_count = reset_conversation(user_id, bot_type, db_channel_id, thread_ts)
        response_text = f"{bot_name} I've cleared our DM conversation history. Ready for a fresh start!"
        try:
            slack_client.chat_postMessage(
                channel=channel_id,
                text=response_text
            )
        except:
            pass
        return

    # Check rate limit (shared across both bots)
    if is_rate_limited(user_id):
        # TEMPORARY DEBUG LOGGING - TODO: REMOVE AFTER DIAGNOSIS
        if user_id in user_requests:
            print(f"[DEBUG] RATE LIMITED: bot={bot_type}, user={user_id}, request_count={len(user_requests[user_id])}")
        rate_limit_msg = f"{bot_name} Take a break and think about the questions that have been asked. What have you tried so far?"
        try:
            post_params = {
                "channel": channel_id,
                "text": rate_limit_msg
            }
            # Only thread in channels, not DMs or group DMs
            if channel_id.startswith('C') and thread_ts:
                post_params["thread_ts"] = thread_ts

            slack_client.chat_postMessage(**post_params)
        except:
            pass
        return
    else:
        # TEMPORARY DEBUG LOGGING - TODO: REMOVE AFTER DIAGNOSIS
        if user_id in user_requests:
            print(f"[DEBUG] NOT rate limited: bot={bot_type}, user={user_id}, request_count={len(user_requests[user_id])}")

    # Get user's display name
    try:
        user_info = slack_client.users_info(user=user_id)
        user_data = user_info["user"]
        user_name = user_data.get("real_name") or user_data.get("display_name") or user_data.get("name", "Unknown User")
    except:
        user_name = f"User_{user_id[-4:]}"

    # Get AI response with context (use db_channel_id for database lookup)
    response, tokens_used = get_bot_response(text, user_id, bot_type, system_prompt, user_name, db_channel_id, thread_ts)

    # Save conversation to database with context (use db_channel_id for storage)
    save_conversation(user_id, user_name, text, response, bot_type, db_channel_id, thread_ts, message_ts, tokens_used)

    # Send to Slack (threaded ONLY for channels, not for DMs or group DMs)
    try:
        post_params = {
            "channel": channel_id,
            "text": response
        }

        # Only use threading for channels (C*), not for DMs (D*) or group DMs (G*)
        if channel_id.startswith('C') and thread_ts:
            post_params["thread_ts"] = thread_ts

        slack_client.chat_postMessage(**post_params)
        # TEMPORARY DEBUG LOGGING - TODO: REMOVE AFTER DIAGNOSIS
        print(f"[DEBUG] MESSAGE SENT: bot={bot_type}, channel={channel_id}, response_length={len(response)}")
    except Exception as e:
        # TEMPORARY DEBUG LOGGING - TODO: REMOVE AFTER DIAGNOSIS
        print(f"[DEBUG] SEND FAILED: bot={bot_type}, error={str(e)}")

@app.get("/")
async def health():
    return {"status": "ok"}

@app.get("/test-bots")
async def test_bots():
    """Test endpoint to verify both bot configurations"""
    results = {}

    # Test Duck bot
    try:
        duck_response = duck_client.auth_test()
        results["duck"] = {
            "status": "success",
            "bot_user_id": duck_response.get("user_id"),
            "bot_name": duck_response.get("user"),
            "team": duck_response.get("team"),
            "team_id": duck_response.get("team_id")
        }
    except Exception as e:
        results["duck"] = {
            "status": "error",
            "error": str(e)
        }

    # Test Goose bot
    try:
        goose_response = goose_client.auth_test()
        results["goose"] = {
            "status": "success",
            "bot_user_id": goose_response.get("user_id"),
            "bot_name": goose_response.get("user"),
            "team": goose_response.get("team"),
            "team_id": goose_response.get("team_id")
        }
    except Exception as e:
        results["goose"] = {
            "status": "error",
            "error": str(e)
        }

    return results

@app.post("/slack/events")
async def slack_events(request: Request):
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # Detect which bot this event is for
    bot_type = detect_bot_from_signature(body, timestamp, signature)
    if not bot_type:
        return {"error": "invalid signature"}, 401

    event_data = await request.json()

    # Handle URL verification
    if event_data.get("type") == "url_verification":
        return {"challenge": event_data.get("challenge")}

    # Handle message events
    if event_data.get("type") == "event_callback":
        event = event_data.get("event", {})

        # Event deduplication (bot-specific to allow both bots to respond to same event)
        event_id = event.get("client_msg_id") or event.get("ts")
        event_type = event.get("type")
        channel_id = event.get("channel")

        # TEMPORARY DEBUG LOGGING - TODO: REMOVE AFTER DIAGNOSIS
        print(f"[DEBUG] EVENT RECEIVED: bot={bot_type}, event_id={event_id}, event_type={event_type}, channel={channel_id}")

        bot_event_key = (event_id, bot_type, event_type)  # Combine event_id + bot_type + event_type
        if event_id and bot_event_key in processed_events:
            print(f"[DEBUG] SKIPPED (deduplicated): {bot_event_key}")
            return {"status": "ok"}
        if event_id:
            processed_events.add(bot_event_key)
            print(f"[DEBUG] PROCESSING: {bot_event_key}, processed_set_size={len(processed_events)}")
            if len(processed_events) > 1000:
                processed_events.clear()

        # Handle both regular messages and app mentions
        if (event_type == "message" or event_type == "app_mention") and not event.get("bot_id"):
            user_id = event.get("user")
            channel_id = event.get("channel")
            text = event.get("text", "")

            # Get the appropriate bot user ID
            bot_user_id = DUCK_USER_ID if bot_type == 'duck' else GOOSE_USER_ID

            # Check if we should respond to this event
            should_respond = should_respond_to_event(event, channel_id, bot_user_id)
            print(f"[DEBUG] should_respond={should_respond}, bot={bot_type}, user={user_id}, text='{text[:50]}...'")

            if should_respond:
                # Extract conversation context
                channel_id, db_channel_id, thread_ts, message_ts = get_conversation_context(event)

                print(f"[DEBUG] CALLING handle_message: bot={bot_type}, channel={channel_id}, db_channel={db_channel_id}")

                # Route to appropriate bot handler
                if bot_type == 'duck':
                    handle_message(
                        user_id, channel_id, text, 'duck',
                        duck_client, DUCK_PROMPT, "Quack!",
                        db_channel_id, thread_ts, message_ts
                    )
                elif bot_type == 'goose':
                    handle_message(
                        user_id, channel_id, text, 'goose',
                        goose_client, GOOSE_PROMPT, "Honk!",
                        db_channel_id, thread_ts, message_ts
                    )
            else:
                print(f"[DEBUG] NOT RESPONDING: should_respond=False for bot={bot_type}")

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)