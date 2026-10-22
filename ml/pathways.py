"""Group RPPA proteins into pathway blocks. The JEPA hides whole blocks and
predicts their representation, so it learns pathway-level structure instead of
memorising single noisy proteins.

Groupings are a pragmatic, hand-curated approximation of standard RPPA pathway
annotations (e.g. Akbani et al., Nat Commun 2014). Swap in Reactome later if wanted.
"""
from __future__ import annotations

import numpy as np

BLOCKS: dict[str, set[str]] = {
    "hormone_lineage": {"ESR1", "PGR", "AR", "GATA3", "INPP4B", "XBP1", "NKX2-1"},
    "rtk": {"EGFR", "ERBB2", "ERBB3", "NRG1", "KIT", "MET", "KDR", "ERRFI1", "IGFBP2",
            "IRS1", "GAB2", "SHC1", "SRC", "ACVRL1", "PECAM1"},
    "pi3k_mtor": {"AKT1", "AKT2", "AKT3", "PIK3CA", "PIK3R1", "PIK3R2", "PTEN", "MTOR",
                  "RPTOR", "RICTOR", "TSC1", "TSC2", "AKT1S1", "RPS6", "RPS6KB1",
                  "EIF4EBP1", "EIF4E", "EIF4G1", "PDK1", "GSK3A", "GSK3B", "FOXO3",
                  "PRKAA1", "STK11", "EEF2", "EEF2K", "PDCD4"},
    "mapk": {"MAPK1", "MAPK3", "MAP2K1", "RAF1", "ARAF", "BRAF", "NRAS", "MAPK8", "MAPK9",
             "MAPK14", "JUN", "RPS6KA1", "PEA15", "YBX1", "DIRAS3", "PREX1", "PRKCA",
             "PRKCB", "PRKCD", "ETS1"},
    "dna_repair": {"ATM", "CHEK1", "CHEK2", "TP53BP1", "XRCC1", "XRCC5", "MRE11A", "RAD50",
                   "RAD51", "BRCA2", "PARP1", "ERCC1", "MSH2", "MSH6", "TP53", "BAP1",
                   "ARID1A"},
    "cell_cycle": {"CDK1", "CCNB1", "CCND1", "CCNE1", "CCNE2", "CDKN1A", "CDKN1B", "RB1",
                   "PCNA", "FOXM1", "STMN1", "MYC"},
    "apoptosis": {"BAK1", "BAX", "BCL2", "BCL2L1", "BCL2L11", "BID", "BAD", "BIRC2",
                  "CASP3", "CASP7", "CASP9", "DIABLO", "BECN1", "SQSTM1"},
    "adhesion_emt": {"CDH1", "CDH2", "CDH3", "CTNNB1", "CTNNA1", "CLDN7", "FN1", "COL6A1",
                     "SERPINE1", "PXN", "CAV1", "ITGA2", "TGM2", "MYH11", "MYH9", "ANXA1",
                     "ANXA7", "RAB11A", "RAB11B", "RAB25", "TUBA1B"},
    "developmental": {"YAP1", "WWTR1", "NF2", "DVL3", "NOTCH1", "SMAD1", "SMAD3", "SMAD4"},
    "metabolism_stress": {"ACACA", "ACACB", "FASN", "SCD1", "G6PD", "GAPDH", "ASNS",
                          "TIGAR", "PARK7", "PRDX1", "HSPA1A", "NDRG1", "VHL", "TFRC"},
    "immune": {"LCK", "SYK", "MS4A1", "STAT3", "STAT5A", "NFKB1"},
}
OTHER = "other"


def gene_symbols(protein: str) -> list[str]:
    """'AKT1 AKT2 AKT3|Akt_pS473' -> ['AKT1', 'AKT2', 'AKT3']"""
    return protein.split("|")[0].split()


def assign_blocks(proteins: list[str]) -> tuple[np.ndarray, list[str]]:
    """Return an integer block id per protein and the list of block names."""
    names = list(BLOCKS) + [OTHER]
    ids = []
    for p in proteins:
        genes = set(gene_symbols(p))
        hit = next((i for i, (_, members) in enumerate(BLOCKS.items()) if genes & members),
                   len(names) - 1)
        ids.append(hit)
    return np.array(ids), names


if __name__ == "__main__":
    import data
    ds = data.build_dataset()
    ids, names = assign_blocks(ds.proteins)
    for i, n in enumerate(names):
        members = [ds.proteins[j].split("|")[1] for j in np.where(ids == i)[0]]
        print(f"{n:18s} {len(members):3d}  {', '.join(members[:8])}{' ...' if len(members) > 8 else ''}")
