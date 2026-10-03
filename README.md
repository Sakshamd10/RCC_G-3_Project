# G+3 RCC Structural Optimization (Standalone Mode)

Hyper-simplified, lightweight **Multi-Objective Optimization** for G+3 Reinforced Cement Concrete (RCC) building structures using **NSGA-II (Genetic Algorithm)**, **Latin Hypercube Sampling (LHS)**, and **Matplotlib**.

---

## 📁 File Structure & Purpose

| File Name | Purpose |
|---|---|
| **[`Optimization.py`](file:///c:/Users/YASH/Downloads/RCC_Optimization-20260916T150512Z-1-001/RCC_Optimization/Optimization.py)** | **Main Entry Point** — Runs NSGA-II optimization, picks the best compromise solution, and exports `G+3 RCC FINAL_Modified.std`. |
| **[`rcc_nsga2_optimization.py`](file:///c:/Users/YASH/Downloads/RCC_Optimization-20260916T150512Z-1-001/RCC_Optimization/rcc_nsga2_optimization.py)** | **Optimization Engine** — 1,000 LHS design samples, NSGA-II solver, IS 456 capacity constraints, carbon ($CO_2$), and cost evaluation. |
| **[`plot_pareto_front.py`](file:///c:/Users/YASH/Downloads/RCC_Optimization-20260916T150512Z-1-001/RCC_Optimization/plot_pareto_front.py)** | **Visualizer** — Matplotlib chart generator plotting 1,000 LHS points vs. NSGA-II Pareto curve (`pareto_front_highres.png`). |
| **[`staad_file_handler.py`](file:///c:/Users/YASH/Downloads/RCC_Optimization-20260916T150512Z-1-001/RCC_Optimization/staad_file_handler.py)** | **File Updater** — Clean 20-line utility function to update member section sizes in `.std` text files. |

---

## 🚀 How to Run

```bash
# 1. Run Main Optimization & Generate Modified STAAD File
python Optimization.py

# 2. Plot Pareto Front (Embodied Carbon vs Cost)
python plot_pareto_front.py
```
