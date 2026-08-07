"""EverOS memory substrate — where the invariants live.

Speaks the EverOS storage-root layout natively (everos precept: pack-plane
binding + storage-root layout; same seam Groundwork realizes in
groundwork/core/memory.py):

    <root>/idatasight/<dataset_id>/
        agents/<user>/skills/skill_<name>/     the pack plane — SKILL.md is the
            SKILL.md                           canon of the latest ratified
            references/v<N>.json               declaration; every version kept
                                               verbatim, append-only
        users/<user>/episodes/                 the run-record plane —
            episode-<YYYY-MM-DD>.md            entry-bracketed daily appends

Default root is ~/.everos (override with EVEROS_ROOT). No server is required —
the file canon suffices and is the no-network fallback; an EverOS server
started over this same root indexes every unit. The markdown tree is the
asset; any index directory is disposable. All writes are atomic
(same-directory tmp + rename); a version, once remembered, is never
overwritten. Token-ledger rows stay in the application (data/store/) — only
the episode record is booked to memory.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_APP = "idatasight"


def _atomic_write(path: Path, text: str) -> None:
    handle, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            file.write(text)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def _render_skill(record: dict, agent_id: str) -> str:
    """SKILL.md — the canon of the latest ratified declaration."""
    name = record.get("concept", "belief")
    fields = record.get("fields", {})
    front = "\n".join(
        [
            "---",
            f"id: skill_{name}",
            "type: agent_skill",
            "schema_version: 1",
            f"agent_id: {agent_id}",
            "track: agent",
            "---",
        ]
    )
    body = "\n".join(
        [
            f"# {record.get('display_name', name)} (v{record.get('version', 1)})",
            "",
            record.get("statement", ""),
            "",
            f"Definition: {fields.get('Definition', '')}",
            f"Primary series: {fields.get('Primary', '')}",
            f"Forbidden: {fields.get('Forbidden', '')}",
            f"Threshold: {fields.get('Threshold', '')}",
            "",
            "```json",
            json.dumps(record, indent=2),
            "```",
        ]
    )
    return front + "\n\n" + body + "\n"


class EverOSMemory:
    """remember, recall, history — against the EverOS storage root."""

    def __init__(self, root: str | Path | None = None) -> None:
        self._root = Path(
            root or os.environ.get("EVEROS_ROOT") or (Path.home() / ".everos")
        )

    @property
    def root(self) -> Path:
        return self._root

    # --- path planes -------------------------------------------------------

    def _skill_dir(self, user: str, dataset_id: str, name: str) -> Path:
        return (
            self._root / _APP / dataset_id / "agents" / user / "skills"
            / f"skill_{name}"
        )

    def _skills_home(self, user: str, dataset_id: str) -> Path:
        return self._root / _APP / dataset_id / "agents" / user / "skills"

    def _episodes_home(self, user: str, dataset_id: str) -> Path:
        return self._root / _APP / dataset_id / "users" / user / "episodes"

    # --- the pack plane ----------------------------------------------------

    def remember_pack(self, user: str, dataset_id: str, record: dict) -> None:
        """Canon write of one belief version. Append-only, never overwrites."""
        name = record["concept"]
        version = int(record["version"])
        skill = self._skill_dir(user, dataset_id, name)
        references = skill / "references"
        references.mkdir(parents=True, exist_ok=True)
        unit = references / f"v{version}.json"
        if unit.exists():
            raise ValueError(
                f"already remembered: {name} v{version} for {user!r}"
            )
        _atomic_write(
            unit,
            json.dumps(
                {
                    "pack": record,
                    "remembered_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            ),
        )
        latest = max(
            (v for v in self.history(user, dataset_id) if v["concept"] == name),
            key=lambda r: r["version"],
        )
        _atomic_write(skill / "SKILL.md", _render_skill(latest, user))

    def recall(self, user: str, dataset_id: str) -> dict | None:
        """The latest remembered declaration, or None if memory is empty."""
        versions = self.history(user, dataset_id)
        return versions[-1] if versions else None

    def history(self, user: str, dataset_id: str) -> list[dict]:
        """Every remembered version, oldest first."""
        home = self._skills_home(user, dataset_id)
        if not home.exists():
            return []
        records = []
        for unit in home.glob("skill_*/references/v*.json"):
            payload = json.loads(unit.read_text(encoding="utf-8"))
            record = payload["pack"]
            record["remembered_at"] = payload.get("remembered_at", "")
            records.append(record)
        return sorted(records, key=lambda r: r["version"])

    # --- the run-record plane ----------------------------------------------

    def remember_episode(
        self, user: str, dataset_id: str, episode_id: int, note: str = ""
    ) -> None:
        """Book one run to the daily episode log (entry-bracketed append)."""
        home = self._episodes_home(user, dataset_id)
        home.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc)
        page = home / f"episode-{stamp:%Y-%m-%d}.md"
        marker = f"ep_{stamp:%Y%m%d}_{episode_id:08d}"
        line = note or f"episode {episode_id} booked to the ledger"
        entry = f"<!-- entry:{marker} -->\n{line}\n"
        with page.open("a", encoding="utf-8") as handle:
            handle.write(entry)

    def episodes(self, user: str, dataset_id: str) -> tuple[int, ...]:
        home = self._episodes_home(user, dataset_id)
        if not home.exists():
            return ()
        found: list[int] = []
        for page in sorted(home.glob("episode-*.md")):
            for line in page.read_text(encoding="utf-8").splitlines():
                if line.startswith("<!-- entry:ep_"):
                    found.append(int(line.split("_")[-1].rstrip(" ->")))
        return tuple(found)
