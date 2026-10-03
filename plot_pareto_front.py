import os
import numpy as np
import matplotlib.pyplot as plt
from rcc_nsga2_optimization import run_nsga2_optimization, RCCOptimizationProblem

def plot_pareto_front():
    result, lhs_samples = run_nsga2_optimization()
    problem = RCCOptimizationProblem()

    # Evaluate feasible LHS initial samples
    lhs_evals = []
    for sample in lhs_samples:
        out = {}
        problem._evaluate(sample, out)
        if all(g <= 0 for g in out["G"]):
            lhs_evals.append(out["F"])
    lhs_evals = np.array(lhs_evals)

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
        plt.scatter(lhs_evals[:, 0] / 1000.0, lhs_evals[:, 1] / 100000.0, color='gray', alpha=0.3, s=25, label='1,000 LHS Initial Samples')

    plt.plot(carbon_sorted, cost_sorted, color='crimson', linewidth=2.5, label='NSGA-II Pareto Front')
    plt.scatter(carbon_sorted, cost_sorted, color='red', edgecolors='black', s=60, zorder=4)

    min_idx = np.argmin(carbon_sorted)
    plt.scatter(carbon_sorted[min_idx], cost_sorted[min_idx], color='green', s=130, marker='*', zorder=5, label='Min Carbon Winner')

    plt.title('G+3 RCC Building: Embodied Carbon vs Structural Cost', fontsize=13, fontweight='bold')
    plt.xlabel('Total Embodied Carbon (Tonnes CO2) ↓', fontsize=11)
    plt.ylabel('Total Structural Cost (Lakhs INR) ↓', fontsize=11)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()
    plt.tight_layout()

    output_png = "pareto_front_highres.png"
    plt.savefig(output_png, dpi=300)

    brain_path = r"C:\Users\YASH\.gemini\antigravity-ide\brain\a6489ccf-8dd1-4463-8812-bd5e37b7ace5\pareto_front_highres.png"
    if os.path.exists(os.path.dirname(brain_path)):
        plt.savefig(brain_path, dpi=300)

    print(f"Pareto Front plot saved to '{os.path.abspath(output_png)}'")

if __name__ == "__main__":
    plot_pareto_front()
