"""Pipeline settings. One place for paths, seeds and split sizes."""
from pathlib import Path

DATAHUB = "https://media.githubusercontent.com/media/cBioPortal/datahub/master/public"
STUDY = "brca_tcga_pan_can_atlas_2018"
FILES = ["data_rppa.txt", "data_clinical_patient.txt"]
CACHE_DIR = Path(__file__).resolve().parent / ".cache"

SEED = 0
N_TEST = 176
N_VAL = 105
CLASSES = ["LumA", "LumB", "Basal", "Her2", "Normal"]
