"""Question 2: optimize one FY1 smoke bomb against missile M1.

The primary objective is the total time for which every sight segment from M1
to the complete cylindrical target intersects the effective smoke sphere.
Decision variables are heading, UAV speed, explosion time and fuse delay; the
release time and the two spatial points are recovered from these variables.
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
OUT = ROOT / "results" / "q2"
FIG = ROOT / "figures" / "q2"


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


def fixed_states(p: Parameters) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    missile_initial = np.asarray(p.missile_initial, dtype=float)
    missile_velocity = -p.missile_speed * missile_initial / np.linalg.norm(missile_initial)
    uav_initial = np.asarray(p.uav_initial, dtype=float)
    impact_time = float(np.linalg.norm(missile_initial) / p.missile_speed)
    return missile_initial, missile_velocity, uav_initial, impact_time


def target_rims(p: Parameters, n_theta: int) -> np.ndarray:
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


def decode(x: np.ndarray, p: Parameters) -> dict[str, np.ndarray | float]:
    """Decode [heading, speed, explosion time, fuse delay]."""
    heading, speed, explosion_time, delay = map(float, x)
    direction = np.array([np.cos(heading), np.sin(heading), 0.0])
    uav_velocity = speed * direction
    release_time = explosion_time - delay
    _, _, uav_initial, _ = fixed_states(p)
    release_point = uav_initial + uav_velocity * release_time
    explosion_point = uav_initial + uav_velocity * explosion_time
    explosion_point[2] -= 0.5 * p.gravity * delay**2
    return {
        "heading_rad": heading,
        "heading_deg": float(np.degrees(heading) % 360.0),
        "speed": speed,
        "release_time": release_time,
        "fuse_delay": delay,
        "explosion_time": explosion_time,
        "uav_velocity": uav_velocity,
        "release_point": release_point,
        "explosion_point": explosion_point,
    }


def feasible(x: np.ndarray, p: Parameters) -> bool:
    state = decode(x, p)
    _, _, _, impact_time = fixed_states(p)
    return bool(
        p.speed_min <= state["speed"] <= p.speed_max
        and state["release_time"] >= 0.0
        and state["fuse_delay"] >= 0.0
        and state["explosion_time"] <= impact_time
        and state["explosion_point"][2] >= 0.0
    )


def distances_over_time(
    times: np.ndarray, x: np.ndarray, p: Parameters, targets: np.ndarray
) -> np.ndarray:
    state = decode(x, p)
    missile_initial, missile_velocity, _, _ = fixed_states(p)
    missiles = missile_initial[None, :] + times[:, None] * missile_velocity[None, :]
    clouds = np.repeat(state["explosion_point"][None, :], len(times), axis=0)
    clouds[:, 2] -= p.cloud_descent_speed * (times - state["explosion_time"])
    sight = targets[None, :, :] - missiles[:, None, :]
    offset = clouds[:, None, :] - missiles[:, None, :]
    lam = np.einsum("ntj,ntj->nt", sight, offset) / np.einsum("ntj,ntj->nt", sight, sight)
    lam = np.clip(lam, 0.0, 1.0)
    closest = missiles[:, None, :] + lam[:, :, None] * sight
    return np.linalg.norm(clouds[:, None, :] - closest, axis=2).max(axis=1)


def metric(t: float, x: np.ndarray, p: Parameters, targets: np.ndarray) -> float:
    return float(distances_over_time(np.array([t]), x, p, targets)[0])


def effective_intervals(
    x: np.ndarray,
    p: Parameters,
    targets: np.ndarray,
    coarse_step: float,
) -> list[tuple[float, float]]:
    if not feasible(x, p):
        return []
    state = decode(x, p)
    _, _, _, impact_time = fixed_states(p)
    start = float(state["explosion_time"])
    end = min(start + p.cloud_lifetime, impact_time)
    if end <= start:
        return []
    grid = np.arange(start, end, coarse_step)
    if len(grid) == 0 or grid[-1] < end:
        grid = np.append(grid, end)
    values = distances_over_time(grid, x, p, targets) - p.cloud_radius
    roots: list[float] = []
    for a, b, fa, fb in zip(grid[:-1], grid[1:], values[:-1], values[1:]):
        if fa == 0.0:
            roots.append(float(a))
        elif fa * fb < 0.0:
            roots.append(
                float(
                    brentq(
                        lambda t: metric(t, x, p, targets) - p.cloud_radius,
                        float(a),
                        float(b),
                        xtol=1e-10,
                    )
                )
            )
    cuts = [start, *roots, end]
    intervals: list[tuple[float, float]] = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        if metric((a + b) / 2.0, x, p, targets) <= p.cloud_radius:
            intervals.append((float(a), float(b)))
    return intervals


def duration(x: np.ndarray, p: Parameters, targets: np.ndarray, coarse_step: float) -> float:
    return float(sum(b - a for a, b in effective_intervals(x, p, targets, coarse_step)))


def optimize_once(p: Parameters, seed: int, maxiter: int, popsize: int) -> tuple[np.ndarray, float, list[float]]:
    targets = target_rims(p, 72)
    _, _, _, impact_time = fixed_states(p)
    max_delay = np.sqrt(2.0 * p.uav_initial[2] / p.gravity)
    history: list[float] = []

    def objective(x: np.ndarray) -> float:
        if not feasible(x, p):
            state = decode(x, p)
            penalty = 100.0 * max(0.0, -float(state["release_time"]))
            penalty += 100.0 * max(0.0, -float(state["explosion_point"][2]))
            return 50.0 + penalty
        state = decode(x, p)
        _, _, _, impact_time = fixed_states(p)
        start = float(state["explosion_time"])
        end = min(start + p.cloud_lifetime, impact_time)
        probe_times = np.linspace(start, end, 121)
        minimum_distance = float(distances_over_time(probe_times, x, p, targets).min())
        # A pure duration objective is flat whenever a trial cloud misses every
        # sightline.  The miss distance supplies a continuous search direction
        # until the first feasible interval is reached.
        if minimum_distance > p.cloud_radius:
            return (minimum_distance - p.cloud_radius) / 100.0
        return -duration(x, p, targets, coarse_step=0.08)

    rng = np.random.default_rng(seed)
    population_size = max(5, popsize * 4)
    lower = np.array([0.0, p.speed_min, 0.0, 0.0])
    upper = np.array([2.0 * np.pi, p.speed_max, impact_time, max_delay])
    initial = rng.uniform(lower, upper, size=(population_size, 4))
    q1 = np.array([np.pi, 120.0, 5.1, 3.6])
    initial[0] = q1
    for i, scales in enumerate((0.02, 0.05, 0.10, 0.20), start=1):
        initial[i] = np.clip(
            q1 + rng.normal(size=4) * np.array([scales, 10.0 * scales, 4.0 * scales, 2.0 * scales]),
            lower,
            upper,
        )

    result = differential_evolution(
        objective,
        bounds=[(0.0, 2.0 * np.pi), (p.speed_min, p.speed_max), (0.0, impact_time), (0.0, max_delay)],
        constraints=(),
        init=initial,
        seed=seed,
        maxiter=maxiter,
        popsize=popsize,
        tol=2e-7,
        polish=False,
        updating="immediate",
        workers=1,
        callback=lambda xk, convergence: history.append(-objective(xk)),
    )
    local = minimize(
        objective,
        result.x,
        method="Nelder-Mead",
        options={"maxiter": 1800, "xatol": 2e-8, "fatol": 2e-9},
    )
    best_x = local.x if local.fun < result.fun else result.x
    return best_x, -float(min(local.fun, result.fun)), history


def refine_outward_basin(p: Parameters) -> tuple[np.ndarray, float, list[float]]:
    """Independently refine the +x heading basin found by geometric screening."""
    targets = target_rims(p, 360)
    history: list[float] = []
    lower = np.array([-0.20, p.speed_min, 0.0, 0.0])
    upper = np.array([0.30, p.speed_max, 5.0, 2.0])

    def to_x(y: np.ndarray) -> np.ndarray:
        heading, speed, release_time, delay = y
        return np.array([heading, speed, release_time + delay, delay])

    def objective(y: np.ndarray) -> float:
        if np.any(y < lower) or np.any(y > upper):
            return 50.0 + float(np.maximum(lower - y, 0.0).sum() + np.maximum(y - upper, 0.0).sum())
        x = to_x(y)
        value = duration(x, p, targets, coarse_step=0.01)
        if value > 0.0:
            return -value
        state = decode(x, p)
        probe = np.linspace(float(state["explosion_time"]), float(state["explosion_time"]) + 8.0, 121)
        return float(distances_over_time(probe, x, p, targets).min() - p.cloud_radius) / 100.0

    initial = np.array([0.10, 135.0, 1.00, 0.05])

    def callback(yk: np.ndarray) -> None:
        history.append(max(0.0, -objective(yk)))

    result = minimize(
        objective,
        initial,
        method="Nelder-Mead",
        callback=callback,
        options={"maxiter": 2500, "xatol": 1e-10, "fatol": 1e-10},
    )
    polished = result.x.copy()
    if 0.0 <= polished[3] < 1e-8:
        polished[3] = 0.0

    def boundary_objective(z: np.ndarray) -> float:
        y = np.array([z[0], p.speed_max, z[1], z[2]])
        return objective(y)

    boundary = minimize(
        boundary_objective,
        np.array([polished[0], polished[2], polished[3]]),
        method="Nelder-Mead",
        callback=lambda zk: history.append(max(0.0, -boundary_objective(zk))),
        options={"maxiter": 1800, "xatol": 1e-10, "fatol": 1e-10},
    )
    boundary_y = np.array([boundary.x[0], p.speed_max, boundary.x[1], boundary.x[2]])
    if boundary.fun < result.fun:
        polished = boundary_y
    x = to_x(polished)
    return x, duration(x, p, targets, coarse_step=0.005), history


def configure_plotting() -> None:
    available = {f.name for f in font_manager.fontManager.ttflist}
    chinese = next(
        (name for name in ("SimSun", "Microsoft YaHei", "SimHei", "Noto Sans CJK SC") if name in available),
        "DejaVu Sans",
    )
    plt.rcParams.update(
        {
            "font.family": chinese,
            "font.size": 8,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 7.5,
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


def make_figure(p: Parameters, x: np.ndarray, result: dict, histories: list[list[float]]) -> None:
    configure_plotting()
    state = decode(x, p)
    targets = target_rims(p, 1440)
    _, _, _, impact_time = fixed_states(p)
    times = np.linspace(
        float(state["explosion_time"]),
        min(float(state["explosion_time"]) + p.cloud_lifetime, impact_time),
        1601,
    )
    curve = distances_over_time(times, x, p, targets)
    rows = [
        {"time_s": f"{t:.9f}", "worst_distance_m": f"{d:.9f}", "threshold_m": "10.000000000"}
        for t, d in zip(times, curve)
    ]
    write_csv(OUT / "optimal_margin_curve.csv", rows)

    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.0), constrained_layout=True)
    ax = axes[0]
    for i, history in enumerate(histories, 1):
        label = f"种子 {i}" if i <= 3 else "外向盆地细化"
        ax.plot(np.arange(1, len(history) + 1), history, lw=1.2, label=label)
    ax.set_xlim(0, min(120, max(len(history) for history in histories)))
    ax.set_xlabel("优化迭代次数")
    ax.set_ylabel("当前最优遮蔽时长 (s)")
    ax.grid(axis="y", color="#D9D9D9", lw=0.55)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False)
    ax.text(0.02, 0.96, "(a)", transform=ax.transAxes, va="top", fontfamily="Times New Roman")

    ax = axes[1]
    ax.plot(times, curve, color="#3B6FB6", lw=1.8, label="完整圆柱最坏视线")
    ax.axhline(10.0, color="#B46A55", lw=1.1, ls="--", label="有效半径 10 m")
    for a, b in result["full_target"]["intervals"]:
        ax.axvspan(a, b, color="#3B6FB6", alpha=0.13, lw=0)
    display_end = result["full_target"]["intervals"][-1][1] + 0.5
    ax.set_xlim(float(state["explosion_time"]), display_end)
    visible = curve[times <= display_end]
    ax.set_ylim(max(0.0, float(visible.min()) - 0.8), float(visible.max()) + 0.8)
    ax.set_xlabel("雷达发现后的时间 $t$ (s)")
    ax.set_ylabel("最坏视线距离 $D(t)$ (m)")
    ax.grid(axis="y", color="#D9D9D9", lw=0.55)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False)
    ax.text(0.02, 0.96, "(b)", transform=ax.transAxes, va="top", fontfamily="Times New Roman")
    fig.savefig(FIG / "q2_optimization_diagnostics.pdf", bbox_inches="tight", pad_inches=0.04)
    fig.savefig(FIG / "q2_optimization_diagnostics.png", dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def solve(maxiter: int = 90, popsize: int = 11) -> dict:
    p = Parameters()
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    seeds = (2025, 2026, 2027)
    candidates: list[tuple[np.ndarray, float]] = []
    histories: list[list[float]] = []
    run_rows: list[dict] = []
    for seed in seeds:
        x, approx_duration, history = optimize_once(p, seed, maxiter=maxiter, popsize=popsize)
        candidates.append((x, approx_duration))
        histories.append(history)
        run_rows.append(
            {
                "seed": seed,
                "heading_deg": f"{np.degrees(x[0]) % 360.0:.9f}",
                "speed_m_s": f"{x[1]:.9f}",
                "explosion_time_s": f"{x[2]:.9f}",
                "fuse_delay_s": f"{x[3]:.9f}",
                "coarse_duration_s": f"{approx_duration:.9f}",
            }
        )
    outward_x, outward_duration, outward_history = refine_outward_basin(p)
    candidates.append((outward_x, outward_duration))
    histories.append(outward_history)
    run_rows.append(
        {
            "seed": "outward_geometric_start",
            "heading_deg": f"{np.degrees(outward_x[0]) % 360.0:.9f}",
            "speed_m_s": f"{outward_x[1]:.9f}",
            "explosion_time_s": f"{outward_x[2]:.9f}",
            "fuse_delay_s": f"{outward_x[3]:.9f}",
            "coarse_duration_s": f"{outward_duration:.9f}",
        }
    )
    write_csv(OUT / "multistart.csv", run_rows)
    history_rows = [
        {"seed": seed, "iteration": iteration, "best_duration_s": f"{value:.9f}"}
        for seed, history in zip((*seeds, "outward_geometric_start"), histories)
        for iteration, value in enumerate(history, 1)
    ]
    write_csv(OUT / "optimization_history.csv", history_rows)

    fine_targets = target_rims(p, 5760)
    fine = [(x, duration(x, p, fine_targets, coarse_step=0.01)) for x, _ in candidates]
    best_x, best_duration = max(fine, key=lambda item: item[1])
    state = decode(best_x, p)
    intervals = effective_intervals(best_x, p, fine_targets, coarse_step=0.005)
    best_duration = float(sum(b - a for a, b in intervals))

    convergence_rows: list[dict] = []
    for n_theta in (90, 180, 360, 720, 1440, 2880, 5760):
        ints = effective_intervals(best_x, p, target_rims(p, n_theta), coarse_step=0.01)
        convergence_rows.append(
            {
                "n_theta": n_theta,
                "entry_time_s": f"{ints[0][0]:.10f}" if ints else "",
                "exit_time_s": f"{ints[-1][1]:.10f}" if ints else "",
                "duration_s": f"{sum(b-a for a,b in ints):.10f}",
            }
        )
    write_csv(OUT / "convergence.csv", convergence_rows)

    boundary_rows: list[dict] = []
    perturbations = (
        ("baseline", 0.0, 0.0, 0.0, 0.0),
        ("heading_minus", -0.001, 0.0, 0.0, 0.0),
        ("heading_plus", 0.001, 0.0, 0.0, 0.0),
        ("speed_minus", 0.0, -0.1, 0.0, 0.0),
        ("release_minus", 0.0, 0.0, -0.01, 0.0),
        ("release_plus", 0.0, 0.0, 0.01, 0.0),
        ("delay_minus", 0.0, 0.0, 0.0, -0.01),
        ("delay_plus", 0.0, 0.0, 0.0, 0.01),
    )
    for name, heading_add, speed_add, release_add, delay_add in perturbations:
        trial = best_x.copy()
        trial[0] += heading_add
        trial[1] += speed_add
        trial[2] += release_add + delay_add
        trial[3] += delay_add
        boundary_rows.append(
            {
                "case": name,
                "heading_rad": f"{trial[0]:.9f}",
                "speed_m_s": f"{trial[1]:.6f}",
                "release_time_s": f"{trial[2]-trial[3]:.6f}",
                "fuse_delay_s": f"{trial[3]:.6f}",
                "duration_s": f"{duration(trial, p, fine_targets, coarse_step=0.01):.10f}",
            }
        )
    write_csv(OUT / "active_bound_checks.csv", boundary_rows)

    result = {
        "parameters": asdict(p),
        "decision_variables": {
            "heading_rad": float(state["heading_rad"]),
            "heading_deg_from_positive_x_counterclockwise": float(state["heading_deg"]),
            "speed_m_s": float(state["speed"]),
            "release_time_s": float(state["release_time"]),
            "fuse_delay_s": float(state["fuse_delay"]),
            "explosion_time_s": float(state["explosion_time"]),
        },
        "uav_velocity_m_s": state["uav_velocity"].tolist(),
        "release_point_m": state["release_point"].tolist(),
        "explosion_point_m": state["explosion_point"].tolist(),
        "full_target": {
            "intervals": [list(v) for v in intervals],
            "duration_s": best_duration,
            "n_theta": 5760,
            "time_root_scan_step_s": 0.005,
        },
        "verification": {
            "independent_seeds": list(seeds),
            "multistart_file": "results/q2/multistart.csv",
            "optimization_history_file": "results/q2/optimization_history.csv",
            "convergence_file": "results/q2/convergence.csv",
            "curve_file": "results/q2/optimal_margin_curve.csv",
            "active_bound_check_file": "results/q2/active_bound_checks.csv",
            "release_nonnegative": bool(state["release_time"] >= 0.0),
            "explosion_above_ground": bool(state["explosion_point"][2] >= 0.0),
        },
    }
    with (OUT / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    make_figure(p, best_x, result, histories)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--maxiter", type=int, default=90)
    parser.add_argument("--popsize", type=int, default=11)
    args = parser.parse_args()
    print(json.dumps(solve(args.maxiter, args.popsize), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
