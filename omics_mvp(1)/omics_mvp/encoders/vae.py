"""Standard baseline from the deck: a VAE, optionally with jointly trained
subtype and survival heads. Missing proteins are excluded from the reconstruction loss.
"""
from __future__ import annotations

import copy

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

import config as C
from .base import Encoder


def _t(x):
    return torch.as_tensor(x, dtype=torch.float32)


class _VAE(nn.Module):
    def __init__(self, p: int, z: int, hidden=(256, 128), n_classes: int = 0, dropout=0.1):
        super().__init__()
        layers, d = [], p
        for h in hidden:
            layers += [nn.Linear(d, h), nn.LayerNorm(h), nn.GELU(), nn.Dropout(dropout)]
            d = h
        self.enc = nn.Sequential(*layers)
        self.mu, self.logvar = nn.Linear(d, z), nn.Linear(d, z)
        layers, d = [], z
        for h in reversed(hidden):
            layers += [nn.Linear(d, h), nn.LayerNorm(h), nn.GELU()]
            d = h
        layers.append(nn.Linear(d, p))
        self.dec = nn.Sequential(*layers)
        self.cls = nn.Linear(z, n_classes) if n_classes else None
        self.surv = nn.Linear(z, 1)

    def forward(self, x):
        h = self.enc(x)
        mu, lv = self.mu(h), self.logvar(h).clamp(-8, 8)
        z = mu + torch.randn_like(mu) * torch.exp(0.5 * lv) if self.training else mu
        return self.dec(z), mu, lv


def _elbo_terms(model, x, obs):
    xhat, mu, lv = model(x)
    recon = (((xhat - x) ** 2) * obs).sum(1).mean()
    kl = (-0.5 * (1 + lv - mu ** 2 - lv.exp())).sum(1).mean()
    return recon, kl, mu


def cox_loss(risk, time, event):
    """Negative Cox partial log-likelihood (Breslow approximation for ties)."""
    order = torch.argsort(time, descending=True)
    r, e = risk[order], event[order]
    return -((r - torch.logcumsumexp(r, 0)) * e).sum() / e.sum().clamp(min=1)


class VAEEncoder(Encoder):
    """Unsupervised VAE pretrained on the pan-cancer pool. Embedding = posterior mean."""
    name = "vae"

    def _defaults(self):
        c = dict(dim=C.EMBED_DIM, epochs=100, batch=256, lr=1e-3, beta=1.0, warmup=20,
                 patience=10, threads=None)
        c.update(self.cfg)
        return c

    def _pretrain(self, ds, seed):
        c = self._defaults()
        if c["threads"]:
            torch.set_num_threads(c["threads"])
        torch.manual_seed(seed)
        rng = np.random.default_rng(seed)
        X = ds.X_pre
        obs, x = ~np.isnan(X), np.nan_to_num(X)
        perm = rng.permutation(len(X))
        n_ho = max(1, int(0.1 * len(X)))
        ho, tr = perm[:n_ho], perm[n_ho:]
        model = _VAE(X.shape[1], c["dim"])
        opt = torch.optim.Adam(model.parameters(), lr=c["lr"], weight_decay=1e-5)
        xt, ot = _t(x), _t(obs)
        best, best_state, bad = np.inf, None, 0
        for ep in range(c["epochs"]):
            beta = c["beta"] * min(1.0, (ep + 1) / c["warmup"])
            model.train()
            for b in np.array_split(rng.permutation(tr), max(1, len(tr) // c["batch"])):
                recon, kl, _ = _elbo_terms(model, xt[b], ot[b])
                loss = recon + beta * kl
                opt.zero_grad(); loss.backward(); opt.step()
            model.eval()
            with torch.no_grad():
                recon, kl, _ = _elbo_terms(model, xt[ho], ot[ho])
                ho_loss = float(recon + c["beta"] * kl)
            self.log.append({"stage": "pretrain", "epoch": ep, "holdout_loss": ho_loss,
                             "recon": float(recon), "kl": float(kl)})
            if ho_loss < best - 1e-3:
                best, best_state, bad = ho_loss, copy.deepcopy(model.state_dict()), 0
            else:
                bad += 1
                if bad >= c["patience"]:
                    break
        model.load_state_dict(best_state)
        return model

    def fit(self, ds, labelled_idx=None, seed=0):
        self.model = self._pretrain(ds, seed)
        return self

    def embed(self, X):
        self.model.eval()
        with torch.no_grad():
            _, mu, _ = self.model(_t(np.nan_to_num(X)))
        return mu.numpy()


class VAEJointEncoder(VAEEncoder):
    """The deck's 'standard base': pan-cancer pretraining, then fine-tuning on breast cancer
    with reconstruction + KL + subtype cross-entropy + Cox survival loss.

    Only the labelled patients passed in `labelled_idx` contribute to the supervised losses.
    Early stopping uses the validation set's label-free ELBO, so no extra labels leak in.
    """
    name = "vae_joint"
    supervised = True

    def _defaults(self):
        c = super()._defaults()
        c.setdefault("ft_epochs", 300)
        c.setdefault("ft_lr", 3e-4)
        c.setdefault("w_cls", 20.0)   # supervised terms are per-patient means; ELBO is a sum over
        c.setdefault("w_surv", 20.0)  # ~200 proteins, so they need a larger weight to matter
        return c

    def fit(self, ds, labelled_idx=None, seed=0):
        c = self._defaults()
        if not hasattr(self, "_pretrained"):  # pretrain once, reuse for every fraction/seed
            self._pretrained = self._pretrain(ds, seed=0).state_dict()
        torch.manual_seed(seed)
        classes = list(ds.classes)
        model = _VAE(ds.X_pre.shape[1], c["dim"], n_classes=len(classes))
        model.load_state_dict(self._pretrained, strict=False)

        tr = ds.train
        x, obs = _t(np.nan_to_num(tr.X)), _t(~np.isnan(tr.X))
        lab = np.zeros(len(tr.X), dtype=bool)
        if labelled_idx is not None:
            lab[labelled_idx] = True
        y = np.array([classes.index(s) if (s is not None and lab[i]) else -1
                      for i, s in enumerate(tr.subtype)])
        surv_ok = lab & np.isfinite(tr.time) & np.isfinite(tr.event)
        counts = np.bincount(y[y >= 0], minlength=len(classes)).astype(float)
        cw = _t(np.where(counts > 0, counts.sum() / (len(classes) * np.maximum(counts, 1)), 0.0))
        yt = torch.as_tensor(y)
        tt, et = _t(np.nan_to_num(tr.time)), _t(np.nan_to_num(tr.event))
        st = torch.as_tensor(surv_ok)

        xv, ov = _t(np.nan_to_num(ds.val.X)), _t(~np.isnan(ds.val.X))
        opt = torch.optim.Adam(model.parameters(), lr=c["ft_lr"], weight_decay=1e-4)
        best, best_state, bad = np.inf, copy.deepcopy(model.state_dict()), 0
        for ep in range(c["ft_epochs"]):
            model.train()
            recon, kl, mu = _elbo_terms(model, x, obs)
            loss = recon + c["beta"] * kl
            if (yt >= 0).any():
                loss = loss + c["w_cls"] * F.cross_entropy(model.cls(mu[yt >= 0]), yt[yt >= 0], weight=cw)
            if st.sum() > 1:
                loss = loss + c["w_surv"] * cox_loss(model.surv(mu[st]).squeeze(-1), tt[st], et[st])
            opt.zero_grad(); loss.backward(); opt.step()
            model.eval()
            with torch.no_grad():
                r, k, _ = _elbo_terms(model, xv, ov)
                v = float(r + c["beta"] * k)
            if v < best - 1e-3:
                best, best_state, bad = v, copy.deepcopy(model.state_dict()), 0
            else:
                bad += 1
                if bad >= 30:
                    break
        self.log.append({"stage": "finetune", "seed": seed, "n_labelled": int(lab.sum()),
                         "epochs": ep + 1, "val_elbo": best})
        model.load_state_dict(best_state)
        self.model = model
        return self
