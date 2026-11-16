# ============================================
#  selfbot/handler.py - auto-reply logic per dialog
#  All code and comments are English. No emojis.
# ============================================
import asyncio

async def _last_message(client, entity):
    msgs = await client.get_messages(entity, limit=1)
    if not msgs:
        return None
    return msgs[0]

async def process_dialog(client, dialog, storage, config, log):
    if not getattr(dialog, "is_user", False):
        return False
    entity = dialog.entity
    if getattr(entity, "bot", False):
        return False
    user_id = getattr(entity, "id", None)
    if user_id is None:
        return False
    replied = await storage.get_replied()
    if user_id in replied:
        return False
    last = await _last_message(client, entity)
    if last is None or getattr(last, "out", False):
        return False
    await asyncio.sleep(config.delay_seconds)
    last2 = await _last_message(client, entity)
    if last2 is None or getattr(last2, "out", False):
        return False
    sent = await client.send_message(entity, config.reply_text)
    if sent is not None and getattr(sent, "id", None):
        try:
            await client.pin_message(entity, sent.id, notify=False)
        except Exception as e:
            log(f"pin failed for user {user_id}: {type(e).__name__}: {e}")
    await storage.add_replied(user_id)
    return True
