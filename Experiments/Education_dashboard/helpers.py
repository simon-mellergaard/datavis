from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def to_num(series: pd.Series) -> pd.Series:
    """Convert a string column with commas to numerics."""
    return pd.to_numeric(
        series.astype(str).str.replace(",", ".", regex=False),
        errors="coerce",
    )


def norm_udbud(value):
    try:
        return str(int(value))
    except Exception:
        return str(value)


def parse_ref(raw):
    if pd.isna(raw):
        return None
    text = str(raw)
    if ":" not in text:
        return None
    artikel, udbud = text.split(":", 1)
    return artikel.strip(), norm_udbud(udbud.strip())


def mode_str(series: pd.Series) -> str:
    values = series.dropna().astype(str)
    return values.value_counts().idxmax() if not values.empty else ""


def mean_fmt(series: pd.Series):
    values = to_num(series).dropna()
    return float(values.mean()) if not values.empty else None


MUNICIPALITY_COORDS: Dict[str, tuple[float, float]] = {
    "København": (55.6761, 12.5683),
    "Aarhus": (56.1629, 10.2039),
    "Odense": (55.4038, 10.4023),
    "Aalborg": (57.0488, 9.9217),
    "Esbjerg": (55.4767, 8.4520),
    "Roskilde": (55.6415, 12.0803),
    "Kolding": (55.4904, 9.4721),
}


def ensure_latlon_from_municipality(df_in: pd.DataFrame) -> pd.DataFrame:
    """Fill missing lat/lon using municipality centroids."""
    frame = df_in.copy()
    if "inst_lat" not in frame.columns:
        frame["inst_lat"] = np.nan
    if "inst_lon" not in frame.columns:
        frame["inst_lon"] = np.nan

    if "instkommunetx" not in frame.columns:
        return frame

    missing = frame["inst_lat"].isna() | frame["inst_lon"].isna()
    for idx in frame[missing].index:
        muni = frame.at[idx, "instkommunetx"]
        if pd.isna(muni):
            continue
        coords = MUNICIPALITY_COORDS.get(str(muni))
        if not coords:
            continue
        lat, lon = coords
        if pd.isna(frame.at[idx, "inst_lat"]):
            frame.at[idx, "inst_lat"] = lat
        if pd.isna(frame.at[idx, "inst_lon"]):
            frame.at[idx, "inst_lon"] = lon
    return frame
