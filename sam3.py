import asyncio
import logging
from pyrogram import Client, filters, idle
from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait
from config import *

# Logs kam karne ke liye
logging.getLogger("pyrogram").setLevel(logging.ERROR)

app = Client(
    SESSION,
    api_id=API_ID,
    api_hash=API_HASH
)

# ==============================
# DEAD DIALOG CLEANUP (SAFE)
# ==============================
async def cleanup_dead_dialogs():
    removed = 0
    async for dialog in app.get_dialogs():
        cid = dialog.chat.id
        try:
            await app.get_chat(cid)
        except:
            try:
                await app.delete_dialog(cid)
                removed += 1
            except:
                pass
    print(f">>> Cleanup done | Removed: {removed}")

# ==============================
# AUTO GROUP FETCH
# ==============================
async def get_all_groups():
    groups = []
    async for dialog in app.get_dialogs():
        chat = dialog.chat
        if chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            try:
                await app.get_chat(chat.id)
                groups.append(chat.id)
            except:
                continue
    return groups

# ==============================
# LOGGER / ADMIN SE BROADCAST
# ==============================
@app.on_message(filters.chat(ADMIN_CHANNEL) & filters.text)
async def broadcast_handler(_, msg):
    text = msg.text

    try:
        await app.send_message(LOGGER_CHANNEL, "📡 Broadcast started...")
    except:
        return

    groups = await get_all_groups()

    sent = failed = batch = 0

    for gid in groups:
        try:
            await app.send_message(gid, text)
            sent += 1
            batch += 1

            await asyncio.sleep(DELAY)

            if batch >= MAX_PER_BATCH:
                batch = 0
                await asyncio.sleep(BATCH_SLEEP)

        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            failed += 1
            continue

    report = (
        "📢 **Broadcast Finished**\n\n"
        f"✅ Sent: `{sent}`\n"
        f"❌ Failed: `{failed}`\n"
        f"📦 Total Groups: `{len(groups)}`"
    )

    try:
        await app.send_message(LOGGER_CHANNEL, report)
    except:
        pass

# ==============================
# START BOT (CORRECT WAY)
# ==============================
async def main():
    await app.start()
    await cleanup_dead_dialogs()
    print(">>> Logger-based Auto Broadcast Userbot Started")
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.loop.run_until_complete(main())









