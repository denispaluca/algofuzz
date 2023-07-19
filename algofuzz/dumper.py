import time
from pathlib import Path

class DataDumper:
    def __init__(self, path: Path, interval: int, is_minute_interval: bool):
        self.path = path
        self.interval = interval
        self.is_minute_interval = is_minute_interval
        self.file = open(path, "a")
        self.file.write("lines_covered, coverage, covered_paths, transitions, rejected_calls, call_count\n")
        self.last_time = None

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
            self.last_time = time.time()

        def write_line():
            self.file.write(f"{covered_line_count}, {coverage:.2f}, {covered_paths}, {transitions}, {rejected_calls}, {call_count}\n")
        
        if self.is_minute_interval:
            time_passed = time.time() - self.last_time
            minutes = int(time_passed / 60)
            if minutes == 0: 
                return
            if minutes % self.interval != 0:
                return
            
            write_line()
            self.last_time = time.time()
            return
        
        if call_count % self.interval == 0:
            write_line()