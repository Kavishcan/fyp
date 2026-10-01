"""Two published federated-RAG baselines, run on this project's data (docs/53).

RAGRoute — Guerraoui et al., "Efficient Federated Search for Retrieval-
Augmented Generation" (EuroMLSys 2025), code github.com/sacs-epfl/ragroute
(MIT licence). A selective router: a small neural network scores every
source from (query embedding, source centroid, one-hot source id) and the
query goes, as text, only to the sources scored above 0.5. Reproduced here
from the repository (ragroute/router.py CorpusRoutingNN, and the training
loop in scripts/train/train_medrag_router.py): 128-64-32 layers with
LayerNorm, ReLU and Dropout 0.4; StandardScaler on the features; BCE with
logits (the script computes a positive-class weight but does not pass it to
the loss, so neither does this); Adam lr 1e-3, weight decay 3e-5, batch 128,
CyclicLR 1e-3..5e-3 (triangular2, step 10) then StepLR; 150 epochs; the
checkpoint with the best validation AUC; 30/10/60 train/validation/test
split by query; label = the source holds at least one of the global top-15
documents. Each selected source returns its exact top-50; RAGRoute then
reranks with the BAAI/bge-reranker-v2-m3 cross-encoder (~2 GB, over this
project's download limit) — replaced here by the same ranking every other
configuration uses (dense or hybrid), which is stated wherever it is reported.

Flower FedRAG — the "fedrag" example of the Flower framework
(github.com/adap/flower, examples/fedrag, Apache-2.0). The server sends the
question to every client; each client embeds it with its own model
(sentence-transformers/all-MiniLM-L6-v2 by default) and searches a FAISS
IndexIVFFlat (L2, nlist = sqrt(N)); the server merges with reciprocal rank
fusion (k = 60). `flower_merge_documents` below is the example's
`merge_documents`, copied with its behaviour unchanged. The example's
default k-nn is 8; this harness uses 10 so every configuration is scored on
the same top-10.

Neither baseline is presented as the authors' full system: no reranker for
RAGRoute, no LLM-side evaluation for Flower, both on this project's PMC
hospitals. What is reproduced is the routing/dispatch behaviour that decides
privacy and cost.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict

import numpy as np


# --- Flower FedRAG ----------------------------------------------------------------


def flower_merge_documents(documents, scores, knn, k_rrf=0, reverse_sort=False):
    """examples/fedrag/fedrag/server_app.py merge_documents (Apache-2.0),
    unchanged except that documents are hashed with sha256 instead of the
    example's get_hash helper. Lower scores rank first (FAISS L2)."""
    rrf = defaultdict(dict)
    order = np.array(scores).argsort()
    if reverse_sort:
        order = order[::-1]
    ranked = [documents[i] for i in order]
    if k_rrf == 0:
        return ranked[:knn]
    for idx, doc in enumerate(ranked):
        key = hashlib.sha256(doc.encode("utf-8")).hexdigest()
        rrf[key]["rank"] = 1 / (k_rrf + idx + 1)
        rrf[key]["doc"] = doc
    merged = sorted(rrf.values(), key=lambda x: x["rank"], reverse=True)
    return [m["doc"] for m in merged][:knn]


class FlowerClientIndex:
    """One Flower client's retriever: FAISS IndexIVFFlat, METRIC_L2,
    nlist = int(sqrt(N)), as in examples/fedrag/fedrag/retriever.py."""

    def __init__(self, documents: list[str], embeddings: np.ndarray) -> None:
        import faiss

        x = np.asarray(embeddings, dtype="float32")
        self.documents = documents
        quantizer = faiss.IndexFlatL2(x.shape[1])
        self.index = faiss.IndexIVFFlat(quantizer, x.shape[1], max(1, int(np.sqrt(len(x)))), faiss.METRIC_L2)
        self.index.train(x)
        self.index.add(x)
        self._quantizer = quantizer          # keep alive

    def search(self, query_vector: np.ndarray, knn: int) -> list[tuple[str, float]]:
        scores, idx = self.index.search(np.asarray([query_vector], dtype="float32"), knn)
        return [(self.documents[i], float(s)) for i, s in zip(idx[0], scores[0]) if i >= 0]


# --- RAGRoute ---------------------------------------------------------------------


def _router_net(input_dim: int):
    import torch.nn as nn
    import torch.nn.functional as F

    class CorpusRoutingNN(nn.Module):          # ragroute/ragroute/router.py (MIT)
        def __init__(self) -> None:
            super().__init__()
            self.fc1, self.ln1, self.dropout1 = nn.Linear(input_dim, 128), nn.LayerNorm(128), nn.Dropout(0.4)
            self.fc2, self.ln2, self.dropout2 = nn.Linear(128, 64), nn.LayerNorm(64), nn.Dropout(0.4)
            self.fc3, self.ln3, self.dropout3 = nn.Linear(64, 32), nn.LayerNorm(32), nn.Dropout(0.4)
            self.fc_out = nn.Linear(32, 1)

        def forward(self, x):
            x = self.dropout1(F.relu(self.ln1(self.fc1(x))))
            x = self.dropout2(F.relu(self.ln2(self.fc2(x))))
            x = self.dropout3(F.relu(self.ln3(self.fc3(x))))
            return self.fc_out(x)

    return CorpusRoutingNN()


class RAGRouteRouter:
    """Trained once per federation; `route(q)` returns the selected sources."""

    def __init__(self, sources: list[str], centroids: dict[str, np.ndarray], seed: int = 0) -> None:
        self.sources = list(sources)
        self.centroids = {s: np.asarray(centroids[s], dtype=np.float32) for s in self.sources}
        self.seed = seed
        self.model = None
        self.scaler = None
        self.val_auc = None

    def _features(self, q: np.ndarray) -> np.ndarray:
        eye = np.eye(len(self.sources), dtype=np.float32)
        return np.stack([np.concatenate([np.asarray(q, dtype=np.float32), self.centroids[s], eye[i]])
                         for i, s in enumerate(self.sources)])

    def fit(self, train_q: list[np.ndarray], train_labels: list[set[str]], val_q: list[np.ndarray],
            val_labels: list[set[str]], epochs: int = 150) -> "RAGRouteRouter":
        import torch
        from sklearn.metrics import roc_auc_score
        from sklearn.preprocessing import StandardScaler

        torch.manual_seed(self.seed)
        rng = np.random.default_rng(self.seed)
        def xy(qs, labels):
            x = np.concatenate([self._features(q) for q in qs])
            y = np.array([1.0 if s in lab else 0.0 for lab in labels for s in self.sources], dtype=np.float32)
            return x, y
        xt, yt = xy(train_q, train_labels)
        xv, yv = xy(val_q, val_labels)
        self.scaler = StandardScaler().fit(xt)
        xt, xv = self.scaler.transform(xt).astype(np.float32), self.scaler.transform(xv).astype(np.float32)
        model = _router_net(xt.shape[1])
        criterion = torch.nn.BCEWithLogitsLoss()
        opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=3e-5)
        cyclic = torch.optim.lr_scheduler.CyclicLR(opt, base_lr=1e-3, max_lr=5e-3, step_size_up=10,
                                                   mode="triangular2", cycle_momentum=False)
        fixed = torch.optim.lr_scheduler.StepLR(opt, step_size=50, gamma=0.05)
        best, best_state = -1.0, None
        xt_t, yt_t, xv_t = torch.tensor(xt), torch.tensor(yt), torch.tensor(xv)
        for epoch in range(epochs):
            model.train()
            perm = rng.permutation(len(xt))
            for s in range(0, len(perm), 128):
                b = perm[s:s + 128]
                opt.zero_grad()
                loss = criterion(model(xt_t[b]).squeeze(-1), yt_t[b])
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                opt.step()
                (cyclic if epoch < 115 else fixed).step()
            model.eval()
            with torch.no_grad():
                pv = torch.sigmoid(model(xv_t).squeeze(-1)).numpy()
            auc = roc_auc_score(yv, pv) if len(set(yv.tolist())) > 1 else 0.0
            if auc > best + 1e-6:
                best = auc
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
        model.load_state_dict(best_state)
        model.eval()
        self.model, self.val_auc = model, best
        return self

    def route(self, q: np.ndarray, threshold: float = 0.5) -> list[str]:
        import torch

        x = torch.tensor(self.scaler.transform(self._features(q)).astype(np.float32))
        with torch.no_grad():
            p = torch.sigmoid(self.model(x).squeeze(-1)).numpy()
        return [s for s, pi in zip(self.sources, p) if pi > threshold]
