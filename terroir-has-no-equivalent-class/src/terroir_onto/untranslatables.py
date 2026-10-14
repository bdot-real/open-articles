"""Demo 3: what English did with each untranslatable word, read off the SKOS labels."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Literal, URIRef
from rdflib.namespace import SKOS

from .graphs import U, label, load


@dataclass(frozen=True)
class Word:
    word: str
    language: str
    strategy: str          # "borrowed" or "paraphrased"
    pattern: str
    mappings: list[str]    # e.g. ["broadMatch longing"]


MAPPING_PROPS = ("exactMatch", "closeMatch", "broadMatch", "narrowMatch", "relatedMatch")


def report() -> list[Word]:
    g = load("terroir.ttl", "untranslatables.ttl")
    words = []
    for concept in sorted(g.subjects(SKOS.inScheme, U.Words), key=str):
        labels: list[Literal] = list(g.objects(concept, SKOS.prefLabel))
        source = next(l for l in labels if l.language and not l.language.startswith("en")
                      and "-" not in l.language)
        native_forms = {str(l) for l in labels if not (l.language or "").startswith("en")}
        english = [str(l) for l in labels if (l.language or "") == "en"]
        # Borrowing = English carries a label identical to a native form.
        strategy = "borrowed" if any(e in native_forms for e in english) else "paraphrased"
        mappings = [
            f"{p} {label(g, o)}"
            for p in MAPPING_PROPS
            for o in g.objects(concept, URIRef(str(SKOS) + p))
        ]
        words.append(Word(
            word=_display(labels),
            language=source.language,
            strategy=strategy,
            pattern=label(g, g.value(concept, U.pattern)),
            mappings=mappings,
        ))
    return words


def _display(labels: list[Literal]) -> str:
    latin = [l for l in labels if (l.language or "").endswith("Latn") or (l.language or "") == "en"]
    return str(latin[0]) if latin else str(labels[0])
