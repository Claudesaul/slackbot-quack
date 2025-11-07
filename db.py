import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()

class Conversation(Base):
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    user_name = Column(String)
    thread_id = Column(String, nullable=False)  # Keep for backward compatibility
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    bot_type = Column(String, nullable=False, default='duck')
    timestamp = Column(DateTime, default=func.now())

    # New columns for multi-context support (DMs, channels, group DMs)
    channel_id = Column(String)  # Slack channel ID (D*, C*, G*)
    thread_ts = Column(String)   # Slack thread timestamp
    message_ts = Column(String)  # Slack message timestamp
    tokens_used = Column(Integer, default=0)  # Token usage tracking

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./conversations.db")

# Handle Railway's Postgres URL format
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

    # Migration: Add missing columns if they don't exist
    from sqlalchemy import text, inspect
    inspector = inspect(engine)

    # Check if conversations table exists
    if 'conversations' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('conversations')]

        # Add bot_type column if missing
        if 'bot_type' not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE conversations ADD COLUMN bot_type VARCHAR DEFAULT 'duck'"))
                conn.commit()
                print("Migration: Added bot_type column to conversations table")

        # Add new context columns if missing
        with engine.connect() as conn:
            if 'channel_id' not in columns:
                conn.execute(text("ALTER TABLE conversations ADD COLUMN channel_id VARCHAR"))
                conn.commit()
                print("Migration: Added channel_id column to conversations table")

                # Backfill: Set channel_id = user_id for old DM conversations
                # This ensures backward compatibility with existing data
                conn.execute(text(
                    "UPDATE conversations SET channel_id = user_id WHERE channel_id IS NULL"
                ))
                conn.commit()
                print("Migration: Backfilled channel_id for existing conversations")

            if 'thread_ts' not in columns:
                conn.execute(text("ALTER TABLE conversations ADD COLUMN thread_ts VARCHAR"))
                conn.commit()
                print("Migration: Added thread_ts column to conversations table")

            if 'message_ts' not in columns:
                conn.execute(text("ALTER TABLE conversations ADD COLUMN message_ts VARCHAR"))
                conn.commit()
                print("Migration: Added message_ts column to conversations table")

            if 'tokens_used' not in columns:
                conn.execute(text("ALTER TABLE conversations ADD COLUMN tokens_used INTEGER DEFAULT 0"))
                conn.commit()
                print("Migration: Added tokens_used column to conversations table")

                # Backfill: Estimate tokens for existing conversations
                # Using formula: (message_length + response_length) / 4
                conn.execute(text("""
                    UPDATE conversations
                    SET tokens_used = (LENGTH(message) + LENGTH(response)) / 4
                    WHERE tokens_used = 0 OR tokens_used IS NULL
                """))
                conn.commit()
                print("Migration: Estimated tokens for existing conversations")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_conversation(
    user_id: str,
    user_name: str,
    message: str,
    response: str,
    bot_type: str = 'duck',
    channel_id: str = None,
    thread_ts: str = None,
    message_ts: str = None,
    tokens_used: int = 0
):
    """
    Save a conversation to the database.

    Args:
        user_id: Slack user ID
        user_name: User's display name
        message: User's message
        response: Bot's response
        bot_type: 'duck' or 'goose'
        channel_id: Slack channel ID (D* for DM, C* for channel, G* for group DM)
        thread_ts: Slack thread timestamp (None for non-threaded)
        message_ts: Slack message timestamp
        tokens_used: Number of tokens used in this conversation
    """
    db = SessionLocal()
    try:
        # Save new conversation
        conversation = Conversation(
            user_id=user_id,
            user_name=user_name,
            thread_id=thread_ts or user_id,  # Use thread_ts if available, else user_id (backward compat)
            message=message,
            response=response,
            bot_type=bot_type,
            channel_id=channel_id or user_id,  # Fallback to user_id for old DMs
            thread_ts=thread_ts,
            message_ts=message_ts,
            tokens_used=tokens_used
        )
        db.add(conversation)
        db.commit()

        # Keep only last 100 conversations per user per bot
        excess_conversations = db.query(Conversation)\
            .filter(Conversation.user_id == user_id)\
            .filter(Conversation.bot_type == bot_type)\
            .order_by(Conversation.timestamp.desc())\
            .offset(100)\
            .all()

        for conv in excess_conversations:
            db.delete(conv)

        db.commit()
    finally:
        db.close()

def get_conversation_history(
    user_id: str,
    bot_type: str = 'duck',
    channel_id: str = None,
    thread_ts: str = None
) -> list:
    """
    Get conversation history for a specific context.

    Args:
        user_id: Slack user ID
        bot_type: 'duck' or 'goose'
        channel_id: Slack channel ID (optional, for context filtering)
        thread_ts: Slack thread timestamp (optional, for thread isolation)

    Returns:
        List of (message, response) tuples in chronological order
    """
    db = SessionLocal()
    try:
        query = db.query(Conversation.message, Conversation.response)\
            .filter(Conversation.user_id == user_id)\
            .filter(Conversation.bot_type == bot_type)

        # Filter by context if provided
        if channel_id:
            query = query.filter(Conversation.channel_id == channel_id)

            if thread_ts:  # Channel thread - only this specific thread
                query = query.filter(Conversation.thread_ts == thread_ts)
            else:  # DM or group DM (non-threaded)
                query = query.filter(Conversation.thread_ts.is_(None))

        conversations = query.order_by(Conversation.timestamp.desc()).limit(30).all()

        # Return in chronological order (oldest first)
        return [(conv.message, conv.response) for conv in reversed(conversations)]
    finally:
        db.close()

def reset_conversation(
    user_id: str,
    bot_type: str = 'duck',
    channel_id: str = None,
    thread_ts: str = None
) -> int:
    """
    Reset conversation history for a specific context.

    Args:
        user_id: Slack user ID
        bot_type: 'duck' or 'goose'
        channel_id: Slack channel ID (optional - if provided, only clears that context)
        thread_ts: Slack thread timestamp (optional - for thread-specific clearing)

    Returns:
        Number of conversations deleted
    """
    db = SessionLocal()
    try:
        query = db.query(Conversation)\
            .filter(Conversation.user_id == user_id)\
            .filter(Conversation.bot_type == bot_type)

        # Filter by context if provided
        if channel_id:
            query = query.filter(Conversation.channel_id == channel_id)

            if thread_ts:
                query = query.filter(Conversation.thread_ts == thread_ts)
            else:
                # If no thread_ts, clear non-threaded messages in this channel
                query = query.filter(Conversation.thread_ts.is_(None))

        deleted_count = query.count()
        query.delete()

        db.commit()
        return deleted_count
    finally:
        db.close()

def delete_conversations_by_user_name(user_name: str) -> int:
    db = SessionLocal()
    try:
        deleted_count = db.query(Conversation)\
            .filter(Conversation.user_name == user_name)\
            .count()

        db.query(Conversation)\
            .filter(Conversation.user_name == user_name)\
            .delete()

        db.commit()
        return deleted_count
    finally:
        db.close()

def get_bot_stats(bot_type: str) -> dict:
    """
    Get statistics for a specific bot.

    Args:
        bot_type: 'duck' or 'goose'

    Returns:
        Dictionary with total_tokens, total_messages, unique_users, earliest_date, latest_date
    """
    db = SessionLocal()
    try:
        from sqlalchemy import func as sql_func

        # Total tokens
        total_tokens = db.query(sql_func.sum(Conversation.tokens_used))\
            .filter(Conversation.bot_type == bot_type)\
            .scalar() or 0

        # Total messages
        total_messages = db.query(Conversation)\
            .filter(Conversation.bot_type == bot_type)\
            .count()

        # Unique users
        unique_users = db.query(sql_func.count(sql_func.distinct(Conversation.user_id)))\
            .filter(Conversation.bot_type == bot_type)\
            .scalar() or 0

        # Date range
        earliest = db.query(sql_func.min(Conversation.timestamp))\
            .filter(Conversation.bot_type == bot_type)\
            .scalar()

        latest = db.query(sql_func.max(Conversation.timestamp))\
            .filter(Conversation.bot_type == bot_type)\
            .scalar()

        return {
            "total_tokens": int(total_tokens),
            "total_messages": total_messages,
            "unique_users": unique_users,
            "earliest_date": earliest,
            "latest_date": latest
        }
    finally:
        db.close()

def get_recent_queries(bot_type: str, limit: int = 10) -> list:
    """
    Get recent user queries for a specific bot.

    Args:
        bot_type: 'duck' or 'goose'
        limit: Number of queries to return (max 100)

    Returns:
        List of tuples: (timestamp, user_name, message)
    """
    db = SessionLocal()
    try:
        # Cap limit at 100
        limit = min(limit, 100)

        queries = db.query(
            Conversation.timestamp,
            Conversation.user_name,
            Conversation.message
        )\
            .filter(Conversation.bot_type == bot_type)\
            .order_by(Conversation.timestamp.desc())\
            .limit(limit)\
            .all()

        return [(q.timestamp, q.user_name, q.message) for q in queries]
    finally:
        db.close()