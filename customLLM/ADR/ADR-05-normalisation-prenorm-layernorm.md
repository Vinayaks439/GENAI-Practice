# ADR-05 · Normalisation: Pre-norm LayerNorm

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Stage** | 6 — Transformer block |
| **Deciders** | Project author |
| **Date** | 2026-05-28 |

---

## Context

Deep networks suffer from internal covariate shift — the distribution of each
layer's inputs changes during training, destabilising learning. Normalisation
layers address this. Two decisions were needed:

1. **Which normalisation?** LayerNorm vs BatchNorm vs RMSNorm
2. **Where to apply it?** Before the sublayer (pre-norm) or after (post-norm)

---

## Decision

### Normalisation type: LayerNorm

```
BatchNorm: normalises across the batch dimension (B)
  → statistics depend on batch size; unstable for small B or variable T

LayerNorm: normalises across the feature dimension (E) per token
  → statistics computed independently per token; works for any B or T
```

LayerNorm per token:

```
For a single token embedding x ∈ ℝᴱ:

  μ = mean(x)          scalar
  σ² = var(x)          scalar (unbiased=False)
  x̂ = (x - μ) / √(σ² + ε)

  output = γ ⊙ x̂ + β  (γ, β are learned parameters, shape E)
```

`γ` (scale) initialised to ones, `β` (shift) to zeros — identity at init.

### Pre-norm placement (GPT-2 style)

```
Original Transformer (2017) — Post-norm:
  x = LayerNorm(x + Attn(x))
  x = LayerNorm(x + FFN(x))

GPT-2 onward — Pre-norm:
  x = x + Attn(LayerNorm(x))   ← LN applied to the INPUT of each sublayer
  x = x + FFN(LayerNorm(x))
```

**Why pre-norm is better for training stability:**

In post-norm, the residual path passes through LayerNorm. During early
training, when weights are random, this can cause the residual to be
normalised away, effectively blocking gradient flow.

In pre-norm, the residual path (`+ x`) is always clean — gradients flow
back to early layers without passing through any normalisation. This is
why pre-norm models can train stably with larger learning rates and shorter
warmup.

```
Pre-norm gradient flow:

  Loss → LN(x) sublayer gradient path
       ↘
         direct residual gradient path  ← always clean
```

---

## Why not RMSNorm?

RMSNorm (used by LLaMA) removes the mean-centering step:

```
RMSNorm(x) = x / RMS(x) * γ   (no shift β, no mean subtraction)
```

~15% faster than LayerNorm; quality is equivalent or better in practice.

We use LayerNorm because:
- It matches GPT-2 exactly (easier to cross-reference)
- The speed difference is negligible at our scale
- Implementing it from scratch makes the normalisation more transparent

---

## Consequences

**Positive**
- Pre-norm allows training with `lr_max=3e-4` and warmup=100 — a large,
  fast schedule that post-norm would struggle with
- Residual stream is never normalised — its magnitude can be used as a
  signal of model confidence (interpretability research relies on this)
- LayerNorm parameters (`γ`, `β`) are excluded from weight decay by
  convention — they are exempt from the AdamW `weight_decay` parameter

**Negative / Trade-offs**
- Pre-norm means the *output* of the model before the LM head is not
  normalised. The final LayerNorm added after the last block (before the
  LM head) compensates for this
- Slightly more complex than post-norm to reason about in terms of
  representation space

---

## Related ADRs

- [ADR-04](ADR-04-attention-causal-multihead.md) — LayerNorm wraps MHA
- [ADR-06](ADR-06-activation-gelu.md) — GELU sits inside the FFN that
  LayerNorm feeds into
