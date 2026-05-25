import os
import threading
import logging
from flask import Flask, render_template, jsonify, request

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s — %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def dashboard():
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    from db import get_stats
    return jsonify(get_stats())

@app.route('/api/checkins')
def api_checkins():
    from db import get_checkins_history
    days = min(int(request.args.get('days', 30)), 90)
    return jsonify(get_checkins_history(days))

@app.route('/api/expenses')
def api_expenses():
    from db import get_expenses_history
    days = min(int(request.args.get('days', 30)), 90)
    return jsonify(get_expenses_history(days))

# ── Startup ───────────────────────────────────────────────────────────────────

def _start_services():
    from db import init_db
    init_db()

    from scheduler import start_scheduler
    start_scheduler()

    from bot import run_bot
    t = threading.Thread(target=run_bot, name='telegram-bot', daemon=True)
    t.start()
    logger.info("Todos os serviços iniciados.")

_start_services()

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
