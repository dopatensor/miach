"""Shared settings for the MVP comparison."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
CACHE_DIR = ROOT / "data" / "cache"
RESULTS_DIR = ROOT / "results"

DATAHUB = "https://media.githubusercontent.com/media/cBioPortal/datahub/master/public"
TARGET_STUDY = "brca"

# TCGA PanCancer Atlas studies with RPPA protein data (laml has none).
PANCAN_STUDIES = [
    "acc", "blca", "brca", "cesc", "chol", "coadread", "dlbc", "esca", "gbm",
    "hnsc", "kich", "kirc", "kirp", "lgg", "lihc", "luad", "lusc", "meso", "ov",
    "paad", "pcpg", "prad", "sarc", "skcm", "stad", "tgct", "thca", "thym",
    "ucec", "ucs", "uvm",
]

SPLIT_SEED = 2026          # fixed: the locked test set never changes
TEST_FRACTION = 0.20
VAL_FRACTION = 0.15        # carved from the BRCA training set, used for early stopping

# PFS is the endpoint recommended for TCGA breast cancer (Liu et al., Cell 2018);
# overall survival has too few events with TCGA follow-up.
SURVIVAL_STATUS_COL = "PFS_STATUS"
SURVIVAL_TIME_COL = "PFS_MONTHS"

LABEL_FRACTIONS = [0.10, 0.25, 1.00]
PROBE_SEEDS = [0, 1, 2, 3, 4]
N_BOOTSTRAP = 1000

# Known breast cancer markers used for the sanity check on marker ranking.
KNOWN_MARKERS = ["ESR1", "PGR", "ERBB2", "GATA3", "AR", "INPP4B"]

EMBED_DIM = 32  # latent size for PCA and the VAEs
