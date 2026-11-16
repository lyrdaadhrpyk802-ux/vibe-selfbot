# ============================================
#  selfbot/handler.py - auto-reply logic per dialog
#  All code and comments are English. No emojis.
# ============================================
import asyncio
from datetime import datetime, timezone, timedelta

async def _last_message(client, entity, log, user_id):
    try:
        msgs = await client.get_messages(entity, limit=1)
        if not msgs:
            return None
        return msgs[0]
    except Exception as e:
        log(f"get_messages error for {user_id}: {type(e).__name__}: {e}")
        return None

async def process_dialog(client, dialog, entity, storage, config, log):
    user_id = entity.id
    
    # Ignore known system bots (Vibe/Telegram service accounts)
    if user_id in (777000, 42777, 333000):
        return False

    if getattr(entity, "bot", False) or getattr(entity, "deleted", False):
        return False

    replied = await storage.get_replied()
    if user_id in replied:
        return False

    last = await _last_message(client, entity, log, user_id)
    if last is None:
        return False
        
    if getattr(last, "out", False):
        return False

    # Check if the message is actually "new" (arrived in the last 10 minutes)
    if not getattr(last, "date", None):
        return False
        
    now = datetime.now(timezone.utc)
    msg_age = now - last.date
    if msg_age > timedelta(minutes=10):
        # Message is old, meaning the bot is reading chat history. Skip.
        return False

    log(f"waiting {config.delay_seconds}s for {user_id} before replying")
    await asyncio.sleep(config.delay_seconds)

    last2 = await _last_message(client, entity, log, user_id)
    if last2 is None or getattr(last2, "out", False):
        log(f"skip {user_id}: condition changed after delay")
        return False

    try:
        log(f"sending reply to {user_id}")
        sent = await client.send_message(entity, config.reply_text)
        if sent is not None and getattr(sent, "id", None):
            try:
                await client.pin_message(entity, sent.id, notify=False)
                log(f"pinned message for {user_id}")
            except Exception as e:
                log(f"pin failed for user {user_id}: {type(e).__name__}: {e}")
        await storage.add_replied(user_id)
        log(f"successfully replied to {user_id}")
        return True
    except Exception as e:
        log(f"send failed for user {user_id}: {type(e).__name__}: {e}")
        return False
