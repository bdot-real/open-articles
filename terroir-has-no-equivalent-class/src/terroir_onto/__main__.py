"""python -m terroir_onto [demo ...]"""

from __future__ import annotations

import argparse

from . import gate, law_tax, terroir, untranslatables
from .graphs import ontology_dir


def h(title: str) -> None:
    print(f"\n== {title} " + "=" * max(0, 66 - len(title)))


def demo_naive() -> None:
    h("1. Naive alignment: fr:Terroir owl:equivalentClass en:Soil")
    r = terroir.naive_alignment()
    for name in r.soil_that_became_terroir:
        print(f"  inferred terroir: {name}")
    for name in r.terroir_that_became_soil:
        print(f"  inferred soil:    {name}")
    print("  No error raised. Both inferences are wrong.")


def demo_defined() -> None:
    h("2. Minted class, defined by its parts (no instance asserted as Terroir)")
    for c in terroir.defined_class():
        verdict = "TERROIR" if c.is_terroir else "not terroir"
        gap = f"  missing: {', '.join(c.missing)}" if c.missing else ""
        print(f"  {c.place:<28} {verdict:<12}{gap}")


def demo_words() -> None:
    h("3. Words with no English equivalent")
    print(f"  {'word':<15}{'lang':<6}{'English did':<13}{'pattern':<19}mappings")
    for w in untranslatables.report():
        print(f"  {w.word:<15}{w.language:<6}{w.strategy:<13}{w.pattern:<19}{'; '.join(w.mappings) or '-'}")


def demo_law() -> None:
    h("4. Law: who owns the property in a trust?")
    for t in law_tax.trusts_and_owners():
        print(f"  {t.concept:<14} {t.system:<16} owner: {t.owner or 'nobody'}")
    print("  Bijural doublet for one federal concept:")
    for lang, text in sorted(law_tax.bijural_labels().items()):
        print(f"    {lang:<16} {text}")


def demo_tax() -> None:
    h("5. Tax: one entity, a class per jurisdiction")
    for entity in ("AcmeLLC", "MapleULC", "NorthwindInc"):
        us, _ = law_tax.tax_class(entity, "US")
        ca, _ = law_tax.tax_class(entity, "Canada")
        print(f"  {entity:<14} US: {us:<19} Canada: {ca}")
    print(f"  Hybrids: {', '.join(law_tax.hybrid_entities())}")
    print("  Flattened to a single global class, the reasoner reports:")
    for msg in law_tax.flatten_to_global_class():
        print(f"    {msg.replace('https://example.org/tax/', '')}")


def demo_gate() -> None:
    h("6. Mapping gate: strong relations need a human signature")
    for v in gate.run_gate(gate.read_proposals(ontology_dir() / "proposals.csv")):
        p = v.proposal
        src, tgt = p.source.rsplit("/", 1)[-1], p.target.rsplit("/", 1)[-1]
        mark = "ACCEPT" if v.accepted else "BLOCK "
        print(f"  {mark} {p.score:.2f}  {src} {p.relation} {tgt}")


DEMOS = {
    "naive": demo_naive, "defined": demo_defined, "words": demo_words,
    "law": demo_law, "tax": demo_tax, "gate": demo_gate,
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="terroir-onto")
    parser.add_argument("demos", nargs="*", choices=[*DEMOS, "all"], default="all")
    args = parser.parse_args()
    for name in (DEMOS if "all" in args.demos else args.demos):
        DEMOS[name]()
    print()


if __name__ == "__main__":
    main()
