"""
DiceVault pure core — no Qt, no network, no persistence.

This package is the portable entropy + BIP39 engine for Option A.
Desktop UI should import from here. Future hardware can re-use or re-implement
the same logic without the desktop ceremony layer.
"""

from .entropy import (
    APPROVED_PROFILES,
    FIVE_D6,
    MIXED_DICE,
    PROFILE_BY_ID,
    PROFILE_BY_NAME,
    DiceInputError,
    EntropyProfile,
    RollResult,
    evaluate_roll,
)
from .bip39 import (
    BIP39_ENGLISH_SHA256,
    entropy_to_mnemonic,
    indexes_to_entropy,
    indexes_to_mnemonic,
    load_wordlist,
    mnemonic_to_entropy,
    run_startup_self_tests,
    validate_mnemonic,
    validate_mnemonic_independent,
    verify_mnemonic_round_trip,
    wipe_int_list,
)
from .session import SessionState

__all__ = [
    "APPROVED_PROFILES",
    "BIP39_ENGLISH_SHA256",
    "DiceInputError",
    "EntropyProfile",
    "FIVE_D6",
    "MIXED_DICE",
    "PROFILE_BY_ID",
    "PROFILE_BY_NAME",
    "RollResult",
    "SessionState",
    "entropy_to_mnemonic",
    "evaluate_roll",
    "indexes_to_entropy",
    "indexes_to_mnemonic",
    "load_wordlist",
    "mnemonic_to_entropy",
    "run_startup_self_tests",
    "validate_mnemonic",
    "validate_mnemonic_independent",
    "verify_mnemonic_round_trip",
    "wipe_int_list",
]

__version__ = "0.1.0-option-a"
