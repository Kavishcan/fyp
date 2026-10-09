# Repository guidance

The authoritative statement of what is implemented, measured and claimed is
docs/41-current-system-specification.md; docs 04, 07–08 and 13–17 are
historical and carry a status line. `decoy_policy="cells"` (docs/40) is now
a select_dispatch option and a QueryRequest field alongside "topic_stable".
The API default remains legacy; the studio (frontend) defaults to blind
unlock (P=8) + hybrid rerank + evidence_top_k=2 with every mode selectable and labelled. Paillier encrypted scoring (docs/34) is an
experimental in-cluster tier, disabled by default, not the mechanism.
Preserve the negative v2 results. Do not resume the evidence-budget direction.

## Current research direction

Docs/57: C-FedRAG-style answers (eval/run_cfedrag_style.py; corpus from
eval/build_pubmed_subset.py: 23,247 NCBI abstracts + 17,277 BM25-selected
MedRAG Textbooks snippets; 8 k-means hospitals; Qwen3.5-9B; 8 passages).
All 1,118 MIRAGE PubMedQA + BioASQ: closed-book 0.686, broadcast
(C-FedRAG-style) = centralized 0.842, selective top-2 0.833 (topic 0.637 vs
floor 0.184), FedSafeRAG P=8 0.822 (-0.020, p<0.001, significant), P=24
0.834 (-0.007, p=0.11, n.s.); FedSafeRAG topic 0.166 at floor, 0 hospitals
read the question; records 124 (P=8) / 362 (P=24) vs 64 broadcast; hospital
CPU 72/211 ms vs 103 ms broadcast incl. per-hospital query embedding; 96 MB
one-time tables. Secondary evidence; never compare with C-FedRAG's 72.51.
"FedSafeRAG" is the system name for the blind-unlock design in all writing.

Docs/56: Gap 3, source content released per question (eval/run_release.py,
PMC 986 q, hybrid). Default blind (clusters 10/5, P=8) unlocks 140 records
for a top-10 (14x, release precision 1.2%); broadcast returns 80 (but every
hospital reads the question). Clusters 5/5 at P=16: MRR 0.5274 vs 0.5248 for
10/5 P=16 (n.s.) with 218 vs 268 records (-19%), same 5-patient minimum.
Smaller minimums cut release (3/2 P=8: 57) but centroids within cosine 0.95
of one patient rise 3.6% -> 7.2% (5/5) -> 17.2% (5/3) -> 49.4% (3/2); none
within 0.99. Defaults unchanged. Scope (2026-10-02): privacy + retrieval
quality only; generation/MIRAGE is not headline evidence.

Docs/55: large hospitals. Blind unlock's per-question cost is independent
of corpus size; the one-time table download is not (~1.1x the text; 100 GB
text -> ~110 GB). Tier 2 (privacy/pir.py SimplePIR, n=1024, q=2^32, p=256;
PSINode.pir_database, blind_unlock.pir_unlock, recommended_tier): download
a fixed hint (per_column x 67 MB) + tag map, fetch sealed chunks with exactly
F PIR queries per hospital (padded), OPRF unchanged. PMC 986 q: identical
top-10 100%, MRR 0.5062 both, but tier 2 costs 538 MB hints vs 11.3 MB
tables (small hospitals stay tier 1). Measured 1 GB: 67 MB hint, 2.5 MB/q,
0.6 s hospital; 2 GB: 135 MB, 1.2 s. 100 GB EXTRAPOLATED: ~1.2 GB once,
~22 MB/q, ~66 s one core per question. Not wired into MCP/client; numpy
prototype; never call it new (SimplePIR, Tiptoe).

Docs/54: `Deidentifier(level="safe_harbor")` (opt-in; node JSON
"deid_level"; default "basic" byte-identical) adds labelled
account/plan/licence/vehicle/device numbers, fax, partial dates (month-year
-> year), institutions, residence/postcodes, uncued names. Held-out synthetic
benchmark on real PMC prose (eval/run_deid_benchmark.py; dev/test/test2
templates and name pools disjoint). Headline = FRESH test2, run once:
recall 0.459 (basic + NER, the docs/46-53 node setting) -> 0.832
(safe_harbor + NER) -> 0.853 (+ registry). test v1 was 0.528 -> 0.975 before
its gaps were fixed (now 1.000, no longer held out). Rules do not generalise
to unseen phrasing; NER (spaCy sm) added nothing on test2. Uncued
towns/names use privacy/data/common_words.txt.gz (eval/build_common_words.py).
Clean reports altered 13.8% -> 28.9% (mostly real dates/places/companies);
centralized PMC MRR 0.4433 -> 0.4401 (n.s.). Not a validated
de-identifier; never "HIPAA compliant".

Docs/53: published systems on PMC (593 test queries, 30/10/60 split for
RAGRoute's router): RAGRoute (MIT, router copied; cross-encoder replaced) and
Flower FedRAG (Apache-2.0, merge + IVF client copied), backend/baselines/
external_fedrag.py, eval/run_external_baselines.py. Cost at 8/16/32 hospitals
(k-means): bge broadcast hospital CPU 287/542/1,112 ms and 275 KB/0.55/1.1 MB
per question; blind P8 68/137/274 ms and 9/18/37 KB (~4x less CPU, ~30x less
traffic). RAGRoute hospitals only search (~0.1 ms; the coordinator sends text
AND embedding), so blind is NOT cheapest in hospital CPU, and NOT fastest
(modelled 112-148 ms vs 50-114). RAGRoute topic 0.562 vs floor 0.226; on
Dirichlet/random its router (AUC 0.852/0.583) contacts 5.5/7.4 of 8 at
0.95-1.28 MB. Blind P8 hybrid beats RAGRoute hybrid on k-means (+0.04-0.06)
but loses on Dirichlet/random (-0.05/-0.09); P24 ties or beats. Latency is a
model; hospital CPU is one Apple M5. Blind discloses more records (139) than
broadcast (80). Say "privacy at comparable cost", never "cheapest".

Docs/50: robustness, significance, sessions, answers. Blind unlock at the
pattern floor on k-means/Dirichlet/random splits and over 5-question
sessions (router/decoys climb to 0.50–0.57; cells leak on Dirichlet 0.294
vs floor 0.210). Hybrid MRR vs HyFedRAG-style hybrid: P=8 94%/86%/81%,
P=24 98%/97%/97% (k-means/Dirichlet/random); P=24 n.s. on k-means only.
Blind beats PSI+cells by ~+0.07 on every split. MIRAGE: blind 0.613 vs
closed-book 0.547, p=0.035; hybrid does NOT help MIRAGE (0.573); the
broadcast rerun (0.540) is not comparable (machine contention). Result
files archived in docs/results/. Always quote the split with a retrieval
ratio; never "94–98%" alone.

Docs/52: standalone client (backend/client/: Device, CoverTrafficScheduler,
MCPTransport/LocalTransport, `python -m client`). The query path runs on the
user's machine with no server; `privacy/blind_unlock.blind_round` is the one
round implementation (the API coordinator calls it too). Cover rounds (P
dummies to every node) are identical to real rounds on the wire; the
scheduler sends one round per tick, planning happens at submit time, daily
fetches on the tick. Per-question leakage to nodes/observers: credential id
active at a fixed rate. Budget cost: ticks/day x P per node.

Docs/49: security audit. Three no-credential holes, each confirmed on a
real MCP node and now a regression test (tests/test_audit_fixes.py):
Paillier scorer exposed on every node (3 requests stole all embeddings incl.
restricted) — now off by default, never on gated nodes, public rows only;
open text/vector retrieve on gated nodes (top_n=100000 dumped the corpus) —
refused unless `open_retrieval`, top_n capped 20; budget/audit in memory
(spawn-per-call served 6 of a budget of 2) — now SQLite `<node>.usage.sqlite`.
docs/43's enumeration bound was not true of real MCP nodes before this fix.
Unfixed and stated: cell churn and self-declared cell labels, shared HMAC
key across nodes, replay within a day, psi_envelopes size leak, Sybil
registration, prompt injection, de-identification gaps.

Docs/48: device-side hybrid rerank (router/hybrid_rerank.py): z(cosine) +
0.5·z(BM25), BM25 statistics from the pool the device holds only. API
`rerank="dense"|"hybrid"` (default dense, earlier results unchanged;
studio default hybrid), applies to blind pool ranking and the evidence
rerank. PMC-Patients, matched ranking: HyFedRAG-style hybrid 0.543, blind
unlock hybrid 0.509/0.526/0.535 at P=8/16/24 (dense 0.421/0.431/0.437),
centralized hybrid 0.555; held-out-half MRR reported (weight chosen on the
first half). Lead with the matched comparison; "beats HyFedRAG" is only
true against its dense ranker and must say so. No significance test yet.

Docs/47: blind unlock, `routing_mode="blind"` (privacy/blind_unlock.py;
psi.label_tag, dummy_point, PSINode.blind_table/epoch/rotate_keys; node tool
psi_table). Offline, every node's encrypted cluster table (OPRF-derived
lookup tags, float16 payloads padded to one length, deterministic sealing,
restricted collections only to permitted roles) is downloaded once per key
epoch. Per question the device takes the global top-P clusters across all
nodes and sends EXACTLY P blinded points to EVERY node, real r·H(c) or dummy
r·G (same distribution), in sorted node order; replies are unblinded and
envelopes opened by tag lookup. PMC-Patients (docs/46 setup): question to 0
hospitals, topic at the floor 0.239 at every P; MRR 0.399/0.421/0.431/0.437
at P=4/8/16/24 (HyFedRAG-style 0.444), 74–393 records disclosed, device
22–132 ms, slowest hospital 5–29 ms, a few KB per question. One-time
download 86 MB with the first padded layout, now 15.0 MB: tables are
zlib-compressed, cut into 16 KB chunks with per-chunk tags, int8 embeddings
(MRR unchanged, docs/47 addendum). Budgets count dummies. Known pieces: the offline/online
OPRF core IS unbalanced labeled PSI with precomputation (Kiss et al. PoPETs
2017; Chen-Laine-Rindal 2018), plus Wally-style fake queries; the additions
are the multi-owner setting (identical cover probes to every owner,
cross-owner cluster selection, per-role keys). Never call blind unlock a new
protocol or new cryptography.
Semi-honest nodes; timing not measured; records of the P unlocked clusters
still reach the device (de-identified). The docs/43 budget now
persists (docs/49).

Docs/46: HyFedRAG-style design (broadcast, raw edge retrieval, server
fusion, stock Presidio) vs this project on PMC-Patients (545 MB CSV, user
approved; backend/vendor/pmc_patients/), patient-to-patient retrieval with
cross-article relevance only, 5,000 patients in 8 k-means hospitals, 986
queries. HyFedRAG-style MRR 0.444 = centralized, topic at floor 0.239, but
question text to all 8 hospitals; cosine top-4 MRR 0.444, topic 0.318;
ours PSI+cells MRR 0.350 (−0.062 from PSI bucketing, −0.032 from cells),
question to 0 hospitals, topic 0.254. Stock Presidio altered 84.1% of clean
case reports vs ours 11.7%. It is a reimplementation of the described
design, not HyFedRAG's code; not comparable to its published numbers.
Report the 1,000-query run (a 300-query run gave cells 0.383 — unstable).

Docs/45: role-based access to node collections. Documents carry a
collection (`public` default); the node's signed profile publishes
`access_policy` (role -> collections) and `cluster_collections`; client
roles live only in the node allow-list (`roles` per client). Enforcement is
inside PSI: one OPRF key per collection (privacy/psi.PSINode.keys,
`<node>.psi.key` JSON, 0600), and `evaluate_for` evaluates only permitted
collections, so an unpermitted envelope can never open whatever ids are
probed. Unauthenticated legacy/v2 retrieve serves `public` only. Measured
(eval/run_rbac.py): access matrix equals the policy exactly; a client lying
about its role gains 0. Role-scoped publication: the signed profile
(routing centroids, topics, doc count, cluster centroids) is built from
public documents only; restricted centroids come from the node tool
`get_restricted_centroids(auth)`, allow-list checked and Ed25519-signed —
clinical centroids visible 1.000 → 0.000 to unpermitted roles. A node with
no public documents still publishes from restricted content. No LDAP/OPA,
no attribute/consent rules. Single-collection nodes are byte-identical.

Docs/44: nodes previously served RAW documents — redaction ran only inside
embed_documents, so vectors were clean but retrieve results and PSI
envelopes carried PII (authorised client recovered 100% of injected
names/MRN/DOB/phone/email). Nodes now de-identify once at load
(privacy/deidentify.Deidentifier, from nodes/mcp_server and
nodes/simulator) before embedding, profile, cluster table and serving:
cued records leak 0%; bare names leak 100% under rules alone and 0% with the
node's own registry (`known_identifiers`). Clean-text cost: 1–2% of
documents altered, dense recall@10 unchanged. No bare ABC-123 id rule (hits
compounds/cell lines); institutions add formats via `id_patterns`. Optional
NER: `presidio_backend()` (Presidio + spaCy en_core_web_sm, node config
`"ner": "presidio"`), PERSON full names only — bare names leaked 1.000 →
0.126, 7% of clean docs altered, recall unchanged; stock PERSON+LOCATION
altered 66% and is not the default. Not a validated clinical de-identifier;
a clinical transformer (~440 MB) is the stated production choice, not
installed. Do not say "PII is removed" without "rules + registry + NER,
~13% of uncued unregistered names missed".

Docs/43: the PSI step is gated by a federation credential
(privacy/credentials.py): HMAC over (node id, UTC day, blinded points),
node-side allow-list `<node>.clients.json` with a per-client daily
evaluation budget and an audit line per request; refusal happens before the
OPRF key is touched, so it leaks nothing. Absent allow-list = open node
(prior behaviour). Measured with the real gate: dumping a 150–200-cluster
node takes 8–10 days of one credential's 20-evaluation budget, logged under
that id. The node learns which credential asked, never what; anonymous
credentials are the stated direction. TLS is deployment configuration, not
built, and changes no measured number.

Docs/42: the docs/32 ablation re-run with trust as a RANKING term
(`V2Config.trust_weight`, relevance + w·(trust−0.5)). At w=0.5 the forged
attacker's selection falls 0.520 → 0.362 and keeps falling over the stream
(0.42 → 0.30) for 1.4 points of honest recall; larger weights are flat on
the attacker and cost recall. The floor is the trust signal's 0.11 gap, not
the weight. Recommended setting 0.5; default stays 0 so every earlier result
is byte-identical. This is the first routing-level A3 result; it is a
one-third reduction, not a defence.

Docs/40: fixed anonymity cells (router/anonymity.build_cells, cell_cover —
sources partitioned once, the whole cell of the top-1 source dispatched)
are the first decoy policy that reduces BOTH leaks: on FeB4RAG topic
inference 0.454 → 0.201 and source attack 0.744 → 0.231 at equal fan-out,
for 0.12 of graded gain; in the 8-client same-domain healthcare federation
(eval/run_healthcare.py, public literature partitioned by k-means, not
institutional data) topic 0.615 → 0.272 (the majority-class floor) and
source 0.875 → 0.250, where topic-stable decoys leave the source attack at
1.000. Cells are wired into select_dispatch as decoy_policy="cells".
The cross-node evidence rerank (AppState._rerank_evidence, evidence_top_k)
drops the attacker's planted passage from the prompt on the 60 attack
cases (cited 1.000 → 0.067 at top-2) while the attacker is still selected
1.000 — a content filter, not a routing defence. Report the majority-class
rate, not 1/k, as the attack floor on skewed labels.

Docs/39 proves the routing-pattern leak and reverses the docs/30–31 decoy
verdict. On FeB4RAG (13 engines, 640 requests, topic = origin engine) an
observer seeing only contacted ids names the topic 0.496 of the time under
a cosine router (chance 0.077; top-3 0.841). Topic-stable decoys leave
topic inference unchanged (0.495) while cutting the source attack (0.744 →
0.564); random decoys do the reverse (topic 0.336–0.380, source 0.667–
0.692). No decoy strategy measured reduces both; broadcast alone does. Do
not describe sticky decoys as "the working defence" without saying which
attack; the docs/31 result was the source attack only. "Topic-stable"
decoys share only Jaccard 0.23 across same-origin queries because the live
topic key is the nearest of 39 centroids. PSI (docs/36–37) fixes query
content, not the pattern. Hygiene: BroadcastRouter now ignores top_k; PSI
key files are 0600; psi catches only CryptoError; MMLU answer letters are
no longer written into node documents; /nodes reports mode-specific trust;
requirements-lock.txt records the evaluation environment.

Docs/38 is the first answer-level result: MIRAGE, 150 questions, local
Qwen3.5-9B via Ollama. closed-book 0.547, psi (local routing + PSI
dispatch, cap 4) 0.580, broadcast (PSI to all 8 nodes) 0.627. Retrieval
without any node seeing the query helps; routing captures ~40% of the
contact-everything gain at half the contacts; gains concentrate on
literature questions (pubmedqa +13, bioasq +10) and knowledge MCQ do not
benefit. ±8-point intervals at n=150 — do not describe psi vs closed-book
as significant. Corpora are BEIR samples, not MedRAG, so absolute accuracy
is not comparable to published MIRAGE numbers. Addendum: psi + cross-node
rerank (top-2) 0.587 at 2 passages; psi + cells + rerank (the docs/41
configuration) 0.580 at 1.76 medical contacts — the privacy configuration
answers as well as the leaky one at half the passages.

Docs/37: on the project's 200 synthetic privacy cases, psi exposes 0 of 3
sensitive values to nodes; legacy/smart/v2 expose 3 of 3 (v2 via
nearest-neighbour inversion); regex redaction removes only the email. The
PII preamble itself lowers routing (allowed client reached 0.540 vs 0.620
without it) — redaction before embedding and PSI are complementary. All 60
attack cases succeed in every mode (attacker selected and cited 1.000):
there is no A3 defence and no cross-node evidence filter; encryption does
not change that. Enumeration: an authorised client opens a node's whole
table in ⌈clusters/nprobe⌉ queries (75 for 150 clusters) — the OPRF makes
it rate-limitable, not impossible. Persistent MCP sessions
(PersistentMCPNodeHandle) bring legacy/v2/psi to 10/9/61 ms per query on
30 real nodes; psi's real per-contact cost is ~10 ms and ~170 KB per
40-document node. Ollama local generation (localhost only) is the E10
generator (docs/38).

Docs/36: `routing_mode="psi"` is the first dispatch stage in which a node
receives neither the query nor a vector — blinded cluster ids over an
OPRF/labeled-PSI exchange (privacy/psi.py, ed25519 group via PyNaCl, no
ristretto in this build), envelopes opened and reranked on the device.
Verified over real MCP with text/vector tools patched to fail. Cost on 30
real nodes: 4.85 s/query (two spawn-per-call round trips per contact) and
~1 MB response per query because full labeled PSI ships every envelope a
node holds — communication is linear in the node table; do not describe it
as cheap at large nodes. FeB4RAG (13 of 16 engines, 785 requests, graded
qrels): the local profile ranking scores nDCG@1 0.734, MRR 0.578, top-1
0.399; legacy = v2 = psi capture 0.662 of the best graded gain at 6
contacts, smart 0.538. The API process plays the device in psi mode; a
deployment must move that code to the client. Legacy remains the default.

Docs/35 measures bucket recall for PSI-based private retrieval, with no
cryptography. SimHash on bge-base embeddings is unusable for query→passage
matching (relevant pairs at cosine 0.70 vs random 0.51): the only recalling
configuration delivers 45% of the node's corpus per query. Published k-means
cluster ids work: at k=200, nprobe=2, minimum cluster size 5, recall is 0.89
of dense@10 with ~36 passages delivered per contacted node (~3.6x a top-10
fetch). Raising k without a minimum cluster size publishes document
embeddings as centroids (28% at k=500, 60% at k=1000) — never do that. Do
not report disclosure as "x relevant docs" (corpus-dependent); report it
against a dense top-k fetch. No PSI cost has been measured.

Docs/33 measures scaling and transport. At a 6-contact cap, v2/legacy source
recall falls 0.872 → 0.707 → 0.518 from 30 to 100 to 300 sources (smart 0.692
→ 0.429 → 0.273); v2 and legacy stay identical at every N. v2's 768-d vector
dispatch costs ~102 KB per query, ~55x a text request and more than
broadcasting text to 100 sources — do not describe the plaintext-free wire as
free. Routing latency is O(N) because every mode rebuilds its index per query
(v2 2.6 ms at 300). With 30 real MCP subprocesses a query takes ~2.7–2.9 s,
>99.9% of it the spawn-per-call node contacts (~450–490 ms each). 1,000
sources was NOT run; the 300 tier has two seeds. A2 precision falling with N
is a topic-repetition artefact, not privacy. api/state.py now logs per-stage
latency and per-contact bytes on every query.

Docs/32 measures v2 under A1 and A3; both are negative and must be preserved.
A1: vector dispatch gives NO inversion resistance (exact recovery 1.000 at
sigma 0), and noise cannot fix it — at sigma 0.10 retrieval agreement is
already 0.265 while recovery is still 0.997, so utility dies faster than the
attack. Do not describe sigma as an A1 lever. A3: v2's trust is INERT because
`select_dispatch` uses it only as an exclusion gate, and raising the gate above
the 0.5 cold-start prior deadlocks the network entirely (honest recall 0.000) —
a defect in v2, not a tuning result; do not adopt a fix without re-running the
ablation. The plausibility check blocks the attacker only by rejecting 17.7 of
24 honest sources; keep it off by default. A2 decoys remain the only measured
defence.

Docs/30-31 cover the opt-in `routing_mode="v2"` privacy pipeline: local
routing, one exposure budget covering genuine AND decoy contacts with no
exemption, shared-routing-space vector dispatch instead of raw query text, and
Ed25519 profile signing. Preserve these results. v2 TIES legacy at matched
contacts (0.711 recall, 4.45 audit, A2 0.258 vs 0.259) — it is not a better
router, and its benefit is that sigma becomes unnecessary. Two findings must
not be quietly reversed: the E3 decoy-trust exemption identified decoys at
precision/recall 1.00 and is therefore OFF in the API path, and low A2
precision alone does not mean private (smart posts 0.072 only because its
selections are poor). A routing-space vector is not query secrecy — it stays
invertible. Signing proves integrity and key binding, never truthfulness; a
signed forged profile verifies. Legacy remains the API/dashboard default.

FedSafeRouter is a training-free, exposure-constrained and trust-aware adaptive
source router for Federated RAG. The user explicitly chose to implement the
smart router itself. RAGRoute is a comparison baseline, not its required engine.

The current implementation contract is backend/router/smart.py and
docs/13-smart-router-implementation.md. See docs/03-architecture.md and
docs/04-router-design.md for boundaries and the exact selection rule.
The earlier instruction prohibiting a new router is superseded.

## Engineering and evidence rules

- Preserve the legacy pipeline and published baseline semantics as independent
  controls. Do not silently change old experiment outputs or call legacy RAGRoute.
- Smart, v2, psi and blind are opt-in through POST /query; legacy remains the API
  default. The studio defaults to blind + hybrid (docs/41) and shows the mode on
  every answer. Update documentation and tests if either default changes.
- Every smart source contact must fit the positive-cost per-query budget.
  There is no genuine-source exemption, decoy dispatch or fallback broadcast.
- Relevance, trust and overlap are heuristics. Do not claim novelty, optimality,
  privacy guarantees or hijacking resistance from implementation tests.
- Call Gaussian noise empirical embedding perturbation, not DP without a
  separately established formal mechanism and assumptions.
- Source trust starts at 0.5 with an uncertainty penalty. Smart EvidenceTrust
  uses coordinator-embedded passage consistency, not self-advertised trust or
  remote retrieval scores. It is not TASR.
- The coordinator (the API process) sees raw queries and returned passages in
  every mode; in the demo it plays the user's device. What a contacted node
  receives depends on the mode: raw query text (legacy, smart), an invertible
  routing-space vector (v2), blinded cluster ids over OPRF/PSI (psi, docs/36), or
  the same number of real-or-dummy blinded points at every node (blind, docs/47).
  Privacy claims are against contacted nodes and a routing-pattern observer,
  never against the coordinator; moving the device-side code to the client is
  the docs/03 target, not the implementation. Do not say "end-to-end".
- Production authentication and validated de-identification are not implemented
  (nodes run rule + registry de-identification, docs/44). Policy labels are only a demo selection hook.
- The live path's routing space is chosen by ROUTING_EMBEDDER (default
  "hashing"; e.g. "BAAI/bge-base-en-v1.5"), read identically by the
  coordinator and every MCP node process (forwarded through the stdio env);
  registration refuses a node whose centroids are not in the coordinator's
  space. A semantic model needs MCP_PERSISTENT=1 (each node process loads the
  model once, ~10 s). Evaluation must still record model/version/preprocessing.
- A cloned repository is not a reproduced result. Pin code/artifacts and save
  commands, environments, splits and raw per-query outputs.
- Distinguish real MCP transport, in-process simulation and virtual source
  partitions. A 1,000-profile synthetic test does not demonstrate 1,000 servers.
- Do not invent measured costs or leakage. Unit contact cost is an explicit
  exposure definition, not an estimated attack probability.
- Keep paper literature summaries in the student's own writing; repository
  planning/specification notes are support material, not submission-ready prose.
- Inspect existing datasets first. The user disallowed downloads above 500 MB;
  do not silently fetch larger datasets.

## Module map

| Path | Role |
|---|---|
| backend/router/smart.py | SmartConfig, SourceEvidence, SmartRouter, SmartDecision, EvidenceTrust |
| backend/router/v2.py | V2Config (decoy_policy topic_stable/cells), select_dispatch, dispatch_payload, DecoyAwareEvidenceTrust (exemption OFF by default, see docs/30) |
| backend/nodes/signing.py | Ed25519 profile signing; integrity and key binding only, not truthfulness |
| backend/router/pipeline.py | Preserved legacy baseline-plus-layer path |
| backend/router/exposure.py | Legacy proxy accounting; genuine exemptions mean it is not smart budget enforcement |
| backend/router/trust.py | Legacy BoundedTrustUpdate, not official TASR |
| backend/baselines/ | Local controls and external adapters; RAGRoute remains a stub |
| backend/nodes/ | Profile/index construction, MCP client/server, simulator and embedders |
| backend/api/ | Stateful demo coordinator; smart/legacy routing selection |
| backend/attacks/, backend/eval/ | Existing attack/evaluation building blocks |
| backend/eval/run_scaling.py, run_mcp_transport.py, embed_cache.py | Scaling / transport harnesses (docs/33); cache changes no embedding |
| backend/eval/run_bucket_recall.py | SimHash vs cluster-id bucket recall for PSI retrieval (docs/35) |
| backend/privacy/psi.py, cluster_index.py | OPRF/labeled-PSI dispatch and the node's cluster table (docs/36) |
| backend/privacy/credentials.py | HMAC credential + per-client daily evaluation budget gating psi_evaluate (docs/43) |
| backend/privacy/deidentify.py, backend/eval/run_node_deid.py | Node-side de-identification at load, and its leakage/cost measurement (docs/44) |
| backend/eval/run_deid_benchmark.py | Held-out Safe Harbor de-identification benchmark on PMC prose; basic vs safe_harbor level (docs/54) |
| backend/eval/run_rbac.py (+ privacy/credentials roles, psi per-collection keys) | Role-based access to node collections, enforced in the PSI step (docs/45) |
| backend/eval/run_feb4rag.py | FeB4RAG graded resource-selection evaluation (docs/36) |
| backend/eval/run_privacy_cases.py, run_psi_enumeration.py | Synthetic privacy/attack cases and PSI enumeration cost (docs/37) |
| backend/generation/ollama_generator.py | Local-only generator (LLM_PROVIDER=ollama); the only one inside the trust boundary |
| backend/eval/run_answer_quality.py | E10 MIRAGE answer quality, closed-book vs psi vs broadcast (docs/38) |
| backend/attacks/a2_topic_inference.py, backend/eval/run_leakage.py | Contacted-set → query-topic attack and the decoy ablation (docs/39) |
| backend/eval/run_healthcare.py | Same-domain 8-client healthcare federation, hard case for routing leakage (docs/40) |
| backend/eval/run_hyfedrag_compare.py | HyFedRAG-style design vs ours on PMC-Patients (docs/46, blind rows docs/47; `--only` runs a subset) |
| backend/baselines/external_fedrag.py, backend/eval/run_external_baselines.py | RAGRoute and Flower FedRAG reproduced on PMC; quality, privacy and hospital cost vs blind unlock (docs/53) |
| backend/router/hybrid_rerank.py | Device-side dense + pool-BM25 rerank (docs/48); no model, no network |
| backend/client/ | Standalone device: Device (blind unlock, no server), CoverTrafficScheduler, node transports, CLI (docs/52) |
| backend/privacy/blind_unlock.py | Blind unlock: global probe planning, dummy padding, table cache, tag-lookup unlock (docs/47) |
| backend/privacy/pir.py, backend/eval/run_pir_tier.py | Tier 2 for large hospitals: SimplePIR fetch of blind-unlock chunks instead of full download (docs/55) |
| backend/eval/run_release.py | Gap 3: records released per question vs top-10, cluster granularity x P frontier, centroid proximity (docs/56) |
| backend/eval/build_pubmed_subset.py, backend/eval/run_cfedrag_style.py | C-FedRAG-style MIRAGE PubMedQA + BioASQ answer accuracy with privacy, release, cost and timing columns (docs/57) |
| backend/eval/scorecard.py | One command: assemble (or --run then assemble) the central configuration × axis table from result CSVs; copies numbers, never recomputes |
| frontend/lib/api.ts | Hand-maintained mirror of backend/api/schemas.py |
| docs/ | Current design, planned experiments and limitations |
| knowledge/ | Obsidian vault: linked notes (concepts, mechanisms, attacks, results, claims ledger); generated summary of docs/, not a source of truth over docs/41 |

Python 3.10+ is required. Keep tests independent of optional heavy model
dependencies and downloaded corpora where possible. Existing MCP tests use
synthetic fixtures with genuine subprocess transport.

## Verification

Run .venv/bin/pytest -q from the repository root. When API types change, run
frontend/node_modules/.bin/tsc --noEmit --incremental false from frontend.
Do not treat test counts as experimental quality or privacy results.

New code may extend the independent selector, but scientific claims require
the controls and ablations in docs/05-experiments.md. No baseline training is
required by SmartRouter; reproducing a learned comparison method may still
require its offline training or checkpoint.
