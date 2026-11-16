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

from selfbot.config import Config
from selfbot.storage import GistStorage
from selfbot.handler import process_dialog
from userapi import VibeClient

def _log(msg):
    print(f"[selfbot] {msg}", flush=True)

async def _run_once(client, storage, config):
    from telethon.tl.functions.messages import GetDialogsRequest
    from telethon.tl.types import InputPeerEmpty, PeerUser
    
    replied_count = 0
    try:
        result = await client.raw(GetDialogsRequest(
            offset_date=None, offset_id=0, offset_peer=InputPeerEmpty(),
            limit=300, hash=0,
        ))
        
        # Map valid users
        users_map = {u.id: u for u in (result.users or [])}
        
        for d in (result.dialogs or []):
            # In Telethon, dialog.peer is a PeerUser, not InputPeerUser
            if not isinstance(d.peer, PeerUser):
                continue
                
            user_id = d.peer.user_id
            entity = users_map.get(user_id)
            
            if not entity:
                continue
                
            try:
                if await process_dialog(client, d, entity, storage, config, _log):
                    replied_count += 1
            except Exception as e:
                _log(f"dialog error for {user_id}: {type(e).__name__}: {e}")
                
    except Exception as e:
        _log(f"GetDialogsRequest error: {type(e).__name__}: {e}")
        
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

    # Verify Gist access before connecting to Vibe
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
        started = time.monotonic()
        while True:
            elapsed = time.monotonic() - started
            if elapsed >= cfg.max_runtime_seconds:
                _log(f"max runtime reached ({int(elapsed)}s), exiting")
                break
            try:
                n = await _run_once(client, storage, cfg)
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
