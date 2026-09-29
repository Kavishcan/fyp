---
tags: [type/mechanism]
---

# Role-based access ("tolap", docs/45)

Documents belong to collections (public, research, clinical_notes). The signed profile publishes `access_policy` (role → collections); a client's roles live only in the node's allow-list. **One OPRF key per collection**: an unpermitted collection is never evaluated, so its boxes never open. Blind tables include restricted collections only for permitted roles. Built in rather than an external LDAP/OPA product. Results: [[RBAC results]]. See [[Role-scoped publication]].
