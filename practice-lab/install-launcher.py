#!/usr/bin/env python3
"""Register this checkout in the current user's desktop application menu."""
import os
from pathlib import Path

script = Path(__file__).resolve().with_name('launch.sh')
# Desktop Entry Exec quoting is not shell quoting.
quoted = str(script).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
applications = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'applications'
applications.mkdir(parents=True, exist_ok=True)
launcher = applications / 'learning-notes-lab.desktop'
launcher.write_text(f'''[Desktop Entry]
Type=Application
Name=学习笔记 · 实践工坊
Comment=在机器学习场景中练习 Linux 命令
Exec="{quoted}"
Icon=utilities-terminal
Terminal=false
Categories=Education;Development;
''')
print(f'已添加应用菜单入口：{launcher}')
