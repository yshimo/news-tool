#!/usr/bin/env python3

from flask import Flask, render_template, jsonify, request
from news import fetch_articles, generate_digest, translate, FEEDS
from preferences import save_feedback, get_preference_prompt, score_articles
import threading
import time

app = Flask(__name__)

_cache = {"data": None, "updated_at": 0}
_lock = threading.Lock()


def build_news():
    articles = fetch_articles(20)
    if not articles:
        return None

    # 好みに基づいてスコアリング・ソート
    articles = score_articles(articles)

    pref_prompt = get_preference_prompt()
    digest = generate_digest(articles, pref_prompt)

    result = []
    for a in articles:
        title = translate(a["title"]) if a["needs_translation"] else a["title"]
        summary = translate(a["summary"]) if a["needs_translation"] else a["summary"]
        result.append({
            "source": a["source"],
            "title": title,
            "original_title": a["title"],
            "summary": summary,
            "link": a["link"],
        })

    return {"digest": digest, "articles": result}


def refresh_cache():
    with _lock:
        data = build_news()
        if data:
            _cache["data"] = data
            _cache["updated_at"] = time.time()


threading.Thread(target=refresh_cache, daemon=True).start()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/news")
def api_news():
    if _cache["data"] is None:
        return jsonify({"status": "loading"}), 202
    return jsonify({**_cache["data"], "updated_at": int(_cache["updated_at"])})


@app.route("/api/refresh")
def api_refresh():
    threading.Thread(target=refresh_cache, daemon=True).start()
    return jsonify({"status": "refreshing"})


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    data = request.get_json()
    title = data.get("title", "")
    liked = data.get("liked", True)
    if title:
        save_feedback(title, liked)
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
