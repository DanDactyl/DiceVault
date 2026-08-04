"""Pure-core tests for Option A recovery package."""

from __future__ import annotations

from collections import Counter
from itertools import product
from pathlib import Path

import pytest

from dicevault_core import (
    APPROVED_PROFILES,
    FIVE_D6,
    MIXED_DICE,
    SessionState,
    entropy_to_mnemonic,
    evaluate_roll,
    load_wordlist,
    run_startup_self_tests,
    validate_mnemonic,
    validate_mnemonic_independent,
    verify_mnemonic_round_trip,
)

WORDLIST = load_wordlist(
    Path(__file__).resolve().parents[1] / "dicevault_core" / "bip39_english.txt"
)


def all_rolls(profile):
    ranges = [range(1, sides + 1) for sides in profile.die_sides]
    return product(*ranges)


def test_profile_definitions_are_locked() -> None:
    assert FIVE_D6.die_sides == (6, 6, 6, 6, 6)
    assert MIXED_DICE.die_sides == (6, 8, 10, 12, 20)


@pytest.mark.parametrize("profile", APPROVED_PROFILES)
def test_exhaustive_mapping_is_uniform(profile) -> None:
    counts = Counter()
    rejected = 0
    for values in all_rolls(profile):
        result = evaluate_roll(profile, values)
        if result.accepted:
            counts[result.index11] += 1
        else:
            rejected += 1
    assert rejected == profile.rejected_outcomes
    assert len(counts) == 2048
    assert set(counts.values()) == {profile.accepted_outcomes // 2048}


def test_official_zero_entropy_vectors() -> None:
    phrase12 = entropy_to_mnemonic(bytes(16), WORDLIST)
    phrase24 = entropy_to_mnemonic(bytes(32), WORDLIST)
    assert phrase12 == tuple(["abandon"] * 11 + ["about"])
    assert phrase24 == tuple(["abandon"] * 23 + ["art"])
    assert validate_mnemonic(phrase12, WORDLIST)
    assert validate_mnemonic(phrase24, WORDLIST)
    assert validate_mnemonic_independent(phrase12, WORDLIST)
    assert verify_mnemonic_round_trip(phrase24, WORDLIST)


def test_startup_self_tests_pass() -> None:
    passed, failures = run_startup_self_tests(WORDLIST)
    assert passed, failures


def test_session_destroy_clears_secrets() -> None:
    state = SessionState()
    state.accepted_indexes = [1, 2, 3, 4]
    state.final_words = ("abandon", "ability")
    state.offline_verified_for_entropy = True
    state.rejected_count = 9
    state.destroy()
    assert state.accepted_indexes == []
    assert state.final_words is None
    assert state.rejected_count == 0
    assert state.offline_verified_for_entropy is False
