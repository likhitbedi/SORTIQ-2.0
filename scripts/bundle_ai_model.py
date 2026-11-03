"""Download FastEmbed's ONNX model on the Windows BUILD runner, then ship a portable copy."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

MODEL = "BAAI/bge-small-en-v1.5"


def bundle(output: Path) -> None:
    from fastembed import TextEmbedding

    output = output.resolve()
    if output.exists():
        shutil.rmtree(output)
    temp_cache = output.parent / "sortiq-ai-model-cache"
    temp_cache.mkdir(parents=True, exist_ok=True)
    embedding = TextEmbedding(model_name=MODEL, cache_dir=str(temp_cache), local_files_only=False)
    vectors = list(embedding.embed(["Check that the AI model loads before bundling."]))
    if len(vectors) != 1 or len(vectors[0]) != 384:
        raise RuntimeError("Downloaded model failed the embedding test")
    # Resolve Hugging Face cache symlinks by physically copying model files.
    source = Path(embedding.model._model_dir).resolve()
    if not source.is_dir():
        raise RuntimeError(f"No downloaded FastEmbed files found: {source}")
    shutil.copytree(source, output, symlinks=False)
    required = output / embedding.model.model_description.model_file
    if not required.is_file():
        raise RuntimeError(f"Missing bundled ONNX model file: {required}")
    size = sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
    if size < 40_000_000:
        raise RuntimeError(f"Bundled model too small: {size} bytes")
    (output / "sortiq-model.json").write_text(
        json.dumps({
            "model": MODEL, "source": "https://huggingface.co/BAAI/bge-small-en-v1.5",
            "license": "MIT", "embedding_dimensions": 384,
            "model_file": str(embedding.model.model_description.model_file).replace("\\", "/"),
            "runtime_downloads": False
        }, indent=2), encoding="utf-8"
    )
    shutil.rmtree(temp_cache, ignore_errors=True)
    print(f"Bundled {MODEL} model and tokenizer: {size:,} bytes")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    bundle(ap.parse_args().output)
