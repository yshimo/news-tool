#!/usr/bin/env python3

from flask import Flask, render_template, jsonify
from news import fetch_articles, generate_digest, translate, FEEDS
import threading
import time

app = Flask(__name__)

_cache = {"data": None, "updated_at": 0}
_lock = threading.Lock()


def build_news():
    articles = fetch_articles(20)
    if not articles:
        return None

    digest = generate_digest(articles)

    result = []
    for a in articles:
        title = translate(a["title"]) if a["needs_translation"] else a["title"]
        summary = translate(a["summary"]) if a["needs_translation"] else a["summary"]
        result.append({
            "source": a["source"],
            "title": title,
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


# 起動時にバックグラウンドで取得開始
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
