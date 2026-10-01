---
tags: [type/code]
updated: 2026-09-30
---

# client package

Implementation: [device.py](../../backend/client/device.py), [transport.py](../../backend/client/transport.py), [cover.py](../../backend/client/cover.py), [CLI](../../backend/client/__main__.py).

Device owns connect/cache/plan/send/finish. Transports abstract local/MCP nodes. The scheduler now uses one timed run. CLI plans locally before its chosen real tick.

Registry unsigned defaults and arbitrary caller-supplied generators mean privacy-safe configuration is required. See [[Standalone client]], [[Cover traffic]].
