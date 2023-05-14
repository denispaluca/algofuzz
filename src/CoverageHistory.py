

class CoverageHistory:
    history: list[list[int]] = []
    covered_lines: set[int] = set()

    def update(self, lines: list[int]):
        self.history.append(lines)
        last_count = self.count()
        self.covered_lines.update(lines)
        new_lines_covered = self.count() > last_count

        return new_lines_covered

    def count(self):
        return len(self.covered_lines)
