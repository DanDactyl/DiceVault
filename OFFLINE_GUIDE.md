# DiceVault — Run It Truly Offline

One-page guide for real seed creation.

DiceVault turns physical dice into a BIP39 recovery phrase. It does not store
your seed. You are responsible for the machine you run it on.

## 1. Choose a trusted machine

Use a computer (or Raspberry Pi) that will not go online after setup.

Good options:
- Spare laptop you can leave offline forever
- Raspberry Pi dedicated to this job
- Clean install of Linux or Windows used only for seed work

Do not use your daily internet PC for high-value keys.

## 2. Install once, then cut the network

While online (this is the last time):

1. Download DiceVault from the official GitHub Release
2. Verify the file hash against SHA256SUMS.txt
3. Install or copy the app
4. Confirm it opens and core self-tests pass

Then:
- Turn off Wi-Fi and Bluetooth
- Unplug Ethernet
- Prefer: disable adapters in the OS or remove the Wi-Fi hardware

From this point on, treat the machine as air-gapped.

## 3. Prepare the room

- No phones pointing at the screen
- No screen sharing or recording
- No other people reading the display
- Paper and pen only for the words

## 4. Run the session

1. Open DiceVault
2. Read the security notice — continue only if you accept the limits
3. Choose 24 words for serious funds (12 is fine for learning)
4. Prefer Physical dice
5. Pick a profile:
   - Five d6 — five standard six-sided dice
   - Mixed — one each of d6, d8, d10, d12, d20
6. Complete the offline check
7. Roll, enter faces (or use secure system roll only for testing)
8. Accept groups until complete
9. Review words one at a time, then the full list
10. Write them on paper — verify spelling and order
11. Confirm backup — the session is destroyed

DiceVault should retain nothing when you finish.

## 5. Afterward

- Store the paper backup securely (metal backup optional)
- Import into a hardware wallet only through that device’s official seed entry
- Never type the words into a website, phone app, or online “checker”
- Reconnect this machine to a network only if you accept that it is no longer
  a pure offline box

## Honest limits

DiceVault verifies offline links and destroys its session. It cannot protect you
from malware already on the PC, a compromised operating system, or cameras and
shoulder surfing.

For large amounts, a dedicated offline machine (or generating the seed on a
reputable hardware wallet with fixed, audited firmware) is stronger than a
general-purpose computer.

## Quick checklist

- [ ] Dedicated or spare machine
- [ ] App installed, hash checked
- [ ] Network disabled
- [ ] Room controlled
- [ ] Physical dice ready
- [ ] 24-word phrase written and verified
- [ ] Session destroyed
- [ ] Words never entered online

Your dice. Your words. Nothing stored.