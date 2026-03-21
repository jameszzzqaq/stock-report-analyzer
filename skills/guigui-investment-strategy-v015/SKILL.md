---
name: guigui-investment-strategy-v015
description: 将“龟龟投资策略 v0.15”原始 Claude Code 多阶段 workflow 封装为可复用 skill，严格沿用 coordinator 与 phase1/2/3 的原始规则、阶段顺序、否决门、输入输出文件名和报告结构。用于按该策略分析个股、处理上传年报 PDF、生成标准 data_pack_market.md、data_pack_report.md 与最终分析报告，或在用户提供新信息后按原框架重评。
---

# 龟龟投资策略 v0.15

将本 skill 视为原始 workflow 的入口层。以 `references/strategy-v0.15/` 下的四份原始文档为唯一规则来源；本文件只负责触发、导航和不变约束，不重写策略。

## 只读约束

- 将 `references/strategy-v0.15/` 视为只读规则目录。
- 不修改原始策略内容，不改写 prompt，不重排阶段顺序，不增删否决门。
- 不改变原始输入项、输出文件名、输出结构、报告模板、单位换算规则或异常处理分支。
- 若本文件与原始文档存在任何歧义或冲突，以原始文档为准。

## 读取顺序

1. 先读 `references/strategy-v0.15/coordinator.md`。
2. 执行 Phase 1 前，读 `references/strategy-v0.15/phase1_数据采集.md`。
3. 执行 Phase 2 前，读 `references/strategy-v0.15/phase2_PDF解析.md`。
4. 执行 Phase 3 前，读 `references/strategy-v0.15/phase3_分析与报告.md`。

不要一次性把全部文档灌入上下文；按阶段读取，保持上下文精简，但执行规则必须与原文一致。

## 执行流程

### 1. 解析输入

按 `coordinator.md` 的“输入解析”执行，只接受并解析以下输入组合：

- 股票代码或名称
- 持股渠道
- 用户上传的 PDF 年报

若用户只给公司名称，不提前臆测代码；按原 workflow 在 Phase 1 中通过检索确认。

### 2. 创建输出目录

在启动任何阶段前，先创建 `{workspace}/{symbol}/`。

所有运行产物都写入该目录；不要向 skill 目录或原始策略目录写运行时结果。

### 3. 执行 PDF 年报确保步骤

严格按 `coordinator.md` 的 Step 0 执行：

- 根据当前月份确定 `target_year`
- 优先校验用户上传 PDF 是否为最新完整财年年报
- 如无有效 PDF，则按原规则触发年报下载
- 下载失败时保留降级路径，不要发明新分支

### 4. 调度阶段

优先按原 coordinator 复现阶段边界：

- `Phase 1` 输出 `data_pack_market.md`
- `Phase 2` 输出 `data_pack_report.md`
- `Phase 3` 读取前两者并输出最终分析报告

若当前环境支持 sub-agent 或并行任务，保持原设计：Phase 1 与 Phase 2 并行，全部完成后再启动 Phase 3。

若当前环境不支持并行或 sub-agent，则只允许按相同依赖关系串行模拟，不得合并阶段职责，不得改变各阶段各自的输入输出契约。

## 各阶段硬约束

### Phase 1

- 严格按 `phase1_数据采集.md` 采集。
- 只做数据采集与整理，不做分析、估值或投资结论。
- 输出文件必须是 `data_pack_market.md`，结构、字段名、单位说明保持原样。

### Phase 2

- 严格按 `phase2_PDF解析.md` 提取。
- 只提取年报原始数据与文本，不做投资分析或估值判断。
- 输出文件必须是 `data_pack_report.md`，P1-P19 结构和原文引用要求保持原样。

### Phase 3

- 严格按 `phase3_分析与报告.md` 的 `SYSTEM INSTRUCTIONS`、`strategy_knowledge_base`、`execution_workflow` 和 `report_template` 执行。
- 除读取数据包外，不调用外部数据源。
- 严格执行 veto gate、checkpoint、单位换算、币种换算和降级方案。
- 不省略任何报告章节，不跳过公式展示。

## 输入输出契约

保持以下文件契约不变：

- `{workspace}/{symbol}/data_pack_market.md`
- `{workspace}/{symbol}/data_pack_report.md`
- `{workspace}/{symbol}/{company}_{code}_分析报告.md`

若原始文档对文件命名、路径变量或字段格式有更细规则，直接遵循原文，不在此处另造别名。

## 重新评估规则

报告生成后，不接受没有新信息支撑的结论改写请求。

仅当用户提供以下内容时，才按 `phase3_分析与报告.md` 的原规则重评：

- 新数据
- 数据纠错
- 原分析遗漏
- 持股渠道变化导致的税率变化

重评时只重跑受影响的阶段或因子，并保留原框架的修订说明格式。