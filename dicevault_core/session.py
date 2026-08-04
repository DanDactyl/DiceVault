"""Minimal secret-session state for Option A."""

from __future__ import annotations

from dataclasses import dataclass, field

from .bip39 import wipe_int_list
from .entropy import FIVE_D6, EntropyProfile


@dataclass
class SessionState:
    word_count: int = 24
    entropy_source: str = "physical"
    profile: EntropyProfile = FIVE_D6
    offline_verified_for_entropy: bool = False
    accepted_indexes: list[int] = field(default_factory=list)
    rejected_count: int = 0
    final_words: tuple[str, ...] | None = None

    def destroy(self) -> None:
        """Clear active secret-session references (best effort)."""
        wipe_int_list(self.accepted_indexes)
        self.rejected_count = 0
        self.final_words = None
        self.offline_verified_for_entropy = False
