from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

from helpers import norm_udbud, parse_ref, to_num


@dataclass
class DataBundle:
    df_raw: pd.DataFrame
    df: pd.DataFrame
    df_prov: pd.DataFrame
    mapping: pd.DataFrame
    city_options: List[dict]
    size_options: List[dict]
    size_metrics: Dict[str, Tuple[str, str, str]]
    available_titles: List[str]
    available_options: List[dict]
    available_set: set[str]
    bachelor_titles_multi: List[str]
    radar_vars: Sequence[Tuple[str, str]]
    radar_bounds: Tuple[float, float]
    raw_lookup: pd.DataFrame


BASE_DIR = Path(__file__).resolve().parents[1]  # .../datavis
DATA_DIR = BASE_DIR / "Data"
DATA_FILE = DATA_DIR / "DATA_UFM_combined_TEST_AREA_filled_V2.xlsx"
CLUSTER_FILE = DATA_DIR / "education_cluster_mapping.xlsx"

RADAR_VARS = [
    ("fagligmiljo_likert", "Fagligt miljø"),
    ("socialtmiljo_likert", "Socialt miljø"),
    ("stress_daglig_likert", "Stress"),
    ("ensom_likert", "Ensomhed"),
    ("ruster_til_job_likert", "Ruster til job"),
]

SIZE_METRICS = {
    "optagne": ("optagne_num", "sum", "Optagne (sum)"),
    "maanedloen_nyudd": ("maanedloen_nyudd_n", "mean", "Løn (nyudd.) (gennemsnit)"),
    "ledighed_nyudd": ("ledighed_nyudd_n", "mean", "Ledighed (nyudd.) (gennemsnit)"),
}


def _backfill_kandidat(df: pd.DataFrame, df_raw: pd.DataFrame) -> pd.DataFrame:
    if "kandidat_titler" in df.columns and "kandidat_refs" in df.columns:
        return df

    ref_src = df_raw.copy()
    ref_src["artikel_id"] = ref_src["artikel_id"].astype(str)
    ref_src["udbud_id_str"] = ref_src["udbud_id"].apply(norm_udbud)
    ref_index = ref_src.set_index(["artikel_id", "udbud_id_str"])

    titles_out, refs_out = [], []
    for _, row in df.iterrows():
        titles, refs = [], []
        for col in ["hyppigsteid1", "hyppigsteid2", "hyppigsteid3"]:
            reference = parse_ref(row.get(col))
            if not reference or reference not in ref_index.index:
                continue
            record = ref_index.loc[reference]
            if "Kandidat" not in str(record["displaydocclass"]):
                continue
            title = str(record["titel"]).strip()
            key = f"{reference[0]}:{reference[1]}"
            if title and title not in titles:
                titles.append(title)
            if key not in refs:
                refs.append(key)
        titles_out.append(" | ".join(titles))
        refs_out.append(" | ".join(refs))

    df = df.copy()
    df["kandidat_titler"] = titles_out
    df["kandidat_refs"] = refs_out
    return df


def _radar_bounds(df: pd.DataFrame) -> Tuple[float, float]:
    values = []
    for col, _ in RADAR_VARS:
        if col in df.columns:
            arr = df[col].values
            values.append(arr[~pd.isna(arr)])
    if not values:
        return 1.0, 5.0
    concat = np.concatenate(values)
    lower = float(np.nanmax([1, np.nanmin(concat)]))
    upper = float(np.nanmin([5, np.nanmax(concat)]))
    if lower >= upper:
        return 1.0, 5.0
    return lower, upper


def load_data(
    data_file: Path | None = None,
    mapping_file: Path | None = None,
) -> DataBundle:
    data_path = data_file or DATA_FILE
    mapping_path = mapping_file or CLUSTER_FILE

    df_raw = pd.read_excel(data_path, header=0)
    cols = [
        "artikel_id",
        "udbud_id",
        "titel",
        "educational_category",
        "displaydocclass",
        "hovedinsttx",
        "instregiontx",
        "instkommunetx",
        "optagne",
        "kvote_1_kvotient",
        "standby_8",
        "fagligmiljo_likert",
        "arbmedstud_likert",
        "medstuderende_likert",
        "udbytte_undervisning_likert",
        "socialtmiljo_likert",
        "ensom_likert",
        "stress_daglig_likert",
        "tilpas_likert",
        "undervisere_engagerede_likert",
        "undervisere_feedback_likert",
        "undervisere_hjaelp_likert",
        "undervisere_kontakt_likert",
        "afbrud",
        "tidsforbrug_p50",
        "tidsforbrug_arbejde",
        "uddaktivitet_opgaver_pct",
        "uddaktivitet_praktik_pct",
        "uddaktivitet_udlandsophold_pct",
        "uddaktivitet_undervisning_pct",
        "undervisningsform_p1",
        "undervisningsform_p2",
        "undervisningsform_p3",
        "undervisningsform_p4",
        "undervisningsform_p5",
        "foerstejob1tx",
        "foerstejob2tx",
        "foerstejob3tx",
        "foerstejob4tx",
        "jobskabende_p1",
        "jobskabende_p2",
        "jobskabende_p3",
        "jobskabende_p4",
        "jobskabende_p5",
        "kompetencerudd_p1",
        "kompetencerudd_p2",
        "kompetencerudd_p3",
        "kompetencerudd_p4",
        "kompetencerudd_p5",
        "ledighed_nyudd",
        "ledighed_10aar",
        "maanedloen_nyudd",
        "maanedloen_10aar",
        "hyppigsteid1",
        "hyppigsteid2",
        "hyppigsteid3",
        "kandidat_titler",
        "kandidat_refs",
        "cluster_label",
        "inst_lat",
        "inst_lon",
    ]
    keep_cols = [c for c in cols if c in df_raw.columns]
    data = df_raw[keep_cols].copy()

    mapping = pd.read_excel(mapping_path)
    mapping["titel"] = mapping["titel"].astype(str).str.strip()

    national = data[data["udbud_id"] == 999999].copy()
    national["titel"] = national["titel"].astype(str).str.strip()
    national = national.merge(mapping, on="titel", how="left").drop_duplicates("titel")

    df = national.dropna(subset=["titel"]).copy()
    df["titel"] = df["titel"].astype(str).str.strip()
    df = _backfill_kandidat(df, df_raw)

    df_prov = data[data["udbud_id"] != 999999].copy()
    df_prov["titel"] = df_prov["titel"].astype(str).str.strip()
    df_prov = df_prov.merge(mapping, on="titel", how="left")
    df_prov["optagne_num"] = to_num(df_prov.get("optagne"))
    df_prov["maanedloen_nyudd_n"] = to_num(df_prov.get("maanedloen_nyudd"))
    df_prov["ledighed_nyudd_n"] = to_num(df_prov.get("ledighed_nyudd"))

    # View without kandidat programmes (for visuals and dropdowns; dataset remains intact).
    mask_non_kandidat = ~df_prov["displaydocclass"].astype(str).str.contains("kandidat", case=False, na=False)
    df_prov_no_kandidat = df_prov[mask_non_kandidat].copy()

    excluded_cities = {
        "ballerup",
        "bornholm",
        "brøndby",
        "faaborg-midtfyn",
        "guldborgsund",
        "hedensted",
        "ikast-brande",
        "lemvig",
        "mariagerfjord",
        "norddjurs",
        "rudersdal",
        "vordingborg",
        "ærø",
        "uoplyst/ukendt"
    }
    city_list = sorted(
        city
        for city in df_prov["instkommunetx"].dropna().astype(str).str.strip().unique()
        if city.lower() not in excluded_cities
    )
    city_options = (
        [{"label": "Alle kommuner", "value": "__ALL__"}]
        + [{"label": city, "value": city} for city in city_list]
    )
    size_options = [{"label": v[2], "value": k} for k, v in SIZE_METRICS.items()]

    available_titles = sorted(
        df_prov_no_kandidat.dropna(subset=["educational_category", "cluster_label", "titel"])["titel"]
        .dropna()
        .astype(str)
        .unique()
    )
    available_options = [{"label": t, "value": t} for t in available_titles]
    available_set = set(available_titles)

    df = df[df["titel"].isin(available_set)].copy()

    bachelor_titles = sorted(
        set(
            df.loc[
                (df["displaydocclass"] == "Bacheloruddannelse")
                & (df["udbud_id"] == 999999),
                "titel",
            ]
            .dropna()
            .astype(str)
            .unique()
        )
        & available_set
    )

    rad_bounds = _radar_bounds(df)

    df_raw_lu = df_raw.copy()
    df_raw_lu["artikel_id"] = df_raw_lu["artikel_id"].astype(str)
    df_raw_lu["udbud_id_str"] = df_raw_lu["udbud_id"].apply(norm_udbud)
    raw_lookup = df_raw_lu.set_index(["artikel_id", "udbud_id_str"])

    return DataBundle(
        df_raw=df_raw,
        df=df,
        df_prov=df_prov,
        mapping=mapping,
        city_options=city_options,
        size_options=size_options,
        size_metrics=SIZE_METRICS,
        available_titles=available_titles,
        available_options=available_options,
        available_set=available_set,
        bachelor_titles_multi=bachelor_titles,
        radar_vars=RADAR_VARS,
        radar_bounds=rad_bounds,
        raw_lookup=raw_lookup,
    )
