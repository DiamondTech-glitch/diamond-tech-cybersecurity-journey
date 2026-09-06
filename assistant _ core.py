"""
Shared core: database, memory, conversations, settings, and Claude calls.
Used by both bot.py (Telegram) and app.py (web).
"""

import os
import sqlite3
from datetime import date

from anthropic import Anthropic

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
DB_PATH = os.environ.get("DB_PATH", "assistant.db")
MODEL = "claude-sonnet-4-6"
DEFAULT_ASSISTANT_NAME = "Nova"

client = Anthropic(api_key=ANTHROPIC_API_KEY)

BASE_SYSTEM_PROMPT = """You are {name}, Diamond's personal AI study and build assistant.

Diamond is a university cybersecurity student and freelance web/marketing
operator (Diamond Web) who also builds SaaS products. Goals for these chats:
- Help him learn cybersecurity concepts daily — explain clearly, quiz him,
  point out what to review next.
- Help with coding questions and debugging across his projects.
- Help think through automation ideas.

Be direct and practical. Skip generic disclaimers. When explaining a
concept, check understanding with a short question rather than lecturing.
If recent progress notes are provided below, build on them instead of
repeating material already covered."""


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            title TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            day TEXT,
            note TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            user_id TEXT PRIMARY KEY,
            assistant_name TEXT
        )
    """)
    return conn


def create_conversation(user_id: str, title: str) -> int:
    title = (title[:40] + "…") if len(title) > 40 else title
    conn = db()
    cur = conn.execute(
        "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
        (user_id, title),
    )
    conn.commit()
    conv_id = cur.lastrowid
    conn.close()
    return conv_id


def list_conversations(user_id: str):
    conn = db()
    rows = conn.execute(
        "SELECT id, title, created_at FROM conversations "
        "WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "created_at": r[2]} for r in rows]


def delete_conversation(user_id: str, conversation_id: int):
    conn = db()
    conn.execute(
        "DELETE FROM messages WHERE conversation_id = ? AND conversation_id IN "
        "(SELECT id FROM conversations WHERE user_id = ?)",
        (conversation_id, user_id),
    )
    conn.execute(
        "DELETE FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id),
    )
    conn.commit()
    conn.close()


def clear_all_conversations(user_id: str):
    conn = db()
    conn.execute(
        "DELETE FROM messages WHERE conversation_id IN "
        "(SELECT id FROM conversations WHERE user_id = ?)",
        (user_id,),
    )
    conn.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def save_message(conversation_id: int, role: str, content: str):
    conn = db()
    conn.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conversation_id, role, content),
    )
    conn.commit()
    conn.close()


def recent_history(conversation_id: int, limit: int = 20):
    conn = db()
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE conversation_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (conversation_id, limit),
    ).fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in reversed(rows)]


def add_progress_note(user_id: str, note: str):
    conn = db()
    conn.execute(
        "INSERT INTO progress (user_id, day, note) VALUES (?, ?, ?)",
        (user_id, date.today().isoformat(), note),
    )
    conn.commit()
    conn.close()


def recent_progress(user_id: str, days: int = 7):
    conn = db()
    rows = conn.execute(
        "SELECT day, note FROM progress WHERE user_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (user_id, days),
    ).fetchall()
    conn.close()
    return rows


def clear_progress(user_id: str):
    conn = db()
    conn.execute("DELETE FROM progress WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_assistant_name(user_id: str) -> str:
    conn = db()
    row = conn.execute(
        "SELECT assistant_name FROM settings WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row[0] if row and row[0] else DEFAULT_ASSISTANT_NAME


def set_assistant_name(user_id: str, name: str):
    name = name.strip()[:30] or DEFAULT_ASSISTANT_NAME
    conn = db()
    conn.execute(
        "INSERT INTO settings (user_id, assistant_name) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET assistant_name = excluded.assistant_name",
        (user_id, name),
    )
    conn.commit()
    conn.close()
    return name


def ask_claude(user_id: str, conversation_id: int, user_text: str) -> str:
    history = recent_history(conversation_id)
    progress = recent_progress(user_id)
    name = get_assistant_name(user_id)

    system = BASE_SYSTEM_PROMPT.format(name=name)
    if progress:
        notes = "\n".join(f"- {day}: {note}" for day, note in progress)
        system += f"\n\nRecent progress notes:\n{notes}"

    messages = history + [{"role": "user", "content": user_text}]

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    return response.content[0].text