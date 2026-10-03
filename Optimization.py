from staad_file_handler import update_staad_file
from rcc_nsga2_optimization import run_nsga2_optimization

def main():
    print("=== G+3 RCC Structural Optimization (Standalone Mode) ===")
    
    # 1. Run NSGA-II Optimization
    result, _ = run_nsga2_optimization()
    
    # 2. Extract best compromise Pareto solution
    best_x = result.X[0]
    bw_mm = round(best_x[0] / 25.0) * 25
    bd_mm = round(best_x[1] / 25.0) * 25
    
    yd_m = bd_mm / 1000.0  # Depth in meters
    zd_m = bw_mm / 1000.0  # Width in meters
    
    # 3. Update STAAD .std file with optimal section sizes
    original_std = "G+3 RCC FINAL.std"
    modified_std = "G+3 RCC FINAL_Modified.std"
    member_range = "1 TO 80 161 TO 235"
    
    update_staad_file(original_std, modified_std, member_range, yd_m, zd_m)
    
    best_carbon = result.F[0, 0] / 1000.0
    best_cost   = result.F[0, 1] / 100000.0
    
    print("\n--- Optimal Result Summary ---")
    print(f"Optimal Beam Section: {bw_mm}mm x {bd_mm}mm (YD={yd_m}m, ZD={zd_m}m)")
    print(f"Embodied Carbon: {best_carbon:.2f} Tonnes CO2")
    print(f"Structural Cost: INR {best_cost:.2f} Lakhs")

if __name__ == "__main__":
    main()
