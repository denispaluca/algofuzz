import time
from pathlib import Path

class DataDumper:
    def __init__(self, path: Path, interval: int, is_time_interval: bool):
        self.path = path
        self.interval = interval # seconds or calls
        self.is_time_interval = is_time_interval
        self.last_time = None

    
    def create_dump(self, *args):
        self.file = open(self.path, "a")
        for arg in args:
            self.file.write(f"#{arg}\n")
        self.file.write("lines_covered, coverage, covered_paths, transitions, rejected_calls, call_count, exec_time\n")
        

    def dump(
        self,
        covered_line_count: int,
        coverage: float,
        covered_paths: int,
        transitions: int,
        rejected_calls: int,
        call_count: int
    ):
        if(self.last_time is None):
            self.first_time = time.time()
            self.last_time = self.first_time
            self.file.write(f"{covered_line_count}, {coverage:.2f}, {covered_paths}, {transitions}, {rejected_calls}, {call_count} \n")
            return

        
        if self.is_time_interval:
            time_passed = time.time() - self.last_time
            if time_passed < self.interval:
                return
            
            self.file.write(f"{covered_line_count}, {coverage:.2f}, {covered_paths}, {transitions}, {rejected_calls}, {call_count} \n")
            self.last_time = time.time()
            return
        
        if call_count % self.interval == 0:
            self.file.write(f"{covered_line_count}, {coverage:.2f}, {covered_paths}, {transitions}, {rejected_calls}, {call_count} \n")