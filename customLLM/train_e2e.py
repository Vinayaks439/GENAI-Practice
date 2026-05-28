"""End-to-end training script for the Mahabharata GPT.

Runs every stage from the notebooks in one shot:

  1. Download   → Kaggle dataset (cached, skipped on re-run)
  2. Preprocess → clean + train/val split
  3. Tokenize   → GPT-2 BPE → train.bin / val.bin (np.uint16)
  4. Train      → GPT, AdamW, mixed precision, cosine LR, grad clipping
  5. Export     → model.safetensors + config.json (Hugging Face friendly)

Optimizations enabled by default:

  - bf16 mixed precision (CUDA / MPS) — ~2× throughput, negligible quality loss
  - Memory-mapped data loading (np.memmap) — keeps RAM flat for huge corpora
  - Cosine LR schedule with linear warmup
  - Gradient accumulation (raises effective batch size without using more VRAM)
  - Fused AdamW on CUDA
  - Optional torch.compile (`--compile`) for further speedup on PyTorch 2.x
  - SDPA for attention (Flash/MemEfficient kernels) when available

Usage:
    python train_e2e.py                  # full pipeline, defaults
    python train_e2e.py --max-iters 5000 # train longer
    python train_e2e.py --skip-data      # reuse cached data/processed/*.bin
    python train_e2e.py --compile        # PyTorch 2 compile
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import time
import unicodedata
import re
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from model import GPTModel


# ─────────────────────────────────────────────────────────────────────────────
# Config defaults — override via CLI
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_MODEL_CFG = {
    "vocab_size":  50257,   # GPT-2 BPE
    "context_len": 256,
    "emb_dim":     384,
    "n_heads":     6,
    "n_layers":    6,
    "drop_rate":   0.1,
    "qkv_bias":    False,
}


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — data download
# ─────────────────────────────────────────────────────────────────────────────
def stage_download(raw_dir: Path) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    if any(raw_dir.iterdir()):
        print(f"[1/5] download   ✓ raw/ already populated → {raw_dir}")
        return raw_dir

    import kagglehub
    print("[1/5] download   ↓ fetching tilakd/mahabharata from Kaggle …")
    src = Path(kagglehub.dataset_download("tilakd/mahabharata"))
    for f in src.rglob("*"):
        if f.is_file():
            shutil.copy2(f, raw_dir / f.name)
    print(f"[1/5] download   ✓ staged {len(list(raw_dir.iterdir()))} files → {raw_dir}")
    return raw_dir


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3 — preprocessing
# ─────────────────────────────────────────────────────────────────────────────
_GUTENBERG_START = re.compile(r"\*\*\* ?START OF.*?\*\*\*", re.IGNORECASE)
_GUTENBERG_END   = re.compile(r"\*\*\* ?END OF.*?\*\*\*",   re.IGNORECASE)
_MULTI_BLANK     = re.compile(r"\n{3,}")
_TRAIL_WS        = re.compile(r"[ \t]+(\n|$)")


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    if (m := _GUTENBERG_START.search(text)):
        text = text[m.end():]
    if (m := _GUTENBERG_END.search(text)):
        text = text[:m.start()]
    text = (text
            .replace("‘", "'").replace("’", "'")
            .replace("“", '"').replace("”", '"')
            .replace("–", "-").replace("—", "-"))
    text = _TRAIL_WS.sub(r"\1", text)
    text = _MULTI_BLANK.sub("\n\n", text)
    return text.strip()


def stage_preprocess(raw_dir: Path, proc_dir: Path) -> tuple[Path, Path]:
    proc_dir.mkdir(parents=True, exist_ok=True)
    train_p = proc_dir / "train.txt"
    val_p   = proc_dir / "val.txt"
    if train_p.exists() and val_p.exists():
        print(f"[2/5] preprocess ✓ cached at {proc_dir}")
        return train_p, val_p

    import pandas as pd
    docs: list[str] = []
    for p in sorted(raw_dir.iterdir()):
        if p.suffix.lower() == ".csv":
            df = pd.read_csv(p)
            text_cols = [c for c in df.columns if df[c].dtype == object]
            docs.append("\n".join(df[text_cols].astype(str).agg(" ".join, axis=1).tolist()))
        elif p.suffix.lower() == ".txt":
            docs.append(p.read_text(encoding="utf-8", errors="replace"))

    corpus = "\n\n<|endofdoc|>\n\n".join(_clean(d) for d in docs)
    (proc_dir / "corpus.txt").write_text(corpus, encoding="utf-8")
    split = int(0.9 * len(corpus))
    train_p.write_text(corpus[:split], encoding="utf-8")
    val_p.write_text(corpus[split:], encoding="utf-8")
    print(f"[2/5] preprocess ✓ {len(corpus):,} chars → train/val ({split:,} / {len(corpus)-split:,})")
    return train_p, val_p


# ─────────────────────────────────────────────────────────────────────────────
# Stage 4 — tokenization (cached binaries)
# ─────────────────────────────────────────────────────────────────────────────
def stage_tokenize(train_p: Path, val_p: Path, proc_dir: Path) -> tuple[Path, Path]:
    train_bin = proc_dir / "train.bin"
    val_bin   = proc_dir / "val.bin"
    if train_bin.exists() and val_bin.exists():
        print(f"[3/5] tokenize   ✓ cached binaries at {proc_dir}")
        return train_bin, val_bin

    import tiktoken
    tok = tiktoken.get_encoding("gpt2")
    for src_p, dst_p in ((train_p, train_bin), (val_p, val_bin)):
        text = src_p.read_text(encoding="utf-8")
        ids  = tok.encode(text, allowed_special={"<|endoftext|>"})
        np.array(ids, dtype=np.uint16).tofile(dst_p)
        print(f"[3/5] tokenize   ✓ {src_p.name:10s} → {dst_p.name}  ({len(ids):,} tokens)")
    return train_bin, val_bin


# ─────────────────────────────────────────────────────────────────────────────
# Stage 7 — training
# ─────────────────────────────────────────────────────────────────────────────
def _fmt_eta(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s   = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def _pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _pick_dtype(device: str) -> torch.dtype | None:
    """Pick best autocast dtype, or None to disable autocast."""
    if device == "cuda":
        # bf16 is safer than fp16 (no dynamic loss scaling needed)
        return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    if device == "mps":
        # MPS supports bf16 since recent torch — fall back to no autocast if it fails.
        return torch.bfloat16
    return None  # cpu: keep fp32


def _cosine_lr(step: int, *, warmup: int, max_steps: int, lr_max: float, lr_min: float) -> float:
    if step < warmup:
        return lr_max * (step + 1) / warmup
    if step >= max_steps:
        return lr_min
    progress = (step - warmup) / max(1, max_steps - warmup)
    coeff = 0.5 * (1.0 + math.cos(math.pi * progress))
    return lr_min + coeff * (lr_max - lr_min)


class TokenLoader:
    """Memory-mapped random-window sampler. Keeps RAM flat for huge corpora."""

    def __init__(self, bin_path: Path, context_len: int, batch_size: int, device: str):
        self.ids = np.memmap(bin_path, dtype=np.uint16, mode="r")
        self.T   = context_len
        self.B   = batch_size
        self.device = device

    def __call__(self) -> tuple[torch.Tensor, torch.Tensor]:
        starts = np.random.randint(0, len(self.ids) - self.T - 1, size=self.B)
        x = np.stack([self.ids[i:i + self.T].astype(np.int64)         for i in starts])
        y = np.stack([self.ids[i + 1:i + 1 + self.T].astype(np.int64) for i in starts])
        xt = torch.from_numpy(x)
        yt = torch.from_numpy(y)
        if self.device == "cuda":
            xt = xt.pin_memory().to(self.device, non_blocking=True)
            yt = yt.pin_memory().to(self.device, non_blocking=True)
        else:
            xt = xt.to(self.device)
            yt = yt.to(self.device)
        return xt, yt


def stage_train(
    *,
    train_bin: Path,
    val_bin: Path,
    cfg: dict,
    out_dir: Path,
    max_iters: int,
    batch_size: int,
    grad_accum: int,
    lr_max: float,
    lr_min: float,
    warmup: int,
    weight_decay: float,
    eval_every: int,
    eval_batches: int,
    compile_model: bool,
) -> Path:
    device = _pick_device()
    dtype  = _pick_dtype(device)
    print(f"[4/5] train      • device={device}  autocast={dtype}  compile={compile_model}")

    model = GPTModel(cfg).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[4/5] train      • params={n_params:,} (~{n_params/1e6:.2f}M)")

    # Fused AdamW on CUDA is meaningfully faster.
    fused = device == "cuda"
    optim = torch.optim.AdamW(
        model.parameters(),
        lr=lr_max,
        betas=(0.9, 0.95),
        weight_decay=weight_decay,
        fused=fused,
    )

    # fp16 needs GradScaler; bf16/fp32 do not.
    use_scaler = dtype == torch.float16
    scaler = torch.amp.GradScaler("cuda", enabled=use_scaler) if use_scaler else None

    if compile_model:
        try:
            model = torch.compile(model)
            print("[4/5] train      • torch.compile applied")
        except Exception as e:  # noqa: BLE001
            print(f"[4/5] train      ⚠ torch.compile failed: {e}")

    train_loader = TokenLoader(train_bin, cfg["context_len"], batch_size, device)
    val_loader   = TokenLoader(val_bin,   cfg["context_len"], batch_size, device)

    def autocast_ctx():
        if dtype is None:
            return torch.amp.autocast(device_type=device, enabled=False)
        return torch.amp.autocast(device_type=device, dtype=dtype)

    @torch.no_grad()
    def estimate_loss() -> dict[str, float]:
        model.eval()
        out = {}
        for split, loader in (("train", train_loader), ("val", val_loader)):
            losses = torch.zeros(eval_batches)
            for k in range(eval_batches):
                xb, yb = loader()
                with autocast_ctx():
                    logits = model(xb)
                    loss = F.cross_entropy(logits.flatten(0, 1), yb.flatten())
                losses[k] = loss.item()
            out[split] = losses.mean().item()
        model.train()
        return out

    from tqdm import tqdm
    from collections import deque

    history: list[tuple[int, float, float]] = []
    # Rolling window for per-step tok/s (last 50 steps).
    step_times: deque[float] = deque(maxlen=50)
    tokens_per_step = batch_size * grad_accum * cfg["context_len"]

    t0 = time.time()
    model.train()

    bar = tqdm(
        range(1, max_iters + 1),
        desc="training",
        unit="step",
        dynamic_ncols=True,
        colour="cyan",
    )

    for step in bar:
        step_t0 = time.time()

        # ── Cosine LR with linear warmup ──────────────────────────────────
        lr = _cosine_lr(step - 1, warmup=warmup, max_steps=max_iters, lr_max=lr_max, lr_min=lr_min)
        for pg in optim.param_groups:
            pg["lr"] = lr

        # ── Forward + backward (with optional gradient accumulation) ──────
        optim.zero_grad(set_to_none=True)
        loss_accum = 0.0
        for _ in range(grad_accum):
            xb, yb = train_loader()
            with autocast_ctx():
                logits = model(xb)
                loss = F.cross_entropy(logits.flatten(0, 1), yb.flatten()) / grad_accum
            if scaler is not None:
                scaler.scale(loss).backward()
            else:
                loss.backward()
            loss_accum += loss.item() * grad_accum

        # ── Gradient clipping + optimizer step ────────────────────────────
        if scaler is not None:
            scaler.unscale_(optim)
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0).item()
        if scaler is not None:
            scaler.step(optim)
            scaler.update()
        else:
            optim.step()

        # ── Per-step throughput ───────────────────────────────────────────
        step_dt = time.time() - step_t0
        step_times.append(step_dt)
        avg_dt  = sum(step_times) / len(step_times)
        tps     = tokens_per_step / max(avg_dt, 1e-6)
        eta_sec = avg_dt * (max_iters - step)

        bar.set_postfix(
            loss=f"{loss_accum:.4f}",
            lr=f"{lr:.1e}",
            gnorm=f"{grad_norm:.2f}",
            tok_s=f"{tps:.0f}",
            eta=_fmt_eta(eta_sec),
            refresh=False,
        )

        # ── Periodic eval ─────────────────────────────────────────────────
        if step % eval_every == 0 or step == 1 or step == max_iters:
            m = estimate_loss()
            history.append((step, m["train"], m["val"]))
            elapsed = time.time() - t0
            ppl_train = math.exp(min(m["train"], 20))  # cap to avoid overflow
            ppl_val   = math.exp(min(m["val"],   20))
            bar.write(
                f"{'─'*72}\n"
                f"  step {step:>5d}/{max_iters}"
                f"  lr={lr:.2e}"
                f"  train loss={m['train']:.4f} (ppl={ppl_train:.1f})"
                f"  val loss={m['val']:.4f} (ppl={ppl_val:.1f})\n"
                f"  gnorm={grad_norm:.3f}"
                f"  tok/s={tps:.0f}"
                f"  elapsed={_fmt_eta(elapsed)}"
                f"  ETA={_fmt_eta(eta_sec)}\n"
                f"{'─'*72}"
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    history_path = out_dir / "training_history.json"
    history_path.write_text(json.dumps(
        [{"step": s, "train_loss": t, "val_loss": v} for s, t, v in history], indent=2
    ))

    ckpt_path = out_dir / "checkpoint.pt"
    state = model.state_dict()
    # torch.compile prefixes keys with "_orig_mod." — strip for clean export.
    state = {k.removeprefix("_orig_mod."): v for k, v in state.items()}
    torch.save({"model_state": state, "cfg": cfg}, ckpt_path)
    print(f"[4/5] train      ✓ checkpoint → {ckpt_path}  ({ckpt_path.stat().st_size / 1e6:.1f} MB)")
    return ckpt_path


# ─────────────────────────────────────────────────────────────────────────────
# Stage 8 — HF-style export (safetensors + config.json)
# ─────────────────────────────────────────────────────────────────────────────
def stage_export_safetensors(ckpt_path: Path, hf_dir: Path) -> Path:
    from safetensors.torch import save_file

    hf_dir.mkdir(parents=True, exist_ok=True)
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    cfg, state = ckpt["cfg"], ckpt["model_state"]

    # safetensors requires contiguous tensors that don't share storage.
    state = {k: v.detach().contiguous().clone() for k, v in state.items()}

    weights_path = hf_dir / "model.safetensors"
    save_file(
        state,
        str(weights_path),
        metadata={"format": "pt", "model_type": "mahabharata_gpt"},
    )

    config_path = hf_dir / "config.json"
    config_path.write_text(json.dumps({
        "architectures": ["MahabharataGPT"],
        "model_type": "mahabharata_gpt",
        "vocab_size":            cfg["vocab_size"],
        "n_positions":           cfg["context_len"],
        "n_embd":                cfg["emb_dim"],
        "n_head":                cfg["n_heads"],
        "n_layer":               cfg["n_layers"],
        "attention_dropout":     cfg["drop_rate"],
        "resid_pdrop":           cfg["drop_rate"],
        "embd_pdrop":            cfg["drop_rate"],
        "qkv_bias":              cfg["qkv_bias"],
        "tokenizer_class":       "GPT2Tokenizer",
        "tokenizer":             "gpt2",
        "bos_token":             "<|endoftext|>",
        "eos_token":             "<|endoftext|>",
        "torch_dtype":           "float32",
    }, indent=2))

    # Minimal model card.
    readme = hf_dir / "README.md"
    readme.write_text(
        "---\n"
        "library_name: pytorch\n"
        "license: mit\n"
        "tags:\n"
        "  - gpt\n"
        "  - text-generation\n"
        "  - mahabharata\n"
        "  - from-scratch\n"
        "language:\n"
        "  - en\n"
        "---\n\n"
        "# Mahabharata-GPT\n\n"
        "A small decoder-only LM trained from scratch on the Mahabharata "
        "([tilakd/mahabharata](https://www.kaggle.com/datasets/tilakd/mahabharata) on Kaggle).\n\n"
        "## Usage\n\n"
        "```python\n"
        "from safetensors.torch import load_file\n"
        "from model import GPTModel  # see repo\n"
        "import json, torch, tiktoken\n\n"
        "cfg = json.load(open('config.json'))\n"
        "model_cfg = {\n"
        "    'vocab_size':  cfg['vocab_size'],\n"
        "    'context_len': cfg['n_positions'],\n"
        "    'emb_dim':     cfg['n_embd'],\n"
        "    'n_heads':     cfg['n_head'],\n"
        "    'n_layers':    cfg['n_layer'],\n"
        "    'drop_rate':   cfg['attention_dropout'],\n"
        "    'qkv_bias':    cfg['qkv_bias'],\n"
        "}\n"
        "model = GPTModel(model_cfg)\n"
        "model.load_state_dict(load_file('model.safetensors'))\n"
        "tok = tiktoken.get_encoding('gpt2')\n"
        "```\n\n"
        "## Architecture\n\n"
        "Pre-norm decoder-only transformer with multi-head causal attention, GELU MLP, "
        "and GPT-2 BPE tokenizer.\n"
    )

    # Verify the round-trip loads.
    from safetensors.torch import load_file
    reloaded = load_file(str(weights_path))
    assert reloaded.keys() == state.keys(), "safetensors round-trip key mismatch"
    print(f"[5/5] export     ✓ {weights_path.name}  ({weights_path.stat().st_size / 1e6:.1f} MB)")
    print(f"[5/5] export     ✓ {config_path.name}, {readme.name}")
    print(f"[5/5] export     → upload directory: {hf_dir}")
    return weights_path


# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Mahabharata GPT end-to-end trainer")
    p.add_argument("--data-dir",   type=Path, default=Path("data"))
    p.add_argument("--out-dir",    type=Path, default=Path("checkpoints"))
    p.add_argument("--hf-dir",     type=Path, default=Path("hf_export"))
    p.add_argument("--skip-data",  action="store_true", help="reuse cached data/processed/*.bin")

    # Model
    p.add_argument("--context-len", type=int, default=DEFAULT_MODEL_CFG["context_len"])
    p.add_argument("--emb-dim",     type=int, default=DEFAULT_MODEL_CFG["emb_dim"])
    p.add_argument("--n-heads",     type=int, default=DEFAULT_MODEL_CFG["n_heads"])
    p.add_argument("--n-layers",    type=int, default=DEFAULT_MODEL_CFG["n_layers"])
    p.add_argument("--drop-rate",   type=float, default=DEFAULT_MODEL_CFG["drop_rate"])

    # Training
    p.add_argument("--max-iters",     type=int,   default=2000)
    p.add_argument("--batch-size",    type=int,   default=32)
    p.add_argument("--grad-accum",    type=int,   default=1)
    p.add_argument("--lr-max",        type=float, default=3e-4)
    p.add_argument("--lr-min",        type=float, default=3e-5)
    p.add_argument("--warmup",        type=int,   default=100)
    p.add_argument("--weight-decay",  type=float, default=0.1)
    p.add_argument("--eval-every",    type=int,   default=200)
    p.add_argument("--eval-batches",  type=int,   default=20)
    p.add_argument("--compile",       action="store_true", dest="compile_model")
    p.add_argument("--seed",          type=int,   default=123)
    return p.parse_args()


def main():
    args = parse_args()
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    cfg = dict(DEFAULT_MODEL_CFG)
    cfg.update({
        "context_len": args.context_len,
        "emb_dim":     args.emb_dim,
        "n_heads":     args.n_heads,
        "n_layers":    args.n_layers,
        "drop_rate":   args.drop_rate,
    })

    raw_dir  = args.data_dir / "raw"
    proc_dir = args.data_dir / "processed"

    if not args.skip_data:
        stage_download(raw_dir)
        train_p, val_p = stage_preprocess(raw_dir, proc_dir)
        train_bin, val_bin = stage_tokenize(train_p, val_p, proc_dir)
    else:
        train_bin = proc_dir / "train.bin"
        val_bin   = proc_dir / "val.bin"
        assert train_bin.exists() and val_bin.exists(), "--skip-data set but binaries missing"
        print("[1-3/5] data     ✓ skipped (reusing cached binaries)")

    ckpt_path = stage_train(
        train_bin=train_bin,
        val_bin=val_bin,
        cfg=cfg,
        out_dir=args.out_dir,
        max_iters=args.max_iters,
        batch_size=args.batch_size,
        grad_accum=args.grad_accum,
        lr_max=args.lr_max,
        lr_min=args.lr_min,
        warmup=args.warmup,
        weight_decay=args.weight_decay,
        eval_every=args.eval_every,
        eval_batches=args.eval_batches,
        compile_model=args.compile_model,
    )

    stage_export_safetensors(ckpt_path, args.hf_dir)

    print("\nDone. Upload to Hugging Face:")
    print(f"  huggingface-cli login")
    print(f"  huggingface-cli upload <your-username>/mahabharata-gpt {args.hf_dir} . --repo-type model")
    print("  # or use the helper: python push_to_hub.py <your-username>/mahabharata-gpt")


if __name__ == "__main__":
    main()
