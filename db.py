import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('conversations.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            user_name TEXT,
            message TEXT,
            response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add user_name column if it doesn't exist (for existing databases)
    try:
        conn.execute('ALTER TABLE conversations ADD COLUMN user_name TEXT')
    except:
        pass  # Column already exists
        
    conn.commit()
    conn.close()

def save_conversation(user_id: str, user_name: str, message: str, response: str):
    conn = sqlite3.connect('conversations.db')
    
    # Save new conversation
    conn.execute('INSERT INTO conversations (user_id, user_name, message, response) VALUES (?, ?, ?, ?)',
                (user_id, user_name, message, response))
    
    # Keep only last 100 conversations per user
    conn.execute('''
        DELETE FROM conversations 
        WHERE user_id = ? AND id NOT IN (
            SELECT id FROM conversations 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 100
        )
    ''', (user_id, user_id))
    
    conn.commit()
    conn.close()

def get_conversation_history(user_id: str) -> list:
    conn = sqlite3.connect('conversations.db')
    cursor = conn.execute('''
        SELECT message, response FROM conversations 
        WHERE user_id = ? 
        ORDER BY timestamp DESC
        LIMIT 30
    ''', (user_id,))
    
    history = cursor.fetchall()
    conn.close()
    # Return in chronological order (oldest first)
    return history[::-1]