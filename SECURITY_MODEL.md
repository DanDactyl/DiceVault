# DiceVault Security Model — Option A (Core Ceremony)

**Product identity**  
DiceVault Core is a desktop offline dice → BIP39 ceremony tool.  
It generates a checksum-valid recovery phrase from physical dice with strong process controls, then destroys the secret session.

It is **not** a vault manager, audit platform, or multisig coordinator on the default path.

---

## Intentionally absent (default path)

- Network transmission of secrets
- Telemetry or analytics
- Cloud integration
- Seed / mnemonic storage
- Entropy / dice-value storage
- Ceremony identity records
- Clipboard export of secrets
- Printing of secrets
- Private QR export of secrets
- Automatic updates that could touch secret state
- Automatic crash-report upload

---

## Fixed entropy profiles only

1. Five ordered d6 dice  
2. Ordered d6, d8, d10, d12, d20  

Custom profiles are rejected. Fixed profiles keep exhaustive distribution testing practical.

---

## Secret lifecycle

1. Secrets are created as late as possible.  
2. The mnemonic does not exist until offline verification has succeeded and entropy collection is complete.  
3. The mnemonic is validated before display.  
4. Backup verification is required before final destruction.  
5. Session destruction removes retained application references as a best effort.  
6. Secrets are destroyed before any completion / report UI that could encourage retention.

Python and a general-purpose OS cannot guarantee physical memory erasure (swap, crash dumps, display buffers, interpreter copies). Destruction is therefore best-effort, not a cryptographic wipe claim.

---

## Offline policy

- Offline verification is required before entropy collection.  
- Offline state is silently rechecked before mnemonic construction.  
- DiceVault verifies network state; it does not disable adapters or drivers on the Option A path.  
- Physical air-gap, closed remote-access tools, and a controlled room remain the user’s responsibility.  
- A small ONLINE/OFFLINE badge is informational only and is not the security gate.

---

## Anonymity default

- No ceremony ID is assigned on the default path.  
- No persistent vault record is written on the default path.  
- No audit certificate is produced unless the user explicitly opts in.  
- Any export or identity feature must be explicit and opt-in.

---

## Approved promise

> DiceVault is designed not to transmit, save, copy, print, or intentionally retain your recovery phrase on the default path. For strongest privacy, use a dedicated offline hardware environment.

---

## Honest limit

This remains desktop software. Malware, screen recording, accessibility tools, remote desktop, swap, and forensic imaging of the host are outside DiceVault’s control. Dedicated stateless hardware remains the stronger long-term target.
