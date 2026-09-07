---
name: 5writing
description: "按捆绑的 CUMCM 1.1.0 官方 LaTeX 工程逐题撰写数学建模论文；每完成一个子问题正文并编译检查后暂停等待用户审查。"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, WebSearch, WebFetch
---

# CUMCM 论文逐题写作

本项目模板已固定，不询问排版引擎。必须使用本 skill 的：

```text
assets/cumcm-1.1.0.zip
```

该资产来自用户指定的 `cumcm-1.1.0 2026-8-21 171238 1.zip`。除非用户明确更换模板，不得使用旧 Typst 模板、旧 `templates/zh/cumcm-latex`、通用骨架或从零自建版式。

## 模板完整性

首次创建 `paper/` 时，从 ZIP 内 `cumcm-1.1.0/` 原样初始化，并保留：`main.tex`、`latexmkrc`、`commons/cumcmthesis.cls`、`commons/preamble.tex`、`contents/info.tex`、`contents/abstract.tex`、`contents/references.tex`、`contents/sections/`、`contents/appendix/`、`figures/`、`fonts/`。

- 不修改 `cumcmthesis.cls` 的版式，不替换字体，不改页边距、字号、标题、编号、摘要或参考文献样式。
- `main.tex` 保持 `\documentclass[withoutpreface,bwprint]{commons/cumcmthesis}`、无目录、导言与内容分文件 `\input{}` 结构。
- 可重写 `s1.tex` 至 `s6.tex` 的示例内容；需要更多章节时增加 `s7.tex` 等，并在 `main.tex` 用相同 `\input{contents/sections/sN.tex}` 方式引入。
- 用户信息只写 `contents/info.tex`，摘要只写 `contents/abstract.tex`，参考文献只写 `contents/references.tex`，附录只写 `contents/appendix/`。
- 将已批准图复制到 `paper/figures/`，用有意义的英文/数字文件名引用，禁止绝对路径。

## 强制逐题审查门

每次只处理当前已完成计算的问题 i：

1. 读取问题 i 已验证的建模、结果和 DrawIO 记录。
2. 写入问题分析、模型、求解、结果、校验与图表；同步维护必要的公共假设、符号和预处理段落。
3. 只引用已生成并核验的数值与图表，不提前写问题 i+1 的结论。
4. 编译当前整篇稿，检查新增部分的公式、引用、图表、分页和乱码。
5. 报告新增章节、关键结果、图表和 PDF 路径，然后停止等待用户审查。

用户明确批准后才开始下一题；要求修改时先修改当前题、重新编译并再次停止。摘要最后写：全部子问题逐题批准后，才汇总 `contents/abstract.tex`，再完成模型评价、参考文献、附录和最终验收。

## 内容规则

- 用连贯学术段落连接“假设—公式—算法—结果—解释”。
- 数值和四舍五入与 `RESULTS_REPORT.md` 完全一致。
- 图用模板的 `figure`、`\includegraphics`、`\caption`、`\label`；表用 `booktabs` 三线表；用 `\cref{}` 或模板已有命令交叉引用。
- 正文不泄露内部目录、skill 名称或工作流；图表必须在相邻正文中分析。
- 只使用真实、可核验的参考文献。

## 编译

在 `paper/` 优先运行 `latexmk main`；不可用时运行两遍 `xelatex -interaction=nonstopmode main.tex`。每个审查点检查编译成功、无未解析引用/缺图/溢出版心，中文和公式字体正常。最终稿不得带 `draft`，保持 `withoutpreface,bwprint`；若当年通知冲突，先向用户说明再调整。
