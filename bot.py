"""Telegram bot — 3 check-ins diários + gastos."""
import os
import json
import logging
import telebot
from telebot import types
from db import upsert_checkin, save_expense, get_streaks, get_today_checkin, DIET_PLAN
from ocr import extract_expense

logger = logging.getLogger(__name__)

TOKEN   = os.environ.get('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = str(os.environ.get('TELEGRAM_CHAT_ID', ''))

bot = telebot.TeleBot(TOKEN, parse_mode='HTML') if TOKEN else None

# ── State machine (single user) ───────────────────────────────────────────────
_state: dict = {}   # chat_id -> state string
_temp:  dict = {}   # chat_id -> dict with in-progress data
_pending_expense: dict = {}  # chat_id -> (amount, category, desc, next_state)

def S(cid):        return _state.get(str(cid), 'idle')
def set_S(cid, s): _state[str(cid)] = s
def T(cid):        return _temp.setdefault(str(cid), {})
def set_T(cid, k, v): T(cid)[k] = v
def reset_T(cid):  _temp[str(cid)] = {}

# ── EMOÇÕES disponíveis ───────────────────────────────────────────────────────
EMOTIONS = {
    'feliz':    '😊 Feliz',   'animado':   '🔥 Animado',
    'motivado': '💪 Motivado','focado':    '🎯 Focado',
    'tranquilo':'😌 Tranquilo','cansado':  '😴 Cansado',
    'irritado': '😤 Irritado','ansioso':   '😰 Ansioso',
    'triste':   '😔 Triste',  'sobrecarregado':'🫠 Sobrecarregado',
    'grato':    '🙏 Grato',   'estressado':'🤯 Estressado',
}

# ── Helpers de teclado ────────────────────────────────────────────────────────
def _anx_kb(prefix: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=4)
    kb.add(
        types.InlineKeyboardButton("1–3 😌", callback_data=f'{prefix}:2'),
        types.InlineKeyboardButton("4–5 😐", callback_data=f'{prefix}:4'),
        types.InlineKeyboardButton("6–7 😤", callback_data=f'{prefix}:6'),
        types.InlineKeyboardButton("8–10 😰", callback_data=f'{prefix}:9'),
    )
    return kb

def _yn_kb(yes_data: str, no_data: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("✅ Sim", callback_data=yes_data),
           types.InlineKeyboardButton("❌ Não", callback_data=no_data))
    return kb

# ─────────────────────────────────────────────────────────────────────────────
# CHECK-IN DA MANHÃ  (7h30)
# ─────────────────────────────────────────────────────────────────────────────

def _is_busy(chat_id: int) -> bool:
    """Returns True if user is already in the middle of a flow."""
    return S(chat_id) != 'idle'

def start_morning(chat_id: int):
    if _is_busy(chat_id):
        bot.send_message(chat_id, "⚠️ Você já está no meio de um check-in. Termina ele ou manda /cancelar pra recomeçar.")
        return
    reset_T(chat_id)
    bot.send_message(chat_id, "☀️ <b>Bom dia, Wellington!</b>\nCheck-in da manhã — 30 segundos 👊")
    _ask_bup(chat_id)

def _ask_bup(cid):
    set_S(cid, 'm_bup')
    bot.send_message(cid, "💊 Tomou Bupropiona?", reply_markup=_yn_kb('m_bup:1','m_bup:0'))

def _ask_m_anx(cid):
    set_S(cid, 'm_anx')
    bot.send_message(cid, "🧠 Ansiedade agora?", reply_markup=_anx_kb('m_anx'))

def _ask_sleep(cid):
    set_S(cid, 'm_sleep')
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(
        types.InlineKeyboardButton("😴 Mal",   callback_data='m_sleep:mal'),
        types.InlineKeyboardButton("😐 Ok",    callback_data='m_sleep:ok'),
        types.InlineKeyboardButton("⚡ Ótimo", callback_data='m_sleep:otimo'),
    )
    bot.send_message(cid, "😴 Como acordou?", reply_markup=kb)

def _ask_mit(cid):
    set_S(cid, 'm_mit')
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⏭️ Pular", callback_data='m_mit:skip'))
    bot.send_message(cid,
        "🎯 <b>Qual sua 1 prioridade de hoje?</b>\n<i>Digita o MIT ou pula.</i>",
        reply_markup=kb)

def _ask_gym_today(cid):
    set_S(cid, 'm_gym')
    bot.send_message(cid, "💪 Hoje é dia de treino?", reply_markup=_yn_kb('m_gym:1','m_gym:0'))

def _finish_morning(cid):
    set_S(cid, 'idle')
    data = dict(T(cid))
    upsert_checkin(data)
    reset_T(cid)
    bot.send_message(cid, "✅ Manhã registrada! Boa segunda-feira — vai lá. 🚀")

# ─────────────────────────────────────────────────────────────────────────────
# CHECK-IN DA TARDE  (13h)
# ─────────────────────────────────────────────────────────────────────────────

def start_afternoon(chat_id: int):
    if _is_busy(chat_id):
        bot.send_message(chat_id, "⚠️ Você já está no meio de um check-in. Termina ele ou manda /cancelar.")
        return
    reset_T(chat_id)
    bot.send_message(chat_id, "☀️ <b>Pulso rápido do meio-dia!</b>\n3 cliques e pronto 👌")
    _ask_t_anx(chat_id)

def _ask_t_anx(cid):
    set_S(cid, 't_anx')
    bot.send_message(cid, "🧠 Ansiedade agora?", reply_markup=_anx_kb('t_anx'))

def _ask_work(cid):
    set_S(cid, 't_work')
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(
        types.InlineKeyboardButton("🔥 Fluindo",  callback_data='t_work:fluindo'),
        types.InlineKeyboardButton("😐 Normal",   callback_data='t_work:normal'),
        types.InlineKeyboardButton("🤯 Pesado",   callback_data='t_work:pesado'),
    )
    bot.send_message(cid, "💼 Como tá o trabalho hoje?", reply_markup=kb)

def _ask_lunch(cid):
    set_S(cid, 't_lunch')
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(
        types.InlineKeyboardButton("✅ Segui",        callback_data='t_lunch:2'),
        types.InlineKeyboardButton("〰️ Parcialmente", callback_data='t_lunch:1'),
        types.InlineKeyboardButton("❌ Não segui",    callback_data='t_lunch:0'),
    )
    bot.send_message(cid, "🥗 Seguiu a dieta no almoço?", reply_markup=kb)

def _finish_afternoon(cid):
    set_S(cid, 'idle')
    data = dict(T(cid))
    upsert_checkin(data)
    reset_T(cid)
    bot.send_message(cid, "✅ Tarde registrada! Boa tarde 💪")

# ─────────────────────────────────────────────────────────────────────────────
# CHECK-IN DA NOITE  (21h)
# ─────────────────────────────────────────────────────────────────────────────

def start_evening(chat_id: int):
    if _is_busy(chat_id):
        bot.send_message(chat_id, "⚠️ Você já está no meio de um check-in. Termina ele ou manda /cancelar.")
        return
    reset_T(chat_id)
    bot.send_message(chat_id, "🌙 <b>Check-in da noite!</b>\nFechamento do dia — 1 minutinho 👊")
    _ask_n_anx(chat_id)

def _ask_n_anx(cid):
    set_S(cid, 'n_anx')
    bot.send_message(cid, "🧠 Ansiedade agora?", reply_markup=_anx_kb('n_anx'))

def _ask_smoke(cid):
    set_S(cid, 'n_smoke')
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🚭 Não fumei", callback_data='n_smoke:0'),
        types.InlineKeyboardButton("🚬 Fumei",     callback_data='n_smoke:yes'),
    )
    bot.send_message(cid, "🚬 Fumou cigarro hoje?", reply_markup=kb)

def _ask_smoke_count(cid):
    set_S(cid, 'n_smoke_n')
    kb = types.InlineKeyboardMarkup(row_width=5)
    kb.add(*[types.InlineKeyboardButton(str(i), callback_data=f'n_smoke_n:{i}') for i in range(1,6)])
    bot.send_message(cid, "Quantos cigarros?", reply_markup=kb)

def _ask_drink(cid):
    set_S(cid, 'n_drink')
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🍹 Não bebi",  callback_data='n_drink:0'),
        types.InlineKeyboardButton("🍺 Bebi",      callback_data='n_drink:1'),
    )
    bot.send_message(cid, "🍺 Bebeu álcool?", reply_markup=kb)

def _ask_exercise(cid):
    set_S(cid, 'n_exercise')
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🏋️ Academia",  callback_data='n_ex:academia'),
        types.InlineKeyboardButton("🏃 Corrida",   callback_data='n_ex:corrida'),
        types.InlineKeyboardButton("🚴 Ciclismo",  callback_data='n_ex:ciclismo'),
        types.InlineKeyboardButton("🤸 Outro",     callback_data='n_ex:outro'),
        types.InlineKeyboardButton("❌ Não fiz",   callback_data='n_ex:'),
    )
    bot.send_message(cid, "💪 Exercitou hoje?", reply_markup=kb)

def _ask_diet(cid):
    set_S(cid, 'n_diet')
    # Start with all meals unchecked
    T(cid)['diet_selection'] = [False] * len(DIET_PLAN)
    _send_diet_keyboard(cid)

def _send_diet_keyboard(cid, message_id=None):
    sel = T(cid).get('diet_selection', [False]*len(DIET_PLAN))
    kb = types.InlineKeyboardMarkup(row_width=1)
    for i, meal in enumerate(DIET_PLAN):
        mark = '✅' if sel[i] else '⬜'
        kb.add(types.InlineKeyboardButton(
            f"{mark} {meal['icon']} {meal['name']} ({meal['time']})",
            callback_data=f'n_diet_toggle:{i}'
        ))
    kb.add(types.InlineKeyboardButton("✔️ Confirmar", callback_data='n_diet_confirm'))

    text = "🥗 <b>Quais refeições você fez hoje?</b>\n<i>Toca pra marcar cada uma:</i>"
    if message_id:
        try:
            bot.edit_message_text(text, cid, message_id, reply_markup=kb, parse_mode='HTML')
        except: pass
    else:
        msg = bot.send_message(cid, text, reply_markup=kb)
        set_T(cid, 'diet_msg_id', msg.message_id)

def _ask_mit_done(cid):
    mit_text = T(cid).get('mit') or get_today_checkin() and get_today_checkin().get('mit')
    set_S(cid, 'n_mit_done')
    if not mit_text:
        # skip if no MIT was set
        set_T(cid, 'mit_done', None)
        _ask_emotions(cid)
        return
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(
        types.InlineKeyboardButton("✅ Fiz",       callback_data='n_mit:done'),
        types.InlineKeyboardButton("〰️ Parcial",  callback_data='n_mit:partial'),
        types.InlineKeyboardButton("❌ Não fiz",   callback_data='n_mit:miss'),
    )
    bot.send_message(cid, f"🎯 MIT de hoje:\n<i>{mit_text}</i>\n\nCompletou?", reply_markup=kb)

def _ask_emotions(cid):
    set_S(cid, 'n_emotions')
    T(cid).setdefault('emotions_selection', [])
    _send_emotions_keyboard(cid)

def _send_emotions_keyboard(cid, message_id=None):
    sel = T(cid).get('emotions_selection', [])
    kb  = types.InlineKeyboardMarkup(row_width=2)
    for key, label in EMOTIONS.items():
        mark = '✅' if key in sel else ''
        kb.add(types.InlineKeyboardButton(f"{mark} {label}", callback_data=f'n_emo:{key}'))
    kb.add(types.InlineKeyboardButton("✔️ Confirmar", callback_data='n_emo_confirm'))

    text = "💭 <b>Que emoções você sentiu hoje?</b>\n<i>Marca quantas quiser:</i>"
    if message_id:
        try:
            bot.edit_message_text(text, cid, message_id, reply_markup=kb, parse_mode='HTML')
        except: pass
    else:
        msg = bot.send_message(cid, text, reply_markup=kb)
        set_T(cid, 'emo_msg_id', msg.message_id)

def _ask_thought(cid):
    set_S(cid, 'n_thought')
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⏭️ Pular", callback_data='n_thought:skip'))
    bot.send_message(cid,
        "📝 <b>Pensamento do dia</b>\n<i>Digita algo que ficou na cabeça, ou pula:</i>",
        reply_markup=kb)

def _ask_expense(cid):
    set_S(cid, 'n_expense')
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⏭️ Pular", callback_data='n_expense:skip'))
    bot.send_message(cid,
        "💰 <b>Algum gasto pra registrar?</b>\n"
        "Manda foto do comprovante, ou digita:\n<code>45.90 Almoço</code>",
        reply_markup=kb)

def _finish_evening(cid):
    set_S(cid, 'idle')
    data = dict(T(cid))

    # Serialize list fields
    if isinstance(data.get('diet_meals'), list):
        data['diet_meals'] = json.dumps(data['diet_meals'])
    if isinstance(data.get('emotions'), list):
        data['emotions']   = json.dumps(data['emotions'])

    # Remove internal keys
    for k in ('diet_selection', 'diet_msg_id', 'emotions_selection', 'emo_msg_id'):
        data.pop(k, None)

    upsert_checkin(data)
    streaks = get_streaks()
    reset_T(cid)

    smoke_n  = data.get('smoked', 0) or 0
    drank    = data.get('drank', 0)  or 0
    exercised = data.get('exercised', '')

    smoke_line = f"🚭 Sem fumar: <b>{streaks['no_smoke']} dias</b> 🔥" if smoke_n == 0 else f"🚬 Fumou {smoke_n} cigarro(s)"
    drink_line = f"🍹 Sem beber: <b>{streaks['no_drink']} dias</b> 💪" if drank == 0 else "🍺 Bebeu hoje"
    ex_map = {'academia':'🏋️ Academia','corrida':'🏃 Corrida','ciclismo':'🚴 Ciclismo','outro':'🤸 Outro','':'❌ Sem treino'}
    ex_line = ex_map.get(exercised or '', '❌ Sem treino')

    url = os.environ.get('APP_URL', 'http://localhost:5000')
    bot.send_message(cid,
        f"✅ <b>Dia fechado!</b>\n\n"
        f"{smoke_line}\n{drink_line}\n{ex_line}\n\n"
        f"<a href='{url}'>📊 Ver dashboard</a>"
    )

# ─────────────────────────────────────────────────────────────────────────────
# GASTOS AVULSOS
# ─────────────────────────────────────────────────────────────────────────────

def _handle_expense_text(cid, text: str, next_state='idle'):
    result = extract_expense(text.encode(), is_image=False)
    if result:
        amount, category, desc = result
        _pending_expense[str(cid)] = (amount, category, desc, next_state)
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("✅ Confirmar", callback_data='exp_ok'),
            types.InlineKeyboardButton("❌ Cancelar",  callback_data='exp_cancel'),
        )
        bot.send_message(cid,
            f"Entendi:\n💰 <b>R$ {amount:.2f}</b>\n📂 {category}\n📝 {desc}\n\nConfirma?",
            reply_markup=kb)
    else:
        bot.send_message(cid, "Não entendi. Tenta: <code>45.90 Almoço</code>")

def _handle_expense_photo(cid, photo, next_state='idle'):
    bot.send_message(cid, "🔍 Analisando comprovante...")
    try:
        fi = bot.get_file(photo[-1].file_id)
        fb = bot.download_file(fi.file_path)
        result = extract_expense(fb, is_image=True)
        if result:
            amount, category, desc = result
            _pending_expense[str(cid)] = (amount, category, desc, next_state)
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("✅ Confirmar", callback_data='exp_ok'),
                types.InlineKeyboardButton("❌ Cancelar",  callback_data='exp_cancel'),
            )
            bot.send_message(cid,
                f"Entendi:\n💰 <b>R$ {amount:.2f}</b>\n📂 {category}\n📝 {desc}\n\nConfirma?",
                reply_markup=kb)
        else:
            bot.send_message(cid, "Não consegui extrair. Digita: <code>45.90 Descrição</code>")
    except Exception as e:
        logger.error("Photo expense error: %s", e)
        bot.send_message(cid, "Erro ao processar imagem. Tenta digitar o valor.")

# ─────────────────────────────────────────────────────────────────────────────
# COMMAND HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['start', 'ajuda', 'help'])
def cmd_start(msg):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Check-in manhã",  callback_data='do_morning'),
           types.InlineKeyboardButton("🌙 Check-in noite",  callback_data='do_evening'))
    bot.send_message(msg.chat.id,
        f"Oi, <b>Wellington</b>! 👋\n\n"
        f"Seu ID é: <code>{msg.chat.id}</code>\n\n"
        "Comandos:\n"
        "/manha — check-in da manhã\n"
        "/tarde — check-in da tarde\n"
        "/noite — check-in da noite\n"
        "/streaks — ver streaks\n"
        "/hoje — resumo de hoje\n"
        "/gastos — registrar gasto\n"
        "/dashboard — link do painel\n"
        "/backup — exportar dados",
        reply_markup=kb)

@bot.message_handler(commands=['cancelar'])
def cmd_cancelar(msg):
    set_S(msg.chat.id, 'idle')
    reset_T(msg.chat.id)
    _pending_expense.pop(str(msg.chat.id), None)
    bot.send_message(msg.chat.id, "✅ Cancelado. Manda /manha, /tarde ou /noite quando quiser recomeçar.")

@bot.message_handler(commands=['manha'])
def cmd_manha(msg): start_morning(msg.chat.id)

@bot.message_handler(commands=['tarde'])
def cmd_tarde(msg): start_afternoon(msg.chat.id)

@bot.message_handler(commands=['noite'])
def cmd_noite(msg): start_evening(msg.chat.id)

@bot.message_handler(commands=['streaks'])
def cmd_streaks(msg):
    s = get_streaks()
    bot.send_message(msg.chat.id,
        f"🏆 <b>Suas streaks:</b>\n\n"
        f"🚭 Sem fumar: <b>{s['no_smoke']} dias</b>\n"
        f"🍹 Sem beber: <b>{s['no_drink']} dias</b>")

@bot.message_handler(commands=['hoje'])
def cmd_hoje(msg):
    t = get_today_checkin()
    if not t:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("☀️ Check-in manhã", callback_data='do_morning'))
        bot.send_message(msg.chat.id, "❌ Nenhum check-in hoje ainda.", reply_markup=kb)
        return
    ex_map = {'academia':'🏋️','corrida':'🏃','ciclismo':'🚴','outro':'🤸','':' –','None':' –'}
    bot.send_message(msg.chat.id,
        f"📋 <b>Hoje:</b>\n\n"
        f"💊 Bup: {'✅' if t.get('took_bup') else '❌'}\n"
        f"🧠 Ansiedade: {t.get('anx_manha','–')} / {t.get('anx_tarde','–')} / {t.get('anx_noite','–')}\n"
        f"🚬 Fumou: {'Não' if t.get('smoked')==0 else str(t.get('smoked','–'))}\n"
        f"🍺 Bebeu: {'Não' if t.get('drank')==0 else 'Sim'}\n"
        f"💪 Treino: {ex_map.get(str(t.get('exercised')),'–')}\n"
        f"🎯 MIT: {t.get('mit','–')}")

@bot.message_handler(commands=['gastos'])
def cmd_gastos(msg):
    set_S(msg.chat.id, 'standalone_expense')
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("❌ Cancelar", callback_data='exp_cancel'))
    bot.send_message(msg.chat.id,
        "💰 <b>Registrar gasto:</b>\n\nManda foto ou digita:\n<code>45.90 Almoço</code>",
        reply_markup=kb)

@bot.message_handler(commands=['dashboard'])
def cmd_dashboard(msg):
    url = os.environ.get('APP_URL', 'http://localhost:5000')
    bot.send_message(msg.chat.id, f"📊 <a href='{url}'>Abrir Dashboard</a>")

@bot.message_handler(commands=['backup'])
def cmd_backup(msg):
    import io, json as _json
    from db import export_all
    data = export_all()
    buf = io.BytesIO(_json.dumps(data, ensure_ascii=False, indent=2, default=str).encode())
    buf.name = 'backup.json'
    bot.send_document(msg.chat.id, buf, caption="📦 Backup dos seus dados")

# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK HANDLER
# ─────────────────────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call):
    cid  = call.message.chat.id
    data = call.data
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass  # ignora se o callback expirou (> 30s)

    # ── Launch flows ──
    if data == 'do_morning':  start_morning(cid);   return
    if data == 'do_afternoon':start_afternoon(cid); return
    if data == 'do_evening':  start_evening(cid);   return

    # ── Morning ──
    if data.startswith('m_bup:'):
        set_T(cid, 'took_bup', int(data.split(':')[1]))
        _ask_m_anx(cid)
    elif data.startswith('m_anx:'):
        set_T(cid, 'anx_manha', int(data.split(':')[1]))
        _ask_sleep(cid)
    elif data.startswith('m_sleep:'):
        set_T(cid, 'sleep_quality', data.split(':')[1])
        _ask_mit(cid)
    elif data == 'm_mit:skip':
        _ask_gym_today(cid)
    elif data.startswith('m_gym:'):
        set_T(cid, 'gym_today', int(data.split(':')[1]))
        _finish_morning(cid)

    # ── Afternoon ──
    elif data.startswith('t_anx:'):
        set_T(cid, 'anx_tarde', int(data.split(':')[1]))
        _ask_work(cid)
    elif data.startswith('t_work:'):
        set_T(cid, 'work_mood', data.split(':')[1])
        _ask_lunch(cid)
    elif data.startswith('t_lunch:'):
        set_T(cid, 'diet_lunch', int(data.split(':')[1]))
        _finish_afternoon(cid)

    # ── Evening ──
    elif data.startswith('n_anx:'):
        set_T(cid, 'anx_noite', int(data.split(':')[1]))
        _ask_smoke(cid)
    elif data == 'n_smoke:0':
        set_T(cid, 'smoked', 0)
        _ask_drink(cid)
    elif data == 'n_smoke:yes':
        _ask_smoke_count(cid)
    elif data.startswith('n_smoke_n:'):
        set_T(cid, 'smoked', int(data.split(':')[1]))
        _ask_drink(cid)
    elif data.startswith('n_drink:'):
        set_T(cid, 'drank', int(data.split(':')[1]))
        _ask_exercise(cid)
    elif data.startswith('n_ex:'):
        set_T(cid, 'exercised', data.split(':')[1])
        _ask_diet(cid)

    # Diet multi-select
    elif data.startswith('n_diet_toggle:'):
        idx = int(data.split(':')[1])
        sel = T(cid).get('diet_selection', [False]*len(DIET_PLAN))
        sel[idx] = not sel[idx]
        set_T(cid, 'diet_selection', sel)
        _send_diet_keyboard(cid, message_id=call.message.message_id)
    elif data == 'n_diet_confirm':
        sel = T(cid).get('diet_selection', [False]*len(DIET_PLAN))
        set_T(cid, 'diet_meals', sel)
        _ask_mit_done(cid)

    elif data.startswith('n_mit:'):
        set_T(cid, 'mit_done', data.split(':')[1])
        _ask_emotions(cid)

    # Emotions multi-select
    elif data.startswith('n_emo:'):
        key = data.split(':')[1]
        sel = T(cid).get('emotions_selection', [])
        if key in sel: sel.remove(key)
        else: sel.append(key)
        set_T(cid, 'emotions_selection', sel)
        _send_emotions_keyboard(cid, message_id=call.message.message_id)
    elif data == 'n_emo_confirm':
        set_T(cid, 'emotions', T(cid).get('emotions_selection', []))
        _ask_thought(cid)

    elif data == 'n_thought:skip':
        _ask_expense(cid)
    elif data == 'n_expense:skip':
        _finish_evening(cid)

    # ── Expense confirm/cancel ──
    elif data == 'exp_ok':
        pending = _pending_expense.pop(str(cid), None)
        if pending:
            amount, category, desc, next_state = pending
            save_expense(amount, category, desc)
            bot.send_message(cid, f"✅ R$ {amount:.2f} — {category} salvo!")
            if next_state == 'finish_evening':
                _finish_evening(cid)
            else:
                set_S(cid, 'idle')
    elif data == 'exp_cancel':
        _pending_expense.pop(str(cid), None)
        bot.send_message(cid, "Gasto cancelado.")
        if S(cid) == 'n_expense':
            _finish_evening(cid)
        else:
            set_S(cid, 'idle')

# ─────────────────────────────────────────────────────────────────────────────
# TEXT / PHOTO HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@bot.message_handler(content_types=['text'])
def handle_text(msg):
    cid  = msg.chat.id
    text = msg.text.strip()
    if text.startswith('/'): return
    s = S(cid)

    if s == 'm_mit':
        set_T(cid, 'mit', text)
        _ask_gym_today(cid)
    elif s == 'n_thought':
        set_T(cid, 'thought', text)
        _ask_expense(cid)
    elif s in ('n_expense', 'standalone_expense'):
        ns = 'finish_evening' if s == 'n_expense' else 'idle'
        _handle_expense_text(cid, text, next_state=ns)
    else:
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("☀️ Manhã", callback_data='do_morning'),
               types.InlineKeyboardButton("🌙 Noite",  callback_data='do_evening'))
        bot.send_message(cid, "Use /ajuda pra ver os comandos.", reply_markup=kb)

@bot.message_handler(content_types=['photo'])
def handle_photo(msg):
    cid = msg.chat.id
    s   = S(cid)
    if s in ('n_expense', 'standalone_expense'):
        ns = 'finish_evening' if s == 'n_expense' else 'idle'
        _handle_expense_photo(cid, msg.photo, next_state=ns)

# ─────────────────────────────────────────────────────────────────────────────

def run_bot():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN não configurado — bot não iniciou.")
        return
    logger.info("Bot iniciando polling...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
