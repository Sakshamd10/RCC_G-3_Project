import os
import re

def update_staad_file(input_std: str, output_std: str, member_range: str, yd: float, zd: float) -> bool:
    """Updates member cross-section dimensions (YD, ZD) in a STAAD .std file."""
    if not os.path.exists(input_std):
        print(f"Error: '{input_std}' not found.")
        return False

    with open(input_std, "r") as file:
        content = file.read()

    pattern = re.escape(member_range) + r"\s+PRIS\s+YD\s+[\d\.]+\s+ZD\s+[\d\.]+"
    replacement = f"{member_range} PRIS YD {yd:.2f} ZD {zd:.2f}"

    if re.search(pattern, content):
        updated_content = re.sub(pattern, replacement, content)
    else:
        old_line = f"{member_range} PRIS YD 0.45 ZD 0.3"
        new_line = f"{member_range} PRIS YD {yd:.2f} ZD {zd:.2f}"
        updated_content = content.replace(old_line, new_line)

    with open(output_std, "w") as file:
        file.write(updated_content)

    print(f"Updated STAAD model saved to: '{output_std}' (YD={yd}m, ZD={zd}m)")
    return True
