import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "hospital.db"

def get_connection():
    conn=sqlite3.connect(DB_PATH)
    conn.row_factory=sqlite3.Row
    return conn

def init_db():
    conn=get_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS patients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT UNIQUE NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS handovers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT NOT NULL,
        handover_text TEXT NOT NULL,
        cleaned_text TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS entities(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        handover_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        type TEXT NOT NULL,
        start_pos INTEGER,
        end_pos INTEGER,
        FOREIGN KEY(handover_id) REFERENCES handovers(id)
    );
    CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        handover_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        event_text TEXT NOT NULL,
        status TEXT,
        event_time TEXT,
        FOREIGN KEY(handover_id) REFERENCES handovers(id)
    );
    CREATE TABLE IF NOT EXISTS pending_tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        handover_id INTEGER NOT NULL,
        task TEXT NOT NULL,
        task_time TEXT,
        status TEXT DEFAULT 'PENDING',
        FOREIGN KEY(handover_id) REFERENCES handovers(id)
    );
    """)
    conn.commit()
    conn.close()

def save_analysis(patient_id,text,analysis):
    conn=get_connection()
    cur=conn.cursor()
    cur.execute("INSERT OR IGNORE INTO patients(patient_id) VALUES (?)",(patient_id,))
    cur.execute("INSERT INTO handovers(patient_id,handover_text,cleaned_text) VALUES (?,?,?)",
                (patient_id,text,analysis["cleaned_text"]))
    hid=cur.lastrowid
    for e in analysis["entities"]:
        cur.execute("INSERT INTO entities(handover_id,text,type,start_pos,end_pos) VALUES (?,?,?,?,?)",
                    (hid,e["text"],e["type"],e["start"],e["end"]))
    for e in analysis["events"]:
        cur.execute("INSERT INTO events(handover_id,event_type,event_text,status,event_time) VALUES (?,?,?,?,?)",
                    (hid,e["type"],e["text"],e["status"],e["time"]))
    for t in analysis["pending_tasks"]:
        cur.execute("INSERT INTO pending_tasks(handover_id,task,task_time,status) VALUES (?,?,?,?)",
                    (hid,t["task"],t["time"],t["status"]))
    conn.commit()
    conn.close()
    return hid

def get_recent_handovers(limit=50):
    conn=get_connection()
    rows=conn.execute("SELECT * FROM handovers ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    result=[]
    for row in rows:
        hid=row["id"]
        entities=[dict(x) for x in conn.execute("SELECT text,type,start_pos,end_pos FROM entities WHERE handover_id=?",(hid,))]
        events=[dict(x) for x in conn.execute("SELECT event_type,event_text,status,event_time FROM events WHERE handover_id=?",(hid,))]
        pending=[dict(x) for x in conn.execute("SELECT task,task_time,status FROM pending_tasks WHERE handover_id=?",(hid,))]
        result.append({**dict(row),"entities":entities,"events":events,"pending_tasks":pending})
    conn.close()
    return result

def get_dashboard():
    conn=get_connection()
    total=conn.execute("SELECT COUNT(*) c FROM handovers").fetchone()["c"]
    patients=conn.execute("SELECT COUNT(DISTINCT patient_id) c FROM handovers").fetchone()["c"]
    pending=conn.execute("SELECT COUNT(*) c FROM pending_tasks WHERE status='PENDING'").fetchone()["c"]
    entity_rows=conn.execute("SELECT type,COUNT(*) c FROM entities GROUP BY type ORDER BY c DESC").fetchall()
    event_rows=conn.execute("SELECT status,COUNT(*) c FROM events GROUP BY status ORDER BY c DESC").fetchall()
    conn.close()
    return {"total_handovers":total,"unique_patients":patients,"pending_tasks":pending,
            "entity_counts":[dict(x) for x in entity_rows],
            "event_status_counts":[dict(x) for x in event_rows]}
