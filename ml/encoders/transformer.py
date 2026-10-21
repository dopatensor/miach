"""Pathway-masked transformer, trained two ways on identical inputs and masks:

  mode="jepa"  : predict the *embedding* of the hidden pathways, as produced by a
                 slowly updated (EMA) target encoder. Noise it can't predict is free to ignore.
  mode="recon" : predict the hidden *raw values*. This is the control that isolates whether
                 the JEPA objective itself helps.

Each protein is one token: a learned protein-identity embedding plus an encoding of its value.
Unmeasured proteins are simply left out of attention, so missing data needs no imputation.
"""
from __future__ import annotations

import copy
import math

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from evaluate import collapse_stats
from pathways import assign_blocks
from .base import Encoder


def _t(x, dtype=torch.float32):
    return torch.as_tensor(x, dtype=dtype)


def _layer(d, heads, ff, dropout):
    return nn.TransformerEncoderLayer(d, heads, ff, dropout, batch_first=True,
                                      norm_first=True, activation="gelu")


class _Backbone(nn.Module):
    """Context / target encoder: tokens for all proteins, attention only over `visible` ones."""

    def __init__(self, P, d, layers, heads, ff, dropout):
        super().__init__()
        self.prot = nn.Embedding(P, d)
        self.val = nn.Sequential(nn.Linear(1, d), nn.GELU(), nn.Linear(d, d))
        self.tf = nn.TransformerEncoder(_layer(d, heads, ff, dropout), layers,
                                        enable_nested_tensor=False)
        self.norm = nn.LayerNorm(d)
        self.register_buffer("pos", torch.arange(P), persistent=False)

    def forward(self, x, visible):
        tok = self.prot(self.pos)[None] + self.val(x.unsqueeze(-1))
        h = self.norm(self.tf(tok, src_key_padding_mask=~visible))
        return torch.where(visible[..., None], h, torch.zeros_like(h))

    @staticmethod
    def pool(h, visible):
        v = visible.float()[..., None]
        return (h * v).sum(1) / v.sum(1).clamp(min=1)


class _Predictor(nn.Module):
    """Sees context outputs at visible positions plus a query token (mask token + protein id)
    at each hidden position, and outputs a prediction at every position."""

    def __init__(self, P, d, layers, heads, ff, dropout, out_dim):
        super().__init__()
        self.inp = nn.Linear(d, d)
        self.prot = nn.Embedding(P, d)
        self.mask_tok = nn.Parameter(torch.zeros(d))
        nn.init.normal_(self.mask_tok, std=0.02)
        self.tf = nn.TransformerEncoder(_layer(d, heads, ff, dropout), layers,
                                        enable_nested_tensor=False)
        self.norm = nn.LayerNorm(d)
        self.out = nn.Linear(d, out_dim)
        self.register_buffer("pos", torch.arange(P), persistent=False)

    def forward(self, ctx_h, visible, hidden):
        pe = self.prot(self.pos)[None]
        query = (pe + self.mask_tok).expand(ctx_h.shape[0], -1, -1)
        h = torch.where(visible[..., None], self.inp(ctx_h) + pe, query)
        h = self.tf(h, src_key_padding_mask=~(visible | hidden))
        return self.out(self.norm(h))


class TransformerSSLEncoder(Encoder):
    name = "jepa"

    def __init__(self, mode="jepa", **cfg):
        super().__init__(**cfg)
        assert mode in ("jepa", "recon")
        self.mode = self.name = mode

    def _defaults(self):
        c = dict(d=128, layers=4, heads=4, ff=256, dropout=0.1,
                 # target_norm: "layer" (I-JEPA style, default) or "batch" (standardise each
                 # protein across the batch). In the quick test "batch" raised patient spread
                 # but fell into ~6 effective dimensions and probed worse, so "layer" is default.
                 pred_layers=2, n_mask_blocks=3, target="block", target_norm="layer",
                 epochs=30, batch=128, lr=5e-4, weight_decay=0.05, warmup_frac=0.05,
                 ema_start=0.996, ema_end=1.0, threads=None, device="auto")
        c.update(self.cfg)
        return c

    @staticmethod
    def _pick_device(name):
        if name != "auto":
            return torch.device(name)
        if torch.cuda.is_available():
            return torch.device("cuda")
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    # ------------------------------------------------------------- masking
    def _sample_mask(self, obs, gen):
        """Hide `n_mask_blocks` whole pathway blocks per patient (among blocks with data)."""
        B = obs.shape[0]
        has = (obs.float() @ self.block_onehot) > 0                     # (B, K)
        scores = torch.rand(B, self.K, generator=gen).to(self.dev).masked_fill(~has, -1.0)
        k = min(self.c["n_mask_blocks"], self.K - 1)
        top = scores.topk(k, dim=1).indices
        block_mask = torch.zeros(B, self.K, dtype=torch.bool, device=self.dev).scatter_(1, top, True) & has
        hidden = block_mask[:, self.block_ids] & obs
        visible = obs & ~hidden
        return visible, hidden

    def _block_pool(self, H, hidden):
        """Mean over the hidden tokens of each block -> (B, K, d) and a validity mask."""
        W = hidden.float()[..., None] * self.block_onehot[None]          # (B, P, K)
        cnt = W.sum(1)                                                   # (B, K)
        pooled = torch.einsum("bpk,bpd->bkd", W, H) / cnt.clamp(min=1)[..., None]
        return pooled, cnt > 0

    def _loss(self, x, obs, gen):
        visible, hidden = self._sample_mask(obs, gen)
        pred = self.pred(self.ctx(x, visible), visible, hidden)
        if self.mode == "recon":
            m = hidden.float()
            return (((pred.squeeze(-1) - x) ** 2) * m).sum() / m.sum().clamp(min=1)
        with torch.no_grad():
            tgt = self.tgt(x, obs)
            if self.c["target_norm"] == "batch":
                # Standardise each (protein, dim) across the patients in the batch. Target tokens
                # contain a protein-identity component that is identical for every patient; without
                # this, the predictor can score well just by knowing *which* proteins are hidden.
                m = obs.float()[..., None]
                cnt = m.sum(0).clamp(min=1)
                mu = (tgt * m).sum(0) / cnt
                var = (((tgt - mu) ** 2) * m).sum(0) / cnt
                tgt = (tgt - mu) / torch.sqrt(var + 1e-5)
            else:
                tgt = F.layer_norm(tgt, (self.c["d"],))
        if self.c["target"] == "token":
            m = hidden.float()[..., None]
            return (((pred - tgt) ** 2) * m).sum() / (m.sum() * self.c["d"]).clamp(min=1)
        p_blk, valid = self._block_pool(pred, hidden)
        t_blk, _ = self._block_pool(tgt, hidden)
        return ((p_blk - t_blk) ** 2).mean(-1)[valid].mean()

    # ------------------------------------------------------------- training
    def fit(self, ds, labelled_idx=None, seed=0):
        c = self.c = self._defaults()
        if c["threads"]:
            torch.set_num_threads(c["threads"])
        torch.manual_seed(seed)
        rng = np.random.default_rng(seed)
        gen = torch.Generator().manual_seed(seed)
        self.dev = dev = self._pick_device(c["device"])
        print(f"    [{self.mode}] training on {dev}", flush=True)

        ids, names = assign_blocks(ds.proteins)
        self.K = len(names)
        self.block_ids = torch.as_tensor(ids, device=dev)
        self.block_onehot = F.one_hot(self.block_ids, self.K).float()   # (P, K)

        X = ds.X_pre
        obs_all, x_all = _t(~np.isnan(X), torch.bool), _t(np.nan_to_num(X))
        P = X.shape[1]
        perm = rng.permutation(len(X))
        n_ho = max(1, int(0.05 * len(X)))
        ho, tr = perm[:n_ho], perm[n_ho:]

        self.ctx = _Backbone(P, c["d"], c["layers"], c["heads"], c["ff"], c["dropout"]).to(dev)
        out_dim = c["d"] if self.mode == "jepa" else 1
        self.pred = _Predictor(P, c["d"], c["pred_layers"], c["heads"], c["ff"], c["dropout"],
                               out_dim).to(dev)
        if self.mode == "jepa":
            self.tgt = copy.deepcopy(self.ctx).eval()
            for p in self.tgt.parameters():
                p.requires_grad_(False)

        params = list(self.ctx.parameters()) + list(self.pred.parameters())
        opt = torch.optim.AdamW(params, lr=c["lr"], weight_decay=c["weight_decay"])
        steps_per_epoch = max(1, len(tr) // c["batch"])
        total = steps_per_epoch * c["epochs"]
        warm = max(1, int(c["warmup_frac"] * total))
        sched = torch.optim.lr_scheduler.LambdaLR(
            opt, lambda s: (s + 1) / warm if s < warm
            else 0.5 * (1 + math.cos(math.pi * (s - warm) / max(1, total - warm))))

        step = 0
        for ep in range(c["epochs"]):
            self.ctx.train(); self.pred.train()
            losses = []
            for b in np.array_split(rng.permutation(tr), steps_per_epoch):
                loss = self._loss(x_all[b].to(dev), obs_all[b].to(dev), gen)
                opt.zero_grad(); loss.backward()
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                opt.step(); sched.step(); step += 1
                losses.append(float(loss.detach()))
                if self.mode == "jepa":
                    m = c["ema_start"] + (c["ema_end"] - c["ema_start"]) * step / total
                    with torch.no_grad():
                        for pt, pc in zip(self.tgt.parameters(), self.ctx.parameters()):
                            pt.mul_(m).add_(pc.detach(), alpha=1 - m)
            # monitor: holdout loss with a fixed mask, and collapse of the patient embeddings
            self.ctx.eval(); self.pred.eval()
            with torch.no_grad():
                ho_loss = float(self._loss(x_all[ho].to(dev), obs_all[ho].to(dev),
                                           torch.Generator().manual_seed(0)))
            stats = collapse_stats(self.embed(X[ho]))
            self.log.append({"epoch": ep, "train_loss": float(np.mean(losses)),
                             "holdout_loss": ho_loss, **stats})
            print(f"    [{self.mode}] epoch {ep + 1:3d}/{c['epochs']}  train {np.mean(losses):.4f}  "
                  f"holdout {ho_loss:.4f}  rel_std {stats['rel_std']:.3f}  "
                  f"eff_rank {stats['eff_rank']:.1f}{'  COLLAPSED' if stats['collapsed'] else ''}",
                  flush=True)
        return self

    def embed(self, X, batch=512):
        self.ctx.eval()
        out = []
        with torch.no_grad():
            for i in range(0, len(X), batch):
                xb = X[i:i + batch]
                obs = _t(~np.isnan(xb), torch.bool).to(self.dev)
                x = _t(np.nan_to_num(xb)).to(self.dev)
                out.append(_Backbone.pool(self.ctx(x, obs), obs).cpu().numpy())
        return np.concatenate(out)
