from app.core.normalization.disease_normalizer import MultiSourceDiseaseNormalizer
from app.core.normalization.gene_normalizer import HGNCGeneNormalizer


def test_gene_alias_normalization_snca() -> None:
    normalizer = HGNCGeneNormalizer("data/standards/hgnc/hgnc_complete_set.json")
    assert normalizer.normalize("alpha-synuclein").normalized_label == "SNCA"
    assert normalizer.normalize("α-synuclein").normalized_label == "SNCA"


def test_gene_alias_normalization_park7_and_pink1() -> None:
    normalizer = HGNCGeneNormalizer("data/standards/hgnc/hgnc_complete_set.json")
    assert normalizer.normalize("DJ-1").normalized_label == "PARK7"
    assert normalizer.normalize("PINK-1").normalized_label == "PINK1"


def test_disease_normalization_pd() -> None:
    normalizer = MultiSourceDiseaseNormalizer(
        "data/standards/mondo/mondo_snapshot.json",
        "data/standards/mesh/mesh_snapshot.json",
        "data/standards/orphanet/orphanet_snapshot.json",
    )
    result = normalizer.normalize("Parkinson disease")
    assert result.ids["mondo"] == "MONDO:0005180"
    assert result.ids["mesh"] == "D010300"
    assert result.ids["orphanet"] == "ORPHA:282"


def test_fuzzy_conflict_not_hard_resolve() -> None:
    normalizer = MultiSourceDiseaseNormalizer(
        "data/standards/mondo/mondo_snapshot.json",
        "data/standards/mesh/mesh_snapshot.json",
        "data/standards/orphanet/orphanet_snapshot.json",
    )
    result = normalizer.normalize("Parkinson dis")
    assert "fuzzy_only" in result.qa_flags or "unresolved" in result.qa_flags
