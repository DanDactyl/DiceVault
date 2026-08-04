"""
DiceVault Core — Option A
Offline dice → BIP39 session. No vaults, multisig, or audit platform.
"""

from __future__ import annotations

import secrets
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.network_guard import verify_offline_environment
from dicevault_core import (
    APPROVED_PROFILES,
    FIVE_D6,
    SessionState,
    evaluate_roll,
    indexes_to_mnemonic,
    load_wordlist,
    run_startup_self_tests,
    validate_mnemonic,
    validate_mnemonic_independent,
    verify_mnemonic_round_trip,
    wipe_int_list,
)

APP_NAME = "DiceVault"
APP_VERSION = "7.0.0-core"
WINDOW_TITLE = "DiceVault — Offline Dice Session"

STYLE = """
QWidget { background: #0B1218; color: #E8EEF4; font-family: Segoe UI, sans-serif; font-size: 14px; }
QLabel#title { font-size: 26px; font-weight: 700; color: #F4F7FA; }
QLabel#subtitle { color: #9AA8B5; font-size: 15px; }
QLabel#muted { color: #7A8A99; }
QLabel#statusOk { color: #3DDC97; font-weight: 600; }
QLabel#statusBad { color: #FF6B6B; font-weight: 600; }
QLabel#wordBig { font-size: 28px; font-weight: 700; color: #FF9818; }
QPushButton {
    background: #1A2632; color: #E8EEF4; border: 1px solid #2A3A48;
    border-radius: 8px; padding: 12px 18px; font-weight: 600;
}
QPushButton:hover { background: #243444; }
QPushButton#primary {
    background: #FF9818; color: #111; border: none; font-size: 15px; padding: 14px 22px;
}
QPushButton#primary:hover { background: #FFB04A; }
QPushButton#primary:disabled { background: #5A4630; color: #222; }
QPushButton#danger { background: #3A1A1A; color: #FF8A8A; border: 1px solid #5A2A2A; }
QFrame#card {
    background: #121C26; border: 1px solid #243444; border-radius: 14px;
}
QRadioButton, QCheckBox { spacing: 10px; }
"""


class Page(QWidget):
    def __init__(self, window: "MainWindow", title: str, subtitle: str = "") -> None:
        super().__init__()
        self.window = window
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 36, 48, 36)
        root.setSpacing(16)

        head = QHBoxLayout()
        self.back = QPushButton("← Back")
        self.back.clicked.connect(window.go_back)
        head.addWidget(self.back)
        head.addStretch(1)
        ver = QLabel(f"{APP_NAME}  v{APP_VERSION}")
        ver.setObjectName("muted")
        head.addWidget(ver)
        root.addLayout(head)

        t = QLabel(title)
        t.setObjectName("title")
        t.setWordWrap(True)
        root.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("subtitle")
            s.setWordWrap(True)
            root.addWidget(s)

        self.body = QVBoxLayout()
        self.body.setSpacing(12)
        root.addLayout(self.body, 1)


class HomePage(Page):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window, "Offline Dice Session", "Create a recovery phrase from physical dice. Nothing is saved.")
        self.back.hide()

        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)
        lay.addWidget(QLabel("Physical dice recommended. Offline verification is required before entropy and before the phrase is created."))
        start = QPushButton("START OFFLINE DICE SESSION")
        start.setObjectName("primary")
        start.clicked.connect(lambda: window.goto("security"))
        lay.addWidget(start)
        self.body.addWidget(card)
        self.body.addStretch(1)


class SecurityPage(Page):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__(
            window,
            "Private by design. Honest about limits.",
            "DiceVault does not transmit, save, copy, or intentionally retain your recovery phrase.",
        )
        notes = [
            ("PHYSICALLY OFFLINE", "Use a machine with networking physically disabled when creating real keys."),
            ("CONTROL THE ROOM", "No cameras, screen share, or shoulder surfing."),
            ("DESKTOP LIMIT", "Windows swap, crash dumps, and malware are outside this app's control."),
            ("HARDWARE TARGET", "Dedicated offline hardware remains stronger for high-value keys."),
        ]
        for title, detail in notes:
            card = QFrame()
            card.setObjectName("card")
            lay = QVBoxLayout(card)
            lay.setContentsMargins(18, 14, 18, 14)
            h = QLabel(title)
            h.setStyleSheet("font-weight:700; color:#FF9818;")
            lay.addWidget(h)
            d = QLabel(detail)
            d.setWordWrap(True)
            lay.addWidget(d)
            self.body.addWidget(card)

        go = QPushButton("I Understand — Continue")
        go.setObjectName("primary")
        go.clicked.connect(lambda: window.goto("length"))
        self.body.addWidget(go)


class LengthPage(Page):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window, "Recovery phrase length")
        self.group = QButtonGroup(self)
        for words, label in ((24, "24 words (256-bit) — recommended"), (12, "12 words (128-bit)")):
            rb = QRadioButton(label)
            rb.setProperty("words", words)
            self.group.addButton(rb)
            self.body.addWidget(rb)
            if words == 24:
                rb.setChecked(True)
        nxt = QPushButton("Continue")
        nxt.setObjectName("primary")
        nxt.clicked.connect(self._next)
        self.body.addWidget(nxt)
        self.body.addStretch(1)

    def _next(self) -> None:
        btn = self.group.checkedButton()
        self.window.state.word_count = int(btn.property("words"))
        self.window.goto("source")


class SourcePage(Page):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window, "Entropy source")
        self.group = QButtonGroup(self)
        for key, label in (
            ("physical", "Physical dice — recommended"),
            ("system", "Secure system random (OS CSPRNG)"),
        ):
            rb = QRadioButton(label)
            rb.setProperty("source", key)
            self.group.addButton(rb)
            self.body.addWidget(rb)
            if key == "physical":
                rb.setChecked(True)
        nxt = QPushButton("Continue")
        nxt.setObjectName("primary")
        nxt.clicked.connect(self._next)
        self.body.addWidget(nxt)
        self.body.addStretch(1)

    def _next(self) -> None:
        self.window.state.entropy_source = str(self.group.checkedButton().property("source"))
        self.window.goto("profile")


class ProfilePage(Page):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window, "Dice profile")
        self.group = QButtonGroup(self)
        for profile in APPROVED_PROFILES:
            rb = QRadioButton(
                f"{profile.display_name}  ·  "
                f"{profile.total_outcomes} outcomes, "
                f"{profile.rejected_outcomes} rejected for uniform mapping"
            )
            rb.setProperty("profile_id", profile.profile_id)
            self.group.addButton(rb)
            self.body.addWidget(rb)
            if profile.profile_id == FIVE_D6.profile_id:
                rb.setChecked(True)
        nxt = QPushButton("Continue to offline check")
        nxt.setObjectName("primary")
        nxt.clicked.connect(self._next)
        self.body.addWidget(nxt)
        self.body.addStretch(1)

    def _next(self) -> None:
        pid = str(self.group.checkedButton().property("profile_id"))
        for profile in APPROVED_PROFILES:
            if profile.profile_id == pid:
                self.window.state.profile = profile
                break
        self.window.goto("offline")


class OfflinePage(Page):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__(
            window,
            "Verify offline environment",
            "Required before entropy collection. DiceVault checks links; it does not disable adapters.",
        )
        self.status = QLabel("Not checked yet.")
        self.status.setWordWrap(True)
        self.body.addWidget(self.status)

        self.confirm = QCheckBox(
            "I confirm Ethernet, Wi-Fi, Bluetooth, remote access, and screen recording are off."
        )
        self.confirm.toggled.connect(self._update_continue)
        self.body.addWidget(self.confirm)

        row = QHBoxLayout()
        check = QPushButton("Run offline check")
        check.clicked.connect(self._check)
        row.addWidget(check)
        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setObjectName("primary")
        self.continue_btn.setEnabled(False)
        self.continue_btn.clicked.connect(self._continue)
        row.addWidget(self.continue_btn)
        self.body.addLayout(row)
        self.body.addStretch(1)
        self._ok = False
        self._for_phrase = False

    def reset(self, for_phrase: bool = False) -> None:
        self._for_phrase = for_phrase
        self._ok = False
        self.confirm.setChecked(False)
        self.continue_btn.setEnabled(False)
        self.status.setText("Not checked yet.")
        self.status.setObjectName("muted")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def _check(self) -> None:
        report = verify_offline_environment()
        self._ok = report.verified_offline
        if self._ok:
            self.status.setText("Verified offline: no active physical Wi-Fi/Ethernet and public reachability failed.")
            self.status.setObjectName("statusOk")
        else:
            detail = report.error or "Active network link or public reachability detected."
            self.status.setText(f"Not offline. {detail}")
            self.status.setObjectName("statusBad")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self._update_continue()

    def _update_continue(self) -> None:
        self.continue_btn.setEnabled(self._ok and self.confirm.isChecked())

    def _continue(self) -> None:
        if not (self._ok and self.confirm.isChecked()):
            return
        if self._for_phrase:
            self.window.finalize_phrase()
        else:
            self.window.state.offline_verified_for_entropy = True
            self.window.goto("roll")


class RollPage(Page):
    """Dice entry with mixed-profile labels and secure-roll animation."""

    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window, "Entropy collection")
        self.progress = QLabel()
        self.progress.setObjectName("subtitle")
        self.body.addWidget(self.progress)

        self.profile_note = QLabel()
        self.profile_note.setObjectName("muted")
        self.profile_note.setWordWrap(True)
        self.body.addWidget(self.profile_note)

        self.die_labels: list[QLabel] = []
        self.die_side_labels: list[QLabel] = []
        self.die_values: list[int] = []
        self.die_sides: list[int] = []
        self.dice_row = QHBoxLayout()
        self.dice_row.setSpacing(12)
        self.body.addLayout(self.dice_row)

        self.hint = QLabel()
        self.hint.setObjectName("muted")
        self.hint.setWordWrap(True)
        self.body.addWidget(self.hint)

        row = QHBoxLayout()
        self.gen_btn = QPushButton("Generate secure roll")
        self.gen_btn.clicked.connect(self._start_secure_roll)
        row.addWidget(self.gen_btn)

        self.accept_btn = QPushButton("Accept group")
        self.accept_btn.setObjectName("primary")
        self.accept_btn.clicked.connect(self._accept)
        row.addWidget(self.accept_btn)

        undo = QPushButton("Undo last group")
        undo.clicked.connect(self._undo)
        row.addWidget(undo)

        destroy = QPushButton("Destroy session")
        destroy.setObjectName("danger")
        destroy.clicked.connect(lambda: window.destroy_session())
        row.addWidget(destroy)
        self.body.addLayout(row)

        self.msg = QLabel("")
        self.msg.setWordWrap(True)
        self.body.addWidget(self.msg)
        self.body.addStretch(1)

        # Secure-roll animation state (system random only)
        self.animation_targets: list[int] = []
        self.animation_tick = 0
        self.animation_total_ticks = 24
        self.roll_ready = False
        self.timer = QTimer(self)
        self.timer.setInterval(45)
        self.timer.timeout.connect(self._animation_step)

    def refresh(self) -> None:
        if self.timer.isActive():
            self.timer.stop()

        state = self.window.state
        profile = state.profile
        self.progress.setText(
            f"Accepted {len(state.accepted_indexes)} / {state.word_count} groups · "
            f"Rejected {state.rejected_count} · Source: {state.entropy_source}"
        )

        if profile.profile_id == "mixed_dice":
            self.profile_note.setText(
                "Mixed dice profile — use one of each: "
                "d6, d8, d10, d12, and d20 (in that order)."
            )
        else:
            self.profile_note.setText(
                "Five 6-sided dice (d6 × 5). Roll all five, enter each face, then Accept."
            )

        while self.dice_row.count():
            item = self.dice_row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.die_labels.clear()
        self.die_side_labels.clear()
        self.die_sides = list(profile.die_sides)
        self.die_values = [1] * len(profile.die_sides)
        self.animation_targets = []
        self.roll_ready = state.entropy_source == "physical"

        physical = state.entropy_source == "physical"

        for i, sides in enumerate(profile.die_sides):
            col = QVBoxLayout()
            col.setSpacing(6)

            # Clear die identity: d6 / d8 / d10 / d12 / d20
            label_text = profile.die_labels[i]
            if profile.profile_id == "mixed_dice":
                label_text = f"d{sides}"
            name = QLabel(label_text)
            name.setStyleSheet("font-weight:700; color:#FF9818; font-size:16px;")
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(name)

            range_lab = QLabel(f"1–{sides}")
            range_lab.setObjectName("muted")
            range_lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.die_side_labels.append(range_lab)
            col.addWidget(range_lab)

            val = QLabel("—" if not physical else "1")
            val.setObjectName("wordBig")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val.setMinimumWidth(72)
            self.die_labels.append(val)
            col.addWidget(val)

            br = QHBoxLayout()
            dec = QPushButton("−")
            inc = QPushButton("+")
            dec.setEnabled(physical)
            inc.setEnabled(physical)
            dec.clicked.connect(lambda _=False, idx=i, s=sides: self._bump(idx, -1, s))
            inc.clicked.connect(lambda _=False, idx=i, s=sides: self._bump(idx, 1, s))
            br.addWidget(dec)
            br.addWidget(inc)
            col.addLayout(br)

            wrap = QFrame()
            wrap.setObjectName("card")
            wrap.setLayout(col)
            self.dice_row.addWidget(wrap)

        self.gen_btn.setVisible(not physical)
        self.gen_btn.setEnabled(not physical)
        self.accept_btn.setEnabled(self.roll_ready)
        self.hint.setText(
            "Roll the physical dice shown above, set each face with + / −, then Accept."
            if physical
            else "Generate selects final values first (CSPRNG), then animates the spin. "
            "When the dice stop, review and Accept — or Generate again."
        )
        self.msg.setText("")

    def _bump(self, idx: int, delta: int, sides: int) -> None:
        if self.window.state.entropy_source != "physical":
            return
        self.die_values[idx] = max(1, min(sides, self.die_values[idx] + delta))
        self.die_labels[idx].setText(str(self.die_values[idx]))
        self.roll_ready = True
        self.accept_btn.setEnabled(True)

    def _start_secure_roll(self) -> None:
        """Pick final values first, then animate. Animation never adds entropy."""
        if self.timer.isActive():
            return
        profile = self.window.state.profile
        # Final outcomes chosen before any animation frame
        self.animation_targets = [secrets.randbelow(s) + 1 for s in profile.die_sides]
        self.die_values = list(self.animation_targets)
        self.animation_tick = 0
        self.roll_ready = False
        self.accept_btn.setEnabled(False)
        self.gen_btn.setEnabled(False)
        self.msg.setText("Rolling… values were already selected securely.")
        self.timer.start()

    def _animation_step(self) -> None:
        self.animation_tick += 1
        profile = self.window.state.profile
        # Early ticks: fast random faces; later ticks: settle onto targets
        settling = self.animation_tick > self.animation_total_ticks - 8
        for i, sides in enumerate(profile.die_sides):
            if settling and self.animation_tick >= self.animation_total_ticks - (5 - min(i, 4)):
                shown = self.animation_targets[i]
            else:
                shown = secrets.randbelow(sides) + 1
            self.die_labels[i].setText(str(shown))

        if self.animation_tick >= self.animation_total_ticks:
            self.timer.stop()
            for i, target in enumerate(self.animation_targets):
                self.die_labels[i].setText(str(target))
            self.die_values = list(self.animation_targets)
            self.roll_ready = True
            self.accept_btn.setEnabled(True)
            self.gen_btn.setEnabled(True)
            self.msg.setText("Roll complete — Accept this group or Generate again.")

    def _accept(self) -> None:
        if not self.roll_ready or self.timer.isActive():
            return
        state = self.window.state
        result = evaluate_roll(state.profile, self.die_values)
        if not result.accepted:
            state.rejected_count += 1
            self.msg.setText(result.message + " Generate or enter a new group.")
            if state.entropy_source == "system":
                self.roll_ready = False
                self.accept_btn.setEnabled(False)
                for lab in self.die_labels:
                    lab.setText("—")
            self.progress.setText(
                f"Accepted {len(state.accepted_indexes)} / {state.word_count} groups · "
                f"Rejected {state.rejected_count} · Source: {state.entropy_source}"
            )
            return
        assert result.index11 is not None
        state.accepted_indexes.append(result.index11)
        self.msg.setText(f"Accepted group {len(state.accepted_indexes)} of {state.word_count}.")
        if len(state.accepted_indexes) >= state.word_count:
            self.window.complete_entropy()
        else:
            # Ready for next group — user must Generate again in system mode
            self.refresh()

    def _undo(self) -> None:
        if self.timer.isActive():
            self.timer.stop()
        state = self.window.state
        if not state.accepted_indexes:
            return
        state.accepted_indexes[-1] = 0
        state.accepted_indexes.pop()
        state.final_words = None
        self.refresh()


class WordsPage(Page):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window, "Review recovery words")
        self.index = 0
        self.counter = QLabel()
        self.counter.setObjectName("subtitle")
        self.body.addWidget(self.counter)
        self.word = QLabel("")
        self.word.setObjectName("wordBig")
        self.word.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(self.word)
        row = QHBoxLayout()
        prev = QPushButton("Previous")
        prev.clicked.connect(self._prev)
        row.addWidget(prev)
        nxt = QPushButton("Next word")
        nxt.setObjectName("primary")
        nxt.clicked.connect(self._next)
        row.addWidget(nxt)
        self.body.addLayout(row)
        self.body.addStretch(1)

    def refresh(self) -> None:
        self.index = 0
        self._show()

    def _show(self) -> None:
        words = self.window.state.final_words or ()
        if not words:
            self.word.setText("")
            return
        self.index = max(0, min(self.index, len(words) - 1))
        self.counter.setText(f"Word {self.index + 1} of {len(words)}")
        self.word.setText(words[self.index])

    def _prev(self) -> None:
        self.index -= 1
        self._show()

    def _next(self) -> None:
        words = self.window.state.final_words or ()
        if self.index >= len(words) - 1:
            self.window.goto("full")
        else:
            self.index += 1
            self._show()


class FullPage(Page):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window, "Full phrase review", "Write these down offline. They are not stored by DiceVault.")
        self.list = QLabel()
        self.list.setWordWrap(True)
        self.list.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.body.addWidget(self.list)
        nxt = QPushButton("I have written them down — continue")
        nxt.setObjectName("primary")
        nxt.clicked.connect(lambda: window.goto("confirm"))
        self.body.addWidget(nxt)
        self.body.addStretch(1)

    def refresh(self) -> None:
        words = self.window.state.final_words or ()
        lines = [f"{i + 1:>2}.  {w}" for i, w in enumerate(words)]
        self.list.setText("\n".join(lines))

    def clear(self) -> None:
        self.list.setText("")


class ConfirmPage(Page):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window, "Final verification")
        self.checks = [
            QCheckBox("Every word is spelled correctly."),
            QCheckBox("Every word is in the correct numbered position."),
            QCheckBox("The backup contains exactly 12 or 24 words."),
        ]
        for c in self.checks:
            c.toggled.connect(self._update)
            self.body.addWidget(c)
        self.done = QPushButton("Verified — destroy session")
        self.done.setObjectName("primary")
        self.done.setEnabled(False)
        self.done.clicked.connect(window.finish_verified)
        self.body.addWidget(self.done)
        self.body.addStretch(1)

    def reset(self) -> None:
        for c in self.checks:
            c.setChecked(False)
        self._update()

    def _update(self) -> None:
        self.done.setEnabled(all(c.isChecked() for c in self.checks))


class DonePage(Page):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window, "Session destroyed")
        self.back.hide()
        self.body.addWidget(QLabel(
            "The recovery phrase was verified and the in-memory session was destroyed.\n"
            "DiceVault retains no seed data. Reconnect networking only after you leave this screen."
        ))
        home = QPushButton("Return to home")
        home.setObjectName("primary")
        home.clicked.connect(lambda: window.goto("home"))
        self.body.addWidget(home)
        self.body.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(960, 720)

        self.wordlist = load_wordlist(
            Path(__file__).resolve().parent / "dicevault_core" / "bip39_english.txt"
        )
        passed, failures = run_startup_self_tests(self.wordlist)
        self.self_tests_passed = passed
        if not passed:
            QMessageBox.critical(
                self,
                "Self-tests failed",
                "Startup self-tests failed:\n" + "\n".join(failures),
            )

        self.state = SessionState()
        self.history: list[str] = []

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.pages: dict[str, Page] = {}
        self.offline_page = OfflinePage(self)
        self.roll_page = RollPage(self)
        self.words_page = WordsPage(self)
        self.full_page = FullPage(self)
        self.confirm_page = ConfirmPage(self)

        for name, page in (
            ("home", HomePage(self)),
            ("security", SecurityPage(self)),
            ("length", LengthPage(self)),
            ("source", SourcePage(self)),
            ("profile", ProfilePage(self)),
            ("offline", self.offline_page),
            ("roll", self.roll_page),
            ("words", self.words_page),
            ("full", self.full_page),
            ("confirm", self.confirm_page),
            ("done", DonePage(self)),
        ):
            self.pages[name] = page
            self.stack.addWidget(page)

        if not self.self_tests_passed:
            for name, page in self.pages.items():
                if name != "home":
                    page.setEnabled(False)

        self.goto("home", record=False)

    def goto(self, name: str, record: bool = True) -> None:
        current = self.current_name()
        if record and current and current != name:
            self.history.append(current)
        if name == "length" and current in {"home", "security"}:
            self.begin_session()
        if name == "roll":
            self.roll_page.refresh()
        elif name == "words":
            self.words_page.refresh()
        elif name == "full":
            self.full_page.refresh()
        elif name == "confirm":
            self.confirm_page.reset()
        elif name == "offline":
            pass
        self.stack.setCurrentWidget(self.pages[name])

    def current_name(self) -> str | None:
        w = self.stack.currentWidget()
        for name, page in self.pages.items():
            if page is w:
                return name
        return None

    def go_back(self) -> None:
        current = self.current_name()
        if current == "roll" and self.state.accepted_indexes:
            answer = QMessageBox.question(
                self,
                "Discard rolls?",
                "Going back erases accepted entropy groups. Continue?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            wipe_int_list(self.state.accepted_indexes)
            self.state.rejected_count = 0
            self.state.final_words = None
            self.state.offline_verified_for_entropy = False

        if self.history:
            prev = self.history.pop()
            self.goto(prev, record=False)
            return
        fallback = {
            "security": "home",
            "length": "security",
            "source": "length",
            "profile": "source",
            "offline": "profile",
            "roll": "offline",
            "words": "roll",
            "full": "words",
            "confirm": "full",
        }.get(current or "", "home")
        self.goto(fallback, record=False)

    def begin_session(self) -> None:
        self.state = SessionState()
        self.full_page.clear()

    def complete_entropy(self) -> None:
        report = verify_offline_environment()
        if report.verified_offline:
            self.finalize_phrase()
            return
        self.offline_page.reset(for_phrase=True)
        self.goto("offline")

    def finalize_phrase(self) -> None:
        state = self.state
        if len(state.accepted_indexes) != state.word_count:
            QMessageBox.critical(self, "Incomplete", "Not enough entropy groups.")
            return
        words = indexes_to_mnemonic(state.accepted_indexes, state.word_count, self.wordlist)
        if not (
            validate_mnemonic(words, self.wordlist)
            and validate_mnemonic_independent(words, self.wordlist)
            and verify_mnemonic_round_trip(words, self.wordlist)
        ):
            self.destroy_session(force=True)
            QMessageBox.critical(self, "BIP39 validation failed", "Session destroyed.")
            return
        state.final_words = words
        self.goto("words")

    def finish_verified(self) -> None:
        self.state.destroy()
        self.full_page.clear()
        self.words_page.word.setText("")
        self.history.clear()
        self.goto("done", record=False)

    def destroy_session(self, force: bool = False) -> None:
        has = bool(self.state.accepted_indexes or self.state.final_words)
        if has and not force:
            answer = QMessageBox.question(
                self,
                "Destroy session",
                "Destroy all accepted rolls and any generated phrase?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.state.destroy()
        self.full_page.clear()
        self.words_page.word.setText("")
        self.history.clear()
        self.goto("home", record=False)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.state.accepted_indexes or self.state.final_words:
            answer = QMessageBox.question(
                self,
                "Exit",
                "Destroy the in-memory session and exit?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        self.state.destroy()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
