# G+3 RCC Structural Optimization (Standalone Mode)

Hyper-simplified, lightweight **Multi-Objective Optimization** for G+3 Reinforced Cement Concrete (RCC) building structures using **NSGA-II (Genetic Algorithm)**, **Latin Hypercube Sampling (LHS)**, and **Matplotlib**.

---

## 📁 File Structure & Purpose

| File Name | Purpose |
|---|---|
| **[`Optimization.py`](Optimization.py)** | **Main Entry Point** — Runs LHS + NSGA-II, picks the best compromise solution, and exports `G+3 RCC FINAL_Modified.std` (beam size, column size, FC, FYMAIN). |
| **[`rcc_nsga2_optimization.py`](rcc_nsga2_optimization.py)** | **Optimization Engine** — 1,000 LHS design samples, NSGA-II solver, IS 456 capacity constraints, carbon ($CO_2$) and cost evaluation, design log. |
| **[`plot_pareto_front.py`](plot_pareto_front.py)** | **Visualizer** — Plots feasible LHS samples, NSGA-II evaluations and the Pareto front (`pareto_front_highres.png`). |
| **[`staad_file_handler.py`](staad_file_handler.py)** | **File Updater** — Updates member section sizes and design grades in `.std` text files. |
| **`design_log.csv`** | **Output** — Every design evaluated (LHS + each NSGA-II generation), with sizes, materials, carbon, cost and feasibility. |

---

## 🚀 How to Run

```bash
pip install numpy scipy pymoo matplotlib

# 1. Run Main Optimization & Generate Modified STAAD File
python Optimization.py

# 2. Plot Pareto Front (Embodied Carbon vs Cost)
python plot_pareto_front.py
```

---

## ⚙️ How It Works

**Design variables (9)**

| Variable | Range |
|---|---|
| Beam width | 250–400 mm (25 mm steps) |
| Beam depth | 350–600 mm (25 mm steps) |
| Ground column (square) | 400–600 mm (25 mm steps) |
| Upper column (square) | 300–500 mm (25 mm steps) |
| Concrete grade | M25 / M30 / M35 / M40 |
| Steel grade | Fe500 / Fe550 |
| Beam tension steel | 0.8–2.5 % of b·d (0.05 % steps) |
| Column steel | 1.0–4.0 % of gross area (0.05 % steps) |
| Binder | OPC / PPC (30% fly ash) / GGBS (50%) |

**Quantities** use the member lengths of the STAAD model: 775 m of beams (155 × 5 m), 80 m of ground columns (20 × 4 m incl. plinth stub), 180 m of upper columns (20 × 9 m).

**Objectives** — minimise embodied carbon (kg CO₂) and structural cost (INR: concrete + steel + formwork).

**Constraints (IS 456)**
1. Upper column ≤ ground column
2. Beam moment capacity (Annex G, from the actual steel provided) ≥ 140 kN·m
3. Beam under-reinforced: xu ≤ xu,max
4. Ground column axial capacity (Cl. 39.3) ≥ max Pu of ground columns
5. Upper column axial capacity ≥ max Pu of upper columns
6. Span / effective depth ≤ 26 (Cl. 23.2.1)

Column Pu demands are read from the STAAD column design in `G+3 RCC FINAL.ANL` (currently 2057 kN ground, 1656 kN upper). The beam moment demand is an estimate because beam design in that STAAD run was aborted.

**Search** — 1,000 LHS designs are evaluated; the best 100 seed NSGA-II, which runs 100 generations × 100 designs = 10,000 more evaluations. All 11,000 are written to `design_log.csv`. The best compromise is the Pareto point closest to the ideal (min carbon, min cost) after normalising both objectives.

> No STAAD analysis is run inside the loop — every design is checked with the IS 456 formulas above. Re-analyse `G+3 RCC FINAL_Modified.std` in STAAD.Pro to verify the chosen design.

**Assumptions to replace with your own data** — concrete carbon (300–420 kg CO₂/m³ for OPC), binder factors (PPC ×0.75, GGBS ×0.55 carbon; ×0.97, ×1.08 cost), steel carbon 2.8–2.9 kg CO₂/kg, and all unit rates. They are constants at the top of `rcc_nsga2_optimization.py`.
