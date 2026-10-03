import numpy as np
from scipy.stats import qmc
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.core.population import Population

# Building frame total member lengths (m)
TOTAL_BEAM_LENGTH = 320.0
GROUND_COL_LENGTH = 56.0
UPPER_COL_LENGTH  = 144.0

STEEL_DENSITY = 7850.0  # kg/m3

# Material unit carbon factors (kg CO2 per m3 or kg)
CARBON_CONCRETE = [300.0, 340.0, 380.0, 420.0]  # M25, M30, M35, M40
CARBON_STEEL    = [2.80, 2.90]                   # Fe-500, Fe-550

# Material unit costs (INR per m3, kg, or m2)
COST_CONCRETE = [5200.0, 5700.0, 6200.0, 6800.0]
COST_STEEL    = [65.0, 70.0]
COST_FORMWORK = 450.0

# Structural load demands (IS 456 envelope)
REQUIRED_MOMENT_KNM = 140.0
REQUIRED_AXIAL_KN   = 1800.0


class RCCOptimizationProblem(ElementwiseProblem):
    def __init__(self):
        # Variables: [bw, bd, Cg, Cu, fck_idx, fy_idx, rho_b, rho_c]
        xl = np.array([250.0, 350.0, 400.0, 300.0, 0, 0, 0.8, 1.0])
        xu = np.array([400.0, 600.0, 600.0, 500.0, 3, 1, 2.5, 4.0])

        super().__init__(n_var=8, n_obj=2, n_ieq_constr=3, xl=xl, xu=xu)

    def _evaluate(self, x, out, *args, **kwargs):
        # Round member dimensions to standard 25mm steps
        bw = round(x[0] / 25.0) * 25.0 / 1000.0
        bd = round(x[1] / 25.0) * 25.0 / 1000.0
        Cg = round(x[2] / 25.0) * 25.0 / 1000.0
        Cu = round(x[3] / 25.0) * 25.0 / 1000.0

        fck_idx = int(round(x[4]))
        fy_idx  = int(round(x[5]))
        rho_b   = x[6]
        rho_c   = x[7]

        fck = [25, 30, 35, 40][fck_idx]
        fy  = [500, 550][fy_idx]

        # Volumes and masses
        v_beam  = TOTAL_BEAM_LENGTH * bw * bd
        v_col_g = GROUND_COL_LENGTH * (Cg ** 2)
        v_col_u = UPPER_COL_LENGTH * (Cu ** 2)
        v_conc  = v_beam + v_col_g + v_col_u

        w_steel = (v_beam * (rho_b / 100.0) + (v_col_g + v_col_u) * (rho_c / 100.0)) * STEEL_DENSITY
        a_formwork = TOTAL_BEAM_LENGTH * (bw + 2 * bd) + GROUND_COL_LENGTH * 4 * Cg + UPPER_COL_LENGTH * 4 * Cu

        # Objective 1: Embodied Carbon (kg CO2)
        total_carbon = v_conc * CARBON_CONCRETE[fck_idx] + w_steel * CARBON_STEEL[fy_idx]

        # Objective 2: Total Cost (INR)
        total_cost = v_conc * COST_CONCRETE[fck_idx] + w_steel * COST_STEEL[fy_idx] + a_formwork * COST_FORMWORK

        out["F"] = [total_carbon, total_cost]

        # Structural constraints (G <= 0)
        g1 = Cu - Cg  # Upper column size <= Ground column size

        d_eff = bd - 0.040
        xu_max = (0.46 if fy == 500 else 0.44) * d_eff
        mu_cap = (0.36 * fck * (bw * 1000) * (xu_max * 1000) * ((d_eff - 0.42 * xu_max) * 1000)) / 1e6
        g2 = REQUIRED_MOMENT_KNM - mu_cap  # Moment demand <= Beam moment capacity

        ac = (Cg * 1000) ** 2
        asc = (rho_c / 100.0) * ac
        pu_cap = (0.4 * fck * (ac - asc) + 0.67 * fy * asc) / 1000.0
        g3 = REQUIRED_AXIAL_KN - pu_cap  # Axial demand <= Column axial capacity

        out["G"] = [g1, g2, g3]


def generate_lhs_samples(n_samples=1000):
    """Generates 1,000 Latin Hypercube design samples using SciPy."""
    problem = RCCOptimizationProblem()
    sampler = qmc.LatinHypercube(d=problem.n_var, seed=42)
    raw_samples = sampler.random(n=n_samples)
    return qmc.scale(raw_samples, problem.xl, problem.xu)


def run_nsga2_optimization():
    """Runs NSGA-II Multi-Objective Genetic Algorithm."""
    lhs_samples = generate_lhs_samples(n_samples=1000)
    problem = RCCOptimizationProblem()

    initial_pop = Population.new("X", lhs_samples[:100])
    algorithm = NSGA2(pop_size=100, sampling=initial_pop, eliminate_duplicates=True)

    result = minimize(problem, algorithm, ('n_gen', 100), seed=42, verbose=False)
    return result, lhs_samples


if __name__ == "__main__":
    result, _ = run_nsga2_optimization()
    print(f"Optimization Finished! Found {len(result.F)} Pareto optimal solutions.")
    best_carbon = result.F[0, 0] / 1000.0
    best_cost   = result.F[0, 1] / 100000.0
    print(f"Best Compromise -> Carbon: {best_carbon:.2f} Tonnes CO2 | Cost: INR {best_cost:.2f} Lakhs")
