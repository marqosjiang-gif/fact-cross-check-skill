#!/bin/bash
# weixin_search.sh — 微信公众号文章搜索通道（fact-cross-check-skill 第三后端）
# 主通道：搜狗微信搜索（weixin.sogou.com，免登录）
#
# 用法:
#   sh weixin_search.sh "<query>"              # 文章搜索，输出 Top10
#   sh weixin_search.sh "<query>" --limit=5    # 限制条数
#   sh weixin_search.sh "<query>" --json       # 原始 JSON（接流水线）
#
# 退出码: 0=有结果  2=无结果  3=被反爬拦截（调用方如实标注降级）  4=网络失败
# 合规：仅做免登录公开检索；反爬拦截时显式降级（不绕过、不伪造指纹），遵循站点访问条款

set -o pipefail

LIMIT=10
JSON_OUT=false
ARGS=()
for a in "$@"; do
  case "$a" in
    --limit=*) LIMIT="${a#*=}" ;;
    --json) JSON_OUT=true ;;
    *) ARGS+=("$a") ;;
  esac
done
QUERY="${ARGS[*]}"
if [ -z "$QUERY" ]; then
  echo "用法: sh weixin_search.sh \"<query>\" [--limit=N] [--json]" >&2
  exit 4
fi

PY="${PYTHON_BIN:-python3}"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
URL="https://weixin.sogou.com/weixin?type=2&query=$(
  "$PY" - "$QUERY" <<'PYEOF'
import sys, urllib.parse
print(urllib.parse.quote(sys.argv[1]))
PYEOF
)"

HTML=$(curl -sL --max-time 20 -A "$UA" \
  -H "Referer: https://weixin.sogou.com/" \
  -H "Accept-Language: zh-CN,zh;q=0.9" \
  "$URL" 2>/dev/null)

if [ -z "$HTML" ]; then
  echo "❌ 网络失败：搜狗微信搜索无响应" >&2
  exit 4
fi

# 反爬检测
if echo "$HTML" | grep -q "antispider\|验证码\|seccodeImage\|切换输入法"; then
  echo "⚠️ 搜狗反爬拦截（验证码/antispider）——调用方应如实标注「⚠️ 公众号通道未完成」，不编造原文内容" >&2
  exit 3
fi

# 结构化解析（纯 stdlib）
RESULT=$("$PY" - "$HTML" "$LIMIT" "$JSON_OUT" <<'PYEOF'
import sys, re, json, html

html_src, limit, json_out = sys.argv[1], int(sys.argv[2]), sys.argv[3] == "true"

items = []
# 每条结果容器
blocks = re.split(r'<div class="txt-box">', html_src)[1:]
for b in blocks[:limit]:
    # 标题 + 相对链接
    m = re.search(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', b, re.S)
    if not m:
        continue
    href, title = m.group(1), re.sub(r'<[^>]+>', '', m.group(2))
    title = html.unescape(title).strip()
    # 公众号名（仅认 class="account"，防止误抓标题链接）
    acct = ""
    ma = re.search(r'class="account"[^>]*>(.*?)</a>', b, re.S)
    if ma:
        acct = html.unescape(re.sub(r'<[^>]+>', '', ma.group(1))).strip()
    # 日期：优先 timeConvert（JS 时间戳秒），回退 s2 文本
    date = ""
    mt = re.search(r"timeConvert\('(\d+)'\)", b)
    if mt:
        import datetime
        date = datetime.datetime.fromtimestamp(int(mt.group(1))).strftime("%Y-%m-%d")
    else:
        ms = re.search(r'class="s2"[^>]*>(.*?)</span>', b, re.S)
        if ms:
            date = re.sub(r'<[^>]+>', '', ms.group(1)).strip()
    # 摘要
    summ = ""
    mp = re.search(r'class="txt-info"[^>]*>(.*?)</p>', b, re.S)
    if mp:
        summ = html.unescape(re.sub(r'<[^>]+>', '', mp.group(1))).strip()[:120]
    link = html.unescape("https://weixin.sogou.com" + href if href.startswith("/link") else href)
    items.append({"title": title, "account": acct, "date": date, "summary": summ, "link": link})

if json_out:
    print(json.dumps({"query_count": len(items), "items": items}, ensure_ascii=False, indent=2))
else:
    if not items:
        print("（无结果）")
        sys.exit(2)
    for i, it in enumerate(items, 1):
        print(f"{i}. 《{it['title']}》")
        meta = " | ".join(x for x in [it["account"], it["date"]] if x)
        if meta:
            print(f"   {meta}")
        if it["summary"]:
            print(f"   摘要: {it['summary']}")
        print(f"   链接: {it['link']}")
PYEOF
)

RC=$?
if [ "$JSON_OUT" = true ]; then
  echo "$RESULT"
else
  echo "$RESULT"
fi
exit $RC
