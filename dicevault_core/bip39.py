"""BIP39 wordlist, mnemonic construction, and validation."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Sequence

from .entropy import APPROVED_PROFILES, evaluate_roll

BIP39_ENGLISH_SHA256 = (
    "2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda"
)


def load_wordlist(path: Path | None = None) -> tuple[str, ...]:
    source = path or Path(__file__).with_name("bip39_english.txt")
    raw = source.read_bytes()
    digest = sha256(raw).hexdigest()
    if digest != BIP39_ENGLISH_SHA256:
        raise RuntimeError("BIP39 English word-list integrity check failed.")

    words = tuple(
        line.strip()
        for line in raw.decode("utf-8").splitlines()
        if line.strip()
    )
    if len(words) != 2048:
        raise RuntimeError(
            f"BIP39 word list must contain 2,048 words; found {len(words)}."
        )
    if len(set(words)) != 2048:
        raise RuntimeError("BIP39 English word list contains duplicate words.")
    if words[0] != "abandon" or words[-1] != "zoo":
        raise RuntimeError("Unexpected BIP39 English word list.")
    return words


def indexes_to_entropy(indexes: Sequence[int], word_count: int) -> bytes:
    if word_count not in (12, 24):
        raise ValueError("Word count must be 12 or 24.")
    if len(indexes) != word_count:
        raise ValueError(f"Exactly {word_count} accepted indexes are required.")
    if any(index < 0 or index > 2047 for index in indexes):
        raise ValueError("Every accepted index must be between 0 and 2,047.")

    entropy_bit_length = 128 if word_count == 12 else 256
    supplied_bits = "".join(f"{index:011b}" for index in indexes)
    entropy_bits = supplied_bits[:entropy_bit_length]
    return int(entropy_bits, 2).to_bytes(entropy_bit_length // 8, "big")


def entropy_to_mnemonic(
    entropy: bytes,
    wordlist: Sequence[str],
) -> tuple[str, ...]:
    entropy_bit_length = len(entropy) * 8
    if entropy_bit_length not in (128, 256):
        raise ValueError("Only 128-bit and 256-bit entropy are supported.")
    if len(wordlist) != 2048:
        raise ValueError("The BIP39 word list must contain exactly 2,048 words.")

    checksum_length = entropy_bit_length // 32
    entropy_bits = f"{int.from_bytes(entropy, 'big'):0{entropy_bit_length}b}"
    checksum_bits = f"{sha256(entropy).digest()[0]:08b}"[:checksum_length]
    combined_bits = entropy_bits + checksum_bits

    return tuple(
        wordlist[int(combined_bits[offset : offset + 11], 2)]
        for offset in range(0, len(combined_bits), 11)
    )


def indexes_to_mnemonic(
    indexes: Sequence[int],
    word_count: int,
    wordlist: Sequence[str],
) -> tuple[str, ...]:
    entropy = indexes_to_entropy(indexes, word_count)
    return entropy_to_mnemonic(entropy, wordlist)


def validate_mnemonic(
    mnemonic: Sequence[str],
    wordlist: Sequence[str],
) -> bool:
    if len(mnemonic) not in (12, 24):
        return False

    index_by_word = {word: index for index, word in enumerate(wordlist)}
    try:
        bits = "".join(f"{index_by_word[word]:011b}" for word in mnemonic)
    except KeyError:
        return False

    entropy_length = 128 if len(mnemonic) == 12 else 256
    checksum_length = entropy_length // 32
    entropy_bits = bits[:entropy_length]
    supplied_checksum = bits[entropy_length:]
    entropy = int(entropy_bits, 2).to_bytes(entropy_length // 8, "big")
    expected_checksum = f"{sha256(entropy).digest()[0]:08b}"[:checksum_length]
    return supplied_checksum == expected_checksum


def validate_mnemonic_independent(
    mnemonic: Sequence[str],
    wordlist: Sequence[str],
) -> bool:
    """Validate BIP39 checksum using an independent integer-based path."""
    word_count = len(mnemonic)
    if word_count not in (12, 24) or len(wordlist) != 2048:
        return False

    lookup = {word: position for position, word in enumerate(wordlist)}
    accumulator = 0
    try:
        for word in mnemonic:
            accumulator = (accumulator << 11) | lookup[word]
    except KeyError:
        return False

    total_bits = word_count * 11
    checksum_bits = total_bits // 33
    entropy_bits = total_bits - checksum_bits

    supplied_checksum = accumulator & ((1 << checksum_bits) - 1)
    entropy_integer = accumulator >> checksum_bits
    entropy = entropy_integer.to_bytes(entropy_bits // 8, "big")
    expected_checksum = int.from_bytes(sha256(entropy).digest(), "big") >> (
        256 - checksum_bits
    )
    return supplied_checksum == expected_checksum


def mnemonic_to_entropy(
    mnemonic: Sequence[str],
    wordlist: Sequence[str],
) -> bytes:
    """Recover entropy only after both BIP39 checksum validators pass."""
    if not validate_mnemonic(mnemonic, wordlist):
        raise ValueError("Mnemonic failed primary BIP39 checksum validation.")
    if not validate_mnemonic_independent(mnemonic, wordlist):
        raise ValueError("Mnemonic failed independent BIP39 checksum validation.")

    lookup = {word: position for position, word in enumerate(wordlist)}
    bits = "".join(f"{lookup[word]:011b}" for word in mnemonic)
    entropy_length = 128 if len(mnemonic) == 12 else 256
    return int(bits[:entropy_length], 2).to_bytes(entropy_length // 8, "big")


def verify_mnemonic_round_trip(
    mnemonic: Sequence[str],
    wordlist: Sequence[str],
) -> bool:
    """Require checksum agreement and exact entropy→mnemonic regeneration."""
    try:
        entropy = mnemonic_to_entropy(mnemonic, wordlist)
    except ValueError:
        return False
    regenerated = entropy_to_mnemonic(entropy, wordlist)
    return tuple(mnemonic) == regenerated


def wipe_int_list(values: list[int]) -> None:
    """Best-effort removal of retained application references."""
    for position in range(len(values)):
        values[position] = 0
    values.clear()


def run_startup_self_tests(wordlist: Sequence[str]) -> tuple[bool, tuple[str, ...]]:
    """Run fast deterministic checks before the UI permits generation."""
    failures: list[str] = []

    try:
        if len(wordlist) != 2048:
            failures.append("word-list length")

        vector12 = entropy_to_mnemonic(bytes(16), wordlist)
        expected12 = tuple(["abandon"] * 11 + ["about"])
        if vector12 != expected12 or not validate_mnemonic(vector12, wordlist):
            failures.append("12-word BIP39 vector")

        vector24 = entropy_to_mnemonic(bytes(32), wordlist)
        expected24 = tuple(["abandon"] * 23 + ["art"])
        if (
            vector24 != expected24
            or not validate_mnemonic(vector24, wordlist)
            or not validate_mnemonic_independent(vector24, wordlist)
            or not verify_mnemonic_round_trip(vector24, wordlist)
        ):
            failures.append("24-word BIP39 vector")

        if (
            not validate_mnemonic_independent(vector12, wordlist)
            or not verify_mnemonic_round_trip(vector12, wordlist)
        ):
            failures.append("12-word independent validation")

        for counter in range(256):
            entropy12 = sha256(
                b"DiceVault-BIP39-12" + counter.to_bytes(2, "big")
            ).digest()[:16]
            phrase12 = entropy_to_mnemonic(entropy12, wordlist)
            if (
                not validate_mnemonic(phrase12, wordlist)
                or not validate_mnemonic_independent(phrase12, wordlist)
                or not verify_mnemonic_round_trip(phrase12, wordlist)
            ):
                failures.append("12-word deterministic compatibility sweep")
                break

            entropy24 = sha256(
                b"DiceVault-BIP39-24" + counter.to_bytes(2, "big")
            ).digest()
            phrase24 = entropy_to_mnemonic(entropy24, wordlist)
            if (
                not validate_mnemonic(phrase24, wordlist)
                or not validate_mnemonic_independent(phrase24, wordlist)
                or not verify_mnemonic_round_trip(phrase24, wordlist)
            ):
                failures.append("24-word deterministic compatibility sweep")
                break

        for profile in APPROVED_PROFILES:
            first = evaluate_roll(profile, [1] * len(profile.die_sides))
            if not first.accepted or first.index11 != 0:
                failures.append(f"{profile.profile_id} first boundary")

            last = evaluate_roll(profile, list(profile.die_sides))
            if last.accepted:
                failures.append(f"{profile.profile_id} rejection boundary")

    except Exception as exc:  # pragma: no cover
        failures.append(type(exc).__name__)

    return (not failures, tuple(failures))
