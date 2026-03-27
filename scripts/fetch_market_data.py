#!/usr/bin/env python3
"""
龟龟投资策略 v0.15 — 市场数据采集脚本

使用 yfinance 获取股票市场数据，输出为 data_pack_market.md 的结构化数据部分（§1-§6, §11）。
AI 负责补充 WebSearch 部分（§7-§10 管理层/行业/子公司/MD&A）。

⚠️ 注意：股票代码格式
  - 港股：使用 Yahoo Finance 标准代码（通常保留交易所要求的补零位数，如 0001.HK）
  - A股：使用 .SS（上海）或 .SZ（深圳）后缀（如 600519.SS）

用法：
    python fetch_market_data.py <stock_code> [--output-dir <dir>] [--channel <channel>]

示例：
    python fetch_market_data.py 0001.HK --output-dir ./0001 --channel 港股通
    python fetch_market_data.py 3613.HK
    python fetch_market_data.py 600519.SS --channel 长期持有
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance 未安装。请运行: pip install yfinance>=0.2.36", file=sys.stderr)
    sys.exit(1)


# ─────────────────────────────────────────────
# 税率表
# ─────────────────────────────────────────────
TAX_TABLE = {
    ("H股", "直接持有"): (28, 72),
    ("H股", "港股通"): (20, 80),
    ("红筹", "直接持有"): (20, 80),
    ("红筹", "港股通"): (20, 80),
    ("开曼", "直接持有"): (20, 80),
    ("开曼", "港股通"): (20, 80),
    ("A股", "长期持有"): (0, 100),
    ("A股", "持有1月-1年"): (10, 90),
    ("A股", "持有不足1月"): (20, 80),
}

DEFAULT_CHANNELS = {
    "HK": "港股通",
    "SS": "长期持有",
    "SZ": "长期持有",
}


def get_exchange_suffix(code: str) -> str:
    """Extract exchange suffix from stock code."""
    if "." in code:
        return code.split(".")[-1]
    return ""


def get_default_channel(code: str) -> str:
    suffix = get_exchange_suffix(code)
    return DEFAULT_CHANNELS.get(suffix, "直接持有")


def validate_supported_code(code: str) -> None:
    """Reject unsupported markets early so the skill scope matches real capability."""
    suffix = get_exchange_suffix(code).upper()
    if suffix not in {"HK", "SS", "SZ"}:
        print(
            "ERROR: 当前脚本仅支持港股和A股代码。港股请使用 .HK，A股请使用 .SS 或 .SZ 后缀。",
            file=sys.stderr,
        )
        sys.exit(2)


def safe_get(data, key, default="⚠️缺失"):
    """Safely get a value from a dict/series, return default if missing or NaN."""
    try:
        val = data[key]
        if val is None:
            return default
        import math
        if isinstance(val, float) and math.isnan(val):
            return default
        return val
    except (KeyError, IndexError, TypeError):
        return default


def fmt_num(val, abs_val=False):
    """Format a number for Markdown table. Returns '⚠️缺失' for missing values."""
    if isinstance(val, str):
        return val
    try:
        import math
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return "⚠️缺失"
        v = abs(val) if abs_val else val
        # Convert to millions (yfinance returns raw values)
        v_millions = v / 1_000_000
        return f"{v_millions:,.2f}"
    except (TypeError, ValueError):
        return "⚠️缺失"


def fmt_num_raw(val):
    """Format number without million conversion (for per-share data etc.)."""
    if isinstance(val, str):
        return val
    try:
        import math
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return "⚠️缺失"
        return f"{val:,.4f}" if abs(val) < 1 else f"{val:,.2f}"
    except (TypeError, ValueError):
        return "⚠️缺失"


def fmt_percent(val):
    """Format a percentage, tolerating providers that return either 0.038 or 3.8."""
    if isinstance(val, str):
        return val
    try:
        import math
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return "⚠️缺失"
        pct = val * 100 if abs(val) <= 1 else val
        return f"{pct:.2f}%"
    except (TypeError, ValueError):
        return "⚠️缺失"


def fetch_data(code: str, channel: str, output_dir: str):
    """Main data fetching and markdown generation."""
    
    print(f"📡 正在获取 {code} 的数据...", file=sys.stderr)
    ticker = yf.Ticker(code)
    
    # ── Basic info ──
    print("  → 基础信息...", file=sys.stderr)
    info = ticker.info
    if not info or info.get("regularMarketPrice") is None:
        print(f"⛔ 无法获取 {code} 的市场数据，请检查股票代码。", file=sys.stderr)
        sys.exit(1)
    
    company_name = info.get("longName") or info.get("shortName") or code
    currency = info.get("financialCurrency") or info.get("currency") or "N/A"
    exchange = info.get("exchange", "N/A")
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    market_cap = info.get("marketCap")
    shares_outstanding = info.get("sharesOutstanding")
    dividend_yield = info.get("dividendYield")
    fifty_two_high = info.get("fiftyTwoWeekHigh")
    fifty_two_low = info.get("fiftyTwoWeekLow")
    industry = info.get("industry") or info.get("sector") or "N/A"
    price_currency = info.get("currency") or currency
    
    symbol = code.split(".")[0] if "." in code else code
    
    # ── Financial statements (annual, 5 years) ──
    print("  → 财务报表...", file=sys.stderr)
    income_stmt = ticker.financials  # Annual income statement
    balance_sheet = ticker.balance_sheet  # Annual balance sheet
    cashflow = ticker.cashflow  # Annual cash flow
    
    # ── Dividends ──
    print("  → 股息记录...", file=sys.stderr)
    dividends = ticker.dividends
    
    # ── Historical prices (10y weekly) ──
    print("  → 10年历史价格...", file=sys.stderr)
    hist = ticker.history(period="10y", interval="1wk")
    
    now = datetime.now()
    
    # ─────────────────────────────────────────
    # Generate Markdown
    # ─────────────────────────────────────────
    lines = []
    
    def w(line=""):
        lines.append(line)
    
    w(f"# 数据包：{company_name}（{code}）")
    w()
    w(f"> 采集时间：{now.strftime('%Y-%m-%d %H:%M')}")
    w(f"> 采集工具：yfinance 脚本（fetch_market_data.py）+ WebSearch")
    w(f"> 数据完整性：{{待AI补充WebSearch部分后确认}}")
    w()
    w("---")
    w()
    
    # ── §1. 基础信息 ──
    w("## §1. 基础信息")
    w()
    w("| 项目 | 数值 |")
    w("|:-----|:-----|")
    w(f"| 股票代码 | {code} |")
    w(f"| 公司名称 | {company_name} |")
    w(f"| 上市地 | {exchange} |")
    w(f"| 上市结构 | {{待WebSearch确认：H股/红筹/开曼/A股}} |")
    w(f"| 持股渠道 | {channel} |")
    w(f"| 适用股息税率 Q | {{待确认上市结构后填写}}% |")
    w(f"| 报表币种 | {currency} |")
    w(f"| 价格币种 | {price_currency} |")
    w(f"| 汇率（若需换算） | {{待WebSearch确认}} |")
    w(f"| 行业分类 | {industry} |")
    w(f"| 是否控股公司 | {{待WebSearch确认}} |")
    w()
    w("---")
    w()
    
    # ── §2. 市场数据 ──
    w("## §2. 市场数据")
    w()
    w("| 项目 | 数值 |")
    w("|:-----|:-----|")
    w(f"| 当前股价 | {fmt_num_raw(current_price)} {price_currency}（截至 {now.strftime('%Y-%m-%d')}） |")
    if market_cap:
        mc_yi = market_cap / 100_000_000
        w(f"| 总市值 | {mc_yi:,.2f} 亿{price_currency}（{market_cap / 1_000_000:,.2f} 百万{price_currency}） |")
    else:
        w("| 总市值 | ⚠️缺失 |")
    if shares_outstanding:
        w(f"| 总股本 | {shares_outstanding:,.0f} 股 |")
    else:
        w("| 总股本 | ⚠️缺失 |")
    if dividend_yield is not None:
        w(f"| 股息率(TTM) | {fmt_percent(dividend_yield)} |")
    else:
        w("| 股息率(TTM) | ⚠️缺失 |")
    w(f"| 52周高/低 | {fmt_num_raw(fifty_two_high)} / {fmt_num_raw(fifty_two_low)} |")
    w(f"| Rf（十年期国债） | {{待WebSearch获取}} |")
    w()
    w("---")
    w()
    
    # ── §3-§5. Financial Statements ──
    def get_field_value(df, aliases, col):
        """Return the first matching row value for a logical field."""
        alias_list = aliases if isinstance(aliases, (list, tuple)) else [aliases]
        for alias in alias_list:
            try:
                return df.loc[alias, col]
            except (KeyError, TypeError):
                continue
        return None

    def write_financial_table(title, section_num, df, fields, abs_fields=None):
        """Write a financial statement table."""
        abs_fields = abs_fields or set()
        w(f"## §{section_num}. {title}")
        w()
        
        if df is None or df.empty:
            w(f"> ⚠️ 无法获取{title}数据")
            w()
            return
        
        # Get years (columns are dates, most recent first in yfinance)
        years = []
        for col in df.columns:
            try:
                yr = col.strftime("%Y") if hasattr(col, "strftime") else str(col)[:4]
                years.append((col, yr))
            except:
                years.append((col, str(col)))
        
        # Reverse to show old→new
        years = list(reversed(years))
        
        year_headers = " | ".join(yr for _, yr in years)
        w(f"| 科目（单位：{currency}百万） | {year_headers} |")
        w("|:-----|" + "------:|" * len(years))
        
        for field_aliases, field_cn in fields:
            alias_list = field_aliases if isinstance(field_aliases, (list, tuple)) else [field_aliases]
            vals = []
            for col, _ in years:
                val = get_field_value(df, alias_list, col)
                use_abs = any(alias in abs_fields for alias in alias_list)
                vals.append(fmt_num(val, abs_val=use_abs))
            
            val_str = " | ".join(vals)
            w(f"| {field_cn} | {val_str} |")
        
        w()
        w(f"> **说明：** 所有金额单位为{currency}百万元。yfinance 原始输出为{currency}元，已除以 1,000,000 换算为百万。")
        w()
        w("---")
        w()
    
    # Income Statement fields
    income_fields = [
        (("Total Revenue", "Operating Revenue"), "营业收入"),
        ("Cost Of Revenue", "营业成本"),
        ("Gross Profit", "毛利润"),
        (("Research Development", "Research And Development"), "研发费用"),
        (("Selling General Administrative", "Selling General And Administration"), "销售及管理费用"),
        ("Operating Income", "经营利润"),
        (("Other Income Expense Net", "Other Non Operating Income Expenses"), "其他收入/支出净额"),
        (("Income Before Tax", "Pretax Income"), "税前利润"),
        (("Income Tax Expense", "Tax Provision"), "所得税"),
        ("Net Income", "集团净利润"),
        (("Net Income Applicable To Common Shares", "Net Income Common Stockholders", "Diluted NI Availto Com Stockholders"), "归母净利润"),
        (("Minority Interest", "Minority Interests"), "少数股东损益"),
        (("Depreciation", "Reconciled Depreciation", "Depreciation And Amortization In Income Statement"), "折旧摊销"),
        ("Stock Based Compensation", "SBC（股权激励）"),
    ]
    
    write_financial_table("五年损益表", 3, income_stmt, income_fields)
    
    # Balance Sheet fields
    bs_fields = [
        (("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"), "现金及等价物"),
        (("Short Term Investments", "Other Short Term Investments", "Available For Sale Securities", "Held To Maturity Securities"), "短期投资"),
        (("Net Receivables", "Receivables", "Accounts Receivable", "Gross Accounts Receivable"), "应收账款净额"),
        ("Inventory", "存货"),
        (("Other Current Assets", "Prepaid Assets"), "其他流动资产"),
        (("Total Current Assets", "Current Assets"), "流动资产合计"),
        (("Long Term Investments", "Long Term Equity Investment", "Investmentsin Joint Venturesat Cost", "Investmentsin Associatesat Cost"), "长期投资"),
        (("Property Plant Equipment", "Net PPE"), "固定资产净额"),
        ("Goodwill", "商誉"),
        (("Intangible Assets", "Other Intangible Assets"), "无形资产"),
        ("Total Assets", "总资产"),
        (("Short Long Term Debt", "Current Debt", "Current Debt And Capital Lease Obligation"), "短期有息负债"),
        (("Long Term Debt", "Long Term Debt And Capital Lease Obligation"), "长期有息负债"),
        ("Accounts Payable", "应付账款"),
        (("Deferred Revenue", "Current Deferred Revenue", "Non Current Deferred Revenue"), "递延收入/合同负债 ⭐"),
        (("Total Current Liabilities", "Current Liabilities"), "流动负债合计"),
        (("Total Liab", "Total Liabilities Net Minority Interest"), "总负债"),
        (("Total Stockholder Equity", "Stockholders Equity", "Common Stock Equity"), "股东权益"),
        (("Minority Interest", "Minority Interests"), "少数股东权益"),
    ]
    
    write_financial_table("五年资产负债表", 4, balance_sheet, bs_fields)
    
    # Cash Flow fields
    cf_fields = [
        (("Total Cash From Operating Activities", "Operating Cash Flow"), "经营活动现金流"),
        (("Capital Expenditures", "Capital Expenditure", "Purchase Of PPE"), "资本支出"),
        (("Total Cash From Investing Activities", "Investing Cash Flow"), "投资活动现金流"),
        (("Total Cash From Financing Activities", "Financing Cash Flow"), "融资活动现金流"),
        (("Dividends Paid", "Cash Dividends Paid", "Common Stock Dividend Paid"), "股息支付"),
        (("Repurchase Of Stock", "Repurchase Of Capital Stock"), "股份回购"),
        (("Depreciation", "Depreciation And Amortization"), "折旧摊销"),
        ("Change In Receivables", "应收账款变动"),
        (("Change In Payables", "Change In Payable", "Change In Payables And Accrued Expense"), "应付账款变动"),
        ("Change In Inventory", "存货变动"),
    ]
    
    cf_abs_fields = {"Capital Expenditures", "Capital Expenditure", 
                     "Purchase Of PPE", "Dividends Paid", "Cash Dividends Paid", "Common Stock Dividend Paid",
                     "Repurchase Of Stock", "Repurchase Of Capital Stock"}
    
    write_financial_table("五年现金流量表", 5, cashflow, cf_fields, abs_fields=cf_abs_fields)
    
    # ── §6. 股息历史 ──
    w("## §6. 股息历史")
    w()
    if dividends is not None and len(dividends) > 0:
        w("| 除净日 | 每股股息(DPS) | 币种 | 类型 |")
        w("|:-------|------------:|:-----|:-----|")
        for date, dps in dividends.items():
            date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)[:10]
            w(f"| {date_str} | {dps:.4f} | {price_currency} | {{待AI补充}} |")
    else:
        w("> ⚠️ 未获取到股息记录")
    w()
    
    # Buyback from cash flow
    w("回购记录（取自§5现金流量表 Repurchase of Stock）：")
    w()
    if cashflow is not None and not cashflow.empty:
        w("| 年份 | 回购金额（百万） | 来源 |")
        w("|:-----|----------------:|:-----|")
        buyback_keys = ["Repurchase Of Stock", "Repurchase Of Capital Stock"]
        for col in reversed(list(cashflow.columns)):
            yr = col.strftime("%Y") if hasattr(col, "strftime") else str(col)[:4]
            val = None
            for bk in buyback_keys:
                try:
                    val = cashflow.loc[bk, col]
                    break
                except KeyError:
                    continue
            w(f"| {yr} | {fmt_num(val, abs_val=True)} | yfinance |")
    w()
    w("> ⚠️ **禁止**直接使用 yfinance info 的 `payoutRatio` 字段（跨币种换算失真）。")
    w("> 支付率由 Phase 3 根据年报同币种数据计算。")
    w()
    w("---")
    w()
    
    # ── §7-§10 placeholders ──
    for section, title, desc in [
        ("§7", "管理层与治理", "WebSearch 采集"),
        ("§8", "行业与竞争", "WebSearch 采集"),
        ("§9", "子公司数据（控股公司适用）", "WebSearch + yfinance 采集"),
        ("§10", "MD&A 摘要", "WebSearch 采集"),
    ]:
        w(f"## {section}. {title}")
        w()
        w(f"> 📍 本节需 AI 通过 {desc} 补充，脚本不处理此部分。")
        w(f"> 请参照 `01_phase1_数据采集.md` 中 {section} 的指引完成。")
        w()
        w("---")
        w()
    
    # ── §11. 10年历史价格 ──
    w("## §11. 10年历史价格")
    w()
    if hist is not None and len(hist) > 0:
        closes = hist["Close"]
        w("| 项目 | 数值 |")
        w("|:-----|:-----|")
        w(f"| 数据覆盖区间 | {closes.index[0].strftime('%Y-%m-%d')} — {closes.index[-1].strftime('%Y-%m-%d')} |")
        w(f"| 数据点数量 | {len(closes)} |")
        min_idx = closes.idxmin()
        max_idx = closes.idxmax()
        w(f"| 10年最低价 | {closes[min_idx]:.2f}（{min_idx.strftime('%Y-%m-%d')}） |")
        w(f"| 10年最高价 | {closes[max_idx]:.2f}（{max_idx.strftime('%Y-%m-%d')}） |")
        w()
        
        # Annual summary
        w("年度摘要：")
        w()
        w("| 年份 | 最低 | 最高 | 年末收盘 |")
        w("|:-----|-----:|-----:|--------:|")
        
        for year in sorted(closes.index.year.unique()):
            year_data = closes[closes.index.year == year]
            if len(year_data) == 0:
                continue
            w(f"| {year} | {year_data.min():.2f} | {year_data.max():.2f} | {year_data.iloc[-1]:.2f} |")
        w()
        w("---")
        w()
        
        # Full weekly data as appendix
        w("## 附录A：10年周线收盘价完整数据")
        w()
        w("| 日期 | 收盘价 |")
        w("|:-----|------:|")
        for date, price in closes.items():
            w(f"| {date.strftime('%Y-%m-%d')} | {price:.2f} |")
    else:
        w("> ⚠️ 未获取到历史价格数据")
    
    w()
    w("---")
    w()
    w(f"*数据由 fetch_market_data.py 自动生成 | yfinance | {now.strftime('%Y-%m-%d %H:%M')}*")
    
    # ─────────────────────────────────────────
    # Write output
    # ─────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "data_pack_market.md")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"✅ 数据包已写入：{output_path}", file=sys.stderr)
    print(f"   §1-§6, §11: 已完成（yfinance）", file=sys.stderr)
    print(f"   §7-§10: 需 AI 通过 WebSearch 补充", file=sys.stderr)
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="龟龟投资策略 v0.15 — 市场数据采集脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
    python fetch_market_data.py 0001.HK
    python fetch_market_data.py 6049.HK --output-dir ./06049 --channel 港股通
    python fetch_market_data.py 600519.SS --channel 长期持有
        """
    )
    parser.add_argument("stock_code", help="股票代码，如 0001.HK, 6049.HK, 600519.SS")
    parser.add_argument("--output-dir", "-o", default=None,
                        help="输出目录（默认：./{symbol}/）")
    parser.add_argument("--channel", "-c", default=None,
                        help="持股渠道（默认按上市地自动判断）")
    
    args = parser.parse_args()
    
    code = args.stock_code
    validate_supported_code(code)
    
    symbol = code.split(".")[0] if "." in code else code
    output_dir = args.output_dir or f"./{symbol}/"
    channel = args.channel or get_default_channel(code)
    
    fetch_data(code, channel, output_dir)


if __name__ == "__main__":
    main()
