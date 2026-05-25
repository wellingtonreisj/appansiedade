import sqlite3
import os
import json
import threading
import logging
from datetime import datetime, date, timedelta
import pytz

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get('DB_PATH', 'data.db')
_BRT   = pytz.timezone('America/Sao_Paulo')
_lock  = threading.Lock()

DIET_PLAN = [
    {"time": "7h",    "icon": "☀️", "name": "Café da manhã", "desc": "3 ovos + pão integral + fruta"},
    {"time": "10h",   "icon": "🍎", "name": "Lanche manhã",  "desc": "Iogurte grego + castanhas"},
    {"time": "12h30", "icon": "🍽️", "name": "Almoço",        "desc": "Frango + arroz integral + salada"},
    {"time": "17h30", "icon": "⚡", "name": "Pré-treino",    "desc": "Banana + pasta de amendoim"},
    {"time": "21h",   "icon": "🌙", "name": "Pós-treino",    "desc": "Proteína + legumes"},
]

def today_str() -> str:
    return datetime.now(_BRT).strftime('%Y-%m-%d')

def _conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with _lock:
        c = _conn()
        c.executescript("""
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS checkins (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                date          TEXT    NOT NULL UNIQUE,
                took_bup      INTEGER DEFAULT NULL,
                sleep_quality TEXT    DEFAULT NULL,
                mit           TEXT    DEFAULT NULL,
                gym_today     INTEGER DEFAULT NULL,
                anx_manha     INTEGER DEFAULT NULL,
                anx_tarde     INTEGER DEFAULT NULL,
                anx_noite     INTEGER DEFAULT NULL,
                work_mood     TEXT    DEFAULT NULL,
                diet_lunch    INTEGER DEFAULT NULL,
                smoked        INTEGER DEFAULT NULL,
                drank         INTEGER DEFAULT NULL,
                exercised     TEXT    DEFAULT NULL,
                mit_done      TEXT    DEFAULT NULL,
                diet_meals    TEXT    DEFAULT NULL,
                emotions      TEXT    DEFAULT NULL,
                thought       TEXT    DEFAULT NULL,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT    NOT NULL,
                amount      REAL    NOT NULL,
                category    TEXT    DEFAULT 'Outros',
                description TEXT    DEFAULT '',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        c.commit()
        c.close()
    logger.info("DB pronto: %s", DB_PATH)

# ── Checkins ──────────────────────────────────────────────────────────────────

def upsert_checkin(fields: dict):
    """Insert or update today's checkin — only updates provided fields."""
    with _lock:
        c = _conn()
        d = today_str()
        exists = c.execute("SELECT id FROM checkins WHERE date=?", (d,)).fetchone()
        if exists:
            updates = {k: v for k, v in fields.items() if v is not None}
            if updates:
                sql = "UPDATE checkins SET " + ", ".join(f"{k}=?" for k in updates) + " WHERE date=?"
                c.execute(sql, list(updates.values()) + [d])
        else:
            fields['date'] = d
            cols = ", ".join(fields.keys())
            ph   = ", ".join("?" * len(fields))
            c.execute(f"INSERT INTO checkins ({cols}) VALUES ({ph})", list(fields.values()))
        c.commit()
        c.close()

def get_today_checkin() -> dict | None:
    c = _conn()
    row = c.execute("SELECT * FROM checkins WHERE date=?", (today_str(),)).fetchone()
    c.close()
    return _parse_row(row) if row else None

def get_checkins_history(days=30) -> list:
    c = _conn()
    rows = c.execute("SELECT * FROM checkins ORDER BY date DESC LIMIT ?", (days,)).fetchall()
    c.close()
    return [_parse_row(r) for r in rows]

def _parse_row(row) -> dict:
    d = dict(row)
    for field in ('diet_meals', 'emotions'):
        if isinstance(d.get(field), str):
            try:   d[field] = json.loads(d[field])
            except: pass
    return d

# ── Expenses ──────────────────────────────────────────────────────────────────

def save_expense(amount: float, category: str, description: str):
    with _lock:
        c = _conn()
        c.execute("INSERT INTO expenses (date, amount, category, description) VALUES (?,?,?,?)",
                  (today_str(), amount, category, description))
        c.commit()
        c.close()

def get_expenses_history(days=30) -> list:
    c = _conn()
    rows = c.execute(
        "SELECT * FROM expenses WHERE date >= date('now', ?) ORDER BY created_at DESC",
        (f'-{days} days',)
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]

# ── Streaks ───────────────────────────────────────────────────────────────────

def get_streaks() -> dict:
    c = _conn()
    rows = c.execute("SELECT date, smoked, drank FROM checkins ORDER BY date DESC").fetchall()
    c.close()
    smoke_streak = drink_streak = 0
    for i, r in enumerate(rows):
        if r['smoked'] == 0: smoke_streak += 1
        else: smoke_streak = 0 if i == 0 else smoke_streak; break
    for i, r in enumerate(rows):
        if r['drank'] == 0: drink_streak += 1
        else: drink_streak = 0 if i == 0 else drink_streak; break
    return {'no_smoke': smoke_streak, 'no_drink': drink_streak}

# ── Week training ─────────────────────────────────────────────────────────────

def get_week_training() -> list:
    """Returns list of 7 booleans/None (Mon–Sun). None = future day."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_dates = [(monday + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    c = _conn()
    rows = {r['date']: r['exercised'] for r in c.execute(
        "SELECT date, exercised FROM checkins WHERE date >= ?", (week_dates[0],)
    ).fetchall()}
    c.close()
    result = []
    for d in week_dates:
        d_obj = datetime.strptime(d, '%Y-%m-%d').date()
        if d_obj > today:
            result.append(None)
        elif d in rows:
            result.append(bool(rows[d] and rows[d] != ''))
        else:
            result.append(False)
    return result

# ── Correlations ──────────────────────────────────────────────────────────────

def get_correlations() -> list:
    """Anxiety correlations with habits. Requires ≥14 days of data."""
    c = _conn()
    rows = c.execute("""
        SELECT anx_noite, smoked, drank, exercised
        FROM checkins WHERE anx_noite IS NOT NULL
        ORDER BY date DESC LIMIT 60
    """).fetchall()
    c.close()
    if len(rows) < 7:
        return []

    def avg(lst):
        vals = [r['anx_noite'] for r in lst if r['anx_noite'] is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    results = []

    trained    = [r for r in rows if r['exercised'] and r['exercised'] != '']
    no_trained = [r for r in rows if not r['exercised'] or r['exercised'] == '']
    if len(trained) >= 3 and len(no_trained) >= 3:
        a, b = avg(trained), avg(no_trained)
        if a and b:
            results.append({'label':'🏋️ Dias que treinou', 'anx':a,'ref':b,'diff':round(a-b,1),'positive':a<b})

    drank_rows  = [r for r in rows if r['drank'] == 1]
    sober_rows  = [r for r in rows if r['drank'] == 0]
    if len(drank_rows) >= 3:
        a, b = avg(drank_rows), avg(sober_rows)
        if a and b:
            results.append({'label':'🍺 Dia seguinte ao álcool', 'anx':a,'ref':b,'diff':round(a-b,1),'positive':a<b})

    smoked_rows  = [r for r in rows if r['smoked'] and r['smoked'] > 0]
    no_smoke_rows = [r for r in rows if r['smoked'] == 0]
    if len(smoked_rows) >= 3 and len(no_smoke_rows) >= 3:
        a, b = avg(no_smoke_rows), avg(smoked_rows)
        if a and b:
            results.append({'label':'🚭 Dias sem cigarro', 'anx':a,'ref':b,'diff':round(a-b,1),'positive':a<b})

    return results

# ── Stats (API) ───────────────────────────────────────────────────────────────

def get_exercise_history_30() -> list:
    """30-day list of booleans/None. None = no checkin that day."""
    today = date.today()
    c = _conn()
    rows = {r['date']: r['exercised'] for r in c.execute(
        "SELECT date, exercised FROM checkins WHERE date >= date('now', '-30 days')"
    ).fetchall()}
    c.close()
    result = []
    for i in range(29, -1, -1):
        d = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        if d in rows:
            ex = rows[d]
            result.append(bool(ex and ex != ''))
        else:
            result.append(None)
    return result

def get_stats() -> dict:
    from quotes import get_daily_quote
    checkins = get_checkins_history(30)
    expenses = get_expenses_history(30)

    anx_history = []
    for row in reversed(checkins[:14]):
        anx_history.append({
            'd': row['date'][5:].replace('-', '/'),
            'm': row.get('anx_manha'),
            't': row.get('anx_tarde'),
            'n': row.get('anx_noite'),
        })

    return {
        'streaks':           get_streaks(),
        'today':             get_today_checkin(),
        'anxiety_history':   anx_history,
        'exercise_history':  get_exercise_history_30(),
        'expenses':          expenses,
        'expense_total':     sum(e['amount'] for e in expenses),
        'week_training':     get_week_training(),
        'correlations':      get_correlations(),
        'diet_plan':         DIET_PLAN,
        'quote':             get_daily_quote(),
    }

# ── Backup ────────────────────────────────────────────────────────────────────

def export_all() -> dict:
    c = _conn()
    checkins = [_parse_row(r) for r in c.execute("SELECT * FROM checkins ORDER BY date").fetchall()]
    expenses = [dict(r)        for r in c.execute("SELECT * FROM expenses  ORDER BY date").fetchall()]
    c.close()
    return {'checkins': checkins, 'expenses': expenses}
