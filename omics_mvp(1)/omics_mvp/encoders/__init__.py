"""Encoder registry. PyTorch is imported lazily so the classic baselines run without it."""
from __future__ import annotations

from .base import Encoder

ALL = ["raw", "pca", "vae", "vae_joint", "recon", "jepa"]
LABELS = {
    "raw": "Elastic net (raw proteins)",
    "pca": "PCA",
    "vae": "VAE (pan-cancer pretrained)",
    "vae_joint": "VAE + subtype/survival heads (deck baseline)",
    "recon": "Transformer, masked-value reconstruction (control)",
    "jepa": "Pathway JEPA",
}


def get_encoder(name: str, **cfg) -> Encoder:
    if name == "raw":
        from .classic import RawEncoder
        return RawEncoder(**cfg)
    if name == "pca":
        from .classic import PCAEncoder
        return PCAEncoder(**cfg)
    if name == "vae":
        from .vae import VAEEncoder
        return VAEEncoder(**cfg)
    if name == "vae_joint":
        from .vae import VAEJointEncoder
        return VAEJointEncoder(**cfg)
    if name in ("jepa", "recon"):
        from .transformer import TransformerSSLEncoder
        return TransformerSSLEncoder(mode=name, **cfg)
    raise ValueError(f"unknown encoder {name!r}; choose from {ALL}")
