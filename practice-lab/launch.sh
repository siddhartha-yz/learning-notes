#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! command -v bwrap >/dev/null || ! /usr/bin/python3 -c "import gi; gi.require_version('Gtk', '3.0')" 2>/dev/null; then
  echo '请安装依赖：sudo apt install python3-gi gir1.2-gtk-3.0 bubblewrap' >&2
  exit 1
fi
exec /usr/bin/python3 app.py
