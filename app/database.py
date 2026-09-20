from pathlib import Path
from datetime import datetime, timezone
from contextlib import closing
import json
import sqlite3
import uuid

from .config import ROOT, settings

DATA = ROOT / "app" / "data"

def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def connect() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(settings.db_path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA journal_mode=WAL")
    return db

def init_db() -> None:
    with closing(connect()) as db, db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS conversations(
            id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, channel TEXT NOT NULL,
            subject TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'Não identificado',
            team TEXT NOT NULL DEFAULT 'Atendimento', priority TEXT NOT NULL DEFAULT 'P3',
            score REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'bot_active',
            assigned_to TEXT, route TEXT NOT NULL DEFAULT 'CHATBOT',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL,
            author_type TEXT NOT NULL, author_id TEXT, author_name TEXT NOT NULL,
            text TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL,
            type TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
        """)
        count = db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        if count == 0:
            seed(db)

def seed(db: sqlite3.Connection) -> None:
    data = json.loads((DATA / "seed_conversations.json").read_text(encoding="utf-8"))
    stamp = now_iso()
    for item in data["conversations"]:
        db.execute("""INSERT INTO conversations
            (id,customer_id,channel,subject,category,team,priority,score,status,route,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (
            item["id"], item["customer_id"], item["channel"], item["subject"], item["subject"],
            item["team"], item["priority"], item["score"], item["status"],
            "HUMANO" if "human" in item["status"] else "CHATBOT", stamp, stamp
        ))
        for msg in item["messages"]:
            db.execute("INSERT INTO messages(conversation_id,author_type,author_name,text,created_at) VALUES(?,?,?,?,?)",
                       (item["id"], msg["author_type"], msg["author_name"], msg["text"], stamp))
        db.execute("INSERT INTO events(conversation_id,type,detail,created_at) VALUES(?,?,?,?)",
                   (item["id"], "seeded", "Conversa fictícia carregada", stamp))

def reset_db() -> None:
    with closing(connect()) as db, db:
        db.execute("DELETE FROM messages")
        db.execute("DELETE FROM events")
        db.execute("DELETE FROM conversations")
        seed(db)

def new_id() -> str:
    return "T-" + uuid.uuid4().hex[:6].upper()

def create_conversation(customer_id: str, channel: str, text: str, customer_name: str) -> str:
    ticket_id, stamp = new_id(), now_iso()
    with closing(connect()) as db, db:
        db.execute("""INSERT INTO conversations
            (id,customer_id,channel,subject,created_at,updated_at) VALUES(?,?,?,?,?,?)""",
            (ticket_id, customer_id, channel, "Novo atendimento", stamp, stamp))
        db.execute("INSERT INTO messages(conversation_id,author_type,author_id,author_name,text,created_at) VALUES(?,?,?,?,?,?)",
                   (ticket_id, "customer", customer_id, customer_name, text, stamp))
        db.execute("INSERT INTO events(conversation_id,type,detail,created_at) VALUES(?,?,?,?)",
                   (ticket_id, "opened", f"Entrada pelo canal {channel}", stamp))
    return ticket_id

def add_message(ticket_id: str, author_type: str, author_id: str, author_name: str, text: str) -> None:
    stamp = now_iso()
    with closing(connect()) as db, db:
        db.execute("INSERT INTO messages(conversation_id,author_type,author_id,author_name,text,created_at) VALUES(?,?,?,?,?,?)",
                   (ticket_id, author_type, author_id, author_name, text, stamp))
        db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (stamp, ticket_id))

def add_event(ticket_id: str, event_type: str, detail: str) -> None:
    with closing(connect()) as db, db:
        db.execute("INSERT INTO events(conversation_id,type,detail,created_at) VALUES(?,?,?,?)",
                   (ticket_id, event_type, detail, now_iso()))

def update_conversation(ticket_id: str, **fields) -> None:
    allowed = {"subject", "category", "team", "priority", "score", "status", "assigned_to", "route"}
    clean = {k: v for k, v in fields.items() if k in allowed}
    if not clean:
        return
    clean["updated_at"] = now_iso()
    sql = ",".join(f"{key}=?" for key in clean)
    with closing(connect()) as db, db:
        db.execute(f"UPDATE conversations SET {sql} WHERE id=?", (*clean.values(), ticket_id))

def conversation(ticket_id: str):
    with closing(connect()) as db, db:
        row = db.execute("SELECT * FROM conversations WHERE id=?", (ticket_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["messages"] = [dict(x) for x in db.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY id", (ticket_id,))]
        item["events"] = [dict(x) for x in db.execute("SELECT * FROM events WHERE conversation_id=? ORDER BY id", (ticket_id,))]
        return item

def conversations() -> list[dict]:
    with closing(connect()) as db, db:
        return [dict(x) for x in db.execute("SELECT * FROM conversations ORDER BY CASE priority WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END, score DESC, updated_at ASC")]
