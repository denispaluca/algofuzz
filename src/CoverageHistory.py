

class CoverageHistory:
    def __init__(self):
        self.history: list[list[int]] = []
        self.covered_lines: set[int] = set()

    def update(self, lines: list[int]):
        self.history.append(lines)
        last_covered_lines = self.covered_lines.copy()
        self.covered_lines.update(lines)
        new_lines_covered = self.covered_lines - last_covered_lines

        return new_lines_covered

    def count(self):
        return len(self.covered_lines)
