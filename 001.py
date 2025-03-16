import logging
import re
import json
import time
import asyncio
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.functions.account import UpdateProfileRequest

# اطلاعات API تلگرام
api_id = 28039994
api_hash = '00877cdcd706564a4de6abf7f7d64349'
client = TelegramClient('session', api_id, api_hash)

# لیست آیدی‌های مجاز
allowed_users = {7429570175, 6824031586}  # آیدی‌های عددی مجاز

# متغیرها
spam_text = "متن اسپم تنظیم نشده"

# بارگیری لیست دشمنان و دوستان از فایل
def load_data():
    try:
        with open("data.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {"enemies": {}, "friends": {}}

def save_data():
    with open("data.json", "w", encoding="utf-8") as file:
        json.dump({"enemies": enemies, "friends": friends}, file, ensure_ascii=False, indent=4)

data = load_data()
enemies = data["enemies"]
friends = data["friends"]

enemy_responses = ["پیام پیش‌فرض برای بدخاها"]
friend_responses = ["پیام پیش‌فرض برای مشتی‌ها"]
user_response_queue = {}

is_time_enabled = False
current_time_str = ""

# متغیر برای کنترل اسپم
spamming = False

# تابع ارسال متن اسپم
async def send_spam(event):
    global spam_text, spamming
    if spamming:
        await event.reply("⚠️ اسپم از قبل فعاله!")
        return
    
    spamming = True
    await event.reply("✅ اسپم فعال شد! برای توقف، دستور 'اسپم غیر فعال' رو بزنید.")

    while spamming:
        await event.reply(spam_text)
        await asyncio.sleep(3)  # هر 3 ثانیه ارسال خواهد شد

# توقف اسپم
async def stop_spam(event):
    global spamming
    spamming = False
    await event.reply("🛑 اسپم غیر فعال شد.")

# تنظیم متن اسپم
async def set_spam_text(event):
    global spam_text
    new_text = event.raw_text.split("تنظیم متن اسپم", 1)[1].strip()
    if new_text:
        spam_text = new_text
        await event.reply(f"✅ متن اسپم به: {spam_text} تغییر کرد.")
    else:
        await event.reply("❌ لطفاً یک متن برای اسپم وارد کنید.")

# تابع برای ذخیره مدیا
async def save_media_to_saved(event):
    if event.is_reply:
        replied_message = await event.get_reply_message()
        if event.raw_text.strip().lower() == "سیو" and replied_message.media:
            try:
                await event.message.delete()
                await client.send_file('me', replied_message.media)
                await client.send_message('me', "مدیا مورد نظر با موفقیت ذخیره شد✓")
            except Exception as e:
                print(f"خطا در پردازش مدیا: {e}")

# تابع برای تغییر نام
async def handle_name_change(event):
    match = re.match(r"اسم عوض بشه به (.+)", event.raw_text)
    if match:
        new_name = match.group(1)
        try:
            await client(UpdateProfileRequest(first_name=new_name))
            await event.respond("اسم شما تغییر کرد✓")
        except Exception as e:
            logging.error(f"خطا در تغییر نام: {e}")

# تابع برای ارسال آیدی کاربر
async def send_user_id(event):
    if event.is_reply:
        replied_message = await event.get_reply_message()
        await event.reply(f"آیدی عددی این فرد: {replied_message.sender_id}")

# اضافه کردن دشمن
async def add_enemy(event):
    if event.is_reply:
        replied_message = await event.get_reply_message()
        user_id = str(replied_message.sender_id)
        enemies[user_id] = True
        save_data()
        await event.reply("کاربر به عنوان بدخا ثبت شد✓")

# حذف دشمن
async def remove_enemy(event):
    if event.is_reply:
        replied_message = await event.get_reply_message()
        user_id = str(replied_message.sender_id)
        if user_id in enemies:
            del enemies[user_id]
            save_data()
            await event.reply("کاربر از لیست بدخاها حذف شد✓")

# اضافه کردن دوست
async def add_friend(event):
    if event.is_reply:
        replied_message = await event.get_reply_message()
        user_id = str(replied_message.sender_id)
        friends[user_id] = True
        save_data()
        await event.reply("کاربر به عنوان مشتی ثبت شد✓")

# حذف دوست
async def remove_friend(event):
    if event.is_reply:
        replied_message = await event.get_reply_message()
        user_id = str(replied_message.sender_id)
        if user_id in friends:
            del friends[user_id]
            save_data()
            await event.reply("کاربر از لیست مشتی‌ها حذف شد✓")

# نمایش اطلاعات کاربر
async def get_user_info(event):
    if event.is_reply:
        replied_message = await event.get_reply_message()
        user = await client.get_entity(replied_message.sender_id)

        username = f"@{user.username}" if user.username else "ندارد"
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        user_id = user.id
        last_seen = "نامشخص"

        if user.status:
            if hasattr(user.status, 'was_online'):
                last_seen = f"آخرین بازدید: {user.status.was_online}"
            elif hasattr(user.status, 'expires'):
                last_seen = f"آنلاین تا: {user.status.expires}"

        response_text = f"""
📌 اطلاعات کاربر:
👤 نام: {full_name}
🆔 آیدی: {username}
🔢 آیدی عددی: {user_id}
⏳ آخرین بازدید: {last_seen}
        """
        await event.reply(response_text.strip())

# تابع بروزرسانی ساعت
async def update_time():
    global is_time_enabled, current_time_str
    while True:
        if is_time_enabled:
            current_time_str = datetime.now().strftime("%H:%M")
        await asyncio.sleep(60)

# نمایش ساعت در کنار نام کاربری
async def show_time_in_username():
    while True:
        if is_time_enabled:
            try:
                user = await client.get_me()
                original_name = user.first_name.split("|")[0].strip()  # حذف ساعت قبلی
                new_name = f"{original_name} | ⏰ {current_time_str}"
                await client(UpdateProfileRequest(first_name=new_name))
            except Exception as e:
                logging.error(f"خطا در تغییر نام برای نمایش ساعت: {e}")
        
        await asyncio.sleep(60)

# هندل کردن پیام‌ها
@client.on(events.NewMessage)
async def handler(event):
    sender_id = event.sender_id
    message_text = event.raw_text.lower()

    if sender_id not in allowed_users:
        return  

    commands = {
        "دستورات": send_and_replace_command_list,
        "سیو": save_media_to_saved,
        "ایدی": send_user_id,
        "تنظیم بدخا": add_enemy,
        "حذف بدخا": remove_enemy,
        "تنظیم مشتی": add_friend,
        "حذف مشتی": remove_friend,
        "اطلاعات": get_user_info,
        "تایم روشن": turn_on_time,
        "تایم خاموش": turn_off_time,
        "اسپم فعال": send_spam,
        "اسپم غیر فعال": stop_spam,
    }

    if message_text.startswith("اسم عوض بشه"):
        await handle_name_change(event)
    elif message_text in commands:
        await commands[message_text](event)
    elif message_text.startswith("تنظیم متن اسپم"):
        await set_spam_text(event)  # تنظیم متن اسپم

# روشن کردن ساعت
async def turn_on_time(event):
    global is_time_enabled
    is_time_enabled = True
    await event.reply("ساعت روشن شد. هر 60 ثانیه به روزرسانی خواهد شد.")

# خاموش کردن ساعت
async def turn_off_time(event):
    global is_time_enabled
    is_time_enabled = False
    await event.reply("ساعت خاموش شد.")

# ارسال لیست دستورات
async def send_and_replace_command_list(event):
    command_list_text = """
📜 لیست دستورات:
🟥 تنظیم بدخا (ریپلای کنید)
🟩 حذف بدخا (ریپلای کنید)
🟦 تنظیم مشتی (ریپلای کنید)
🟧 حذف مشتی (ریپلای کنید)
📥 سیو
✏️ اسم عوض بشه به x
🔢 ایدی
📌 اطلاعات (ریپلای کنید)
⏰ تایم روشن
⏸️ تایم خاموش
🕹️ اسپم فعال
🛑 اسپم غیر فعال
📝 تنظیم متن اسپم
    """
    await event.reply(command_list_text)

# اجرای اصلی برنامه
async def main():
    await client.start()
    print("Bot is running...")
    client.loop.create_task(update_time())  # شروع بروزرسانی ساعت
    client.loop.create_task(show_time_in_username())  # نمایش ساعت در کنار نام
    await client.run_until_disconnected()

client.loop.run_until_complete(main())