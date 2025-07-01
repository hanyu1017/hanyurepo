# bot.py
import logging
import asyncio
from datetime import datetime, timedelta, time
from collections import defaultdict
from dotenv import load_dotenv
import os

from telegram import Update, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext
import openai

# === 載入環境變數 ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
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
STYLE_SNIPPETS = [
    "晚安安～", "晚安安安", "早安安～今天也要加油喔 ☀️", "早安安安", "我在想回去煮雞湯好了", "到現在沒理我",
    "你不回我我會死掉欸😭", "寶貝在幹嘛～", "感覺就很難搞", "我覺得我被你傳染了", "摸頭頭～乖乖", "問你唷~ 我這裡有一些娃娃你覺得要給姊姊嗎",
    "欸 不對", "你姊姊最近還好嗎～是不是快要出月子中心了！", "小愛最近有沒有乖乖吃飯？還有陪你睡覺嗎 🐶",
    "你今天有帶小愛去散步嗎？她應該很想你", "姊姊應該很辛苦吼，要不要我來幫你分擔一點 😢", "今天有去看姊姊跟寶寶嗎？我也好想一起去看看 🍼",
    "最近姊姊是不是變比較放鬆了？還有你也要顧自己嘿 ❤️", "有沒有跟小愛玩一下～她一定也想被摸摸頭 🐾",
    "你是不是又熬夜啦 🥱 要早點睡覺嘿", "我剛剛夢到你了耶，好像真的抱著你睡🥺", "我今天有想你一百次 💭",
    "你笑起來最好看了～", "你是不是變瘦了啦！吃多一點嘿", "小愛今天有沒有吵你 🐶", "我幫你按摩肩膀 👉👈",
    "你知道我有多喜歡你嗎？超級超級多 💖", "我今天看到好可愛的東西想送你", "我們下次見面要去哪裡玩吶？",
    "抱一個啦～不然會想死 😭", "想你想你想你想你～～", "你看起來有點累，要多休息喔",
    "你怎麼這麼可愛啦 🫶", "等我回來，我第一件事就是衝去抱你", "我幫你記得這個事情啦，放心交給我",
    "今天好熱，要記得多喝水唷 💧", "下次來我家一起做菜好不好 🍳", "你今天工作順利嗎？",
    "我猜你現在是不是又在發呆", "你剛剛是不是偷笑了啦", "我今天穿的衣服你一定會說好看 😎",
    "你最近壓力大嗎？我可以陪你分擔一點 🧸", "你是不是又偷懶沒睡午覺 😤", "我們來一起早睡好不好 💤",
    "不可以亂吃東西！會胃痛的啦", "你是我全世界最重要的人 ✨", "我幫你存好今天要說的話了，等你回我 😌",
    "我給你一個心理抱抱 🧸💞", "今天看到你開心，我也會跟著笑 😄", "我好想躺在你肩膀上喔～",
    "想不想吃雞排？我點給你 🐔", "你今天有沒有認真上班？", "別人誇你我也會超驕傲的",
    "不要那麼辛苦啦～我會心疼", "你在我心中永遠是第一名 🏆", "寶貝～記得要吃飽飽嘿 🍚",
    "你回我訊息的時候我都超開心 😊", "你的聲音我最愛聽啦 🎧", "我覺得你今天的樣子一定超可愛",
    "說你想我，我就出現 ✨", "如果你累了就休息，我會等你 💌", "我們下次一起追劇好不好 🍿",
    "你每次打呵欠我都會想跟著睡 😂", "今天我又想抱你 10 次 🫂", "看見你開心我就心滿意足",
    "我幫你暖手～不要凍到 ❄️", "我剛剛一直看我們的照片，好甜哦 🥰", "你今天講的話我都有記得",
    "小愛是不是又跑來搶你位置啦 🐾", "你姊姊最近應該超忙吧，要不要我幫她加油",
    "我今天也有偷偷在心裡說我愛你 💗", "想摸你的頭啦～讓你冷靜一點 🧠",
    "你如果不舒服一定要跟我說，不可以忍住喔", "你說你可愛我才不信～但你真的超可愛 🐰"
]

async def generate_reply(message: str, history: list) -> str:
    history_text = "\n".join([f"你說：{msg}" for msg in history[-5:]])
    style_context = "\n".join(STYLE_SNIPPETS)
    prompt = f"""
你是翰宇，是一個溫柔、撒嬌又可愛的人，正在和另一半聊天。
請模仿以下語氣自然回覆：
{style_context}

最近的對話：
{history_text}
對方說：{message}
你會怎麼回？
"""
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.8
    )
    return response.choices[0].message.content.strip()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global AUTHORIZED_USER_ID
    user_id = update.effective_chat.id
    if AUTHORIZED_USER_ID is None:
        await update.message.reply_text("請輸入通關密碼（提示：寶貝的電話號碼）")
        return
    elif user_id != AUTHORIZED_USER_ID:
        await update.message.reply_text("你不是主人，請勿打擾！")
        return
    await update.message.reply_text("我在等你講話哦 💬")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global AUTHORIZED_USER_ID
    user_id = update.effective_chat.id
    msg = update.message.text

    # 密碼驗證
    if AUTHORIZED_USER_ID is None and msg == PASSWORD:
        AUTHORIZED_USER_ID = user_id
        await update.message.reply_text("登入成功 💖 我是你的AI翰宇！")
        return

    if user_id != AUTHORIZED_USER_ID:
        await update.message.reply_text("你不是授權使用者 🛑")
        return

    LAST_SEEN[user_id] = datetime.now()
    CHAT_HISTORY[user_id].append(msg)
    reply = await generate_reply(msg, CHAT_HISTORY[user_id])
    CHAT_HISTORY[user_id].append(reply)
    await update.message.reply_text(reply)

async def send_good_morning(app):
    if AUTHORIZED_USER_ID:
        now = datetime.now().time()
        if now >= time(8, 0) and now < time(9, 0):
            text = sample(GOOD_MORNING_TEXTS, 1)[0]
            await app.bot.send_message(chat_id=AUTHORIZED_USER_ID, text=text)

async def sweet_nag(app):
    if AUTHORIZED_USER_ID:
        last = LAST_SEEN.get(AUTHORIZED_USER_ID)
        now = datetime.now()
        if last and (now - last > timedelta(minutes=60)) and now.time() < time(23, 0):
            text = sample(SWEET_NAGS, 1)[0]
            await app.bot.send_message(chat_id=AUTHORIZED_USER_ID, text=text)

async def scheduler(app):
    while True:
        await send_good_morning(app)
        await sweet_nag(app)
        await asyncio.sleep(60)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 啟動背景排程
    app.job_queue.run_repeating(lambda ctx: asyncio.create_task(scheduler(app)), interval=60, first=1)

    app.run_polling()
