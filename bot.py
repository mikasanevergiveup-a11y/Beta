import telebot
from telebot import types
from datetime import datetime
import json
import os
import threading
import time
import requests
from flask import Flask

# --- Render ရဲ့ Environment Variables မှ ဖတ်ယူခြင်း ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_GROUP_ID_STR = os.environ.get("ADMIN_GROUP_ID")
ADMIN_GROUP_ID = int(ADMIN_GROUP_ID_STR) if ADMIN_GROUP_ID_STR else 0

bot = telebot.TeleBot(BOT_TOKEN)
DB_FILE = "user_database.json"

# Channels အချက်အလက်များ
CHANNEL_1_ID = "@CandyHub_Ch"
CHANNEL_2_ID = "@candyhubassissiant"
CHANNEL_1_URL = "https://t.me/CandyHub_Ch"
CHANNEL_2_URL = "https://t.me/candyhubassissiant"

# --- 🌐 KEEP-ALIVE SERVER (FLASK & SELF-PING) SECTION ---
app = Flask('')

@app.route('/')
def home():
    return "Candy Hub Bot is alive and running smoothly! 🚀"

def ping_self():
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        print("⚠️ RENDER_EXTERNAL_URL မတွေ့ရှိပါ။ Self-ping စနစ်ကို ခေတ္တပိတ်ထားပါသည်။")
        return
    
    print(f"🔄 Self-ping စနစ် စတင်ပါပြီ။ URL: {url}")
    while True:
        time.sleep(600)  # ၁၀ မိနစ်တစ်ကြိမ်
        try:
            response = requests.get(url)
            print(f"🟢 Ping အောင်မြင်သည် - Status Code: {response.status_code}")
        except Exception as e:
            print(f"🔴 Ping ရန် ကြိုးစားမှု ပျက်ကွက်သည်: {e}")

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- 💾 DATABASE HELPER FUNCTIONS ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}
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
        print(f"Error checking status: {e}")
        return False

# ==================== /start Command ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = str(message.from_user.id)
    first_name = message.from_user.first_name
    
    db = load_db()
    if user_id not in db:
        db[user_id] = {"name": first_name, "email": None, "username": message.from_user.username or "မရှိပါ"}
        save_db(db)

    welcome_text = (
        f"👋 ✨ **မင်္ဂလာပါ {first_name}** ✨\n\n"
        f"🤖 Bot ကို အသုံးပြုရန် အောက်ပါ Channels (၂) ခုလုံးကို Join ပေးပါရန် လိုအပ်ပါတယ်ဗျာ။ 👇"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("🌐 ခလုတ် ၁ (CandyHub Ch)", url=CHANNEL_1_URL)
    btn2 = types.InlineKeyboardButton("🌐 ခလုတ် ၂ (CandyHub Assistant)", url=CHANNEL_2_URL)
    btn_check = types.InlineKeyboardButton("🔄 Check Status", callback_data="check_channels")
    markup.add(btn1, btn2, btn_check)
    
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)

# ==================== Callback Query Handler ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = str(call.from_user.id)
    chat_id = call.message.chat.id
    db = load_db()

    if call.data == "check_channels":
        if check_status(call.from_user.id):
            bot.answer_callback_query(call.id, "✅ ချန်နယ်များအားလုံး Join ပြီးပါပြီ။")
            ask_email(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ ချန်နယ် (၂) ခုလုံးကို မဝင်ရသေးပါဗျာ။", show_alert=True)

    elif call.data.startswith("confirm_email_"):
        choice = call.data.split("_")[2]
        temp_email = call.data.split("_")[3]
        
        if choice == "yes":
            db[user_id]["email"] = temp_email
            save_db(db)
            bot.edit_message_text(f"🎉 **အီးမေးလ် အတည်ပြုသိမ်းဆည်းပြီးပါပြီ!**\n💾 Email: `{temp_email}`\n\n👉 ယခုမှစ၍ `/profile` သို့မဟုတ် `/check` ဟုရိုက်နှိပ်ကာ Task များ စစ်ဆေးနိုင်ပါပြီ။", chat_id, call.message.message_id, parse_mode="Markdown")
        else:
            bot.delete_message(chat_id, call.message.message_id)
            msg = bot.send_message(chat_id, "ℹ️ အီးမေးလ်ကို ပြန်လည်ရေးသားပေးပါရန်။")
            bot.register_next_step_handler(msg, process_email)

    elif call.data.startswith("task_verify_"):
        choice = call.data.split("_")[2]
        if choice == "yes":
            bot.answer_callback_query(call.id, "🚀 သက်သေကို Admin ထံ ပေးပို့နေပါပြီ...")
            
            photo_id = db[user_id].get("last_photo_id")
            user_email = db[user_id].get("email")
            name = db[user_id].get("name", call.from_user.first_name)
            
            # Screenshot ထဲကအတိုင်း ပုံစံညှိခြင်း (YYYY-MM-DD HH:MM:SS)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 🖼️ Screenshot ပါ စာသားပုံစံအတိုင်း ကွက်တိ ပြင်ဆင်ထားသောနေရာ
            admin_caption = (
                f"📥 Task 1 စစ်ဆေးရန် တောင်းဆိုချက်\n\n"
                f"👤 Name: {name}\n"
                f"🆔 ID: {user_id}\n"
                f"📧 Gmail: {user_email}\n"
                f"🔑 Pass: မသတ်မှတ်ရသေး\n"
                f"⏰ အချိန်: {current_time}"
            )
            
            admin_markup = types.InlineKeyboardMarkup()
            btn_confirm = types.InlineKeyboardButton("✅ Confirm", callback_data=f"adm_confirm_{user_id}")
            btn_reject = types.InlineKeyboardButton("❌ Reject", callback_data=f"adm_reject_{user_id}")
            admin_markup.add(btn_confirm, btn_reject)
            
            # 🛡️ Group ထဲသို့ ပို့မရပါက ဘာကြောင့်လဲဆိုတာသိအောင် Error Catch လုပ်ထားခြင်း
            try:
                bot.send_photo(ADMIN_GROUP_ID, photo_id, caption=admin_caption, reply_markup=admin_markup)
                
                user_reply = (
                    "✨ ━━━━━━━━━━━━━━━━━━ ✨\n"
                    "📩 **သင်၏ Task လုပ်ထားသောသက်သေကို Admin ထံသို့ ပို့ထားပြီးဖြစ်ပါသည်။**\n\n"
                    "⏰ ည (၈) နာရီ သို့မဟုတ် (၉) နာရီ ကြားတွင် စစ်ဆေးပြီး Coins ထည့်သွင်းပေးသွားမည် ဖြစ်ပါသည်ဗျာ။\n\n"
                    "🙏 **ကျေးဇူးအထူးတင်ရှိပါသည်ခင်ဗျာ!** ✨"
                )
                bot.edit_message_text(user_reply, chat_id, call.message.message_id, parse_mode="Markdown")
            
            except Exception as e:
                print(f"🔴 Admin Group သို့ ပို့မရပါ: {e}")
                error_msg = (
                    f"❌ **Admin Group သို့ သက်သေလှမ်းပို့ခြင်း မအောင်မြင်ပါ!**\n\n"
                    f"⚠️ **အကြောင်းရင်း:** `{e}`\n\n"
                    f"💡 **ဖြေရှင်းနည်း:**\n"
                    f"၁။ သင့် Bot ကို အုပ်ချုပ်သူ Group ထဲမှာ **Admin** အဖြစ် ခန့်ထားပေးရပါမယ်။\n"
                    f"၂။ Render Environment ထဲက `ADMIN_GROUP_ID` နံပါတ် မှန်ကန်မှုရှိမရှိ ပြန်စစ်ပေးပါ။ (အရှေ့က အနှုတ်လက္ခဏာ `-` ပါရပါမယ်)"
                )
                bot.edit_message_text(error_msg, chat_id, call.message.message_id, parse_mode="Markdown")
        else:
            bot.edit_message_text("❌ Task စစ်ဆေးမှုကို ဖျက်သိမ်းလိုက်ပါသည်။ `/check` ဖြင့် ပြန်လည်လုပ်ဆောင်နိုင်ပါသည်။", chat_id, call.message.message_id)

    elif call.data.startswith("adm_confirm_"):
        target_user_id = call.data.split("_")[2]
        admin_name = call.from_user.first_name
        
        orig_caption = call.message.caption or ""
        updated_caption = f"{orig_caption}\n\n👮 **Confirmed by:** {admin_name} ✅"
        bot.edit_message_caption(updated_caption, ADMIN_GROUP_ID, call.message.message_id, reply_markup=None)
        
        user_markup = types.InlineKeyboardMarkup()
        btn_no_coin = types.InlineKeyboardButton("❌ Coin မရောက်ပါ", callback_data=f"user_nocoin_{target_user_id}")
        user_markup.add(btn_no_coin)
        
        success_msg = (
            "🍬 ✨ **Candy Hub Notification** ✨ 🍬\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎉 **ဂုဏ်ယူပါသည်! Candy Hub မှ လူကြီးမင်း၏ Task ကို အောင်မြင်စွာ အတည်ပြုလိုက်ပါပြီ။**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🧸 _ဆုကြေး Coins များကို အကောင့်ထဲသို့ ထည့်သွင်းပေးလိုက်ပါပြီဗျာ။_"
        )
        bot.send_message(int(target_user_id), success_msg, parse_mode="Markdown", reply_markup=user_markup)

    elif call.data.startswith("adm_reject_"):
        target_user_id = call.data.split("_")[2]
        admin_name = call.from_user.first_name
        
        orig_caption = call.message.caption or ""
        updated_caption = f"{orig_caption}\n\n❌ **Rejected by:** {admin_name}"
        bot.edit_message_caption(updated_caption, ADMIN_GROUP_ID, call.message.message_id, reply_markup=None)
        
        reject_msg = (
            "⚠️ ━━━━━━━━━━━━━━━━━━ ⚠️\n"
            "😭 **တောင်းပန်ပါတယ်ခင်ဗျာ...**\n"
            "❌ **လူကြီးမင်း ပေးပို့ထားသော သက်သေသည် ပယ်ချခံရပါသည်။**\n\n"
            "📸 _ကျေးဇူးပြု၍ ပုံကို သေချာပြန်လည်စစ်ဆေးပြီး မှန်ကန်စွာ ပြန်လည်ပေးပို့ပေးပါဦးနော်။_\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(int(target_user_id), reject_msg, parse_mode="Markdown")

    elif call.data.startswith("user_nocoin_"):
        target_user_id = call.data.split("_")[2]
        user_info = db.get(target_user_id, {})
        
        to_gp_markup = types.InlineKeyboardMarkup()
        btn_fixed = types.InlineKeyboardButton("✅ Confirm / Fixed", callback_data=f"adm_fixed_{target_user_id}")
        to_gp_markup.add(btn_fixed)
        
        alert_gp_text = (
            f"⚠️ 🔔 **🚨 COIN NOT RECEIVED ALERT 🚨**\n\n"
            f"👤 **User:** {user_info.get('name')} ( ID: `{target_user_id}` )\n"
            f"📧 **Email:** `{user_info.get('email')}`\n\n"
            f"❗ **သည် Coin မရရှိသေးပါ။ ပြန်လည်စစ်ဆေးပေးပါ။**"
        )
        bot.send_message(ADMIN_GROUP_ID, alert_gp_text, parse_mode="Markdown", reply_markup=to_gp_markup)
        bot.answer_callback_query(call.id, "✅ မှတ်ချက်ကို Admin ထံ တင်ပြပေးလိုက်ပါပြီ။", show_alert=True)

    elif call.data.startswith("adm_fixed_"):
        target_user_id = call.data.split("_")[2]
        bot.edit_message_text(f"✅ User ID `{target_user_id}` အတွက် Coins ပြဿနာကို ဖြေရှင်းပြီးပါပြီ။", ADMIN_GROUP_ID, call.message.message_id)
        
        apology_msg = (
            "🥺 ━━━━━━━━━━━━━━━━━━ 🥺\n"
            "💖 **ချစ်လှစွာသော User ခင်ဗျာ...**\n"
            "📬 **တောင်းပန်ပါတယ်နော်။ စနစ်ပိုင်းအမှားအယွင်းကြောင့် လွဲချော်သွားလို့ပါဗျာ။**\n\n"
            "✨ _ယခုအခါ Coins များကို သေချာပေါက် ဖြည့်သွင်းပေးပြီးဖြစ်လို့ ပြန်လည်စစ်ဆေးပေးပါဦးခင်ဗျာ။_ 🙏"
        )
        bot.send_message(int(target_user_id), apology_msg, parse_mode="Markdown")

# ==================== Email Process Flow ====================
def ask_email(message):
    msg = bot.send_message(message.chat.id, "📧 **သင်၏ Candy Hub Acc ထဲသို့ Coin လှမ်းထည့်မည့် Email (အသေ) ကို ရေးသားပေးပါ၊ မမှားပါစေနှင့်။**")
    bot.register_next_step_handler(msg, process_email)

def process_email(message):
    email = message.text.strip()
    if "@" not in email or "." not in email:
        msg = bot.send_message(message.chat.id, "❌ အီးမေးလ်ပုံစံ မမှန်ကန်ပါ။ ပြန်လည်ရိုက်ထည့်ပေးပါ။")
        bot.register_next_step_handler(msg, process_email)
        return
        
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Yes", callback_data=f"confirm_email_yes_{email}"),
               types.InlineKeyboardButton("❌ No", callback_data=f"confirm_email_no_{email}"))
    
    bot.send_message(message.chat.id, f"❓ လူကြီးမင်းရိုက်ထည့်လိုက်သော Email မှာ `{email}` ဖြစ်ပါသည်။ သေချာပါသလားဗျာ?", parse_mode="Markdown", reply_markup=markup)

# ==================== /profile Command ====================
@bot.message_handler(commands=['profile'])
def profile_cmd(message):
    user_id = str(message.from_user.id)
    db = load_db()
    
    if user_id not in db or not db[user_id].get("email"):
        bot.send_message(message.chat.id, "⚠️ လူကြီးမင်း အီးမေးလ် မမှတ်ပုံတင်ရသေးပါ။ လော့ဂ်အင်ပြန်ဝင်ရန် `/start` ကိုနှိပ်ပါ။")
        return

    profile_text = (
        f"👤 ══ **YOUR PROFILE** ══ 👤\n\n"
        f"📛 **Name -** {db[user_id]['name']}\n"
        f"📧 **Email (အသေ) -** `{db[user_id]['email']}`"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📝 Task စစ်ဆေးရန်", callback_data="trigger_check"))
    bot.send_message(message.chat.id, profile_text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "trigger_check")
def trigger_check_btn(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    check_cmd(call.message)

# ==================== /check Command ====================
@bot.message_handler(commands=['check'])
def check_cmd(message):
    user_id = str(message.chat.id)
    db = load_db()
    
    if user_id not in db or not db[user_id].get("email"):
        bot.send_message(message.chat.id, "⚠️ ကျေးဇူးပြု၍ ပထမဦးစွာ `/start` တွင် Email သတ်မှတ်ပေးပါ။")
        return
        
    msg = bot.send_message(message.chat.id, "📸 **သင်၏ Download ဆွဲထားသော APK ပါသည့် Screenshot ပုံလေးကို ပို့ပေးပါရန်။**")
    bot.register_next_step_handler(msg, process_screenshot)

def process_screenshot(message):
    if not message.photo:
        msg = bot.send_message(message.chat.id, "❌ ပုံစံမမှန်ကန်ပါ။ ကျေးဇူးပြု၍ Screenshot ဓာတ်ပုံကိုသာ ပို့ပေးပါ။")
        bot.register_next_step_handler(msg, process_screenshot)
        return
        
    user_id = str(message.chat.id)
    db = load_db()
    
    photo_id = message.photo[-1].file_id
    db[user_id]["last_photo_id"] = photo_id
    save_db(db)
    
    user_email = db[user_id]["email"]
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Yes", callback_data="task_verify_yes"),
               types.InlineKeyboardButton("❌ No", callback_data="task_verify_no"))
    
    verify_text = (
        f"🧐 **သက်သေခံပုံနှင့် ပုံသေ Email ကို တိုက်ဆိုင်စစ်ဆေးခြင်း**\n\n"
        f"📧 လူကြီးမင်း၏ ပုံသေ Email ဖြစ်သော `{user_email}` သည် မှန်ကန်ပါသလားခင်ဗျာ?"
    )
    bot.send_message(message.chat.id, verify_text, parse_mode="Markdown", reply_markup=markup)

# ==================== 🚀 MAIN RUNNER SECTION ====================
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    ping_thread = threading.Thread(target=ping_self)
    ping_thread.daemon = True
    ping_thread.start()

    print("🤖 Keep-Alive စနစ်ပါဝင်သော Candy Hub Bot စတင်အလုပ်လုပ်နေပါပြီ...")
    bot.infinity_polling()

