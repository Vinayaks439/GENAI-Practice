---
library_name: pytorch
license: mit
tags:
  - gpt
  - text-generation
  - mahabharata
  - from-scratch
language:
  - en
---

# Mahabharata-GPT

A small decoder-only LM trained from scratch on the Mahabharata ([tilakd/mahabharata](https://www.kaggle.com/datasets/tilakd/mahabharata) on Kaggle).

## Usage

```python
from safetensors.torch import load_file
from model import GPTModel  # see repo
import json, torch, tiktoken

cfg = json.load(open('config.json'))
model_cfg = {
    'vocab_size':  cfg['vocab_size'],
    'context_len': cfg['n_positions'],
    'emb_dim':     cfg['n_embd'],
    'n_heads':     cfg['n_head'],
    'n_layers':    cfg['n_layer'],
    'drop_rate':   cfg['attention_dropout'],
    'qkv_bias':    cfg['qkv_bias'],
}
model = GPTModel(model_cfg)
model.load_state_dict(load_file('model.safetensors'))
tok = tiktoken.get_encoding('gpt2')
```

## Architecture

Pre-norm decoder-only transformer with multi-head causal attention, GELU MLP, and GPT-2 BPE tokenizer.
