"""Encoders. Production uses only "raw" (elastic net on raw proteins).

Deep encoders (VAE, JEPA) are a research track and not part of this package.
"""
from .raw import RawElasticNet


def get_encoder(name: str):
    if name == "raw":
        return RawElasticNet()
    raise ValueError(f"unknown encoder {name!r}; only 'raw' ships in production")
