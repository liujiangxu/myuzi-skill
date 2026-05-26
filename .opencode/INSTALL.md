# UZI-Skill · OpenCode 安装指南

## 安装

```bash
git clone https://github.com/wbh604/UZI-Skill.git
cd UZI-Skill
pip install -r requirements.txt
```

## 使用

对 OpenCode / OpenClaw 说：

> 分析 贵州茅台

或直接执行：

```bash
python run.py 贵州茅台 --no-browser
```

## 自然语言路由

OpenCode / OpenClaw 中推荐直接说自然语言。股票名或代码可以放在动作前，也可以放在动作后。

| 自然语言 | 等价命令 | 用途 |
|---|---|---|
| `贵州茅台 完整分析` / `完整分析 贵州茅台` | `/stock-deep-analyzer:analyze-stock 贵州茅台`；CLI fallback: `python run.py 贵州茅台 --depth deep --no-browser` | 最高档 deep，完整 22 维 × 51 评委分析，并返回完整 HTML 报告 |
| `002217 快速扫描` / `快速扫描 002217` | `/stock-deep-analyzer:quick-scan 002217` | 30 秒速判 |
| `002217 杀猪盘排查` / `杀猪盘排查 002217` | `/stock-deep-analyzer:scan-trap 002217` | 杀猪盘排查 |
| `600519 DCF估值` / `DCF估值 600519` | `/stock-deep-analyzer:dcf 600519` | DCF 估值专项 |

若自然语言无法被平台路由，直接使用上表里的 `/stock-deep-analyzer:<cmd>` 全名命令；其中“完整分析”必须使用最高档 deep，CLI fallback 为 `python run.py <股票> --depth deep --no-browser`，并在完成后返回完整 HTML 报告路径。若股票名无法唯一解析，先让用户确认具体股票代码。

## 两段式深度分析

```bash
cd skills/deep-analysis/scripts

# Stage 1: 数据采集 + 骨架分
python -c "from run_real_test import stage1; stage1('600519.SH')"

# Agent 分析（读 .cache/600519.SH/panel.json，逐组分析 51 评委）

# Stage 2: 生成报告
python -c "from run_real_test import stage2; stage2('600519.SH')"
```

## 远程查看

```bash
python run.py 贵州茅台 --remote
```

## 更多信息

- `AGENTS.md` — Agent 指令
- `skills/deep-analysis/SKILL.md` — 完整分析师手册
- `README.md` — 项目介绍
