import logging
from telegram import (
    Update,
    BotCommand,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

TOKEN = "YOUR_BOT_TOKEN_HERE"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# =========================
# GLOBAL STATE (per group)
# =========================
games = {}  # chat_id -> game data


def get_game(chat_id):
    if chat_id not in games:
        games[chat_id] = {
            "players": [],
            "started": False,
            "current_turn": 0,
            "story": [],
        }
    return games[chat_id]


# =========================
# HELPERS
# =========================
async def is_admin(update: Update) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    member = await chat.get_member(user.id)
    return member.status in ("administrator", "creator")


# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.type == "private":
        await update.message.reply_text(
            "👋 Hi!\n\n"
            "Add me to a group and use:\n"
            "• /startgame – start a story\n"
            "• /join – join the game"
        )
    else:
        await update.message.reply_text(
            "📖 Story Bot Ready!\n"
            "Admins can use /startgame"
        )


async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        await update.message.reply_text("🛑 Only admins can start the game.")
        return

    chat_id = update.effective_chat.id
    game = get_game(chat_id)

    if game["started"]:
        await update.message.reply_text("⚠️ Game already started.")
        return

    if len(game["players"]) < 2:
        await update.message.reply_text("👥 Need at least 2 players. Use /join.")
        return

    game["started"] = True
    game["current_turn"] = 0
    game["story"] = []

    players = ", ".join(p["name"] for p in game["players"])
    first_player = game["players"][0]["name"]

    await update.message.reply_text(
        f"🎬 *Story Started!*\n\n"
        f"Players:\n{players}\n\n"
        f"✍️ {first_player}, your turn!",
        parse_mode="Markdown",
    )


async def endstory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        await update.message.reply_text("🛑 Only admins can end the story.")
        return

    chat_id = update.effective_chat.id
    game = get_game(chat_id)

    if not game["started"]:
        await update.message.reply_text("❌ No active game.")
        return

    story_text = " ".join(game["story"]) or "*(No words added)*"

    games.pop(chat_id, None)

    await update.message.reply_text(
        f"🏁 *Story Ended!*\n\n📖 {story_text}",
        parse_mode="Markdown",
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    game = get_game(chat_id)

    if game["started"]:
        await update.message.reply_text("❌ Game already started.")
        return

    if any(p["id"] == user.id for p in game["players"]):
        await update.message.reply_text("⚠️ You already joined.")
        return

    game["players"].append(
        {
            "id": user.id,
            "name": user.first_name,
        }
    )

    await update.message.reply_text(f"✅ {user.first_name} joined the game!")


async def word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    game = get_game(chat_id)

    if not game["started"]:
        return

    if user.id != game["players"][game["current_turn"]]["id"]:
        return

    text = update.message.text.strip()
    if " " in text or len(text) > 20:
        await update.message.reply_text("❌ One word only (max 20 chars).")
        return

    game["story"].append(text)

    game["current_turn"] = (game["current_turn"] + 1) % len(game["players"])
    next_player = game["players"][game["current_turn"]]["name"]

    await update.message.reply_text(
        f"✅ Added: *{text}*\n\n✍️ {next_player}, your turn!",
        parse_mode="Markdown",
    )


# =========================
# BOT COMMAND MENU
# =========================
async def set_commands(app):
    await app.bot.set_my_commands(
        [
            BotCommand("start", "Start the bot"),
            BotCommand("startgame", "Start story game (admin)"),
            BotCommand("endstory", "End story (admin)"),
            BotCommand("join", "Join the game"),
        ]
    )


# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.post_init = set_commands

    app.add_handler(CommandHandler("start", start), group=0)
    app.add_handler(CommandHandler("startgame", startgame))
    app.add_handler(CommandHandler("endstory", endstory))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler(None, word))

    print("🤖 Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
