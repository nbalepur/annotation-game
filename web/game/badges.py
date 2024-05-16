from dataclasses import dataclass
from enum import StrEnum, auto

class BuzzBadgeStatus(StrEnum):
    CORRECT = "<CORRECT_BUZZ>"
    INCORRECT = "<INCORRECT_BUZZ>"
    CURRENT = "<CURRENT_BUZZ>"

@dataclass
class BuzzBadge:
    index: int
    status: BuzzBadgeStatus