from staad_file_handler import update_staad_design
from rcc_nsga2_optimization import (run_nsga2_optimization, best_compromise_index, print_run_summary,
                                    decode, GRADES, BINDERS, DESIGN_LOG)

# Member lists exactly as they appear under MEMBER PROPERTY in the STAAD file
BEAM_MEMBERS   = "1 TO 80 161 TO 235"
COLUMN_MEMBERS = "81 TO 160 236 237 239 241 246 TO 249 254 TO 257 262 TO 265 270 TO 272 273"


def main():
    print("=== G+3 RCC Structural Optimization (Standalone Mode) ===")

    # 1. Run LHS + NSGA-II Optimization
    result, _ = run_nsga2_optimization()
    print_run_summary(result)

    # 2. Extract best compromise Pareto solution
    i = best_compromise_index(result.F)
    d = decode(result.X[i])
    fck = GRADES[d["fck_idx"]]
    fy = [500, 550][d["fy_idx"]]

    # 3. Update STAAD .std file with optimal section sizes and material grades
    #    All columns share one section line in the STAAD model, so they get the ground column size
    #    (the governing one); split the line into ground/upper groups to use the smaller upper size.
    original_std = "G+3 RCC FINAL.STD"
    modified_std = "G+3 RCC FINAL_Modified.std"
    update_staad_design(original_std, modified_std,
                        sections={BEAM_MEMBERS: (d["bd"], d["bw"]), COLUMN_MEMBERS: (d["Cg"], d["Cg"])},
                        fc_kn_m2=fck * 1000, fy_kn_m2=fy * 1000)

    print("\n--- Optimal Result Summary (best compromise) ---")
    print(f"Beam Section       : {d['bw'] * 1000:.0f}mm x {d['bd'] * 1000:.0f}mm, steel {d['rho_b']:.2f}%")
    print(f"Ground Columns     : {d['Cg'] * 1000:.0f}mm x {d['Cg'] * 1000:.0f}mm, steel {d['rho_c']:.2f}%")
    print(f"Upper Columns      : {d['Cu'] * 1000:.0f}mm x {d['Cu'] * 1000:.0f}mm, steel {d['rho_c']:.2f}%")
    print(f"Materials          : M{fck} {BINDERS[d['binder_idx']]}, Fe{fy}")
    print(f"Embodied Carbon    : {result.F[i, 0] / 1000.0:.2f} Tonnes CO2")
    print(f"Structural Cost    : INR {result.F[i, 1] / 100000.0:.2f} Lakhs")

    print("\n--- All Pareto Designs ---")
    for j in result.F[:, 0].argsort():
        dj = decode(result.X[j])
        mark = "  <- best compromise" if j == i else ""
        print(f"{result.F[j, 0] / 1000.0:7.2f} t CO2 | INR {result.F[j, 1] / 100000.0:6.2f} L | "
              f"beam {dj['bw'] * 1000:.0f}x{dj['bd'] * 1000:.0f} | col {dj['Cg'] * 1000:.0f}/{dj['Cu'] * 1000:.0f} | "
              f"M{GRADES[dj['fck_idx']]} {BINDERS[dj['binder_idx']]} | Fe{[500, 550][dj['fy_idx']]}{mark}")
    print(f"\nEvery evaluated design is listed in '{DESIGN_LOG}'.")


if __name__ == "__main__":
    main()
