#!/usr/bin/env python3

import feedparser
import argparse
import sys
import re
import json
import urllib.request
from datetime import datetime, timezone
from deep_translator import GoogleTranslator

FEEDS = {
    "BBC World":     "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera":    "https://www.aljazeera.com/xml/rss/all.xml",
    "The Guardian":  "https://www.theguardian.com/world/rss",
    "NPR World":     "https://feeds.npr.org/1004/rss.xml",
    "NHK":           "https://www3.nhk.or.jp/rss/news/cat0.xml",
}

JAPANESE_SOURCES = {"NHK"}
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"

_translator = GoogleTranslator(source="auto", target="ja")


def translate(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"<[^>]+>", "", text).strip()
    try:
        return _translator.translate(text)
    except Exception:
        return text


def fetch_articles(max_per_feed: int) -> list[dict]:
    articles = []
    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_per_feed]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                if title:
                    articles.append({
                        "source": source,
                        "title": title,
                        "summary": summary[:400] if summary else "",
                        "link": entry.get("link", ""),
                        "needs_translation": source not in JAPANESE_SOURCES,
                    })
        except Exception as e:
            print(f"Warning: {source} の取得に失敗しました: {e}", file=sys.stderr)
    return articles


def generate_digest(articles: list[dict]) -> str:
    titles = "\n".join(
        f"- {a['title']}" for a in articles[:15]
    )
    prompt = f"""Read these news headlines and respond in Japanese only.

Write exactly two sections:

## 本日のニュース要約
(Summarize today's news in 3 sentences in Japanese)

## 今後の展望
(Describe future outlook in 3 sentences in Japanese)

Headlines:
{titles}"""

    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }).encode()

    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=300) as res:
            return json.loads(res.read())["response"].strip()
    except Exception as e:
        return f"（要約生成に失敗しました: {e}）"


def build_output(articles: list[dict], digest: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# 世界ニュース一覧",
        f"\n**収集日時:** {now}  \n**記事数:** {len(articles)} 件  \n**ソース:** {', '.join(FEEDS.keys())}",
        "\n---\n",
        digest,
        "\n---\n",
    ]
    current_source = None
    for a in articles:
        if a["source"] != current_source:
            current_source = a["source"]
            lines.append(f"\n## {current_source}\n")
        title = translate(a["title"]) if a["needs_translation"] else a["title"]
        summary = translate(a["summary"]) if a["needs_translation"] else a["summary"]
        lines.append(f"- **{title}**")
        if summary:
            lines.append(f"  {summary}")
        if a["link"]:
            lines.append(f"  {a['link']}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="世界ニュース収集ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""使用例:
  python news.py                    # 標準出力
  python news.py --output news.md   # ファイルに保存
  python news.py --max 10           # フィードあたり10件取得""",
    )
    parser.add_argument("--max", type=int, default=20, metavar="N", help="フィードあたりの最大取得記事数 (デフォルト: 20)")
    parser.add_argument("--output", metavar="FILE", help="Markdownファイルへの出力先 (省略時は標準出力)")
    args = parser.parse_args()

    print("ニュースフィードを取得中...", file=sys.stderr)
    articles = fetch_articles(args.max)

    if not articles:
        print("エラー: 記事を1件も取得できませんでした。ネットワーク接続を確認してください。", file=sys.stderr)
        sys.exit(1)

    print(f"{len(articles)} 件取得。要約・考察を生成中 (llama3.2)...", file=sys.stderr)
    digest = generate_digest(articles)

    print("翻訳中...", file=sys.stderr)
    output = build_output(articles, digest)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"保存完了: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
