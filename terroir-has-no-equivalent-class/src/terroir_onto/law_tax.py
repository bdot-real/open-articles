"""Demo 4 and 5: jurisdiction-scoped tax classes, and a trust with no owner."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import RDF, Graph
from rdflib.namespace import SKOS

from .graphs import LAW, TAX, inconsistencies, label, load, reason


# ---- Tax ------------------------------------------------------------------

CLASSIFY = """
PREFIX ex: <https://example.org/tax/>
SELECT ?class ?basis WHERE {
    ?entity ex:taxClassification ?c .
    ?c ex:jurisdiction ?j ; ex:class ?class ; ex:basis ?basis .
}
"""


def tax_class(entity: str, jurisdiction: str) -> tuple[str, str]:
    """Answer 'what is this entity?' only after being told who is asking."""
    g = load("law_tax.ttl")
    rows = list(g.query(CLASSIFY, initBindings={"entity": TAX[entity], "j": TAX[jurisdiction]}))
    if len(rows) != 1:
        raise LookupError(f"{entity} has {len(rows)} classifications in {jurisdiction}")
    cls, basis = rows[0]
    return _local(cls), _local(basis)


HYBRIDS = """
PREFIX ex: <https://example.org/tax/>
SELECT DISTINCT ?entity WHERE {
    ?entity ex:taxClassification ?a , ?b .
    ?a ex:class ?ca . ?b ex:class ?cb .
    FILTER (?ca != ?cb)
}
"""


def hybrid_entities() -> list[str]:
    """Entities whose class depends on the jurisdiction: BEPS Action 2's raw material."""
    g = load("law_tax.ttl")
    return sorted(label(g, r.entity) for r in g.query(HYBRIDS))


def flatten_to_global_class() -> list[str]:
    """Collapse every classification onto the entity, as a global taxClass column would.

    PassThroughEntity and Corporation are declared disjoint, so the reasoner
    reports each hybrid as an inconsistency.
    """
    g = load("law_tax.ttl")
    flat = Graph()
    for entity, c in g.subject_objects(TAX.taxClassification):
        flat.add((entity, RDF.type, g.value(c, TAX["class"])))
    g += flat
    return inconsistencies(reason(g))


# ---- Law ------------------------------------------------------------------

@dataclass(frozen=True)
class TrustConcept:
    concept: str
    system: str
    owner: str | None


def trusts_and_owners() -> list[TrustConcept]:
    """Every concept labelled 'trust' or 'fiducie', and who owns the property."""
    g = load("law_tax.ttl")
    out = []
    for concept in sorted(set(g.subjects(SKOS.prefLabel, None)), key=str):
        names = {str(l).lower() for l in g.objects(concept, SKOS.prefLabel)}
        if names & {"trust", "fiducie"}:
            owner = g.value(concept, LAW.hasOwner)
            out.append(TrustConcept(
                concept=_local(concept),
                system=_local(g.value(concept, LAW.system)),
                owner=_local(owner) if owner else None,
            ))
    return out


def bijural_labels() -> dict[str, str]:
    """The four labels Canadian federal drafting keeps for one concept."""
    g = load("law_tax.ttl")
    return {l.language: str(l) for l in g.objects(LAW.RealPropertyImmovable, SKOS.prefLabel)}


def _local(node) -> str:
    return str(node).rsplit("/", 1)[-1]
