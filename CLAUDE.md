# UZI-Skill · Claude Code Context

> 本文件供 Claude Code 自动读取，提供项目上下文。

## 这是什么

一个股票深度分析 plugin。用户说"分析 XXX"时，你应该自动触发 `deep-analysis` skill。

## 核心技能

| Skill | 触发条件 | 说明 |
|---|---|---|
| `deep-analysis` | 用户提到"分析/研究/估值/DCF/值不值得买"等 | 22维数据 + 51评委 + Bloomberg报告 |
| `investor-panel` | 用户要求"只看评委/大佬怎么看" | 单独跑投资者面板 |
| `lhb-analyzer` | 用户提到"龙虎榜/游资/营业部" | 龙虎榜专项分析 |
| `trap-detector` | 用户提到"杀猪盘/有没有问题/安全吗" | 杀猪盘检测 |

## 自然语言等价命令

用户可以把股票名或代码放在动作前，也可以放在动作后。以下说法应按等价命令处理：

| 用户自然语言 | 等价命令 |
|---|---|
| `<股票> 完整分析` / `完整分析 <股票>` / `深度分析 <股票>` | `/stock-deep-analyzer:analyze-stock <股票>`；按最高档 deep 执行，CLI fallback: `python run.py <股票> --depth deep --no-browser`，完成后返回完整 HTML 报告路径 |
| `<股票> 快速扫描` / `快速扫描 <股票>` / `速判 <股票>` | `/stock-deep-analyzer:quick-scan <股票>` |
| `<股票> 杀猪盘排查` / `杀猪盘排查 <股票>` / `<股票> 安全吗` | `/stock-deep-analyzer:scan-trap <股票>` |
| `<股票> DCF估值` / `DCF估值 <股票>` / `<股票> 值多少钱` | `/stock-deep-analyzer:dcf <股票>` |

如果股票名无法唯一解析为上市主体，先要求用户确认具体股票代码，不要自行猜测。

## 工作流 · 深浅两档（v2.10.6）

**快速路径（默认）**：用户说"分析/看看"时，优先走 CLI 直跑。
```
python3 run.py <ticker> --depth lite --no-browser   # 30-60s
# 或
python3 run.py <ticker> --depth medium --no-browser # 2-4min，默认完整度
```
v2.10.4 起 CLI 直跑 `agent_analysis.json` 缺失自动降级 warning，照样出 HTML 报告。**不需要 role-play 51 评委**。

**深度路径**：当用户明确要“完整分析”/ 深度分析 / DCF / IC memo / 首次覆盖 / 投委会备忘录等深度产物时走最高档 deep 或两段式：
1. `stage1()` — 脚本采集数据 + 规则引擎骨架分
2. **你介入** — 读 `panel.json`，role-play 51 评委，写 `agent_analysis.json`
3. `stage2()` — 自动合并你的分析，生成报告

详细流程见 `AGENTS.md` / `skills/deep-analysis/SKILL.md`。

## 重要文件

- `AGENTS.md` — 完整 agent 指令
- `skills/deep-analysis/SKILL.md` — 深度分析工作流
- `skills/deep-analysis/scripts/run_real_test.py` — 主引擎
- `commands/analyze-stock.md` — `/analyze-stock` 命令
