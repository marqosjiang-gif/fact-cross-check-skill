#!/bin/sh
# jiaozhen-factcheck 状态检查
# 输出 JSON，字段对齐 SKILL.md Phase 1 解析约定。
CLI="${JIAOZHEN_CLI:-$HOME/.tencent-news-cli/bin/tencent-news-cli}"

cliPath="$CLI"
cliSource="global"
cliExists="false"
if [ -x "$CLI" ]; then
  cliExists="true"
elif command -v tencent-news-cli >/dev/null 2>&1; then
  cliPath="$(command -v tencent-news-cli)"
  cliSource="global"
  cliExists="true"
else
  cliSource="none"
  cliPath=""
fi

# API Key 状态：通过 apikey-get / version 探测（不泄露明文）
apiKeyPresent="false"
apiKeyStatus="missing"
apiKeyError=""
if [ "$cliExists" = "true" ]; then
  # apikey-get 在配置缺失时会报错/返回空，配置后返回脱敏值
  out="$("$CLI" apikey-get 2>&1)"
  rc=$?
  if [ $rc -eq 0 ] && echo "$out" | grep -qE "ak_|AK_|[0-9a-f]{8}" ; then
    apiKeyPresent="true"
    apiKeyStatus="configured"
  else
    apiKeyError="$out"
  fi
fi

# 版本/更新探测
needUpdate="false"
updateError=""
if [ "$cliExists" = "true" ]; then
  vout="$("$CLI" version 2>&1)"
  if echo "$vout" | grep -qiE "需要更新|update available|new version"; then
    needUpdate="true"
  fi
fi

cat <<EOF
{
  "platform": {
    "cliPath": "$cliPath",
    "cliSource": "$cliSource"
  },
  "cliExists": $cliExists,
  "update": {
    "needUpdate": $needUpdate,
    "error": "$updateError"
  },
  "apiKey": {
    "present": $apiKeyPresent,
    "status": "$apiKeyStatus",
    "error": "$apiKeyError"
  }
}
EOF
