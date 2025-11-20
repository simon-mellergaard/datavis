from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple, TYPE_CHECKING

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html

from .helpers import (
    ensure_latlon_from_municipality,
    mean_fmt,
    mode_str,
    norm_udbud,
    parse_ref,
    to_num,
)
from .theme import CUSTOM_BG, CUSTOM_CARD, FONT_COL, PLOT_BG

if TYPE_CHECKING:  # avoid circular import during runtime
    from .data_loader import DataBundle

DETAIL_GROUPS = {
    "Undervisningsform": [
        "undervisningsform_p1",
        "undervisningsform_p2",
        "undervisningsform_p3",
        "undervisningsform_p4",
        "undervisningsform_p5",
    ],
    "Jobskabende": [
        "jobskabende_p1",
        "jobskabende_p2",
        "jobskabende_p3",
        "jobskabende_p4",
        "jobskabende_p5",
    ],
    "Kompetencer (udd.)": [
        "kompetencerudd_p1",
        "kompetencerudd_p2",
        "kompetencerudd_p3",
        "kompetencerudd_p4",
        "kompetencerudd_p5",
    ],
}
DETAIL_NUMERIC = ["kvote_1_kvotient", "standby_8"]

PARCOORD_VARIABLES = [
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
    "arbejdstid_timer",
    "ledighed_nyudd",
    "maanedloen_nyudd",
    "maanedloen_10aar",
]
PARCOORD_DEFAULT_VARS = PARCOORD_VARIABLES[:5]
PARCOORD_LIKERT_COLUMNS = {
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
}

COLOR_PALETTE = [
    "#d62728",
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
]
PARCOORD_LABELS: Dict[str, str] = {
    "fagligmiljo_likert": "Fagligt miljø",
    "arbmedstud_likert": "Arbejde med studier",
    "medstuderende_likert": "Medstuderende",
    "udbytte_undervisning_likert": "Udbytte af undervisning",
    "socialtmiljo_likert": "Socialt miljø",
    "ensom_likert": "Ensomhed",
    "stress_daglig_likert": "Stress",
    "tilpas_likert": "Trives",
    "undervisere_engagerede_likert": "Undervisere engagerede",
    "undervisere_feedback_likert": "Feedback",
    "undervisere_hjaelp_likert": "Hjælp fra undervisere",
    "undervisere_kontakt_likert": "Kontakt til undervisere",
    "afbrud": "Afbrud (%)",
    "tidsforbrug_p50": "Tidsforbrug (timer)",
    "tidsforbrug_arbejde": "Tidsforbrug arbejde",
    "arbejdstid_timer": "Arbejdstid (timer)",
    "ledighed_nyudd": "Ledighed nyudd.",
    "maanedloen_nyudd": "Løn (nyudd.)",
    "maanedloen_10aar": "Løn (10 år)",
}


def bar_colors(n: int) -> Sequence[str]:
    steps = [i / (n - 1) if n > 1 else 0 for i in range(max(n, 1))]
    return px.colors.sample_colorscale(px.colors.sequential.Blues_r, steps)


def build_color_map_for_selected(
    selected_titles: Iterable[str],
    previous_map: Dict[str, str] | None = None,
) -> Dict[str, str]:
    selected_list = [t for t in selected_titles if t]
    cmap = dict(previous_map or {})
    next_idx = len(cmap)
    for title in selected_list:
        if title not in cmap:
            cmap[title] = COLOR_PALETTE[next_idx % len(COLOR_PALETTE)]
            next_idx += 1
    return cmap


def build_parcoord_legend(selected_titles: Iterable[str], color_map: Dict[str, str]) -> html.Div:
    titles = [t for t in selected_titles if t]
    if not titles:
        return html.Div(
            "Ingen uddannelser valgt endnu.",
            style={"color": "#adb5c6", "fontStyle": "italic", "fontSize": "14px"},
        )

    items = []
    for title in titles:
        swatch = html.Div(
            style={
                "width": "16px",
                "height": "16px",
                "borderRadius": "4px",
                "backgroundColor": color_map.get(title, "#f8f9fa"),
                "marginRight": "8px",
            }
        )
        label = html.Span(title, style={"color": FONT_COL, "fontSize": "14px"})
        items.append(html.Div([swatch, label], style={"display": "flex", "alignItems": "center"}))

    return html.Div(items, style={"display": "flex", "flexWrap": "wrap", "gap": "12px"})


def build_flow_df(data: DataBundle, selected_bachelors: Iterable[str]) -> pd.DataFrame:
    selected = [b for b in selected_bachelors if b]
    if not selected:
        return pd.DataFrame(
            columns=[
                "bachelor",
                "kandidat",
                "weight",
                "ledighed_nyudd",
                "maanedloen_nyudd",
                "maanedloen_10aar",
            ]
        )

    rows = []
    rank_weights = {"hyppigsteid1": 3, "hyppigsteid2": 2, "hyppigsteid3": 1}
    for bachelor in selected:
        bachelor_row = data.df[
            (data.df["titel"] == bachelor)
            & (data.df["displaydocclass"] == "Bacheloruddannelse")
            & (data.df["udbud_id"] == 999999)
        ]
        if bachelor_row.empty:
            bachelor_row = data.df[
                (data.df["titel"] == bachelor)
                & (data.df["displaydocclass"] == "Bacheloruddannelse")
            ]
        if bachelor_row.empty:
            continue

        record = bachelor_row.iloc[0]
        pairs, weights = [], []

        if (
            "kandidat_refs" in data.df.columns
            and isinstance(record.get("kandidat_refs"), str)
            and record["kandidat_refs"].strip()
        ):
            for reference in record["kandidat_refs"].split("|"):
                reference = reference.strip()
                if ":" not in reference:
                    continue
                artikel, udbud = reference.split(":", 1)
                pairs.append((artikel.strip(), norm_udbud(udbud.strip())))
                weights.append(1)
        else:
            for col, weight in rank_weights.items():
                ref = parse_ref(record.get(col))
                if not ref:
                    continue
                pairs.append(ref)
                weights.append(weight)

        for (artikel, udbud), weight in zip(pairs, weights):
            key = (artikel, udbud)
            if key not in data.raw_lookup.index:
                continue
            target = data.raw_lookup.loc[key]
            if "Kandidat" not in str(target["displaydocclass"]):
                continue
            rows.append(
                {
                    "bachelor": bachelor,
                    "kandidat": str(target["titel"]).strip(),
                    "weight": weight,
                    "ledighed_nyudd": target.get("ledighed_nyudd", np.nan),
                    "maanedloen_nyudd": target.get("maanedloen_nyudd", np.nan),
                    "maanedloen_10aar": target.get("maanedloen_10aar", np.nan),
                }
            )

    flow = pd.DataFrame(rows)
    if flow.empty:
        return flow

    return (
        flow.groupby(["bachelor", "kandidat"], as_index=False)
        .agg(
            {
                "weight": "sum",
                "ledighed_nyudd": "mean",
                "maanedloen_nyudd": "mean",
                "maanedloen_10aar": "mean",
            }
        )
        .sort_values("weight", ascending=False)
    )


def build_sankey(
    data: DataBundle,
    flow: pd.DataFrame,
    selected_bachelors: Iterable[str],
    top_k: int = 20,
) -> go.Figure:
    if flow.empty:
        empty = go.Figure()
        empty.update_layout(
            template="plotly_dark",
            paper_bgcolor=CUSTOM_BG,
            plot_bgcolor=PLOT_BG,
            font_color=FONT_COL,
        )
        return empty

    top = (
        flow.groupby("kandidat", as_index=False)["weight"]
        .sum()
        .sort_values("weight", ascending=False)
    )
    keep = set(top["kandidat"].head(top_k))
    filtered = flow[flow["kandidat"].isin(keep)].copy()
    if filtered.empty:
        filtered = flow.copy()

    bachelors = list(dict.fromkeys([b for b in selected_bachelors if b]))
    kandidater = sorted(filtered["kandidat"].unique())
    labels = bachelors + kandidater
    index_map = {label: idx for idx, label in enumerate(labels)}

    sources = [index_map[row["bachelor"]] for _, row in filtered.iterrows()]
    targets = [index_map[row["kandidat"]] for _, row in filtered.iterrows()]
    values = [row["weight"] for _, row in filtered.iterrows()]

    left_colors = (
        px.colors.sample_colorscale(
            px.colors.sequential.Blues_r,
            [i / max(1, len(bachelors) - 1) for i in range(len(bachelors))],
        )
        if bachelors
        else []
    )
    right_colors = (
        px.colors.sample_colorscale(
            px.colors.sequential.Blues,
            [i / max(1, len(kandidater) - 1) for i in range(len(kandidater))],
        )
        if kandidater
        else []
    )

    custom = np.c_[
        filtered["ledighed_nyudd"],
        filtered["maanedloen_nyudd"],
        filtered["maanedloen_10aar"],
    ]
    hover = (
        "<b>%{source.label}</b> → <b>%{target.label}</b><br>"
        "Vægt: %{value:.0f}<br>"
        "Ledighed (nyudd.): %{customdata[0]:.1f}%<br>"
        "Løn (nyudd.): %{customdata[1]:.0f}<br>"
        "Løn (10 år): %{customdata[2]:.0f}<extra></extra>"
    )

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                label=labels,
                color=left_colors + right_colors,
                pad=12,
                thickness=16,
                line=dict(color="#2a2f3a", width=1),
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                customdata=custom,
                hovertemplate=hover,
            ),
        )
    )
    fig.update_layout(
        title="Flow chart: Bachelor → Kandidat (tykkelse = vægt)",
        template="plotly_dark",
        paper_bgcolor=CUSTOM_BG,
        plot_bgcolor=PLOT_BG,
        font_color=FONT_COL,
        margin=dict(t=50, l=10, r=20, b=20),
        height=480,
    )
    return fig


def build_detail_table(data: DataBundle, edu_title: str):
    providers = data.df_raw[
        (data.df_raw["titel"].astype(str) == str(edu_title))
        & (data.df_raw["udbud_id"] != 999999)
    ].copy()
    if providers.empty:
        providers = data.df_raw[data.df_raw["titel"].astype(str) == str(edu_title)].copy()

    strings = {
        label: mode_str(providers.get(col, pd.Series(dtype=object)))
        for col, label in [
            ("foerstejob1tx", "Første job #1"),
            ("foerstejob2tx", "Første job #2"),
            ("foerstejob3tx", "Første job #3"),
            ("foerstejob4tx", "Første job #4"),
        ]
    }

    numeric = {}
    for column in DETAIL_NUMERIC:
        if column in providers.columns:
            mean_value = mean_fmt(providers[column])
            if mean_value is not None:
                numeric[column] = mean_value

    rows = [html.Tr([html.Th("Uddannelse"), html.Td(edu_title)])]
    for key, value in numeric.items():
        label = "Kvote 1 kvotient" if key == "kvote_1_kvotient" else "Standby (8)"
        rows.append(html.Tr([html.Th(label), html.Td(f"{value:.2f}")]))
    if any(strings.values()):
        rows.append(
            html.Tr(
                [
                    html.Th("Første job (typisk)"),
                    html.Td(", ".join([s for s in strings.values() if s])),
                ]
            )
        )

    keep_cols = [
        "hovedinsttx",
        "instkommunetx",
        "instregiontx",
        "udbud_id",
        "artikel_id",
        "titel",
        "kvote_1_kvotient",
        "standby_8",
        "inst_lat",
        "inst_lon",
    ]
    keep_cols = [c for c in keep_cols if c in providers.columns]
    providers_small = providers[keep_cols].copy()

    table = html.Table(
        [html.Tbody(rows)],
        style={"width": "100%", "borderCollapse": "collapse"},
    )
    return table, providers_small


def build_providers_map(providers_df: pd.DataFrame) -> go.Figure:
    if providers_df.empty:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=CUSTOM_BG,
            plot_bgcolor=PLOT_BG,
            margin=dict(t=0, l=0, r=0, b=0),
            font_color=FONT_COL,
        )
        return fig

    providers_geo = ensure_latlon_from_municipality(providers_df)
    if "kvote_1_kvotient" in providers_geo.columns:
        providers_geo["kvote_num"] = to_num(providers_geo["kvote_1_kvotient"])
    if "standby_8" in providers_geo.columns:
        providers_geo["standby_num"] = to_num(providers_geo["standby_8"])

    providers_geo = providers_geo.dropna(subset=["inst_lat", "inst_lon"])
    if providers_geo.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Ingen koordinater og ingen kendt kommune-match.",
            showarrow=False,
            font=dict(color=FONT_COL, size=12),
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=CUSTOM_BG,
            plot_bgcolor=PLOT_BG,
            margin=dict(t=0, l=0, r=0, b=0),
            font_color=FONT_COL,
        )
        return fig

    hover_cols = [
        col
        for col in ["instkommunetx", "instregiontx", "titel", "kvote_num", "standby_num"]
        if col in providers_geo.columns
    ]
    fig = px.scatter_mapbox(
        providers_geo,
        lat="inst_lat",
        lon="inst_lon",
        hover_name="hovedinsttx",
        hover_data=hover_cols,
        zoom=6,
        height=520,
    )

    latitudes = providers_geo["inst_lat"].astype(float)
    longitudes = providers_geo["inst_lon"].astype(float)
    lat_span = float(latitudes.max() - latitudes.min()) if len(latitudes) else 0.0
    lon_span = float(longitudes.max() - longitudes.min()) if len(longitudes) else 0.0
    center_lat = float(latitudes.mean()) if len(latitudes) else 56.0
    center_lon = float(longitudes.mean()) if len(longitudes) else 10.5

    zoom = 6.0
    span = max(lat_span, lon_span)
    if span < 0.8:
        zoom = 7.5
    elif span > 6:
        zoom = 5.2

    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox=dict(center=dict(lat=center_lat, lon=center_lon), zoom=zoom),
        template="plotly_dark",
        paper_bgcolor=CUSTOM_BG,
        plot_bgcolor=PLOT_BG,
        font_color=FONT_COL,
        margin=dict(t=0, l=0, r=0, b=0),
    )
    return fig


TREEMAP_LEVELS = ["titel", "cluster_label", "educational_category"]


def build_hierarchical_dataframe(
    source_df: pd.DataFrame,
    levels: Sequence[str],
    value_column: str,
    color_column: str,
) -> pd.DataFrame:
    frames = []
    for idx, level in enumerate(levels):
        df_tree = pd.DataFrame(columns=["id", "label", "parent", "value", "color"])
        grouped = source_df.groupby(levels[idx:]).sum(numeric_only=True)
        grouped["tmp"] = source_df.groupby(levels[idx:]).count()[color_column]
        grouped = grouped.reset_index()

        df_tree["label"] = grouped[level].astype(str)
        df_tree["id"] = df_tree["label"]
        for j in range(idx + 1, len(levels)):
            df_tree["id"] = grouped[levels[j]].astype(str) + "/" + df_tree["id"]

        if idx < len(levels) - 1:
            parent = grouped[levels[idx + 1]].astype(str)
            j = idx + 1
            while j < len(levels) - 1:
                parent = grouped[levels[j + 1]].astype(str) + "/" + parent
                j += 1
            df_tree["parent"] = parent
        else:
            df_tree["parent"] = ""

        values = grouped[value_column].astype(float).to_numpy()
        counts = grouped["tmp"].astype(float).to_numpy()
        df_tree["value"] = values
        df_tree["color"] = np.divide(
            values,
            counts,
            out=np.zeros(len(values), dtype=float),
            where=counts != 0,
        )
        df_tree["level"] = level
        frames.append(df_tree)

    return pd.concat(frames, ignore_index=True)


def build_city_treemap(
    data: DataBundle,
    city_value: str,
    metric_key: str,
    selected_titles: Iterable[str] | None = None,
) -> go.Figure:
    metric = data.size_metrics.get(metric_key)
    if not metric:
        metric_key = next(iter(data.size_metrics.keys()))
        metric = data.size_metrics[metric_key]
    metric_col, how, metric_label = metric

    if city_value and city_value != "__ALL__":
        df_sel = data.df_prov[data.df_prov["instkommunetx"] == city_value].copy()
    else:
        df_sel = data.df_prov.copy()

    df_sel = df_sel.dropna(subset=["educational_category", "cluster_label", "titel"])
    df_sel = df_sel[~df_sel[metric_col].isna()]

    if df_sel.empty:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=CUSTOM_BG,
            plot_bgcolor=PLOT_BG,
            font_color=FONT_COL,
            margin=dict(t=30, l=20, r=20, b=20),
        )
        fig.add_annotation(
            text="Ingen data for valgte filter.",
            showarrow=False,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            font=dict(color=FONT_COL),
        )
        return fig

    df_sel = df_sel.drop_duplicates()
    if how == "sum":
        grouped = (
            df_sel.groupby(["educational_category", "cluster_label", "titel"], as_index=False)[metric_col]
            .sum()
            .rename(columns={metric_col: "size"})
        )
    else:
        grouped = (
            df_sel.groupby(["educational_category", "cluster_label", "titel"], as_index=False)[metric_col]
            .mean()
            .rename(columns={metric_col: "size"})
        )

    grouped = grouped[np.isfinite(grouped["size"])]
    grouped = grouped[grouped["size"] > 0]
    if grouped.empty:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=CUSTOM_BG,
            plot_bgcolor=PLOT_BG,
            font_color=FONT_COL,
            margin=dict(t=30, l=20, r=20, b=20),
        )
        fig.add_annotation(
            text="Ingen data for valgte filter.",
            showarrow=False,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            font=dict(color=FONT_COL),
        )
        return fig

    title_txt = f"{metric_label} - " + (city_value if city_value != "__ALL__" else "Alle kommuner")
    df_new = build_hierarchical_dataframe(grouped, TREEMAP_LEVELS, "size", "size")

    selected_titles = set(selected_titles or [])
    base_colors = df_new["color"].astype(float)
    min_val = float(base_colors.min()) if len(base_colors) else 0.0
    max_val = float(base_colors.max()) if len(base_colors) else 1.0
    span = max(max_val - min_val, 1e-9)
    norm = (base_colors - min_val) / span
    text_colors = np.where(norm > 0.35, "#f8f9ff", "#11151b")

    selected_mask = (df_new["level"] == "titel") & df_new["label"].isin(selected_titles)
    color_values = base_colors.copy()
    marker_colorscale = px.colors.sequential.Blues
    marker_cmin = min_val
    marker_cmax = max_val

    if selected_mask.any():
        text_colors = np.array(text_colors, copy=True)
        text_colors[selected_mask] = "#ced4da"

        epsilon = max(span * 1e-6, 1e-9)
        near_min_mask = (~selected_mask) & np.isclose(color_values, min_val)
        color_values[near_min_mask] = color_values[near_min_mask] + epsilon
        color_values[selected_mask] = min_val

        grey_break = min(max(epsilon / span, 1e-4), 0.05)
        scaled = [[0.0, "#6c757d"], [grey_break, "#6c757d"]]
        blues = px.colors.sequential.Blues
        if len(blues) == 1:
            scaled.append([1.0, blues[0]])
        else:
            for idx, color in enumerate(blues):
                t = idx / (len(blues) - 1)
                mapped = grey_break + (1 - grey_break) * t
                scaled.append([mapped, color])
        marker_colorscale = scaled

    hover_text = (
        f"<b>%{{label}}</b><br>{metric_label}: %{{value:,.0f}}<br>"
        "%{percentParent:.1%} af niveauet over<br>"
        "%{percentEntry:.1%} af totalen<extra></extra>"
    )

    marker_dict = dict(
        colors=color_values,
        colorscale=marker_colorscale,
        colorbar=dict(
            title=dict(text=metric_label, font=dict(color=FONT_COL)),
            tickfont=dict(color=FONT_COL),
            outlinecolor="#2a2f3a",
        ),
    )
    marker_dict["cmin"] = marker_cmin
    marker_dict["cmax"] = marker_cmax

    fig = go.Figure(
        go.Treemap(
            ids=df_new["id"],
            labels=df_new["label"],
            parents=df_new["parent"],
            values=df_new["value"],
            branchvalues="total",
            marker=marker_dict,
            texttemplate=f"<b>%{{label}}</b><br>{metric_label}: %{{value:,.0f}}<br>%{{percentParent:.1%}}",
            textfont=dict(color=text_colors),
            hovertemplate=hover_text,
            maxdepth=3,
            name="",
        )
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=CUSTOM_BG,
        plot_bgcolor=PLOT_BG,
        font_color=FONT_COL,
        margin=dict(t=50, l=30, r=50, b=20),
        title=title_txt,
    )
    fig.update_traces(root_color="#1c1f26")
    return fig


def build_parallel_coordinates(
    data: DataBundle,
    selected_titles: Iterable[str],
    slider_filter: Dict[str, Sequence[float]],
    selected_vars: Iterable[str],
    color_map: Dict[str, str],
) -> go.Figure:
    df = data.df.copy().dropna(subset=["titel"])
    columns = [col for col in selected_vars if col in df.columns]
    if not columns:
        fig = go.Figure()
        fig.add_annotation(
            text="Ingen variabler valgt til parallelkoordinater.",
            showarrow=False,
            font=dict(color=FONT_COL),
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=CUSTOM_BG,
            plot_bgcolor=PLOT_BG,
            font_color=FONT_COL,
            margin=dict(t=20, l=20, r=20, b=20),
            height=560,
        )
        return fig

    df = df.dropna(subset=columns)
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Ingen data til de valgte variabler.",
            showarrow=False,
            font=dict(color=FONT_COL),
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=CUSTOM_BG,
            plot_bgcolor=PLOT_BG,
            font_color=FONT_COL,
            margin=dict(t=20, l=20, r=20, b=20),
            height=560,
        )
        return fig
    selected_list = [t for t in selected_titles if t]
    slider_active = bool(slider_filter)
    numeric_line_values: List[float] = []
    for _, row in df.iterrows():
        title = row["titel"]
        if title in selected_list:
            numeric_line_values.append(selected_list.index(title) + 1)
            continue
        if slider_active:
            matches = True
            for col, (low, high) in slider_filter.items():
                if col not in row or pd.isna(row[col]):
                    matches = False
                    break
                value = float(row[col])
                if value < low or value > high:
                    matches = False
                    break
            numeric_line_values.append(0.5 if matches else 0.0)
        else:
            numeric_line_values.append(0.0)

    dimensions = []
    for col in columns:
        values = df[col].astype(float)
        if col in PARCOORD_LIKERT_COLUMNS:
            dim_range = [1, 5]
        else:
            dim_range = [float(values.min()), float(values.max())]
            if np.isclose(dim_range[0], dim_range[1]):
                dim_range[1] = dim_range[0] + 1.0
        dimension = dict(
            range=dim_range,
            label=PARCOORD_LABELS.get(col, col),
            values=values,
        )
        if col in slider_filter:
            dimension["constraintrange"] = slider_filter[col]
        dimensions.append(dimension)

    count_selected = len(selected_list)
    cmin = 0.0
    cmax = max(1.0, float(count_selected) or 1.0)
    colorscale: List[List[float | str]] = [[0.0, "#E8E8E8"], [1.0, "#E8E8E8"]]
    if slider_active:
        colorscale.insert(1, [0.5 / cmax, "#87CEFA"])
    if count_selected:
        for idx, title in enumerate(selected_list, start=1):
            pos = float(idx) / cmax
            colorscale.insert(-1, [pos, color_map.get(title, "#E8E8E8")])

    fig = go.Figure(
        go.Parcoords(
            line=dict(
                color=numeric_line_values,
                colorscale=colorscale,
                cmin=cmin,
                cmax=cmax,
                showscale=False,
            ),
            dimensions=dimensions,
            ids=df["titel"].astype(str),
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=CUSTOM_BG,
        plot_bgcolor=PLOT_BG,
        font_color=FONT_COL,
        margin=dict(t=30, l=40, r=20, b=30),
        height=560,
    )
    return fig


def build_parcoord_sliders(
    data: DataBundle,
    selected_vars: Iterable[str],
    previous_values: Dict[str, Sequence[float]],
) -> Tuple[List[html.Div], Dict[str, Sequence[float]]]:
    components: List[html.Div] = []
    slider_filter: Dict[str, Sequence[float]] = {}
    df = data.df

    for col in selected_vars:
        if col not in df.columns:
            continue
        if col in PARCOORD_LIKERT_COLUMNS:
            min_val, max_val = 1.0, 5.0
            step = 0.1
            marks = {i: str(i) for i in range(1, 6)}
            default = [5.0, 5.0]
        else:
            series = df[col].dropna().astype(float)
            if series.empty:
                continue
            min_val = float(series.min())
            max_val = float(series.max())
            if np.isclose(min_val, max_val):
                max_val = min_val + 1.0
            step = max((max_val - min_val) / 100.0, 1e-2)
            ticks = np.linspace(min_val, max_val, num=4)
            marks = {float(f"{t:.0f}"): f"{t:.0f}" for t in ticks}
            default = [max_val, max_val]

        current = list(previous_values.get(col, default))
        slider = dcc.RangeSlider(
            id={"type": "parcoord-slider", "column": col},
            min=min_val,
            max=max_val,
            step=step,
            value=current,
            marks=marks,
            tooltip={"placement": "bottom", "always_visible": False},
            allowCross=False,
        )
        components.append(
            html.Div(
                [html.Label(PARCOORD_LABELS.get(col, col)), slider],
                style={"marginBottom": "16px"},
            )
        )
        if current != default:
            slider_filter[col] = current

    return components, slider_filter
