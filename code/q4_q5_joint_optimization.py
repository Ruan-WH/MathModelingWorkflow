"""Questions 4 and 5: multi-UAV smoke-screen coordination.

The optimization and the final verifier use the same finite-segment geometry as
Questions 1--3.  A hierarchical search first selects productive UAV--missile
pairs, then optimizes continuous flight/drop variables inside each assignment.
The final score is computed from exact event intervals; overlaps are merged.
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
from scipy.optimize import brentq


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"


@dataclass(frozen=True)
class Parameters:
    missile_speed: float = 300.0
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


P = Parameters()
MISSILES = {
    "M1": np.array((20000.0, 0.0, 2000.0)),
    "M2": np.array((19000.0, 600.0, 2100.0)),
    "M3": np.array((18000.0, -600.0, 1900.0)),
}
UAVS = {
    "FY1": np.array((17800.0, 0.0, 1800.0)),
    "FY2": np.array((12000.0, 1400.0, 1400.0)),
    "FY3": np.array((6000.0, -3000.0, 700.0)),
    "FY4": np.array((11000.0, 2000.0, 1800.0)),
    "FY5": np.array((13000.0, -2000.0, 1300.0)),
}


@dataclass(frozen=True)
class BombPlan:
    uav: str
    missile: str
    bomb: int
    heading_deg: float
    speed: float
    release_time: float
    delay: float


Q4_PLANS = [
    # FY1 uses the stronger outward-flight basin found in Question 2.
    BombPlan("FY1", "M1", 1, 5.112023148207133, 140.0, 0.878619601412594, 0.053112383643653),
    BombPlan("FY2", "M1", 1, 306.1909375490924, 136.85323, 8.55122, 3.98572),
    BombPlan("FY3", "M1", 1, 122.4743123715745, 92.96017, 31.73266, 7.64581),
]

# The nonzero allocation found by pair screening.  Blank template rows are
# intentionally left unused rather than filled with zero-contribution bombs.
Q5_PLANS = [
    BombPlan("FY1", "M1", 1, 179.6474789164988, 139.99828, 0.003, 3.611),
    BombPlan("FY1", "M1", 2, 179.6474789164988, 139.99828, 3.702, 5.337),
    BombPlan("FY1", "M1", 3, 179.6474789164988, 139.99828, 5.569, 6.041),
    BombPlan("FY2", "M2", 1, 293.6618167855297, 140.0, 5.767995934019878, 1.759839527145142),
    BombPlan("FY2", "M2", 2, 293.6618167855297, 140.0, 6.867995934019878, 0.759839527145142),
    BombPlan("FY3", "M2", 1, 86.80310596231972, 133.4, 24.29, 0.3),
    BombPlan("FY4", "M2", 1, 237.6055976407524, 81.6, 12.54, 11.86),
    BombPlan("FY5", "M3", 1, 116.3775391070642, 140.0, 11.808152214609857, 1.040372307813712),
]


def target_rims(n_theta: int) -> np.ndarray:
    angle = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    x0, y0 = P.target_center_xy
    circles = [
        np.column_stack((x0 + P.target_radius * np.cos(angle),
                         y0 + P.target_radius * np.sin(angle),
                         np.full_like(angle, z)))
        for z in (0.0, P.target_height)
    ]
    extras = np.array([[x0, y0, 0.0], [x0, y0, P.target_height],
                       [x0, y0, P.target_height / 2.0]])
    return np.vstack((*circles, extras))


def missile_state(name: str) -> tuple[np.ndarray, np.ndarray, float]:
    initial = MISSILES[name]
    velocity = -P.missile_speed * initial / np.linalg.norm(initial)
    return initial, velocity, float(np.linalg.norm(initial) / P.missile_speed)


def plan_state(plan: BombPlan) -> dict:
    heading = np.deg2rad(plan.heading_deg)
    direction = np.array((np.cos(heading), np.sin(heading), 0.0))
    velocity = plan.speed * direction
    initial = UAVS[plan.uav]
    explosion_time = plan.release_time + plan.delay
    release = initial + velocity * plan.release_time
    explosion = initial + velocity * explosion_time
    explosion[2] -= 0.5 * P.gravity * plan.delay**2
    return {
        "velocity": velocity,
        "explosion_time": explosion_time,
        "release_point": release,
        "explosion_point": explosion,
    }


def feasible(plan: BombPlan) -> bool:
    state = plan_state(plan)
    _, _, impact_time = missile_state(plan.missile)
    return bool(
        0.0 <= plan.heading_deg < 360.0
        and P.speed_min <= plan.speed <= P.speed_max
        and plan.release_time >= 0.0
        and plan.delay >= 0.0
        and state["explosion_time"] <= impact_time
        and state["explosion_point"][2] >= 0.0
    )


def distances_over_time(times: np.ndarray, plan: BombPlan, targets: np.ndarray) -> np.ndarray:
    state = plan_state(plan)
    missile_initial, missile_velocity, _ = missile_state(plan.missile)
    output = np.empty(len(times), dtype=float)
    # Chunking keeps the 5760-angle final verification below 100 MB.
    for start in range(0, len(times), 64):
        stop = min(start + 64, len(times))
        t = times[start:stop]
        missiles = missile_initial[None, :] + t[:, None] * missile_velocity[None, :]
        clouds = np.repeat(state["explosion_point"][None, :], len(t), axis=0)
        clouds[:, 2] -= P.cloud_descent_speed * (t - state["explosion_time"])
        sight = targets[None, :, :] - missiles[:, None, :]
        offset = clouds[:, None, :] - missiles[:, None, :]
        lam = np.einsum("ntj,ntj->nt", sight, offset) / np.einsum("ntj,ntj->nt", sight, sight)
        lam = np.clip(lam, 0.0, 1.0)
        closest = missiles[:, None, :] + lam[:, :, None] * sight
        output[start:stop] = np.linalg.norm(clouds[:, None, :] - closest, axis=2).max(axis=1)
    return output


def metric(t: float, plan: BombPlan, targets: np.ndarray) -> float:
    return float(distances_over_time(np.array([t]), plan, targets)[0])


def intervals(plan: BombPlan, targets: np.ndarray, step: float) -> list[tuple[float, float]]:
    if not feasible(plan):
        return []
    state = plan_state(plan)
    _, _, impact_time = missile_state(plan.missile)
    start = float(state["explosion_time"])
    end = min(start + P.cloud_lifetime, impact_time)
    grid = np.arange(start, end, step)
    if len(grid) == 0 or grid[-1] < end:
        grid = np.append(grid, end)
    values = distances_over_time(grid, plan, targets) - P.cloud_radius
    roots: list[float] = []
    for a, b, fa, fb in zip(grid[:-1], grid[1:], values[:-1], values[1:]):
        if fa == 0.0:
            roots.append(float(a))
        elif fa * fb < 0.0:
            roots.append(float(brentq(lambda t: metric(t, plan, targets) - P.cloud_radius,
                                      float(a), float(b), xtol=1e-10)))
    cuts = [start, *roots, end]
    return [(float(a), float(b)) for a, b in zip(cuts[:-1], cuts[1:])
            if metric((a + b) / 2.0, plan, targets) <= P.cloud_radius]


def merge_intervals(groups: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
    ordered = sorted(interval for group in groups for interval in group)
    if not ordered:
        return []
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        if start <= merged[-1][1] + 1e-9:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def duration(items: list[tuple[float, float]]) -> float:
    return float(sum(end - start for start, end in items))


def validate_release_gaps(plans: list[BombPlan]) -> dict[str, list[float]]:
    checks: dict[str, list[float]] = {}
    for uav in UAVS:
        times = sorted(p.release_time for p in plans if p.uav == uav)
        checks[uav] = np.diff(times).tolist() if len(times) > 1 else []
    return checks


def evaluate_case(plans: list[BombPlan], n_theta: int = 5760, step: float = 0.005) -> dict:
    targets = target_rims(n_theta)
    bomb_rows = []
    grouped: dict[str, list[list[tuple[float, float]]]] = {name: [] for name in MISSILES}
    for plan in plans:
        state = plan_state(plan)
        active = intervals(plan, targets, step)
        grouped[plan.missile].append(active)
        bomb_rows.append({
            **asdict(plan),
            "explosion_time": float(state["explosion_time"]),
            "velocity": state["velocity"].tolist(),
            "release_point": state["release_point"].tolist(),
            "explosion_point": state["explosion_point"].tolist(),
            "intervals": [list(x) for x in active],
            "duration": duration(active),
            "feasible": feasible(plan),
        })
    missile_intervals = {name: merge_intervals(groups) for name, groups in grouped.items()}
    totals = {name: duration(items) for name, items in missile_intervals.items()}
    gaps = validate_release_gaps(plans)
    return {
        "parameters": asdict(P),
        "bombs": bomb_rows,
        "missile_intervals": {k: [list(x) for x in v] for k, v in missile_intervals.items()},
        "missile_durations": totals,
        "objective_sum_s": float(sum(totals.values())),
        "release_gaps_s": gaps,
        "all_release_gaps_feasible": all(all(g >= P.minimum_release_gap - 1e-9 for g in v) for v in gaps.values()),
        "all_bombs_feasible": all(row["feasible"] for row in bomb_rows),
        "n_theta": n_theta,
        "time_root_scan_step_s": step,
        "method": "pair screening + grouped continuous search + exact interval-union verification",
    }


def configure_plotting() -> None:
    available = {f.name for f in font_manager.fontManager.ttflist}
    chinese = next((name for name in ("SimSun", "Microsoft YaHei", "SimHei") if name in available), "DejaVu Sans")
    plt.rcParams.update({"font.family": chinese, "font.size": 8, "axes.labelsize": 9,
                         "xtick.labelsize": 8, "ytick.labelsize": 8,
                         "legend.fontsize": 7.2, "axes.linewidth": 0.9,
                         "pdf.fonttype": 42, "axes.unicode_minus": False})


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save_outputs(tag: str, result: dict) -> None:
    out = RESULTS / tag
    out.mkdir(parents=True, exist_ok=True)
    with (out / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    rows = []
    for b in result["bombs"]:
        rp, ep = b["release_point"], b["explosion_point"]
        rows.append({
            "uav": b["uav"], "missile": b["missile"], "bomb": b["bomb"],
            "heading_deg": b["heading_deg"], "speed_m_s": b["speed"],
            "release_time_s": b["release_time"], "delay_s": b["delay"],
            "explosion_time_s": b["explosion_time"],
            "release_x_m": rp[0], "release_y_m": rp[1], "release_z_m": rp[2],
            "explosion_x_m": ep[0], "explosion_y_m": ep[1], "explosion_z_m": ep[2],
            "individual_duration_s": b["duration"],
        })
    write_csv(out / "strategy.csv", rows)
    interval_rows = [{"missile": m, "start_s": a, "end_s": b, "duration_s": b-a}
                     for m, groups in result["missile_intervals"].items() for a, b in groups]
    write_csv(out / "coverage_intervals.csv", interval_rows)


def make_figure(tag: str, result: dict) -> None:
    configure_plotting()
    out = FIGURES / tag
    out.mkdir(parents=True, exist_ok=True)
    if tag == "q4":
        fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.9), constrained_layout=True)
        names = [b["uav"] for b in result["bombs"]]
        vals = [b["duration"] for b in result["bombs"]]
        axes[0].bar(names, vals, color=["#3B6FB6", "#3A8F7B", "#B46A55"], width=0.58)
        axes[0].set_ylabel("单弹有效遮蔽时长 (s)")
        axes[0].grid(axis="y", color="#D9D9D9", lw=0.55)
        axes[0].spines[["top", "right"]].set_visible(False)
        axes[0].text(0.02, 0.96, "(a)", transform=axes[0].transAxes, va="top", fontfamily="Times New Roman")
        ax = axes[1]
        for idx, b in enumerate(result["bombs"]):
            for a, c in b["intervals"]:
                ax.barh(idx, c-a, left=a, height=0.42, color=["#3B6FB6", "#3A8F7B", "#B46A55"][idx])
        ax.set_yticks(range(len(names)), names)
        ax.set_xlabel("雷达发现后的时间 $t$ (s)")
        ax.set_ylabel("执行无人机")
        ax.grid(axis="x", color="#D9D9D9", lw=0.55)
        ax.spines[["top", "right"]].set_visible(False)
        ax.text(0.02, 0.96, "(b)", transform=ax.transAxes, va="top", fontfamily="Times New Roman")
    else:
        fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.1), constrained_layout=True)
        missiles = list(MISSILES)
        vals = [result["missile_durations"][m] for m in missiles]
        axes[0].bar(missiles, vals, color=["#3B6FB6", "#3A8F7B", "#B46A55"], width=0.58)
        axes[0].set_ylabel("联合有效遮蔽时长 (s)")
        axes[0].grid(axis="y", color="#D9D9D9", lw=0.55)
        axes[0].spines[["top", "right"]].set_visible(False)
        axes[0].text(0.02, 0.96, "(a)", transform=axes[0].transAxes, va="top", fontfamily="Times New Roman")
        ax = axes[1]
        colors = {"M1": "#3B6FB6", "M2": "#3A8F7B", "M3": "#B46A55"}
        for idx, m in enumerate(missiles):
            for a, b in result["missile_intervals"][m]:
                ax.barh(idx, b-a, left=a, height=0.42, color=colors[m])
        ax.set_yticks(range(3), missiles)
        ax.set_xlabel("雷达发现后的时间 $t$ (s)")
        ax.set_ylabel("来袭导弹")
        ax.grid(axis="x", color="#D9D9D9", lw=0.55)
        ax.spines[["top", "right"]].set_visible(False)
        ax.text(0.02, 0.96, "(b)", transform=ax.transAxes, va="top", fontfamily="Times New Roman")
    fig.savefig(out / f"{tag}_coordination_diagnostics.pdf", bbox_inches="tight", pad_inches=0.04)
    fig.savefig(out / f"{tag}_coordination_diagnostics.png", dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def solve(n_theta: int = 5760, step: float = 0.005) -> dict:
    q4 = evaluate_case(Q4_PLANS, n_theta=n_theta, step=step)
    q5 = evaluate_case(Q5_PLANS, n_theta=n_theta, step=step)
    save_outputs("q4", q4)
    save_outputs("q5", q5)
    make_figure("q4", q4)
    make_figure("q5", q5)
    return {"q4": q4, "q5": q5}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-theta", type=int, default=5760)
    parser.add_argument("--step", type=float, default=0.005)
    args = parser.parse_args()
    result = solve(args.n_theta, args.step)
    compact = {k: {"objective_sum_s": v["objective_sum_s"],
                   "missile_durations": v["missile_durations"],
                   "all_bombs_feasible": v["all_bombs_feasible"],
                   "all_release_gaps_feasible": v["all_release_gaps_feasible"]}
               for k, v in result.items()}
    print(json.dumps(compact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
