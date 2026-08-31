# Baseline selection and evidence quality

## Supervisor-aligned decision

Reuse a suitable published router instead of rebuilding standard source routing
from zero. The existing router is the baseline platform. Student implementation
effort goes into routing-leakage measurement, the privacy mechanism, the
privacy-utility-cost evaluation and the interaction with trust defence.

```text
Published source router
  -> reproduce on FeB4RAG
  -> record routing quality and cost
  -> measure A1/A2 leakage
  -> add proposed privacy layer
  -> repeat the same attacks and metrics
  -> integrate A3/TASR
  -> evaluate privacy-trust interference
```

## Selected works

| Work | Publication/evidence status | Fit | Project role |
|---|---|---|---|
| RAGRoute | Peer-reviewed EuroMLSys 2025 / later revised work; public code | Direct federated knowledge-source routing | Primary routing baseline and platform |
| RAGRouter | NeurIPS 2025 Main Conference; public code/data | Routes among RAG-enabled language models, not knowledge silos | Strong adjacent method; optional methodology comparison |
| Routing Hijacking + TASR | 2026 arXiv preprint with public attack/defence code | Direct routing-security fit | Core emerging evidence for A3, HERouter and trust baseline |
| Broadcast | Standard control | Direct | Maximum coverage/exposure/cost baseline |
| Random top-k | Standard control | Direct | Weak selection baseline |
| Cosine top-k | Transparent local control | Direct | Training-free relevance baseline |
| Oracle | qrel-derived upper bound | Direct | Maximum achievable source-selection reference |

Author H-index is not used as the main evidence criterion. Rank evidence by direct
relevance, publication status/venue, methodological quality, experimental strength,
reproducibility, code/data availability and recency. Recent preprints are valuable
for the research frontier but should be supported by peer-reviewed and foundational
work.

## Direct benchmark eligibility

Open source code is ideal but not mandatory. A method is eligible for a direct
benchmark when the project can:

- register or configure the same knowledge sources;
- submit the same test queries;
- obtain ranked/selected source IDs;
- set or observe top-k;
- measure latency and sources contacted;
- execute repeated programmatic runs;
- comply with the licence and access conditions.

Executable software, a package, model checkpoint or hosted API can satisfy these
conditions. A fixed online demo normally cannot. Published aggregate results alone
are literature comparison and cannot be placed beside project results as though
the conditions were identical.

## Reproduction checklist

For each direct baseline save:

| Field | Required record |
|---|---|
| Upstream identity | Repository/package/API and exact commit/version |
| Status | Peer-reviewed venue or preprint |
| Licence | Permitted use and adaptation |
| Environment | OS, Python, dependencies and model versions |
| Data | Dataset version, source construction and split manifest |
| Parameters | Embedding model, top-k, thresholds and random seed |
| Hardware | CPU/GPU/RAM relevant to latency |
| Interface | Inputs, ranked outputs, scores and metrics available |
| Command | Exact reproduction command/configuration |
| Adaptation | Every local change required to run the comparison |
| Result | Raw per-query routing output plus aggregate metrics |

## Fallback order

1. Use official runnable implementation directly.
2. Use checkpoint/package/API as a black-box baseline.
3. Reimplement only the minimal published routing logic when necessary.
4. If comparability remains impossible, report the paper only in related work and
   retain broadcast, random, cosine and oracle as direct controls.

## Primary links

- RAGRoute code: https://github.com/sacs-epfl/ragroute
- RAGRoute paper: https://doi.org/10.1145/3721146.3721942
- RAGRouter paper: https://proceedings.neurips.cc/paper_files/paper/2025/hash/1759a83b007f0685c3fbc460fa1b6395-Abstract-Conference.html
- RAGRouter code: https://github.com/OwwO99/RAGRouter
- Routing Hijacking/TASR code: https://github.com/Junjie-Mu/routing-hijacking-fedrag
- Routing Hijacking preprint: https://arxiv.org/abs/2605.28112
