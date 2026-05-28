# ADR-07 · Training: AdamW + Cosine LR + Mixed Precision + Grad Clipping

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Stage** | 7 — Training loop |
| **Deciders** | Project author |
| **Date** | 2026-05-28 |

---

## Context

Several training decisions are tightly coupled and documented together:
optimiser, learning rate schedule, numerical precision, gradient handling,
and batch strategy.

---

## Decision 1 — Optimiser: AdamW

**Why Adam over SGD?**

SGD requires careful per-layer learning rate tuning. Transformers have very
different gradient scales across layers (embeddings vs attention projections).
Adam adapts the effective learning rate per parameter, making it the default
for Transformer training.

**Why AdamW over Adam?**

Standard Adam applies weight decay as an additive gradient term, which
interacts with the adaptive learning rate scaling:

```
Adam:   θ ← θ - α * (m̂/√v̂) - α * λ * θ   ← λ is scaled by the adaptive LR
AdamW:  θ ← (1 - α*λ) * θ - α * (m̂/√v̂)   ← λ is decoupled
```

AdamW's decoupled weight decay behaves as true L2 regularisation regardless
of gradient magnitude. Empirically it generalises better for LLMs.

**Hyperparameters (GPT-3 recipe):**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `lr_max` | 3e-4 | Standard for small transformers |
| `betas` | (0.9, 0.95) | β₂=0.95 (vs default 0.999) adapts faster to sudden gradient changes |
| `weight_decay` | 0.1 | Applied to weight matrices only; biases and LN params are excluded |
| `eps` | 1e-8 | Numerical stability floor |

Weight decay is **not** applied to biases or LayerNorm `γ/β` — these
parameters are small and regularising them hurts more than helps.

---

## Decision 2 — LR Schedule: Linear Warmup + Cosine Decay

```
lr
▲
│ lr_max (3e-4)
│   ╱‾‾‾‾‾╲
│  ╱        ╲_____________________________________
│ ╱                                               ╲__ lr_min (3e-5)
│╱
└────────────────────────────────────────────────────► step
  0   warmup(100)                         max_iters(5000)

Phase 1 (steps 0→100):   lr = lr_max * step / warmup
Phase 2 (steps 100→5000): lr = lr_min + 0.5*(lr_max-lr_min)*(1+cos(π*progress))
```

**Why warmup?**
At initialisation, weights are random. The first batches produce large,
noisy gradients. Starting with a tiny LR and ramping up prevents a
catastrophic first update from destabilising the loss.

**Why cosine over step decay?**
Step decay produces sudden loss spikes when LR drops. Cosine decay is
smooth — the model never sees a jarring LR change, which produces a
cleaner final loss curve and slightly better perplexity.

**Why not a constant LR?**
A constant LR that works for early training (when gradients are large) is
too large for late training (when the loss landscape is nearly flat). The
model oscillates instead of converging. Decay avoids this.

---

## Decision 3 — Mixed Precision: bfloat16

| Format | Exponent bits | Mantissa bits | Notes |
|--------|--------------|---------------|-------|
| float32 | 8 | 23 | Full precision; slow |
| float16 | 5 | 10 | Fast; overflows at ~65K; needs GradScaler |
| **bfloat16** | **8** | **7** | **Fast; same range as fp32; no GradScaler** |

We use bf16 because it has the same exponent range as float32 — no overflow
for large logits or gradients — but half the storage. Unlike fp16, no
dynamic loss scaling is needed, simplifying the training code.

```python
with torch.amp.autocast(device_type='mps', dtype=torch.bfloat16):
    logits = model(x)
    loss = F.cross_entropy(logits.flatten(0,1), y.flatten())
loss.backward()   # grads computed in bf16 where possible
optim.step()      # master weights updated in fp32 inside AdamW
```

Result: ~2× throughput on MPS (5,500 tok/s vs ~2,500 tok/s for fp32).

---

## Decision 4 — Gradient clipping at norm 1.0

```python
grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
```

If the global gradient norm exceeds 1.0, all gradients are scaled down
proportionally so the norm equals exactly 1.0. If it is already ≤ 1.0,
nothing changes.

**Why clip?**
Occasionally a batch with unusual token distribution produces very large
gradients. Without clipping, a single bad batch can permanently corrupt
model weights. Clipping provides a safety ceiling with negligible cost on
normal batches.

**`gnorm` in the training log:**
The value displayed is the *raw* norm *before* clipping. Healthy range is
0.3–1.5 during stable training. Persistent values > 3.0 suggest the LR
is too high or the model is diverging.

---

## Decision 5 — Gradient accumulation

```
effective_batch_size = batch_size × grad_accum

Default: 32 × 1 = 32
With --grad-accum 4: 8 × 4 = 32 (uses 4× less VRAM)
```

Accumulate gradients over `grad_accum` forward/backward passes before
calling `optim.step()`. Mathematically equivalent to a larger batch.

Used when GPU memory is insufficient for the target batch size.

---

## Consequences

**Positive**
- bf16 autocast gives ~2× speed on MPS with no code complexity vs FP16
- Cosine schedule consistently produces 5–10% lower final val loss vs
  constant LR at the same number of steps
- Gradient clipping makes training robust to dataset outliers
- Fused AdamW (CUDA only) gives an additional ~5% speedup on GPU

**Negative / Trade-offs**
- bf16 on MPS can produce NaN in the first few steps with very aggressive
  LR — the warmup ramp mitigates this entirely in practice
- Gradient accumulation adds slight memory overhead (gradients accumulate
  across `grad_accum` steps before being freed)

---

## Related ADRs

- [ADR-03](ADR-03-architecture-decoder-only.md) — training loss is
  cross-entropy over next-token predictions
- [ADR-08](ADR-08-serialisation-safetensors.md) — checkpoint saved after
  training completes
