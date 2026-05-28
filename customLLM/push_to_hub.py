"""Push the safetensors export to the Hugging Face Hub.

Prereqs:
    pip install huggingface_hub
    huggingface-cli login          # one-time, stores token in ~/.cache/huggingface

Usage:
    python push_to_hub.py <username>/mahabharata-gpt
    python push_to_hub.py <username>/mahabharata-gpt --private
    python push_to_hub.py <username>/mahabharata-gpt --dir hf_export
"""
from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import HfApi, create_repo


REQUIRED = ("model.safetensors", "config.json", "README.md")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("repo_id", help="repo identifier, e.g. 'username/mahabharata-gpt'")
    p.add_argument("--dir",   type=Path, default=Path("hf_export"),
                   help="directory containing model.safetensors + config.json + README.md")
    p.add_argument("--private",      action="store_true")
    p.add_argument("--commit-msg",   default="Upload Mahabharata-GPT")
    args = p.parse_args()

    missing = [f for f in REQUIRED if not (args.dir / f).exists()]
    if missing:
        raise SystemExit(f"missing required files in {args.dir}: {missing}\n"
                         f"Run train_e2e.py first.")

    print(f"creating repo {args.repo_id}  (private={args.private})")
    create_repo(args.repo_id, repo_type="model", private=args.private, exist_ok=True)

    print(f"uploading folder {args.dir} → {args.repo_id}")
    HfApi().upload_folder(
        repo_id=args.repo_id,
        repo_type="model",
        folder_path=str(args.dir),
        commit_message=args.commit_msg,
    )
    print(f"✓ https://huggingface.co/{args.repo_id}")


if __name__ == "__main__":
    main()
