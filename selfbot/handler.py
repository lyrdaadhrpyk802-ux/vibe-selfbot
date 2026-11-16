# ============================================
#  selfbot/handler.py - auto-reply logic per dialog
#  All code and comments are English. No emojis.
# ============================================
import asyncio

async def _last_message(client, peer):
    try:
        msgs = await client.get_messages(peer, limit=1)
        if not msgs:
            return None
        return msgs[0]
    except Exception:
        return None

async def process_dialog(client, dialog, storage, config, log):
    if not getattr(dialog, "is_user", False):
        return False

    entity = dialog.entity
    if getattr(entity, "bot", False) or getattr(entity, "deleted", False):
        return False

    user_id = getattr(entity, "id", None)
    if user_id is None:
        return False

    # Skip invalid users without access_hash
    if getattr(entity, "access_hash", None) is None and not getattr(dialog, "input_entity", None):
        return False

    replied = await storage.get_replied()
    if user_id in replied:
        return False

    # Use input_entity for API calls to avoid access_hash issues
    peer = getattr(dialog, "input_entity", None) or entity

    last = await _last_message(client, peer)
    if last is None or getattr(last, "out", False):
        return False

    await asyncio.sleep(config.delay_seconds)

    last2 = await _last_message(client, peer)
    if last2 is None or getattr(last2, "out", False):
        return False

    try:
        sent = await client.send_message(peer, config.reply_text)
        if sent is not None and getattr(sent, "id", None):
            try:
                await client.pin_message(peer, sent.id, notify=False)
            except Exception as e:
                log(f"pin failed for user {user_id}: {type(e).__name__}: {e}")
        await storage.add_replied(user_id)
        return True
    except Exception as e:
        log(f"send failed for user {user_id}: {type(e).__name__}: {e}")
        return False
