import telebot
from telebot import types
from datetime import datetime, timedelta
import json
import os
import threading
import time
import requests
from flask import Flask
import logging

# ============================================
#  LOGGING CONFIGURATION
# ============================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================
#  ENVIRONMENT VARIABLES
# ============================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_GROUP_ID_STR = os.environ.get("ADMIN_GROUP_ID")
ADMIN_GROUP_ID = int(ADMIN_GROUP_ID_STR) if ADMIN_GROUP_ID_STR else -1002422128365

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN မတွေ့ရှိပါ။ Environment Variable ကို စစ်ဆေးပါ။")
    exit(1)

if not ADMIN_GROUP_ID:
    logger.warning("⚠️ ADMIN_GROUP_ID မတွေ့ရှိပါ။")

bot = telebot.TeleBot(BOT_TOKEN)
DB_FILE = "user_database.json"

# ============================================
#  CHANNEL CONFIGURATION
# ============================================
CHANNEL_1_ID = "@CandyHub_Ch"
CHANNEL_2_ID = "@candyhubassissiant"
CHANNEL_1_URL = "https://t.me/CandyHub_Ch"
CHANNEL_2_URL = "https://t.me/candyhubassissiant"

# ============================================
#  FLASK KEEP-ALIVE SERVER
# ============================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🍬 Candy Hub Bot is alive and running smoothly! 🚀"

@app.route('/health')
def health():
    return "OK", 200

def ping_self():
    """Self-ping စနစ် - Render ရဲ့ sleep ကိုကာကွယ်ရန်"""
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        url = "https://beta-no7j.onrender.com"
        logger.info(f"🔄 Using hardcoded URL: {url}")
    
    logger.info(f"🔄 Self-ping စတင်ပါပြီ။ URL: {url}")
    while True:
        time.sleep(300)
        try:
            response = requests.get(f"{url}/health", timeout=10)
            logger.info(f"🟢 Ping အောင်မြင်သည် - Status: {response.status_code}")
        except Exception as e:
            logger.error(f"🔴 Ping ပျက်ကွက်သည်: {e}")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

# ============================================
#  DATABASE FUNCTIONS
# ============================================
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: 
                return json.load(f)
            except: 
                return {}
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def check_status(user_id):
    try:
        member1 = bot.get_chat_member(CHANNEL_1_ID, user_id)
        member2 = bot.get_chat_member(CHANNEL_2_ID, user_id)
        allowed = ['member', 'administrator', 'creator']
        return member1.status in allowed and member2.status in allowed
    except Exception as e:
        logger.error(f"❌ Status check error: {e}")
        return False

def can_submit_task(user_id):
    """တစ်နေ့တစ်ခါသာ task တင်နိုင်ရန် စစ်ဆေးခြင်း"""
    db = load_db()
    user_id = str(user_id)
    
    if user_id not in db:
        return True
    
    last_task = db[user_id].get("last_task_time")
    if not last_task:
        return True
    
    try:
        last_time = datetime.fromisoformat(last_task)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if last_time >= today:
            return False
    except:
        return True
    
    return True

def get_task_count_today(user_id):
    """ဒီနေ့ task တင်ပြီးသား အရေအတွက်"""
    db = load_db()
    user_id = str(user_id)
    return db.get(user_id, {}).get("task_count_today", 0)

# ============================================
#  SEND MESSAGE TO ADMIN GROUP
# ============================================
def send_to_admin_group(photo_id, caption, reply_markup=None):
    """Admin Group သို့ message ပို့ရန် function"""
    try:
        if reply_markup:
            bot.send_photo(
                ADMIN_GROUP_ID, 
                photo_id, 
                caption=caption, 
                parse_mode="Markdown", 
                reply_markup=reply_markup
            )
        else:
            bot.send_photo(
                ADMIN_GROUP_ID, 
                photo_id, 
                caption=caption, 
                parse_mode="Markdown"
            )
        logger.info(f"✅ Photo sent to admin group: {ADMIN_GROUP_ID}")
        return True
    except Exception as e:
        logger.error(f"❌ Error sending to admin group: {e}")
        return False

# ============================================
#  /start COMMAND
# ============================================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = str(message.from_user.id)
    first_name = message.from_user.first_name or "User"
    safe_name = first_name.replace("_", "\\_").replace("*", "").replace("[", "").replace("`", "")
    
    db = load_db()
    if user_id not in db:
        db[user_id] = {
            "name": first_name, 
            "email": None, 
            "username": message.from_user.username or "မရှိပါ",
            "last_task_time": None,
            "task_count_today": 0
        }
        save_db(db)

    welcome_text = (
        f"👋 *မင်္ဂလာပါ {safe_name}*\n\n"
        f"🤖 Bot ကို အသုံးပြုရန် အောက်ပါ Channels (၂) ခုလုံးကို Join ပေးပါရန် လိုအပ်ပါတယ်ဗျာ။ 👇"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("🌐 ခလုတ် ၁ (CandyHub Ch)", url=CHANNEL_1_URL)
    btn2 = types.InlineKeyboardButton("🌐 ခလုတ် ၂ (CandyHub Assistant)", url=CHANNEL_2_URL)
    btn_check = types.InlineKeyboardButton("🔄 Check Status", callback_data="check_channels")
    markup.add(btn1, btn2, btn_check)
    
    try:
        bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        logger.error(f"❌ /start message error: {e}")
        bot.send_message(message.chat.id, welcome_text.replace('*', ''), reply_markup=markup)

# ============================================
#  CALLBACK QUERY HANDLER
# ============================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = str(call.from_user.id)
    chat_id = call.message.chat.id
    db = load_db()

    try:
        # ----- Check Channels -----
        if call.data == "check_channels":
            if check_status(call.from_user.id):
                bot.answer_callback_query(call.id, "✅ ချန်နယ်များအားလုံး Join ပြီးပါပြီ။")
                ask_email(call.message)
            else:
                bot.answer_callback_query(call.id, "❌ ချန်နယ် (၂) ခုလုံးကို မဝင်ရသေးပါဗျာ။", show_alert=True)

        # ----- Confirm Email (Modified for safety) -----
        elif call.data.startswith("confirm_email_"):
            choice = call.data.split("_")[2] # 'yes' or 'no'
            
            if choice == "yes":
                if user_id not in db:
                    db[user_id] = {}
                    
                temp_email = db.get(user_id, {}).get("pending_email")
                
                if not temp_email:
                    bot.answer_callback_query(call.id, "❌ အီးမေးလ် အချက်အလက် မတွေ့ရှိပါ။ ပြန်လည်ရိုက်ထည့်ပါ။", show_alert=True)
                    bot.delete_message(chat_id, call.message.message_id)
                    msg = bot.send_message(chat_id, "ℹ️ အီးမေးလ်ကို ပြန်လည်ရေးသားပေးပါရန်။")
                    bot.register_next_step_handler(msg, process_email)
                    return

                # Save email to DB and clear pending
                db[user_id]["email"] = temp_email
                db[user_id]["pending_email"] = None 
                save_db(db)
                
                bot.edit_message_text(
                    f"🎉 *အီးမေးလ် အတည်ပြုသိမ်းဆည်းပြီးပါပြီ!*\n"
                    f"💾 Email: `{temp_email}`\n\n"
                    f"👉 `/profile` သို့မဟုတ် `/check` ဖြင့် Task များ စစ်ဆေးနိုင်ပါပြီ။",
                    chat_id, 
                    call.message.message_id, 
                    parse_mode="Markdown"
                )
            else:
                bot.delete_message(chat_id, call.message.message_id)
                msg = bot.send_message(chat_id, "ℹ️ အီးမေးလ်ကို ပြန်လည်ရေးသားပေးပါရန်။")
                bot.register_next_step_handler(msg, process_email)

        # ----- Task Verify -----
        elif call.data.startswith("task_verify_"):
            choice = call.data.split("_")[2]
            if choice == "yes":
                if not can_submit_task(user_id):
                    today_count = get_task_count_today(user_id)
                    bot.answer_callback_query(
                        call.id, 
                        f"⚠️ ဒီနေ့ task {today_count} ခါ တင်ပြီးပါပြီ။ မနက်ဖြန် ပြန်လာခဲ့ပါ။", 
                        show_alert=True
                    )
                    return
                
                bot.answer_callback_query(call.id, "🚀 သက်သေကို Admin ထံ ပေးပို့နေပါပြီ...")
                
                photo_id = db.get(user_id, {}).get("last_photo_id")
                user_email = db.get(user_id, {}).get("email")
                name = db.get(user_id, {}).get("name", call.from_user.first_name)
                
                if not photo_id:
                    bot.edit_message_text(
                        "❌ Screenshot မတွေ့ရှိပါ။ `/check` ဖြင့် ပြန်လည်စတင်ပါ။",
                        chat_id, 
                        call.message.message_id
                    )
                    return
                
                current_time = datetime.now().strftime("%I:%M %p")
                current_date = datetime.now().strftime("%Y-%m-%d")
                user_mention = f"[{name}](tg://user?id={user_id})"
                
                admin_caption = (
                    f"📥 *Task စစ်ဆေးရန် တောင်းဆိုချက်*\n\n"
                    f"👤 *Name:* {user_mention}\n"
                    f"🆔 *ID:* `{user_id}`\n"
                    f"📧 *Gmail:* `{user_email}`\n"
                    f"⏰ *အချိန်:* {current_time} ({current_date})"
                )
                
                admin_markup = types.InlineKeyboardMarkup(row_width=2)
                btn_confirm = types.InlineKeyboardButton("✅ Confirm", callback_data=f"adm_confirm_{user_id}")
                btn_reject = types.InlineKeyboardButton("❌ Reject", callback_data=f"adm_reject_{user_id}")
                admin_markup.add(btn_confirm, btn_reject)
                
                success = send_to_admin_group(photo_id, admin_caption, admin_markup)
                
                if success:
                    user_reply = (
                        "✨ ━━━━━━━━━━━━━━━━━━ ✨\n"
                        "📩 *သင်၏ Task လုပ်ထားသော သက်သေကို Admin ထံသို့ ပို့ထားပြီးဖြစ်ပါသည်။*\n\n"
                        "⏰ ည (၈) နာရီ သို့မဟုတ် (၉) နာရီ ကြားတွင် စစ်ဆေးပြီး Coins ထည့်သွင်းပေးသွားမည် ဖြစ်ပါသည်ဗျာ။\n\n"
                        "🙏 *ကျေးဇူးအထူးတင်ရှိပါသည်ခင်ဗျာ!* ✨"
                    )
                    bot.edit_message_text(user_reply, chat_id, call.message.message_id, parse_mode="Markdown")
                    
                    db[user_id]["last_task_time"] = datetime.now().isoformat()
                    db[user_id]["task_count_today"] = db.get(user_id, {}).get("task_count_today", 0) + 1
                    db[user_id]["last_photo_id"] = None
                    save_db(db)
                else:
                    error_msg = (
                        f"❌ *Admin Group သို့ သက်သေလှမ်းပို့ခြင်း မအောင်မြင်ပါ!*\n\n"
                        f"💡 *ဖြေရှင်းနည်း:*\n"
                        f"၁။ Bot ကို Admin Group ထဲမှာ *Admin* အဖြစ် ခန့်ထားပါ။\n"
                        f"၂။ `ADMIN_GROUP_ID` နံပါတ် မှန်ကန်မှုရှိမရှိ စစ်ဆေးပါ။\n"
                        f"၃။ Group က Public ဖြစ်မဖြစ် စစ်ဆေးပါ။"
                    )
                    bot.edit_message_text(error_msg, chat_id, call.message.message_id, parse_mode="Markdown")
            else:
                bot.edit_message_text(
                    "❌ Task စစ်ဆေးမှုကို ဖျက်သိမ်းလိုက်ပါသည်။ `/check` ဖြင့် ပြန်လည်လုပ်ဆောင်နိုင်ပါသည်။",
                    chat_id, 
                    call.message.message_id
                )

        # ----- Admin Confirm -----
        elif call.data.startswith("adm_confirm_"):
            logger.info(f"✅ Confirm button clicked by admin: {call.from_user.id}")
            
            target_user_id = call.data.split("_")[2]
            admin_name = call.from_user.first_name
            admin_username = call.from_user.username or "No username"
            
            try:
                orig_caption = call.message.caption or ""
                updated_caption = f"{orig_caption}\n\n✅ *Confirmed by:* @{admin_username} ({admin_name})"
                
                bot.edit_message_caption(
                    caption=updated_caption,
                    chat_id=ADMIN_GROUP_ID, 
                    message_id=call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=None
                )
                
                user_markup = types.InlineKeyboardMarkup(row_width=1)
                btn_no_coin = types.InlineKeyboardButton("❌ Coin မရောက်ပါ", callback_data=f"user_nocoin_{target_user_id}")
                user_markup.add(btn_no_coin)
                
                success_msg = (
                    "🍬 ✨ *Candy Hub Notification* ✨ 🍬\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🎉 *Candy Hub မှ သင်၏ Task ကို အတည်ပြုလိုက်ပါသည်။*\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🧸 _ဆုကြေး Coins များကို အကောင့်ထဲသို့ ထည့်သွင်းပေးလိုက်ပါပြီဗျာ။_"
                )
                
                try:
                    bot.send_message(int(target_user_id), success_msg, parse_mode="Markdown", reply_markup=user_markup)
                except Exception as e:
                    logger.error(f"❌ Error sending to user: {e}")
                
                bot.answer_callback_query(call.id, "✅ အတည်ပြုပြီးပါပြီ။")
                
            except Exception as e:
                bot.answer_callback_query(call.id, f"❌ Error: {str(e)[:50]}", show_alert=True)

        # ----- Admin Reject -----
        elif call.data.startswith("adm_reject_"):
            logger.info(f"❌ Reject button clicked by admin: {call.from_user.id}")
            
            target_user_id = call.data.split("_")[2]
            admin_name = call.from_user.first_name
            admin_username = call.from_user.username or "No username"
            
            try:
                orig_caption = call.message.caption or ""
                updated_caption = f"{orig_caption}\n\n❌ *Rejected by:* @{admin_username} ({admin_name})"
                
                bot.edit_message_caption(
                    caption=updated_caption,
                    chat_id=ADMIN_GROUP_ID, 
                    message_id=call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=None
                )
                
                reject_msg = (
                    "⚠️ ━━━━━━━━━━━━━━━━━━ ⚠️\n"
                    "😭 *တောင်းပန်ပါတယ်ခင်ဗျာ...*\n"
                    "❌ *လူကြီးမင်း ပေးပို့ထားသော သက်သေသည် ပယ်ချခံရပါသည်။*\n\n"
                    "📸 _ကျေးဇူးပြု၍ ပုံကို သေချာပြန်လည်စစ်ဆေးပြီး မှန်ကန်စွာ ပြန်လည်ပေးပို့ပေးပါဦးနော်။_"
                )
                
                try:
                    bot.send_message(int(target_user_id), reject_msg, parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"❌ Error sending to user: {e}")
                
                bot.answer_callback_query(call.id, "✅ ပယ်ချပြီးပါပြီ။")
                
            except Exception as e:
                bot.answer_callback_query(call.id, f"❌ Error: {str(e)[:50]}", show_alert=True)

        # ----- User No Coin -----
        elif call.data.startswith("user_nocoin_"):
            target_user_id = call.data.split("_")[2]
            user_info = db.get(target_user_id, {})
            user_name = user_info.get('name', 'Unknown')
            user_email = user_info.get('email', 'No email')
            
            to_gp_markup = types.InlineKeyboardMarkup(row_width=1)
            btn_fixed = types.InlineKeyboardButton("✅ Confirm / Fixed", callback_data=f"adm_fixed_{target_user_id}")
            to_gp_markup.add(btn_fixed)
            
            alert_gp_text = (
                f"⚠️ 🔔 *🚨 COIN NOT RECEIVED ALERT 🚨*\n\n"
                f"👤 *User:* {user_name}\n"
                f"📧 *Email:* `{user_email}`\n\n"
                f"❗ *သည် Coin မရရှိသေးပါ။ ပြန်လည်စစ်ဆေးပေးပါ။*"
            )
            
            try:
                bot.send_message(ADMIN_GROUP_ID, alert_gp_text, parse_mode="Markdown", reply_markup=to_gp_markup)
                bot.answer_callback_query(call.id, "✅ Admin ထံ တင်ပြပေးလိုက်ပါပြီ။", show_alert=True)
            except Exception as e:
                logger.error(f"❌ Error sending no coin alert: {e}")

        # ----- Admin Fixed -----
        elif call.data.startswith("adm_fixed_"):
            target_user_id = call.data.split("_")[2]
            
            try:
                bot.edit_message_text(
                    f"✅ User ID `{target_user_id}` အတွက် Coins ပြဿနာကို ဖြေရှင်းပြီးပါပြီ။",
                    ADMIN_GROUP_ID, 
                    call.message.message_id
                )
            except Exception as e:
                logger.error(f"❌ Error editing message: {e}")
            
            apology_msg = (
                "🥺 ━━━━━━━━━━━━━━━━━━ 🥺\n"
                "💖 *ချစ်လှစွာသော User ခင်ဗျာ...*\n"
                "📬 *တောင်းပန်ပါတယ်နော်။ စနစ်ပိုင်းအမှားအယွင်းကြောင့် လွဲချော်သွားလို့ပါဗျာ။*\n\n"
                "✨ _ယခုအခါ Coins များကို သေချာပေါက် ဖြည့်သွင်းပေးပြီးဖြစ်လို့ ပြန်လည်စစ်ဆေးပေးပါဦးခင်ဗျာ။_ 🙏"
            )
            
            try:
                bot.send_message(int(target_user_id), apology_msg, parse_mode="Markdown")
                bot.answer_callback_query(call.id, "✅ User ကို အကြောင်းကြားပြီးပါပြီ။")
            except Exception as e:
                logger.error(f"❌ Error sending apology: {e}")

        # ----- Trigger Check from Profile -----
        elif call.data == "trigger_check":
            bot.delete_message(call.message.chat.id, call.message.message_id)
            check_cmd(call.message)
            
    except Exception as e:
        logger.error(f"❌ Callback error: {e}")
        try:
            bot.answer_callback_query(call.id, f"❌ Error: {str(e)[:50]}", show_alert=True)
        except:
            pass

# ============================================
#  EMAIL PROCESS
# ============================================
def ask_email(message):
    try:
        msg = bot.send_message(
            message.chat.id, 
            "📧 *သင်၏ Candy Hub Acc ထဲသို့ Coin လှမ်းထည့်မည့် Email (အသေ) ကို ရေးသားပေးပါ၊ မမှားပါစေနှင့်။*",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_email)
    except Exception as e:
        msg = bot.send_message(message.chat.id, "📧 သင်၏ Candy Hub Acc ထဲသို့ Coin လှမ်းထည့်မည့် Email (အသေ) ကို ရေးသားပေးပါ၊ မမှားပါစေနှင့်။")
        bot.register_next_step_handler(msg, process_email)

def process_email(message):
    email = message.text.strip()
    if "@" not in email or "." not in email:
        msg = bot.send_message(
            message.chat.id, 
            "❌ အီးမေးလ်ပုံစံ မမှန်ကန်ပါ။ ပြန်လည်ရိုက်ထည့်ပေးပါ။"
        )
        bot.register_next_step_handler(msg, process_email)
        return
    
    # ❗ Save email temporarily in DB instead of putting it in callback_data
    user_id = str(message.chat.id)
    db = load_db()
    if user_id not in db:
        db[user_id] = {"name": message.from_user.first_name, "email": None, "task_count_today": 0}
    db[user_id]["pending_email"] = email
    save_db(db)
        
    markup = types.InlineKeyboardMarkup(row_width=2)
    # ❗ callback_data limit (64 bytes) ကိုမကျော်စေရန် data အတိုသာသုံးထားသည်
    markup.add(
        types.InlineKeyboardButton("✅ Yes", callback_data="confirm_email_yes"),
        types.InlineKeyboardButton("❌ No", callback_data="confirm_email_no")
    )
    
    bot.send_message(
        message.chat.id, 
        f"❓ လူကြီးမင်းရိုက်ထည့်လိုက်သော Email မှာ `{email}` ဖြစ်ပါသည်။ သေချာပါသလားဗျာ?",
        parse_mode="Markdown", 
        reply_markup=markup
    )

# ============================================
#  /profile COMMAND
# ============================================
@bot.message_handler(commands=['profile'])
def profile_cmd(message):
    user_id = str(message.from_user.id)
    db = load_db()
    
    if user_id not in db or not db[user_id].get("email"):
        bot.send_message(
            message.chat.id, 
            "⚠️ လူကြီးမင်း အီးမေးလ် မမှတ်ပုံတင်ရသေးပါ။ `/start` ကိုနှိပ်ပါ။"
        )
        return

    profile_text = (
        f"👤 ══ *YOUR PROFILE* ══ 👤\n\n"
        f"📛 *Name -* {db[user_id]['name']}\n"
        f"📧 *Email (အသေ) -* `{db[user_id]['email']}`"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📝 Task စစ်ဆေးရန်", callback_data="trigger_check"))
    bot.send_message(message.chat.id, profile_text, parse_mode="Markdown", reply_markup=markup)

# ============================================
#  /check COMMAND
# ============================================
@bot.message_handler(commands=['check'])
def check_cmd(message):
    user_id = str(message.chat.id)
    db = load_db()
    
    if user_id not in db or not db[user_id].get("email"):
        bot.send_message(
            message.chat.id, 
            "⚠️ ကျေးဇူးပြု၍ `/start` တွင် Email သတ်မှတ်ပေးပါ။"
        )
        return
    
    if not can_submit_task(user_id):
        today_count = get_task_count_today(user_id)
        bot.send_message(
            message.chat.id,
            f"⚠️ ဒီနေ့ task {today_count} ခါ တင်ပြီးပါပြီ။\n\n"
            f"📅 မနက်ဖြန် ပြန်လာခဲ့ပါဦးဗျာ။ 🙏"
        )
        return
        
    msg = bot.send_message(
        message.chat.id, 
        "📸 *သင်၏ Download ဆွဲထားသော APK ပါသည့် Screenshot ပုံလေးကို ပို့ပေးပါရန်။*",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_screenshot)

def process_screenshot(message):
    if not message.photo:
        msg = bot.send_message(
            message.chat.id, 
            "❌ ပုံစံမမှန်ကန်ပါ။ ကျေးဇူးပြု၍ Screenshot ဓာတ်ပုံကိုသာ ပို့ပေးပါ။"
        )
        bot.register_next_step_handler(msg, process_screenshot)
        return
        
    user_id = str(message.chat.id)
    db = load_db()
    
    photo_id = message.photo[-1].file_id
    db[user_id]["last_photo_id"] = photo_id
    save_db(db)
    
    user_email = db[user_id]["email"]
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Yes", callback_data="task_verify_yes"),
        types.InlineKeyboardButton("❌ No", callback_data="task_verify_no")
    )
    
    verify_text = (
        f"🧐 *သက်သေခံပုံနှင့် ပုံသေ Email ကို တိုက်ဆိုင်စစ်ဆေးခြင်း*\n\n"
        f"📧 လူကြီးမင်း၏ ပုံသေ Email ဖြစ်သော `{user_email}` သည် မှန်ကန်ပါသလားဗျာ?"
    )
    bot.send_message(message.chat.id, verify_text, parse_mode="Markdown", reply_markup=markup)

# ============================================
#  MAIN RUNNER
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("🍬 Candy Hub Bot စတင်နေပါပြီ...")
    print(f"🤖 Bot Token: {BOT_TOKEN[:10]}...")
    print(f"📢 Admin Group ID: {ADMIN_GROUP_ID}")
    print("=" * 50)
    
    # Flask server ကို background thread မှာ run
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    print("✅ Flask server started")

    # Self-ping ကို background thread မှာ run
    ping_thread = threading.Thread(target=ping_self)
    ping_thread.daemon = True
    ping_thread.start()
    print("✅ Self-ping system started")

    print("=" * 50)
    print("🤖 Bot is now running...")
    print("=" * 50)
    
    # Remove webhook and use polling
    try:
        bot.remove_webhook()
        print("✅ Webhook removed successfully")
    except Exception as e:
        print(f"⚠️ Webhook removal error: {e}")
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"⚠️ Polling error: {e}")
            print("🔄 5 seconds နောက် ပြန်စတင်မည်...")
            time.sleep(5)
