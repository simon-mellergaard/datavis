import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output

# ---------- Import data ----------
df_raw = pd.read_excel('../Data/DATA_UFM_combined_TEST_AREA_filled.xlsx', header=0)

# ---------- Columns to keep ----------
cols = [
    'udbud_id', 'titel', 'educational_category', 'displaydocclass', 'hovedinsttx',
    'instregiontx', 'instkommunetx', 'optagne', 'kvote_1_kvotient',
    'fagligmiljo_likert','arbmedstud_likert','medstuderende_likert','udbytte_undervisning_likert',
    'socialtmiljo_likert','ensom_likert','stress_daglig_likert','tilpas_likert',
    'undervisere_engagerede_likert','undervisere_feedback_likert','undervisere_hjaelp_likert',
    'undervisere_kontakt_likert','afbrud','tidsforbrug_p50','tidsforbrug_arbejde',
    'uddaktivitet_opgaver_pct','uddaktivitet_praktik_pct','uddaktivitet_udlandsophold_pct',
    'uddaktivitet_undervisning_pct','undervisningsform_p1','arbejdstid_timer','ledighed_nyudd',
    'maanedloen_nyudd','maanedloen_10aar','ruster_til_job_likert','relevans_overens_udd_job_likert'
]
data = df_raw[cols]

# ---------- Filter national-level ----------
data_whole_edu = data[data['udbud_id'] == 999999].copy()
data_whole_edu['titel'] = data_whole_edu['titel'].astype(str).str.strip()

# ---------- Load cluster mapping ----------
mapping = pd.read_excel("../Data/education_cluster_mapping.xlsx")
mapping['titel'] = mapping['titel'].astype(str).str.strip()
data_whole_edu = data_whole_edu.merge(mapping, on='titel', how='left')
data_whole_edu = data_whole_edu.drop_duplicates(subset=['titel'])

# ---------- Base DF ----------
df = data_whole_edu.copy()
df = df.dropna(subset=['titel'])
df['titel'] = df['titel'].astype(str).str.strip()

# ---------- CLEAN for treemap ----------
df_tm = df.dropna(subset=[
    'educational_category', 'cluster_label', 'titel',
    'maanedloen_10aar', 'socialtmiljo_likert'
]).copy()

# ---------- Radar metrics & z-scores ----------
radar_vars = [
    ('maanedloen_10aar', 'Løn 10 år'),
    ('maanedloen_nyudd', 'Løn nyudd'),
    ('arbejdstid_timer', 'Arbejdstid'),
    ('stress_daglig_likert', 'Stress'),
    ('ensom_likert', 'Ensomhed')
]
for col, _ in radar_vars:
    mean = df[col].mean()
    std = df[col].std(ddof=0)
    df[col + '_z'] = (df[col] - mean) / std if std > 0 else 0.0

# ---------- Treemap (dark) ----------
CUSTOM_BG = "#0f1115"
PLOT_BG   = "#0f1115"
FONT_COL  = "#e5e7eb"

treemap = px.treemap(
    df_tm,
    path=['educational_category', 'cluster_label', 'titel'],
    values='maanedloen_10aar',
    color='socialtmiljo_likert',
    color_continuous_scale=["#08306B", "#FFFFFF", "#DEEBF7"],
)
treemap.update_layout(
    template="plotly_dark",
    paper_bgcolor=CUSTOM_BG,
    plot_bgcolor=PLOT_BG,
    font_color=FONT_COL,
    margin=dict(t=50, l=30, r=50, b=20),
)
# make the colorbar font visible on dark
treemap.update_traces(root_color="#1c1f26",
                      marker_colorbar=dict(tickfont=dict(color=FONT_COL),
                                           titlefont=dict(color=FONT_COL),
                                           outlinecolor="#2a2f3a"))

# ---------- Radar builder (dark + NA-safe) ----------
def build_radar(titles):
    fig = go.Figure()
    theta = [lbl for _, lbl in radar_vars]
    theta_closed = theta + [theta[0]]

    for t in titles:
        row = df[df['titel'] == t]
        if row.empty:
            continue

        r = []
        for col, _lbl in radar_vars:
            val = row[col + '_z'].iloc[0]
            r.append(0.0 if pd.isna(val) else float(val))
        r_closed = r + [r[0]]

        fig.add_trace(go.Scatterpolar(
            r=r_closed, theta=theta_closed, mode='lines+markers',
            name=t, fill='toself'
        ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=CUSTOM_BG,
        plot_bgcolor=PLOT_BG,
        font_color=FONT_COL,
        title="Radar sammenligning",
        polar=dict(
            bgcolor="#12151c",
            radialaxis=dict(visible=True, range=[-2.5, 2.5], tickvals=[-2,-1,0,1,2], gridcolor="#2a2f3a"),
            angularaxis=dict(gridcolor="#2a2f3a")
        ),
        legend=dict(orientation='v', x=1.02, xanchor='left', y=1),
        margin=dict(t=40, l=30, r=30, b=30),
    )
    return fig

# ---------- Dash app (dark container + responsive layout) ----------
app = Dash(__name__)
titles_options = sorted(df['titel'].dropna().unique())

app.layout = html.Div(
    style={"padding":"12px", "backgroundColor": CUSTOM_BG, "color": FONT_COL, "minHeight":"100vh"},
    children=[
        html.Div([
            html.Div([
                dcc.Graph(id="treemap", figure=treemap, style={"height":"560px", "width":"100%"})
            ], style={"flex":"1 1 800px", "minWidth":"600px"}),

            html.Div([
                html.Div("Vælg op til 3 uddannelser:", style={"marginBottom":"8px", "fontWeight":"600"}),
                dcc.Dropdown(titles_options, id="edu1", placeholder="Uddannelse A", clearable=True,
                             style={"marginBottom":"10px", "backgroundColor":"#1f2630", "color":FONT_COL, "border":"1px solid #2a2f3a"}),
                dcc.Dropdown(titles_options, id="edu2", placeholder="Uddannelse B", clearable=True,
                             style={"marginBottom":"10px", "backgroundColor":"#1f2630", "color":FONT_COL, "border":"1px solid #2a2f3a"}),
                dcc.Dropdown(titles_options, id="edu3", placeholder="Uddannelse C", clearable=True,
                             style={"backgroundColor":"#1f2630", "color":FONT_COL, "border":"1px solid #2a2f3a"}),
                html.Div("Tip: Manglende værdier vises som 0 (middel) i radaren.",
                         style={"marginTop":"12px", "color":"#9aa4b2", "fontSize":"12px"})
            ], style={"flex":"0 0 360px", "maxWidth":"360px", "padding":"8px", "backgroundColor":"#11151b", "border":"1px solid #2a2f3a", "borderRadius":"8px"})
        ], style={"display":"flex", "gap":"16px", "alignItems":"flex-start", "flexWrap":"wrap"}),

        html.Hr(style={"borderColor":"#2a2f3a"}),

        dcc.Graph(id="radar", style={"height":"560px"})
    ]
)

# ---------- Callback ----------
@app.callback(
    Output("radar", "figure"),
    Input("edu1", "value"),
    Input("edu2", "value"),
    Input("edu3", "value"),
)
def update_radar(a, b, c):
    selected = [x for x in [a, b, c] if x]
    return build_radar(selected) if selected else build_radar([])

if __name__ == "__main__":
    app.run_server(debug=True)
