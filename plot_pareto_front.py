import os
import numpy as np
import matplotlib.pyplot as plt
from rcc_nsga2_optimization import run_nsga2_optimization, best_compromise_index


def plot_pareto_front():
    result, _ = run_nsga2_optimization()
    log = result.design_log

    # Feasible LHS initial samples and all feasible NSGA-II evaluations (from the design log)
    lhs_evals = np.array([[r["carbon_t"], r["cost_lakh"]] for r in log if r["stage"] == "LHS" and r["feasible"]])
    ga_evals  = np.array([[r["carbon_t"], r["cost_lakh"]] for r in log if r["stage"] == "NSGA-II" and r["feasible"]])

    # Extract Pareto values
    carbon_pareto = result.F[:, 0] / 1000.0  # Tonnes CO2
    cost_pareto   = result.F[:, 1] / 100000.0 # Lakhs INR

    # Sort Pareto front
    sorted_idx = np.argsort(carbon_pareto)
    carbon_sorted = carbon_pareto[sorted_idx]
    cost_sorted   = cost_pareto[sorted_idx]

    # Matplotlib Plotting
    plt.figure(figsize=(10, 6))

    if len(lhs_evals) > 0:
        plt.scatter(lhs_evals[:, 0], lhs_evals[:, 1], color='gray', alpha=0.3, s=25,
                    label=f'Feasible LHS samples ({len(lhs_evals)} of 1,000)')
    if len(ga_evals) > 0:
        plt.scatter(ga_evals[:, 0], ga_evals[:, 1], color='steelblue', alpha=0.15, s=10,
                    label=f'Feasible NSGA-II evaluations ({len(ga_evals)})')

    plt.plot(carbon_sorted, cost_sorted, color='crimson', linewidth=2.5, label='NSGA-II Pareto Front')
    plt.scatter(carbon_sorted, cost_sorted, color='red', edgecolors='black', s=60, zorder=4)

    best = best_compromise_index(result.F)
    plt.scatter(carbon_pareto[best], cost_pareto[best], color='green', s=200, marker='*', zorder=5,
                label='Best Compromise')

    # Zoomed inset on the Pareto front
    ax = plt.gca()
    inset = ax.inset_axes([0.55, 0.08, 0.42, 0.38])
    inset.plot(carbon_sorted, cost_sorted, color='crimson', linewidth=1.5)
    inset.scatter(carbon_sorted, cost_sorted, color='red', edgecolors='black', s=30, zorder=4)
    inset.scatter(carbon_pareto[best], cost_pareto[best], color='green', s=120, marker='*', zorder=5)
    inset.set_title('Pareto front (zoom)', fontsize=9)
    inset.tick_params(labelsize=8)
    inset.grid(True, linestyle=':', alpha=0.6)

    plt.title('G+3 RCC Building: Embodied Carbon vs Structural Cost', fontsize=13, fontweight='bold')
    plt.xlabel('Total Embodied Carbon (Tonnes CO2) ↓', fontsize=11)
    plt.ylabel('Total Structural Cost (Lakhs INR) ↓', fontsize=11)
    plt.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='upper left')
    plt.tight_layout()

    output_png = "pareto_front_highres.png"
    plt.savefig(output_png, dpi=300)
    plt.savefig("pareto_front.png", dpi=100)

    print(f"Pareto Front plot saved to '{os.path.abspath(output_png)}'")


if __name__ == "__main__":
    plot_pareto_front()
