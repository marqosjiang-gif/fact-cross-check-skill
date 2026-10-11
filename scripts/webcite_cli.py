#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
webcite_cli.py — WebCite API 查证包装器（CLI）

设计约定（对齐 jiaozhen-factcheck 的「基础设施交给脚本」原则）：
- 仅用标准库（urllib + json），不依赖 requests，避免环境差异。
- 查证失败 / key 缺失 / 额度耗尽时，明确报错并以非零退出，**绝不回退到 WebSearch 自行编造**。
- 输出结构化中文 markdown：立场（支持/反驳/中立）+ 来源可信度评分 + 结构化引用。

API 文档：https://webcite.co/api-docs
端点：POST {BASE}/api/v1/verify
认证：Header `x-api-key: <KEY>`
计费：基础检索 2 + stance 1 + verdict 1 = 完整 4 credits（免费档 50/月）
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

DEFAULT_BASE = "https://api.webcite.co"
CONFIG_ENV = os.path.expanduser("~/.webcite/config.env")

# WebCite 枚举 → 中文映射
VERDICT_MAP = {
    "supported": "支持",
    "partially_false": "部分失实",
    "contradicted": "反驳",
    "neutral": "中立",
    "mixed": "混合（支持与反驳并存）",
    "unverifiable": "无法核实",
}
STANCE_MAP = {
    "supports": "支持",
    "contradicts": "反驳",
    "partially_supports": "部分支持",
    "neutral": "中立",
    "inconclusive": "无法判定",
}


def load_api_key(explicit=None):
    """key 优先级：命令行 --key > 环境变量 WEBCITE_API_KEY > ~/.webcite/config.env"""
    if explicit:
        return explicit.strip()
    env = os.environ.get("WEBCITE_API_KEY")
    if env and env.strip():
        return env.strip()
    if os.path.isfile(CONFIG_ENV):
        try:
            with open(CONFIG_ENV, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    if k.strip() == "WEBCITE_API_KEY" and v.strip():
                        return v.strip()
        except OSError:
            pass
    return None


def load_base_url():
    if os.environ.get("WEBCITE_API_URL"):
        return os.environ["WEBCITE_API_URL"].rstrip("/")
    if os.path.isfile(CONFIG_ENV):
        try:
            with open(CONFIG_ENV, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    if k.strip() == "WEBCITE_API_URL" and v.strip():
                        return v.strip().rstrip("/")
        except OSError:
            pass
    return DEFAULT_BASE


def call_verify(base, api_key, claim, include_stance=True, include_verdict=True,
                decompose=False, thread_id=None):
    """调用 WebCite 流式端点并聚合 SSE 事件为统一结构。

    注意：非流式 `/api/v1/verify` 在当前免费档下持续返回 totalResults=0，
    因此默认使用 `/api/v1/verify/stream`，实时聚合 citation / verdict / result。
    """
    url = f"{base}/api/v1/verify/stream"
    payload = {
        "claim": claim,
        "include_stance": include_stance,
        "include_verdict": include_verdict,
        "decompose_claim": decompose,
    }
    if thread_id:
        payload["thread_id"] = thread_id
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    citations = {}
    verdict = None
    result = None
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                payload_str = line[5:].strip()
                if not payload_str:
                    continue
                try:
                    event = json.loads(payload_str)
                except json.JSONDecodeError:
                    continue
                etype = event.get("type")
                edata = event.get("data") or {}
                if etype == "citation":
                    cid = edata.get("id")
                    if cid is not None:
                        citations[cid] = edata
                elif etype == "citation-update":
                    cid = edata.get("id")
                    if cid is not None and cid in citations:
                        citations[cid].update(edata)
                elif etype == "verdict":
                    verdict = edata
                elif etype == "result":
                    result = edata
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        return None, f"HTTP {e.code}: {body[:400]}"
    except urllib.error.URLError as e:
        return None, f"网络错误: {e.reason}"
    except Exception as e:  # noqa: BLE001
        return None, f"未知错误: {e}"

    # 优先使用 result 事件中的完整结构
    if result and isinstance(result.get("claim_groups"), list) and result["claim_groups"]:
        group = result["claim_groups"][0]
        return {
            "claim": group.get("claim") or claim,
            "citations": group.get("citations") or list(citations.values()),
            "verdict": group.get("verdict") or verdict or {},
            "totalResults": group.get("citation_count") or len(citations),
        }, None

    # 降级：手动聚合
    return {
        "claim": claim,
        "citations": list(citations.values()),
        "verdict": verdict or {},
        "totalResults": len(citations),
    }, None


def render_markdown(resp):
    lines = []
    verd = (resp.get("verdict") or {}).get("result")
    conf = (resp.get("verdict") or {}).get("confidence")
    if verd:
        cn = VERDICT_MAP.get(verd, verd)
        conf_s = f"（置信度 {conf}%）" if conf is not None else ""
        lines.append(f"【查证结论】{cn}{conf_s}")
    else:
        lines.append("【查证结论】未返回总体验证结论（可 retry 开启 include_verdict）")

    sb = (resp.get("verdict") or {}).get("stance_breakdown") or {}
    if sb:
        parts = []
        for en, cn in (("supports", "支持"), ("partially_supports", "部分支持"),
                       ("contradicts", "反驳"), ("neutral", "中立"),
                       ("inconclusive", "无法判定")):
            if sb.get(en):
                parts.append(f"{cn} {sb[en]}")
        lines.append("【立场分布】" + " ｜ ".join(parts) if parts else "【立场分布】无")

    citations = resp.get("citations") or []
    lines.append("")
    lines.append("【来源可信度与引用】")
    if citations:
        lines.append("| # | 来源 | 立场 | 可信度 | 类型 | 链接 |")
        lines.append("|---|------|------|--------|------|------|")
        for i, c in enumerate(citations, 1):
            stance = STANCE_MAP.get(c.get("stance"), c.get("stance") or "—")
            cred = c.get("credibility_score")
            cred_s = f"{cred}" if cred is not None else "—"
            stype = c.get("source_type") or "—"
            url = c.get("url") or "—"
            title = (c.get("title") or "—").replace("|", "\\|")
            lines.append(f"| {i} | {title} | {stance} | {cred_s} | {stype} | {url} |")
    else:
        lines.append("（无来源返回）")

    findings = (resp.get("verdict") or {}).get("key_findings") or []
    if findings:
        lines.append("")
        lines.append("【关键发现】")
        for fnd in findings:
            fid = fnd.get("finding") or ""
            fconf = fnd.get("confidence")
            fconf_s = f"（置信 {fconf}%）" if fconf is not None else ""
            lines.append(f"- {fid}{fconf_s}")

    corrections = (resp.get("verdict") or {}).get("corrections") or []
    if corrections:
        lines.append("")
        lines.append("【纠错】")
        for cor in corrections:
            lines.append(f"- {cor}")

    summary = (resp.get("verdict") or {}).get("summary")
    if summary:
        lines.append("")
        lines.append(f"【摘要】{summary}")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="WebCite 事实查证 CLI（立场+可信度+引用）")
    ap.add_argument("claim", help="待查证的事实声明 / 命题 / 叙事")
    ap.add_argument("--key", help="WebCite API Key（缺省读 env 或 ~/.webcite/config.env）")
    ap.add_argument("--base", help="API base url（缺省读 env 或默认）")
    ap.add_argument("--no-stance", action="store_true", help="跳过立场分析（省 1 credit）")
    ap.add_argument("--no-verdict", action="store_true", help="跳过总体验证结论（省 1 credit）")
    ap.add_argument("--decompose", action="store_true", help="复杂命题拆解为子声明分别验证")
    ap.add_argument("--thread-id", help="会话线程 ID，用于分组多次查证")
    ap.add_argument("--json", action="store_true", help="输出原始 JSON（不渲染 markdown）")
    args = ap.parse_args()

    api_key = load_api_key(args.key)
    if not api_key:
        sys.stderr.write(
            "ERROR: 未配置 WebCite API Key。\n"
            "获取：https://webcite.co/api-keys （免费档 50 credits/月）\n"
            "配置：export WEBCITE_API_KEY=xxx  或写入 ~/.webcite/config.env（WEBCITE_API_KEY=xxx）\n"
        )
        return 2

    base = args.base or load_base_url()
    resp, err = call_verify(
        base, api_key, args.claim,
        include_stance=not args.no_stance,
        include_verdict=not args.no_verdict,
        decompose=args.decompose,
        thread_id=args.thread_id,
    )
    if err:
        sys.stderr.write(f"ERROR: WebCite 调用失败 — {err}\n")
        return 3

    if args.json:
        print(json.dumps(resp, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(resp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
