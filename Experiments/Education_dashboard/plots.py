from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple, TYPE_CHECKING

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html
from bokeh.embed import file_html
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.plotting import figure
from bokeh.resources import CDN

from .helpers import (
    ensure_latlon_from_municipality,
    mode_str,
    norm_udbud,
    parse_ref,
    to_num,
)
from .theme import DEFAULT_THEME, Theme

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
DETAIL_OVERVIEW_SPECS = [
    ("optagne", "Optagne", "sum", lambda v: f"{v:,.0f}"),
    ("kvote_1_kvotient", "Kvote 1 kvotient", "mean", lambda v: f"{v:.2f}"),
    ("standby_8", "Standby", "mean", lambda v: f"{v:.2f}"),
    ("afbrud", "Afbrud (%)", "mean", lambda v: f"{v:.1f}%"),
    ("tidsforbrug_p50", "Tidsforbrug (timer)", "mean", lambda v: f"{v:.1f}"),
    ("ledighed_nyudd", "Ledighed (nyudd.)", "mean", lambda v: f"{v:.1f}%"),
    ("ledighed_10aar", "Ledighed (10 år)", "mean", lambda v: f"{v:.1f}%"),
    ("maanedloen_nyudd", "Løn (nyudd.)", "mean", lambda v: f"{v:,.0f} kr"),
    ("maanedloen_10aar", "Løn (10 år)", "mean", lambda v: f"{v:,.0f} kr"),
]

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

TREEMAP_DRILL_METRICS = [
    ("maanedloen_nyudd", PARCOORD_LABELS["maanedloen_nyudd"]),
    ("ledighed_nyudd", PARCOORD_LABELS["ledighed_nyudd"]),
    ("stress_daglig_likert", PARCOORD_LABELS["stress_daglig_likert"]),
    ("tilpas_likert", PARCOORD_LABELS["tilpas_likert"]),
]


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


def build_parcoord_legend(selected_titles: Iterable[str], color_map: Dict[str, str], theme: Theme) -> html.Div:
    titles = [t for t in selected_titles if t]
    if not titles:
        return html.Div(
            "Ingen uddannelser valgt endnu.",
            style={"color": theme.muted_text, "fontStyle": "italic", "fontSize": "14px"},
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
        label = html.Span(title, style={"color": theme.font, "fontSize": "14px"})
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
    theme: Theme | None = None,
) -> go.Figure:
    theme = theme or DEFAULT_THEME
    if flow.empty:
        empty = go.Figure()
        empty.update_layout(
            template=theme.template,
            paper_bgcolor=theme.app_bg,
            plot_bgcolor=theme.plot_bg,
            font_color=theme.font,
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
                line=dict(color=theme.card_border, width=1),
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
        template=theme.template,
        paper_bgcolor=theme.app_bg,
        plot_bgcolor=theme.plot_bg,
        font_color=theme.font,
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

    overview = data.df[data.df["titel"].astype(str) == str(edu_title)]
    overview_row = overview.iloc[0] if not overview.empty else None

    strings = {
        label: mode_str(providers.get(col, pd.Series(dtype=object)))
        for col, label in [
            ("foerstejob1tx", "Første job #1"),
            ("foerstejob2tx", "Første job #2"),
            ("foerstejob3tx", "Første job #3"),
            ("foerstejob4tx", "Første job #4"),
        ]
    }

    def parse_single_value(value):
        series = pd.Series([value])
        numeric = to_num(series).iloc[0]
        return None if pd.isna(numeric) else float(numeric)

    def metric_value(column: str, how: str):
        if overview_row is not None and column in overview_row.index:
            val = parse_single_value(overview_row[column])
            if val is not None:
                return val
        if column in providers.columns:
            series = to_num(providers[column]).dropna()
            if series.empty:
                return None
            return float(series.sum()) if how == "sum" else float(series.mean())
        return None

    rows = [html.Tr([html.Th("Uddannelse"), html.Td(edu_title)])]
    for column, label, how, formatter in DETAIL_OVERVIEW_SPECS:
        value = metric_value(column, how)
        display = formatter(value) if value is not None else "N/A"
        rows.append(html.Tr([html.Th(label), html.Td(display)]))
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


def build_providers_map(providers_df: pd.DataFrame, theme: Theme | None = None) -> go.Figure:
    theme = theme or DEFAULT_THEME
    if providers_df.empty:
        fig = go.Figure()
        fig.update_layout(
            template=theme.template,
            paper_bgcolor=theme.app_bg,
            plot_bgcolor=theme.plot_bg,
            margin=dict(t=0, l=0, r=0, b=0),
            font_color=theme.font,
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
            font=dict(color=theme.font, size=12),
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
        )
        fig.update_layout(
            template=theme.template,
            paper_bgcolor=theme.app_bg,
            plot_bgcolor=theme.plot_bg,
            margin=dict(t=0, l=0, r=0, b=0),
            font_color=theme.font,
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
        template=theme.template,
        paper_bgcolor=theme.app_bg,
        plot_bgcolor=theme.plot_bg,
        font_color=theme.font,
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


def build_treemap_drill_chart(
    data: "DataBundle",
    edu_title: str,
    metric_key: str,
    city_value: str = "__ALL__",
    theme: Theme | None = None,
) -> go.Figure:
    theme = theme or DEFAULT_THEME
    df = data.df_prov[data.df_prov["titel"] == edu_title].copy()
    if city_value and city_value != "__ALL__":
        df = df[df["instkommunetx"] == city_value]
        # If we asked for a specific city but have no rows, return an empty chart instead of national fallback.
        if df.empty:
            empty = go.Figure()
            empty.update_layout(
                template=theme.template,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color=theme.font,
                margin=dict(t=10, l=10, r=10, b=10),
                height=160,
            )
            empty.add_annotation(
                text=f"Ingen data for {city_value}.",
                showarrow=False,
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                font=dict(color=theme.font, size=12),
            )
            return empty
    if df.empty:
        df = data.df[data.df["titel"] == edu_title].copy()
    if df.empty or metric_key not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            template=theme.template,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color=theme.font,
            margin=dict(t=10, l=10, r=10, b=10),
            height=200,
        )
        fig.add_annotation(
            text="Ingen data for valgte måling.",
            showarrow=False,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            font=dict(color=theme.font, size=12),
        )
        return fig

    df = df.dropna(subset=[metric_key])
    if df.empty:
        empty = go.Figure()
        empty.update_layout(
            template=theme.template,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color=theme.font,
            margin=dict(t=10, l=10, r=10, b=10),
            height=160,
        )
        empty.add_annotation(
            text="Ingen observationer for denne variabel.",
            showarrow=False,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            font=dict(color=theme.font, size=12),
        )
        return empty

    label = PARCOORD_LABELS.get(metric_key, metric_key)

    if city_value and city_value != "__ALL__":
        df["provider"] = df.get("hovedinsttx", pd.Series(["Udbyder"] * len(df))).fillna("Udbyder")
        df_plot = (
            df.groupby("provider", as_index=False)[metric_key]
            .mean()
            .sort_values(metric_key, ascending=False)
        )
        title_text = f"{label} - {city_value}"
        # National comparison bar
        nat_source = data.df_prov if metric_key in data.df_prov.columns else data.df
        nat_vals = pd.to_numeric(nat_source[metric_key], errors="coerce")
        nat_mean = float(nat_vals.mean()) if not nat_vals.dropna().empty else np.nan
        if not np.isnan(nat_mean):
            nat_row = pd.DataFrame({"provider": ["Nationalt gennemsnit"], metric_key: [nat_mean]})
            df_plot = pd.concat([df_plot, nat_row], ignore_index=True)
            # Ensure chosen providers stay left and national last
            df_plot["order_key"] = df_plot["provider"].apply(lambda x: 1 if x == "Nationalt gennemsnit" else 0)
            df_plot = df_plot.sort_values(["order_key", "provider"], ascending=[True, True])
    else:
        # National aggregation: single bar
        df_plot = (
            df.groupby("titel", as_index=False)[metric_key]
            .mean()
            .rename(columns={metric_key: "value"})
        )
        df_plot["provider"] = "Nationalt gennemsnit"
        df_plot[metric_key] = df_plot["value"]
        df_plot = df_plot[["provider", metric_key]]
        title_text = f"{label} - Nationalt"

    df_plot = df_plot.sort_values(metric_key, ascending=False).head(8)

    money_metrics = {"maanedloen_nyudd", "maanedloen_10aar"}
    likert_metrics = PARCOORD_LIKERT_COLUMNS
    if metric_key in money_metrics:
        value_col = "value_for_plot"
        df_plot[value_col] = df_plot[metric_key].astype(float) / 1000.0
        tick_format = ",.0f"
        tick_suffix = "k"
        x_title = f"{label} (t.kr)"
    elif metric_key in likert_metrics:
        value_col = metric_key
        tick_format = ".1f"
        tick_suffix = ""
        x_title = label
    else:
        value_col = metric_key
        tick_format = ",.2f"
        tick_suffix = ""
        x_title = label

    def _wrap_label(name: str, max_len: int = 10, max_lines: int = 2) -> str:
        text = str(name)
        chunks = [text[i : i + max_len] for i in range(0, len(text), max_len)]
        if len(chunks) > max_lines:
            chunks = chunks[: max_lines]
            if len(chunks[-1]) >= 1:
                chunks[-1] = chunks[-1][: max_len - 1] + "…"
        return "<br>".join(chunks)

    df_plot["label"] = df_plot["provider"].apply(_wrap_label)

    colors = bar_colors(len(df_plot))
    ordered_labels = df_plot["label"].tolist()

    fig = go.Figure(
        go.Bar(
            x=df_plot["label"],
            y=df_plot[value_col],
            orientation="v",
            marker=dict(color=colors, line=dict(color=theme.card_border, width=0.5)),
            customdata=df_plot["provider"],
            hovertemplate="%{customdata}<br>" + label + ": %{y:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        template=theme.template,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=theme.font,
        margin=dict(t=32, l=12, r=12, b=60),
        height=max(260, 60 * max(1, len(df_plot))),
        xaxis=dict(
            tickangle=0,
            tickfont=dict(color=theme.font, size=10),
            automargin=True,
            title="",
            showgrid=False,
            categoryorder="array",
            categoryarray=ordered_labels,
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(color=theme.font),
            title=title_text,
            tickformat=tick_format,
            ticksuffix=tick_suffix,
            automargin=True,
            range=[1, 5] if metric_key in likert_metrics else None,
            dtick=1 if metric_key in likert_metrics else None,
        ),
        showlegend=False,
        bargap=0.4,
    )
    return fig


def build_city_treemap(
    data: DataBundle,
    city_value: str,
    metric_key: str,
    selected_titles: Iterable[str] | None = None,
    slider_filter: Dict[str, Sequence[float]] | None = None,
    theme: Theme | None = None,
) -> go.Figure:
    theme = theme or DEFAULT_THEME
    metric = data.size_metrics.get(metric_key)
    if not metric:
        metric_key = next(iter(data.size_metrics.keys()))
        metric = data.size_metrics[metric_key]
    metric_col, how, metric_label = metric
    slider_filter = slider_filter or {}

    allowed_titles: set[str] | None = None
    if slider_filter:
        df_base = data.df.dropna(subset=["titel"]).copy()
        if not df_base.empty:
            mask = pd.Series(True, index=df_base.index, dtype=bool)
            for col, bounds in slider_filter.items():
                if col not in df_base.columns:
                    continue
                if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
                    continue
                try:
                    lo = float(bounds[0])
                    hi = float(bounds[1])
                except (TypeError, ValueError):
                    continue
                series = pd.to_numeric(df_base[col], errors="coerce")
                mask &= series.between(lo, hi)
            allowed_titles = set(df_base.loc[mask, "titel"].astype(str).str.strip())
            allowed_titles &= data.available_set
        else:
            allowed_titles = set()

    if city_value and city_value != "__ALL__":
        df_sel = data.df_prov[data.df_prov["instkommunetx"] == city_value].copy()
    else:
        df_sel = data.df_prov.copy()
    if allowed_titles is not None:
        df_sel = df_sel[df_sel["titel"].isin(allowed_titles)]

    df_sel = df_sel.dropna(subset=["educational_category", "cluster_label", "titel"])
    df_sel = df_sel[~df_sel[metric_col].isna()]

    if df_sel.empty:
        fig = go.Figure()
        fig.update_layout(
            template=theme.template,
            paper_bgcolor=theme.app_bg,
            plot_bgcolor=theme.plot_bg,
            font_color=theme.font,
            margin=dict(t=30, l=20, r=20, b=20),
        )
        fig.add_annotation(
            text="Ingen data for valgte filter.",
            showarrow=False,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            font=dict(color=theme.font),
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
            template=theme.template,
            paper_bgcolor=theme.app_bg,
            plot_bgcolor=theme.plot_bg,
            font_color=theme.font,
            margin=dict(t=30, l=20, r=20, b=20),
        )
        fig.add_annotation(
            text="Ingen data for valgte filter.",
            showarrow=False,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            font=dict(color=theme.font),
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
    text_colors = np.where(norm > 0.35, theme.text_on_dark, theme.text_on_light)

    selected_mask = (df_new["level"] == "titel") & df_new["label"].isin(selected_titles)
    color_values = base_colors.copy()
    marker_colorscale = px.colors.sequential.Blues
    marker_cmin = min_val
    marker_cmax = max_val

    if selected_mask.any():
        text_colors = np.array(text_colors, copy=True)
        text_colors[selected_mask] = theme.muted_text

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
            title=dict(text=metric_label, font=dict(color=theme.font)),
            tickfont=dict(color=theme.font),
            outlinecolor=theme.card_border,
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
        template=theme.template,
        paper_bgcolor=theme.app_bg,
        plot_bgcolor=theme.plot_bg,
        font_color=theme.font,
        margin=dict(t=50, l=30, r=50, b=20),
        title=title_txt,
    )
    fig.update_traces(root_color=theme.root_fill)
    return fig


def build_parallel_coordinates(
    data: DataBundle,
    selected_titles: Iterable[str],
    slider_filter: Dict[str, Sequence[float]],
    selected_vars: Iterable[str],
    color_map: Dict[str, str],
    theme: Theme | None = None,
    allowed_titles: set[str] | None = None,
) -> str:
    theme = theme or DEFAULT_THEME
    df = data.df.copy().dropna(subset=["titel"])
    if allowed_titles is not None:
        df = df[df["titel"].isin(allowed_titles)]
    columns = [col for col in selected_vars if col in df.columns]
    if not columns:
        return f"<div style='color:{theme.font};background-color:{theme.app_bg};padding:16px'>Ingen variabler valgt.</div>"

    df = df.dropna(subset=columns)
    if df.empty:
        return f"<div style='color:{theme.font};background-color:{theme.app_bg};padding:16px'>Ingen data for de valgte variabler.</div>"

    selected_list = [t for t in selected_titles if t]
    slider_filter = {k: tuple(v) for k, v in slider_filter.items() if k in columns}

    axis_ranges: Dict[str, Tuple[float, float]] = {}
    for col in columns:
        if col in PARCOORD_LIKERT_COLUMNS:
            axis_ranges[col] = (2.0, 5.0)
        else:
            series = df[col].astype(float)
            vmin = float(series.min())
            vmax = float(series.max())
            if np.isclose(vmin, vmax):
                vmax = vmin + 1.0
            axis_ranges[col] = (vmin, vmax)

    def normalize(value: float, bounds: Tuple[float, float]) -> float:
        lo, hi = bounds
        span = max(hi - lo, 1e-9)
        return float(np.clip((value - lo) / span, 0.0, 1.0))

    def row_values(row):
        return {col: normalize(float(row[col]), axis_ranges[col]) for col in columns}

    def matches_slider(row):
        if not slider_filter:
            return False
        for col, (lo, hi) in slider_filter.items():
            val = row.get(col)
            if pd.isna(val) or val < lo or val > hi:
                return False
        return True

    xs_template = list(range(len(columns)))
    base_xs: List[List[int]] = []
    base_ys: List[List[float]] = []
    base_titles: List[str] = []
    filtered_xs: List[List[int]] = []
    filtered_ys: List[List[float]] = []
    filtered_titles: List[str] = []
    selected_xs: List[List[int]] = []
    selected_ys: List[List[float]] = []
    selected_colors: List[str] = []
    selected_titles_list: List[str] = []
    selected_values_list: List[List[float]] = []

    for _, row in df.iterrows():
        title = str(row["titel"])
        norm_map = row_values(row)
        values = [norm_map[col] for col in columns]
        if title in selected_list:
            selected_xs.append(xs_template[:])
            selected_ys.append(values)
            selected_colors.append(color_map.get(title, "#ff6b6b"))
            selected_titles_list.append(title)
            selected_values_list.append([float(row[col]) for col in columns])
        elif matches_slider(row):
            filtered_xs.append(xs_template[:])
            filtered_ys.append(values)
            filtered_titles.append(title)
        else:
            base_xs.append(xs_template[:])
            base_ys.append(values)
            base_titles.append(title)

    p = figure(
        height=640,
        sizing_mode="stretch_width",
        x_range=(-0.5, len(columns) - 0.5),
        y_range=(0, 1),
        toolbar_location=None,
        background_fill_color=theme.app_bg,
        border_fill_color=theme.app_bg,
    )
    p.grid.visible = False
    p.yaxis.visible = False
    p.xaxis.ticker = list(range(len(columns)))
    p.xaxis.major_label_overrides = {i: PARCOORD_LABELS.get(col, col) for i, col in enumerate(columns)}
    p.xaxis.major_label_text_color = theme.font
    p.xaxis.major_tick_line_color = theme.card_border
    p.xaxis.axis_line_color = theme.card_border

    for idx, col in enumerate(columns):
        p.segment(x0=idx, y0=0, x1=idx, y1=1, line_color=theme.card_border, line_alpha=0.4)
        lo, hi = axis_ranges[col]
        p.text(x=idx, y=1.03, text=[f"{hi:.1f}"], text_align="center", text_color=theme.font, text_font_size="10px")
        p.text(x=idx, y=-0.06, text=[f"{lo:.1f}"], text_align="center", text_color=theme.font, text_font_size="10px")

    hover_renderers = []
    if base_xs:
        source = ColumnDataSource(dict(xs=base_xs, ys=base_ys, title=base_titles))
        p.multi_line("xs", "ys", source=source, line_color="#6c757d", line_alpha=0.18, line_width=1)
    if filtered_xs:
        source = ColumnDataSource(dict(xs=filtered_xs, ys=filtered_ys, title=filtered_titles))
        p.multi_line("xs", "ys", source=source, line_color="#4dabf7", line_alpha=0.7, line_width=1.5)
    if selected_xs:
        tooltip_texts = []
        for value_list in selected_values_list:
            lines = [f"{PARCOORD_LABELS.get(col, col)}: {val:.2f}" for col, val in zip(columns, value_list)]
            tooltip_texts.append("\n".join(lines))
        source = ColumnDataSource(
            dict(xs=selected_xs, ys=selected_ys, title=selected_titles_list, color=selected_colors, details=tooltip_texts)
        )
        r = p.multi_line("xs", "ys", source=source, line_color="color", line_alpha=0.95, line_width=3)
        hover_renderers.append(r)

    if hover_renderers:
        hover = HoverTool(
            tooltips="""
            <div><b>Uddannelse:</b> @title</div>
            <div style="white-space:pre-line;">@details</div>
            """,
            renderers=hover_renderers,
            line_policy="nearest",
        )
        p.add_tools(hover)

    return file_html(p, CDN, "Parallel Coordinates")


def build_parcoord_sliders(
    data: DataBundle,
    selected_vars: Iterable[str],
    previous_values: Dict[str, Sequence[float]],
    allowed_titles: set[str] | None = None,
) -> Tuple[List[html.Div], Dict[str, Sequence[float]]]:
    components: List[html.Div] = []
    slider_filter: Dict[str, Sequence[float]] = {}
    df = data.df
    if allowed_titles is not None:
        df = df[df["titel"].isin(allowed_titles)]

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


def build_selection_bubble(
    data: DataBundle,
    selected_titles: Iterable[str],
    color_map: Dict[str, str],
    theme: Theme | None = None,
    city_value: str | None = None,
) -> go.Figure:
    theme = theme or DEFAULT_THEME
    titles = [t for t in selected_titles if t]
    fig = go.Figure()
    fig.update_layout(template=theme.template, paper_bgcolor=theme.app_bg, plot_bgcolor=theme.plot_bg, font_color=theme.font)
    if not titles:
        fig.add_annotation(
            text="Ingen uddannelser valgt endnu.",
            showarrow=False,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            font=dict(color=theme.font),
        )
        return fig

    # Use provider-level data (same source as treemap) to respect multiple udbud entries per title.
    subset = data.df_prov[data.df_prov["titel"].isin(titles)].copy()
    if city_value and city_value != "__ALL__":
        subset = subset[subset["instkommunetx"] == city_value]
    if subset.empty:
        fig.add_annotation(
            text="Ingen data for de valgte uddannelser.",
            showarrow=False,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            font=dict(color=theme.font),
        )
        return fig

    def kvote_value(series: pd.Series) -> float:
        # Treat non-numeric / "alle" as missing; fallback to 2.0 if no numeric values.
        cleaned = []
        for val in series:
            if pd.isna(val):
                continue
            s = str(val).strip().lower()
            if not s or "alle" in s:
                continue
            num = to_num(pd.Series([val])).iloc[0]
            if pd.isna(num):
                continue
            cleaned.append(float(num))
        if cleaned:
            return float(np.mean(cleaned))
        return 2.0

    rows = []
    for title, group in subset.groupby("titel"):
        led = to_num(group.get("ledighed_nyudd", pd.Series(dtype=float))).dropna()
        lon = to_num(group.get("maanedloen_nyudd", pd.Series(dtype=float))).dropna()
        if led.empty or lon.empty:
            continue
        kvote = kvote_value(group.get("kvote_1_kvotient", pd.Series(dtype=object)))
        rows.append(
            dict(
                titel=title,
                ledighed_num=float(led.mean()),
                lon_num=float(lon.mean()),
                bubble_size=kvote,
            )
        )

    agg = pd.DataFrame(rows)
    if agg.empty:
        fig.add_annotation(
            text="Ingen data for de valgte uddannelser.",
            showarrow=False,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            font=dict(color=theme.font),
        )
        return fig

    sizes = agg["bubble_size"].astype(float)
    size_min, size_max = sizes.min(), sizes.max()
    if np.isclose(size_min, size_max):
        marker_sizes = [32 for _ in sizes]
    else:
        marker_sizes = 20 + 80 * (sizes - size_min) / max(size_max - size_min, 1e-9)

    colors = [color_map.get(t, "#4dabf7") for t in agg["titel"]]
    hover_text = [
        f"<b>{row['titel']}</b><br>Ledighed: {row['ledighed_num']:.1f}%<br>Løn (nyudd.): {row['lon_num']:.0f}<br>Kvote 1: {row['bubble_size']:.2f}"
        for _, row in agg.iterrows()
    ]

    fig.add_trace(
        go.Scatter(
            x=agg["ledighed_num"],
            y=agg["lon_num"],
            mode="markers",
            text=agg["titel"],
            hovertext=hover_text,
            hoverinfo="text",
            marker=dict(size=marker_sizes, color=colors, opacity=0.8, line=dict(color=theme.card_border, width=1)),
        )
    )
    fig.update_layout(
        xaxis_title="Ledighed (nyudd.)",
        yaxis_title="Løn (nyudd.)",
        margin=dict(t=40, l=50, r=30, b=50),
    )
    return fig
