# DiceVault 7.0.0 — Core

Offline dice → BIP39 recovery phrase tool.

## What this is
- Physical dice (or OS CSPRNG for testing) mapped to BIP39 words
- Rejection sampling for uniform 11-bit indexes
- Offline verification before entropy and before phrase creation
- Explicit session destroy — no seed storage
- Two profiles: five d6, mixed (d6/d8/d10/d12/d20)

## What this is not
- Not a hardware wallet
- Not a signing device
- Not a vault or portfolio tracker
- Not a guarantee that a compromised PC is safe

## Verification
- Startup self-tests on the BIP39 path
- 30,000 random end-to-end trials (both profiles × 12/24 words):
  primary checksum, independent check, round-trip — 0 failures

## Packages
| File | Purpose |
|------|---------|
| `DiceVault.exe` | Windows GUI (convenience) |
| `source.zip` | Full source tree — prefer this for serious use |
| `SHA256SUMS.txt` | Hashes for the files above |
| `OFFLINE_GUIDE.md` | How to run on a dedicated offline machine |

## Recommended use
1. Dedicated machine that stays offline after install
2. Verify SHA-256 of the download
3. Physical dice, controlled room
4. 24-word phrase for real funds
5. Write words on paper; never type them into a website
6. Import only via a hardware wallet’s official seed entry

## Honest limits
Windows (or any general OS) may use swap, crash dumps, or already-present malware. DiceVault cannot fully control that. For high-value keys, prefer a dedicated offline machine or seed generation on audited hardware.

## License
MIT — see the `LICENSE` file in the repository and in `source.zip`. No warranty.

## Contact
Issues and review: https://github.com/DanDactyl/DiceVault

## Support
If this tool is useful, tips are welcome (optional):

`bc1qtllfee0yh9wzafm5rd336ryue2qjjd3cplv9pm`

No account, no pressure. The software stays free and open either way.
