<div align="center">

# fact-cross-check-skill

### 消息去伪存真 — 三通道查证 + 甄选规则工具集

**Verify. Cross-check. Grade. Cite.**

一个面向 [WorkBuddy](https://www.workbuddy.cn) / Claude Code 类 Agent 的 **Skill**：对「叙事 / 事件 / 政策 / 平台规则 / 公司声明」做结构化事实核查，输出带信源分级、评级量表与证据链的查证报告。

[![License: MIT](https://img.shields.io/badge/License-MIT-000000.svg)](LICENSE)
[![Core: Bash + Python stdlib](https://img.shields.io/badge/Core-Bash_%2B_Python_stdlib-000000.svg)](#依赖)
[![Channels: 3](https://img.shields.io/badge/Channels-3-0070f3.svg)](#三通道查证)

**[三通道](#三通道查证) · [甄选规则](#甄选规则) · [评级量表](#评级量表) · [快速开始](#快速开始)**

</div>

> [!IMPORTANT]
> 本 skill 只做信息核查：查得到就给证据，查不到就如实标注。**绝不编造、绝不静默降级。**

## 为什么需要它

转发一条消息之前，你能回答三个问题吗：**信源是谁？还有第二源吗？原文在哪？**

大量"官方说法"的原始出处是微信公众号文章，搜索引擎收录差，公开检索只能拿到转载——而各转载版本内容常有出入（实测案例：某 AI 产品销售额环比 +71% 的数据，仅一家权威媒体版本有，其他转载版均无）。本 skill 把"查证"从随口一搜变成可审计的流程。

## 三通道查证

| 通道 | 脚本 | 适用 | 失败时 |
|---|---|---|---|
| **① 腾讯较真** | `jiaozhen_cli.sh` | 中文叙事 / 传闻 / 政策主源 | 标注「⚠️ 较真不可用」，不重试轰炸 |
| **② WebCite** | `webcite_cli.sh` | 国际源补强 / 英文命题 | Key 缺失 exit=2 干净报错；429 标注额度耗尽 |
| **③ 微信公众号** | `weixin_search.sh` | 平台规则 / 官方报告的原文回溯 | 搜狗反爬拦截 → 如实标注「⚠️ 公众号通道未完成」 |

统一入口 `verify.sh` 自动调度：中文 → 较真；英文 → WebCite；中文命题命中「报告 / 政策 / 规则 / 费率」类关键词时自动加挂微信通道回溯原文。

## 甄选规则

内建于查证协议，逐条可审计：

| # | 规则 | 要点 |
|---|---|---|
| 1 | **双源验证** | 每条主张至少 2 个独立来源，否则标"不可靠" |
| 2 | **168 小时窗口** | 事件须落在 `[报告日-6, 报告日]`，过期不纳入 |
| 3 | **原文优先** | 公众号原文 > 权威转载 > 自媒体转述；仅有转载时标注「未回溯原文」 |
| 4 | **版本差异检查** | ≥2 家转载不一致 → 自动触发原文回溯，报告输出「版本差异」提示 |
| 5 | **失败降级** | 单源失败只降级标注，**绝不编造、不静默丢弃** |
| 6 | **误导手法识别** | 统计操纵 / 断章取义 / 错误等价 / 时间穿越，输出前逐条扫描 |

## 评级量表

| 评级 | 含义 |
|---|---|
| ✅ TRUE | ≥2 个独立可靠来源交叉印证 |
| ⚠️ MOSTLY TRUE | 核心事实准确，但缺重要上下文 |
| 🔶 MIXED | 真假参半，或双源直接冲突（同时引用两源，不强行调和） |
| ❌ MOSTLY FALSE / 🚫 FALSE | 误导性强 / 可被明确证伪 |
| ❓ UNVERIFIABLE | 证据既不能确认也不能否定 |

## 快速开始

```bash
git clone https://github.com/marqosjiang-gif/fact-cross-check-skill.git
cd fact-cross-check-skill

# 自动选择通道：中文 → 较真；英文 → WebCite
bash scripts/verify.sh "中美关税协议已正式签署"

# 显式指定通道
bash scripts/verify.sh "The US Fed cut rates by 25bps" --source=webcite
bash scripts/verify.sh "某平台 中秋国庆消费报告 原文" --source=weixin

# 双通道交叉
bash scripts/verify.sh "某平台 商家费率调整" --source=both
```

## 目录结构

```
fact-cross-check-skill/
├── SKILL.md                  # 技能主文档（Agent 加载的入口）
├── test-prompts.json         # 验证用测试命题
├── scripts/
│   ├── verify.sh             # 统一入口（三通道智能调度）
│   ├── jiaozhen_cli.sh       # 腾讯较真通道
│   ├── jiaozhen_cli-state.sh # 较真 CLI 状态检查
│   ├── webcite_cli.sh        # WebCite shell 入口
│   ├── webcite_cli.py        # WebCite 流式客户端（纯标准库）
│   └── weixin_search.sh      # 微信公众号搜索通道
└── references/
    ├── sources_catalog.md    # 全信源清单（含公众号官方号层）
    └── geo_scan_schema.md    # 事件扫描输出约定
```

## 依赖

- Bash / sh、Python 3（webcite 客户端纯标准库，无需 pip）
- `tencent-news-cli`（腾讯较真通道的可选依赖；未安装时该通道降级标注，不阻断）
- WebCite API key（可选；配置方法见 SKILL.md）

## 免责声明

本工具用于**信息核查与研究辅助**，输出为信源结构化结果，不构成任何专业建议。信息请以官方披露为准。

## License

[MIT](LICENSE)
