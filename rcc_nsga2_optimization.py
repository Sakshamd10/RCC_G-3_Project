import csv
import os
import re
import numpy as np
from scipy.stats import qmc
from pymoo.core.problem import ElementwiseProblem
from pymoo.core.callback import Callback
from pymoo.core.duplicate import DefaultDuplicateElimination
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.core.population import Population

STAAD_ANL = "G+3 RCC FINAL.ANL"
DESIGN_LOG = "design_log.csv"

# Building frame total member lengths (m), measured from "G+3 RCC FINAL.STD"
# 4 x 3 bays of 5 m, beams at plinth + 4 floor levels, 20 columns
TOTAL_BEAM_LENGTH = 775.0   # 155 beams x 5 m
GROUND_COL_LENGTH = 80.0    # 20 columns x (1 m plinth stub + 3 m ground storey)
UPPER_COL_LENGTH  = 180.0   # 20 columns x 3 storeys x 3 m
BEAM_SPAN         = 5.0

STEEL_DENSITY = 7850.0  # kg/m3
COVER = 0.040           # m, effective cover (CLEAR 0.04 in STAAD)

# Concrete grades and binder types
GRADES  = [25, 30, 35, 40]                 # M25, M30, M35, M40
BINDERS = ["OPC", "PPC (30% fly ash)", "GGBS (50%)"]

# Material unit carbon factors (kg CO2 per m3 or kg)
CARBON_CONCRETE = [300.0, 340.0, 380.0, 420.0]  # OPC mix, M25..M40
CARBON_BINDER   = [1.00, 0.75, 0.55]            # factor on OPC carbon (indicative, ICE v3 trend)
CARBON_STEEL    = [2.80, 2.90]                  # Fe-500, Fe-550

# Material unit costs (INR per m3, kg, or m2)
COST_CONCRETE = [5200.0, 5700.0, 6200.0, 6800.0]  # OPC mix, M25..M40
COST_BINDER   = [1.00, 0.97, 1.08]                # factor on OPC cost (indicative; replace with local rates)
COST_STEEL    = [65.0, 70.0]
COST_FORMWORK = 450.0

# Structural load demands
REQUIRED_MOMENT_KNM = 140.0     # beam hogging moment envelope (estimate; STAAD beam design was aborted)
REQUIRED_AXIAL_G_KN = 2057.0    # max Pu, ground columns  (from STAAD column design, .ANL)
REQUIRED_AXIAL_U_KN = 1656.0    # max Pu, upper columns   (from STAAD column design, .ANL)
SPAN_DEPTH_LIMIT    = 26.0      # IS 456 Cl. 23.2.1, continuous beam

# Variables: [bw, bd, Cg, Cu, fck_idx, fy_idx, rho_b, rho_c, binder_idx]
VAR_NAMES = ["beam_b_mm", "beam_D_mm", "col_ground_mm", "col_upper_mm",
             "fck_idx", "fy_idx", "rho_beam_pct", "rho_col_pct", "binder_idx"]


def read_staad_axial_demands(anl_file=STAAD_ANL):
    """Reads max column Pu (kN) for ground and upper columns from STAAD column design output.
    Ground = plinth stub (1 m) + first storey; upper = remaining storeys (3 m, members 101..160)."""
    if not os.path.exists(anl_file):
        return REQUIRED_AXIAL_G_KN, REQUIRED_AXIAL_U_KN

    with open(anl_file, encoding="latin-1") as file:
        content = file.read()

    pattern = r"C O L U M N   N O\.\s+(\d+).*?LENGTH:\s+([\d.]+).*?DESIGN AXIAL FORCE \(Pu\)\s+:\s+([\d.]+)"
    ground, upper = [0.0], [0.0]
    for member, length, pu in re.findall(pattern, content, re.S):
        member, length, pu = int(member), float(length), float(pu)
        if length == 1000.0 or 81 <= member <= 160 and (member - 81) % 4 == 0:
            ground.append(pu)
        elif 81 <= member <= 160:
            upper.append(pu)
    return max(ground), max(upper)


def decode(x):
    """Converts a raw variable vector into buildable design values."""
    return {
        "bw":     round(x[0] / 25.0) * 25.0 / 1000.0,  # 25 mm steps, in m
        "bd":     round(x[1] / 25.0) * 25.0 / 1000.0,
        "Cg":     round(x[2] / 25.0) * 25.0 / 1000.0,
        "Cu":     round(x[3] / 25.0) * 25.0 / 1000.0,
        "fck_idx": int(round(x[4])),
        "fy_idx":  int(round(x[5])),
        "rho_b":   round(round(x[6] / 0.05) * 0.05, 2),  # 0.05 % steps
        "rho_c":   round(round(x[7] / 0.05) * 0.05, 2),
        "binder_idx": int(round(x[8])),
    }


class RCCOptimizationProblem(ElementwiseProblem):
    def __init__(self, axial_g=REQUIRED_AXIAL_G_KN, axial_u=REQUIRED_AXIAL_U_KN):
        # Index variables use +/-0.49 so every option gets an equal share after rounding
        xl = np.array([250.0, 350.0, 400.0, 300.0, -0.49, -0.49, 0.8, 1.0, -0.49])
        xu = np.array([400.0, 600.0, 600.0, 500.0,  3.49,  1.49, 2.5, 4.0,  2.49])
        super().__init__(n_var=9, n_obj=2, n_ieq_constr=6, xl=xl, xu=xu)

        self.axial_g = axial_g
        self.axial_u = axial_u
        self.stage = "LHS"
        self.generation = 0
        self.log = []

    def _evaluate(self, x, out, *args, **kwargs):
        d = decode(x)
        bw, bd, Cg, Cu = d["bw"], d["bd"], d["Cg"], d["Cu"]
        fck = GRADES[d["fck_idx"]]
        fy  = [500, 550][d["fy_idx"]]
        rho_b, rho_c = d["rho_b"], d["rho_c"]

        # Volumes and masses
        d_eff  = bd - COVER
        v_beam  = TOTAL_BEAM_LENGTH * bw * bd
        v_col_g = GROUND_COL_LENGTH * (Cg ** 2)
        v_col_u = UPPER_COL_LENGTH * (Cu ** 2)
        v_conc  = v_beam + v_col_g + v_col_u

        ast_b = (rho_b / 100.0) * bw * d_eff  # tension steel (m2); top and bottom both provided
        w_steel = (TOTAL_BEAM_LENGTH * 2 * ast_b + (v_col_g + v_col_u) * (rho_c / 100.0)) * STEEL_DENSITY
        a_formwork = TOTAL_BEAM_LENGTH * (bw + 2 * bd) + GROUND_COL_LENGTH * 4 * Cg + UPPER_COL_LENGTH * 4 * Cu

        # Objective 1: Embodied Carbon (kg CO2)
        carbon_conc = CARBON_CONCRETE[d["fck_idx"]] * CARBON_BINDER[d["binder_idx"]]
        total_carbon = v_conc * carbon_conc + w_steel * CARBON_STEEL[d["fy_idx"]]

        # Objective 2: Total Cost (INR)
        cost_conc = COST_CONCRETE[d["fck_idx"]] * COST_BINDER[d["binder_idx"]]
        total_cost = v_conc * cost_conc + w_steel * COST_STEEL[d["fy_idx"]] + a_formwork * COST_FORMWORK

        out["F"] = [total_carbon, total_cost]

        # Structural constraints (G <= 0)
        g1 = Cu - Cg  # Upper column size <= Ground column size

        # Beam flexure, singly reinforced (IS 456 Annex G)
        ast_mm2 = ast_b * 1e6
        xu = 0.87 * fy * ast_mm2 / (0.36 * fck * bw * 1000)            # mm
        xu_max = (0.46 if fy == 500 else 0.44) * d_eff * 1000          # mm
        mu_cap = 0.87 * fy * ast_mm2 * (d_eff * 1000 - 0.42 * min(xu, xu_max)) / 1e6
        g2 = REQUIRED_MOMENT_KNM - mu_cap  # Moment demand <= Beam moment capacity
        g3 = xu - xu_max                   # Under-reinforced (ductile) section

        # Column axial capacity, short column with min. eccentricity (IS 456 Cl. 39.3)
        def pu_cap(c):
            ac = (c * 1000) ** 2
            asc = (rho_c / 100.0) * ac
            return (0.4 * fck * (ac - asc) + 0.67 * fy * asc) / 1000.0

        g4 = self.axial_g - pu_cap(Cg)  # Ground column axial demand <= capacity
        g5 = self.axial_u - pu_cap(Cu)  # Upper column axial demand <= capacity

        g6 = BEAM_SPAN / d_eff - SPAN_DEPTH_LIMIT  # Deflection control (span/depth)

        out["G"] = [g1, g2, g3, g4, g5, g6]

        self.log.append({
            "eval_no": len(self.log) + 1, "stage": self.stage, "generation": self.generation,
            "beam_b_mm": bw * 1000, "beam_D_mm": bd * 1000,
            "col_ground_mm": Cg * 1000, "col_upper_mm": Cu * 1000,
            "concrete": f"M{fck}", "steel": f"Fe{fy}", "binder": BINDERS[d["binder_idx"]],
            "rho_beam_pct": rho_b, "rho_col_pct": rho_c,
            "carbon_t": round(total_carbon / 1000.0, 3), "cost_lakh": round(total_cost / 1e5, 3),
            "feasible": all(g <= 0 for g in out["G"]),
        })


def decoded_matrix(pop):
    """Buildable design values for a population, so raw vectors that round to the same design count as duplicates."""
    return np.array([list(decode(x).values()) for x in pop.get("X")], dtype=float)


class GenerationTracker(Callback):
    """Tells the problem which NSGA-II generation the next evaluations belong to."""
    def notify(self, algorithm):
        algorithm.problem.generation = algorithm.n_gen


def generate_lhs_samples(n_samples=1000):
    """Generates 1,000 Latin Hypercube design samples using SciPy."""
    problem = RCCOptimizationProblem()
    sampler = qmc.LatinHypercube(d=problem.n_var, seed=42)
    raw_samples = sampler.random(n=n_samples)
    return qmc.scale(raw_samples, problem.xl, problem.xu)


def best_compromise_index(F):
    """Pareto point closest to the ideal (min carbon, min cost) after normalising both objectives."""
    f_min, f_max = F.min(axis=0), F.max(axis=0)
    norm = (F - f_min) / np.where(f_max > f_min, f_max - f_min, 1.0)
    return int(np.argmin(np.linalg.norm(norm, axis=1)))


def save_design_log(log, path=DESIGN_LOG):
    with open(path, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(log[0].keys()))
        writer.writeheader()
        writer.writerows(log)


def run_nsga2_optimization(n_lhs=1000, pop_size=100, n_gen=100, log_path=DESIGN_LOG):
    """Runs NSGA-II Multi-Objective Genetic Algorithm, seeded with the best LHS designs."""
    np.random.seed(42)  # LHS ranking below breaks ties randomly; keep runs repeatable
    problem = RCCOptimizationProblem(*read_staad_axial_demands())

    # Stage 1: evaluate every LHS sample
    lhs_samples = generate_lhs_samples(n_samples=n_lhs)
    lhs_pop = Population.new("X", lhs_samples)
    for ind in lhs_pop:
        out = {}
        problem._evaluate(ind.X, out)
        ind.set("F", np.array(out["F"]))
        ind.set("G", np.array(out["G"]))

    # Stage 2: NSGA-II, starting from the best pop_size LHS designs (ranked by survival)
    algorithm = NSGA2(pop_size=pop_size, eliminate_duplicates=DefaultDuplicateElimination(func=decoded_matrix))
    initial_pop = algorithm.survival.do(problem, lhs_pop, n_survive=pop_size)
    algorithm.initialization.sampling = initial_pop

    problem.stage = "NSGA-II"
    result = minimize(problem, algorithm, ('n_gen', n_gen), seed=42, verbose=False,
                      callback=GenerationTracker())

    if log_path:
        save_design_log(problem.log, log_path)
    result.design_log = problem.log
    result.axial_demands = (problem.axial_g, problem.axial_u)
    return result, lhs_samples


def print_run_summary(result):
    log = result.design_log
    lhs = [r for r in log if r["stage"] == "LHS"]
    ga  = [r for r in log if r["stage"] == "NSGA-II"]
    print(f"Column axial demands (STAAD): ground {result.axial_demands[0]:.0f} kN, "
          f"upper {result.axial_demands[1]:.0f} kN")
    print(f"LHS designs evaluated     : {len(lhs)} ({sum(r['feasible'] for r in lhs)} feasible)")
    print(f"NSGA-II designs evaluated : {len(ga)} ({sum(r['feasible'] for r in ga)} feasible) "
          f"over {len({r['generation'] for r in ga})} generations")
    print(f"Total designs evaluated   : {len(log)}  (all listed in '{DESIGN_LOG}')")
    print(f"Pareto optimal solutions  : {len(result.F)} "
          f"({len(np.unique(np.round(result.F, 0), axis=0))} distinct)")


if __name__ == "__main__":
    result, _ = run_nsga2_optimization()
    print_run_summary(result)
    i = best_compromise_index(result.F)
    print(f"Best Compromise -> Carbon: {result.F[i, 0] / 1000.0:.2f} Tonnes CO2 | "
          f"Cost: INR {result.F[i, 1] / 100000.0:.2f} Lakhs")
