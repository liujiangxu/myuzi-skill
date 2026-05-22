# UZI-Skill · OpenCode 安装指南

## 安装

```bash
git clone https://github.com/wbh604/UZI-Skill.git
cd UZI-Skill
pip install -r requirements.txt
```

## 使用

对 OpenCode 说（推荐自然语言，不需要 `/stock-deep-analyzer:analyze-stock` 格式）：

> 完整深度分析 贵州茅台

或：

> 每日推荐

完整深度分析会同时交付 22 维数据、51 位评委投票、17 种机构方法核心输出和 HTML 报告路径。
每日推荐会给出当天 10 只优选股票，并为每只股票提供简要推荐理由和主要风险。

或直接执行：

```bash
python run.py 贵州茅台 --no-browser
```

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
