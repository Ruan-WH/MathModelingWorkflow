"""Fallback vector renderer for the editable Q4/Q5 DrawIO flowcharts."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

ROOT = Path(__file__).resolve().parents[1]


def configure():
    names = {f.name for f in font_manager.fontManager.ttflist}
    zh = next((x for x in ("SimSun", "Microsoft YaHei", "SimHei") if x in names), "DejaVu Sans")
    plt.rcParams.update({"font.family": zh, "font.size": 11, "pdf.fonttype": 42})


def box(ax, y, text, kind="rect", width=0.62, height=0.085):
    x = 0.5 - width / 2
    if kind == "round":
        patch = FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.008",
                               facecolor="white", edgecolor="#111111", linewidth=1.8)
    elif kind == "diamond":
        patch = Polygon([[0.5, y + height], [x + width, y + height / 2],
                         [0.5, y], [x, y + height / 2]], closed=True,
                        facecolor="#F2F2F2", edgecolor="#111111", linewidth=1.8)
    elif kind == "para":
        s = 0.045
        patch = Polygon([[x+s, y], [x+width-s, y], [x+width, y+height], [x, y+height]],
                        closed=True, facecolor="#F2F2F2", edgecolor="#111111", linewidth=1.8)
    else:
        patch = Rectangle((x, y), width, height, facecolor="white",
                          edgecolor="#111111", linewidth=1.8)
    ax.add_patch(patch)
    ax.text(0.5, y + height/2, text, ha="center", va="center", fontsize=11)
    return y, height


def arrow(ax, y1, y2):
    ax.annotate("", xy=(0.5, y2), xytext=(0.5, y1),
                arrowprops=dict(arrowstyle="-|>", lw=1.8, color="#111111"))


def render(tag, steps):
    configure()
    fig, ax = plt.subplots(figsize=(5.0, 7.2 if tag == "q4" else 8.2))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    positions = []
    for y, text, kind in steps:
        positions.append(box(ax, y, text, kind))
    for (y, h), (ny, nh) in zip(positions[:-1], positions[1:]):
        arrow(ax, y, ny + nh)
    out = ROOT / "diagrams" / tag
    fig.savefig(out / f"fig_flow_{tag}.pdf", bbox_inches="tight", pad_inches=0.04)
    fig.savefig(out / f"fig_flow_{tag}.png", dpi=260, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


render("q4", [
    (0.89, "开始：三机对 M1 协同遮蔽", "round"),
    (0.75, "输入三架无人机初始位置\n与问题二单弹评价器", "para"),
    (0.61, "分别搜索 FY1、FY2、FY3\n单弹可行时间窗", "rect"),
    (0.47, "合并三枚烟幕弹有效区间\n并压缩重叠区间", "rect"),
    (0.31, "约束与时间窗复核", "diamond"),
    (0.15, "5760 点边界采样与事件求根", "rect"),
    (0.01, "输出策略与 result2.xlsx", "para"),
])

render("q5", [
    (0.91, "开始：五机三目标资源协同", "round"),
    (0.80, "输入 5 架无人机、3 枚导弹\n及完整圆柱评价器", "para"),
    (0.69, "全部 UAV–Missile 组合\n单弹效能探针", "rect"),
    (0.58, "筛除零收益组合\n按边际收益建立任务分配", "rect"),
    (0.47, "分组优化共享航迹\n及各弹投放—起爆时序", "rect"),
    (0.34, "容量、间隔和物理约束复核", "diamond"),
    (0.22, "逐导弹合并有效区间\n并计算三目标时长之和", "rect"),
    (0.11, "高密度边界采样与事件求根", "rect"),
    (0.00, "输出资源分配与 result3.xlsx", "para"),
])
