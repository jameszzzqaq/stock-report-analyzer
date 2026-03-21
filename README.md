# 龟龟投资策略 v0.15

系统化价值型/估值回归型选股分析框架。通过四因子递进筛选执行多阶段分析，用于港股、A股和美股标的的价值判断、穿透回报率评估、现金质量审计和安全边际评估。

---

## 功能特点

- 📊 **多阶段分析**：数据采集 → PDF 解析 → 四因子递进筛选
- 🔍 **四因子框架**：定性分析 → 粗算 → 精算 → 估值
- 📈 **多市场支持**：港股、A股、美股
- 🤖 **自动化数据获取**：使用 yfinance 自动获取市场数据和财务报表
- 📝 **结构化报告输出**：按模板生成完整的投资分析报告

---

## 快速开始

### 前置要求

- Python 3.7+
- yfinance 库

### 安装依赖

```bash
pip install -r scripts/requirements.txt
```

### 使用方法

1. **运行 Phase 1 数据采集**：
```bash
python scripts/fetch_market_data.py <stock_code> --output-dir <output_dir> --channel <channel>
```

示例：
```bash
# 港股（港股通渠道）
python scripts/fetch_market_data.py 0001.HK --output-dir ./0001 --channel 港股通

# A股（长期持有）
python scripts/fetch_market_data.py 600519.SS --output-dir ./600519 --channel 长期持有

# 美股（W-8BEN）
python scripts/fetch_market_data.py AAPL --output-dir ./AAPL --channel W-8BEN
```

> ⚠️ 股票代码格式注意：
> - 港股：**不要加前导0**（如 3613.HK，不是 03613.HK）
> - A股：使用 .SS（上海）或 .SZ（深圳）后缀（如 600519.SS）
> - 美股：直接使用 ticker（如 AAPL）

2. **继续后续分析**：
   - 阅读 `00_coordinator.md` 获取完整调度流程
   - 按照四因子框架依次执行分析

---

## 项目结构

```
stock-report-analyzer/
├── 00_coordinator.md           # 协调器：阶段调度、输入解析
├── 01_phase1_数据采集.md      # Phase 1：数据采集
├── 02_phase2_PDF解析.md       # Phase 2：PDF 年报解析
├── 03_strategy_knowledge_base.md  # 策略知识库
├── 04_factor1_定性分析.md     # 因子1：定性分析
├── 05_factor2_粗算.md         # 因子2：穿透回报率粗算
├── 06_factor3_精算.md         # 因子3：穿透回报率精算
├── 07_factor4_估值.md         # 因子4：估值与安全边际
├── 08_report_template.md      # 报告模板
├── SKILL.md                   # Skills 入口
├── scripts/
│   ├── fetch_market_data.py   # 市场数据获取脚本
│   └── requirements.txt       # Python 依赖
├── examples/
│   └── data_pack_market_sample.md  # 示例数据包
└── agents/
    └── openai.yaml            # 代理配置
```

---

## 四因子分析框架

### 因子1：定性分析
- 因子1A：五分钟快筛（6项检查）
- 因子1B：深度定性分析（9个模块）

### 因子2：穿透回报率粗算（Top-Down）
- 步骤1-8逐步计算
- 步骤3分配能力验证为一票否决项
- 输出粗算穿透回报率 R%

### 因子3：穿透回报率精算（Bottom-Up）+ 现金质量审计
- 步骤1-11逐步执行
- 输出精算穿透回报率 GG%
- 步骤11含外推可信度5维度评级

### 因子4：估值与安全边际
- 门槛比较 → 价值陷阱排查 → 安全边际与仓位 → 股价位置与买入触发价评估

---

## 否决门机制

框架内置多级否决门，以下任一触发即停止后续分析：

1. 因子1A 否决：6 项快筛任一不通过
2. 因子1B 否决：管理层判定"损害价值"
3. 因子2 分配能力否决：自由现金流长期为负
4. 因子2 粗算否决门：R < Rf 或 R < II×0.5
5. 因子4 排除：安全边际不足且价值陷阱风险高

---

## 致谢

本项目改编自 [terancejiang/Stock_Analyze_Prompts](https://github.com/terancejiang/Stock_Analyze_Prompts)，感谢原作者的优秀工作和无私分享！

---

## 许可证

本项目仅供学习和研究使用，不构成任何投资建议。投资有风险，入市需谨慎。

---

*龟龟投资策略 v0.15 | 系统化价值型投资分析框架*
