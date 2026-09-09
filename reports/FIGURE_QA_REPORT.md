# 五张数据图重绘与 QA 记录

## 图形契约

| 图件 | 核心结论 | 主证据 | 辅助证据 | 数据来源 |
|---|---|---|---|---|
| Q1 | 完整目标口径下形成 1.392 s 连续遮蔽窗口 | 最不利视线距离曲线与 10 m 阈值 | 两种点目标近似曲线 | `results/q1/margin_curve.csv`、`summary.json` |
| Q2 | 多起点搜索收敛到约 4.588 s，最优解在完整窗口内满足约束 | 收敛轨迹 | 最优解距离裕度曲线 | `results/q2/optimization_history.csv`、`optimal_margin_curve.csv`、`summary.json` |
| Q3 | 时间窗拼接优于其余搜索盆地，并由三枚烟幕弹连续覆盖 7.610 s | 候选解比较 | 单弹有效区间与并集 | `results/q3/multistart.csv`、`summary.json` |
| Q4 | 三架无人机在早、中、晚三个时段形成总计 10.657 s 的分段协同遮蔽 | 三机时间轴 | M1 区间并集 | `results/q4/summary.json` |
| Q5 | 八枚烟幕弹在三类目标间形成明确的时窗与资源分配 | 分导弹时间轴 | 无人机—导弹指派矩阵 | `results/q5/summary.json` |

## 资产与样式来源

- 已扫描 `academic-figure-skill-main/assets/figures/`；折线图继承 `LineTrend` 的开放坐标轴、线宽层级与紧凑标注，候选解比较继承 `BarComparison` 的克制分类配色。
- 示例脚本的数据结构均与本项目的连续曲线、变长优化历史或区间并集不完全兼容，因此采用 `param inherit` / `cross-type inherit`，未运行或复制示例数据。
- 输出宽度按 183 mm 通栏图设计，使用 skill 的 Typography、Color Palette 与 Export Baseline，从同一 Matplotlib Figure 导出 PDF 和 300 dpi PNG。
- CUMCM 双语字体规则为 Times New Roman 优先、SimSun 中文字形回退；多面板编号统一置于各子图下方水平居中位置。

## 数据与统计说明

- Q1 使用 1201 个确定性时间采样点；Q2 使用 633 条优化历史记录和 1601 个距离曲线采样点；Q3 比较 4 个搜索盆地；Q4 含 3 枚烟幕弹；Q5 含 8 枚烟幕弹。
- 图中数值来自已有 CSV/JSON 计算结果，没有下采样、手工改数或从论文抄数。
- 本组图展示确定性几何计算与优化结果，不存在抽样均值、置信区间或显著性检验，故误差条和统计检验不适用；Q2 的多起点轨迹承担算法稳定性证据。

## QA 结论

- AP：脚本含资产确认表、受控色板和规定导出基线，无默认彩虹色、3D、阴影或虚构误差条。
- CL：脚本通过 Python AST 语法检查；`3coding-visual`、`mathmodel-figure-templates` 与 `academic-figure-skill` 通过 skill 校验；academic skill 引用完整性检查为 HEALTHY。
- VI：逐张检查 300 dpi PNG，未发现中文缺字、截断、重叠、面板冗余或不可辨的色彩编码；`(a)`、`(b)` 均位于子图下方且未与横轴标题冲突。
- VV：图中阈值、持续时间、区间并集与资源数均直接读取对应结果文件，未改变模型结论。
- 本轮仅更新 `figures/q1` 至 `figures/q5`，没有同步到 `paper/figures`，也没有修改或编译 `main.tex` / `main.pdf`。
