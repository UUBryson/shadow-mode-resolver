"""Autonomy gate. The agent starts in shadow mode and has to earn the right to write."""


class GateError(RuntimeError):
    pass


class Gate:
    def __init__(self, required_streak: int = 30):
        self.required = required_streak
        self.mode = "shadow"
        self.streak = 0
        self.driver_passed = False
        self.demotions = 0
        self.events = []

    def observe(self, agrees):
        """Feed one graded outcome. None (a skip) leaves the streak alone."""
        if agrees is None:
            return
        if agrees:
            self.streak += 1
            return
        self.streak = 0
        if self.mode == "live":
            self.mode = "shadow"
            self.demotions += 1
            self.events.append("demoted: disagreement while live; owner notified")
        else:
            self.events.append("streak reset: disagreement in shadow")

    @property
    def eligible(self):
        return self.streak >= self.required and self.driver_passed

    def go_live(self):
        if not self.driver_passed:
            raise GateError("write driver has not passed its test-environment run")
        if self.streak < self.required:
            raise GateError(f"agreement streak {self.streak} < required {self.required}")
        self.mode = "live"
        self.events.append(f"promoted to live after {self.streak} straight agreements")
