#!/bin/bash

cd "$(dirname "$0")"

# Ollamaが起動していなければ起動
brew services start ollama > /dev/null 2>&1

# Flaskサーバーをバックグラウンドで起動
python app.py &
FLASK_PID=$!

sleep 2

# ngrokを固定ドメインで起動
ngrok http --domain=contents-repose-unguarded.ngrok-free.dev 8080
