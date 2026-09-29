---
tags: [type/mechanism]
---

# Key epochs and rotation

Each node publishes an epoch id (keyed hash of its OPRF keys); every evaluation reply carries it, so the device re-downloads a table only when that node's keys changed — never because of a question. `PSINode.rotate_keys()` makes every cached copy of the old table permanently unopenable, **provided old secrets are deleted**. Schedules, secure deletion, threshold/hardware keys: [[Future work]].
