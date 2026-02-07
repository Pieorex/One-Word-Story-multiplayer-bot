from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- GAME STATE ---
players = []
current_turn = 0
story_words = []
game_active = False


# --- COMMANDS ---
async def story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global players, story_words, current_turn, game_active

    if update.message.chat.type == "private":
        await update.message.reply_text("❌ This game works only in groups.")
        return

    players.clear()
    story_words.clear()
    current_turn = 0
    game_active = False

    await update.message.reply_text(
        "📖 One-Word Story started!\n\n"
        "Type /join to participate.\n"
        "Admin can type /startgame when ready."
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    if user.id not in players:
        players.append(user.id)
        await update.message.reply_text(f"✅ {user.first_name} joined the story!")
    else:
        await update.message.reply_text("⚠️ You already joined.")


async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_active

    if len(players) < 2:
        await update.message.reply_text("❌ Need at least 2 players.")
        return

    game_active = True
    first_player = players[current_turn]
    await update.message.reply_text(
        f"🎬 Story begins!\n\n"
        f"👉 <a href='tg://user?id={first_player}'>Your turn</a>\n"
        f"Send ONE word only.",
        parse_mode="HTML",
    )


async def endstory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_active

    if not story_words:
        await update.message.reply_text("📭 No story created.")
        return

    game_active = False
    story = " ".join(story_words)

    await update.message.reply_text(
        f"🎬 Final Story\n\n📜 {story}"
    )


# --- MESSAGE HANDLER ---
async def handle_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_turn

    if not game_active:
        return

    user = update.message.from_user

    if user.id != players[current_turn]:
        return

    word = update.message.text.strip()

    if " " in word or not word.isalpha():
        await update.message.reply_text("❌ One WORD only (letters only).")
        return

    story_words.append(word)

    current_turn = (current_turn + 1) % len(players)
    next_player = players[current_turn]

    await update.message.reply_text(
        f"📜 Story so far:\n{' '.join(story_words)}\n\n"
        f"👉 <a href='tg://user?id={next_player}'>Your turn</a>",
        parse_mode="HTML",
    )


# --- MAIN ---
app = ApplicationBuilder().token("7950882826:AAEPsi2Kc-DA7Vtaij-VXjGPqPlKq2uTFlI").build()

app.add_handler(CommandHandler("story", story))
app.add_handler(CommandHandler("join", join))
app.add_handler(CommandHandler("startgame", startgame))
app.add_handler(CommandHandler("endstory", endstory))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_word))

print("🤖 Story bot running...")
app.run_polling()
