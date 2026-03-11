import sqlite3
from typing import Optional, List, Tuple

def get_db_connection(db_name: str):
    return sqlite3.connect(db_name)

def init_users_db():
    with sqlite3.connect("users.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def init_chats_db():
    with sqlite3.connect("chats.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS verified_chats (
                chat_id INTEGER PRIMARY KEY,
                chat_title TEXT,
                verified BOOLEAN NOT NULL DEFAULT 1,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def init_sessions_db():
    with sqlite3.connect("sessions.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                user_id INTEGER,
                session_type TEXT,
                message_id INTEGER,
                PRIMARY KEY (user_id, session_type)
            )
        """)
        conn.commit()

def add_user(user_id: int, first_name: str, username: str = None) -> None:
    with sqlite3.connect("users.db") as conn:
        conn.execute("""
            INSERT OR REPLACE INTO users (user_id, first_name, username, last_activity)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, first_name, username))
        conn.commit()

def update_user_activity(user_id: int) -> None:
    with sqlite3.connect("users.db") as conn:
        conn.execute("""
            UPDATE users SET last_activity = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (user_id,))
        conn.commit()

def get_all_users() -> List[Tuple[int, str, str]]:
    with sqlite3.connect("users.db") as conn:
        result = conn.execute(
            "SELECT user_id, first_name, username FROM users"
        ).fetchall()
        return result

def add_verified_chat(chat_id: int, chat_title: str) -> None:
    with sqlite3.connect("chats.db") as conn:
        conn.execute("""
            INSERT OR IGNORE INTO verified_chats (chat_id, chat_title, verified)
            VALUES (?, ?, 1)
        """, (chat_id, chat_title))
        conn.commit()

def remove_verified_chat(chat_id: int) -> None:
    with sqlite3.connect("chats.db") as conn:
        conn.execute("""
            UPDATE verified_chats SET verified = 0
            WHERE chat_id = ?
        """, (chat_id,))
        conn.commit()

def check_chat_verified(chat_id: int) -> bool:
    if chat_id > 0:
        return True
    with sqlite3.connect("chats.db") as conn:
        result = conn.execute(
            "SELECT verified FROM verified_chats WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        return result is not None and result[0] == 1

def get_all_verified_chats() -> List[Tuple[int, str]]:
    with sqlite3.connect("chats.db") as conn:
        result = conn.execute(
            "SELECT chat_id, chat_title FROM verified_chats WHERE verified = 1"
        ).fetchall()
        return result

def save_session(user_id: int, session_type: str, message_id: int) -> None:
    with sqlite3.connect("sessions.db") as conn:
        conn.execute("""
            INSERT OR REPLACE INTO user_sessions (user_id, session_type, message_id)
            VALUES (?, ?, ?)
        """, (user_id, session_type, message_id))
        conn.commit()

def get_session(user_id: int, session_type: str) -> Optional[int]:
    with sqlite3.connect("sessions.db") as conn:
        result = conn.execute(
            "SELECT message_id FROM user_sessions WHERE user_id = ? AND session_type = ?",
            (user_id, session_type)
        ).fetchone()
        return result[0] if result else None

def check_session_access(user_id: int, message_id: int, session_type: str) -> bool:
    saved = get_session(user_id, session_type)
    return saved == message_id