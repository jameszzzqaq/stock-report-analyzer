# 龟龟投资策略 v0.15 — 协调器（Coordinator）

> 本文件为多阶段分析的调度中枢。协调器自身不执行数据获取或分析计算，仅负责：
> 解析用户输入 -> 确保年报 PDF -> 调度 Phase 1/2/3 -> 交付最终报告。

***

## 1. 输入解析与变量绑定

从用户消息中提取以下信息，并绑定全局变量：

| 输入项         | 示例                    | 必需？ | 默认值                         |
| ----------- | --------------------- | :-: | --------------------------- |
| 股票代码/Ticker | `0001.HK` / `AAPL`    |  ✅  | 若用户只提供名称，需先确认标准代码           |
| 公司名称        | `长和` / `苹果`           |  -  | 用户明确输入，或由代码推断               |
| 持股渠道        | `港股通` / `直接` / `美股券商` |  -  | 港股->港股通；A股->长期持有；美股->W-8BEN |
| PDF 年报文件    | 用户上传的 `.pdf` 附件       |  -  | 协调器自动下载                     |

**解析后绑定**：

```text
stock_code   = {目标公司的标准计算代码，如 0001.HK, 600519.SS, AAPL}
company_name = {公司中文或常用官方名称}
channel      = {用户指定 | 按上表默认值}
workspace    = {当前工作目录}
strategy_dir = {SKILL.md 所在目录}
symbol       = {stock_code 去掉交易所后缀后的目录名，如 0001, 600519, AAPL}
output_dir   = {workspace}/{stock_code}-{company_name}/
```

***

## 2. 执行流程

### Step 0：确保年报 PDF

```text
current_month = {当前月份}
target_year   = (当前年份 - 2) if current_month <= 3 else (当前年份 - 1)

uploaded_pdf = 检查对话附件或上传目录中的 .pdf 文件

if uploaded_pdf 存在 且 文件名含 target_year:
    pdf_path = uploaded_pdf
elif 自动下载成功:
    pdf_path = 下载的PDF路径
elif uploaded_pdf 存在:
    pdf_path = uploaded_pdf
else:
    pdf_path = null
```

**Auto-download**:

1. If the user does not provide a valid PDF, the coordinator must proactively fetch the annual report instead of skipping directly.
2. For A-share and Hong Kong stocks, prefer using `$stock-report-downloader` skill to fetch the `target_year` annual report and save the PDF into `{output_dir}`.
3. When using `$stock-report-downloader`, reuse its existing CLI or wrapper flow instead of reimplementing the download logic; pass an explicit market hint when needed.
4. If `$stock-report-downloader` is not applicable, fails, or the target is not A-share / Hong Kong, then fall back to plugins, scripts, or WebSearch to find `{company_name} {target_year} annual report PDF`.
5. If fallback also fails, record the reason and set `pdf_path = null`.

### Step 1-3：阶段调度

```text
前置：创建输出目录 {output_dir}
建议使用当前 shell 的等价目录创建命令。
PowerShell 示例：New-Item -ItemType Directory -Force -Path {output_dir}
POSIX shell 示例：mkdir -p {output_dir}

Phase 1（始终执行）
  阅读 {strategy_dir}/01_phase1_数据采集.md 并执行。
  输入：stock_code={stock_code}, channel={channel}
  执行：通过 python 脚本生成骨架 + WebSearch 补充缺失项。
  输出：{output_dir}/data_pack_market.md
  无需下载年报 PDF（已由 Step 0 处理）。
  若无法获取股价/市值 -> 终止全部流程，通知用户检查股票代码。

Phase 2（仅当 pdf_path 有效时执行）
  if pdf_path != null:
      阅读 {strategy_dir}/02_phase2_PDF解析.md 并执行。
      输入：pdf_path={pdf_path}, company_name={company_name}
      输出：{output_dir}/data_pack_report.md
      若 PDF 无法解析 -> 跳过，Phase 3 使用降级方案。

Phase 3（始终执行，按需加载因子模块）
  按以下顺序加载并执行（任一因子否决则停止，输出否决报告）：
    ① 阅读 {strategy_dir}/03_strategy_knowledge_base.md
    ② 阅读 {strategy_dir}/04_factor1_定性分析.md
    ③ 阅读 {strategy_dir}/05_factor2_粗算.md
    ④ 阅读 {strategy_dir}/06_factor3_精算.md
    ⑤ 阅读 {strategy_dir}/07_factor4_估值.md
    ⑥ 阅读 {strategy_dir}/08_report_template.md

  输入：{output_dir}/data_pack_market.md + {output_dir}/data_pack_report.md（若存在）
  输出：{output_dir}/{company_name}_{stock_code}_分析报告.md
  Phase 3 不调用任何外部数据源，所有数据来自数据包文件。
  每完成一个因子 -> 立即将结论追加写入报告文件（checkpoint）。
  若无 data_pack_report.md -> 标注"无年报PDF，降级分析"，模块九（母公司单体）不可用，MD&A 基于 WebSearch 摘要。
```

***

## 3. Phase 3 执行步骤详解

收到用户输入的标的名称/代码后，严格按以下顺序执行：

### Step 1: 读取数据包

1. **读取 `data_pack_market.md`**（必有）：
   - 确认基础信息（股票代码、上市结构、持股渠道、税率、汇率）
   - 确认5年三大报表数据完整性
   - 确认10年历史价格数据可用性
   - 若任何关键数据标注 `⚠️缺失`，记录缺失项清单

2. **读取 `data_pack_report.md`**（可选）：
   - 若文件不存在 → 标注「无年报PDF数据包」，后续使用降级方案
   - 若存在 → 确认母公司单体报表、MD&A原文等关键项是否提取成功

3. **数据完整性评估**：
   - 汇总可用数据和缺失数据
   - 若关键计算数据（净利润、OCF、Capex）缺失 → 终止分析，通知用户

### Step 2: 因子1A — 五分钟快筛
→ 加载 `04_factor1_定性分析.md`

- 逐条判断6项检查
- 任一项否决 → 停止全部后续分析，输出否决报告
- 全部通过 → 输出初步画像，进入Step 3

### Step 3: 因子1B — 深度定性分析
→ 继续使用 `04_factor1_定性分析.md`

- 先执行模块〇（三大报表基础数据），建立数据基础并锚定利润口径
- **模块〇(8)参数预提取为强制步骤**：必须完成因子2/3/4所需全部关键参数的提取和来源标注
- 按模块一至模块八逐一分析
- 若模块六（管理层）触发否决 → 停止
- **模块九（控股折价）触发判断**：若标的为控股公司/投资控股/多元化集团结构 → 执行模块九
- 输出因子1B汇总

### Step 4: 因子2 — 穿透回报率粗算（Top-Down）
→ 加载 `05_factor2_粗算.md`

- 按步骤1-8逐步计算
- 步骤3分配能力验证为一票否决项
- 输出粗算穿透回报率 R%
- **粗算否决门判断**：若 R < Rf 或 R < II×0.5 → 直接否决，不进入因子3
- 若 R 边际不达标（II×0.5 ≤ R < II）→ 标注后继续进入因子3

### Step 5: 因子3 — 穿透回报率精算（Bottom-Up）+ 现金质量审计
→ 加载 `06_factor3_精算.md`

- 按步骤1-11逐步执行
- 输出精算穿透回报率 GG%
- 步骤11含外推可信度5维度评级
- 与因子1交叉验证

### Step 6: 因子4 — 估值与安全边际
→ 加载 `07_factor4_估值.md`

- 门槛比较 → 价值陷阱排查 → 安全边际与仓位 → 股价位置与买入触发价评估
- 步骤4使用 data_pack_market §11/附录A 的10年历史周线数据
- 输出最终判断

### Step 7: 生成报告
→ 加载 `08_report_template.md`

- 严格按照报告模板输出完整Markdown报告
- 不得省略任何章节

***

## 4. Checkpoint 提醒

完成每个因子后，**立即将该因子结论追加写入报告文件**，然后再开始下一因子。这样做的目的是：
- 防止长上下文导致信息丢失
- 允许从中断处恢复
- 让用户可以实时查看分析进度

***

## 5. 异常处理速查

| 异常         | 处理                    |
| :--------- | :-------------------- |
| 无法获取股价/市值  | 终止全部，通知用户检查代码         |
| 财报数据不足5年   | 继续执行，标注实际覆盖年份         |
| 年报下载失败且无上传 | 跳过 Phase 2，Phase 3 降级 |
| PDF 无法解析   | 跳过 Phase 2，Phase 3 降级 |
| 因子触发否决     | 停止后续因子，输出否决报告         |
| 上下文接近上限    | checkpoint 已持久化中间结果   |

***

## 6. 文件路径与只读规则

```text
{workspace}/
├── 龟龟投资策略_v0.15_skills/   <- 只读，严禁写入
└── {symbol}/                     <- 运行时输出目录
    ├── data_pack_market.md
    ├── data_pack_report.md      （可选）
    └── {company_name}_{stock_code}_分析报告.md
```

> 只读规则：策略目录（`{strategy_dir}/`）严禁修改。所有输出写入 `{output_dir}`。

***

## 7. 单位与币种规则（速查）

> 详细换算公式见 `03_strategy_knowledge_base.md` 和各因子模块文件。

| 数据源        | 单位        | 说明                 |
| :--------- | :-------- | :----------------- |
| Phase 1 输出 | {报表币种}百万元 | 以文件头标注为准           |
| Phase 2 输出 | {报表原始单位}  | 千元/百万元/万元，以文件头标注为准 |
| 最终报告       | 人民币亿元     | 换算公式见策略知识库         |

禁止将百万元直接当亿元使用。禁止假设单位，必须读取文件头。

***

*龟龟投资策略 v0.15 | Coordinator | 通用 AI 平台兼容*
