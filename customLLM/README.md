# Mahabharata-GPT — Build an LLM from Scratch

A decoder-only transformer language model trained on the Mahabharata, built
entirely from first principles in PyTorch. Every component — tokenizer,
attention, normalisation, training loop — is implemented without calling a
high-level library like Hugging Face Transformers.

---

## Table of Contents

1. [What this project is](#1-what-this-project-is)
2. [Project layout](#2-project-layout)
3. [Quick start](#3-quick-start)
4. [Architecture overview](#4-architecture-overview)
5. [Data layer](#5-data-layer)
6. [Tokenization](#6-tokenization)
7. [The Attention mechanism](#7-the-attention-mechanism)
8. [Transformer block](#8-transformer-block)
9. [Full GPT model](#9-full-gpt-model)
10. [Training setup](#10-training-setup)
11. [Generation / Sampling](#11-generation--sampling)
12. [Exporting to Hugging Face (safetensors)](#12-exporting-to-hugging-face-safetensors)
13. [Architecture Decision Records (ADRs)](#13-architecture-decision-records-adrs)
14. [Hyperparameter reference](#14-hyperparameter-reference)
15. [Glossary](#15-glossary)

---

## 1. What this project is

Most tutorials hand you a pre-built model to fine-tune. This project starts
from raw text and builds every layer by hand so you understand *why* each
design choice was made.

The corpus is the Mahabharata — one of the two major Sanskrit epics of ancient
India, totalling roughly 1.8 million words in its English translation. It is
freely available on Kaggle and large enough to demonstrate real language
patterns while fitting comfortably on a single laptop.

**What you will be able to do after working through this project:**

- Explain how a modern LLM processes text end-to-end
- Read and modify the attention and transformer code without confusion
- Train a language model on any text corpus you choose
- Export a trained model to Hugging Face Hub and share it

---

## 2. Project layout

```
customLLM/
│
├── model.py                 ← all PyTorch building blocks (single source of truth)
├── train_e2e.py             ← end-to-end training script (all stages in one run)
├── generate.py              ← load checkpoint and sample text
├── push_to_hub.py           ← upload hf_export/ to Hugging Face Hub
├── requirements.txt
│
├── 01_env_setup.ipynb       ← stage 1: deps + device check
├── 02_data_collection.ipynb ← stage 2: Kaggle download
├── 03_preprocessing.ipynb   ← stage 3: text cleaning
├── 04_tokenization.ipynb    ← stage 4: BPE (from scratch + tiktoken)
├── 05_attention.ipynb       ← stage 5: attention mechanics
├── 06_transformer_block.ipynb ← stage 6: LayerNorm, GELU, FFN, block
├── 07_gpt_and_training.ipynb  ← stage 7: full GPT + training loop
├── 08_generation.ipynb        ← stage 8: sampling strategies
│
├── data/
│   ├── raw/                 ← original Kaggle files (auto-populated)
│   └── processed/
│       ├── corpus.txt       ← full cleaned text
│       ├── train.txt / val.txt
│       ├── train.bin / val.bin   ← uint16 token ids (memory-mapped)
│
├── checkpoints/
│   ├── checkpoint.pt        ← PyTorch checkpoint (state dict + cfg)
│   └── training_history.json
│
└── hf_export/
    ├── model.safetensors    ← weights in safetensors format
    ├── config.json          ← HF-compatible config
    └── README.md            ← model card
```

---

## 3. Quick start

```bash
# 1. Create and activate the conda environment
conda create -n aiprac python=3.11 -y
conda activate aiprac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Train (downloads data automatically on first run)
python train_e2e.py --max-iters 5000 --batch-size 32

# 4. Generate text from the trained model
python generate.py --prompt "Arjuna said," --temperature 0.8 --top-k 40

# 5. Upload to Hugging Face
huggingface-cli login
python push_to_hub.py <your-username>/mahabharata-gpt
```

If you want to explore step-by-step, open the notebooks in order:
`01_env_setup.ipynb` → `02_data_collection.ipynb` → … → `08_generation.ipynb`

---

## 4. Architecture overview

The model is a **decoder-only transformer** — the same family as GPT-2, GPT-3,
and LLaMA. "Decoder-only" means there is no separate encoder; the model reads
and writes from the same sequence using *causal* (left-to-right) attention.

```
                        ┌─────────────────────────────────────┐
  Input token IDs       │          Mahabharata-GPT             │
  (integers)            │                                       │
                        │  ┌───────────────────────────────┐   │
  [4422, 310, 257, …]──►│  │  Token Embedding  (V × E)    │   │
                        │  └──────────────┬────────────────┘   │
                        │                 │                     │
                        │  ┌──────────────▼────────────────┐   │
                        │  │ Positional Embedding (T × E)  │   │
                        │  └──────────────┬────────────────┘   │
                        │                 │  (sum)              │
                        │                 ▼                     │
                        │  ┌───────────────────────────────┐   │
                        │  │        Dropout                │   │
                        │  └──────────────┬────────────────┘   │
                        │                 │                     │
                        │  ┌──────────────▼────────────────┐   │
                        │  │   TransformerBlock × N        │   │
                        │  │   (repeated N times)          │   │
                        │  └──────────────┬────────────────┘   │
                        │                 │                     │
                        │  ┌──────────────▼────────────────┐   │
                        │  │     Final LayerNorm            │   │
                        │  └──────────────┬────────────────┘   │
                        │                 │                     │
                        │  ┌──────────────▼────────────────┐   │
                        │  │   LM Head  Linear(E → V)      │   │
                        │  └──────────────┬────────────────┘   │
                        └─────────────────┼───────────────────-┘
                                          │
                                          ▼
                          Logits  (B × T × V)
                          one score per vocabulary token
                          per position in the sequence
```

**Key dimensions:**

| Symbol | Meaning | Default |
|--------|---------|---------|
| `V` | Vocabulary size | 50,257 (GPT-2 BPE) |
| `E` | Embedding dimension (`emb_dim`) | 384 |
| `T` | Context length (max tokens) | 256 |
| `N` | Number of transformer blocks | 6 |
| `H` | Number of attention heads | 6 |
| `B` | Batch size | 32 |

---

## 5. Data layer

### 5.1 Raw corpus

The Mahabharata dataset (`tilakd/mahabharata` on Kaggle) contains the full
English translation across `.txt` and `.csv` files — roughly 5–6 MB of text,
or ~1.8 million words.

### 5.2 Preprocessing pipeline

```
raw .txt / .csv files
        │
        ▼
 unicodedata.normalize('NFKC')   ← normalise Unicode (e.g. fullwidth → ASCII)
        │
        ▼
 strip Gutenberg headers/footers ← "*** START OF …" markers removed
        │
        ▼
 curly quotes → ASCII            ← ' ' " " → ' "
        │
        ▼
 collapse 3+ blank lines → 2    ← reduce whitespace
        │
        ▼
 concatenate documents           ← joined with <|endofdoc|> sentinel
        │
        ▼
 90 / 10 character split
 ├── data/processed/train.txt
 └── data/processed/val.txt
```

### 5.3 Memory-mapped token loading

During training, token IDs are stored as `uint16` binary files
(`train.bin`, `val.bin`). They are read via `np.memmap` — the OS pages in
only what is needed, so RAM usage stays constant no matter how large the
corpus grows.

```
train.bin  ──np.memmap──►  [4422, 310, 257, 689, 11, …]  (uint16 array)
                                    │
                     random window sampling
                                    │
                 ┌──────────────────┴──────────────────┐
                 │  x = ids[i : i+T]                   │
                 │  y = ids[i+1 : i+T+1]  (shifted +1) │
                 └──────────────────┬──────────────────┘
                                    │
                    batch together B windows
                                    │
                                    ▼
                          (B × T) tensor pair
```

The `y` is the same window shifted by one because the model's job is to
predict the *next* token at every position. Token 0 predicts token 1, token 1
predicts token 2, and so on — this is called **autoregressive** training.

---

## 6. Tokenization

### Why not split on spaces?

Splitting on whitespace gives a vocabulary of ~100,000+ unique words in the
Mahabharata alone. Rare words (names, inflections) become out-of-vocabulary
immediately. The model can never generate a word it hasn't seen.

### Byte-Pair Encoding (BPE)

BPE starts with individual bytes (256 symbols) and iteratively merges the most
frequent adjacent pair into a new symbol. After enough merges you have a vocab
of ~50,000 tokens that covers any text — rare words are split into familiar
sub-word pieces.

```
Example corpus (simplified):
  "Arjuna Arjuna Krishna"

Byte sequence:
  A r j u n a   A r j u n a   K r i s h n a

Count pairs:
  (A,r)=2  (r,j)=2  (j,u)=2  (u,n)=2  (n,a)=2  ...

Merge most frequent → (n,a) = "na":
  A r j u na   A r j u na   K r i s h na

Merge next → (r,j) = "rj":
  A rj u na   A rj u na   K r i s h na

... continue until vocab target reached.

Final tokenization of "Arjuna":
  ["Ar", "jun", "a"]   → 3 tokens instead of 6 bytes
```

We use OpenAI's `tiktoken` library with the `gpt2` encoding — the same 50,257
token vocabulary GPT-2 was trained on. This is stable, fast, and means our
model is token-compatible with GPT-2.

---

## 7. The Attention mechanism

Attention lets every token look at every other token (or in our case, every
*previous* token) and decide how much to borrow from it.

### 7.1 Scaled dot-product attention (one head)

```
Query (Q) ──────────────┐
                         ▼
Key   (K) ──────── Q × Kᵀ ──── ÷ √d_k ──── mask ──── softmax ──── × V ──► context
                                                                      │
Value (V) ────────────────────────────────────────────────────────────┘
```

In plain English:

1. **Q** (query) — "what am I looking for?"
2. **K** (key) — "what do I contain?"
3. **V** (value) — "what do I actually contribute?"

Each token generates its own Q, K, and V by multiplying with learned weight
matrices. The dot product `Q · Kᵀ` measures how relevant each other token is.
We divide by `√d_k` to keep gradients from vanishing when `d_k` is large.
`softmax` turns the scores into a probability distribution summing to 1.
Finally we take the weighted sum of all `V` vectors.

### 7.2 The causal mask

In a language model, token at position `t` must not see tokens at positions
`> t` (they are the future — the answer we are trying to predict). We enforce
this by masking the upper triangle of the attention matrix with `-∞` before
the softmax, so those positions get weight 0.

```
Attention matrix for a 5-token sequence.
Each row is a query token; each column is a key token.

       tok0  tok1  tok2  tok3  tok4
tok0 [  ·    -∞    -∞    -∞    -∞  ]   tok0 can only attend to itself
tok1 [  ·     ·    -∞    -∞    -∞  ]   tok1 can see tok0 and itself
tok2 [  ·     ·     ·    -∞    -∞  ]
tok3 [  ·     ·     ·     ·    -∞  ]
tok4 [  ·     ·     ·     ·     ·  ]   tok4 can see all previous tokens

· = actual attention score (computed)
-∞ → 0 after softmax (masked away)
```

### 7.3 Multi-head attention

Instead of one set of Q/K/V, we run `H` independent "heads" in parallel on
smaller slices of the embedding (`d_k = emb_dim / H`). Each head can
specialise — one might learn syntactic structure, another co-reference, etc.

```
                    x  (B × T × E)
                    │
       ┌────────────┼────────────┐
       │            │            │
    head_1       head_2  …   head_H      (each gets E/H dims)
       │            │            │
  Attn(Q₁K₁V₁) Attn(Q₂K₂V₂)  ...
       │            │            │
       └────────────┼────────────┘
                    │  concat
                    ▼
              (B × T × E)
                    │
               out_proj   (E × E linear)
                    │
                    ▼
              (B × T × E)
```

**Why multiple heads?**
A single head produces one attention pattern. With `H` heads you get `H`
different relationship maps over the same input — richer than any single view.

---

## 8. Transformer block

One transformer block wraps multi-head attention and a feed-forward network
with residual connections and layer normalisation.

```
  Input x  (B × T × E)
      │
      ├─────────────────────────────────────────────┐  residual
      │                                             │
      ▼                                             │
  LayerNorm                                         │
      │                                             │
      ▼                                             │
  MultiHeadAttention (causal)                       │
      │                                             │
      ▼                                             │
  Dropout                                           │
      │                                             │
      └────────────── + ◄───────────────────────────┘
                      │
                      ├─────────────────────────────┐  residual
                      │                             │
                      ▼                             │
                  LayerNorm                         │
                      │                             │
                      ▼                             │
               FeedForward (MLP)                    │
               ┌────────────────┐                   │
               │ Linear(E→4E)   │                   │
               │ GELU           │                   │
               │ Linear(4E→E)   │                   │
               └────────────────┘                   │
                      │                             │
                      ▼                             │
                  Dropout                           │
                      │                             │
                      └───────── + ◄───────────────-┘
                                 │
                                 ▼
                         Output  (B × T × E)
```

### Pre-norm vs Post-norm

We use **pre-norm** (LayerNorm *before* the sublayer). The original
"Attention Is All You Need" paper used post-norm, but pre-norm trains more
stably without a careful learning-rate warmup schedule.

### Residual connections

The `x = x + sublayer(x)` pattern lets gradients flow directly from the loss
back to the earliest layers without passing through every transformation.
Without residuals, deep networks suffer from vanishing gradients.

### GELU activation

```
        GELU(x)                  ReLU(x)
           │                        │
     ──────┤                  ──────┤
      /    │                   /    │
     /     │                  /     │
────/      │           ──────/      │
           │                        │

GELU is smooth near zero;         ReLU is a hard zero for x < 0.
allows small negative values      Faster but less expressive.
to pass through.
```

GELU (Gaussian Error Linear Unit) outperforms ReLU on language tasks
empirically. GPT-2, BERT, and most modern LLMs use it.

### Feed-forward expansion

The MLP expands to 4× the embedding size in the hidden layer:

```
E ──► Linear ──► 4E ──► GELU ──► Linear ──► E
```

This `4×` ratio is empirical — it comes from the original Transformer paper
and has remained the standard. It gives the model a large "scratch pad" to
compute intermediate representations.

---

## 9. Full GPT model

```
  Token IDs  (B × T)
       │
       ▼
  ┌─────────────────────────────────────────────────────┐
  │  Token Embedding                                     │
  │  nn.Embedding(vocab_size=50257, emb_dim=384)         │
  │  Each integer ID → a 384-dim float vector           │
  └──────────────────────────┬──────────────────────────┘
                             │
  ┌──────────────────────────▼──────────────────────────┐
  │  Positional Embedding                                │
  │  nn.Embedding(context_len=256, emb_dim=384)          │
  │  Position 0 → vector₀, position 1 → vector₁, …     │
  │  (learned, not sinusoidal)                          │
  └──────────────────────────┬──────────────────────────┘
                             │  ← add (not concat)
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │  Dropout(p=0.1)                                      │
  └──────────────────────────┬──────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │  N = 6 times
              ┌─────▼──────────────────────────────────┐
              │  TransformerBlock                        │
              │  ┌──────────────────────────────────┐   │
              │  │ LayerNorm + MultiHeadAttention    │   │
              │  │ (H=6 heads, head_dim=64)          │   │
              │  ├──────────────────────────────────-┤   │
              │  │ LayerNorm + FeedForward           │   │
              │  │ (384 → 1536 → 384, GELU)         │   │
              │  └──────────────────────────────────-┘   │
              └─────────────────────────────────────────┘
                             │
                    └────────┘
                             │
  ┌──────────────────────────▼──────────────────────────┐
  │  Final LayerNorm                                     │
  └──────────────────────────┬──────────────────────────┘
                             │
  ┌──────────────────────────▼──────────────────────────┐
  │  LM Head:  Linear(384 → 50257, bias=False)           │
  │  One logit per vocabulary token                      │
  └──────────────────────────┬──────────────────────────┘
                             │
                             ▼
                    Logits  (B × T × 50257)
```

**Total parameters (default config):**

| Component | Parameters |
|-----------|-----------|
| Token embedding | 50,257 × 384 = 19.3M |
| Positional embedding | 256 × 384 = 98K |
| 6 × TransformerBlock | 6 × (MHA + FFN + norms) ≈ 28.3M |
| Final LN + LM head | 384 + 50,257 × 384 = 19.3M |
| **Total** | **~49M** |

---

## 10. Training setup

### Loss function

Cross-entropy loss over the full vocabulary. Every position in the sequence
generates a prediction, giving `B × T` loss terms per batch:

```
logits  (B × T × V)   ← model output
targets (B × T)        ← token ids shifted by 1

loss = cross_entropy(logits.flatten(0,1), targets.flatten())
     = − (1/BT) Σ log P(correct_token)
```

At random init, loss = `ln(50257) ≈ 10.82`. Lower is better.
**Perplexity** = `exp(loss)` — how many tokens the model is "choosing between"
on average. 10,000 = confused; 100 = learning; 20 = good for a small model.

### Optimiser: AdamW

Adam with decoupled weight decay. The `0.1` weight decay acts as L2
regularisation on the weights (but *not* on biases or LayerNorm parameters).
`betas=(0.9, 0.95)` is the GPT-3 recipe.

### Cosine LR schedule with linear warmup

```
lr
▲
│    warmup       cosine decay
│   /‾‾‾‾‾‾\     ╲
│  /         \     ╲__________
│ /                           ╲___  lr_min
│/
└─────────────────────────────────► step
   0     warmup    max_iters
```

- **Warmup (0 → 100 steps):** Start near 0 and ramp to `lr_max=3e-4`.
  Prevents large gradient updates before the model has any structure.
- **Cosine decay (100 → 5000):** Smoothly reduces to `lr_min=3e-5`.
  Cosine is preferred over step-decay because it avoids sudden loss spikes.

### Gradient clipping

```python
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
```

Caps the global gradient norm at 1.0. If gradients are larger than 1.0 they
are scaled down proportionally. Prevents occasional large batches from causing
a catastrophic weight update. The `gnorm` metric in the progress bar shows the
raw norm before clipping — healthy range is 0.3–1.5.

### Mixed precision (bf16)

On MPS/CUDA, the forward and backward passes run in `bfloat16` (16-bit floats)
instead of `float32`. This roughly halves memory usage and doubles throughput
with no meaningful quality loss. Weight updates are still accumulated in
`float32` internally by the optimiser.

### Gradient accumulation

```
effective_batch = batch_size × grad_accum

--batch-size 8 --grad-accum 4  →  effective batch = 32
```

Runs several small forward/backward passes before calling `optim.step()`,
accumulating gradients. Useful when GPU memory is limited but you want the
stability of a larger batch.

---

## 11. Generation / Sampling

After training, the model produces a probability distribution over the
vocabulary for the next token. How you sample from it controls
creativity vs coherence.

```
  Prompt tokens ──► model ──► logits (50257 values)
                                  │
                       ┌──────────┴──────────────┐
                       │  sampling strategy       │
                       └──────────┬───────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
     temperature               top-k                  top-p
    ─────────────           ──────────             ──────────────
    logits / T              keep only              keep smallest
                            top k tokens            set whose
    T < 1 → sharper         (e.g. k=40)             cumulative
    T = 1 → unchanged       renormalise             prob ≥ p
    T > 1 → flatter         and sample              (nucleus)
          │                       │                       │
          └───────────────────────┴───────────────────────┘
                                  │
                              next token id
                                  │
                           append to sequence
                                  │
                              repeat...
```

**Repetition penalty:** Tokens already in the generated sequence have their
logits divided by `repetition_penalty` (e.g. 1.1) before sampling. Makes the
model less likely to loop.

---

## 12. Exporting to Hugging Face (safetensors)

### Why safetensors?

`.pt` (pickle-based) files can execute arbitrary Python code when loaded —
a security risk. `safetensors` is:

- **Safe:** no code execution, just tensors
- **Fast:** zero-copy mmap loading
- **Portable:** readable from Python, Rust, JS, C

### Export layout

```
hf_export/
├── model.safetensors    ← all weight tensors, contiguous, with metadata
├── config.json          ← HF-style config (n_embd, n_head, n_layer, ...)
└── README.md            ← model card (shown on HF Hub page)
```

### config.json field mapping

```
Our config key   →   HF config key
─────────────────────────────────
emb_dim          →   n_embd
n_heads          →   n_head
n_layers         →   n_layer
context_len      →   n_positions
drop_rate        →   attention_dropout / resid_pdrop / embd_pdrop
```

### Upload

```bash
# one-time login
huggingface-cli login

# upload
python push_to_hub.py <username>/mahabharata-gpt

# or manually
huggingface-cli upload <username>/mahabharata-gpt hf_export/ .
```

---

## 13. Architecture Decision Records (ADRs)

Each ADR documents *why* a design choice was made — context, decision, and
consequences. They live in the [`ADR/`](ADR/) folder, one file per decision.

| ADR | Title | Stage |
|-----|-------|-------|
| [ADR-01](ADR/ADR-01-dataset-mahabharata.md) | Dataset: Mahabharata | 2 — Data collection |
| [ADR-02](ADR/ADR-02-tokenizer-bpe.md) | Tokenizer: GPT-2 BPE via tiktoken | 4 — Tokenization |
| [ADR-03](ADR/ADR-03-architecture-decoder-only.md) | Architecture: Decoder-only Transformer | 5–7 — Model |
| [ADR-04](ADR/ADR-04-attention-causal-multihead.md) | Attention: Causal Multi-Head Self-Attention | 5 — Attention |
| [ADR-05](ADR/ADR-05-normalisation-prenorm-layernorm.md) | Normalisation: Pre-norm LayerNorm | 6 — Block |
| [ADR-06](ADR/ADR-06-activation-gelu.md) | Activation: GELU (tanh approximation) | 6 — Block |
| [ADR-07](ADR/ADR-07-training-adamw-cosine.md) | Training: AdamW + Cosine LR + Mixed Precision | 7 — Training |
| [ADR-08](ADR/ADR-08-serialisation-safetensors.md) | Serialisation: safetensors + HF config.json | Export |

---

## 14. Hyperparameter reference

| Flag | Default | Notes |
|------|---------|-------|
| `--context-len` | 256 | Sequence length. Memory scales as O(T²). |
| `--emb-dim` | 384 | Embedding dimension. Must be divisible by `n-heads`. |
| `--n-heads` | 6 | Attention heads. `head_dim = emb_dim / n_heads = 64`. |
| `--n-layers` | 6 | Transformer block count. |
| `--drop-rate` | 0.1 | Dropout probability (attention + residual + embedding). |
| `--max-iters` | 2000 | Training steps. |
| `--batch-size` | 32 | Sequences per step. |
| `--grad-accum` | 1 | Steps before optimizer update. Effective batch = batch × accum. |
| `--lr-max` | 3e-4 | Peak learning rate. |
| `--lr-min` | 3e-5 | Final learning rate (cosine target). |
| `--warmup` | 100 | Steps to ramp LR from 0 → lr_max. |
| `--weight-decay` | 0.1 | AdamW weight decay (L2 on weights only). |
| `--compile` | off | Enable `torch.compile` (PyTorch 2.x, CUDA recommended). |

**Preset configurations:**

```bash
# Quick experiment (~30 min, CPU/MPS)
python train_e2e.py --emb-dim 128 --n-heads 4 --n-layers 3 --max-iters 2000

# Default (~2 hr, MPS)
python train_e2e.py --max-iters 5000 --batch-size 32

# Full quality (~8 hr, CUDA GPU)
python train_e2e.py --emb-dim 512 --n-heads 8 --n-layers 8 \
    --max-iters 20000 --batch-size 64 --compile
```

---

## 15. Glossary

| Term | Meaning |
|------|---------|
| **Autoregressive** | Generates one token at a time, each conditioned on all previous |
| **BPE** | Byte-Pair Encoding — subword tokenization algorithm |
| **Causal mask** | Upper-triangular -∞ mask preventing attention to future tokens |
| **Context length** | Maximum number of tokens the model processes at once |
| **Cross-entropy** | Loss measuring divergence between predicted and true distribution |
| **Decoder-only** | Transformer with only the decoder stack; used for generation |
| **Embedding** | Learned lookup table mapping integer IDs to float vectors |
| **GELU** | Gaussian Error Linear Unit — smooth activation function |
| **Gradient clipping** | Scaling gradients down when their norm exceeds a threshold |
| **Gradient accumulation** | Accumulating gradients over multiple batches before updating weights |
| **Head** | One parallel attention computation in multi-head attention |
| **LayerNorm** | Normalises each token's features to zero mean, unit variance |
| **LM head** | Final linear layer projecting embeddings to vocabulary logits |
| **Logits** | Raw (unnormalised) scores before softmax |
| **Mixed precision** | Training in bf16/fp16 for speed; master weights kept in fp32 |
| **Perplexity** | exp(loss) — how many tokens the model is "unsure between" |
| **Pre-norm** | LayerNorm applied before (not after) each sublayer |
| **Residual connection** | Skip connection: `output = sublayer(x) + x` |
| **safetensors** | Safe, fast tensor serialisation format (no code execution) |
| **Top-k sampling** | Restrict sampling to the k most probable next tokens |
| **Top-p (nucleus)** | Restrict sampling to smallest set with cumulative prob ≥ p |
| **Warmup** | Gradual LR increase at training start to prevent early instability |
| **Weight decay** | L2 regularisation on model weights to reduce overfitting |


## 16. References
- [Transformer Arch using pytorch](https://medium.com/data-science/build-your-own-transformer-from-scratch-using-pytorch-84c850470dcb)
