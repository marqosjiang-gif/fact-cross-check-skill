#!/bin/bash
# verify.sh — 消息去伪存真 统一入口
# 自动选择后端：中文 → jiaozhen；英文 → webcite；--source 显式覆盖
#
# 用法:
#   bash verify.sh "<claim>"                       # 自动选择
#   bash verify.sh "<claim>" --source=both        # 双后端交叉
#   bash verify.sh "<claim>" --source=jiaozhen    # 强制中文主源
#   bash verify.sh "<claim>" --source=webcite     # 强制国际源
#   bash verify.sh "<claim>" --json               # 原始 JSON 输出
#   bash verify.sh --help

set -e

SKILL_DIR="${FACT_CROSS_CHECK_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
JIAOZHEN="$SKILL_DIR/scripts/jiaozhen_cli.sh"
WEBCITE="$SKILL_DIR/scripts/webcite_cli.sh"
WEIXIN="$SKILL_DIR/scripts/weixin_search.sh"

usage() {
  cat <<EOF
消息去伪存真 verify.sh

  bash verify.sh "<claim>" [--source=auto|jiaozhen|webcite|weixin|both] [--json]

  --source=auto    自动选择：中文→jiaozhen；英文→webcite；
                   中文且含「公众号/报告/政策/说明/公告/指南/规则/费率」→ 额外加挂微信通道
  --source=jiaozhen  强制腾讯较真（中文主源）
  --source=webcite   强制 WebCite（国际源补强）
  --source=weixin    强制微信公众号通道（搜狗微信搜索）
  --source=both      双后端交叉（中文命题附赠微信通道）
  --json            输出原始 JSON（不渲染中文结构化报告）
  --help            显示帮助

示例:
  bash verify.sh "中美关税协议签署"
  bash verify.sh "The Fed cut rates by 25bps" --source=webcite
  bash verify.sh "某平台 2026 中秋国庆消费报告发布" --source=both
  bash verify.sh "抖音生活服务 中秋国庆消费报告 原文" --source=weixin
EOF
}

# 中文检测：claim 字符串中是否含中文字符（用 perl，macOS 自带）
has_chinese() {
  if echo "$1" | perl -CSDA -ne 'exit !/\p{Han}/' >/dev/null 2>&1; then
    return 0  # 含中文
  else
    return 1  # 不含
  fi
}

CLAIM=""
SOURCE="auto"
JSON_OUT=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source=*)
      SOURCE="${1#*=}"
      shift
      ;;
    --json)
      JSON_OUT=true
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    -*)
      echo "未知选项: $1" >&2
      usage
      exit 1
      ;;
    *)
      CLAIM="$1"
      shift
      ;;
  esac
done

if [ -z "$CLAIM" ]; then
  usage
  exit 1
fi

# 自动选择：英文→webcite；中文保持 auto（由 case 分支决定是否加挂微信通道）
if [ "$SOURCE" = "auto" ]; then
  if ! has_chinese "$CLAIM"; then
    SOURCE="webcite"
  fi
fi

# 微信通道加挂判定：中文命题 + 官方发布类关键词（报告/政策/说明/公告/指南/规则/费率/公众号/文件）
weixin_relevant() {
  has_chinese "$1" || return 1
  echo "$1" | grep -qE "公众号|报告|政策|说明|公告|指南|规则|费率|官方|文件|费改" 
}

run_jiaozhen() {
  if [ "$JSON_OUT" = true ]; then
    # jiaozhen CLI 暂无 --json 输出，走 stdout 原文
    sh "$JIAOZHEN" --query "$CLAIM" --caller fact-cross-check
  else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔍 腾讯较真（中文主源）· 后端=jiaozhen"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    sh "$JIAOZHEN" --query "$CLAIM" --caller fact-cross-check
  fi
}

run_webcite() {
  if [ "$JSON_OUT" = true ]; then
    sh "$WEBCITE" "$CLAIM" --json
  else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔍 WebCite（国际源补强）· 后端=webcite"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    sh "$WEBCITE" "$CLAIM"
  fi
}

run_weixin() {
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🔍 微信公众号通道（搜狗微信搜索）· 后端=weixin"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  set +e
  WX_OUT=$(sh "$WEIXIN" "$CLAIM" 2>&1)
  WX_RC=$?
  set -e
  echo "$WX_OUT"
  case $WX_RC in
    0) : ;;
    2) echo "（微信通道：无结果，不代表命题为假）" ;;
    3) echo "⚠️ 降级提示：搜狗被反爬拦截 → 如实标注「⚠️ 公众号通道未完成」，不编造原文内容" ;;
    *) echo "⚠️ 微信通道网络失败（非致命，不阻断主流程）" ;;
  esac
  return 0
}

case "$SOURCE" in
  jiaozhen)
    run_jiaozhen
    ;;
  webcite)
    run_webcite
    ;;
  weixin)
    run_weixin
    ;;
  both)
    run_jiaozhen
    echo
    if weixin_relevant "$CLAIM"; then
      run_weixin
      echo
    fi
    run_webcite
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🧭 双源交叉仲裁"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "（详见上方两源输出。仲裁规则见 SKILL.md「双源交叉仲裁规则」；"
    echo "  公众号原文 > 媒体转载；≥2 家转载不一致时须回溯原文，见「甄选规则」）"
    ;;
  auto)
    # auto 模式：中文主源 + 命中官方发布类关键词时加挂微信通道
    run_jiaozhen
    if weixin_relevant "$CLAIM"; then
      echo
      echo "（命题命中官方发布类关键词，自动加挂微信通道找公众号原文）"
      run_weixin
    fi
    ;;
  *)
    echo "未知 --source: $SOURCE（应为 auto/jiaozhen/webcite/weixin/both）" >&2
    exit 1
    ;;
esac