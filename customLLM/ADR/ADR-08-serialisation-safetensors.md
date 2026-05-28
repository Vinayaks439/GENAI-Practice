# ADR-08 · Serialisation: safetensors + HF config.json

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Stage** | Export |
| **Deciders** | Project author |
| **Date** | 2026-05-28 |

---

## Context

After training, the model weights need to be saved in a format that is:

1. Safe to load from untrusted sources
2. Fast to load (production inference)
3. Compatible with the Hugging Face Hub ecosystem

Two checkpoints are produced:

| File | Purpose |
|------|---------|
| `checkpoints/checkpoint.pt` | Local re-training resumption; fast torch.save |
| `hf_export/model.safetensors` | Distribution and inference; safe, portable |

---

## Decision 1 — Local checkpoint: torch.save (.pt)

The local checkpoint stores everything needed to resume training:

```python
torch.save({
    'model_state': model.state_dict(),
    'cfg': cfg,
}, ckpt_path)
```

This includes the model configuration dict so the architecture can be
reconstructed without any external config file.

**torch.compile key stripping:**
When `--compile` is used, PyTorch prefixes all state dict keys with
`_orig_mod.`. This is stripped at save time so the checkpoint loads
cleanly whether or not compile was used:

```python
state = {k.removeprefix("_orig_mod."): v for k, v in model.state_dict().items()}
```

---

## Decision 2 — Distribution format: safetensors

### Why not just use .pt for distribution?

PyTorch's `.pt` format uses Python's `pickle` serialisation. A maliciously
crafted `.pt` file can execute arbitrary code when loaded:

```python
# A pickle payload can call __reduce__ on any class,
# including subprocess.Popen or os.system
torch.load("untrusted_model.pt")  # ← code execution risk
```

This is a genuine attack vector for shared model weights.

### Why safetensors?

```
safetensors format:
┌──────────────────────────────────────────────────────┐
│ 8 bytes: header length (little-endian uint64)         │
│ N bytes: JSON header                                  │
│          {"layer.weight": {"dtype": "F32",            │
│                            "shape": [384, 384],       │
│                            "data_offsets": [0, 589824]│
│                           }, ...}                     │
│ D bytes: raw tensor data (contiguous)                 │
└──────────────────────────────────────────────────────┘
```

- No code execution — it is a pure data format
- Memory-mapped loading: the OS pages in tensors only when accessed
- Supports all major frameworks (PyTorch, TensorFlow, JAX, Rust)
- Hugging Face Hub shows tensor metadata on the model page automatically

**Round-trip validation:**
After every export, we verify that all tensor values are bit-identical
between the saved and reloaded state dicts before reporting success.

---

## Decision 3 — config.json: HF naming conventions

The config uses Hugging Face GPT-2 field names so the repo page renders
a meaningful model card and future integrations require minimal remapping:

```
Our internal key   →   config.json key
────────────────────────────────────────
emb_dim            →   n_embd
n_heads            →   n_head
n_layers           →   n_layer
context_len        →   n_positions
drop_rate          →   attention_dropout, resid_pdrop, embd_pdrop
```

The `tokenizer_class: "GPT2Tokenizer"` field tells the Hub which tokenizer
to use for the "Try this model" widget.

---

## Decision 4 — README.md model card

HF Hub renders the `README.md` at the top of the model page. We include:

- YAML frontmatter with `tags`, `language`, `library_name`, `license`
- Minimal usage code snippet
- Architecture description

This is the minimum for the Hub to properly index the model and allow
others to discover and use it.

---

## Export directory layout

```
hf_export/
├── model.safetensors    ← weights; mmap-loadable; ~187MB for default config
├── config.json          ← HF-compatible architecture config
└── README.md            ← model card with YAML frontmatter
```

### Loading the exported model

```python
from safetensors.torch import load_file
from model import GPTModel
import json

cfg_hf = json.load(open("hf_export/config.json"))
cfg = {
    "vocab_size":  cfg_hf["vocab_size"],
    "context_len": cfg_hf["n_positions"],
    "emb_dim":     cfg_hf["n_embd"],
    "n_heads":     cfg_hf["n_head"],
    "n_layers":    cfg_hf["n_layer"],
    "drop_rate":   cfg_hf["attention_dropout"],
    "qkv_bias":    cfg_hf["qkv_bias"],
}
model = GPTModel(cfg)
model.load_state_dict(load_file("hf_export/model.safetensors"))
model.eval()
```

---

## Consequences

**Positive**
- safetensors is the de-facto standard on the HF Hub (~90% of new model
  uploads as of 2025)
- Zero-copy mmap means a 200MB model starts generating in under 1 second
  on a machine with warm disk cache
- The round-trip assertion catches any contiguity or dtype mismatch before
  an incorrect model reaches the Hub

**Negative / Trade-offs**
- The custom architecture is not supported by `transformers.AutoModel` —
  users need `model.py` from this repo to load it
- safetensors does not store the optimiser state — only model weights.
  For re-training resumption, `checkpoint.pt` (which includes optimiser
  state if saved) must be kept separately

---

## Upload command

```bash
# one-time login
huggingface-cli login

# upload via helper script
python push_to_hub.py <username>/mahabharata-gpt [--private]

# or manually
huggingface-cli upload <username>/mahabharata-gpt hf_export/ .
```

---

## Related ADRs

- [ADR-07](ADR-07-training-adamw-cosine.md) — checkpoint.pt is produced
  at end of training; safetensors export reads from it
