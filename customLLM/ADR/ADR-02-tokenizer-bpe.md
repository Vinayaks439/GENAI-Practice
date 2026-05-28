# ADR-02 · Tokenizer: GPT-2 BPE via tiktoken

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Stage** | 4 — Tokenization |
| **Deciders** | Project author |
| **Date** | 2026-05-28 |

---

## Context

The tokenizer converts raw text into integer IDs that the model processes.
The choice affects vocabulary size, coverage of rare words, and training speed.

Three options were evaluated:

### Option A — Whitespace tokenizer

```
"Arjuna spoke" → ["Arjuna", "spoke"] → [0, 1]
```

- Vocab size: ~100K+ unique words in the Mahabharata alone
- **Problem:** Any word not seen in training is out-of-vocabulary (OOV).
  The model can never generate a name it hasn't seen.
- Verdict: ❌ Too brittle for a general model

### Option B — BPE trained from scratch on this corpus

```
Merge loop on bytes of this corpus only.
Vocab size: 256 bytes + num_merges (e.g. 512)
```

- Covers the corpus perfectly
- Small vocab → very coarse tokenization for any out-of-domain text
- Trained in seconds, but not reusable
- **Kept in the project (Stage 4 notebook) as an educational demonstration**
- Verdict: ⚠️ Good for pedagogy, not production

### Option C — Pre-trained GPT-2 BPE (tiktoken) ✅

```
"Yudhishthira" → ["Y", "udh", "ish", "thira"] → [56, 463, 680, 5661]
```

- 50,257 tokens; covers all UTF-8 text with no OOV
- Vocabulary was optimised on a large English web text corpus
- Fast (Rust implementation under `tiktoken`)
- Token IDs are byte-compatible with Hugging Face's `GPT2Tokenizer`

---

## Decision

Use `tiktoken.get_encoding("gpt2")` as the production tokenizer.

Also implement BPE from scratch in `04_tokenization.ipynb` to make the
algorithm visible before using the optimised library version.

---

## Consequences

**Positive**
- Zero OOV — any UTF-8 text, including Sanskrit transliterations and proper
  names, is tokenised into known subword pieces
- Fast encoding (~500K tokens/sec on CPU)
- Token IDs are byte-level compatible with GPT-2's `<|endoftext|>` special
  token, which we use as the document separator
- `np.uint16` is sufficient to store all IDs (max 50,256 < 65,535), halving
  storage vs `int32`

**Negative / Trade-offs**
- The vocabulary was optimised for English web text, not archaic Sanskrit names.
  `Yudhishthira` → 4 tokens, `Kunti` → 2 tokens. The model uses slightly more
  tokens per character name than a domain-specific tokenizer would
- Vocabulary is fixed — cannot add special domain tokens without retraining
  the tokenizer

---

## Token storage format

```
text → tiktoken.encode() → List[int] → np.uint16 → train.bin / val.bin
```

`np.memmap` reads the `.bin` files during training — memory usage stays
constant regardless of corpus size.

---

## Related ADRs

- [ADR-01](ADR-01-dataset-mahabharata.md) — corpus choice
- [ADR-03](ADR-03-architecture-decoder-only.md) — vocabulary size (50,257)
  directly determines the LM head output dimension
