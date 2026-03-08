"""Synapse Embeddings — ONNX-based semantic matching engine.

Provides semantic similarity scoring for skill routing using
all-MiniLM-L6-v2 (ONNX export). Gracefully degrades when onnxruntime
or numpy are not installed — all public functions return None.

Usage:
    embedder = get_embedder()  # Returns None if ONNX unavailable
    if embedder:
        score = embedder.similarity("build a REST API", "API design patterns")
"""
import hashlib
import json
import logging
import sys
from pathlib import Path

from synapse.config import (
    ONNX_MODEL_NAME, ONNX_MODEL_REPO, SEMANTIC_THRESHOLD,
    get_cache_path, get_models_path,
)

logger = logging.getLogger("synapse.embeddings")

# ============================================================================
# Availability check
# ============================================================================

HAS_EMBEDDINGS = False
_np = None
_ort = None

try:
    import numpy as _np
    import onnxruntime as _ort
    HAS_EMBEDDINGS = True
except ImportError:
    pass


# ============================================================================
# Model download
# ============================================================================

def _download_model_files(models_dir):
    """Download ONNX model + vocab from HuggingFace if not present.

    Downloads:
        - model.onnx (the sentence-transformer ONNX export)
        - vocab.txt (WordPiece vocabulary)
        - tokenizer_config.json (tokenizer settings)
    """
    import urllib.request

    base_url = f"https://huggingface.co/{ONNX_MODEL_REPO}/resolve/main"
    files = {
        "vocab.txt": f"{base_url}/vocab.txt",
        "tokenizer_config.json": f"{base_url}/tokenizer_config.json",
    }

    # The ONNX model lives in the onnx/ subfolder on HuggingFace
    onnx_url = f"{base_url}/onnx/model.onnx"
    files["model.onnx"] = onnx_url

    models_dir.mkdir(parents=True, exist_ok=True)

    for filename, url in files.items():
        target = models_dir / filename
        if target.exists():
            continue
        print(f"  Downloading {filename}...", file=sys.stderr, end=" ", flush=True)
        try:
            urllib.request.urlretrieve(url, str(target))
            size_mb = target.stat().st_size / (1024 * 1024)
            print(f"({size_mb:.1f} MB)", file=sys.stderr)
        except Exception as e:
            print(f"FAILED: {e}", file=sys.stderr)
            if target.exists():
                target.unlink()
            raise


# ============================================================================
# Embedder class
# ============================================================================

class Embedder:
    """ONNX-based sentence embedder using all-MiniLM-L6-v2."""

    def __init__(self, models_dir=None):
        if not HAS_EMBEDDINGS:
            raise RuntimeError("onnxruntime and numpy required for embeddings")

        self._models_dir = Path(models_dir) if models_dir else get_models_path()
        self._session = None
        self._tokenizer = None
        self._skill_embeddings = None
        self._skill_ids = None

    def _ensure_model(self):
        """Lazy-load the ONNX model, downloading if needed."""
        if self._session is not None:
            return

        model_path = self._models_dir / "model.onnx"
        vocab_path = self._models_dir / "vocab.txt"

        # Download if missing
        if not model_path.exists() or not vocab_path.exists():
            print(f"[synapse] First-time setup: downloading {ONNX_MODEL_NAME}...",
                  file=sys.stderr)
            _download_model_files(self._models_dir)

        # Load tokenizer
        from synapse.tokenizer import WordPieceTokenizer
        self._tokenizer = WordPieceTokenizer(str(vocab_path), max_length=128)

        # Load ONNX session
        opts = _ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 2
        opts.graph_optimization_level = _ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self._session = _ort.InferenceSession(str(model_path), sess_options=opts)

    def encode(self, text):
        """Encode a single text string to a normalized 384-dim vector.

        Returns: np.ndarray of shape (384,)
        """
        self._ensure_model()
        input_ids, attention_mask = self._tokenizer.encode(text)

        # Run ONNX inference
        inputs = {
            "input_ids": _np.array([input_ids], dtype=_np.int64),
            "attention_mask": _np.array([attention_mask], dtype=_np.int64),
            "token_type_ids": _np.zeros((1, len(input_ids)), dtype=_np.int64),
        }
        outputs = self._session.run(None, inputs)

        # Mean pooling over token embeddings (output[0] = last hidden state)
        token_embeddings = outputs[0]  # shape: (1, seq_len, 384)
        mask_expanded = _np.array([attention_mask], dtype=_np.float32)
        mask_expanded = _np.expand_dims(mask_expanded, axis=-1)  # (1, seq_len, 1)

        summed = _np.sum(token_embeddings * mask_expanded, axis=1)  # (1, 384)
        counts = _np.clip(mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)  # (1, 1)
        pooled = summed / counts  # (1, 384)

        # L2 normalize
        norm = _np.linalg.norm(pooled, axis=1, keepdims=True)
        norm = _np.clip(norm, a_min=1e-9, a_max=None)
        normalized = pooled / norm

        return normalized[0]  # (384,)

    def encode_batch(self, texts, batch_size=64):
        """Encode multiple texts. Returns np.ndarray of shape (N, 384)."""
        self._ensure_model()
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            all_ids, all_masks = self._tokenizer.encode_batch(batch_texts)

            inputs = {
                "input_ids": _np.array(all_ids, dtype=_np.int64),
                "attention_mask": _np.array(all_masks, dtype=_np.int64),
                "token_type_ids": _np.zeros_like(_np.array(all_ids, dtype=_np.int64)),
            }
            outputs = self._session.run(None, inputs)

            token_embeddings = outputs[0]
            mask_expanded = _np.array(all_masks, dtype=_np.float32)
            mask_expanded = _np.expand_dims(mask_expanded, axis=-1)

            summed = _np.sum(token_embeddings * mask_expanded, axis=1)
            counts = _np.clip(mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
            pooled = summed / counts

            norms = _np.linalg.norm(pooled, axis=1, keepdims=True)
            norms = _np.clip(norms, a_min=1e-9, a_max=None)
            normalized = pooled / norms

            all_embeddings.append(normalized)

        return _np.vstack(all_embeddings)

    @staticmethod
    def cosine_similarity(a, b):
        """Compute cosine similarity between two vectors.

        Args:
            a: np.ndarray of shape (D,) or (1, D)
            b: np.ndarray of shape (D,) or (N, D)

        Returns: float or np.ndarray of shape (N,)
        """
        a = a.flatten()
        if b.ndim == 1:
            b = b.reshape(1, -1)
        dot = b @ a
        norm_a = _np.linalg.norm(a)
        norm_b = _np.linalg.norm(b, axis=1)
        denom = norm_a * norm_b
        denom = _np.clip(denom, a_min=1e-9, a_max=None)
        sims = dot / denom
        return float(sims[0]) if sims.shape[0] == 1 else sims

    # ========================================================================
    # Skill embedding cache
    # ========================================================================

    def _compute_index_hash(self, skills):
        """Hash skill IDs + descriptions for cache invalidation."""
        content = json.dumps(
            [(s.get("id", ""), s.get("description", "")) for s in skills],
            sort_keys=True,
        )
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def build_skill_cache(self, skills):
        """Compute and cache embeddings for all skills.

        Args:
            skills: list of skill dicts with 'id' and 'description' keys

        Returns: (embeddings_array, skill_ids_list)
        """
        cache_dir = get_cache_path()
        index_hash = self._compute_index_hash(skills)
        embeddings_path = cache_dir / f"skill_embeddings_{index_hash}.npy"
        ids_path = cache_dir / f"skill_ids_{index_hash}.json"

        # Try loading cached
        if embeddings_path.exists() and ids_path.exists():
            try:
                embeddings = _np.load(str(embeddings_path))
                with ids_path.open("r", encoding="utf-8") as f:
                    skill_ids = json.load(f)
                if len(embeddings) == len(skill_ids) == len(skills):
                    self._skill_embeddings = embeddings
                    self._skill_ids = skill_ids
                    return embeddings, skill_ids
            except Exception:
                pass  # Cache corrupted, rebuild

        # Build fresh
        descriptions = []
        skill_ids = []
        for skill in skills:
            sid = skill.get("id") or skill.get("name") or ""
            desc = skill.get("description") or sid
            # Combine ID + description for richer embedding
            text = f"{sid.replace('-', ' ')}: {desc}"
            descriptions.append(text)
            skill_ids.append(sid)

        print(f"[synapse] Building semantic index for {len(skills)} skills...",
              file=sys.stderr, end=" ", flush=True)
        embeddings = self.encode_batch(descriptions)
        print("done.", file=sys.stderr)

        # Save cache
        try:
            _np.save(str(embeddings_path), embeddings)
            with ids_path.open("w", encoding="utf-8") as f:
                json.dump(skill_ids, f)
            # Clean old cache files
            for old_file in cache_dir.glob("skill_embeddings_*.npy"):
                if old_file != embeddings_path:
                    old_file.unlink(missing_ok=True)
            for old_file in cache_dir.glob("skill_ids_*.json"):
                if old_file != ids_path:
                    old_file.unlink(missing_ok=True)
        except Exception as e:
            logger.debug("Failed to save embedding cache: %s", e)

        self._skill_embeddings = embeddings
        self._skill_ids = skill_ids
        return embeddings, skill_ids

    def score_skills_semantic(self, task_text, skills):
        """Score all skills by semantic similarity to the task.

        Returns: dict mapping skill_id → similarity_score (float, 0-1)
        """
        if self._skill_embeddings is None or self._skill_ids is None:
            self.build_skill_cache(skills)

        task_embedding = self.encode(task_text)
        similarities = self.cosine_similarity(task_embedding, self._skill_embeddings)

        scores = {}
        for i, sid in enumerate(self._skill_ids):
            sim = float(similarities[i]) if hasattr(similarities, '__len__') else float(similarities)
            scores[sid] = sim if sim >= SEMANTIC_THRESHOLD else 0.0

        return scores


# ============================================================================
# Module-level singleton
# ============================================================================

_embedder_instance = None


def get_embedder():
    """Get the singleton Embedder instance, or None if ONNX unavailable.

    Returns None (never raises) if onnxruntime/numpy not installed.
    """
    global _embedder_instance
    if not HAS_EMBEDDINGS:
        return None
    if _embedder_instance is None:
        try:
            _embedder_instance = Embedder()
        except Exception as e:
            logger.warning("Failed to initialize embedder: %s", e)
            return None
    return _embedder_instance
