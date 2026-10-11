#!/bin/sh
# 消息去伪存真（fact-cross-check-skill）— 腾讯较真 CLI 包装
# 默认转发到 `tencent-news-cli jiaozhen --query=<内容> --caller fact-cross-check`
# 调用方可以显式传 `jiaozhen` 子命令 + 自定义 `--caller`，脚本会自动透传。
CLI="${JIAOZHEN_CLI:-$HOME/.tencent-news-cli/bin/tencent-news-cli}"

if [ ! -x "$CLI" ]; then
  CLI="$(command -v tencent-news-cli 2>/dev/null || echo "")"
fi

if [ -z "$CLI" ] || [ ! -x "$CLI" ]; then
  echo "ERROR: tencent-news-cli 未找到。请先安装 CLI。" >&2
  exit 127
fi

# 注入 jiaozhen 子命令（除非调用方已显式传入）
case " $* " in
  *" jiaozhen "*) ;;
  *) set -- "jiaozhen" "$@" ;;
esac

# 注入 caller 默认上报名（除非调用方已显式传入）
case " $* " in
  *" --caller "*) ;;
  *) set -- "$@" "--caller" "fact-cross-check" ;;
esac

exec "$CLI" "$@"
