"""Scheduler — lembretes 3x ao dia + reenvio a cada 2h se não respondido."""
import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger(__name__)
_BRT = pytz.timezone('America/Sao_Paulo')


def check_and_remind():
    """
    Função central de lembretes. Roda nos horários abaixo e decide o que mandar.

    Janelas:
      Manhã   → 7h30, 9h30, 11h30       (até anx_manha preenchida)
      Tarde   → 13h,  15h,  17h, 19h    (até anx_tarde preenchida — pula terça)
      Noite   → 21h,  23h               (até anx_noite preenchida)
    """
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not chat_id:
        return

    # Não interrompe se já estiver no meio de um check-in
    try:
        from bot import S
        if S(int(chat_id)) != 'idle':
            return
    except Exception:
        pass

    from db import get_today_checkin
    now     = datetime.now(_BRT)
    hour    = now.hour
    weekday = now.weekday()   # 0=Seg ... 6=Dom
    today   = get_today_checkin()

    try:
        from bot import bot, start_morning, start_afternoon, start_evening

        # ── Manhã (7h–12h) ──────────────────────────────────────────────
        if 7 <= hour <= 12:
            if not today or today.get('anx_manha') is None:
                logger.info("Lembrete manhã → chat %s", chat_id)
                start_morning(int(chat_id))

        # ── Tarde (13h–20h) — pula terça (terapia às 13h) ───────────────
        elif 13 <= hour <= 20 and weekday != 1:
            if not today or today.get('anx_tarde') is None:
                logger.info("Lembrete tarde → chat %s", chat_id)
                start_afternoon(int(chat_id))

        # ── Noite (21h+) ─────────────────────────────────────────────────
        elif hour >= 21:
            if not today or today.get('anx_noite') is None:
                logger.info("Lembrete noite → chat %s", chat_id)
                start_evening(int(chat_id))

    except Exception as e:
        logger.error("Erro no lembrete: %s", e)


def start_scheduler():
    s = BackgroundScheduler(timezone=_BRT)

    # Manhã: 7h30, 9h30, 11h30
    s.add_job(check_and_remind, CronTrigger(hour='7,9,11', minute=30, timezone=_BRT),
              id='remind_manha', replace_existing=True, misfire_grace_time=1800)

    # Tarde: 13h, 15h, 17h, 19h
    s.add_job(check_and_remind, CronTrigger(hour='13,15,17,19', minute=0, timezone=_BRT),
              id='remind_tarde', replace_existing=True, misfire_grace_time=1800)

    # Noite: 21h, 23h
    s.add_job(check_and_remind, CronTrigger(hour='21,23', minute=0, timezone=_BRT),
              id='remind_noite', replace_existing=True, misfire_grace_time=1800)

    s.start()
    logger.info("Scheduler iniciado — Manhã: 7h30/9h30/11h30 | Tarde: 13h/15h/17h/19h | Noite: 21h/23h")
    return s
