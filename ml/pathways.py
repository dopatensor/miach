"""Protein -> pathway block, following the TCGA RPPA pathway scores
(Akbani et al., Nat Commun 2014). Each protein gets one block; proteins not in
those pathway definitions are "Other"."""

BLOCKS: dict[str, list[str]] = {
    "Hormone receptor": ["ER-alpha", "ER-alpha_pS118", "PR", "AR"],
    "Hormone signaling": ["GATA3", "INPP4B", "Bcl-2"],
    "RTK": ["HER2", "HER2_pY1248", "HER3", "HER3_pY1298", "EGFR", "EGFR_pY1068", "EGFR_pY1173",
            "Shc_pY317", "Src_pY416", "Src_pY527", "c-Met_pY1235", "c-Kit", "VEGFR2"],
    "PI3K/AKT": ["Akt_pS473", "Akt_pT308", "GSK3-alpha-beta_pS21_S9", "GSK3_pS9", "PRAS40_pT246",
                 "Tuberin_pT1462", "p27", "PTEN", "PI3K-p110-alpha", "PI3K-p85", "PDK1_pS241"],
    "TSC/mTOR": ["4E-BP1_pS65", "4E-BP1_pT37T46", "4E-BP1_pT70", "mTOR_pS2448", "p70S6K_pT389",
                 "S6_pS235_S236", "S6_pS240_S244"],
    "RAS/MAPK": ["A-Raf_pS299", "C-Raf_pS338", "JNK_pT183_Y185", "MAPK_pT202_Y204",
                 "MEK1_pS217_S221", "p38_pT180_Y182", "p90RSK_pT359_S363", "YB-1_pS102"],
    "Cell cycle": ["CDK1", "Cyclin_B1", "Cyclin_E1", "Cyclin_E2", "p27_pT157", "p27_pT198", "PCNA",
                   "FoxM1", "Cyclin_D1", "Rb_pS807_S811", "p21"],
    "DNA damage": ["53BP1", "BRCA2", "ATM", "Chk1_pS345", "Chk2_pT68", "Ku80", "Mre11", "p53",
                   "Rad50", "Rad51", "XRCC1", "MSH2", "MSH6", "ERCC1", "PARP1"],
    "Apoptosis": ["Bak", "Bax", "Bid", "Bim", "Caspase-7_cleavedD198", "Bad_pS112", "Bcl-xL", "cIAP",
                  "Caspase-3", "Caspase-9", "Smac"],
    "EMT": ["Fibronectin", "N-Cadherin", "Collagen_VI", "Claudin-7", "E-Cadherin", "beta-Catenin",
            "PAI-1"],
    "Breast reactive": ["Caveolin-1", "MYH11", "Rab11", "GAPDH", "RBM15"],
}

_LOOKUP = {p: block for block, ps in BLOCKS.items() for p in ps}


def split_id(protein_id: str) -> tuple[str, str]:
    """'ESR1|ER-alpha' -> ('ESR1', 'ER-alpha')."""
    gene, _, name = protein_id.partition("|")
    return gene.strip(), name.strip()


def block_of(protein_id: str) -> str:
    return _LOOKUP.get(split_id(protein_id)[1], "Other")
