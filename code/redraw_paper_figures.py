# Academic Figure Skill Asset Confirmation (verified against assets/figures/)
# Q1 distance curve -> LineTrend -> param inherit; project data are continuous physical distances.
# Q2 convergence/margin -> LineTrend -> param inherit; variable-length traces are incompatible with demo arrays.
# Q3 basin comparison -> BarComparison -> cross-type inherit; deterministic candidates need no error bars.
# Q3-Q5 interval timelines -> LineTrend -> cross-type inherit; intervals require segment glyphs, not area fills.
# Q5 assignment matrix -> no exact asset -> cross-type inherit from restrained categorical comparison styling.
# RULE: use project CSV/JSON only; inherit typography, palette, open axes, line hierarchy, and compact annotation.
"""Redraw the five verified quantitative figures without touching paper/figures."""

from __future__ import annotations

# Academic Figure Skill Typography Baseline — COPY VERBATIM, place at TOP of script
import matplotlib as mpl
mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans"],
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 8,
    "figure.titlesize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "legend.frameon": False,
})

# Academic Figure Skill Nature/Cell/Science Color Palette -- COPY VERBATIM
CATEGORICAL = ["#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666"]
CATEGORICAL_EXTENDED = [
    "#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666",
    "#4393C3", "#D6604D", "#5AAE61", "#B35806", "#9970AB", "#999999",
]
DIVERGING   = ["#2166AC", "#F7F7F7", "#B2182B"]
SEQUENTIAL  = ["#F7FBFF", "#6BAED6", "#08306B"]
ACCENT_RED  = "#B2182B"
GREY        = "#999999"
BLACK       = "#222222"

# Academic Figure Skill Export Baseline — COPY VERBATIM
mpl.rcParams.update({
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "savefig.bbox": "tight",
    "savefig.dpi": 300,
})

def save_cns_figure(fig, filename):
    """Standard Academic Figure Skill export: vector PDF + 300dpi PNG preview."""
    fig.savefig(f"{filename}.pdf", bbox_inches="tight", dpi=300)
    fig.savefig(f"{filename}.png", bbox_inches="tight", dpi=300)


import csv
import json
from collections import defaultdict
from pathlib import Path

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


ROOT = Path(__file__).resolve().parents[1]
RESULTS, FIGURES = ROOT / "results", ROOT / "figures"
BLUE, RED, GREEN, ORANGE, PURPLE, MID_GREY = CATEGORICAL
PALE_BLUE, LIGHT_GREY = "#DCE9F4", "#E5E5E5"
UAV_COLORS = {"FY1": BLUE, "FY2": ORANGE, "FY3": GREEN, "FY4": PURPLE, "FY5": RED}
MISSILE_COLORS = {"M1": BLUE, "M2": ORANGE, "M3": PURPLE}


def configure_project_fonts() -> None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    required = {"Times New Roman", "SimSun"}
    missing = sorted(required - available)
    if missing:
        raise RuntimeError(f"Required figure fonts are unavailable: {', '.join(missing)}")
    mpl.rcParams.update({
        "font.family": ["Times New Roman", "SimSun"],
        "mathtext.fontset": "custom",
        "mathtext.rm": "Times New Roman",
        "mathtext.it": "Times New Roman:italic",
        "mathtext.bf": "Times New Roman:bold",
        "mathtext.sf": "Times New Roman",
        "axes.unicode_minus": False,
        "savefig.facecolor": "white",
    })


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def polish_axis(ax: plt.Axes, grid_axis: str | None = None) -> None:
    ax.spines["left"].set_color(BLACK)
    ax.spines["bottom"].set_color(BLACK)
    ax.tick_params(colors=BLACK, length=3)
    if grid_axis:
        ax.grid(axis=grid_axis, color=LIGHT_GREY, lw=0.35, zorder=0)
        ax.set_axisbelow(True)


def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(0.5, -0.30, label, transform=ax.transAxes, ha="center", va="top",
            fontsize=9, fontweight="bold", color=BLACK, clip_on=False)


def save_bundle(fig: plt.Figure, folder: Path, stem: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    save_cns_figure(fig, str(folder / stem))
    plt.close(fig)


def draw_q1() -> None:
    rows = read_csv(RESULTS / "q1" / "margin_curve.csv")
    summary = read_json(RESULTS / "q1" / "summary.json")
    t = np.array([float(r["time_s"]) for r in rows])
    full = np.array([float(r["full_target_worst_distance_m"]) for r in rows])
    center = np.array([float(r["center_point_distance_m"]) for r in rows])
    bottom = np.array([float(r["bottom_center_distance_m"]) for r in rows])
    entry, exit_ = summary["full_target"]["intervals"][0]
    fig, ax = plt.subplots(figsize=(183 / 25.4, 78 / 25.4), constrained_layout=True)
    ax.axvspan(entry, exit_, color=PALE_BLUE, alpha=0.75, lw=0)
    ax.plot(t, full, color=BLUE, lw=1.8, label="完整目标：最不利视线", zorder=4)
    ax.plot(t, center, color=MID_GREY, lw=1.0, ls=(0, (5, 3)), label="圆柱几何中心")
    ax.plot(t, bottom, color=GREY, lw=1.0, ls=(0, (1.5, 2.2)), label="底面圆心")
    ax.axhline(10, color=RED, lw=1.0, ls=(0, (4, 2.5)), label="遮蔽阈值 10 m")
    for x, ha in ((entry, "left"), (exit_, "right")):
        ax.axvline(x, color=BLUE, lw=0.6, ls=(0, (2, 2)))
        ax.annotate(f"{x:.3f} s", xy=(x, 10), xytext=(5 if ha == "left" else -5, 9),
                    textcoords="offset points", ha=ha, color=BLUE, fontsize=7.5)
    ax.text((entry + exit_) / 2, 2.2, f"完整遮蔽  {exit_ - entry:.3f} s",
            ha="center", va="center", fontsize=8.2, fontweight="bold", color=BLUE)
    ax.set(xlim=(5.1, 9.8), ylim=(0, 26), xlabel="雷达发现后的时间 t (s)",
           ylabel="烟幕球心至视线段的距离 (m)")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.01), ncol=4, handlelength=2.4,
              columnspacing=1.2, borderaxespad=0)
    polish_axis(ax, "y")
    save_bundle(fig, FIGURES / "q1", "q1_occlusion_distance")


def draw_q2() -> None:
    history = read_csv(RESULTS / "q2" / "optimization_history.csv")
    curve_rows = read_csv(RESULTS / "q2" / "optimal_margin_curve.csv")
    summary = read_json(RESULTS / "q2" / "summary.json")
    grouped: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for row in history:
        grouped[row["seed"]].append((int(row["iteration"]), float(row["best_duration_s"])))
    fig, axes = plt.subplots(1, 2, figsize=(183 / 25.4, 82 / 25.4),
                             gridspec_kw={"width_ratios": [1.25, 1.0]}, constrained_layout=True)
    ax = axes[0]
    for seed, color in zip(("2025", "2026", "2027"), ("#9CAEC8", "#BBC6D6", "#D0D6DF")):
        pts = grouped[seed]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=1.25, label=f"随机种子 {seed}")
    outward = grouped["outward_geometric_start"]
    ax.plot([p[0] for p in outward], [p[1] for p in outward], color=BLUE, lw=2,
            label="外向盆地细化", zorder=4)
    best = summary["full_target"]["duration_s"]
    ax.axhline(best, color=RED, lw=0.8, ls=(0, (4, 2.5)))
    ax.text(520, best + 0.025, f"{best:.3f} s", ha="right", va="bottom", color=RED, fontsize=7)
    ax.set(xscale="log", xlim=(1, 650), ylim=(1.25, 4.75), xlabel="优化迭代次数（对数坐标）",
           ylabel="当前最优遮蔽时长 (s)")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.01), ncol=2, borderaxespad=0,
              fontsize=7, handlelength=2.1, columnspacing=1.1)
    polish_axis(ax, "y")
    panel_label(ax, "(a)")
    ax = axes[1]
    t = np.array([float(r["time_s"]) for r in curve_rows])
    d = np.array([float(r["worst_distance_m"]) for r in curve_rows])
    entry, exit_ = summary["full_target"]["intervals"][0]
    ax.axvspan(entry, exit_, color=PALE_BLUE, alpha=0.75, lw=0)
    ax.plot(t, d, color=BLUE, lw=1.8)
    ax.axhline(10, color=RED, lw=1.0, ls=(0, (4, 2.5)))
    for x in (entry, exit_):
        ax.axvline(x, color=BLUE, lw=0.6, ls=(0, (2, 2)))
    idx = int(np.nanargmin(d))
    ax.scatter(t[idx], d[idx], s=18, color=BLACK, zorder=5)
    ax.annotate(f"最小裕度 {10-d[idx]:.2f} m", xy=(t[idx], d[idx]), xytext=(-8, 13),
                textcoords="offset points", ha="right", fontsize=7, color=BLACK)
    ax.text((entry + exit_) / 2, 9.45, f"{exit_ - entry:.3f} s", ha="center", va="top",
            color=BLUE, fontweight="bold")
    ax.set(xlim=(entry - 0.05, exit_ + 0.38), ylim=(max(0, float(d.min()) - 0.7), 10.7),
           xlabel="雷达发现后的时间 t (s)", ylabel="最坏视线距离 D(t) (m)")
    polish_axis(ax, "y")
    panel_label(ax, "(b)")
    save_bundle(fig, FIGURES / "q2", "q2_optimization_diagnostics")


def draw_q3() -> None:
    candidates = read_csv(RESULTS / "q3" / "multistart.csv")
    summary = read_json(RESULTS / "q3" / "summary.json")
    fig, axes = plt.subplots(1, 2, figsize=(183 / 25.4, 82 / 25.4),
                             gridspec_kw={"width_ratios": [0.9, 1.55]}, constrained_layout=True)
    ax = axes[0]
    labels = {
        "global": "全航向随机搜索", "outward": "外向扇区搜索",
        "inward": "内向扇区搜索", "window_stitching": "时间窗拼接",
    }
    ordered = [next(row for row in candidates if row["basin"] == key) for key in labels]
    ys = np.arange(len(ordered))[::-1]
    values = np.array([float(row["coarse_union_duration_s"]) for row in ordered])
    for y, row, value in zip(ys, ordered, values):
        chosen = row["basin"] == "window_stitching"
        color = BLUE if chosen else GREY
        ax.plot([0, value], [y, y], color=color, lw=1.6 if chosen else 1.0)
        ax.scatter(value, y, s=34 if chosen else 22, color=color, zorder=3)
        ax.text(value + 0.12, y, f"{value:.2f}", va="center", color=color, fontsize=7.3)
    ax.set_yticks(ys, [labels[row["basin"]] for row in ordered])
    ax.set(xlim=(0, 8.15), xlabel="联合有效遮蔽时长 (s)")
    polish_axis(ax, "x")
    panel_label(ax, "(a)")

    ax = axes[1]
    bomb_colors = [BLUE, ORANGE, PURPLE]
    for idx, (bomb, color) in enumerate(zip(summary["bombs"], bomb_colors)):
        y = 3 - idx
        for start, end in bomb["effective_intervals_s"]:
            ax.plot([start, end], [y, y], color=color, lw=7, solid_capstyle="butt")
            ax.text((start + end) / 2, y + 0.18, f"{end-start:.2f} s", ha="center",
                    va="bottom", color=color, fontsize=7)
    union_y = 0.55
    for start, end in summary["union_intervals_s"]:
        ax.plot([start, end], [union_y, union_y], color=BLACK, lw=8, solid_capstyle="butt")
        ax.text((start + end) / 2, union_y - 0.25, f"并集 {end-start:.3f} s", ha="center",
                va="top", color=BLACK, fontsize=7.5, fontweight="bold")
    ax.set_yticks([3, 2, 1, union_y], ["烟幕弹 1", "烟幕弹 2", "烟幕弹 3", "区间并集"])
    ax.set(xlim=(4.7, 13.25), ylim=(0.05, 3.65), xlabel="雷达发现后的时间 t (s)")
    polish_axis(ax, "x")
    panel_label(ax, "(b)")
    save_bundle(fig, FIGURES / "q3", "q3_optimization_diagnostics")


def draw_q4() -> None:
    summary = read_json(RESULTS / "q4" / "summary.json")
    fig, ax = plt.subplots(figsize=(183 / 25.4, 76 / 25.4), constrained_layout=True)
    rows = [(bomb["uav"], bomb["intervals"], bomb["duration"]) for bomb in summary["bombs"]]
    for (uav, intervals, duration), y in zip(rows, [3.2, 2.2, 1.2]):
        for start, end in intervals:
            ax.plot([start, end], [y, y], color=UAV_COLORS[uav], lw=9, solid_capstyle="butt")
            ax.text((start + end) / 2, y + 0.22, f"{duration:.3f} s", ha="center",
                    va="bottom", color=UAV_COLORS[uav], fontsize=7.5)
    for start, end in summary["missile_intervals"]["M1"]:
        ax.plot([start, end], [0.35, 0.35], color=BLACK, lw=9, solid_capstyle="butt")
    ax.text(22.3, 0.02, f"M1 并集  {summary['objective_sum_s']:.3f} s", ha="center",
            va="top", color=BLACK, fontweight="bold")
    ax.set_yticks([3.2, 2.2, 1.2, 0.35], ["FY1 · 早段", "FY2 · 中段", "FY3 · 晚段", "联合窗口"])
    ax.set(xlim=(0, 45), ylim=(-0.25, 3.85), xlabel="雷达发现后的时间 t (s)")
    polish_axis(ax, "x")
    save_bundle(fig, FIGURES / "q4", "q4_coordination_diagnostics")


def draw_q5() -> None:
    summary = read_json(RESULTS / "q5" / "summary.json")
    bombs_by_missile: dict[str, list[dict]] = defaultdict(list)
    for bomb in summary["bombs"]:
        bombs_by_missile[bomb["missile"]].append(bomb)
    fig, axes = plt.subplots(1, 2, figsize=(183 / 25.4, 88 / 25.4),
                             gridspec_kw={"width_ratios": [1.75, 0.85]}, constrained_layout=True)
    ax = axes[0]
    base_y = {"M1": 2.7, "M2": 1.55, "M3": 0.4}
    for missile in ("M1", "M2", "M3"):
        y0 = base_y[missile]
        for start, end in summary["missile_intervals"][missile]:
            ax.plot([start, end], [y0, y0], color=MISSILE_COLORS[missile], alpha=0.2,
                    lw=15, solid_capstyle="butt")
        bombs = bombs_by_missile[missile]
        offsets = np.linspace(-0.25, 0.25, len(bombs)) if len(bombs) > 1 else np.array([0.0])
        for bomb, offset in zip(bombs, offsets):
            for start, end in bomb["intervals"]:
                y = y0 + offset
                color = UAV_COLORS[bomb["uav"]]
                ax.plot([start, end], [y, y], color=color, lw=4.2, solid_capstyle="butt")
                ax.text((start + end) / 2, y + 0.09, f"{bomb['uav']}-{bomb['bomb']}",
                        ha="center", va="bottom", color=color, fontsize=6.2)
        ax.text(31.7, y0, f"{summary['missile_durations'][missile]:.2f} s", ha="left",
                va="center", color=MISSILE_COLORS[missile], fontsize=7.5, fontweight="bold")
    ax.set_yticks([2.7, 1.55, 0.4], ["M1", "M2", "M3"])
    ax.set(xlim=(4.4, 34.2), ylim=(-0.15, 3.25), xlabel="雷达发现后的时间 t (s)", ylabel="来袭导弹")
    polish_axis(ax, "x")
    panel_label(ax, "(a)")

    ax = axes[1]
    uavs, missiles = ["FY1", "FY2", "FY3", "FY4", "FY5"], ["M1", "M2", "M3"]
    counts = {(u, m): 0 for u in uavs for m in missiles}
    for bomb in summary["bombs"]:
        counts[(bomb["uav"], bomb["missile"])] += 1
    for yi, uav in enumerate(uavs[::-1]):
        for xi, missile in enumerate(missiles):
            count = counts[(uav, missile)]
            if count:
                ax.scatter(xi, yi, s=80 + 48 * count, color=MISSILE_COLORS[missile],
                           edgecolor="white", linewidth=0.8)
                ax.text(xi, yi, str(count), ha="center", va="center", fontsize=7.3,
                        color="white", fontweight="bold")
            else:
                ax.scatter(xi, yi, s=20, facecolor="white", edgecolor=LIGHT_GREY, linewidth=0.8)
    ax.set_xticks(range(3), missiles)
    ax.set_yticks(range(5), uavs[::-1])
    ax.set(xlim=(-0.55, 2.55), ylim=(-0.55, 4.55), xlabel="指派目标", ylabel="执行无人机")
    ax.spines[["left", "bottom"]].set_visible(False)
    ax.tick_params(length=0)
    panel_label(ax, "(b)")
    ax.text(0.5, -0.17, "圆内数字为投弹数", transform=ax.transAxes, ha="center",
            va="top", fontsize=6.8, color=GREY)
    save_bundle(fig, FIGURES / "q5", "q5_coordination_diagnostics")


def main() -> None:
    configure_project_fonts()
    draw_q1()
    draw_q2()
    draw_q3()
    draw_q4()
    draw_q5()
    print("Updated five standalone figure bundles under figures/q1 ... figures/q5.")


if __name__ == "__main__":
    main()
