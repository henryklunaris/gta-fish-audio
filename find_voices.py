"""Search Fish Audio public voices. Usage: python3 find_voices.py "gangster" "cop" ..."""
import os, sys, requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
KEY = os.environ["FISH_API_KEY"]

for q in sys.argv[1:] or ["gangster"]:
    r = requests.get("https://api.fish.audio/model", headers={"Authorization": f"Bearer {KEY}"},
                     params={"title": q, "page_size": 8, "sort_by": "score", "language": "en"}, timeout=20)
    r.raise_for_status()
    print(f"\n== {q}")
    for m in r.json().get("items", []):
        print(f"{m['_id']}  {m.get('task_count', 0):>8}  {m['title'][:60]}")
