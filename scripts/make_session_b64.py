# ============================================
#  scripts/make_session_b64.py - encode a Telethon session as base64
#  All code and comments are English. No emojis.
# ============================================
import base64
import sys
from pathlib import Path

def main():
    if len(sys.argv) != 2:
        print("usage: python -m scripts.make_session_b64 <session_file>")
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"[!] not found: {path}")
        sys.exit(1)
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode()
    print(b64)
    print(f"\n[i] size: {len(raw)} bytes -> {len(b64)} base64 chars", file=sys.stderr)

if __name__ == "__main__":
    main()
