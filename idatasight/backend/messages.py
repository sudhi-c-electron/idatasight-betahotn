"""Actor messages — the vocabulary of the iDataSight backend.

Phase 2 (TAOpy): each class below becomes a ``tao.Event`` subclass — a frozen,
validated value object — and is delivered to its actor via ``tao_ask`` /
``tao_tell``. Until then they are plain frozen dataclasses so the UI can speak
the protocol today. Field names are final; the actors are written to them.

Actor map (phase 2 addresses):
    dataset-actor   ListDatasets · FetchColumns · RefreshDataset
    belief-actor    DraftGrounding · RatifyBelief · ListBeliefs · FetchBeliefHistory
    analysis-actor  RunAnalysis
    ledger-actor    FetchLedger
"""

from dataclasses import dataclass, field


# --- dataset-actor ---------------------------------------------------------

@dataclass(frozen=True)
class ListDatasets:
    """All registered datasets, with summaries and belief counts."""


@dataclass(frozen=True)
class FetchColumns:
    """Column catalog for one dataset — plain language, no interpretation."""

    dataset_id: str


@dataclass(frozen=True)
class RefreshDataset:
    """Pull new rows; every remembered belief re-runs automatically."""

    dataset_id: str


# --- belief-actor ----------------------------------------------------------

@dataclass(frozen=True)
class DraftGrounding:
    """Distill a plain-words hypothesis into a proposed grounding pack."""

    hypothesis: str
    dataset_id: str


@dataclass(frozen=True)
class RatifyBelief:
    """Commit a human-confirmed grounding pack to memory as a new version.

    Never overwrites — reopening a belief later drafts the next version.
    """

    dataset_id: str
    statement: str
    fields: dict = field(default_factory=dict)  # key -> ratified value


@dataclass(frozen=True)
class ListBeliefs:
    """Beliefs in memory; optionally only those watching one dataset."""

    dataset_id: str = ""


@dataclass(frozen=True)
class RecallBelief:
    """The latest remembered version of a dataset's belief, verbatim."""

    dataset_id: str


@dataclass(frozen=True)
class FetchBeliefHistory:
    """Both histories of one belief — belief changes and data updates."""

    belief_id: str
    analyst: str = ""


# --- analysis-actor --------------------------------------------------------

@dataclass(frozen=True)
class RunAnalysis:
    """Judge the dataset under a recalled belief; log the receipt."""

    dataset_id: str
    belief_id: str


# --- ledger-actor ----------------------------------------------------------

@dataclass(frozen=True)
class FetchLedger:
    """Cost-per-correct-answer series and the appended run rows."""
