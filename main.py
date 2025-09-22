import asyncio, random, string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = '8247043145:AAHS8Ym_e0EBLw56aSYwMwwkLSiV3UAh4GY'
ADMIN_IDS = [5952132218]

pending_content = None
current_code = None
content_links = {}
REQUIRED_CHANNELS = {}

def generate_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

async def check_subscription(user_id, bot):
    for username in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=f"@{username}", user_id=user_id)
            if member.status not in ['member', 'creator', 'administrator']:
                return False
        except:
            return False
    return True

async def delete_later(bot, chat_id, message_id, delay=15):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    is_subscribed = await check_subscription(user_id, context.bot)
    if not is_subscribed:
        buttons = [
            [InlineKeyboardButton(REQUIRED_CHANNELS[u], url=f"https://t.me/{u}")]
            for u in REQUIRED_CHANNELS
        ]
        buttons.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")])
        await update.message.reply_text(
            "📌 لازم تشترك بالقنوات التالية حتى تستلم المحتوى:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if args:
        code = args[0]
        if code in content_links:
            data = content_links.pop(code)
            for msg_id in data['message_ids']:
                sent = await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=data['chat_id'],
                    message_id=msg_id
                )
                asyncio.create_task(delete_later(context.bot, user_id, sent.message_id))
            await update.message.reply_text("📌 سيتم حذف المحتوى تلقائيًا بعد 15 ثانية.")
        else:
            await update.message.reply_text("هذا الرابط غير صالح أو تم استخدامه مسبقًا ❌")
    else:
        await update.message.reply_text("أهلاً بك! ان كنت تريد المشاهدة الفديوهات اذهب الئ قناة t.me/ALRAYIS3 .")

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("لوحة التحكم للمطوّرين فقط 🚫")
        return

    keyboard = [
        [InlineKeyboardButton("📤 إرسال محتوى خاص", callback_data='send')],
        [InlineKeyboardButton("➕ إضافة قناة", callback_data='add_channel')],
        [InlineKeyboardButton("➖ حذف قناة", callback_data='remove_channel')],
        [InlineKeyboardButton("📌 عرض القنوات", callback_data='show_channels')],
    ]
    await update.message.reply_text("🛠 لوحة تحكم الأدمن:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global pending_content, current_code
    query = update.callback_query
    await query.answer()

    if query.data == 'send':
        pending_content = query.from_user.id
        current_code = generate_code()
        content_links[current_code] = {
            'chat_id': query.message.chat_id,
            'message_ids': []
        }
        await query.edit_message_text("أرسل الفيديوهات والصور الآن، ولما تخلص اضغط '🔚 إنهاء المحتوى'")
        keyboard = [[InlineKeyboardButton("🔚 إنهاء المحتوى", callback_data="finalize_content")]]
        await context.bot.send_message(chat_id=query.message.chat_id, text="📦 اضغط الزر لما تخلص إرسال المحتوى:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "finalize_content":
        if not current_code or current_code not in content_links:
            await query.edit_message_text("❌ لا يوجد محتوى محفوظ حالياً.")
            return
        bot_username = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_username}?start={current_code}"
        await query.edit_message_text(f"✅ تم توليد الرابط:\n{link}\n📎 يحتوي على كل المحتوى، صالح لمرة واحدة فقط")
        pending_content = None
        current_code = None

    elif query.data == "check_sub":
        user_id = query.from_user.id
        is_subscribed = await check_subscription(user_id, context.bot)
        if is_subscribed:
            await query.edit_message_text("✅ تم التحقق من الاشتراك، أرسل الرابط مرة ثانية لاستلام المحتوى.")
        else:
            await query.answer("❌ ما زلت غير مشترك بكل القنوات المطلوبة", show_alert=True)

    elif query.data == 'add_channel':
        context.user_data['awaiting_channel'] = True
        await query.edit_message_text("📥 أرسل الآن اسم مستخدم القناة بدون @")

    elif query.data == 'remove_channel':
        if not REQUIRED_CHANNELS:
            await query.edit_message_text("📭 لا توجد قنوات حالياً.")
            return
        buttons = [
            [InlineKeyboardButton(REQUIRED_CHANNELS[u], callback_data=f"del_{u}")]
            for u in REQUIRED_CHANNELS
        ]
        await query.edit_message_text("❌ اختر القناة التي تريد حذفها:", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data.startswith("del_"):
        username = query.data.replace("del_", "")
        if username in REQUIRED_CHANNELS:
            del REQUIRED_CHANNELS[username]
            await query.edit_message_text(f"✅ تم حذف القناة: @{username}")

    elif query.data == 'show_channels':
        if not REQUIRED_CHANNELS:
            await query.edit_message_text("📭 لا توجد قنوات حالياً.")
        else:
            text = "📌 القنوات الحالية:\n"
            for u in REQUIRED_CHANNELS:
                text += f"- @{u} ({REQUIRED_CHANNELS[u]})\n"
            await query.edit_message_text(text)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global pending_content, current_code
    if update.effective_user.id != pending_content:
        await update.message.reply_text("اضغط زر '📤 إرسال محتوى خاص' أولاً.")
        return

    media = update.message.video or update.message.photo[-1]
    if not media:
        await update.message.reply_text("أرسل فيديو أو صورة فقط.")
        return

    content_links[current_code]['message_ids'].append(update.message.message_id)
    await update.message.reply_text("✅ تم حفظ المحتوى، أرسل المزيد أو اضغط '🔚 إنهاء المحتوى' لما تخلص.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_channel'):
        username = update.message.text.strip().replace("@", "")
        REQUIRED_CHANNELS[username] = f"@{username}"
        context.user_data['awaiting_channel'] = False
        await update.message.reply_text(f"✅ تم إضافة القناة: @{username}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", panel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VIDEO | filters.PHOTO, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == '__main__':
    main()
