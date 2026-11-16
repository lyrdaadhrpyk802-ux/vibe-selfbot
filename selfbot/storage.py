# ============================================
#  selfbot/storage.py - replied-state persisted in a private Gist
#  All code and comments are English. No emojis.
# ============================================
import asyncio
import json
import aiohttp

GITHUB_API = "https://api.github.com"

class GistStorage:
    def __init__(self, token, gist_id, filename="replied.json"):
        self._token = token
        self._gist_id = gist_id
        self._filename = filename
        self._lock = asyncio.Lock()
        self._cache = None
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "vibe-selfbot",
        }

    async def _load_from_gist(self, session):
        url = f"{GITHUB_API}/gists/{self._gist_id}"
        async with session.get(url, headers=self._headers) as r:
            if r.status != 200:
                raise RuntimeError(f"gist load failed: {r.status}")
            data = await r.json()
        files = data.get("files") or {}
        entry = files.get(self._filename)
        if not entry:
            return {"replied": []}
        content = entry.get("content") or ""
        if not content.strip():
            return {"replied": []}
        try:
            parsed = json.loads(content)
        except Exception:
            return {"replied": []}
        if not isinstance(parsed, dict):
            return {"replied": []}
        parsed.setdefault("replied", [])
        return parsed

    async def _save_to_gist(self, session, payload):
        url = f"{GITHUB_API}/gists/{self._gist_id}"
        body = {
            "files": {
                self._filename: {
                    "content": json.dumps(payload, indent=2, ensure_ascii=False),
                }
            }
        }
        async with session.patch(url, headers=self._headers, json=body) as r:
            if r.status not in (200, 201):
                text = await r.text()
                raise RuntimeError(f"gist save failed {r.status}: {text[:200]}")

    async def _ensure_cache(self):
        if self._cache is not None:
            return
        async with aiohttp.ClientSession() as session:
            self._cache = await self._load_from_gist(session)

    async def get_replied(self):
        async with self._lock:
            await self._ensure_cache()
            return set(self._cache.get("replied") or [])

    async def add_replied(self, user_id):
        async with self._lock:
            await self._ensure_cache()
            replied = set(self._cache.get("replied") or [])
            if user_id in replied:
                return False
            replied.add(user_id)
            self._cache["replied"] = sorted(replied)
            async with aiohttp.ClientSession() as session:
                await self._save_to_gist(session, self._cache)
            return True
