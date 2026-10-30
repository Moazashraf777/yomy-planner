from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import datetime, date
from pathlib import Path

app = Flask(__name__)
DB_PATH = Path(__file__).with_name("planner.db")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS lectures (
            id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT NOT NULL,
            lecturer TEXT DEFAULT '', day TEXT NOT NULL, start_time TEXT NOT NULL,
            location TEXT DEFAULT '', remind INTEGER DEFAULT 15)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
            amount REAL NOT NULL, category TEXT NOT NULL, spent_on TEXT NOT NULL,
            note TEXT DEFAULT '')""")
        conn.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            event_at TEXT NOT NULL, category TEXT DEFAULT 'شخصي',
            remind INTEGER DEFAULT 15, note TEXT DEFAULT '', done INTEGER DEFAULT 0)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT NOT NULL)""")
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('budget','0')")

@app.route("/")
def index():
    with db() as conn:
        lectures = conn.execute("SELECT * FROM lectures ORDER BY CASE day WHEN 'السبت' THEN 1 WHEN 'الأحد' THEN 2 WHEN 'الإثنين' THEN 3 WHEN 'الثلاثاء' THEN 4 WHEN 'الأربعاء' THEN 5 WHEN 'الخميس' THEN 6 ELSE 7 END, start_time").fetchall()
        expenses = conn.execute("SELECT * FROM expenses ORDER BY spent_on DESC, id DESC LIMIT 8").fetchall()
        events = conn.execute("SELECT * FROM events WHERE done=0 ORDER BY event_at LIMIT 10").fetchall()
        total = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE kind='مصروف' AND substr(spent_on,1,7)=?", (date.today().strftime("%Y-%m"),)).fetchone()[0]
        income = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE kind='دخل' AND substr(spent_on,1,7)=?", (date.today().strftime("%Y-%m"),)).fetchone()[0]
        budget = conn.execute("SELECT value FROM settings WHERE key='budget'").fetchone()["value"]
        all_events = conn.execute("SELECT id,title,event_at,remind,category FROM events WHERE done=0").fetchall()
    return render_template("index.html", lectures=lectures, expenses=expenses, events=events,
                           total=total, income=income, budget=float(budget or 0), reminders=[dict(x) for x in all_events],
                           today=date.today().isoformat())

@app.post("/lecture/add")
def add_lecture():
    f=request.form
    with db() as conn:
        conn.execute("INSERT INTO lectures(subject,lecturer,day,start_time,location,remind) VALUES(?,?,?,?,?,?)",
                     (f["subject"].strip(),f.get("lecturer","").strip(),f["day"],f["start_time"],f.get("location","").strip(),int(f.get("remind",15))))
    return redirect(url_for("index")+"#lectures")

@app.post("/lecture/delete/<int:item_id>")
def delete_lecture(item_id):
    with db() as conn: conn.execute("DELETE FROM lectures WHERE id=?",(item_id,))
    return redirect(url_for("index")+"#lectures")

@app.post("/expense/add")
def add_expense():
    f=request.form
    with db() as conn:
        conn.execute("INSERT INTO expenses(kind,amount,category,spent_on,note) VALUES(?,?,?,?,?)",
                     (f["kind"],float(f["amount"]),f["category"],f["spent_on"],f.get("note","").strip()))
    return redirect(url_for("index")+"#expenses")

@app.post("/expense/delete/<int:item_id>")
def delete_expense(item_id):
    with db() as conn: conn.execute("DELETE FROM expenses WHERE id=?",(item_id,))
    return redirect(url_for("index")+"#expenses")

@app.post("/event/add")
def add_event():
    f=request.form
    with db() as conn:
        conn.execute("INSERT INTO events(title,event_at,category,remind,note) VALUES(?,?,?,?,?)",
                     (f["title"].strip(),f["event_at"],f.get("category","شخصي"),int(f.get("remind",15)),f.get("note","").strip()))
    return redirect(url_for("index")+"#events")

@app.post("/event/done/<int:item_id>")
def done_event(item_id):
    with db() as conn: conn.execute("UPDATE events SET done=1 WHERE id=?",(item_id,))
    return redirect(url_for("index")+"#events")

@app.post("/event/delete/<int:item_id>")
def delete_event(item_id):
    with db() as conn: conn.execute("DELETE FROM events WHERE id=?",(item_id,))
    return redirect(url_for("index")+"#events")

@app.post("/budget")
def set_budget():
    budget=max(0,float(request.form.get("budget",0)))
    with db() as conn: conn.execute("INSERT INTO settings(key,value) VALUES('budget',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(str(budget),))
    return redirect(url_for("index")+"#expenses")

@app.get("/api/reminders")
def api_reminders():
    with db() as conn:
        rows=conn.execute("SELECT id,title,event_at,remind,category FROM events WHERE done=0").fetchall()
    return jsonify([dict(r) for r in rows])

init_db()
if __name__ == "__main__":
    app.run(debug=True)
