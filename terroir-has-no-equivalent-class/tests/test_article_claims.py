"""Each test pins one claim the article makes. If a test fails, the prose is wrong."""

from terroir_onto import gate, law_tax, terroir, untranslatables
from terroir_onto.graphs import ontology_dir


# ---- "Modelling terroir: the wrong mapping and the right one" -------------

def test_naive_equivalence_makes_potting_mix_a_terroir():
    r = terroir.naive_alignment()
    assert "40 L bag of potting mix" in r.soil_that_became_terroir


def test_naive_equivalence_runs_both_directions():
    r = terroir.naive_alignment()
    assert "Clos de Vougeot" in r.terroir_that_became_soil


def test_defined_class_classifies_by_parts_alone():
    result = {c.place: c.is_terroir for c in terroir.defined_class()}
    assert result == {
        "Clos de Vougeot": True,
        "Norfolk County sugar bush": True,
        "40 L bag of potting mix": False,
        "Hydroponic greenhouse": False,
    }


def test_partial_match_reports_what_is_missing():
    greenhouse = next(c for c in terroir.defined_class() if c.place == "Hydroponic greenhouse")
    assert greenhouse.missing == ["soil profile", "local practice"]


# ---- "Words with no English equivalent" -----------------------------------

ARTICLE_TABLE = {
    "terroir": "borrowed",
    "Schadenfreude": "borrowed",
    "hygge": "borrowed",
    "saudade": "paraphrased",
    "hiraeth": "paraphrased",
    "komorebi": "paraphrased",
    "wabi-sabi": "borrowed",
}


def test_borrow_or_paraphrase_matches_article_table():
    got = {w.word: w.strategy for w in untranslatables.report()}
    assert got == ARTICLE_TABLE


def test_no_untranslatable_has_an_exact_match():
    for w in untranslatables.report():
        assert not any(m.startswith("exactMatch") for m in w.mappings), w.word


def test_salience_gap_has_no_mapping_at_all():
    komorebi = next(w for w in untranslatables.report() if w.word == "komorebi")
    assert komorebi.pattern == "salience gap"
    assert komorebi.mappings == []


# ---- "Law and tax" --------------------------------------------------------

def test_quebec_trust_has_no_owner():
    owners = {t.concept: t.owner for t in law_tax.trusts_and_owners()}
    assert owners["QuebecTrust"] is None
    assert owners["Trust"] == "Trustee"


def test_bijural_concept_carries_four_labels():
    labels = law_tax.bijural_labels()
    assert labels["en-x-commonlaw"] == "real property"
    assert labels["en-x-civillaw"] == "immovable"
    assert len(labels) == 4


def test_tax_class_depends_on_jurisdiction():
    assert law_tax.tax_class("AcmeLLC", "US")[0] == "PassThroughEntity"
    assert law_tax.tax_class("AcmeLLC", "Canada")[0] == "Corporation"


def test_ulc_runs_the_other_direction():
    assert law_tax.tax_class("MapleULC", "Canada")[0] == "Corporation"
    assert law_tax.tax_class("MapleULC", "US")[0] == "PassThroughEntity"


def test_hybrids_detected_and_ordinary_corporation_is_not():
    assert law_tax.hybrid_entities() == ["Acme LLC", "Maple Holdings ULC"]


def test_global_tax_class_is_inconsistent():
    errors = law_tax.flatten_to_global_class()
    assert len(errors) == 2
    assert all("Disjoint classes" in e for e in errors)


# ---- "Why this matters": the mapping gate ---------------------------------

def _verdicts():
    return gate.run_gate(gate.read_proposals(ontology_dir() / "proposals.csv"))


def test_unsigned_strong_mappings_are_blocked():
    for v in _verdicts():
        p = v.proposal
        if p.relation in ("equivalentClass", "exactMatch") and not p.approved_by:
            assert not v.accepted, p


def test_weak_mappings_pass_without_signature():
    for v in _verdicts():
        if v.proposal.relation in ("closeMatch", "broadMatch", "narrowMatch", "relatedMatch"):
            assert v.accepted, v.proposal


def test_signed_strong_mapping_passes():
    signed = [v for v in _verdicts() if v.proposal.approved_by]
    assert signed and all(v.accepted for v in signed)


def test_score_does_not_decide_the_verdict():
    # Same pair, same score, opposite verdicts: the relation decides, not the number.
    pairs = {}
    for v in _verdicts():
        key = (v.proposal.source, v.proposal.target, v.proposal.score)
        pairs.setdefault(key, set()).add(v.accepted)
    assert any(outcomes == {True, False} for outcomes in pairs.values())
