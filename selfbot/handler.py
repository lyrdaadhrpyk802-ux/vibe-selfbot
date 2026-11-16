# ============================================
#  selfbot/handler.py - auto-reply logic per dialog
#  All code and comments are English. No emojis.
# ============================================
import asyncio
from telethon.tl.types import InputPeerUser

async def _last_message(client, peer):
    try:
        msgs = await client.get_messages(peer, limit=1)
        if not msgs:
            return None
        return msgs[0]
    except Exception:
        return None

async def process_dialog(client, dialog, storage, config, log):
    # Only process private user chats
    if not isinstance(dialog.peer, InputPeerUser):
        return False

    user_id = dialog.peer.user_id

    replied = await storage.get_replied()
    if user_id in replied:
        return False

    # dialog.peer is an InputPeer containing the access_hash.
    # Passing it directly prevents Telethon from doing a database lookup.
    peer = dialog.peer

    last = await _last_message(client, peer)
    if last is None or getattr(last, "out", False):
        return False

    # Wait 5 seconds to batch consecutive messages
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
