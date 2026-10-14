"""Demo 1 and 2: the naive equivalence versus the minted, defined class."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import RDF, Graph

from .graphs import EN, EX, FR, label, load, reason


@dataclass(frozen=True)
class NaiveResult:
    soil_that_became_terroir: list[str]
    terroir_that_became_soil: list[str]


def naive_alignment() -> NaiveResult:
    """Reason over `fr:Terroir owl:equivalentClass en:Soil` and report the damage."""
    g = reason(load("terroir_naive.ttl"))
    asserted = load("terroir_naive.ttl")

    def inferred_only(cls) -> list[str]:
        return sorted(
            label(g, s) for s in g.subjects(RDF.type, cls)
            if (s, RDF.type, cls) not in asserted and not _is_class(g, s)
        )

    return NaiveResult(
        soil_that_became_terroir=inferred_only(FR.Terroir),
        terroir_that_became_soil=inferred_only(EN.Soil),
    )


@dataclass(frozen=True)
class Classification:
    place: str
    is_terroir: bool
    missing: list[str]


DIMENSIONS = {
    "production place": None,
    "soil profile": EX.hasSoilProfile,
    "microclimate": EX.hasMicroclimate,
    "local practice": EX.hasLocalPractice,
}


def defined_class() -> list[Classification]:
    """Let the reasoner decide what is a terroir from the class definition alone.

    No instance in terroir.ttl is asserted to be an ex:Terroir. Membership is
    inferred from the owl:intersectionOf definition.
    """
    raw = load("terroir.ttl")
    g = reason(load("terroir.ttl"))
    candidates = sorted(
        set(raw.subjects(RDF.type, EX.ProductionPlace)) | set(raw.subjects(RDF.type, EN.Soil)),
        key=str,
    )
    out = []
    for node in candidates:
        if (node, RDF.type, EX.ProductionPlace) not in raw:
            out.append(Classification(label(g, node), (node, RDF.type, EX.Terroir) in g,
                                      ["not a production place"]))
            continue
        missing = []
        for name, prop in DIMENSIONS.items():
            if prop is not None and raw.value(node, prop) is None:
                missing.append(name)
        out.append(Classification(label(g, node), (node, RDF.type, EX.Terroir) in g, missing))
    return out


def _is_class(g: Graph, node) -> bool:
    from rdflib import OWL, RDFS
    return (node, RDF.type, OWL.Class) in g or (node, RDF.type, RDFS.Class) in g
