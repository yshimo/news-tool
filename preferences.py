#!/usr/bin/env python3

import json
import os
import urllib.request
from pathlib import Path

PREFS_FILE = Path(__file__).parent / "preferences.json"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"


def load_prefs() -> dict:
    if PREFS_FILE.exists():
        return json.loads(PREFS_FILE.read_text())
    return {"liked": [], "disliked": []}


def save_feedback(title: str, liked: bool):
    prefs = load_prefs()
    key = "liked" if liked else "disliked"
    if title not in prefs[key]:
        prefs[key].append(title)
    PREFS_FILE.write_text(json.dumps(prefs, ensure_ascii=False, indent=2))


def get_preference_prompt() -> str:
    prefs = load_prefs()
    liked = prefs["liked"][-20:]
    disliked = prefs["disliked"][-20:]

    if not liked and not disliked:
        return ""

    liked_str = "\n".join(f"- {t}" for t in liked) if liked else "なし"
    disliked_str = "\n".join(f"- {t}" for t in disliked) if disliked else "なし"

    return f"""
ユーザーの好み（過去のフィードバックより）:
興味あり:
{liked_str}
興味なし:
{disliked_str}

上記を参考に、ユーザーが興味を持ちそうな記事を優先して要約・展望を書いてください。
"""


def score_articles(articles: list[dict]) -> list[dict]:
    prefs = load_prefs()
    liked_words = set(" ".join(prefs["liked"]).lower().split())
    disliked_words = set(" ".join(prefs["disliked"]).lower().split())

    for a in articles:
        words = set(a["title"].lower().split())
        score = len(words & liked_words) - len(words & disliked_words)
        a["score"] = score

    return sorted(articles, key=lambda x: x.get("score", 0), reverse=True)
