"""Demo 6: a SHACL gate for machine-proposed mappings.

A similarity score says two terms keep similar company. It does not say which
SKOS relation holds. This gate lets weak relations through, and refuses strong
ones (owl:equivalentClass, skos:exactMatch) until a named person signs them.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from pyshacl import validate
from rdflib import RDF, BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, SKOS, XSD

from .graphs import MAP, ontology_dir

RELATIONS = {
    "equivalentClass": OWL.equivalentClass,
    "exactMatch": SKOS.exactMatch,
    "closeMatch": SKOS.closeMatch,
    "broadMatch": SKOS.broadMatch,
    "narrowMatch": SKOS.narrowMatch,
    "relatedMatch": SKOS.relatedMatch,
}


@dataclass(frozen=True)
class Proposal:
    source: str
    target: str
    relation: str
    score: float
    approved_by: str = ""
    approved_on: str = ""


def read_proposals(path: Path) -> list[Proposal]:
    with path.open(newline="", encoding="utf-8") as f:
        return [
            Proposal(r["source"], r["target"], r["relation"], float(r["score"]),
                     r.get("approved_by", ""), r.get("approved_on", ""))
            for r in csv.DictReader(f)
        ]


def to_graph(proposals: list[Proposal]) -> tuple[Graph, dict[URIRef | BNode, Proposal]]:
    g = Graph()
    index = {}
    for i, p in enumerate(proposals):
        node = MAP[f"m{i}"]
        index[node] = p
        g.add((node, RDF.type, MAP.Mapping))
        g.add((node, MAP.source, URIRef(p.source)))
        g.add((node, MAP.target, URIRef(p.target)))
        g.add((node, MAP.relation, RELATIONS[p.relation]))
        g.add((node, MAP.score, Literal(p.score, datatype=XSD.decimal)))
        if p.approved_by:
            g.add((node, MAP.approvedBy, Literal(p.approved_by)))
        if p.approved_on:
            g.add((node, MAP.approvedOn, Literal(p.approved_on, datatype=XSD.date)))
    return g, index


@dataclass(frozen=True)
class Verdict:
    proposal: Proposal
    accepted: bool
    reason: str


def run_gate(proposals: list[Proposal]) -> list[Verdict]:
    data, index = to_graph(proposals)
    shapes = Graph().parse(ontology_dir() / "mapping_gate.shacl.ttl", format="turtle")
    _, report, _ = validate(data, shacl_graph=shapes, advanced=True, allow_warnings=True)

    SH = "http://www.w3.org/ns/shacl#"
    failures: dict = {}
    for result in report.subjects(RDF.type, URIRef(SH + "ValidationResult")):
        focus = report.value(result, URIRef(SH + "focusNode"))
        failures[focus] = str(report.value(result, URIRef(SH + "resultMessage")))

    return [
        Verdict(p, node not in failures, failures.get(node, "ok"))
        for node, p in index.items()
    ]
