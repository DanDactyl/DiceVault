# DiceVault Core — Option A

Offline dice → BIP39 recovery phrase tool.

**What this is**
- Physical dice (or secure system random) entropy
- Unbiased rejection sampling
- Offline checks before entropy and before phrase creation
- Backup verification, then session destroy
- No seed storage, no vaults, no multisig, no audit platform

**What this is not**
- Not a hardware wallet
- Not a vault manager
- Not a multisig coordinator

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest tests -q
python main.py
```

## Flow

1. Security notice  
2. Phrase length (12 / 24)  
3. Entropy source  
4. Dice profile  
5. Offline verification  
6. Enter / accept dice groups  
7. Silent offline recheck → create phrase  
8. Word review → full review → confirm  
9. Destroy session  

## Honest limit

This is desktop software. Windows swap, malware, and screen capture are outside its control. Dedicated offline hardware remains stronger for high-value keys.
