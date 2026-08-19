"""The deployable unit is a pair, not a prompt.

Behaviour is a function of your prompt and their model. Those version
independently and only one of those changes is an event you receive. A registry
that versions only the prompt cannot answer the rollback question, because a
prompt is known-good for a PAIRING rather than on its own.

Two rules are encoded here and both are free:

  the model version is dated, never an alias
  every response records the pair that produced it
"""
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

# A dated version looks like name-YYYYMMDD or name-YYYYMMDD-vN. A bare alias
# does not, and a bare alias is a deferred incident for the same reason a
# mutable container tag is.
DATED = re.compile(r"-\d{8}(-v\d+)?$")


class UnpinnedModel(ValueError):
    pass


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@dataclass(frozen=True)
class Release:
    """An immutable prompt-and-model pairing."""
    prompt_id: str
    prompt_text: str
    model_version: str
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not DATED.search(self.model_version):
            raise UnpinnedModel(
                f"{self.model_version!r} looks like an alias. Pin the dated "
                f"version, or you cannot roll back to a pairing that existed."
            )

    @property
    def prompt_hash(self) -> str:
        return content_hash(self.prompt_text)

    @property
    def pair(self) -> str:
        """The identifier that actually determines behaviour."""
        return f"{self.prompt_hash[:12]}@{self.model_version}"


@dataclass
class Registry:
    """Append-only history of pairings, with observed quality.

    Append-only matters. The rollback question is answered from history, and a
    registry you can edit is a history you cannot trust.
    """
    _releases: list[Release] = field(default_factory=list)
    _quality: dict[str, float] = field(default_factory=dict)

    def publish(self, release: Release) -> Release:
        self._releases.append(release)
        return release

    def observe(self, release: Release, quality: float) -> None:
        self._quality[release.pair] = quality

    def quality_of(self, release: Release) -> float | None:
        return self._quality.get(release.pair)

    def current(self) -> Release:
        return self._releases[-1]

    def best_by_prompt_label(self, threshold: float) -> Release | None:
        """The lookup people actually perform, and the trap.

        Quality gets recorded against the prompt version, because that is what
        the team changed and what the changelog remembers. Ask this registry
        which prompt was best and it answers honestly from history: the one
        that scored highest, ever, against any model.

        That prompt may be badly matched to the model serving today. History
        keyed by prompt alone cannot tell you, because the model was never part
        of the key.
        """
        best, best_q = None, threshold
        for r in self._releases[:-1]:
            q = self._quality.get(r.pair)
            if q is not None and q >= best_q:
                best, best_q = r, q
        return best

    def last_known_good(self, threshold: float,
                        model_version: str | None = None) -> Release | None:
        """The rollback target, and the reason this method takes an argument.

        Constrained to a model version, this returns a pairing that was
        actually observed to work. Unconstrained, it happily returns a prompt
        that was excellent against a model no longer serving, which can be
        worse than the release you are rolling back from.
        """
        for r in reversed(self._releases[:-1]):
            if model_version is not None and r.model_version != model_version:
                continue
            q = self._quality.get(r.pair)
            if q is not None and q >= threshold:
                return r
        return None
