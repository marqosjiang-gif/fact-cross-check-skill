# geopolitical_events.json Schema 与校验规则（机制 B）

事件扫描**不能在脚本内直连 WebSearch**（WebSearch 是 Agent 工具）。流程为：Agent 参照维度种子词跑 WebSearch → 把结果写入 `geopolitical_events.json` → 报告加载器读取。

`scripts/geo_scan.py` 负责生成维度提示词（`prompts`）、写骨架（`write-template`）、校验（`validate`）。

## 维度种子词库（8 维，内嵌于 geo_scan.py）

| 维度 | 种子关键词（示例） |
|---|---|
| 俄乌冲突 | 俄乌冲突最新进展 / 俄乌停火谈判 / 乌克兰 总统选举 |
| 中日关系 | 中日关系最新动态 / 中日 半导体限制 / 日本 台湾问题 |
| 台海局势 | 台海局势 最新 / 台湾问题 国防白皮书 |
| 中东/霍尔木兹 | 霍尔木兹海峡 通航 / 美伊关系 停火 / 伊朗 核问题 |
| 中美贸易/制裁 | 中美贸易关系 关税 制裁 / 美国 撤销 中国 PNTR |
| 朝鲜半岛局势 | 朝鲜半岛 局势 最新 / 朝鲜 导弹 韩国 军演 |
| 南海争端 | 南海争端 最新 / 中国 菲律宾 南海 |
| 欧盟对华政策 | 欧盟 对华政策 最新 / 欧盟 对华关税 制裁 |

> V10.2 起废除"固定 8 维度强制扫描"，改为**动态事件驱动**：围绕过去 168 小时实际发生的事件做事件驱动检索，不限于种子维度；每条事件须显式给出相关性影响度评分。

## OUTPUT_SCHEMA

```json
{
  "metadata": {
    "scan_time": "ISO 8601 时间戳",
    "window_start": "YYYY-MM-DD",
    "window_end": "YYYY-MM-DD",
    "data_source": "WebSearch (agent执行)",
    "scan_method": "动态事件驱动扫描说明",
    "selection_rule": "按影响度评分降序取Top N",
    "scoring_formula": "主题关联度0-40 + 可核验锚点0-30 + 事件烈度0-20 + 验证等级0-10",
    "verification": "每条事件至少2个独立来源",
    "glossary": {"英文缩写": "中文注释"}
  },
  "events": [
    {
      "name": "事件标题",
      "dimension": "维度名",
      "event_date": "YYYY-MM-DD",
      "hard_fact": "可核验的硬事实描述",
      "impact_score": 85,
      "sources": ["来源A", "来源B"],
      "truth_level": "✅印证 / 🔴存疑 / ⚪无覆盖 / ⚠️盲区",
      "third_source_label": "由 jiaozhen 填入"
    }
  ]
}
```

## 加载器校验规则（报告 `_load_geopolitical_events_json`）

必须满足，否则只返回"⚠️ 事件扫描未完成"标记：

1. **window_end ≥ 报告日**：`scan_window_end < report_end` → 拒收（已固化为 `geo-scan-pre-report-gate` 规则）。
2. **逐事件 168h 窗口**：`event_date` 须在 `[报告日-6, 报告日]`。
3. **双源验证**：每条事件 `len(sources) >= 2`。
4. **影响度评分**：按评分降序取 Top N（默认 5）。

`geo_scan.py validate --path X --report-date Y` 会在合并前检查上述 1–3 项并输出告警，便于 Agent 提前修。

## 第三源核查（jiaozhen）

对进入事实表的事件（非盲区 / 非纯转述推断），调用较真 CLI 做交叉核实：
```bash
sh $SKILL/scripts/jiaozhen_cli.sh --query "<claim>"
```
标签：🔴存疑 / ✅印证 / ⚪无覆盖 / ⚠️未完成超时。**不阻断报告**。
