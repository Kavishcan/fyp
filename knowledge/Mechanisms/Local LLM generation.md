---
tags: [type/mechanism]
updated: 2026-09-30
---

# Local LLM generation

The measured answer experiments use localhost Ollama with Qwen3.5-9B. Query and context remain inside the trusted device only when the selected generator and its logging are genuinely local.

The repository also contains remote generator integrations. Using one changes the privacy claim. Node-provided evidence can contain prompt injection; that integrity risk is not solved by private dispatch.

See [[Answer quality results]], [[Trust boundary]].

## Implementation / Experiment Sources

- [backend/generation/ollama_generator.py](../../backend/generation/ollama_generator.py)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
