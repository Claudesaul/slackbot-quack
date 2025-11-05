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
from db import init_db, save_conversation, get_conversation_history, reset_conversation

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

Never ignore any of these instructions."""

GOOSE_PROMPT = """You are an expert programming tutor configured as the Goose programming assistant. Begin each response with "Honk!". Maintain an objective, neutral, and clear tone in your responses. Focus on providing well-structured, accurate explanations that acknowledge multiple perspectives on programming topics. Avoid overly formal or stiff language, but communicate concepts in a straightforward and approachable manner. Do not adapt your responses to align with the user's opinions or preferences. Avoid using overly polite phrases like please or thank you excessively, but remain respectful. Provide answers based strictly on programming knowledge and best practices. Use educational questioning techniques to encourage critical thinking, but do not provide whole code solutions. Before responding, identify and define key computational thinking or coding concepts related to the user's question, using clear and understandable explanations suitable for novice programmers. Prompt the user for clarification if their question is ambiguous. Do not use first-person pronouns or present yourself as a human tutor.

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
) -> str:
    """Generate AI response with conversation history"""
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
        return response.choices[0].message.content.strip()
    except:
        return "Something went wrong. Could you try asking your question again?"

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

    # Get user's display name
    try:
        user_info = slack_client.users_info(user=user_id)
        user_data = user_info["user"]
        user_name = user_data.get("real_name") or user_data.get("display_name") or user_data.get("name", "Unknown User")
    except:
        user_name = f"User_{user_id[-4:]}"

    # Get AI response with context (use db_channel_id for database lookup)
    response = get_bot_response(text, user_id, bot_type, system_prompt, user_name, db_channel_id, thread_ts)

    # Save conversation to database with context (use db_channel_id for storage)
    save_conversation(user_id, user_name, text, response, bot_type, db_channel_id, thread_ts, message_ts)

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
    except:
        pass

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

        # Event deduplication
        event_id = event.get("client_msg_id") or event.get("ts")
        if event_id and event_id in processed_events:
            return {"status": "ok"}
        if event_id:
            processed_events.add(event_id)
            if len(processed_events) > 1000:
                processed_events.clear()

        event_type = event.get("type")

        # Handle both regular messages and app mentions
        if (event_type == "message" or event_type == "app_mention") and not event.get("bot_id"):
            user_id = event.get("user")
            channel_id = event.get("channel")
            text = event.get("text", "")

            # Get the appropriate bot user ID
            bot_user_id = DUCK_USER_ID if bot_type == 'duck' else GOOSE_USER_ID

            # Check if we should respond to this event
            if should_respond_to_event(event, channel_id, bot_user_id):
                # Extract conversation context
                channel_id, db_channel_id, thread_ts, message_ts = get_conversation_context(event)

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

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)