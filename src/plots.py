from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple, TYPE_CHECKING

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html
import dash_leaflet as dl
from bokeh.embed import file_html
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.plotting import figure
from bokeh.resources import CDN

from helpers import (
    ensure_latlon_from_municipality,
    mode_str,
    norm_udbud,
    parse_ref,
    to_num,
)
from theme import DEFAULT_THEME, Theme

if TYPE_CHECKING:  # avoid circular import during runtime
    from data_loader import DataBundle

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
    # "afbrud",
    # "tidsforbrug_p50",
    # "tidsforbrug_arbejde",
    # "arbejdstid_timer",
    # "ledighed_nyudd",
    # "maanedloen_nyudd",
    # "maanedloen_10aar",
]
PARCOORD_DEFAULT_VARS = [
    "fagligmiljo_likert",
    "socialtmiljo_likert",
    "tilpas_likert",
    "stress_daglig_likert",
    "undervisere_engagerede_likert",
]
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

COLOR_PALETTE = [ #categorical colours - paul tols bright colours
    "#4477AA",  # Blue
    "#66CCEE",  # Cyan
    "#228833",  # Green
    "#CCBB44",  # Yellow
    "#EE6677",  # Red
    "#AA3377",  # Purple
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
    "optagne_num": "Optagne (sum)",
    "ledighed_nyudd_n": "Ledighed nyudd.",
    "maanedloen_nyudd_n": "Løn (nyudd.)",
    "afbrud_num": "Afbrud (%)",
    "tidsforbrug_p50_num": "Tidsforbrug på studiet (timer)",
}

# Short explanatory tooltips for parallel-coordinate variables (shown on hover)
PARCOORD_TOOLTIPS: Dict[str, str] = {
    "fagligmiljo_likert": 'Hvor enig eller uenig er du i følgende udsagn: "Der er et godt fagligt miljø" (5: Helt enig, 1: Helt uenig)',
    "arbmedstud_likert": 'Hvor enig eller uenig er du i følgende udsagn: "Jeg har det generelt godt med at arbejde sammen med andre studerende" (5: Helt enig, 1: Helt uenig)',
    "medstuderende_likert": 'Hvor enig eller uenig er du i følgende udsagn: "Jeg forstår tingene bedre, når jeg har talt med mine medstuderende om dem" (5: Helt enig, 1: Helt uenig)',
    "udbytte_undervisning_likert": 'Hvor enig eller uenig er du i følgende udsagn: "Mit udbytte af undervisningen er højt" (5: Helt enig, 1: Helt uenig)',
    "socialtmiljo_likert": 'Hvor enig eller uenig er du i følgende udsagn: "Der er et godt socialt miljø" (5: Helt enig, 1: Helt uenig)',
    "ensom_likert": 'Hvor enig eller uenig er du i følgende udsagn: "Har du oplevet at føle dig ensom på studiet?" (5: Aldrig, 1: Altid)',
    "stress_daglig_likert": 'Hvor ofte gør følgende sig gældende for dig i forbindelse med dit studie: "Har du oplevet stærke stress-symptomer i forbindelse med dit studie i dagligdagen?" (5: Aldrig, 1: Altid)',
    "tilpas_likert": 'Hvor enig eller uenig er du i følgende udsagn: "Jeg føler mig generelt godt tilpas på min uddannelse" (5: Helt enig, 1: Helt uenig)',
    "undervisere_engagerede_likert": 'Hvor enig eller uenig er du i følgende udsagn: "Underviserne virker entusiastiske for det, de underviser i" (5: Helt enig, 1: Helt uenig)',
    "undervisere_feedback_likert": 'Hvor enig eller uenig er du i følgende udsagn: "Den feedback, jeg får, hjælper mig til at arbejde videre med det, jeg skal lære" (5: Helt enig, 1: Helt uenig)',
    "undervisere_hjaelp_likert": 'Hvor enig eller uenig er du i følgende udsagn: "Underviserne hjælper os med at forstå, hvordan man tænker og drager konklusioner på uddannelsen" (5: Helt enig, 1: Helt uenig)',
    "undervisere_kontakt_likert": 'Hvor enig eller uenig er du i følgende udsagn: "Mine undervisere er nemme at komme i kontakt med" (5: Helt enig, 1: Helt uenig)',
    "afbrud": "Andel der afbryder uddannelsen i løbet af første studieår.",
    "tidsforbrug_p50": "Typisk tidsforbrug (median) på undervisning, forberedelse og evt. praktik sammenlagt.",
    "tidsforbrug_arbejde": "Typisk tidsforbrug på arbejde ved siden af studiet (studiejob og frivilligt arbejde lagt sammen)",
    "arbejdstid_timer": "Gennemsnitlige ugentlige antal arbejdstimer for færdiguddannede.",
    "ledighed_nyudd": "Gennemsnitlig ledigheden for nyuddannede i 4-7 kvartal efter endt uddannelse.",
    "maanedloen_nyudd": "Månedlig erhvervsindkomst (median) i andet år efter fuldførelse af ud-dannelser. Afrundet til hele 100 kr.",
    "maanedloen_10aar": "Månedlig erhvervsindkomst (median) for personer med 10 års anciennitet. Afrundet til hele 100 kr.",
}

TREEMAP_DRILL_METRICS = [
    ("afbrud_num", "Afbrud (%)"),
    ("maanedloen_nyudd_n", "Løn"),
    ("ledighed_nyudd_n", "Ledighed"),
    ("tilpas_likert", "Trives (likert)"),
    ("optagne_num", "Optagne"),
    ("tidsforbrug_p50_num", "Tidsforbrug på studiet"),
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
            "No educations selected. Select an education in the treemap or bubble chart.",
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

    def first_link(frame: pd.DataFrame, column: str):
        if column not in frame.columns:
            return None
        series = frame[column].dropna().astype(str).str.strip()
        series = series[series != ""]
        return series.iloc[0] if not series.empty else None

    rows = [html.Tr([html.Th("Uddannelse"), html.Td(edu_title)])]
    for column, label, how, formatter in DETAIL_OVERVIEW_SPECS:
        value = metric_value(column, how)
        display = formatter(value) if value is not None else "N/A"
        rows.append(html.Tr([html.Th(label), html.Td(display)]))
    # Show each listed "Første job" on its own row instead of joining them
    jobs = [s for s in strings.values() if s]
    if jobs:
        # Header row with the first job
        rows.append(html.Tr([html.Th("Første job (typisk)"), html.Td(jobs[0])]))
        # Additional jobs on their own rows with an empty first cell for alignment
        for job in jobs[1:]:
            rows.append(html.Tr([html.Th(""), html.Td(job)]))

    ug_link = first_link(providers, "url") or (first_link(overview, "url") if not overview.empty else None)
    if ug_link:
        ug_link = ug_link.strip()
        if not ug_link.lower().startswith(("http://", "https://")):
            ug_link = f"https://{ug_link}"
        rows.append(
            html.Tr(
                [
                    html.Th("UG.dk"),
                    html.Td(
                        html.A(
                            "Åbn på UG.dk",
                            href=ug_link,
                            target="_blank",
                            rel="noopener noreferrer",
                            style={"color": "#0d6efd"},
                        )
                    ),
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
        "optagne",
        "kvote_1_kvotient",
        "standby_8",
        "afbrud",
        "tidsforbrug_p50",
        "ledighed_nyudd",
        "ledighed_10aar",
        "maanedloen_nyudd",
        "maanedloen_10aar",
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


def build_leaflet_map(providers_df: pd.DataFrame, theme: Theme | None = None):
    """Simplified map for provider locations using dash-leaflet."""
    theme = theme or DEFAULT_THEME
    if providers_df.empty:
        return html.Div("Ingen koordinater fundet for denne uddannelse.", style={"color": theme.font})

    providers_geo = ensure_latlon_from_municipality(providers_df)
    providers_geo = providers_geo.dropna(subset=["inst_lat", "inst_lon"])
    providers_geo = providers_geo[np.isfinite(providers_geo["inst_lat"]) & np.isfinite(providers_geo["inst_lon"])]
    if providers_geo.empty:
        return html.Div("Ingen koordinater fundet for denne uddannelse.", style={"color": theme.font})

    # Fixed Denmark view; markers move, viewport stays consistent.
    center_lat, center_lon = 56.0, 10.5
    zoom = 7.0
    bounds = None

    markers = []
    for _, row in providers_geo.iterrows():
        label_parts = [str(row.get("hovedinsttx", "")).strip()]
        muni = str(row.get("instkommunetx", "")).strip()
        if muni:
            label_parts.append(muni)
        title = str(row.get("titel", "")).strip()
        if title:
            label_parts.append(title)
        tooltip_text = " • ".join([p for p in label_parts if p])

        def fmt_percent(val):
            num = to_num(pd.Series([val])).iloc[0]
            return f"{num:.1f}%" if not pd.isna(num) else "N/A"

        def fmt_float(val, digits=1):
            num = to_num(pd.Series([val])).iloc[0]
            return f"{num:.{digits}f}" if not pd.isna(num) else "N/A"

        def fmt_kr(val):
            num = to_num(pd.Series([val])).iloc[0]
            return f"{num:,.0f} kr" if not pd.isna(num) else "N/A"

        popup_rows = [
            ("Optagne", fmt_float(row.get("optagne"), 0)),
            ("Kvote 1 kvotient", fmt_float(row.get("kvote_1_kvotient"), 2)),
            ("Standby", fmt_float(row.get("standby_8"), 0)),
            ("Afbrud (%)", fmt_percent(row.get("afbrud"))),
            ("Tidsforbrug (timer)", fmt_float(row.get("tidsforbrug_p50"), 1)),
            ("Ledighed (nyudd.)", fmt_percent(row.get("ledighed_nyudd"))),
            ("Ledighed (10 år)", fmt_percent(row.get("ledighed_10aar"))),
            ("Løn (nyudd.)", fmt_kr(row.get("maanedloen_nyudd"))),
            ("Løn (10 år)", fmt_kr(row.get("maanedloen_10aar"))),
        ]

        popup_table = html.Table(
            [html.Tbody([html.Tr([html.Th(lbl), html.Td(val)]) for lbl, val in popup_rows])],
            style={"fontSize": "12px", "lineHeight": "1.3"},
        )

        markers.append(
            dl.Marker(
                position=(float(row["inst_lat"]), float(row["inst_lon"])),
                children=[
                    dl.Tooltip(tooltip_text),
                    dl.Popup(html.Div(popup_table)),
                ],
            )
        )

    marker_layer = dl.LayerGroup(markers) if markers else None

    return dl.Map(
        id="detail_leaflet_map",
        center=(center_lat, center_lon),
        zoom=zoom if bounds is None else None,  # let bounds drive zoom when present
        bounds=bounds,
        boundsOptions={"padding": [20, 20]},
        zoomControl=False,
        scrollWheelZoom=False,
        doubleClickZoom=False,
        touchZoom=False,
        children=[
            dl.TileLayer(
                url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
                attribution="© OpenStreetMap contributors, © CARTO",
            ),
            *( [marker_layer] if marker_layer else [] ),
        ],
        style={"height": "520px", "width": "100%", "borderRadius": "6px"},
    )


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
            # Ensure chosen providers stay left and national last (keep this ordering on the x-axis).
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

    def _wrap_label(name: str, max_len: int = 18, max_lines: int = 2) -> str:
        text = str(name)
        words = text.split()
        lines = []
        current = ""
        for w in words:
            if len(current) + len(w) + (1 if current else 0) <= max_len:
                current = f"{current} {w}".strip()
            else:
                lines.append(current)
                current = w
            if len(lines) >= max_lines:
                break
        if current and len(lines) < max_lines:
            lines.append(current)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
        if len(lines) == max_lines and len(words) > len(" ".join(lines).split()):
            lines[-1] = lines[-1][: max(0, max_len - 1)] + "…"
        return "<br>".join(lines)

    df_plot["label"] = df_plot["provider"].apply(_wrap_label)

    ordered_labels = df_plot["label"].tolist()
    # Use clearer contrast for national vs selected providers, especially in light mode.
    provider_color = "#1d4ed8" if theme.name == "light" else "#60a5fa"
    national_color = "#e2e8f0" if theme.name == "light" else "#94a3b8"
    colors = [provider_color for _ in df_plot["provider"]]
    nat_mask = df_plot["provider"] == "Nationalt gennemsnit"
    for i, is_nat in enumerate(nat_mask):
        if is_nat:
            colors[i] = national_color

    fig = go.Figure(
        go.Bar(
            x=df_plot["label"],
            y=df_plot[value_col],
            orientation="v",
            width=0.35,  # slightly narrower bars for clearer spacing
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
        bargap=0.45,
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

    currency_label = ""
    if metric_label == "Løn (nyudd.) (gennemsnit)":
        currency_label = " kr."
    hover_text = (
        f"<b>%{{label}}</b><br>{metric_label}: %{{value:,.0f}}{currency_label}"
    )
    text_template = f"<b>%{{label}}</b><br>{metric_label}: %{{value:,.0f}}{currency_label}"
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
    # Ensure treemap rectangles have a clear border color (theme-specific)
    try:
        marker_dict["line"] = dict(color=theme.treemap_border, width=0.6)
    except Exception:
        # Fallback to card border if the theme doesn't provide treemap_border
        marker_dict["line"] = dict(color=theme.card_border, width=0.6)

    fig = go.Figure(
        go.Treemap(
            ids=df_new["id"],
            labels=df_new["label"],
            parents=df_new["parent"],
            values=df_new["value"],
            branchvalues="total",
            marker=marker_dict,
            texttemplate=text_template,
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


FILTERED_GREY = "#BBBBBB" # Neutral Mid-Grey

def build_parallel_coordinates(
    data: DataBundle,
    selected_titles: Iterable[str],
    slider_filter: Dict[str, Sequence[float]],
    selected_vars: Iterable[str],
    color_map: Dict[str, str],
    theme: Theme | None = None,
    allowed_titles: set[str] | None = None,
    scale_mode: str = "FIXED_SCALE",
) -> str:
    theme = theme or DEFAULT_THEME
    
    df = data.df.copy().dropna(subset=["titel"])
    if allowed_titles is not None:
        df = df[df["titel"].isin(allowed_titles)]
    columns = [col for col in selected_vars if col in df.columns]
    
    if not columns:
        return f"<div style='color:{theme.font};background-color:{theme.app_bg};padding:16px'>No variables chosen.</div>"

    df = df.dropna(subset=columns)
    if df.empty:
        return f"<div style='color:{theme.font};background-color:{theme.app_bg};padding:16px'>No data for the selected variables.</div>"

    selected_list = [t for t in selected_titles if t]
    slider_filter = {k: tuple(v) for k, v in slider_filter.items() if k in columns}

    # --- AXIS RANGE CALCULATION ---
    # Scale axes either to data min/max (DATA_SCALE) or fixed Likert range 2-5 (FIXED_SCALE).
    axis_ranges: Dict[str, Tuple[float, float]] = {}
    scaling_df = df.copy().dropna(subset=columns)
    for col in columns:
        if scale_mode == "FIXED_SCALE":
            axis_ranges[col] = (2.0, 5.0)
            continue
        series = scaling_df[col].astype(float)
        vmin = float(series.min())
        vmax = float(series.max())
        if np.isclose(vmin, vmax):
            vmax = vmin + 0.1  # small pad so the axis has a span
        axis_ranges[col] = (vmin, vmax)
    # -------------------------------------

    def normalize(value: float, bounds: Tuple[float, float]) -> float:
        """Normalizes a value to the [0.0, 1.0] range based on axis bounds."""
        lo, hi = bounds
        span = max(hi - lo, 1e-9)
        return float(np.clip((value - lo) / span, 0.0, 1.0))

    def row_values(row):
        """Returns a dict of normalized values for the row."""
        return {col: normalize(float(row[col]), axis_ranges[col]) for col in columns}

    def matches_slider(row):
        """Checks if a row's values fall within the active slider filters."""
        if not slider_filter:
            return True
        for col, (lo, hi) in slider_filter.items():
            val = row.get(col)
            if pd.isna(val) or val < lo or val > hi:
                return False
        return True

    xs_template = list(range(len(columns)))
    
    filtered_xs: List[List[int]] = []
    filtered_ys: List[List[float]] = []
    filtered_titles: List[str] = []
    selected_xs: List[List[int]] = []
    selected_ys: List[List[float]] = []
    selected_colors: List[str] = []
    selected_titles_list: List[str] = []
    selected_values_list: List[List[float]] = []

    # --- CORE ITERATION LOGIC ---
    for _, row in df.iterrows():
        title = str(row["titel"])
        norm_map = row_values(row)
        values = [norm_map[col] for col in columns]
        raw_values = [float(row[col]) for col in columns] 
        
        is_selected = title in selected_list
        is_filtered = matches_slider(row)
        
        if is_selected:
            selected_xs.append(xs_template[:])
            selected_ys.append(values)
            selected_colors.append(color_map.get(title, "#ff6b6b"))
            selected_titles_list.append(title)
            selected_values_list.append(raw_values)
        elif is_filtered:
            filtered_xs.append(xs_template[:])
            filtered_ys.append(values)
            filtered_titles.append(title)
        
    # --- PLOT SETUP ---
    p = figure(
        height=640,
        sizing_mode="stretch_width",
        x_range=(-0.2, len(columns) - 0.8),
        y_range=(-0.1, 1.1),
        toolbar_location=None,
        tools="",
        background_fill_color=theme.app_bg,
        border_fill_color=theme.app_bg,
    )
    p.grid.grid_line_color = theme.card_border
    p.grid.visible = False
    try:
        if getattr(p, "toolbar", None) is not None:
            p.toolbar.active_drag = None
            p.toolbar.active_scroll = None
    except Exception:
        pass
        
    p.yaxis.visible = False
    p.xaxis.ticker = list(range(len(columns)))
    p.xaxis.major_label_overrides = {i: PARCOORD_LABELS.get(col, col) for i, col in enumerate(columns)}
    p.xaxis.major_label_text_color = theme.font
    p.xaxis.major_tick_line_color = theme.card_border
    p.xaxis.axis_line_color = theme.card_border

    # --- AXIS LINES AND LABELS ---
    for idx, col in enumerate(columns):
        p.segment(x0=idx, y0=0, x1=idx, y1=1, line_color=theme.card_border, line_alpha=0.4)
        lo, hi = axis_ranges[col]
        
        # Format string for labels
        format_str = ".1f" if scale_mode == "FIXED_SCALE" else ".2f"
        
        # Axis labels (max/min)
        p.text(x=idx, y=1.03, text=[f"{hi:{format_str}}"], text_align="center", text_color=theme.font, text_font_size="10px")
        p.text(x=idx, y=-0.06, text=[f"{lo:{format_str}}"], text_align="center", text_color=theme.font, text_font_size="10px")
        
        # Likert-style axis gridlines and labels (only in Fixed Scale mode)
        if scale_mode == "FIXED_SCALE":
            for tick in (2, 3, 4):
                if tick >= lo and tick <= hi:
                    y_pos = normalize(float(tick), axis_ranges[col])
                    
                    p.segment(x0=-0.5, y0=y_pos, x1=len(columns) - 0.5, y1=y_pos, line_color=theme.card_border, line_alpha=0.25)
                    
                    if idx == 0:
                        p.text(
                            x=-0.1,
                            y=y_pos,
                            text=[str(tick)],
                            text_align="right",
                            text_color=theme.font,
                            text_font_size="15px",
                        )

    hover_renderers = []
    
    # --- PLOTTING LINES ---
    base_line_color = "#7a7a7a" if theme.name == "light" else "#a0a0a0"
    base_line_alpha = 0.35 if theme.name == "light" else 0.22
    selected_alpha = 1.0
    selected_width = 3.5 if theme.name == "light" else 3.0
    base_width = 1.3 if theme.name == "light" else 1.0

    if filtered_xs:
        source = ColumnDataSource(dict(xs=filtered_xs, ys=filtered_ys, title=filtered_titles))
        p.multi_line(
            "xs",
            "ys",
            source=source,
            line_color=base_line_color,
            line_alpha=base_line_alpha,
            line_width=base_width,
        )
    
    if selected_xs:
        tooltip_texts = []
        for value_list in selected_values_list:
            lines = [f"{PARCOORD_LABELS.get(col, col)}: {val:.2f}" for col, val in zip(columns, value_list)]
            tooltip_texts.append("\n".join(lines))
        source = ColumnDataSource(
            dict(xs=selected_xs, ys=selected_ys, title=selected_titles_list, color=selected_colors, details=tooltip_texts)
        )
        r = p.multi_line("xs", "ys", source=source, line_color="color", line_alpha=selected_alpha, line_width=selected_width)
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
    data: Any,  # your DataBundle object
    selected_vars: Iterable[str],
    previous_values: Dict[str, Sequence[float]],
    allowed_titles: Set[str] | None = None,
    likert_columns: Set[str] | None = None,
    labels: Dict[str, str] | None = None,
    tooltips: Dict[str, str] | None = None,
) -> Tuple[List[html.Div], Dict[str, Sequence[float]]]:
    """
    Fixed version – integer marks (3.0, 4.0, 5.0, etc.) are guaranteed to appear.
    """
    if likert_columns is None:
        likert_columns = PARCOORD_LIKERT_COLUMNS
    if labels is None:
        labels = PARCOORD_LABELS
    if tooltips is None:
        tooltips = PARCOORD_TOOLTIPS

    components: List[html.Div] = []
    slider_filter: Dict[str, Sequence[float]] = {}
    df = data.df

    if allowed_titles is not None:
        df = df[df["titel"].isin(allowed_titles)]

    def clean_float(x: float) -> float:
        """Eliminate floating-point precision quirks – always exactly X.0 or X.1 etc."""
        return round(float(x), 1)

    for col in selected_vars:
        if col not in df.columns:
            continue

        series = df[col].dropna().astype(float)
        if series.empty:
            continue

        # ----- Determine clean min/max from data -----
        data_min = float(series.min())
        data_max = float(series.max())
        if col in likert_columns:
            min_val = clean_float(data_min)
            max_val = clean_float(data_max)
        else:
            min_val = clean_float(data_min)
            max_val = clean_float(data_max)

        if np.isclose(min_val, max_val):
            max_val = min_val + 0.1

        # ----- Hard-coded overrides (still cleaned) -----
        if col == "Socialt miljø":
            min_val = 3.0
        if col == "Undervisere engagerede":
            max_val = 5.0
        if col == "Ensomhed":
            min_val = 3.0
        if col == "Feedback":
            min_val = 3.0

        min_val = clean_float(min_val)
        max_val = clean_float(max_val)
        step = 0.1

        # ----- Build marks with guaranteed clean keys (only min and max) -----
        marks: Dict[float, str] = {}
        marks[min_val + 1e-6] = f"{min_val:.1f}"
        marks[max_val - 1e-6] = f"{max_val:.1f}"

        # ----- Current value (with bounds clamping) -----
        default = [min_val, max_val]
        current = list(previous_values.get(col, default))
        current = [
            max(min_val, min(max_val, clean_float(current[0]))),
            max(min_val, min(max_val, clean_float(current[1])))
        ]

        # ----- Create the slider -----
        slider = dcc.RangeSlider(
            id={"type": "parcoord-slider", "column": col},
            min=min_val,
            max=max_val,
            step=step,
            value=current,
            marks=marks,
            tooltip={"placement": "bottom", "always_visible": False},
            allowCross=False,
            className="dark-slider-track",
        )

        label_text = labels.get(col, col)
        label_tooltip = tooltips.get(col, "")

        components.append(
            html.Div(
                [html.Label(label_text, title=label_tooltip), slider],
                style={"marginBottom": "16px"},
            )
        )

        if not (np.isclose(current[0], default[0]) and np.isclose(current[1], default[1])):
            slider_filter[col] = current

    return components, slider_filter


def build_selection_bubble(
    data: DataBundle,
    selected_titles: Iterable[str],
    color_map: Dict[str, str],
    theme: Theme | None = None,
    city_value: str | None = None,
    slider_filter: Dict[str, Sequence[float]] | None = None,
) -> go.Figure:
    theme = theme or DEFAULT_THEME
    selected_set = {t for t in selected_titles if t}
    titles = list(selected_set)
    fig = go.Figure()
    fig.update_layout(template=theme.template, paper_bgcolor=theme.app_bg, plot_bgcolor=theme.plot_bg, font_color=theme.font)
    slider_filter = slider_filter or {}

    df = data.df_prov.copy()
    df = df[df["titel"].notna()]
    if city_value and city_value != "__ALL__":
        df = df[df["instkommunetx"] == city_value]
    if df.empty:
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
    for title, group in df.groupby("titel"):
        led = to_num(group.get("ledighed_nyudd", pd.Series(dtype=float))).dropna()
        lon = to_num(group.get("maanedloen_nyudd", pd.Series(dtype=float))).dropna()
        if led.empty or lon.empty:
            continue
        kvote = kvote_value(group.get("kvote_1_kvotient", pd.Series(dtype=object)))
        rows.append(
            dict(
                titel=title,
                ledighed_num=float(led.mean()),
                lon_num=float(kvote),
                bubble_size=lon.mean(),
                match_filter=True,  # placeholder
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

    def matches_slider_row(row: pd.Series) -> bool:
        if not slider_filter:
            return False
        for col, bounds in slider_filter.items():
            if col not in row.index:
                continue
            try:
                lo, hi = float(bounds[0]), float(bounds[1])
                val = float(row[col]) if not pd.isna(row[col]) else np.nan
            except (TypeError, ValueError):
                return False
            if pd.isna(val) or val < lo or val > hi:
                return False
        return True

    # Evaluate slider match on available columns; use aggregated values where possible
    for col in slider_filter:
        if col not in agg.columns and col in df.columns:
            agg[col] = df.groupby("titel")[col].mean().reindex(agg["titel"]).values
    agg["match_filter"] = agg.apply(matches_slider_row, axis=1)

    sizes = agg["bubble_size"].astype(float)
    min_diam, max_diam = 10.0, 50.0
    min_area = (min_diam / 2) ** 2 * np.pi
    max_area = (max_diam / 2) ** 2 * np.pi
    if np.isclose(sizes.min(), sizes.max()):
        marker_sizes = [0.5 * (min_diam + max_diam) for _ in sizes]
    else:
        # Scale bubble area linearly between the min and max salary to avoid “flattening” mid-range values.
        span = sizes.max() - sizes.min()
        norm = (sizes - sizes.min()) / span
        areas = min_area + norm * (max_area - min_area)
        marker_sizes = 2 * np.sqrt(areas / np.pi)  # convert area back to diameter for Plotly

    colors = []
    for t, match in zip(agg["titel"], agg["match_filter"]):
        if t in selected_set:
            colors.append(color_map.get(t, "#4dabf7"))
        elif match:
            colors.append("#BBBBBB")  # slider matches but not selected = grey highlight #Both should be the same grey now
        else:
            colors.append("#BBBBBB")  # background (only shown if no sliders)

    hover_text = []
    for _, row in agg.iterrows():
        salary = row["bubble_size"]
        kvote = row["lon_num"]
        hover_text.append(
            f"<b>{row['titel']}</b>"
            f"<br>Ledighed: {row['ledighed_num']:.1f}%"
            f"<br>Løn (nyudd.): {salary:,.0f} kr."
            f"<br>Kvote 1: {kvote:.2f}"
        )

    # Foreground: selected or filter matches
    fg_mask = (agg["titel"].isin(selected_set)) | agg["match_filter"]
    bg_mask = ~fg_mask
    show_background = not bool(slider_filter)

    # Set sensible y-range; allow a small buffer below zero so bubbles don't clip,
    # but only show tick labels from 0% and up.
    y_min = float(agg["ledighed_num"].min())
    y_buffer = 8.0
    y_min_range = min(-6.0, y_min - y_buffer)
    y_max = float(agg["ledighed_num"].max()) + 10.0
    ticks = list(np.arange(0, max(10.0, y_max + 1.0), 5.0))
    ticktext = [f"{int(t)}%" for t in ticks]

    # Draw background (non-selected) points first so selected/matched points
    # added later will appear on top.
    if show_background and bg_mask.any():
        fig.add_trace(
            go.Scatter(
                y=agg.loc[bg_mask, "ledighed_num"],
                x=agg.loc[bg_mask, "lon_num"],
                mode="markers",
                text=agg.loc[bg_mask, "titel"],
                hovertext=[hover_text[i] for i, m in enumerate(bg_mask) if m],
                hoverinfo="text",
                marker=dict(
                    size=np.array(marker_sizes)[bg_mask],
                    color="#BBBBBB",
                    opacity=0.6,
                    line=dict(color=theme.card_border, width=0.5),
                ),
                name="Show/hide all educations",
                customdata=agg.loc[bg_mask, "titel"],
            )
        )

    # Foreground: selected or filter matches - added after background so they
    # render on top and remain visible.
    if fg_mask.any():
        fig.add_trace(
            go.Scatter(
                y=agg.loc[fg_mask, "ledighed_num"],
                x=agg.loc[fg_mask, "lon_num"],
                mode="markers",
                text=agg.loc[fg_mask, "titel"],
                hovertext=[hover_text[i] for i, m in enumerate(fg_mask) if m],
                hoverinfo="text",
                marker=dict(
                    size=np.array(marker_sizes)[fg_mask],
                    color=np.array(colors)[fg_mask],
                    opacity=0.9,
                    line=dict(color=theme.card_border, width=1),
                ),
                name="Match",
                showlegend=False,
                customdata=agg.loc[fg_mask, "titel"],
            )
        )

    # Ensure that 'Match' traces are rendered on top of background points.
    try:
        traces = list(fig.data)
        match_traces = [t for t in traces if getattr(t, "name", "") == "Match"]
        other_traces = [t for t in traces if getattr(t, "name", "") != "Match"]
        # Reassign so non-match traces come first, match traces last (on top)
        fig.data = tuple(other_traces + match_traces)
    except Exception:
        # If reordering fails for any reason, continue without raising.
        pass

    fig.update_traces(cliponaxis=False)
    fig.update_layout(
        xaxis_title="Karakterer (kvote 1)",
        yaxis_title="Ledighed (nyudd.)",
        yaxis=dict(
            hoverformat=".1f%%",
            range=[y_min_range, y_max],
            tickvals=ticks,
            ticktext=ticktext,
            tickmode="array",
        ),
        margin=dict(t=40, l=50, r=30, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig
