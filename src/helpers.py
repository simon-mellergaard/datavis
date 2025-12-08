from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def to_num(series: pd.Series) -> pd.Series:
    """Convert a string column with commas to numerics."""
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce")


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


# Municipality centroids (covers all 46 municipalities present in the dataset)
MUNICIPALITY_COORDS: Dict[str, tuple[float, float]] = {
    "Aabenraa": (55.0443, 9.4174),
    "Aalborg": (57.0488, 9.9217),
    "Aarhus": (56.1629, 10.2039),
    "Ballerup": (55.7316, 12.3633),
    "Bornholm": (55.1007, 14.7067),
    "Brøndby": (55.6436, 12.4345),
    "Esbjerg": (55.4767, 8.4584),
    "Faaborg-Midtfyn": (55.0958, 10.2416),
    "Fredericia": (55.5657, 9.7526),
    "Frederiksberg": (55.6797, 12.5344),
    "Frederikshavn": (57.4407, 10.5366),
    "Guldborgsund": (54.7691, 11.8743),
    "Haderslev": (55.2554, 9.4895),
    "Hedensted": (55.7705, 9.7011),
    "Herning": (56.1366, 8.9788),
    "Hillerød": (55.9276, 12.3000),
    "Hjørring": (57.4642, 10.0134),
    "Holbæk": (55.7184, 11.7120),
    "Holstebro": (56.3601, 8.6160),
    "Horsens": (55.8607, 9.8503),
    "Ikast-Brande": (56.1382, 9.1573),
    "Kalundborg": (55.6850, 11.0890),
    "Kolding": (55.4904, 9.4722),
    "København": (55.6761, 12.5683),
    "Køge": (55.4580, 12.1821),
    "Lemvig": (56.5486, 8.3074),
    "Lyngby-Taarbæk": (55.7700, 12.5038),
    "Mariagerfjord": (56.6427, 9.7906),
    "Norddjurs": (56.4146, 10.8871),
    "Næstved": (55.2299, 11.7609),
    "Odense": (55.4038, 10.4024),
    "Randers": (56.4607, 10.0364),
    "Roskilde": (55.6415, 12.0803),
    "Rudersdal": (55.8237, 12.4805),
    "Silkeborg": (56.1836, 9.5560),
    "Skive": (56.5662, 9.0277),
    "Slagelse": (55.4028, 11.3546),
    "Svendborg": (55.0598, 10.6068),
    "Sønderborg": (54.9093, 9.8074),
    "Thisted": (56.9550, 8.6949),
    "Tønder": (54.9335, 8.8667),
    "Vejle": (55.7113, 9.5364),
    "Viborg": (56.4500, 9.4020),
    "Vordingborg": (55.0090, 11.9101),
    "Ærø": (54.8881, 10.4099),
    "Fredericia ": (55.5657, 9.7526),  # occasional trailing-space variant in raw data
    "Horsens ": (55.8607, 9.8503),
}


def ensure_latlon_from_municipality(df_in: pd.DataFrame) -> pd.DataFrame:
    """Fill missing lat/lon using municipality centroids (or known provider coordinates)."""
    frame = df_in.copy()
    if "inst_lat" not in frame.columns:
        frame["inst_lat"] = np.nan
    if "inst_lon" not in frame.columns:
        frame["inst_lon"] = np.nan

    if "instkommunetx" not in frame.columns:
        return frame

    coords_map: Dict[str, tuple[float, float]] = dict(MUNICIPALITY_COORDS)
    if not frame.dropna(subset=["inst_lat", "inst_lon"]).empty:
        known = (
            frame.dropna(subset=["inst_lat", "inst_lon"])
            .groupby("instkommunetx")[["inst_lat", "inst_lon"]]
            .median()
            .reset_index()
        )
        for _, row in known.iterrows():
            coords_map[str(row["instkommunetx"])] = (float(row["inst_lat"]), float(row["inst_lon"]))

    missing = frame["inst_lat"].isna() | frame["inst_lon"].isna()
    for idx in frame[missing].index:
        muni = frame.at[idx, "instkommunetx"]
        if pd.isna(muni):
            continue
        coords = coords_map.get(str(muni))
        if not coords:
            continue
        lat, lon = coords
        if pd.isna(frame.at[idx, "inst_lat"]):
            frame.at[idx, "inst_lat"] = lat
        if pd.isna(frame.at[idx, "inst_lon"]):
            frame.at[idx, "inst_lon"] = lon
    return frame
