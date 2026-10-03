import os
import re


def _member_pattern(member_range: str) -> str:
    """Regex for a STAAD member list; tolerates the ' -' line continuation STAAD uses for long lists."""
    return r"[\s\-]+".join(re.escape(token) for token in member_range.split())


def update_staad_file(input_std: str, output_std: str, member_range: str, yd: float, zd: float) -> bool:
    """Updates member cross-section dimensions (YD, ZD) in a STAAD .std file."""
    return update_staad_design(input_std, output_std, sections={member_range: (yd, zd)})


def update_staad_design(input_std: str, output_std: str, sections: dict,
                        fc_kn_m2: float = None, fy_kn_m2: float = None) -> bool:
    """Updates PRIS section sizes for each member list in `sections` ({member_range: (yd, zd)} in m)
    and, optionally, the concrete design grade (FC) and main steel grade (FYMAIN)."""
    if not os.path.exists(input_std):
        print(f"Error: '{input_std}' not found.")
        return False

    with open(input_std, "r", encoding="latin-1") as file:
        content = file.read()

    for member_range, (yd, zd) in sections.items():
        pattern = r"(" + _member_pattern(member_range) + r"\s+PRIS\s+YD\s+)[\d\.]+(\s+ZD\s+)[\d\.]+"
        content, count = re.subn(pattern, rf"\g<1>{yd:.3f}\g<2>{zd:.3f}", content)
        if count == 0:
            print(f"Warning: section line for members '{member_range}' not found; left unchanged.")

    if fc_kn_m2 is not None:
        content = re.sub(r"^FC\s+[\d\.]+\s+ALL", f"FC {fc_kn_m2:.0f} ALL", content, flags=re.M)
    if fy_kn_m2 is not None:
        content = re.sub(r"^FYMAIN\s+[\d\.]+\s+ALL", f"FYMAIN {fy_kn_m2:.0f} ALL", content, flags=re.M)

    with open(output_std, "w", encoding="latin-1") as file:
        file.write(content)

    print(f"Updated STAAD model saved to: '{output_std}'")
    return True
