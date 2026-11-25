#!/bin/sh
# PROTOTYPE (issue #87), throwaway. Serves assets/ (the pages need ../../vendor/katex
# and ../fonts, which Firefox will not load from file://) and opens the viewer.
# Usage: sh assets/prototype-skald/run.sh   (Ctrl+C stops the server)
PORT="${PORT:-8790}"
cd "$(dirname "$0")/.." || exit 1
URL="http://127.0.0.1:$PORT/prototype-skald/"
echo "Skald prototype viewer: $URL"
(sleep 1; xdg-open "$URL" >/dev/null 2>&1 || open "$URL" >/dev/null 2>&1) &
exec python3 -m http.server "$PORT" --bind 127.0.0.1
