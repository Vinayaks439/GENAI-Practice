# ADR-04 · Attention: Causal Multi-Head Self-Attention

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Stage** | 5 — Attention |
| **Deciders** | Project author |
| **Date** | 2026-05-28 |

---

## Context

Self-attention is the core operation of the Transformer. Several design
decisions were needed:

1. Should attention be bidirectional or causal?
2. Single-head or multi-head?
3. How to implement multiple heads — separate modules or one reshaped matmul?
4. Where does the causal mask live?

---

## Decision

### 1. Causal (masked) attention

Token at position `t` may only attend to positions `0 … t`.
Implemented via an upper-triangular `-inf` mask applied before softmax.

```
Attention scores for a 5-token sequence before masking:

       t=0   t=1   t=2   t=3   t=4
t=0 [  s00   s01   s02   s03   s04 ]
t=1 [  s10   s11   s12   s13   s14 ]
t=2 [  s20   s21   s22   s23   s24 ]
t=3 [  s30   s31   s32   s33   s34 ]
t=4 [  s40   s41   s42   s43   s44 ]

After applying causal mask (-inf → 0 after softmax):

       t=0   t=1   t=2   t=3   t=4
t=0 [  s00   -∞    -∞    -∞    -∞  ]  ← can only see itself
t=1 [  s10   s11   -∞    -∞    -∞  ]
t=2 [  s20   s21   s22   -∞    -∞  ]
t=3 [  s30   s31   s32   s33   -∞  ]
t=4 [  s40   s41   s42   s43   s44 ]  ← can see all history
```

### 2. Multi-head attention (H = 6 heads)

Run H parallel attention computations on equal-sized slices of the embedding.

```
emb_dim = 384,  n_heads = 6,  head_dim = 384 / 6 = 64

x  (B × T × 384)
│
├─ W_q ─► Q (B × T × 384) ─ reshape ─► (B × H × T × 64)
├─ W_k ─► K (B × T × 384) ─ reshape ─► (B × H × T × 64)
└─ W_v ─► V (B × T × 384) ─ reshape ─► (B × H × T × 64)

For each head h:
  scores_h = Q_h @ K_hᵀ / √64       (B × T × T)
  scores_h = scores_h.masked_fill(mask, -inf)
  weights_h = softmax(scores_h)
  ctx_h = weights_h @ V_h            (B × T × 64)

Concat all heads:
  ctx = [ctx_0 | ctx_1 | … | ctx_5]  (B × T × 384)
  out = ctx @ W_out                  (B × T × 384)
```

**Why multiple heads?**
Each head learns a different attention pattern — one may track subject-verb
agreement, another co-reference (who "he" refers to), another proximity.
A single head forces one pattern to capture everything.

### 3. Single-matmul implementation

Instead of H separate `nn.Linear` modules, we use one `W_q`, `W_k`, `W_v`
of size `(emb_dim, emb_dim)` and reshape the output:

```python
q = self.W_q(x).view(B, T, H, head_dim).transpose(1, 2)
# shape: (B, H, T, head_dim)
```

This is one large matmul instead of H small ones — faster on GPU/MPS due to
better parallelism and reduced kernel launch overhead.

### 4. Mask as a registered buffer

```python
self.register_buffer(
    'mask',
    torch.triu(torch.ones(context_len, context_len), diagonal=1).bool()
)
```

`register_buffer` means:
- Not a parameter (not updated by the optimiser)
- Moves automatically with `.to(device)` / `.to(dtype)`
- Saved and loaded with `state_dict()`

---

## Scaling the dot products

Without scaling, dot products grow with `head_dim`:

```
E[qᵢ · kⱼ] ≈ head_dim   (for random unit-norm vectors)

head_dim = 64 → scores ~8× larger than needed
→ softmax saturates → gradients vanish
```

Dividing by `√head_dim` keeps the variance of scores at ~1 regardless of
`head_dim`.

---

## Consequences

**Positive**
- Causal mask is registered once at module creation and reused every forward
  pass — zero allocation during training
- Single-matmul multi-head is the same pattern used by PyTorch's
  `nn.MultiheadAttention` and Flash Attention — switching to SDPA is trivial
- H=6 heads with head_dim=64 is the GPT-2 small ratio — well-studied behaviour

**Negative / Trade-offs**
- Full O(T²) memory for the attention matrix. Context T=256 is fine;
  scaling to T=4096+ would require Flash Attention or window attention
- The causal mask buffer has size `(T × T)` — for T=256 this is 64KB,
  negligible. For T=8192 it would be 64MB per layer

---

## Related ADRs

- [ADR-03](ADR-03-architecture-decoder-only.md) — the causal mask is what
  makes the architecture decoder-only
- [ADR-05](ADR-05-normalisation-prenorm-layernorm.md) — attention sits inside
  the transformer block alongside LayerNorm
