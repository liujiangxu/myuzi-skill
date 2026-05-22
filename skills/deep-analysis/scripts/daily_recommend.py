#!/usr/bin/env python3
"""Daily top-10 stock recommendation helper.

用法:
    cd skills/deep-analysis/scripts
    python daily_recommend.py
    python daily_recommend.py --universe a --top 10 --pool 80

设计目标：
1. 先用全市场快照做轻量预筛，避免对 5000 只股票逐只跑完整 22 维。
2. 对候选池按质量、估值、动量、流动性、风险惩罚综合排序。
3. 输出每日 10 只优选股票，每只给出可读的推荐理由和风险提示。

注意：这不是投资建议。若用于正式报告，Agent 应对最终 10 只继续调用完整深度分析
（22 维数据 + 51 评委 + 17 种机构方法 + HTML 报告）做二次确认。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    import akshare as ak  # type: ignore
except Exception:  # pragma: no cover - depends on runtime env
    ak = None

from lib.cache import CACHE_ROOT, TTL_DAILY, cached, market_status
from lib.market_router import parse_ticker


@dataclass
class DailyPick:
    rank: int
    code: str
    name: str
    price: float
    change_pct: float
    market_cap_yi: float
    pe_ttm: float
    pb: float
    turnover_pct: float
    score: float
    style: str
    reasons: list[str]
    risks: list[str]


def _num(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        s = str(v).replace("%", "").replace(",", "").replace("亿", "").strip()
        if s in ("", "-", "--", "—", "nan", "None"):
            return default
        x = float(s)
        if math.isnan(x) or math.isinf(x):
            return default
        return x
    except Exception:
        return default


def _first(row: dict, names: tuple[str, ...], default: Any = None) -> Any:
    for n in names:
        if n in row and row[n] not in (None, "", "—", "-"):
            return row[n]
    return default


def _normalize_code(code: str) -> str:
    return parse_ticker(str(code).zfill(6)).full


def _load_a_universe() -> list[dict]:
    if ak is None:
        raise RuntimeError("akshare 未安装，无法拉取 A 股全市场快照。请先 pip install -r requirements.txt")

    def _fetch() -> list[dict]:
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            return []
        return df.to_dict("records")

    return cached("_global", "daily_recommend_a_spot_em", _fetch, ttl=TTL_DAILY)


def _score_row(row: dict) -> tuple[float, list[str], list[str], str] | None:
    code_raw = str(_first(row, ("代码", "code"), "")).strip()
    name = str(_first(row, ("名称", "name"), "")).strip()
    if not code_raw or not name:
        return None
    if name.startswith(("ST", "*ST", "退")) or "ST" in name[:4]:
        return None

    price = _num(_first(row, ("最新价", "最新", "price")))
    change_pct = _num(_first(row, ("涨跌幅", "change_pct")))
    turnover_pct = _num(_first(row, ("换手率", "turnover", "turnover_pct")))
    pe = _num(_first(row, ("市盈率-动态", "市盈率TTM", "市盈率-ttm", "pe_ttm")))
    pb = _num(_first(row, ("市净率", "pb")))
    mcap_yi = _num(_first(row, ("总市值", "market_cap"))) / 1e8
    amount_yi = _num(_first(row, ("成交额", "amount"))) / 1e8

    # 基础可交易过滤：去掉极端小票、无成交、极端高波动日。
    if price <= 0 or mcap_yi < 50 or amount_yi < 1:
        return None
    if change_pct <= -8.5 or change_pct >= 9.8:
        return None

    score = 50.0
    reasons: list[str] = []
    risks: list[str] = []

    # 估值：PE/PB 不追求最低，偏好合理区间。
    if 0 < pe <= 18:
        score += 14
        reasons.append(f"PE {pe:.1f}x 处在偏低区间，估值安全垫较好")
    elif 18 < pe <= 35:
        score += 8
        reasons.append(f"PE {pe:.1f}x 处在可接受区间，未明显透支预期")
    elif pe > 60:
        score -= 14
        risks.append(f"PE {pe:.1f}x 偏高，业绩兑现压力较大")

    if 0 < pb <= 1.5:
        score += 8
        reasons.append(f"PB {pb:.2f}x 偏低，资产端有一定保护")
    elif 1.5 < pb <= 4:
        score += 4
    elif pb > 8:
        score -= 8
        risks.append(f"PB {pb:.2f}x 偏高，若成长放缓估值弹性会收缩")

    # 动量：偏好温和上涨 + 有流动性，不追涨停。
    if 1 <= change_pct <= 5:
        score += 10
        reasons.append(f"当日涨幅 {change_pct:.1f}%，动量确认但未过热")
    elif -2 <= change_pct < 1:
        score += 4
        reasons.append(f"当日涨跌 {change_pct:.1f}%，位置相对平稳，适合继续观察")
    elif change_pct > 6:
        score -= 5
        risks.append(f"当日涨幅 {change_pct:.1f}% 偏高，短线追高风险上升")

    if 1 <= turnover_pct <= 8:
        score += 8
        reasons.append(f"换手率 {turnover_pct:.1f}%，流动性和筹码活跃度较均衡")
    elif turnover_pct > 15:
        score -= 8
        risks.append(f"换手率 {turnover_pct:.1f}% 过高，可能存在短线资金博弈")

    if 100 <= mcap_yi <= 3000:
        score += 6
        reasons.append(f"总市值约 {mcap_yi:.0f} 亿，兼具流动性与弹性")
    elif mcap_yi > 8000:
        score -= 3
        risks.append("超大市值标的弹性通常较弱，需要基本面强催化")

    if amount_yi >= 5:
        score += 4
        reasons.append(f"成交额约 {amount_yi:.1f} 亿，交易承接尚可")

    # 风格判断。
    if 0 < pe <= 18 and 0 < pb <= 2:
        style = "价值低估"
    elif change_pct >= 2 and turnover_pct >= 2:
        style = "动量增强"
    elif mcap_yi >= 1000 and 0 < pe <= 35:
        style = "白马稳健"
    else:
        style = "均衡配置"

    if not risks:
        risks.append("仍需用完整深度分析复核财报、行业、政策和杀猪盘风险")

    return round(max(0, min(100, score)), 1), reasons[:4], risks[:3], style


def build_daily_recommendations(universe: str = "a", top: int = 10, pool: int = 80) -> dict:
    if universe.lower() not in ("a", "ashare", "a-share"):
        raise ValueError("当前每日推荐先支持 A 股全市场。后续可扩展 HK / US。")

    rows = _load_a_universe()
    scored: list[dict] = []
    for row in rows:
        scored_result = _score_row(row)
        if scored_result is None:
            continue
        score, reasons, risks, style = scored_result
        code_raw = str(_first(row, ("代码", "code"), "")).strip()
        try:
            code = _normalize_code(code_raw)
        except Exception:
            continue
        scored.append({
            "code": code,
            "name": str(_first(row, ("名称", "name"), "")).strip(),
            "price": _num(_first(row, ("最新价", "price"))),
            "change_pct": _num(_first(row, ("涨跌幅", "change_pct"))),
            "market_cap_yi": round(_num(_first(row, ("总市值", "market_cap"))) / 1e8, 1),
            "pe_ttm": _num(_first(row, ("市盈率-动态", "市盈率TTM", "市盈率-ttm", "pe_ttm"))),
            "pb": _num(_first(row, ("市净率", "pb"))),
            "turnover_pct": _num(_first(row, ("换手率", "turnover_pct"))),
            "score": score,
            "style": style,
            "reasons": reasons,
            "risks": risks,
        })

    # 分散化：同名/同代码去重，优先高分；保留 pool 便于审计。
    scored.sort(key=lambda x: (x["score"], x["market_cap_yi"]), reverse=True)
    dedup: list[dict] = []
    seen: set[str] = set()
    for item in scored:
        if item["code"] in seen:
            continue
        seen.add(item["code"])
        dedup.append(item)
        if len(dedup) >= max(pool, top):
            break

    picks = [DailyPick(rank=i + 1, **item) for i, item in enumerate(dedup[:top])]
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "market_status": market_status(),
        "universe": "A-share",
        "method": "全市场快照预筛 + 质量/估值/动量/流动性/风险惩罚综合评分；最终 10 只建议继续跑完整深度分析复核",
        "candidate_count": len(scored),
        "pool_size": len(dedup),
        "top": top,
        "recommendations": [asdict(p) for p in picks],
    }
    out_dir = CACHE_ROOT / "_global"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "daily_recommendations.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def render_markdown(payload: dict) -> str:
    lines = []
    lines.append("# 每日推荐 · 10 只优选股票")
    lines.append("")
    lines.append(f"生成时间：{payload.get('generated_at')} · 市场：{payload.get('universe')} · {payload.get('market_status', {}).get('label', '')}")
    lines.append("")
    lines.append("> 说明：这是全市场预筛后的每日优选清单，不构成投资建议。正式买入前应对每只票继续执行完整深度分析。")
    lines.append("")
    lines.append("| 排名 | 股票 | 风格 | 综合分 | 价格 | 涨跌幅 | PE | PB | 推荐理由 | 主要风险 |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---|---|")
    for p in payload.get("recommendations", []):
        reasons = "；".join(p.get("reasons") or [])
        risks = "；".join(p.get("risks") or [])
        lines.append(
            f"| {p['rank']} | {p['name']} ({p['code']}) | {p['style']} | {p['score']:.1f} | "
            f"{p['price']:.2f} | {p['change_pct']:+.1f}% | {p['pe_ttm']:.1f} | {p['pb']:.2f} | {reasons} | {risks} |"
        )
    lines.append("")
    lines.append("下一步建议：对排名前 3 或用户感兴趣的标的说 `完整深度分析 <代码>`，复核 22 维数据、51 评委、17 种机构方法和 HTML 报告。")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="每日推荐 10 只优选股票")
    parser.add_argument("--universe", default="a", help="股票池：a / ashare / a-share（当前先支持 A 股）")
    parser.add_argument("--top", type=int, default=10, help="输出推荐数量，默认 10")
    parser.add_argument("--pool", type=int, default=80, help="保留候选池大小，默认 80")
    parser.add_argument("--json", action="store_true", help="输出 JSON 而不是 Markdown")
    args = parser.parse_args(argv)

    payload = build_daily_recommendations(args.universe, top=args.top, pool=args.pool)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
