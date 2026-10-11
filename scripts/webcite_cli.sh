#!/bin/sh
# webcite_cli.sh — WebCite 查证包装器（shell 入口）
# 对齐 jiaozhen run-cli.sh：基础设施交给脚本，智能体只选参数。
# 实际调用 scripts/webcite_cli.py（纯标准库，无需 pip）。

DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$DIR/webcite_cli.py"

# 优先使用受管 python，回退到 PATH 中 python3
MNG="${MANAGED_PYTHON:-$HOME/.workbuddy/binaries/python/current/bin/python3}"
if [ -x "$MNG" ]; then
  PYTHON="$MNG"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
else
  echo "ERROR: 未找到 python3（受管或系统）。" >&2
  exit 127
fi

if [ ! -f "$PY" ]; then
  echo "ERROR: webcite_cli.py 未找到（$PY）。" >&2
  exit 127
fi

exec "$PYTHON" "$PY" "$@"
