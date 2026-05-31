# Minecraft Bedrock Mods Bot
import asyncio
import json
import os
import re
import aiohttp
import aiofiles
from datetime import datetime
from telegram import (
    Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "123456789").split(",")]
DATA_FILE = "data.json"
DOWNLOADS_DIR = "downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
MCPEDL_BASE = "https://mcpedl.com"
MCPEDL_MODS = "https://mcpedl.com/category/mods/"
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "channels": [],
        "interval_hours": 6,
        "mods_per_post": 1,
        "auto_post": False,
        "posted_mods": [],
        "last_check": None
    }

def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def scrape_latest_mods(count: int = 5) -> list:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    mods = []
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(MCPEDL_MODS, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()
        except Exception as e:
            print(f"[SCRAPER] Error: {e}")
            return []
    pattern = re.compile(
        r'<article[^>]*class="[^"]*bp-entry[^"]*"[^>]*>(.*?)</article>',
        re.DOTALL
    )
    cards = pattern.findall(html)
    for card in cards[:count * 2]:
        try:
            title_match = re.search(r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', card)
            if not title_match:
                continue
            url = title_match.group(1)
            name = title_match.group(2).strip()
            img_match = re.search(r'<img[^>]*src="([^"]+)"[^>]*>', card)
            img_url = img_match.group(1) if img_match else None
            if img_url and img_url.startswith("//"):
                img_url = "https:" + img_url
            if img_url and not img_url.startswith("http"):
                img_url = MCPEDL_BASE + img_url
            mods.append({"name": name, "url": url, "image": img_url, "fetched_at": datetime.now().isoformat()})
            if len(mods) >= count:
                break
        except Exception:
            continue
    return mods
  async def get_mod_download_link(mod_url: str) -> str | None:
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(mod_url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
        except Exception:
            return None
    dl_match = re.search(r'href="([^"]*(?:\.mcpack|\.mcaddon|\.zip)[^"]*)"', html, re.IGNORECASE)
    return dl_match.group(1) if dl_match else None

async def download_file(url: str, name: str) -> str | None:
    safe_name = re.sub(r'[^\w\-.]', '_', name)
    ext = url.split("?")[0].split(".")[-1]
    if ext not in ("mcpack", "mcaddon", "zip"):
        ext = "mcpack"
    path = os.path.join(DOWNLOADS_DIR, f"{safe_name}.{ext}")
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    return None
                async with aiofiles.open(path, "wb") as f:
                    await f.write(await resp.read())
            return path
        except Exception as e:
            print(f"[DOWNLOAD] Error: {e}")
            return None

async def download_image(url: str, name: str) -> str | None:
    safe_name = re.sub(r'[^\w\-.]', '_', name)
    path = os.path.join(DOWNLOADS_DIR, f"{safe_name}_thumb.jpg")
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    return None
                async with aiofiles.open(path, "wb") as f:
                    await f.write(await resp.read())
            return path
        except Exception:
          def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 إدارة القنوات", callback_data="channels_menu"),
         InlineKeyboardButton("🎮 جلب مودات", callback_data="fetch_mods")],
        [InlineKeyboardButton("⏰ إعدادات النشر", callback_data="settings_menu"),
         InlineKeyboardButton("🔄 حالة النشر التلقائي", callback_data="toggle_auto")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")]
    ])

def channels_keyboard(channels: list):
    buttons = []
    for i, ch in enumerate(channels):
        buttons.append([InlineKeyboardButton(f"🔴 حذف: {ch}", callback_data=f"del_ch_{i}")])
    buttons.append([InlineKeyboardButton("➕ إضافة قناة", callback_data="add_channel")])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def settings_keyboard(data: dict):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⏱ الفترة: كل {data['interval_hours']} ساعة", callback_data="set_interval")],
        [InlineKeyboardButton(f"📦 مودات/نشرة: {data['mods_per_post']}", callback_data="set_mod_count")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
    ])

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])
            return None
async def post_mod_to_channels(bot: Bot, mod: dict, channels: list):
    caption = (
        f"🎮 **{mod['name']}**\n\n"
        f"🔗 [صفحة المود]({mod['url']})\n"
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"#ماين_كرافت #مودات #Bedrock"
    )
    img_path = None
    if mod.get("image"):
        img_path = await download_image(mod["image"], mod["name"])
    dl_url = await get_mod_download_link(mod["url"])
    file_path = None
    if dl_url:
        file_path = await download_file(dl_url, mod["name"])
    results = []
    for channel in channels:
        try:
            if img_path and os.path.exists(img_path):
                with open(img_path, "rb") as img_f:
                    if file_path and os.path.exists(file_path):
                        await bot.send_photo(chat_id=channel, photo=img_f, caption=caption, parse_mode="Markdown")
                        with open(file_path, "rb") as dl_f:
                            await bot.send_document(chat_id=channel, document=dl_f, filename=os.path.basename(file_path), caption=f"📥 ملف المود: {mod['name']}")
                    else:
                        await bot.send_photo(chat_id=channel, photo=img_f, caption=caption, parse_mode="Markdown")
            else:
                await bot.send_message(chat_id=channel, text=caption, parse_mode="Markdown")
            results.append(f"✅ {channel}")
        except Exception as e:
            results.append(f"❌ {channel}: {str(e)[:50]}")
    for p in [img_path, file_path]:
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    return results

async def auto_post_job(context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data["auto_post"] or not data["channels"]:
        return
    mods = await scrape_latest_mods(data["mods_per_post"] + 5)
    posted = set(data.get("posted_mods", []))
    new_mods = [m for m in mods if m["url"] not in posted]
    if not new_mods:
        return
    to_post = new_mods[:data["mods_per_post"]]
    for mod in to_post:
        await post_mod_to_channels(context.bot, mod, data["channels"])
        data["posted_mods"].append(mod["url"])
        if len(data["posted_mods"]) > 500:
            data["posted_mods"] = data["posted_mods"][-200:]
    data["last_check"] = datetime.now().isoformat()
    save_data(data)
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ غير مصرح.")
        return
    data = load_data()
    auto_status = "✅ مفعّل" if data["auto_post"] else "❌ موقف"
    text = (
        f"🎮 **بوت مودات ماين كرافت Bedrock**\n\n"
        f"📢 القنوات: {len(data['channels'])}\n"
        f"⏱ الفترة: كل {data['interval_hours']} ساعة\n"
        f"📦 مودات/نشرة: {data['mods_per_post']}\n"
        f"🔄 نشر تلقائي: {auto_status}"
    )
    await update.message.reply_text(text, reply_markup=main_keyboard(), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔ غير مصرح.")
        return
    data = load_data()
    cb = query.data
    if cb == "main_menu":
        auto_status = "✅ مفعّل" if data["auto_post"] else "❌ موقف"
        await query.edit_message_text(f"🎮 **القائمة الرئيسية**\n\n📢 القنوات: {len(data['channels'])}\n⏱ الفترة: كل {data['interval_hours']} ساعة\n🔄 نشر تلقائي: {auto_status}", reply_markup=main_keyboard(), parse_mode="Markdown")
    elif cb == "channels_menu":
        ch_list = "\n".join([f"• `{c}`" for c in data["channels"]]) or "لا توجد قنوات."
        await query.edit_message_text(f"📢 **القنوات:**\n\n{ch_list}", reply_markup=channels_keyboard(data["channels"]), parse_mode="Markdown")
    elif cb == "add_channel":
        await query.edit_message_text("➕ أرسل يوزرنيم القناة\nمثال: `@my_channel`\n\n⚠️ البوت لازم Admin بالقناة.", parse_mode="Markdown", reply_markup=back_keyboard())
        context.user_data["waiting_for"] = "channel"
    elif cb.startswith("del_ch_"):
        idx = int(cb.split("_")[-1])
        if 0 <= idx < len(data["channels"]):
            removed = data["channels"].pop(idx)
            save_data(data)
            await query.edit_message_text(f"✅ تم حذف: `{removed}`", parse_mode="Markdown", reply_markup=channels_keyboard(data["channels"]))
    elif cb == "fetch_mods":
        if not data["channels"]:
            await query.edit_message_text("⚠️ أضف قناة أولاً.", reply_markup=back_keyboard())
            return
        await query.edit_message_text("⏳ جاري جلب المودات...")
        mods = await scrape_latest_mods(data["mods_per_post"])
        if not mods:
            await query.edit_message_text("❌ فشل جلب المودات.", reply_markup=back_keyboard())
            return
        for mod in mods:
            results = await post_mod_to_channels(query.message.bot, mod, data["channels"])
            data["posted_mods"].append(mod["url"])
            await context.bot.send_message(chat_id=query.from_user.id, text=f"📦 نُشر: **{mod['name']}**\n" + "\n".join(results), parse_mode="Markdown")
        save_data(data)
        await query.edit_message_text(f"✅ تم نشر {len(mods)} مود.", reply_markup=back_keyboard())
    elif cb == "settings_menu":
        await query.edit_message_text("⚙️ **إعدادات النشر:**", reply_markup=settings_keyboard(data), parse_mode="Markdown")
    elif cb == "set_interval":
        await query.edit_message_text(f"⏱ الفترة الحالية: {data['interval_hours']} ساعة\n\nأرسل العدد الجديد:", parse_mode="Markdown", reply_markup=back_keyboard())
        context.user_data["waiting_for"] = "interval"
    elif cb == "set_mod_count":
        await query.edit_message_text(f"📦 العدد الحالي: {data['mods_per_post']}\n\nأرسل العدد الجديد (1-10):", parse_mode="Markdown", reply_markup=back_keyboard())
        context.user_data["waiting_for"] = "mod_count"
    elif cb == "toggle_auto":
        data["auto_post"] = not data["auto_post"]
        save_data(data)
        status = "✅ مفعّل" if data["auto_post"] else "❌ موقف"
        if data["auto_post"] and context.job_queue:
            for job in context.job_queue.get_jobs_by_name("auto_post"):
                job.schedule_removal()
            context.job_queue.run_repeating(auto_post_job, interval=data["interval_hours"]*3600, first=10, name="auto_post")
        await query.edit_message_text(f"🔄 النشر التلقائي: {status}", reply_markup=back_keyboard())
    elif cb == "stats":
        await query.edit_message_text(f"📊 **الإحصائيات:**\n\n📢 القنوات: {len(data['channels'])}\n📦 مودات نُشرت: {len(data.get('posted_mods', []))}\n⏱ الفترة: {data['interval_hours']} ساعة\n🕐 آخر فحص: {data.get('last_check', 'لم يبدأ')}", reply_markup=back_keyboard(), parse_mode="Markdown")
      async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    waiting = context.user_data.get("waiting_for")
    if not waiting:
        return
    text = update.message.text.strip()
    data = load_data()
    if waiting == "channel":
        if not (text.startswith("@") or text.startswith("-100")):
            await update.message.reply_text("⚠️ أرسل مثل: `@my_channel`", parse_mode="Markdown")
            return
        if text in data["channels"]:
            await update.message.reply_text("⚠️ القناة مضافة مسبقاً.")
            return
        try:
            await context.bot.send_message(chat_id=text, text="✅ تم ربط القناة ببوت مودات ماين كرافت!")
            data["channels"].append(text)
            save_data(data)
            await update.message.reply_text(f"✅ تم إضافة: `{text}`", parse_mode="Markdown", reply_markup=main_keyboard())
        except Exception as e:
            await update.message.reply_text(f"❌ فشل. تأكد إن البوت Admin بالقناة.\n{str(e)[:100]}")
    elif waiting == "interval":
        try:
            hours = int(text)
            if hours < 1 or hours > 168:
                raise ValueError
            data["interval_hours"] = hours
            save_data(data)
            if data["auto_post"] and context.job_queue:
                for job in context.job_queue.get_jobs_by_name("auto_post"):
                    job.schedule_removal()
                context.job_queue.run_repeating(auto_post_job, interval=hours*3600, first=10, name="auto_post")
            await update.message.reply_text(f"✅ تم تحديث الفترة إلى {hours} ساعة.", reply_markup=main_keyboard())
        except ValueError:
            await update.message.reply_text("⚠️ أرسل رقم بين 1 و 168.")
            return
    elif waiting == "mod_count":
        try:
            count = int(text)
            if count < 1 or count > 10:
                raise ValueError
            data["mods_per_post"] = count
            save_data(data)
            await update.message.reply_text(f"✅ تم تحديث العدد إلى {count}.", reply_markup=main_keyboard())
        except ValueError:
            await update.message.reply_text("⚠️ أرسل رقم بين 1 و 10.")
            return
    context.user_data.pop("waiting_for", None)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    data = load_data()
    if data["auto_post"] and app.job_queue:
        app.job_queue.run_repeating(auto_post_job, interval=data["interval_hours"]*3600, first=30, name="auto_post")
    print("✅ Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
