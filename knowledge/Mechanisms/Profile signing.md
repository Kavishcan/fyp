---
tags: [type/mechanism]
---

# Profile signing (Ed25519, `nodes/signing.py`)

Proves integrity and key binding of a node's profile, never truthfulness — a signed forged profile verifies ([[Forged profile attack]]). Re-registering under the same key keeps earned trust; a signed node re-serving its profile is a refresh (docs/49).
