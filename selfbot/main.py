# ============================================
#  selfbot/main.py - long-running loop for GitHub Actions
#  All code and comments are English. No emojis.
# ============================================
import asyncio
import base64
import sys
import time

from selfbot.config import Config
from selfbot.storage import GistStorage
from selfbot.handler import process_dialog
from userapi import VibeClient

def _log(msg):
    print(f"[selfbot] {msg}", flush=True)

async def _run_once(client, storage, config):
    replied_count = 0
    dialogs = await client.get_dialogs(limit=300)
    for d in dialogs:
        try:
            if await process_dialog(client, d, storage, config, _log):
                replied_count += 1
        except Exception as e:
            _log(f"dialog error: {type(e).__name__}: {e}")
    return replied_count

async def main():
    cfg = Config()
    try:
        raw = base64.b64decode(cfg.session_b64)
    except Exception as e:
        _log(f"session decode error: {e}")
        sys.exit(1)

    cfg.session_path.parent.mkdir(parents=True, exist_ok=True)
    session_file = cfg.session_path.with_suffix(".session")
    session_file.write_bytes(raw)
    _log(f"session restored to {session_file}")

    client = VibeClient(session_path=str(cfg.session_path))
    storage = GistStorage(cfg.gh_token, cfg.gist_id, cfg.gist_filename)

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
