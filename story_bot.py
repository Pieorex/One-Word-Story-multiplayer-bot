import os
import json
import random
import asyncio
import logging
from telegram import Update, Message
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN env variable missing")

TURN_TIMEOUT = 15
MAX_WORD_LENGTH = 15
STATE_FILE = "state.json"
DEBUG = True

logging.basicConfig(level=logging.INFO if DEBUG else logging.WARNING)

# =========================
# STATE (MULTI-GROUP)
# =========================
games = {}       # chat_id -> game state
scores = {}      # user_id -> score


def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump({"games": games, "scores": scores}, f)


def load_state():
    global games, scores
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            games = data.get("games", {})
            scores = data.get("scores", {})
    except FileNotFoundError:
        pass


load_state()


# =========================
# HELPERS
# =========================
def is_admin(update: Update):
    member = update.effective_chat.get_member(update.effective_user.id)
    return member.status in ("administrator", "creator")


def format_story(words):
    if not words:
        return ""
    words[0] = words[0].capitalize()
    return " ".join(words)


async def start_timer(chat_id, context):
    await asyncio.sleep(TURN_TIMEOUT)
    game = games.get(chat_id)
    if not game or not game["active"]:
        return

    game["turn"] = (game["turn"] + 1) % len(game["players"])
    await send_turn_message(chat_id, context, skipped=True)


async def send_turn_message(chat_id, context, skipped=False):
    game = games[chat_id]
    player = game["players"][game["turn"]]

    text = (
        f"⏭️ Skipped!\n" if skipped else ""
    ) + (
        f"📜 {format_story(game['story'])}\n\n"
        f"👉 **{player['name']}**, your turn!"
    )

    if game["silent"]:
        await game["message"].edit_text(text, parse_mode="Markdown")
    else:
        game["message"] = await context.bot.send_message(
            chat_id, text, parse_mode="Markdown"
        )

    if game.get("timer"):
        game["timer"].cancel()
    game["timer"] = asyncio.create_task(start_timer(chat_id, context))


# =========================
# COMMANDS
# =========================
async def story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    games[chat_id] = {
        "players": [],
        "player_ids": set(),
        "story": [],
        "turn": 0,
        "active": False,
        "used_words": set(),
        "silent": True,
        "timer": None,
        "message": None,
    }

    await update.message.reply_text(
        "📖 **One-Word Story started!**\n\n"
        "Players use /join\n"
        "Admin uses /startgame",
        parse_mode="Markdown",
    )
    save_state()


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    game = games.get(chat_id)

    if not game:
        return

    if user.id in game["player_ids"]:
        return

    game["players"].append({"id": user.id, "name": user.first_name})
    game["player_ids"].add(user.id)

    await update.message.reply_text(f"✅ {user.first_name} joined!")
    save_state()


async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    chat_id = update.effective_chat.id
    game = games.get(chat_id)

    if not game or len(game["players"]) < 2:
        await update.message.reply_text("❌ Need at least 2 players.")
        return

    game["active"] = True
    game["turn"] = 0

    players = ", ".join(p["name"] for p in game["players"])
    game["message"] = await update.message.reply_text(
        f"🎬 **Game Started!**\n\n👥 Players: {players}",
        parse_mode="Markdown",
    )

    await send_turn_message(chat_id, context)
    save_state()


async def endstory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    chat_id = update.effective_chat.id
    game = games.get(chat_id)
    if not game:
        return

    game["active"] = False
    story = format_story(game["story"])

    await update.message.reply_text(
        f"🎬 **Final Story**\n\n📜 {story}",
        parse_mode="Markdown",
    )
    save_state()


# =========================
# WORD HANDLER
# =========================
async def handle_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = games.get(chat_id)

    if not game or not game["active"]:
        return

    user = update.effective_user
    current = game["players"][game["turn"]]

    if user.id != current["id"]:
        return

    word = update.message.text.strip().lower()

    if (
        " " in word
        or not word.isalpha()
        or len(word) > MAX_WORD_LENGTH
        or word in game["used_words"]
    ):
        return

    game["used_words"].add(word)
    game["story"].append(word)
    scores[user.id] = scores.get(user.id, 0) + 1

    # CHAOS EVENT (20%)
    if random.random() < 0.2:
        event = random.choice(["reverse", "double", "forced"])
        if event == "reverse":
            game["players"].reverse()
        elif event == "double":
            pass
        elif event == "forced":
            game["story"].append("suddenly")

    game["turn"] = (game["turn"] + 1) % len(game["players"])
    await send_turn_message(chat_id, context)
    save_state()


# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("story", story))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("startgame", startgame))
    app.add_handler(CommandHandler("endstory", endstory))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_word))

    print("🤖 Advanced Story Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
