---
name: mathmodel-figure-templates
description: "为数学建模数据图选择和复用现成科研绘图模板，包括雨云图、ROC 置信区间、泰勒图、相关组合图、预测边缘分布和 Nature 和弦图。"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob
---

# 科研绘图模板

模板脚本位于 `scripts/templates/`，目录映射见 `references/figure-catalog.md`，实现思路见 `references/plot-recipes.md`。

## 使用

1. 根据要回答的科学问题选择最接近的模板，而不是按外观堆图。
2. 先复制模板脚本到当前项目的 `code/` 或绘图脚本目录，再修改副本；不要改本 skill 的基准模板。
3. 用项目真实数据替换模板的模拟数据。若只做模板演示，必须明确标注为模拟数据。
4. 保留确定性随机种子、字体嵌入、PNG/PDF/SVG 导出与紧凑布局技巧。
5. 服从 `3coding-visual/references/nature-visual-style.md` 的统一样式，不机械复制模板中的标题、颜色、字号或示例数值。

模板可提供复杂图层结构，如原始点+分布+摘要、折间曲线+置信带、主散点+边缘分布、多面板共享图例。选择后仍需按论文最终尺寸做视觉验收。
