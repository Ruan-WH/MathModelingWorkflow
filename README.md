# MathModelingWorkflow

> 面向数学建模竞赛的可复现工作流：从问题拆解、模型建立和数值求解，到科研绘图、DrawIO 流程图、LaTeX 写作与最终验收。

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![LaTeX](https://img.shields.io/badge/LaTeX-XeLaTeX-008080?logo=latex&logoColor=white)
![Status](https://img.shields.io/badge/进度-问题二待审查-f0ad4e)
![License](https://img.shields.io/badge/用途-学习与研究-blue)

[查看当前论文](paper/main.pdf) · [查看数值结果](reports/RESULTS_REPORT.md) · [查看验收报告](reports/VERIFY_REPORT.md) · [查看任务进度](todo.md)

## 项目简介

本仓库以 2025 年高教社杯全国大学生数学建模竞赛 A 题“烟幕干扰弹的投放策略”为实例，构建了一套可审计、可复现、可逐题验收的数学建模流程。

项目不只保存最终论文，还保留模型分析、求解代码、中间数据、收敛性检验、科研图、DrawIO 源文件与验收报告，使每个结论都能回溯到公式、程序和数据。

## 核心特点

- **逐题推进**：按照问题依赖关系依次完成建模、编码、制图、写作与验收，前一问批准后再进入下一问。
- **严格几何判据**：将真目标保留为完整圆柱体，以全部目标视线的最坏距离判断完全遮蔽，同时给出点目标简化结果用于对照。
- **事件驱动求解**：使用 Brent 法定位遮蔽状态切换时刻，避免固定时间步长带来的边界误差。
- **全局与局部联合优化**：结合多初值差分进化、航向扇区筛查和局部细化，降低陷入局部最优盆地的风险。
- **论文级可视化**：图表由真实计算数据生成，流程图保留可编辑的 DrawIO 源文件，并同步导出论文用 PDF。
- **完整质量检查**：核对数值复现、约束实现、图文一致性、网格收敛、边界扰动和 LaTeX 版式。

## 效果预览

![问题二优化诊断图](figures/q2/q2_optimization_diagnostics.png)

左图展示不同初值与外向航向盆地的优化过程，右图展示最优策略下完整圆柱目标的最坏视线距离及有效遮蔽区间。

## 当前成果

| 子问题 | 任务 | 核心结果 | 状态 |
| --- | --- | --- | --- |
| 问题一 | 给定策略下计算单枚烟幕弹的有效遮蔽时长 | 完整圆柱口径 `1.392 s` | 已批准 |
| 问题二 | 优化 FY1 航向、速度、投放时刻与引信延时 | 最大有效遮蔽时长 `4.588 s` | 待审查 |
| 问题三 | 单机三弹时序优化 | — | 未开始 |
| 问题四 | 三机单弹协同优化 | — | 未开始 |
| 问题五 | 多机、多弹、多目标资源分配 | — | 未开始 |

问题二当前最优策略：航向角 `5.112023°`、飞行速度 `140 m/s`、投放时刻 `0.878620 s`、引信延时 `0.053112 s`，完整遮蔽区间为 `[0.931732, 5.519794] s`。

## 工作流

```text
题目与附件
    ↓
问题拆解与依赖分析
    ↓
数学模型与完整约束
    ↓
代码求解、收敛与敏感性检验
    ↓
科研数据图与 DrawIO 流程图
    ↓
CUMCM LaTeX 正文
    ↓
结果一致性与 PDF 版式验收
```

仓库内置的 Skills 将流程拆分为以下模块：

| Skill | 作用 |
| --- | --- |
| `1start-mathmodel` | 初始化任务、识别子问题并控制逐题审查 |
| `2analysis-modeling` | 建立可编码、可验证的数学模型与完整约束组 |
| `3coding-visual` | 编写求解程序、验证结果并生成科研数据图 |
| `4drawio` | 绘制技术路线图、算法流程图和模型结构图 |
| `5writing` | 使用 CUMCM LaTeX 模板逐题撰写论文 |
| `6verity` | 检查复现性、数值一致性、图表质量和版式 |

## 项目结构

```text
MathModelingWorkflow/
├── .agents/skills/    # 数学建模工作流 Skills 与规范
├── A题/               # 题目及原始附件
├── code/              # 各子问题的 Python 求解程序
├── diagrams/          # DrawIO 源文件与导出图
├── figures/           # 科研数据图（PDF/PNG）
├── paper/             # CUMCM LaTeX 论文工程
├── reports/           # 建模、结果与验收报告
├── results/           # JSON/CSV 数值结果和作图数据
├── plan.md            # 顶层建模计划与统一口径
└── todo.md            # 逐题进度与验收清单
```

## 快速开始

### 1. 准备 Python 环境

建议使用 Python 3.10 或更高版本：

```bash
pip install numpy scipy matplotlib
```

### 2. 复现问题一

在仓库根目录运行：

```bash
python code/q1_smoke_duration.py
```

结果将写入 `results/q1/`，图片将写入 `figures/q1/`。

### 3. 复现问题二

```bash
python code/q2_single_smoke_optimization.py --maxiter 90 --popsize 11
```

该步骤包含全局搜索、局部细化、边界检查和高密度圆柱轮廓复算，运行时间会明显长于问题一。

### 4. 编译论文

进入论文目录后使用 XeLaTeX：

```powershell
cd paper
xelatex -interaction=nonstopmode main.tex; xelatex -interaction=nonstopmode main.tex
```

需要运行两轮，是因为交叉引用、图表编号和页码信息要在第一轮写入辅助文件，再由第二轮回填。若本机已安装 Perl，也可以使用：

```bash
latexmk -xelatex main.tex
```

论文工程的详细说明见 [`paper/README.md`](paper/README.md)。

## 关键输出

- 最终论文：`paper/main.pdf`
- 问题一主结果：`results/q1/summary.json`
- 问题二主结果：`results/q2/summary.json`
- 数值结果汇总：`reports/RESULTS_REPORT.md`
- 验收记录：`reports/VERIFY_REPORT.md`
- 当前任务状态：`todo.md`

## 建模口径

本项目主模型采用完整圆柱目标的保守遮蔽定义：仅当导弹到圆柱目标所有点的有限视线段均与有效烟幕球相交时，才认为目标被完全遮蔽。代码中将投影参数限制在有限线段 `[0,1]`，避免把导弹后方的无限延长线误判为遮蔽。

对于题意可能存在的口径差异，仓库同时保存目标中心点和底面圆心的对照结果，并通过角向网格加密、事件根求解和参数扰动验证结果稳定性。

## 说明

- 本仓库仍在按照逐题审查流程完善，问题三至问题五尚未开始。
- 题目、附件及 CUMCM 模板的著作权归原作者或相关组织所有。
- 本项目用于数学建模学习、研究与工作流实践，请遵守竞赛规则和学术诚信要求。

## 致谢

论文部分基于 [CUMCMThesis](https://github.com/latexstudio/CUMCMThesis) 模板整理，并参考了项目内附带的全国大学生数学建模竞赛论文格式规范。
