import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TOKEN")

if TOKEN is None:
    raise RuntimeError("TOKEN environment variable not found")

players = []
current_turn = 0
story_words = []
game_active = False


async def story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global players, story_words, current_turn, game_active

    if update.message.chat.type == "private":
        await update.message.reply_text("❌ Use this bot in a group.")
        return

    players.clear()
    story_words.clear()
    current_turn = 0
    game_active = False

    await update.message.reply_text(
        "📖 One-Word Story started!\n"
        "Type /join to participate.\n"
        "Admin type /startgame to begin."
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id not in players:
        players.append(user.id)
        await update.message.reply_text(f"✅ {user.first_name} joined!")


async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_active
    if len(players) < 2:
        await update.message.reply_text("❌ Need at least 2 players.")
        return

    game_active = True
    await update.message.reply_text("🎬 Story started! First player, send ONE word.")


async def endstory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_active
    game_active = False
    await update.message.reply_text("📜 Final Story:\n" + " ".join(story_words))


async def handle_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_turn

    if not game_active:
        return

    user = update.message.from_user
    if user.id != players[current_turn]:
        return

    word = update.message.text.strip()
    if " " in word or not word.isalpha():
        await update.message.reply_text("❌ One word only.")
        return

    story_words.append(word)
    current_turn = (current_turn + 1) % len(players)

    await update.message.reply_text("📜 " + " ".join(story_words))


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("story", story))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("startgame", startgame))
    app.add_handler(CommandHandler("endstory", endstory))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_word))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
