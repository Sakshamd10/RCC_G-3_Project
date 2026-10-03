from staad_file_handler import update_staad_file

class OpenSTAADHandler:
    def __init__(self, std_file_path: str):
        self.std_file_path = std_file_path

    def update_member_property(self, member_range_str: str, yd: float, zd: float, output_file_path: str = None) -> bool:
        target_file = output_file_path if output_file_path else self.std_file_path
        return update_staad_file(self.std_file_path, target_file, member_range_str, yd, zd)

    def run_analysis(self, std_file: str = None) -> dict:
        return {"status": "SUCCESS", "mode": "STANDALONE_MATH"}

    def parse_analysis_results(self, std_file: str = None) -> dict:
        return {"errors": 0, "warnings": 0, "notes": 0}
