"""Fixed dice profiles and unbiased rejection sampling."""

from __future__ import annotations

from dataclasses import dataclass
from math import prod
from typing import Sequence


class DiceInputError(ValueError):
    """Raised when an entropy input is malformed or outside its allowed range."""


@dataclass(frozen=True)
class EntropyProfile:
    profile_id: str
    display_name: str
    die_sides: tuple[int, ...]
    die_labels: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.profile_id:
            raise ValueError("profile_id is required.")
        if len(self.die_sides) == 0:
            raise ValueError("At least one die is required.")
        if len(self.die_sides) != len(self.die_labels):
            raise ValueError("die_sides and die_labels must have the same length.")
        if any(sides < 2 for sides in self.die_sides):
            raise ValueError("Every die must have at least two sides.")

    @property
    def total_outcomes(self) -> int:
        return prod(self.die_sides)

    @property
    def accepted_outcomes(self) -> int:
        return (self.total_outcomes // 2048) * 2048

    @property
    def rejected_outcomes(self) -> int:
        return self.total_outcomes - self.accepted_outcomes

    @property
    def acceptance_probability(self) -> float:
        return self.accepted_outcomes / self.total_outcomes


@dataclass(frozen=True)
class RollResult:
    accepted: bool
    raw_value: int
    index11: int | None
    message: str


FIVE_D6 = EntropyProfile(
    profile_id="five_d6",
    display_name="(5) 6-Sided",
    die_sides=(6, 6, 6, 6, 6),
    die_labels=("d6 #1", "d6 #2", "d6 #3", "d6 #4", "d6 #5"),
)

MIXED_DICE = EntropyProfile(
    profile_id="mixed_dice",
    display_name="Mixed Dice",
    die_sides=(6, 8, 10, 12, 20),
    die_labels=("d6", "d8", "d10", "d12", "d20"),
)

APPROVED_PROFILES: tuple[EntropyProfile, ...] = (FIVE_D6, MIXED_DICE)
PROFILE_BY_NAME = {profile.display_name: profile for profile in APPROVED_PROFILES}
PROFILE_BY_ID = {profile.profile_id: profile for profile in APPROVED_PROFILES}


def evaluate_roll(profile: EntropyProfile, values: Sequence[int]) -> RollResult:
    """Map a physical dice roll to a uniform BIP39 index using rejection sampling.

    Ordered dice values are one mixed-radix integer. Only the largest prefix
    whose length is divisible by 2048 is accepted. The incomplete tail is
    rejected, preventing modulo bias.
    """
    if len(values) != len(profile.die_sides):
        raise DiceInputError(
            f"{profile.display_name} requires exactly {len(profile.die_sides)} values."
        )

    raw = 0
    for value, sides, label in zip(values, profile.die_sides, profile.die_labels):
        if value < 1 or value > sides:
            raise DiceInputError(f"{label} must be between 1 and {sides}.")
        raw = raw * sides + (value - 1)

    if raw >= profile.accepted_outcomes:
        return RollResult(
            accepted=False,
            raw_value=raw,
            index11=None,
            message="Rejected roll — reroll every die in this profile.",
        )

    return RollResult(
        accepted=True,
        raw_value=raw,
        index11=raw % 2048,
        message="Accepted.",
    )
