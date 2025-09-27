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
    thread_id = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now())

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./conversations.db")

# Handle Railway's Postgres URL format
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_conversation(user_id: str, user_name: str, message: str, response: str):
    db = SessionLocal()
    try:
        # Save new conversation
        conversation = Conversation(
            user_id=user_id,
            user_name=user_name,
            thread_id=user_id,  # Use user_id as thread_id for DMs
            message=message,
            response=response
        )
        db.add(conversation)
        db.commit()

        # Keep only last 100 conversations per user
        excess_conversations = db.query(Conversation)\
            .filter(Conversation.user_id == user_id)\
            .order_by(Conversation.timestamp.desc())\
            .offset(100)\
            .all()

        for conv in excess_conversations:
            db.delete(conv)

        db.commit()
    finally:
        db.close()

def get_conversation_history(user_id: str) -> list:
    db = SessionLocal()
    try:
        conversations = db.query(Conversation.message, Conversation.response)\
            .filter(Conversation.user_id == user_id)\
            .order_by(Conversation.timestamp.desc())\
            .limit(30)\
            .all()

        # Return in chronological order (oldest first)
        return [(conv.message, conv.response) for conv in reversed(conversations)]
    finally:
        db.close()

def reset_conversation(user_id: str) -> int:
    db = SessionLocal()
    try:
        deleted_count = db.query(Conversation)\
            .filter(Conversation.user_id == user_id)\
            .count()

        db.query(Conversation)\
            .filter(Conversation.user_id == user_id)\
            .delete()

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