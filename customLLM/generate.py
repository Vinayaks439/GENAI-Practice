"""Load a safetensors checkpoint and generate text.

Usage:
    python generate.py --prompt "Arjuna said," --max-new 200
    python generate.py --model-dir hf_export --temperature 0.8 --top-k 40
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
import torch.nn.functional as F
import tiktoken
from safetensors.torch import load_file

from model import GPTModel


def _pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_model(model_dir: Path, device: str) -> tuple[GPTModel, dict]:
    cfg_hf = json.loads((model_dir / "config.json").read_text())
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
    model.load_state_dict(load_file(str(model_dir / "model.safetensors")))
    return model.to(device).eval(), cfg


@torch.no_grad()
def generate(
    model: GPTModel,
    tok,
    prompt: str,
    *,
    max_new: int,
    temperature: float,
    top_k: int | None,
    top_p: float | None,
    repetition_penalty: float,
    device: str,
    ctx_len: int,
    eos_id: int | None = None,
) -> str:
    ids = torch.tensor([tok.encode(prompt, allowed_special={"<|endoftext|>"})],
                       dtype=torch.long, device=device)

    for _ in range(max_new):
        ctx = ids[:, -ctx_len:]
        logits = model(ctx)[:, -1, :]

        if repetition_penalty != 1.0:
            seen = ids[0].unique()
            logits[0, seen] /= repetition_penalty

        if temperature == 0:
            next_id = logits.argmax(dim=-1, keepdim=True)
        else:
            logits = logits / temperature

            if top_k is not None:
                v, _ = torch.topk(logits, k=min(top_k, logits.size(-1)))
                logits = torch.where(logits < v[:, [-1]],
                                      torch.full_like(logits, float("-inf")), logits)

            if top_p is not None:
                # Nucleus sampling: keep tokens whose cumulative prob ≤ top_p.
                sorted_logits, sorted_idx = torch.sort(logits, descending=True, dim=-1)
                cum = F.softmax(sorted_logits, dim=-1).cumsum(dim=-1)
                mask = cum > top_p
                # always keep the top-1 token
                mask[..., 0] = False
                sorted_logits = sorted_logits.masked_fill(mask, float("-inf"))
                logits = torch.empty_like(logits).scatter_(-1, sorted_idx, sorted_logits)

            probs = F.softmax(logits, dim=-1)
            next_id = torch.multinomial(probs, num_samples=1)

        if eos_id is not None and next_id.item() == eos_id:
            break
        ids = torch.cat([ids, next_id], dim=1)

    return tok.decode(ids[0].tolist())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model-dir",          type=Path, default=Path("hf_export"))
    p.add_argument("--prompt",             type=str,  default="Arjuna said,")
    p.add_argument("--max-new",            type=int,  default=200)
    p.add_argument("--temperature",        type=float, default=0.8)
    p.add_argument("--top-k",              type=int,  default=40)
    p.add_argument("--top-p",              type=float, default=None,
                   help="nucleus sampling threshold (disables top-k filter if both set)")
    p.add_argument("--repetition-penalty", type=float, default=1.1)
    p.add_argument("--seed",               type=int,   default=None)
    args = p.parse_args()

    if args.seed is not None:
        torch.manual_seed(args.seed)

    device = _pick_device()
    model, cfg = load_model(args.model_dir, device)
    tok = tiktoken.get_encoding("gpt2")
    eos_id = tok.encode("<|endoftext|>", allowed_special={"<|endoftext|>"})[0]

    print(f"device={device}  ctx={cfg['context_len']}  prompt={args.prompt!r}\n")
    out = generate(
        model, tok, args.prompt,
        max_new=args.max_new,
        temperature=args.temperature,
        top_k=args.top_k,
        top_p=args.top_p,
        repetition_penalty=args.repetition_penalty,
        device=device,
        ctx_len=cfg["context_len"],
        eos_id=eos_id,
    )
    print(out)


if __name__ == "__main__":
    main()
