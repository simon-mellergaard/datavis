app.py
import pandas as pd
import numpy as np
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go

from dash import Dash, dcc, html, Input, Output, State, callback, no_update

# -------------------- LOAD & PREP DATA (your pipeline) --------------------
df_raw = pd.read_excel('../Data/DATA_UFM_combined.xlsx', header=0)

cols = [
    'udbud_id','titel','educational_category','displaydocclass','hovedinsttx',
    'instregiontx','instkommunetx','optagne','kvote_1_kvotient',
    # likert
    'fagligmiljo_likert','arbmedstud_likert','medstuderende_likert','udbytte_undervisning_likert',
    'socialtmiljo_likert','ensom_likert','stress_daglig_likert','tilpas_likert',
    'undervisere_engagerede_likert','undervisere_feedback_likert','undervisere_hjaelp_likert',
    'undervisere_kontakt_likert',
    # continuous
    'afbrud','tidsforbrug_p50','tidsforbrug_arbejde',
    'uddaktivitet_opgaver_pct','uddaktivitet_praktik_pct','uddaktivitet_udlandsophold_pct',
    'uddaktivitet_undervisning_pct','undervisningsform_p1',
    # job
    'arbejdstid_timer','ledighed_nyudd','maanedloen_nyudd','maanedloen_10aar',
    # likert
    'ruster_til_job_likert','relevans_overens_udd_job_likert',
]
data = df_raw[cols]

# national-level rows (one per title desired)
data_whole_edu = data[data['udbud_id'] == 999999].copy()
data = data[data['udbud_id'] != 999999].drop(columns=['udbud_id'])  # not used further here

# mapping
mapping_path = "../Data/education_cluster_mapping.xlsx"
mapping = pd.read_excel(mapping_path)
mapping['titel'] = mapping['titel'].astype(str).str.strip()
data_whole_edu['titel'] = data_whole_edu['titel'].astype(str).str.strip()

data_whole_edu = data_whole_edu.merge(mapping, on='titel', how='left', suffixes=('', '_map'))
data_whole_edu = data_whole_edu.drop_duplicates(subset=['titel'])

# plotting dataset for treemap
plot_cols = [
    'titel','educational_category','cluster_label','displaydocclass',
    'maanedloen_nyudd','maanedloen_10aar',
    'fagligmiljo_likert','arbmedstud_likert','medstuderende_likert','udbytte_undervisning_likert',
    'socialtmiljo_likert','ensom_likert','stress_daglig_likert','tilpas_likert',
    'undervisere_engagerede_likert','undervisere_feedback_likert','undervisere_hjaelp_likert',
    'undervisere_kontakt_likert','ruster_til_job_likert','relevans_overens_udd_job_likert','afbrud'
]
dat = data_whole_edu[plot_cols].copy()
dat['titel'] = dat['titel'].astype(str).str.strip()
dat = dat.dropna(subset=['educational_category','cluster_label','titel','maanedloen_10aar'])

# -------------------- CONFIG --------------------
# color variable choices
COLOR_VARS = {
    'socialtmiljo_likert': 'Socialt miljø',
    'ruster_til_job_likert': 'Ruster til job',
    'fagligmiljo_likert': 'Fagligt miljø',
    'arbmedstud_likert': 'Arbejde med studier',
    'medstuderende_likert': 'Medstuderende',
    'udbytte_undervisning_likert': 'Udbytte af undervisning',
    'ensom_likert': 'Ensomhed',
    'stress_daglig_likert': 'Daglig stress',
    'tilpas_likert': 'Trivsel/tilpas',
    'undervisere_engagerede_likert': 'Undervisere engagerede',
    'undervisere_feedback_likert': 'Undervisere feedback',
    'undervisere_hjaelp_likert': 'Undervisere hjælpsomhed',
    'undervisere_kontakt_likert': 'Undervisere kontakt',
    'relevans_overens_udd_job_likert': 'Relevans udd. vs job',
    'afbrud': 'Frafald (afbrud)',
}

# 5 metrics for the radar (edit as you like)
RADAR_METRICS = [
    ('maanedloen_10aar', 'Månedsløn 10 år'),
    ('maanedloen_nyudd', 'Månedsløn nyudd.'),
    ('arbejdstid_timer', 'Arbejdstid (timer)'),
    ('ensom_likert', 'Ensom (Likert)'),
    ('stress_daglig_likert', 'Daglig stress (Likert)'),
]

CUSTOM_SCALE = ["#DEEBF7", "#FFFFFF", "#08306B"]  # light → white → dark (high at dark)
MAX_SELECT = 3

# Precompute z-scores for radar metrics on national-level data
z_dat = data_whole_edu[['titel'] + [c for c, _ in RADAR_METRICS]].copy()
for col, _ in RADAR_METRICS:
    m, s = z_dat[col].mean(), z_dat[col].std(ddof=0)
    z_dat[col + '__z'] = (z_dat[col] - m) / s if s else 0.0

# -------------------- FIGURE MAKERS --------------------
def make_treemap(color_col: str) -> go.Figure:
    df = dat.dropna(subset=[color_col]).copy()
    df['__titel__'] = df['titel']  # for clickData
    midpoint = float(df[color_col].mean())
    cmin, cmax = float(df[color_col].min()), float(df[color_col].max())

    fig = px.treemap(
        df,
        path=['educational_category','cluster_label','titel'],
        values='maanedloen_10aar',
        color=color_col,
        custom_data=['__titel__'],
        title=f"Treemap — farvelagt efter: {COLOR_VARS[color_col]} ({color_col})"
    )
    # per-trace scale + visible colorbar
    tr = fig.data[0]
    tr.update(
        marker_coloraxis=None,
        marker_colorscale=CUSTOM_SCALE,
        marker_cmin=cmin, marker_cmax=cmax, marker_cmid=midpoint,
        marker_colorbar=dict(title=COLOR_VARS[color_col], thickness=16, len=0.8, x=1.02, reversed=True),
        marker_showscale=True
    )
    fig.update_traces(root_color="lightgrey")
    fig.update_layout(margin=dict(t=60, l=30, r=50, b=20))
    return fig

def make_radar(selected_titles: list[str]) -> go.Figure:
    fig = go.Figure()
    if not selected_titles:
        fig.update_layout(
            title="Vælg op til 3 uddannelser (klik på bladene i treemappen)",
            polar=dict(radialaxis=dict(range=[-2.5, 2.5], tickvals=[-2,-1,0,1,2])),
            margin=dict(t=50, l=30, r=30, b=30),
            showlegend=True
        )
        return fig

    theta = [lbl for _, lbl in RADAR_METRICS]
    theta_closed = theta + [theta[0]]

    for t in selected_titles:
        row = z_dat[z_dat['titel'] == t]
        if row.empty:
            continue
        r = [float(row[c + '__z'].iloc[0]) for c, _ in RADAR_METRICS]
        r_closed = r + [r[0]]
        fig.add_trace(go.Scatterpolar(r=r_closed, theta=theta_closed, mode='lines+markers',
                                      name=t, fill='toself'))
    fig.update_layout(
        title="Radar — sammenlign valgte uddannelser (z-scores)",
        polar=dict(radialaxis=dict(range=[-2.5, 2.5], tickvals=[-2,-1,0,1,2])),
        margin=dict(t=50, l=30, r=30, b=30),
        showlegend=True
    )
    return fig

# -------------------- DASH APP --------------------
app = Dash(__name__)
app.title = "Uddannelses Treemap + Radar"

app.layout = html.Div(
    style={"backgroundColor": "#111", "color": "#eee", "padding": "12px", "fontFamily": "Inter, Arial, sans-serif"},
    children=[
        html.Div([
            html.Label("Farvemåling:", style={"marginRight": "8px"}),
            dcc.Dropdown(
                id="color-var",
                options=[{"label": f"{v} ({k})", "value": k} for k, v in COLOR_VARS.items()],
                value="socialtmiljo_likert",
                clearable=False,
                style={"width": "420px", "display": "inline-block", "verticalAlign": "middle"}
            ),
            html.Button("Ryd valg", id="clear-btn", n_clicks=0,
                        style={"marginLeft":"12px","height":"36px","cursor":"pointer"})
        ], style={"marginBottom": "8px"}),

        dcc.Graph(id="treemap", figure=make_treemap("socialtmiljo_likert"), config={"displayModeBar": True}),
        dcc.Store(id="selected-store", data=[]),
        html.Div(id="selection-chips", style={"margin":"4px 0 12px 0"}),

        dcc.Graph(id="radar", figure=make_radar([]), config={"displayModeBar": True})
    ]
)

# -------------------- CALLBACKS --------------------
@callback(
    Output("treemap", "figure"),
    Input("color-var", "value")
)
def update_treemap(color_col):
    return make_treemap(color_col)

@callback(
    Output("selected-store", "data"),
    Input("treemap", "clickData"),
    Input("clear-btn", "n_clicks"),
    State("selected-store", "data"),
    prevent_initial_call=True
)
def toggle_selection(clickData, clear_clicks, selected):
    ctx = dash.callback_context  # which input fired
    if not selected:
        selected = []
    if ctx.triggered and "clear-btn" in ctx.triggered[0]["prop_id"]:
        return []  # clear all

    # Handle treemap click
    if clickData and "points" in clickData and clickData["points"]:
        pt = clickData["points"][0]
        # We stored 'titel' in customdata
        try:
            clicked_title = pt["customdata"][0]
        except Exception:
            return selected
        if clicked_title in selected:
            selected = [t for t in selected if t != clicked_title]
        else:
            selected = (selected + [clicked_title])[:MAX_SELECT]
    return selected

@callback(
    Output("selection-chips", "children"),
    Output("radar", "figure"),
    Input("selected-store", "data")
)
def update_radar_and_chips(selected):
    chips = []
    for t in selected or []:
        chips.append(html.Span(
            t, style={"display":"inline-block","padding":"4px 8px","marginRight":"6px",
                      "background":"#2a2a2a","borderRadius":"12px","border":"1px solid #444"}
        ))
    if not chips:
        chips = [html.Span("Ingen valgt endnu.", style={"color":"#aaa"})]
    return chips, make_radar(selected or [])

if __name__ == "__main__":
    import dash
    app.run_server(debug=True)
