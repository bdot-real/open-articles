"""Loading and reasoning helpers shared by every demo."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import owlrl
from rdflib import Graph, Namespace, URIRef

EX = Namespace("https://example.org/onto/")
EN = Namespace("https://example.org/en/")
FR = Namespace("https://example.org/fr/")
TAX = Namespace("https://example.org/tax/")
LAW = Namespace("https://example.org/law/")
U = Namespace("https://example.org/untranslatable/")
MAP = Namespace("https://example.org/mapping/")

# owlrl records inconsistencies as triples on this predicate rather than raising.
OWLRL_ERROR = URIRef("http://www.daml.org/2002/03/agents/agent-ont#error")


def ontology_dir() -> Path:
    """The ontology/ folder at the repository root."""
    return Path(__file__).resolve().parents[2] / "ontology"


def load(*names: str) -> Graph:
    """Parse one or more Turtle files from ontology/ into a single graph."""
    g = Graph()
    for name in names:
        g.parse(ontology_dir() / name, format="turtle")
    return g


def reason(g: Graph) -> Graph:
    """Expand the graph in place with the OWL 2 RL rule set and return it."""
    owlrl.DeductiveClosure(
        owlrl.OWLRL_Semantics,
        rdfs_closure=False,
        axiomatic_triples=False,
        datatype_axioms=False,
    ).expand(g)
    return g


def inconsistencies(g: Graph) -> list[str]:
    """Messages owlrl left in the graph after reasoning."""
    return sorted(str(o) for o in g.objects(None, OWLRL_ERROR))


def label(g: Graph, node: URIRef) -> str:
    """First rdfs:label or skos:prefLabel, falling back to the local name."""
    for pred in ("http://www.w3.org/2000/01/rdf-schema#label",
                 "http://www.w3.org/2004/02/skos/core#prefLabel"):
        for o in g.objects(node, URIRef(pred)):
            return str(o)
    return str(node).rsplit("/", 1)[-1]
