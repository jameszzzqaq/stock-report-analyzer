# 龟龟投资策略-skill

系统化价值型/估值回归型选股分析框架。通过四因子递进筛选执行多阶段分析，用于港股和A股标的的价值判断、穿透回报率评估、现金质量审计和安全边际评估。

---

## 功能特点

- 📊 **多阶段分析**：数据采集 → PDF 解析 → 四因子递进筛选
- 🔍 **四因子框架**：定性分析 → 粗算 → 精算 → 估值
- 📈 **市场支持**：港股、A股
- 🤖 **自动化数据获取**：使用 yfinance 自动获取市场数据和财务报表
- 📝 **结构化报告输出**：按模板生成完整的投资分析报告

## 最小自测

先做脚本语法检查：

```bash
python3 -m py_compile scripts/fetch_market_data.py
```

再各跑一个港股和 A 股样本：

```bash
python3 scripts/fetch_market_data.py 0001.HK --output-dir /tmp/skill-regression-0001 --channel 港股通
python3 scripts/fetch_market_data.py 600519.SS --output-dir /tmp/skill-regression-600519 --channel 长期持有
```

预期结果：
- 两个命令都成功生成 `data_pack_market.md`
- 输出中应包含当前股价、总市值、股息率(TTM)、10年价格区间
- 非港股/A股代码应被脚本直接拒绝

## 致谢

- [terancejiang/Stock_Analyze_Prompts](https://github.com/terancejiang/Stock_Analyze_Prompts)
- [史诗级韭菜](https://space.bilibili.com/322005137)

---

## 许可证

MIT
