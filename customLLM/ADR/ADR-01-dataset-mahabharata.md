# ADR-01 · Dataset: Mahabharata

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Stage** | 2 — Data collection |
| **Deciders** | Project author |
| **Date** | 2026-05-28 |

---

## Context

We needed a public domain English corpus large enough to show real language
learning (~1M+ tokens) but small enough to train on a single laptop in a
reasonable time (under 8 hours on CPU/MPS).

Candidates considered:

| Dataset | Tokens | Domain | Notes |
|---------|--------|--------|-------|
| Tiny Shakespeare | ~1M | Drama | Too small; well-worn tutorial example |
| OpenWebText sample | ~100M | Web text | Too large for a from-scratch demo |
| Project Gutenberg novel | ~300K | Fiction | Too small; single voice |
| **Mahabharata (tilakd/kaggle)** | **~1.8M** | **Epic narrative** | **Chosen** |

---

## Decision

Use the Mahabharata English translation from Kaggle (`tilakd/mahabharata`).

**Why this corpus specifically:**
- ~1.8 million words — large enough for the model to learn meaningful patterns
- Single coherent domain (epic narrative) makes learned patterns visible in
  generated text without needing a large model
- Named characters, repeated speech patterns, and consistent register make
  qualitative evaluation easy ("does the model sound like the Mahabharata?")
- Free, versioned, downloadable via `kagglehub` in one line

---

## Consequences

**Positive**
- Domain coherence — the model quickly learns character names (`Arjuna`,
  `Krishna`, `Bhishma`), speech acts (`said`, `replied`, `spoke`), and
  narrative connectives (`thus`, `O king`, `verily`)
- Fits in RAM; trains to interesting behaviour in 2–5 hours on Apple MPS
- Clear qualitative signal: good training produces recognisably archaic/epic
  English; bad training produces word salad

**Negative / Trade-offs**
- Small by LLM standards — expect repetition and hallucination on out-of-domain
  prompts
- Formal/archaic English register — modern conversational prompts produce odd
  output
- All data is in English; the original Sanskrit is not represented

---

## Related ADRs

- [ADR-02](ADR-02-tokenizer-bpe.md) — tokenizer choice is informed by the
  domain (Sanskrit proper names are tokenized into multiple subword pieces)
