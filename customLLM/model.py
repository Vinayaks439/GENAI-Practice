"""Reusable GPT building blocks — same definitions as the stage notebooks.

Stage 7 (training) and Stage 8 (generation) import from here so the model
definition lives in one place. The notebooks remain self-contained for
pedagogy by re-defining the blocks inline; this module is the practical
copy used by the training/generation loops.
"""
from __future__ import annotations

import math
import torch
import torch.nn as nn


class LayerNorm(nn.Module):
    def __init__(self, emb_dim: int, eps: float = 1e-5):
        super().__init__()
        self.eps = eps
        self.scale = nn.Parameter(torch.ones(emb_dim))
        self.shift = nn.Parameter(torch.zeros(emb_dim))

    def forward(self, x):
        mean = x.mean(dim=-1, keepdim=True)
        var = x.var(dim=-1, keepdim=True, unbiased=False)
        return self.scale * (x - mean) / torch.sqrt(var + self.eps) + self.shift


class GELU(nn.Module):
    def forward(self, x):
        return 0.5 * x * (1 + torch.tanh(
            math.sqrt(2 / math.pi) * (x + 0.044715 * x.pow(3))
        ))


class FeedForward(nn.Module):
    def __init__(self, emb_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(emb_dim, 4 * emb_dim),
            GELU(),
            nn.Linear(4 * emb_dim, emb_dim),
        )

    def forward(self, x):
        return self.net(x)


class MultiHeadAttention(nn.Module):
    def __init__(self, d_in, d_out, context_len, num_heads, dropout=0.0, qkv_bias=False):
        super().__init__()
        assert d_out % num_heads == 0
        self.num_heads = num_heads
        self.head_dim = d_out // num_heads
        self.d_out = d_out
        self.W_q = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_k = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.W_v = nn.Linear(d_in, d_out, bias=qkv_bias)
        self.out_proj = nn.Linear(d_out, d_out)
        self.dropout = nn.Dropout(dropout)
        self.register_buffer(
            "mask",
            torch.triu(torch.ones(context_len, context_len), diagonal=1).bool(),
        )

    def forward(self, x):
        B, T, _ = x.shape
        q = self.W_q(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.W_k(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.W_v(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        scores = q @ k.transpose(-2, -1)
        scores = scores.masked_fill(self.mask[:T, :T], float("-inf"))
        weights = torch.softmax(scores / (self.head_dim ** 0.5), dim=-1)
        weights = self.dropout(weights)
        ctx = (weights @ v).transpose(1, 2).contiguous().view(B, T, self.d_out)
        return self.out_proj(ctx)


class TransformerBlock(nn.Module):
    def __init__(self, cfg: dict):
        super().__init__()
        self.ln1 = LayerNorm(cfg["emb_dim"])
        self.attn = MultiHeadAttention(
            d_in=cfg["emb_dim"], d_out=cfg["emb_dim"],
            context_len=cfg["context_len"],
            num_heads=cfg["n_heads"],
            dropout=cfg["drop_rate"],
            qkv_bias=cfg.get("qkv_bias", False),
        )
        self.ln2 = LayerNorm(cfg["emb_dim"])
        self.ffn = FeedForward(cfg["emb_dim"])
        self.drop = nn.Dropout(cfg["drop_rate"])

    def forward(self, x):
        x = x + self.drop(self.attn(self.ln1(x)))
        x = x + self.drop(self.ffn(self.ln2(x)))
        return x


class GPTModel(nn.Module):
    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        self.tok_emb = nn.Embedding(cfg["vocab_size"], cfg["emb_dim"])
        self.pos_emb = nn.Embedding(cfg["context_len"], cfg["emb_dim"])
        self.drop = nn.Dropout(cfg["drop_rate"])
        self.blocks = nn.Sequential(*[TransformerBlock(cfg) for _ in range(cfg["n_layers"])])
        self.ln_f = LayerNorm(cfg["emb_dim"])
        self.lm_head = nn.Linear(cfg["emb_dim"], cfg["vocab_size"], bias=False)

    def forward(self, idx):
        B, T = idx.shape
        pos = torch.arange(T, device=idx.device)
        x = self.tok_emb(idx) + self.pos_emb(pos)
        x = self.drop(x)
        x = self.blocks(x)
        x = self.ln_f(x)
        return self.lm_head(x)  # (B, T, vocab_size)
