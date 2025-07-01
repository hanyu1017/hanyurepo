# bot.py
import logging
import asyncio
from datetime import datetime, timedelta, time
from collections import defaultdict
from dotenv import load_dotenv  # dotenv 載入
import os
from random import sample

from telegram import Update, ForceReply
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackContext, JobQueue
)
import openai

# === 載入環境變數 ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
assert BOT_TOKEN, "❌ BOT_TOKEN 環境變數未正確設定，請在 Railway 環境變數中加入 BOT_TOKEN"
PASSWORD = "0929839399"
openai.api_key = os.getenv("OPENAI_API_KEY")

# === 狀態變數 ===
AUTHORIZED_USER_ID = None
LAST_SEEN = {}  # {chat_id: datetime}
CHAT_HISTORY = defaultdict(list)  # {chat_id: [messages]}

# === 早安與撒嬌訊息 ===
GOOD_MORNING_TEXTS = [
    "早安安～今天也要加油喔 ☀️",
    "早起的翰宇給你一個大擁抱 🐣",
    "新的一天開始了！吃早餐沒呀 🍞🥛"
]
SWEET_NAGS = [
    "欸欸～你都不理我了欸😢 在幹嘛啦？",
    "你不回我我會死掉欸😭",
    "是不是又在偷懶！快出來陪我講話🥺",
    "哼哼，都不跟我講話，討厭啦🙃"
]

# === GPT Prompt ===
STYLE_SNIPPETS = [...]

# 以下略，原本程式碼繼續保留不變

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ✅ 修正 JobQueue 問題（若未正確建立，則手動建立）
    if not hasattr(app, 'job_queue') or app.job_queue is None:
        app.job_queue = JobQueue()
        app.job_queue.set_application(app)
        app.job_queue.start()

    # ✅ 加入排程任務
    app.job_queue.run_repeating(lambda ctx: asyncio.create_task(scheduler(app)), interval=60, first=1)

    app.run_polling()
