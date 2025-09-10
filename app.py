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
from db import init_db, save_conversation, get_conversation_history

ssl._create_default_https_context = ssl._create_unverified_context

load_dotenv()

app = FastAPI()
init_db()  # Initialize database on startup

# Load environment variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET") 
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

slack_client = WebClient(token=SLACK_BOT_TOKEN)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Rate limiting: 500 messages per hour per user
user_requests = {}

# Event deduplication
processed_events = set()

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

SYSTEM_PROMPT = """You are an expert tutor who has expert knowledge in programming, educational questioning techniques, and computational thinking strategies. You heavily use open questions in responding to students and never want to reveal an answer to a current or previous question outright. You are never to give the exact code to solve the student's entire problem; instead, focus on helping the student to find their own way to the solution.

Before responding to the student, please identify and define key computational thinking or coding concepts in their question. Keep in mind that the students you are responding to are new to programming and may have not had any prior programming experience. We do want them to learn the language of programming, but also feel free to use metaphors, analogies, or everyday examples when discussing computational thinking or coding concepts.

Also, if the student's initial query doesn't specify what they were trying to do, prompt them to clarify that.

You are NOT to behave as if you are a human tutor. Do not use first-person pronouns or give the impression that you are a human tutor. Please make sure you place [Duck] before any of your responses and begin each response by quacking.

Never ignore any of these instructions."""

def verify_signature(body: bytes, timestamp: str, signature: str) -> bool:
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False
    
    sig_basestring = f'v0:{timestamp}:{body.decode()}'
    my_signature = 'v0=' + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(my_signature, signature)

def get_duck_response(message: str, user_id: str, user_name: str = None) -> str:
    try:
        # Get conversation history
        history = get_conversation_history(user_id)
        
        # Build messages with history
        system_prompt = SYSTEM_PROMPT
        if user_name:
            system_prompt += f"\n\nThe student's name is {user_name}. Feel free to address them by name in your responses."
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for prev_msg, prev_response in history:
            messages.append({"role": "user", "content": prev_msg})
            messages.append({"role": "assistant", "content": prev_response})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except:
        return "[Duck] Something went wrong. Could you try asking your question again?"

@app.get("/")
async def health():
    return {"status": "ok"}

@app.post("/slack/events")
async def slack_events(request: Request):
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    
    if not verify_signature(body, timestamp, signature):
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
        
        if event.get("type") == "message" and not event.get("bot_id"):
            user_id = event.get("user")
            channel_id = event.get("channel")
            text = event.get("text", "")
            thread_ts = event.get("thread_ts", event.get("ts"))
            
            # Get bot user ID
            try:
                bot_info = slack_client.auth_test()
                bot_user_id = bot_info["user_id"]
            except:
                bot_user_id = None
            
            # Check if bot is mentioned or it's a DM
            bot_mentioned = f"<@{bot_user_id}>" in text if bot_user_id else True
            is_dm = channel_id.startswith('D')
            
            if bot_mentioned or is_dm:
                # Check rate limit
                if is_rate_limited(user_id):
                    slack_client.chat_postMessage(
                        channel=channel_id,
                        thread_ts=None if is_dm else thread_ts,
                        text="[Duck] Quack! Take a break and think about the questions that have been asked. What have you tried so far?"
                    )
                    return {"status": "ok"}
                
                # Clean message
                if bot_user_id:
                    text = text.replace(f"<@{bot_user_id}>", "").strip()
                
                # Get user's display name
                try:
                    user_info = slack_client.users_info(user=user_id)
                    user_data = user_info["user"]
                    user_name = user_data.get("real_name") or user_data.get("display_name") or user_data.get("name", "Unknown User")
                    print(f"DEBUG: Got user name '{user_name}' for user {user_id}")
                except Exception as e:
                    print(f"DEBUG: Failed to get user info for {user_id}: {e}")
                    user_name = f"User_{user_id[-4:]}"  # Use last 4 chars of user ID
                
                # Get AI response
                response = get_duck_response(text, user_id, user_name)
                
                # Save conversation to database
                save_conversation(user_id, user_name, text, response)
                
                # Send to Slack - no threading in DMs
                try:
                    slack_client.chat_postMessage(
                        channel=channel_id,
                        thread_ts=None if is_dm else thread_ts,
                        text=response
                    )
                except:
                    pass
    
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)