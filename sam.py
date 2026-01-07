import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.enums import ChatType, ChatMemberStatus
from pyrogram.errors import FloodWait, ChannelPrivate, RPCError, BadRequest
from config import *

logging.getLogger("pyrogram").setLevel(logging.ERROR)

app = Client(
    SESSION,
    api_id=API_ID,
    api_hash=API_HASH
)

# -----------------------------
# SAFE GET GROUPS
# -----------------------------
async def get_groups():
    groups = []
    try:
        async for d in app.get_dialogs():
            try:
                if d.chat and d.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                    groups.append(d.chat.id)
            except:
                continue
    except (ChannelPrivate, RPCError):
        pass
    return list(set(groups))


# -----------------------------
# AUTO LEAVE MUTED
# -----------------------------
async def auto_leave_if_muted():
    while True:
        try:
            async for d in app.get_dialogs():
                try:
                    if d.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                        m = await app.get_chat_member(d.chat.id, "me")
                        if m.status == ChatMemberStatus.RESTRICTED:
                            await app.leave_chat(d.chat.id)
                            await app.send_message(
                                LOGGER_CHANNEL,
                                f"🚪 Auto Left Muted\n📌 {d.chat.title}"
                            )
                            await asyncio.sleep(2)
                except:
                    continue
        except:
            pass
        await asyncio.sleep(300)  # check every 5 minutes


# -----------------------------
# BROADCAST WITH SAFE BATCHES + LIVE %
# -----------------------------
@app.on_message(filters.chat(ADMIN_CHANNEL) & filters.command("bc"))
async def broadcast(_, msg):

    if len(msg.command) < 2:
        await msg.reply("❌ Use: /bc your message")
        return

    text = msg.text.split(" ", 1)[1]

    log = await app.send_message(
        LOGGER_CHANNEL,
        "📡 Broadcast Triggered\n⏳ Fetching groups..."
    )

    groups = await get_groups()
    total = len(groups)
    batches = (total // MAX_PER_BATCH) + 1

    await app.edit_message_text(
        LOGGER_CHANNEL,
        log.id,
        f"🚀 Broadcast Started\n📦 Total Groups: {total}\n⚡ Batch Size: {MAX_PER_BATCH}\n⏱ Batch Delay: {BATCH_SLEEP}s"
    )

    sent = failed = batch_count = done = 0

    for i, gid in enumerate(groups, start=1):
        try:
            await app.send_message(gid, text)
            sent += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except:
            failed += 1

        done += 1
        batch_count += 1

        # 🔁 Live progress update every 5 messages
        if done % 5 == 0 or done == total:
            percent = round((done / total) * 100, 2)
            try:
                await app.edit_message_text(
                    LOGGER_CHANNEL,
                    log.id,
                    f"📢 Broadcasting...\n\n📦 Total: {total}\n📨 Sent: {sent}\n❌ Failed: {failed}\n📊 Progress: {percent}%\n📂 Batch: {(done-1)//MAX_PER_BATCH+1}/{batches}"
                )
            except:
                pass

        await asyncio.sleep(DELAY)

        if batch_count >= MAX_PER_BATCH:
            batch_count = 0
            await asyncio.sleep(BATCH_SLEEP)  # safe pause between batches

    # ✅ Final completion message
    await app.edit_message_text(
        LOGGER_CHANNEL,
        log.id,
        f"✅ Broadcast Completed\n\n📦 Total Groups: {total}\n📨 Sent: {sent}\n❌ Failed: {failed}\n📊 Success Rate: {round((sent/total)*100,2)}%"
    )


# -----------------------------
# START BOT
# -----------------------------
async def main():
    await app.start()
    print(">>> SAFE Broadcast + Auto Leave Started")
    asyncio.create_task(auto_leave_if_muted())
    await asyncio.Event().wait()

app.loop.run_until_complete(main())









