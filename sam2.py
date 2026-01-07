import re
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.enums import ChatType, ChatMemberStatus
from pyrogram.errors import FloodWait, UserAlreadyParticipant
from config import *

logging.getLogger("pyrogram").setLevel(logging.ERROR)

app = Client(
    SESSION,
    api_id=API_ID,
    api_hash=API_HASH
)

JOINED_TODAY = 0
joined_links = set()

LINK_REGEX = r"(https?://t\.me/\+[\w-]+|https?://t\.me/[\w-]+)"


# -------------------------------------------------
# PROCESS LINKS (ADVANCED LOGGER)
# -------------------------------------------------
async def process_links(links):
    global JOINED_TODAY

    for link in links:
        if JOINED_TODAY >= MAX_JOIN_PER_DAY:
            return

        if link in joined_links:
            continue

        try:
            chat = await app.join_chat(link)
            joined_links.add(link)
            JOINED_TODAY += 1

            chat_id = chat.id
            chat_title = chat.title or "No Title"
            chat_type = chat.type.value

            await app.send_message(
                LOGGER_CHANNEL,
                f"""✅ **Joined Successfully**

📌 **Name:** {chat_title}
🆔 **ID:** `{chat_id}`
📂 **Type:** {chat_type}
🔗 **Link:** {link}

📊 **Today:** {JOINED_TODAY}/{MAX_JOIN_PER_DAY}
"""
            )

            await asyncio.sleep(JOIN_DELAY)

        except UserAlreadyParticipant:
            joined_links.add(link)
            try:
                chat = await app.get_chat(link)
                await app.send_message(
                    LOGGER_CHANNEL,
                    f"""ℹ️ **Already Joined**

📌 **Name:** {chat.title}
🆔 **ID:** `{chat.id}`
🔗 **Link:** {link}
"""
                )
            except:
                pass

        except FloodWait as e:
            await asyncio.sleep(e.value)

        except Exception as e:
            joined_links.add(link)
            await app.send_message(
                LOGGER_CHANNEL,
                f"""❌ **Join Failed**

🔗 {link}
⚠️ Reason: `{str(e)[:120]}`
"""
            )


# -------------------------------------------------
# OLD MESSAGES SCAN
# -------------------------------------------------
async def scan_old_messages():
    async for msg in app.get_chat_history(SOURCE_CHANNEL, limit=500):
        if msg.text:
            links = re.findall(LINK_REGEX, msg.text)
            await process_links(links)


# -------------------------------------------------
# NEW MESSAGES
# -------------------------------------------------
@app.on_message(filters.chat(SOURCE_CHANNEL) & filters.text)
async def auto_join(_, msg):
    links = re.findall(LINK_REGEX, msg.text)
    await process_links(links)


# -------------------------------------------------
# AUTO LEAVE IF MUTED
# -------------------------------------------------
async def auto_leave_if_muted():
    while True:
        async for dialog in app.get_dialogs():
            chat = dialog.chat
            if chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                try:
                    member = await app.get_chat_member(chat.id, "me")
                    if member.status == ChatMemberStatus.RESTRICTED:
                        await app.leave_chat(chat.id)
                        await app.send_message(
                            LOGGER_CHANNEL,
                            f"🚪 **Left Muted Group**\n📌 {chat.title}\n🆔 `{chat.id}`"
                        )
                        await asyncio.sleep(5)
                except:
                    continue
        await asyncio.sleep(300)

async def scan_old_messages():
    try:
        async for msg in app.get_chat_history(SOURCE_CHANNEL, limit=500):
            if msg.text:
                links = re.findall(LINK_REGEX, msg.text)
                await process_links(links)
    except Exception as e:
        await app.send_message(
            LOGGER_CHANNEL,
            f"⚠️ SOURCE_CHANNEL scan failed\nReason: `{e}`"
        )
# -------------------------------------------------
# GET GROUPS
# -------------------------------------------------
async def get_all_groups():
    groups = []
    async for dialog in app.get_dialogs():
        if dialog.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            groups.append(dialog.chat.id)
    return groups


# -------------------------------------------------
# BROADCAST
# -------------------------------------------------
@app.on_message(filters.chat(ADMIN_CHANNEL) & filters.text)
async def broadcast(_, msg):
    text = msg.text
    await app.send_message(LOGGER_CHANNEL, "📡 **Broadcast started**")

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

    await app.send_message(
        LOGGER_CHANNEL,
        f"""📢 **Broadcast Finished**

✅ Sent: `{sent}`
❌ Failed: `{failed}`
📦 Groups: `{len(groups)}`
"""
    )


# -------------------------------------------------
# START
# -------------------------------------------------
async def main():
    await app.start()
    print(">>> Auto Join + Broadcast Userbot Started")

    await scan_old_messages()
    asyncio.create_task(auto_leave_if_muted())

    await asyncio.Event().wait()

app.loop.run_until_complete(main())

