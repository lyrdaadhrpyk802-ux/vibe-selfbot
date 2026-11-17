# ============================================
#  selfbot/handler.py - auto-reply logic per dialog
#  All code and comments are English. No emojis.
# ============================================
import time

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
    
    # Ignore system bots
    if user_id in (777000, 42777, 333000):
        return False

    if getattr(entity, "bot", False) or getattr(entity, "deleted", False):
        return False

    replied_dict = await storage.get_replied()
    last_replied_time = replied_dict.get(str(user_id), 0)
    
    # Check if 8-hour cooldown has passed
    now_ts = time.time()
    if now_ts - last_replied_time < config.cooldown_seconds:
        return False

    last = await _last_message(client, entity, log, user_id)
    if last is None:
        return False
        
    if getattr(last, "out", False):
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
                
        # Save current time as last replied time
        await storage.add_replied(user_id, now_ts)
        log(f"successfully replied to {user_id}")
        return True
    except Exception as e:
        log(f"send failed for user {user_id}: {type(e).__name__}: {e}")
        return False
