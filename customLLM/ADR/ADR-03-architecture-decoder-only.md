# ADR-03 · Architecture: Decoder-only Transformer

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Stage** | 5–7 — Attention + model |
| **Deciders** | Project author |
| **Date** | 2026-05-28 |

---

## Context

The Transformer family has three major variants. The right choice depends on
the task.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Transformer Variants                                                │
├─────────────────┬──────────────────┬────────────────────────────────┤
│  Encoder-only   │ Encoder-Decoder  │  Decoder-only                  │
│  (BERT, RoBERTa)│ (T5, BART)       │  (GPT-2/3/4, LLaMA, Mistral)  │
├─────────────────┼──────────────────┼────────────────────────────────┤
│ Bidirectional   │ Bidirectional    │  Causal (left-to-right)        │
│ attention       │ encoder +        │  attention only                │
│                 │ causal decoder   │                                 │
├─────────────────┼──────────────────┼────────────────────────────────┤
│ Best for:       │ Best for:        │  Best for:                     │
│ Classification  │ Translation      │  Text generation               │
│ Embedding       │ Summarisation    │  Completion / chat             │
│ NER             │ Seq2seq tasks    │  Language modelling            │
└─────────────────┴──────────────────┴────────────────────────────────┘
```

Our goal is **text generation**: given a prompt, continue it in the style of
the Mahabharata. This is a next-token prediction task.

---

## Decision

Use a **decoder-only** transformer.

The model has a single stack of N transformer blocks. Each block uses causal
(masked) self-attention — token at position `t` can only attend to positions
`0…t`. This enforces the autoregressive property.

```
ids → embed → [Block₀ → Block₁ → … → BlockN₋₁] → LN → LM head → logits
```

Training objective: predict the next token at every position simultaneously
(teacher forcing). This gives `B × T` gradient signals per batch, making
training very data-efficient.

---

## Consequences

**Positive**
- Simple: one stack of layers, one loss function (cross-entropy)
- Same family as GPT-2/3/4, LLaMA, Mistral — insights transfer directly
- Autoregressive generation is natural: append one token, re-run, repeat
- Scales better than encoder-decoder for pure generation at equivalent
  parameter count (Chinchilla, PaLM scaling papers)

**Negative / Trade-offs**
- Cannot be trivially repurposed for classification or translation without
  modifying the architecture or adding a task head
- Bidirectional context (seeing the full sentence before predicting a masked
  token, as in BERT) is unavailable — each position only sees its past

---

## Autoregressive training visualised

```
Input ids:   [4422,  310,  257,  689,   11]
             "Arjuna  on   a   battlefield  ,"

Positions:      0     1    2     3      4

Target ids:  [ 310,  257,  689,   11,  628]
             "on    a   battlefield   ,   \n"

Each position predicts the next:
  pos 0 ("Arjuna")      → predict "on"
  pos 1 ("on")          → predict "a"
  pos 2 ("a")           → predict "battlefield"
  …

Loss = average cross-entropy over all B×T predictions.
```

---

## Related ADRs

- [ADR-04](ADR-04-attention-causal-multihead.md) — causal masking is the
  mechanism that enforces the decoder-only constraint
- [ADR-07](ADR-07-training-adamw-cosine.md) — training setup
