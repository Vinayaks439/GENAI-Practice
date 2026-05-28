# ADR-06 · Activation Function: GELU (tanh approximation)

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Stage** | 6 — Transformer block |
| **Deciders** | Project author |
| **Date** | 2026-05-28 |

---

## Context

The feed-forward sublayer needs a non-linearity between its two linear layers.
Without it, the two `Linear` layers collapse into a single linear operation
regardless of depth.

```
FeedForward(x):
  h = Linear(emb_dim → 4*emb_dim)(x)
  h = Activation(h)                   ← decision point
  return Linear(4*emb_dim → emb_dim)(h)
```

Candidates evaluated:

| Activation | Properties |
|------------|-----------|
| ReLU | `max(0, x)`. Fast, sparse. Hard zero for x < 0 kills gradients. |
| Leaky ReLU | Small negative slope. Fixes dying ReLU but rarely used in LLMs. |
| **GELU** | Smooth, probabilistic gating. Used by GPT-2, BERT, T5. |
| SiLU / Swish | `x * sigmoid(x)`. Used by LLaMA 1. Similar to GELU. |
| SwiGLU | Gated variant. Used by LLaMA 2/3, PaLM. Better but more complex. |

---

## Decision

Use GELU with the **tanh approximation** matching GPT-2 exactly:

```python
GELU(x) = 0.5 * x * (1 + tanh(√(2/π) * (x + 0.044715 * x³)))
```

This is an approximation of the true GELU:

```
True GELU(x) = x * Φ(x)       where Φ is the standard normal CDF
```

The tanh approximation matches true GELU to within ~0.0001 and avoids the
expensive `erf` computation.

---

## Shape comparison

```
         ┌────────────────────────────────────────────┐
   3.0 ─ │                             ╱‾‾‾‾‾‾‾‾     │
         │                           ╱               │
   2.0 ─ │                         ╱                 │  GELU
         │                       ╱                   │  ─────
   1.0 ─ │                     ╱     ╱‾‾‾‾‾‾‾‾       │  ReLU
         │         ╱‾‾‾‾‾‾‾  ╱    ╱                  │  -----
   0.0 ─ │────────/─────────/────/────────────────── │
         │      ╱          ╱                          │
  -0.2 ─ │    ╲           ╱                           │
         │     ╲_________/                            │
         └────────────────────────────────────────────┘
             -3    -2    -1     0     1     2     3
```

Key difference: GELU allows a small negative output for negative inputs
(peak of ~-0.17 at x ≈ -0.75). This means neurons are never completely
dead — small negative gradients still flow back.

---

## Consequences

**Positive**
- Smooth everywhere — gradient never drops to exactly zero (unlike ReLU)
- Empirically outperforms ReLU on NLP benchmarks (Hendrycks & Gimpel 2016)
- Matches GPT-2 precisely — useful for reproducing or comparing results
- `torch.nn.functional.gelu(x, approximate='tanh')` is equivalent and
  torch-compiled-friendly

**Negative / Trade-offs**
- Slightly more compute than ReLU (tanh vs comparison) — negligible at our scale
- SwiGLU (LLaMA 2 style) is empirically better but requires changing the
  feed-forward to a gated structure: `SwiGLU(x) = (xW₁) ⊙ SiLU(xW₂)`.
  Left as a future upgrade

---

## Feed-forward dimension: why 4×?

```
emb_dim=384 → hidden=1536 → emb_dim=384
```

The 4× expansion ratio comes from the original Transformer paper (Vaswani 2017)
and has remained the default across GPT-2, BERT, and most successors.

The expanded hidden layer acts as a "scratch pad" — the model can compute richer
intermediate representations before projecting back. Empirically, smaller
ratios (2×, 3×) underperform; larger (8×) help marginally at huge scale.

---

## Related ADRs

- [ADR-05](ADR-05-normalisation-prenorm-layernorm.md) — GELU sits between the
  two linears inside the FFN that LayerNorm feeds
