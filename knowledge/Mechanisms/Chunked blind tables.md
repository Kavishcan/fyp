---
tags: [type/mechanism]
---

# Chunked blind tables (docs/47 addendum)

Each cluster's payload (de-identified text + int8 embeddings) is zlib-compressed and cut into fixed 16 KB chunks; chunk i sealed under the cluster key with i as associated data, listed under its own pseudorandom tag. Sizes hidden without padding every box to the largest.

| Layout | Download, 8 PMC hospitals | MRR P=8 |
|---|---|---|
| padded to largest (first version) | 86 MB (66% padding) | 0.421 |
| chunked + compressed + int8 (default) | **15.0 MB** | 0.423 |

~3 KB per record → ~180 MB at 100 hospitals ([[Scaling of blind unlock]]). Why it lives on the device: fetching only the needed box would reveal which box ([[Blind unlock]]).
