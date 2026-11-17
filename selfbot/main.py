# ============================================
#  selfbot/main.py - long-running loop for GitHub Actions
#  All code and comments are English. No emojis.
# ============================================
import asyncio
import base64
import sys
import time
import re
import hashlib
from datetime import datetime, timezone

from selfbot.config import Config
from selfbot.storage import GistStorage
from selfbot.handler import process_dialog
from userapi import VibeClient

def _log(msg):
    print(f"[selfbot] {msg}", flush=True)

async def _handle_self_commands(client, entity, started_time, log):
    """Checks for /ping command in Saved Messages."""
    try:
        msgs = await client.get_messages(entity, limit=1)
        if not msgs:
            return False
        last = msgs[0]
        
        if getattr(last, "out", False) and last.text:
            cmd = last.text.strip().lower()
            if cmd == "/ping":
                # Only reply if the command is recent (last 5 minutes)
                if last.date:
                    now = datetime.now(timezone.utc)
                    if (now - last.date).total_seconds() > 300:
                        return False
                        
                uptime_sec = int(time.monotonic() - started_time)
                m, s = divmod(uptime_sec, 60)
                h, m = divmod(m, 60)
                
                text = f"Pong!\n\nUptime: {h}h {m}m {s}s\nSelfbot is online."
                await client.send_message(entity, text)
                log("replied to /ping in Saved Messages")
                return True
    except Exception as e:
        log(f"error in self commands: {e}")
    return False

async def _run_once(client, storage, config, my_id, started_time, log):
    from telethon.tl.functions.messages import GetDialogsRequest
    from telethon.tl.types import InputPeerEmpty, PeerUser
    
    replied_count = 0
    try:
        result = await client.raw(GetDialogsRequest(
            offset_date=None, offset_id=0, offset_peer=InputPeerEmpty(),
            limit=300, hash=0,
        ))
        
        users_map = {u.id: u for u in (result.users or [])}
        
        for d in (result.dialogs or []):
            if not isinstance(d.peer, PeerUser):
                continue
                
            user_id = d.peer.user_id
            entity = users_map.get(user_id)
            
            if not entity:
                continue
                
            # Handle commands in Saved Messages (only for owner)
            if user_id == my_id:
                await _handle_self_commands(client, entity, started_time, log)
                continue
                
            try:
                if await process_dialog(client, d, entity, storage, config, log):
                    replied_count += 1
            except Exception as e:
                log(f"dialog error for {user_id}: {type(e).__name__}: {e}")
                
    except Exception as e:
        log(f"GetDialogsRequest error: {type(e).__name__}: {e}")
        
    return replied_count

async def main():
    cfg = Config()
    try:
        b64_clean = re.sub(r'[^A-Za-z0-9+/=]', '', cfg.session_b64)
        padding = len(b64_clean) % 4
        if padding:
            b64_clean += "=" * (4 - padding)
        raw = base64.b64decode(b64_clean)
        _log(f"decoded session size: {len(raw)} bytes")
        _log(f"session md5 hash: {hashlib.md5(raw).hexdigest()}")
    except Exception as e:
        _log(f"session decode error: {e}")
        sys.exit(1)

    cfg.session_path.parent.mkdir(parents=True, exist_ok=True)
    session_file = cfg.session_path.with_suffix(".session")
    session_file.write_bytes(raw)
    _log(f"session restored to {session_file}")

    client = VibeClient(session_path=str(cfg.session_path))
    storage = GistStorage(cfg.gh_token, cfg.gist_id, cfg.gist_filename)

    # Verify Gist access
    try:
        await storage._ensure_cache()
        _log("gist loaded successfully")
    except Exception as e:
        _log(f"FATAL: Failed to load gist: {e}")
        _log("Please check your GH_TOKEN (must have 'gist' scope) and GIST_ID.")
        sys.exit(3)

    try:
        await client.connect()
        _log("connected")
        if not await client.is_authorized():
            _log("session not authorized")
            sys.exit(2)
        _log("authorized")
        
        me = await client.get_me()
        my_id = me.id
        _log(f"selfbot running for account ID: {my_id}")
        
        started = time.monotonic()
        while True:
            elapsed = time.monotonic() - started
            if elapsed >= cfg.max_runtime_seconds:
                _log(f"max runtime reached ({int(elapsed)}s), exiting")
                break
            try:
                n = await _run_once(client, storage, cfg, my_id, started, _log)
                if n:
                    _log(f"replied to {n} new dialog(s)")
            except Exception as e:
                _log(f"loop error: {type(e).__name__}: {e}")
            await asyncio.sleep(cfg.poll_interval)
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass
        try:
            cfg.session_path.unlink()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
