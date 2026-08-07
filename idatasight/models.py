"""View models shared by state, pages, and the backend seam.

Plain dataclasses — Reflex renders them directly via rx.foreach, and the
phase-2 TAOpy actors will return the same shapes from dispatch().
"""

import dataclasses


@dataclasses.dataclass
class Dataset:
    id: str = ""
    name: str = ""
    source: str = ""
    summary: str = ""          # e.g. "29 countries · 2010–2023 · 4,872 rows"
    refreshed: str = ""        # e.g. "refreshed Aug 2026"
    beliefs_attached: int = 0


@dataclasses.dataclass
class ColumnInfo:
    indicator: str = ""        # e.g. "SE.SEC.CMPT.LO.ZS"
    unit: str = ""             # e.g. "%", "% GDP"
    meaning: str = ""          # plain language, no interpretation


@dataclasses.dataclass
class GroundingField:
    key: str = ""              # Definition | Primary | Forbidden | Threshold
    value: str = ""
    mono: bool = False         # render value in mono (indicator codes)
    ratified: bool = False
    editing: bool = False


@dataclasses.dataclass
class MemoryItem:
    """One entry in the always-present Memory / Ledger rail."""

    name: str = ""
    note: str = ""             # e.g. "v1 · remembered"
    highlight: bool = False


@dataclasses.dataclass
class Verdict:
    country: str = ""
    primary: str = ""          # e.g. "98%" or "—"
    verdict: str = ""          # Success | Not yet | outside envelope
    outside: bool = False      # outside the belief's valid envelope


@dataclasses.dataclass
class Trap:
    """A caught proxy trap: the decoy series read one way, the belief's
    primary series says otherwise (e.g. enrollment 103% vs completion 64%)."""

    entity: str = ""
    decoy_name: str = ""           # e.g. "enrollment"
    decoy_label: str = ""          # e.g. "103%"
    decoy_width: str = ""          # bar width, e.g. "100%"
    primary_name: str = ""         # e.g. "completion"
    primary_label: str = ""        # e.g. "64%"
    primary_width: str = ""        # bar width
    unguided: str = ""             # what the ungrounded reading said
    believed: str = ""             # verdict under the belief


@dataclasses.dataclass
class Receipt:
    tokens: int = 0
    series: int = 0
    ungrounded_tokens: int = 0
    ungrounded_series: int = 0
    ledger_row: int = 0


@dataclasses.dataclass
class LedgerPoint:
    episode: str = ""              # "ep 1" … "ep 10"
    with_memory: int = 0
    without_memory: int = 0


@dataclasses.dataclass
class Tile:
    value: str = ""
    label: str = ""
    accent: bool = False


@dataclasses.dataclass
class TimelineEvent:
    kind: str = "data"             # "belief" (meaning moved) | "data" (verdicts moved)
    title: str = ""
    when: str = ""
    detail: str = ""
    note: str = ""


@dataclasses.dataclass
class Analyst:
    name: str = ""
    belief_label: str = ""
    selected: bool = False


# --- composite replies — the contract dispatch() fulfills in phase 2 -------

@dataclasses.dataclass
class GroundingDraft:
    fields: list[GroundingField] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class RatifyResult:
    version: str = ""              # e.g. "v1"
    remembered_on: str = ""        # e.g. "Aug 7, 2026"


@dataclasses.dataclass
class AnalysisResult:
    belief_label: str = ""         # e.g. "Under: Spending ≠ completion · v1"
    verdicts: list[Verdict] = dataclasses.field(default_factory=list)
    traps: list[Trap] = dataclasses.field(default_factory=list)
    trap_count: int = 0
    thesis_note: str = ""
    receipt: Receipt = dataclasses.field(default_factory=Receipt)


@dataclasses.dataclass
class LedgerData:
    points: list[LedgerPoint] = dataclasses.field(default_factory=list)
    tiles: list[Tile] = dataclasses.field(default_factory=list)
    rows: list[MemoryItem] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class BeliefHistory:
    belief_name: str = ""
    version_label: str = ""        # e.g. "Edit → v3"
    analysts: list[Analyst] = dataclasses.field(default_factory=list)
    events: list[TimelineEvent] = dataclasses.field(default_factory=list)
    compare_note: str = ""
