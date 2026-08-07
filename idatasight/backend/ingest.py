"""Ingestion — live re-fetch of a dataset panel from its source API.

Ported from BetaThon scripts/run_five_datasets.py (World Bank fetcher and the
Eurostat JSON-stat parser). Refresh rewrites data/warehouse/<ds>/ and returns
the new row count; the engine then re-runs every remembered belief.
"""

from __future__ import annotations

import csv
import json
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .warehouse import REGISTRY, WAREHOUSE

API = "https://api.worldbank.org/v2"
try:  # uv-managed Pythons ship without macOS system certs
    import certifi

    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl.create_default_context()
UA = {"User-Agent": "iDataSight-Refresh/1.0 (research)"}

COUNTRIES = [
    "US", "CA", "MX", "BR", "AR", "GB", "DE", "FR", "IT", "ES", "NL", "SE", "PL",
    "CN", "JP", "KR", "IN", "ID", "AU", "ZA", "NG", "EG", "TR", "SA", "RU", "SG",
    "VN", "CL", "CO",
]
DATE = "2010:2023"

EUROSTAT_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
    "educ_uoe_fine06?format=JSON&lang=en"
    "&geo=DE&geo=FR&geo=IT&geo=ES&geo=NL&geo=SE&geo=PL&geo=AT&geo=BE&geo=FI"
    "&geo=IE&geo=PT&geo=DK&geo=CZ&geo=HU&geo=RO&geo=BG&geo=EL&geo=HR&geo=SK"
    "&unit=PC_GDP"
    "&time=2010&time=2011&time=2012&time=2013&time=2014&time=2015"
    "&time=2016&time=2017&time=2018&time=2019&time=2020&time=2021&time=2022"
)


def _http_json(url: str, retries: int = 3):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90, context=CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            last = e
            time.sleep(0.8 * (i + 1))
    raise RuntimeError(f"GET failed {url}: {last}")


def _chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def _fetch_wb_indicator(code: str) -> list[dict]:
    rows = []
    for batch in _chunked(COUNTRIES, 15):
        codes = ";".join(batch)
        page, pages = 1, 1
        while page <= pages:
            url = (
                f"{API}/country/{codes}/indicator/{urllib.parse.quote(code)}"
                f"?date={DATE}&format=json&per_page=20000&page={page}"
            )
            data = _http_json(url)
            if not isinstance(data, list) or not data:
                break
            meta = data[0] or {}
            if isinstance(meta, dict) and meta.get("message"):
                break
            pages = int(meta.get("pages") or 1)
            page_rows = data[1] if len(data) > 1 else None
            if not page_rows:
                break
            for r in page_rows:
                country = r.get("country") or {}
                try:
                    year = int(r.get("date"))
                except (TypeError, ValueError):
                    continue
                rows.append(
                    {
                        "country": country.get("value") or "",
                        "iso2": country.get("id") or "",
                        "iso3": r.get("countryiso3code") or "",
                        "year": year,
                        "indicator_code": code,
                        "value": r.get("value"),
                    }
                )
            page += 1
            time.sleep(0.2)
        time.sleep(0.25)
    return rows


def _fetch_eurostat() -> list[dict]:
    data = _http_json(EUROSTAT_URL)
    dim = data.get("dimension") or {}
    size = data.get("size") or []
    id_order = data.get("id") or list(dim.keys())
    values = data.get("value") or {}
    cats, labels = {}, {}
    for dname in id_order:
        cat = (dim.get(dname) or {}).get("category") or {}
        index = cat.get("index") or {}
        if isinstance(index, dict):
            pos_to_code = {int(v): k for k, v in index.items()}
        else:
            pos_to_code = {i: str(v) for i, v in enumerate(index)}
        cats[dname] = pos_to_code
        labels[dname] = cat.get("label") or {}

    def unravel(flat: int) -> dict:
        coords, rem = {}, flat
        for dname, n in zip(reversed(id_order), reversed(size)):
            n = int(n)
            coords[dname] = cats[dname].get(rem % n, str(rem % n))
            rem //= n
        return coords

    obs = []
    for k, v in values.items():
        try:
            coords = unravel(int(k))
        except ValueError:
            continue
        geo = coords.get("geo") or ""
        time_s = coords.get("time") or coords.get("TIME_PERIOD") or ""
        isced = coords.get("isced11") or coords.get("isced97") or "ALL"
        unit = coords.get("unit") or "PC_GDP"
        try:
            year = int(str(time_s)[:4])
        except ValueError:
            continue
        obs.append(
            {
                "country": (labels.get("geo") or {}).get(geo, geo),
                "iso2": geo,
                "iso3": geo,
                "year": year,
                "indicator_code": f"EDU_EXP_{unit}_{isced}",
                "value": float(v) if v is not None else None,
            }
        )
    return obs


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def refresh(ds_id: str) -> dict:
    """Re-pull the dataset's panel; returns counts for the refresh note."""
    prev = len(list(csv.DictReader((WAREHOUSE / ds_id / "observations.csv").open())))

    if ds_id == "eurostat_edu_fin":
        obs = _fetch_eurostat()
    else:
        obs = []
        for code in REGISTRY[ds_id]["indicators"]:
            obs.extend(_fetch_wb_indicator(code))

    if not obs:
        raise RuntimeError("source returned no observations — keeping current panel")

    _write_csv(
        WAREHOUSE / ds_id / "observations.csv",
        ["country", "iso2", "iso3", "year", "indicator_code", "value"],
        obs,
    )
    manifest = WAREHOUSE / ds_id / "manifest.json"
    body = json.loads(manifest.read_text()) if manifest.exists() else {}
    body["pulled_at"] = datetime.now(timezone.utc).isoformat()
    manifest.write_text(json.dumps(body, indent=2))
    non_null = sum(1 for r in obs if r.get("value") not in (None, ""))
    return {"rows": len(obs), "non_null": non_null, "delta": len(obs) - prev}
