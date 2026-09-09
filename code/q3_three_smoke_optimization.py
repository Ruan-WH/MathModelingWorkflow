"""Question 3: optimize three FY1 smoke bombs against missile M1.

FY1 keeps one heading and one speed.  The three release times are ordered and
separated by at least one second.  The objective is the measure of the union
of the complete-cylinder occlusion intervals, not the sum of their lengths.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from scipy.optimize import brentq, differential_evolution, minimize


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "q3"
FIG = ROOT / "figures" / "q3"


@dataclass(frozen=True)
class Parameters:
    missile_initial: tuple[float, float, float] = (20000.0, 0.0, 2000.0)
    missile_speed: float = 300.0
    uav_initial: tuple[float, float, float] = (17800.0, 0.0, 1800.0)
    speed_min: float = 70.0
    speed_max: float = 140.0
    gravity: float = 9.8
    cloud_descent_speed: float = 3.0
    cloud_radius: float = 10.0
    cloud_lifetime: float = 20.0
    target_center_xy: tuple[float, float] = (0.0, 200.0)
    target_radius: float = 7.0
    target_height: float = 10.0
    minimum_release_gap: float = 1.0


def fixed_states(p: Parameters) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    missile_initial = np.asarray(p.missile_initial, dtype=float)
    missile_velocity = -p.missile_speed * missile_initial / np.linalg.norm(missile_initial)
    uav_initial = np.asarray(p.uav_initial, dtype=float)
    impact_time = float(np.linalg.norm(missile_initial) / p.missile_speed)
    return missile_initial, missile_velocity, uav_initial, impact_time


def target_rims(p: Parameters, n_theta: int) -> np.ndarray:
    angle = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    x0, y0 = p.target_center_xy
    circles = [
        np.column_stack(
            (
                x0 + p.target_radius * np.cos(angle),
                y0 + p.target_radius * np.sin(angle),
                np.full_like(angle, z),
            )
        )
        for z in (0.0, p.target_height)
    ]
    extras = np.array(
        [[x0, y0, 0.0], [x0, y0, p.target_height], [x0, y0, p.target_height / 2.0]]
    )
    return np.vstack((*circles, extras))


def decode(y: np.ndarray, p: Parameters) -> dict:
    """Decode [heading, speed, r1, slack12, slack23, delay1, delay2, delay3]."""
    heading, speed, release_1, slack_12, slack_23, *delays = map(float, y)
    release_times = np.array(
        [
            release_1,
            release_1 + p.minimum_release_gap + slack_12,
            release_1 + 2.0 * p.minimum_release_gap + slack_12 + slack_23,
        ]
    )
    delays_array = np.asarray(delays, dtype=float)
    explosion_times = release_times + delays_array
    direction = np.array([np.cos(heading), np.sin(heading), 0.0])
    velocity = speed * direction
    _, _, uav_initial, _ = fixed_states(p)
    release_points = uav_initial[None, :] + release_times[:, None] * velocity[None, :]
    explosion_points = uav_initial[None, :] + explosion_times[:, None] * velocity[None, :]
    explosion_points[:, 2] -= 0.5 * p.gravity * delays_array**2
    return {
        "heading_rad": heading,
        "heading_deg": float(np.degrees(heading) % 360.0),
        "speed": speed,
        "direction": direction,
        "uav_velocity": velocity,
        "release_times": release_times,
        "release_gaps": np.diff(release_times),
        "delays": delays_array,
        "explosion_times": explosion_times,
        "release_points": release_points,
        "explosion_points": explosion_points,
    }


def feasible(y: np.ndarray, p: Parameters) -> bool:
    state = decode(y, p)
    _, _, _, impact_time = fixed_states(p)
    return bool(
        0.0 <= state["heading_rad"] <= 2.0 * np.pi
        and p.speed_min <= state["speed"] <= p.speed_max
        and np.all(state["release_times"] >= 0.0)
        and np.all(state["release_gaps"] >= p.minimum_release_gap - 1e-12)
        and np.all(state["delays"] >= 0.0)
        and np.all(state["explosion_times"] <= impact_time)
        and np.all(state["explosion_points"][:, 2] >= 0.0)
    )


def distances_over_time(
    times: np.ndarray,
    explosion_time: float,
    explosion_point: np.ndarray,
    p: Parameters,
    targets: np.ndarray,
) -> np.ndarray:
    missile_initial, missile_velocity, _, _ = fixed_states(p)
    missiles = missile_initial[None, :] + times[:, None] * missile_velocity[None, :]
    clouds = np.repeat(explosion_point[None, :], len(times), axis=0)
    clouds[:, 2] -= p.cloud_descent_speed * (times - explosion_time)
    sight = targets[None, :, :] - missiles[:, None, :]
    offset = clouds[:, None, :] - missiles[:, None, :]
    lam = np.einsum("ntj,ntj->nt", sight, offset) / np.einsum("ntj,ntj->nt", sight, sight)
    lam = np.clip(lam, 0.0, 1.0)
    closest = missiles[:, None, :] + lam[:, :, None] * sight
    return np.linalg.norm(clouds[:, None, :] - closest, axis=2).max(axis=1)


def bomb_metric(
    t: float,
    explosion_time: float,
    explosion_point: np.ndarray,
    p: Parameters,
    targets: np.ndarray,
) -> float:
    return float(
        distances_over_time(
            np.array([t]), explosion_time, explosion_point, p, targets
        )[0]
    )


def bomb_intervals(
    explosion_time: float,
    explosion_point: np.ndarray,
    p: Parameters,
    targets: np.ndarray,
    coarse_step: float,
) -> list[tuple[float, float]]:
    _, _, _, impact_time = fixed_states(p)
    start = float(explosion_time)
    end = min(start + p.cloud_lifetime, impact_time)
    if end <= start or explosion_point[2] < 0.0:
        return []
    grid = np.arange(start, end, coarse_step)
    if len(grid) == 0 or grid[-1] < end:
        grid = np.append(grid, end)
    values = (
        distances_over_time(grid, explosion_time, explosion_point, p, targets)
        - p.cloud_radius
    )
    roots: list[float] = []
    for a, b, fa, fb in zip(grid[:-1], grid[1:], values[:-1], values[1:]):
        if fa == 0.0:
            roots.append(float(a))
        elif fa * fb < 0.0:
            roots.append(
                float(
                    brentq(
                        lambda t: bomb_metric(
                            t, explosion_time, explosion_point, p, targets
                        )
                        - p.cloud_radius,
                        float(a),
                        float(b),
                        xtol=1e-10,
                    )
                )
            )
    cuts = [start, *roots, end]
    intervals: list[tuple[float, float]] = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        if (
            bomb_metric((a + b) / 2.0, explosion_time, explosion_point, p, targets)
            <= p.cloud_radius
        ):
            intervals.append((float(a), float(b)))
    return intervals


def merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + 1e-10:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def evaluate(
    y: np.ndarray, p: Parameters, targets: np.ndarray, coarse_step: float
) -> tuple[float, list[list[tuple[float, float]]], list[tuple[float, float]]]:
    if not feasible(y, p):
        return 0.0, [[], [], []], []
    state = decode(y, p)
    per_bomb = [
        bomb_intervals(te, point, p, targets, coarse_step)
        for te, point in zip(state["explosion_times"], state["explosion_points"])
    ]
    union = merge_intervals([interval for group in per_bomb for interval in group])
    return float(sum(b - a for a, b in union)), per_bomb, union


def miss_distance(y: np.ndarray, p: Parameters, targets: np.ndarray) -> float:
    if not feasible(y, p):
        return 1e4
    state = decode(y, p)
    penalties = []
    for te, point in zip(state["explosion_times"], state["explosion_points"]):
        end = min(float(te) + 12.0, fixed_states(p)[3])
        times = np.linspace(float(te), end, 81)
        minimum = float(distances_over_time(times, te, point, p, targets).min())
        penalties.append(max(0.0, minimum - p.cloud_radius))
    return float(sum(penalties))


def smooth_union_score(
    y: np.ndarray,
    p: Parameters,
    targets: np.ndarray,
    time_step: float = 0.08,
    transition_width: float = 0.45,
) -> float:
    """Differentiable approximation used only to guide the optimizer."""
    if not feasible(y, p):
        return -100.0
    state = decode(y, p)
    _, _, _, impact_time = fixed_states(p)
    end = min(25.0, impact_time)
    times = np.arange(0.0, end + 0.5 * time_step, time_step)
    probabilities = []
    for te, point in zip(state["explosion_times"], state["explosion_points"]):
        distances = distances_over_time(times, te, point, p, targets)
        active = (times >= te) & (times <= te + p.cloud_lifetime)
        z = np.clip((p.cloud_radius - distances) / transition_width, -40.0, 40.0)
        probability = 1.0 / (1.0 + np.exp(-z))
        probabilities.append(np.where(active, probability, 0.0))
    union_probability = 1.0 - np.prod(1.0 - np.vstack(probabilities), axis=0)
    return float(np.trapezoid(union_probability, times))


def optimize_basin(
    p: Parameters,
    seed: int,
    heading_bounds: tuple[float, float],
    maxiter: int,
    popsize: int,
) -> tuple[np.ndarray, float, list[float]]:
    targets = target_rims(p, 48)
    _, _, _, impact_time = fixed_states(p)
    max_delay = np.sqrt(2.0 * p.uav_initial[2] / p.gravity)
    bounds = [
        heading_bounds,
        (p.speed_min, p.speed_max),
        (0.0, impact_time - 2.0 * p.minimum_release_gap),
        (0.0, impact_time),
        (0.0, impact_time),
        (0.0, max_delay),
        (0.0, max_delay),
        (0.0, max_delay),
    ]
    history: list[float] = []

    def objective(y: np.ndarray) -> float:
        if not feasible(y, p):
            return 100.0
        return -smooth_union_score(y, p, targets)

    rng = np.random.default_rng(seed)
    lower = np.array([b[0] for b in bounds])
    upper = np.array([b[1] for b in bounds])
    population_size = max(40, popsize * len(bounds))
    initial = rng.uniform(lower, upper, size=(population_size, len(bounds)))
    heading_seed = np.clip(0.09, heading_bounds[0], heading_bounds[1])
    base = np.array([heading_seed, 140.0, 0.88, 0.0, 0.0, 0.05, 0.05, 0.05])
    initial[0] = np.clip(base, lower, upper)
    for i in range(1, min(12, population_size)):
        perturb = rng.normal(size=len(bounds)) * np.array(
            [0.04, 7.0, 0.5, 0.5, 0.5, 0.4, 0.4, 0.4]
        )
        initial[i] = np.clip(base + perturb, lower, upper)

    result = differential_evolution(
        objective,
        bounds=bounds,
        init=initial,
        seed=seed,
        maxiter=maxiter,
        popsize=popsize,
        tol=1e-6,
        polish=False,
        updating="immediate",
        workers=1,
        callback=lambda xk, convergence: history.append(-objective(xk)),
    )
    local = minimize(
        objective,
        result.x,
        method="Powell",
        bounds=bounds,
        options={"maxiter": 70, "xtol": 1e-5, "ftol": 1e-6},
    )
    best = local.x if local.fun < result.fun else result.x
    value = evaluate(best, p, target_rims(p, 180), coarse_step=0.025)[0]
    history.append(value)
    return best, value, history


def configure_plotting() -> None:
    available = {f.name for f in font_manager.fontManager.ttflist}
    chinese = next(
        (
            name
            for name in ("SimSun", "Microsoft YaHei", "SimHei", "Noto Sans CJK SC")
            if name in available
        ),
        "DejaVu Sans",
    )
    plt.rcParams.update(
        {
            "font.family": chinese,
            "font.size": 8,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 7.2,
            "axes.linewidth": 0.9,
            "pdf.fonttype": 42,
            "axes.unicode_minus": False,
        }
    )


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_figure(
    p: Parameters, y: np.ndarray, result: dict, histories: list[list[float]]
) -> None:
    configure_plotting()
    state = decode(y, p)
    targets = target_rims(p, 1440)
    start = float(state["explosion_times"].min())
    end = float(max(b for _, b in result["union_intervals_s"]) + 0.45)
    times = np.linspace(start, end, 1401)
    curves = [
        distances_over_time(times, te, point, p, targets)
        for te, point in zip(state["explosion_times"], state["explosion_points"])
    ]
    curve_rows = []
    for index, (te, curve) in enumerate(zip(state["explosion_times"], curves), 1):
        for t, d in zip(times, curve):
            curve_rows.append(
                {
                    "bomb": index,
                    "explosion_time_s": f"{te:.9f}",
                    "time_s": f"{t:.9f}",
                    "worst_distance_m": f"{d:.9f}",
                    "threshold_m": "10.000000000",
                }
            )
    write_csv(OUT / "optimal_margin_curves.csv", curve_rows)

    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.0), constrained_layout=True)
    colors = ("#3B6FB6", "#3A8F7B", "#B46A55")
    ax = axes[0]
    labels = ("全航向种子", "外向扇区种子", "内向扇区种子", "边界构造")
    plot_colors = (*colors, "#777777")
    for history, label, color in zip(histories, labels, plot_colors):
        marker = "o" if len(history) == 1 else None
        ax.plot(
            np.arange(1, len(history) + 1),
            history,
            lw=1.35,
            marker=marker,
            ms=3.5,
            label=label,
            color=color,
        )
    ax.set_xlabel("优化迭代次数")
    ax.set_ylabel("当前最优联合遮蔽时长 (s)")
    ax.grid(axis="y", color="#D9D9D9", lw=0.55)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False)
    ax.text(0.02, 0.96, "(a)", transform=ax.transAxes, va="top", fontfamily="Times New Roman")

    ax = axes[1]
    for index, (curve, color, te) in enumerate(
        zip(curves, colors, state["explosion_times"]), 1
    ):
        visible_curve = np.where(times >= te, curve, np.nan)
        ax.plot(times, visible_curve, color=color, lw=1.25, label=f"烟幕弹 {index}")
    ax.axhline(10.0, color="#555555", lw=1.0, ls="--", label="有效半径 10 m")
    for a, b in result["union_intervals_s"]:
        ax.axvspan(a, b, color="#777777", alpha=0.12, lw=0)
    ax.set_xlim(start, end)
    visible_max = max(float(curve.max()) for curve in curves)
    ax.set_ylim(0.0, min(35.0, visible_max + 1.0))
    ax.set_xlabel("雷达发现后的时间 $t$ (s)")
    ax.set_ylabel("最坏视线距离 $D_i(t)$ (m)")
    ax.grid(axis="y", color="#D9D9D9", lw=0.55)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncol=2)
    ax.text(0.02, 0.96, "(b)", transform=ax.transAxes, va="top", fontfamily="Times New Roman")
    fig.savefig(FIG / "q3_optimization_diagnostics.pdf", bbox_inches="tight", pad_inches=0.04)
    fig.savefig(
        FIG / "q3_optimization_diagnostics.png",
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.04,
    )
    plt.close(fig)


def solve(maxiter: int = 90, popsize: int = 8) -> dict:
    p = Parameters()
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    basins = (
        (2028, (0.0, 2.0 * np.pi), "global"),
        (2029, (0.0, 0.55), "outward"),
        (2030, (np.pi - 0.55, np.pi + 0.55), "inward"),
    )
    candidates = []
    histories = []
    run_rows = []
    for seed, bounds, name in basins:
        y, value, history = optimize_basin(p, seed, bounds, maxiter, popsize)
        candidates.append((y, value, name))
        histories.append(history)
        state = decode(y, p)
        run_rows.append(
            {
                "basin": name,
                "seed": seed,
                "heading_deg": f"{state['heading_deg']:.9f}",
                "speed_m_s": f"{state['speed']:.9f}",
                "release_1_s": f"{state['release_times'][0]:.9f}",
                "release_2_s": f"{state['release_times'][1]:.9f}",
                "release_3_s": f"{state['release_times'][2]:.9f}",
                "coarse_union_duration_s": f"{value:.9f}",
            }
        )

    # A targeted time-window construction supplements the generic population
    # search.  It staggers the three detonations so that the first two intervals
    # join and the third extends the trailing edge; this narrow basin is easily
    # missed by a smooth probability surrogate.
    constructed = np.array(
        [np.deg2rad(179.6474789164988), 139.99828,
         0.003, 2.699, 0.867, 3.611, 5.337, 6.041]
    )
    constructed_value = evaluate(
        constructed, p, target_rims(p, 360), coarse_step=0.02
    )[0]
    candidates.append((constructed, constructed_value, "window_stitching"))
    histories.append([constructed_value])
    constructed_state = decode(constructed, p)
    run_rows.append(
        {
            "basin": "window_stitching",
            "seed": "deterministic",
            "heading_deg": f"{constructed_state['heading_deg']:.9f}",
            "speed_m_s": f"{constructed_state['speed']:.9f}",
            "release_1_s": f"{constructed_state['release_times'][0]:.9f}",
            "release_2_s": f"{constructed_state['release_times'][1]:.9f}",
            "release_3_s": f"{constructed_state['release_times'][2]:.9f}",
            "coarse_union_duration_s": f"{constructed_value:.9f}",
        }
    )
    write_csv(OUT / "multistart.csv", run_rows)
    history_rows = [
        {
            "basin": name,
            "iteration": iteration,
            "best_union_duration_s": f"{value:.9f}",
        }
        for name, history in zip(
            [b[2] for b in basins] + ["window_stitching"], histories
        )
        for iteration, value in enumerate(history, 1)
    ]
    write_csv(OUT / "optimization_history.csv", history_rows)

    fine_targets = target_rims(p, 180)
    fine_candidates = [
        (y, evaluate(y, p, fine_targets, coarse_step=0.01)[0], name)
        for y, _, name in candidates
    ]
    best_y, _, best_basin = max(fine_candidates, key=lambda item: item[1])

    # Final coordinate-scale refinement in the selected basin.
    _, _, _, impact_time = fixed_states(p)
    max_delay = np.sqrt(2.0 * p.uav_initial[2] / p.gravity)
    lower = np.array([0.0, p.speed_min, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    upper = np.array(
        [
            2.0 * np.pi,
            p.speed_max,
            impact_time - 2.0 * p.minimum_release_gap,
            impact_time,
            impact_time,
            max_delay,
            max_delay,
            max_delay,
        ]
    )

    def fine_objective(y: np.ndarray) -> float:
        if np.any(y < lower) or np.any(y > upper) or not feasible(y, p):
            return 100.0
        return -smooth_union_score(
            y, p, fine_targets, time_step=0.05, transition_width=0.16
        )

    polished = minimize(
        fine_objective,
        best_y,
        method="Powell",
        bounds=list(zip(lower, upper)),
        options={"maxiter": 90, "xtol": 2e-6, "ftol": 2e-7},
    )
    refinement_candidates = [best_y]
    if polished.success and feasible(polished.x, p):
        refinement_candidates.append(polished.x)
    comparison_targets = target_rims(p, 1440)
    best_y = max(
        refinement_candidates,
        key=lambda y: evaluate(y, p, comparison_targets, coarse_step=0.01)[0],
    )

    final_targets = target_rims(p, 5760)
    union_duration, per_bomb, union = evaluate(
        best_y, p, final_targets, coarse_step=0.005
    )
    state = decode(best_y, p)

    convergence_rows = []
    for n_theta in (90, 180, 360, 720, 1440, 2880, 5760):
        value, _, intervals = evaluate(
            best_y, p, target_rims(p, n_theta), coarse_step=0.01
        )
        convergence_rows.append(
            {
                "n_theta": n_theta,
                "union_start_s": f"{intervals[0][0]:.10f}" if intervals else "",
                "union_end_s": f"{intervals[-1][1]:.10f}" if intervals else "",
                "union_duration_s": f"{value:.10f}",
            }
        )
    write_csv(OUT / "convergence.csv", convergence_rows)

    perturb_rows = []
    perturbations = [("baseline", np.zeros(8))]
    for index, step in ((0, 0.001), (1, 0.1), (2, 0.01), (3, 0.01), (4, 0.01)):
        for sign, suffix in ((-1.0, "minus"), (1.0, "plus")):
            delta = np.zeros(8)
            delta[index] = sign * step
            perturbations.append((f"x{index + 1}_{suffix}", delta))
    for index in (5, 6, 7):
        for sign, suffix in ((-1.0, "minus"), (1.0, "plus")):
            delta = np.zeros(8)
            delta[index] = sign * 0.01
            perturbations.append((f"delay_{index - 4}_{suffix}", delta))
    for name, delta in perturbations:
        trial = best_y + delta
        value = evaluate(trial, p, final_targets, coarse_step=0.01)[0]
        perturb_rows.append(
            {"case": name, "feasible": feasible(trial, p), "union_duration_s": f"{value:.10f}"}
        )
    write_csv(OUT / "local_perturbations.csv", perturb_rows)

    bomb_rows = []
    bombs = []
    for index in range(3):
        intervals = per_bomb[index]
        individual_duration = float(sum(b - a for a, b in intervals))
        bomb = {
            "bomb": index + 1,
            "release_time_s": float(state["release_times"][index]),
            "fuse_delay_s": float(state["delays"][index]),
            "explosion_time_s": float(state["explosion_times"][index]),
            "release_point_m": state["release_points"][index].tolist(),
            "explosion_point_m": state["explosion_points"][index].tolist(),
            "effective_intervals_s": [list(v) for v in intervals],
            "individual_duration_s": individual_duration,
        }
        bombs.append(bomb)
        bomb_rows.append(
            {
                "bomb": index + 1,
                "release_time_s": f"{bomb['release_time_s']:.9f}",
                "fuse_delay_s": f"{bomb['fuse_delay_s']:.9f}",
                "explosion_time_s": f"{bomb['explosion_time_s']:.9f}",
                "release_x_m": f"{bomb['release_point_m'][0]:.6f}",
                "release_y_m": f"{bomb['release_point_m'][1]:.6f}",
                "release_z_m": f"{bomb['release_point_m'][2]:.6f}",
                "explosion_x_m": f"{bomb['explosion_point_m'][0]:.6f}",
                "explosion_y_m": f"{bomb['explosion_point_m'][1]:.6f}",
                "explosion_z_m": f"{bomb['explosion_point_m'][2]:.6f}",
                "individual_duration_s": f"{individual_duration:.9f}",
            }
        )
    write_csv(OUT / "strategy.csv", bomb_rows)

    marginal_rows = []
    for removed in (None, 0, 1, 2):
        retained = [
            interval
            for bomb_index, group in enumerate(per_bomb)
            if removed is None or bomb_index != removed
            for interval in group
        ]
        retained_union = merge_intervals(retained)
        retained_duration = float(sum(b - a for a, b in retained_union))
        marginal_rows.append(
            {
                "case": "all_bombs" if removed is None else f"remove_bomb_{removed + 1}",
                "union_duration_s": f"{retained_duration:.10f}",
                "loss_from_all_s": f"{union_duration - retained_duration:.10f}",
            }
        )
    write_csv(OUT / "marginal_contributions.csv", marginal_rows)

    representative_rows = []
    for label, heading_deg, speed in (
        ("selected_robust_representative", 5.60, 125.0),
        ("same_duration_speed_boundary", 5.15, 140.0),
        ("nearby_heading_minus", 5.50, 125.0),
        ("nearby_heading_plus", 5.70, 125.0),
    ):
        trial = np.array(
            [np.deg2rad(heading_deg), speed, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        )
        duration, trial_per_bomb, _ = evaluate(
            trial, p, final_targets, coarse_step=0.005
        )
        overlap = 0.0
        if trial_per_bomb[0] and trial_per_bomb[1]:
            overlap = max(
                0.0,
                min(trial_per_bomb[0][0][1], trial_per_bomb[1][0][1])
                - max(trial_per_bomb[0][0][0], trial_per_bomb[1][0][0]),
            )
        representative_rows.append(
            {
                "case": label,
                "heading_deg": f"{heading_deg:.6f}",
                "speed_m_s": f"{speed:.6f}",
                "union_duration_s": f"{duration:.10f}",
                "bomb_1_2_overlap_s": f"{overlap:.10f}",
            }
        )
    write_csv(OUT / "representative_solutions.csv", representative_rows)

    result = {
        "parameters": asdict(p),
        "shared_uav_strategy": {
            "heading_rad": float(state["heading_rad"]),
            "heading_deg_from_positive_x_counterclockwise": float(state["heading_deg"]),
            "speed_m_s": float(state["speed"]),
            "velocity_m_s": state["uav_velocity"].tolist(),
        },
        "bombs": bombs,
        "union_intervals_s": [list(v) for v in union],
        "union_duration_s": union_duration,
        "selected_basin": best_basin,
        "selection_rule": (
            "maximize exact interval-union duration; use staggered detonation "
            "windows to join the first two intervals and extend the trailing edge"
        ),
        "verification": {
            "release_gaps_s": state["release_gaps"].tolist(),
            "minimum_release_gap_s": p.minimum_release_gap,
            "all_release_gaps_feasible": bool(
                np.all(state["release_gaps"] >= p.minimum_release_gap - 1e-10)
            ),
            "all_explosions_above_ground": bool(
                np.all(state["explosion_points"][:, 2] >= 0.0)
            ),
            "n_theta": 5760,
            "time_root_scan_step_s": 0.005,
            "seeds": [b[0] for b in basins],
        },
    }
    with (OUT / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    make_figure(p, best_y, result, histories)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--maxiter", type=int, default=90)
    parser.add_argument("--popsize", type=int, default=8)
    args = parser.parse_args()
    print(json.dumps(solve(args.maxiter, args.popsize), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
