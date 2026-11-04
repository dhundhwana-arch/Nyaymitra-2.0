"""
JARVIS AI Justice Access - Local SQLite Database Module
Developer: Divyesh Bambhaniya
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "justice_access.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Queries / Interactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS query_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_query TEXT NOT NULL,
        language TEXT DEFAULT 'gu',
        category TEXT,
        authority_recommended TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Draft Applications table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS saved_drafts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        applicant_name TEXT,
        phone TEXT,
        authority TEXT,
        subject TEXT,
        body TEXT,
        prayer TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully at:", DB_PATH)

def log_query(user_query: str, language: str, category: str, authority: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO query_logs (user_query, language, category, authority_recommended) VALUES (?, ?, ?, ?)",
            (user_query, language, category, authority)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("Database error logging query:", e)

def save_application_draft(data: dict):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO saved_drafts (applicant_name, phone, authority, subject, body, prayer) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (data.get("applicant_name"), data.get("phone"), data.get("authority"), 
             data.get("subject"), data.get("body"), data.get("prayer"))
        )
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id
    except Exception as e:
        print("Database error saving draft:", e)
        return None

if __name__ == "__main__":
    init_db()
