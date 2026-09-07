"""Solve Question 1 of CUMCM 2025 Problem A.

The primary criterion requires the smoke sphere to intersect every line segment
from missile M1 to the complete cylindrical target. Two point-target criteria
are reported only as modelling-scope comparisons.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from scipy.optimize import brentq, minimize_scalar


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "q1"
FIG = ROOT / "figures" / "q1"


@dataclass(frozen=True)
class Parameters:
    missile_initial: tuple[float, float, float] = (20000.0, 0.0, 2000.0)
    missile_speed: float = 300.0
    uav_initial: tuple[float, float, float] = (17800.0, 0.0, 1800.0)
    uav_speed: float = 120.0
    release_time: float = 1.5
    fuse_delay: float = 3.6
    gravity: float = 9.8
    cloud_descent_speed: float = 3.0
    cloud_radius: float = 10.0
    cloud_lifetime: float = 20.0
    target_center_xy: tuple[float, float] = (0.0, 200.0)
    target_radius: float = 7.0
    target_height: float = 10.0


def kinematics(p: Parameters) -> dict[str, np.ndarray | float]:
    missile_initial = np.asarray(p.missile_initial, dtype=float)
    missile_velocity = -p.missile_speed * missile_initial / np.linalg.norm(missile_initial)
    uav_velocity = np.array([-p.uav_speed, 0.0, 0.0])
    uav_initial = np.asarray(p.uav_initial, dtype=float)
    release_point = uav_initial + uav_velocity * p.release_time
    explosion_time = p.release_time + p.fuse_delay
    explosion_point = release_point + uav_velocity * p.fuse_delay
    explosion_point[2] -= 0.5 * p.gravity * p.fuse_delay**2
    return {
        "missile_initial": missile_initial,
        "missile_velocity": missile_velocity,
        "uav_velocity": uav_velocity,
        "release_point": release_point,
        "explosion_time": explosion_time,
        "explosion_point": explosion_point,
    }


def target_rims(p: Parameters, n_theta: int) -> np.ndarray:
    """Sample the two circular rims that generate the cylinder's visual hull."""
    theta = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    x0, y0 = p.target_center_xy
    circles = [
        np.column_stack(
            (
                x0 + p.target_radius * np.cos(theta),
                y0 + p.target_radius * np.sin(theta),
                np.full_like(theta, z),
            )
        )
        for z in (0.0, p.target_height)
    ]
    extras = np.array(
        [[x0, y0, 0.0], [x0, y0, p.target_height], [x0, y0, p.target_height / 2.0]]
    )
    return np.vstack((*circles, extras))


def states(t: float, p: Parameters, kin: dict) -> tuple[np.ndarray, np.ndarray]:
    missile = kin["missile_initial"] + kin["missile_velocity"] * t
    cloud = kin["explosion_point"].copy()
    cloud[2] -= p.cloud_descent_speed * (t - kin["explosion_time"])
    return missile, cloud


def max_segment_distance(t: float, p: Parameters, kin: dict, targets: np.ndarray) -> float:
    """Maximum cloud-center distance to missile-target sight segments."""
    missile, cloud = states(t, p, kin)
    sight = targets - missile
    lam = np.einsum("ij,j->i", sight, cloud - missile) / np.einsum(
        "ij,ij->i", sight, sight
    )
    lam = np.clip(lam, 0.0, 1.0)
    closest = missile + lam[:, None] * sight
    return float(np.linalg.norm(cloud - closest, axis=1).max())


def point_segment_distance(
    t: float, p: Parameters, kin: dict, target: np.ndarray
) -> float:
    missile, cloud = states(t, p, kin)
    sight = target - missile
    lam = float(np.dot(cloud - missile, sight) / np.dot(sight, sight))
    lam = float(np.clip(lam, 0.0, 1.0))
    return float(np.linalg.norm(cloud - (missile + lam * sight)))


def find_intervals(metric, p: Parameters, kin: dict, coarse_step: float = 0.02):
    start = float(kin["explosion_time"])
    end = start + p.cloud_lifetime
    grid = np.arange(start, end, coarse_step)
    if grid[-1] < end:
        grid = np.append(grid, end)
    values = np.array([metric(float(t)) - p.cloud_radius for t in grid])
    roots: list[float] = []
    for a, b, fa, fb in zip(grid[:-1], grid[1:], values[:-1], values[1:]):
        if fa == 0.0:
            roots.append(float(a))
        elif fa * fb < 0.0:
            roots.append(float(brentq(lambda x: metric(x) - p.cloud_radius, a, b, xtol=1e-11)))
    cuts = [start, *roots, end]
    intervals = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        if metric((a + b) / 2.0) <= p.cloud_radius:
            intervals.append((float(a), float(b)))
    return intervals, roots


def solve(p: Parameters, n_theta: int = 5760, coarse_step: float = 0.02) -> dict:
    kin = kinematics(p)
    target_points = target_rims(p, n_theta)
    full_metric = lambda t: max_segment_distance(t, p, kin, target_points)
    center = np.array([p.target_center_xy[0], p.target_center_xy[1], p.target_height / 2.0])
    bottom = np.array([p.target_center_xy[0], p.target_center_xy[1], 0.0])
    center_metric = lambda t: point_segment_distance(t, p, kin, center)
    bottom_metric = lambda t: point_segment_distance(t, p, kin, bottom)

    full_intervals, full_roots = find_intervals(full_metric, p, kin, coarse_step)
    center_intervals, _ = find_intervals(center_metric, p, kin, coarse_step)
    bottom_intervals, _ = find_intervals(bottom_metric, p, kin, coarse_step)
    bounded = (float(kin["explosion_time"]), float(kin["explosion_time"] + p.cloud_lifetime))
    min_result = minimize_scalar(full_metric, bounds=bounded, method="bounded")

    duration = lambda intervals: float(sum(b - a for a, b in intervals))
    return {
        "parameters": asdict(p),
        "missile_velocity": kin["missile_velocity"].tolist(),
        "release_point": kin["release_point"].tolist(),
        "explosion_time": float(kin["explosion_time"]),
        "explosion_point": kin["explosion_point"].tolist(),
        "full_target": {
            "intervals": [list(x) for x in full_intervals],
            "boundary_roots": full_roots,
            "duration": duration(full_intervals),
            "minimum_worst_distance": float(min_result.fun),
            "minimum_time": float(min_result.x),
            "n_theta": n_theta,
            "coarse_step": coarse_step,
        },
        "center_point": {
            "intervals": [list(x) for x in center_intervals],
            "duration": duration(center_intervals),
        },
        "bottom_center_point": {
            "intervals": [list(x) for x in bottom_intervals],
            "duration": duration(bottom_intervals),
        },
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def configure_plotting() -> None:
    available = {f.name for f in font_manager.fontManager.ttflist}
    font = next(
        (name for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial") if name in available),
        "DejaVu Sans",
    )
    plt.rcParams.update(
        {
            "font.family": font,
            "font.size": 8,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 7.5,
            "axes.linewidth": 0.9,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
            "axes.unicode_minus": False,
        }
    )


def make_figure(p: Parameters, result: dict) -> None:
    kin = kinematics(p)
    targets = target_rims(p, 1440)
    center = np.array([p.target_center_xy[0], p.target_center_xy[1], p.target_height / 2.0])
    bottom = np.array([p.target_center_xy[0], p.target_center_xy[1], 0.0])
    ts = np.linspace(float(kin["explosion_time"]), float(kin["explosion_time"] + p.cloud_lifetime), 1201)
    full = np.array([max_segment_distance(t, p, kin, targets) for t in ts])
    cen = np.array([point_segment_distance(t, p, kin, center) for t in ts])
    bot = np.array([point_segment_distance(t, p, kin, bottom) for t in ts])
    rows = [
        {
            "time_s": f"{t:.8f}",
            "full_target_worst_distance_m": f"{a:.8f}",
            "center_point_distance_m": f"{b:.8f}",
            "bottom_center_distance_m": f"{c:.8f}",
            "threshold_m": f"{p.cloud_radius:.8f}",
        }
        for t, a, b, c in zip(ts, full, cen, bot)
    ]
    write_csv(OUT / "margin_curve.csv", rows)

    configure_plotting()
    fig, ax = plt.subplots(figsize=(6.7, 3.5), constrained_layout=True)
    ax.plot(ts, full, color="#3B6FB6", lw=1.8, label="完整圆柱：最坏视线")
    ax.plot(ts, cen, color="#3A8F7B", lw=1.25, ls="--", label="圆柱几何中心")
    ax.plot(ts, bot, color="#777777", lw=1.1, ls=":", label="底面圆心")
    ax.axhline(p.cloud_radius, color="#B46A55", lw=1.1, ls="-.", label="有效半径 10 m")
    entry, exit_ = result["full_target"]["intervals"][0]
    ax.axvspan(entry, exit_, color="#3B6FB6", alpha=0.12, lw=0)
    for value, align in ((entry, "left"), (exit_, "right")):
        ax.axvline(value, color="#3B6FB6", lw=0.75, ls=(0, (2, 2)), alpha=0.9)
        ax.annotate(
            f"{value:.3f} s",
            xy=(value, p.cloud_radius),
            xytext=(5 if align == "left" else -5, 7),
            textcoords="offset points",
            ha=align,
            va="bottom",
            color="#264E86",
            fontsize=7.5,
        )
    ax.set_xlim(float(kin["explosion_time"]), 13.0)
    ax.set_ylim(0.0, 45.0)
    ax.set_xlabel("雷达发现后的时间 t (s)")
    ax.set_ylabel("烟幕球心至视线段的距离 (m)")
    ax.grid(axis="y", color="#D9D9D9", lw=0.55)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncol=2, loc="upper right", handlelength=2.8, columnspacing=1.2)
    ax.text(
        (entry + exit_) / 2,
        2.2,
        f"完整遮蔽 {exit_ - entry:.3f} s",
        ha="center",
        va="bottom",
        color="#264E86",
        fontsize=8,
    )
    fig.savefig(FIG / "q1_occlusion_distance.pdf", bbox_inches="tight", pad_inches=0.04)
    fig.savefig(FIG / "q1_occlusion_distance.png", dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    base = Parameters()
    result = solve(base)
    convergence_rows = []
    for n_theta in (180, 360, 720, 1440, 2880, 5760):
        item = solve(base, n_theta=n_theta)
        interval = item["full_target"]["intervals"][0]
        convergence_rows.append(
            {
                "n_theta": n_theta,
                "entry_time_s": f"{interval[0]:.10f}",
                "exit_time_s": f"{interval[1]:.10f}",
                "duration_s": f"{item['full_target']['duration']:.10f}",
            }
        )
    write_csv(OUT / "convergence.csv", convergence_rows)
    sensitivity_rows = []
    cases = [
        ("gravity_m_s2", v, Parameters(gravity=v)) for v in (9.7, 9.8, 9.9)
    ] + [
        ("cloud_descent_m_s", v, Parameters(cloud_descent_speed=v)) for v in (2.9, 3.0, 3.1)
    ] + [
        ("cloud_radius_m", v, Parameters(cloud_radius=v)) for v in (9.5, 10.0, 10.5)
    ]
    for parameter, value, params in cases:
        item = solve(params, n_theta=1440)
        sensitivity_rows.append(
            {
                "parameter": parameter,
                "value": f"{value:.6f}",
                "duration_s": f"{item['full_target']['duration']:.10f}",
            }
        )
    write_csv(OUT / "sensitivity.csv", sensitivity_rows)
    result["verification"] = {
        "convergence_file": "results/q1/convergence.csv",
        "sensitivity_file": "results/q1/sensitivity.csv",
        "plot_data_file": "results/q1/margin_curve.csv",
        "projection_parameter_is_clipped_to_segment": True,
        "effective_window_within_cloud_lifetime": all(
            result["explosion_time"] <= a <= b <= result["explosion_time"] + base.cloud_lifetime
            for a, b in result["full_target"]["intervals"]
        ),
    }
    with (OUT / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    make_figure(base, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

