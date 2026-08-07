"""Warehouse — dataset registry and observation access.

Ported from BetaThon (scripts/fetch_wdi.py, scripts/run_five_datasets.py).
Default source is the local CSV mirror under data/warehouse/ (the real panels
pulled from the World Bank / Eurostat APIs). Set IDATASIGHT_SOURCE=snowflake
to read the same tables from Snowflake database BETATHON instead (profile via
~/.snowflake/connections.toml, default connection MN74135 — browser OAuth).
"""

from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE = APP_ROOT / "data" / "warehouse"

SOURCE = os.environ.get("IDATASIGHT_SOURCE", "csv")
SF_CONNECTION = os.environ.get("IDATASIGHT_SF_CONNECTION", "MN74135")

# --- registry — one entry per dataset card ---------------------------------
# concept: the dataset's bound Concept config (BetaThon run_five_datasets
# DATASETS + the formal secondary_completion concept for wdi).

REGISTRY: dict[str, dict] = {
    "wdi": {
        "name": "Education panel",
        "source": "World Bank WDI",
        "snowflake_table": "BETATHON.RAW.WDI_OBSERVATIONS",
        "indicators": [
            "SE.SEC.ENRR", "SE.SEC.CMPT.LO.ZS", "SE.PRM.CMPT.ZS",
            "SE.XPD.TOTL.GD.ZS", "SE.XPD.TOTL.GB.ZS", "NY.GDP.PCAP.CD",
            "NE.TRD.GNFS.ZS", "SP.POP.TOTL", "SE.TER.ENRR",
            "SE.SEC.CUAT.UP.ZS", "GC.XPN.TOTL.GD.ZS", "BX.KLT.DINV.WD.GD.ZS",
        ],
        "concept": {
            "name": "secondary_completion",
            "display_name": "Spending ≠ completion",
            "definition": "success = completing secondary school, not being in it",
            "primary": "SE.SEC.CMPT.LO.ZS",
            "decoy": "SE.SEC.ENRR",
            "forbidden": {
                "SE.SEC.ENRR": "enrollment — counts repeaters",
                "SE.XPD.TOTL.GD.ZS": "spend — effort, not result",
                "SE.XPD.TOTL.GB.ZS": "spend — effort, not result",
                "NY.GDP.PCAP.CD": "GDP — wealth, not schooling",
                "SE.TER.ENRR": "tertiary enrollment — access, not completion",
            },
            "thresholds": {"high": 90.0, "moderate": 75.0},
            "inverted": False,
            "unit": "%",
        },
    },
    "fiscal": {
        "name": "Fiscal",
        "source": "World Bank",
        "snowflake_table": "BETATHON.RAW.DS_FISCAL_OBS",
        "indicators": [
            "GC.TAX.TOTL.GD.ZS", "GC.XPN.TOTL.GD.ZS", "GC.REV.XGRT.GD.ZS",
            "GC.DOD.TOTL.GD.ZS", "GC.NLD.TOTL.GD.ZS", "NY.GDP.PCAP.CD",
        ],
        "concept": {
            "name": "public_fiscal_effort",
            "display_name": "Fiscal effort",
            "definition": "success = scale of government outlay relative to GDP",
            "primary": "GC.XPN.TOTL.GD.ZS",
            "decoy": "NY.GDP.PCAP.CD",
            "forbidden": {
                "NY.GDP.PCAP.CD": "GDP per capita — wealth, not effort",
                "GC.DOD.TOTL.GD.ZS": "debt stock — not effort",
            },
            "thresholds": {"high": 35.0, "moderate": 25.0},
            "inverted": False,
            "unit": "% GDP",
        },
    },
    "trade": {
        "name": "Trade",
        "source": "World Bank",
        "snowflake_table": "BETATHON.RAW.DS_TRADE_OBS",
        "indicators": [
            "NE.EXP.GNFS.ZS", "NE.IMP.GNFS.ZS", "NE.TRD.GNFS.ZS",
            "TX.VAL.MRCH.XD.WD", "TM.VAL.MRCH.XD.WD", "BX.KLT.DINV.WD.GD.ZS",
        ],
        "concept": {
            "name": "export_orientation",
            "display_name": "Export orientation",
            "definition": "success = exports of goods and services relative to GDP",
            "primary": "NE.EXP.GNFS.ZS",
            "decoy": "NE.IMP.GNFS.ZS",
            "forbidden": {
                "BX.KLT.DINV.WD.GD.ZS": "FDI — investment, not exports",
                "TM.VAL.MRCH.XD.WD": "imports index — not orientation",
                "NE.IMP.GNFS.ZS": "imports — dependence, not orientation",
            },
            "thresholds": {"high": 40.0, "moderate": 25.0},
            "inverted": False,
            "unit": "% GDP",
        },
    },
    "labor_hc": {
        "name": "Labor",
        "source": "World Bank",
        "snowflake_table": "BETATHON.RAW.DS_LABOR_HC_OBS",
        "indicators": [
            "SL.UEM.TOTL.ZS", "SL.TLF.CACT.ZS", "SL.TLF.TOTL.IN",
            "SE.ADT.1524.LT.ZS", "SE.SEC.ENRR", "NY.GDP.PCAP.CD",
        ],
        "concept": {
            "name": "labor_force_engagement",
            "display_name": "Labor engagement",
            "definition": "success = participation in the labor force, not low unemployment",
            "primary": "SL.TLF.CACT.ZS",
            "decoy": "SL.UEM.TOTL.ZS",
            "forbidden": {
                "SE.SEC.ENRR": "enrollment — school, not labor",
                "SE.ADT.1524.LT.ZS": "literacy — capability, not engagement",
                "NY.GDP.PCAP.CD": "GDP — wealth, not engagement",
                "SL.UEM.TOTL.ZS": "unemployment — absence, not participation",
            },
            "thresholds": {"high": 65.0, "moderate": 55.0},
            "inverted": False,
            "unit": "%",
        },
    },
    "inequality": {
        "name": "Inequality",
        "source": "World Bank",
        "snowflake_table": "BETATHON.RAW.DS_INEQUALITY_OBS",
        "indicators": [
            "SI.POV.GINI", "SI.DST.05TH.20", "SI.DST.FRST.20",
            "SI.POV.DDAY", "NY.GNP.PCAP.CD", "SP.URB.TOTL.IN.ZS",
        ],
        "concept": {
            "name": "income_equality",
            "display_name": "Income equality",
            "definition": "success = low income dispersion (Gini), not high mean income",
            "primary": "SI.POV.GINI",
            "decoy": "NY.GNP.PCAP.CD",
            "forbidden": {
                "NY.GNP.PCAP.CD": "GNI per capita — wealth, not equality",
                "SP.URB.TOTL.IN.ZS": "urbanization — not equality",
                "SI.POV.DDAY": "poverty headcount — not dispersion",
            },
            # inverted: lower Gini = more equal = success
            "thresholds": {"high": 35.0, "moderate": 42.0},
            "inverted": True,
            "unit": "",
        },
    },
    "eurostat_edu_fin": {
        "name": "EU edu finance",
        "source": "Eurostat",
        "snowflake_table": "BETATHON.RAW.DS_EUROSTAT_EDU_FIN_OBS",
        "indicators": [],  # eurostat codes discovered from the data
        "concept": {
            "name": "eu_public_edu_expenditure",
            "display_name": "EU edu expenditure",
            "definition": "success = public education spend share of GDP (Eurostat)",
            "primary": "",  # chosen at load time: widest-coverage series
            "decoy": "",
            "forbidden": {},
            "thresholds": {"high": 5.5, "moderate": 4.5},
            "inverted": False,
            "unit": "% GDP",
        },
    },
}

# Plain-language column meanings ("no interpretation yet") for known codes.
MEANINGS = {
    "SE.SEC.CMPT.LO.ZS": ("%", "who finishes lower-secondary school"),
    "SE.SEC.ENRR": ("%", "who is enrolled — incl. repeaters, can top 100"),
    "SE.PRM.CMPT.ZS": ("%", "who finishes primary school"),
    "SE.XPD.TOTL.GD.ZS": ("% GDP", "what government spends on education"),
    "SE.XPD.TOTL.GB.ZS": ("% budget", "education share of government spending"),
    "NY.GDP.PCAP.CD": ("USD", "output per person — wealth, not schooling"),
    "NE.TRD.GNFS.ZS": ("% GDP", "trade volume relative to the economy"),
    "SP.POP.TOTL": ("count", "how many people live there"),
    "SE.TER.ENRR": ("%", "who is enrolled in tertiary education"),
    "SE.SEC.CUAT.UP.ZS": ("%", "adults who attained upper secondary"),
    "GC.XPN.TOTL.GD.ZS": ("% GDP", "what government spends overall"),
    "BX.KLT.DINV.WD.GD.ZS": ("% GDP", "foreign direct investment inflows"),
    "GC.TAX.TOTL.GD.ZS": ("% GDP", "what government collects in taxes"),
    "GC.REV.XGRT.GD.ZS": ("% GDP", "government revenue excluding grants"),
    "GC.DOD.TOTL.GD.ZS": ("% GDP", "central government debt stock"),
    "GC.NLD.TOTL.GD.ZS": ("% GDP", "government net lending or borrowing"),
    "NE.EXP.GNFS.ZS": ("% GDP", "what the country exports"),
    "NE.IMP.GNFS.ZS": ("% GDP", "what the country imports"),
    "TX.VAL.MRCH.XD.WD": ("index", "merchandise export volume index"),
    "TM.VAL.MRCH.XD.WD": ("index", "merchandise import volume index"),
    "SL.UEM.TOTL.ZS": ("%", "who is unemployed"),
    "SL.TLF.CACT.ZS": ("%", "who participates in the labor force"),
    "SL.TLF.TOTL.IN": ("count", "size of the labor force"),
    "SE.ADT.1524.LT.ZS": ("%", "young adults who can read"),
    "SI.POV.GINI": ("index", "income dispersion — higher is less equal"),
    "SI.DST.05TH.20": ("%", "income share of the richest fifth"),
    "SI.DST.FRST.20": ("%", "income share of the poorest fifth"),
    "SI.POV.DDAY": ("%", "who lives under the poverty line"),
    "NY.GNP.PCAP.CD": ("USD", "income per person — wealth, not equality"),
    "SP.URB.TOTL.IN.ZS": ("%", "who lives in cities"),
}


def _csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_observations(ds_id: str) -> list[dict]:
    """Long rows: country, iso2, iso3, year, indicator_code, value."""
    if SOURCE == "snowflake":
        rows = _snowflake_observations(ds_id)
        if rows is not None:
            return rows
    return _csv_rows(WAREHOUSE / ds_id / "observations.csv")


def _snowflake_observations(ds_id: str) -> list[dict] | None:
    """Read the same panel from Snowflake BETATHON (BetaThon load_snowflake
    wrote it there). Returns None on any failure so the CSV mirror serves."""
    table = REGISTRY.get(ds_id, {}).get("snowflake_table")
    if not table:
        return None
    try:
        os.environ.setdefault("SF_SKIP_TOKEN_FILE_PERMISSIONS_VERIFICATION", "true")
        import snowflake.connector  # optional dependency

        conn = snowflake.connector.connect(connection_name=SF_CONNECTION)
        cur = conn.cursor()
        cur.execute(
            f"SELECT COUNTRY, ISO2, ISO3, YEAR, INDICATOR_CODE, VALUE FROM {table}"
        )
        rows = [
            {
                "country": r[0], "iso2": r[1], "iso3": r[2],
                "year": r[3], "indicator_code": r[4],
                "value": "" if r[5] is None else r[5],
            }
            for r in cur.fetchall()
        ]
        cur.close()
        conn.close()
        return rows
    except Exception as e:  # connector missing, OAuth expired, offline…
        print(f"[warehouse] snowflake read failed for {ds_id}: {e}; using CSV")
        return None


def load_indicators(ds_id: str) -> list[dict]:
    return _csv_rows(WAREHOUSE / ds_id / "indicators.csv")


def panel_latest(ds_id: str) -> tuple[dict[str, tuple[int, dict]], dict[str, str]]:
    """entity -> (latest year, {code: value}); entity -> display name."""
    by_key_year: dict[tuple[str, int], dict] = defaultdict(dict)
    names: dict[str, str] = {}
    for r in load_observations(ds_id):
        if r.get("value") in (None, ""):
            continue
        key = r.get("iso3") or r.get("iso2") or ""
        year = int(r["year"])
        by_key_year[(key, year)][r["indicator_code"]] = float(r["value"])
        names[key] = r.get("country") or key
    latest: dict[str, tuple[int, dict]] = {}
    for (key, year), vals in by_key_year.items():
        if key not in latest or year > latest[key][0]:
            latest[key] = (year, vals)
    return latest, names


def panel_best(ds_id: str) -> tuple[dict[str, dict[str, float]], dict[str, str]]:
    """entity -> {code: latest non-null value}; entity -> display name.

    BetaThon proof_grounding semantics: per series, the most recent non-null
    observation — a country is judged on its latest completion figure even if
    other series run further forward.
    """
    best: dict[str, dict[str, tuple[int, float]]] = defaultdict(dict)
    names: dict[str, str] = {}
    for r in load_observations(ds_id):
        if r.get("value") in (None, ""):
            continue
        key = r.get("iso3") or r.get("iso2") or ""
        code = r["indicator_code"]
        year = int(r["year"])
        prev = best[key].get(code)
        if prev is None or year > prev[0]:
            best[key][code] = (year, float(r["value"]))
        names[key] = r.get("country") or key
    return (
        {k: {c: v for c, (_, v) in codes.items()} for k, codes in best.items()},
        names,
    )


def concept_cfg(ds_id: str) -> dict:
    """The dataset's bound concept config; eurostat resolves its primary to
    the widest-coverage series (BetaThon score_dataset behavior)."""
    cfg = dict(REGISTRY[ds_id]["concept"])
    if ds_id == "eurostat_edu_fin" and not cfg["primary"]:
        counts: dict[str, int] = defaultdict(int)
        for r in load_observations(ds_id):
            if r.get("value") not in (None, ""):
                counts[r["indicator_code"]] += 1
        if counts:
            cfg["primary"] = max(counts.items(), key=lambda x: x[1])[0]
    return cfg


def dataset_stats(ds_id: str) -> dict:
    """Card summary: countries · years · rows, and the refreshed date."""
    obs = load_observations(ds_id)
    countries = {r.get("iso3") or r.get("iso2") for r in obs if r.get("value") not in (None, "")}
    years = [int(r["year"]) for r in obs if r.get("value") not in (None, "")]
    manifest = WAREHOUSE / ds_id / "manifest.json"
    refreshed = ""
    if manifest.exists():
        pulled = json.loads(manifest.read_text()).get("pulled_at", "")
        refreshed = f"refreshed {pulled[:10]}" if pulled else ""
    if not refreshed:
        p = WAREHOUSE / ds_id / "observations.csv"
        if p.exists():
            from datetime import datetime

            refreshed = "refreshed " + datetime.fromtimestamp(
                p.stat().st_mtime
            ).strftime("%b %Y")
    summary = ""
    if obs:
        summary = (
            f"{len(countries)} countries · {min(years)}–{max(years)} · "
            f"{len(obs):,} rows"
        )
    return {"summary": summary, "refreshed": refreshed}


def column_infos(ds_id: str) -> list[tuple[str, str, str]]:
    """(code, unit, plain-language meaning) for the dataset's columns."""
    seen = []
    metas = {m["code"]: m for m in load_indicators(ds_id)}
    codes = REGISTRY[ds_id]["indicators"] or sorted(metas)
    for code in codes:
        if code in MEANINGS:
            unit, meaning = MEANINGS[code]
        else:
            meta = metas.get(code, {})
            name = meta.get("name") or code
            unit = "% GDP" if "PC_GDP" in code else ""
            meaning = name if name != code else "Eurostat education spend series"
        seen.append((code, unit, meaning))
    return seen
