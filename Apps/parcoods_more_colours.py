import dash
from dash import dcc, html, Input, Output, State, ALL
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# -----------------------------
# LOAD DATA
# -----------------------------
df_raw = pd.read_excel('../Data/DATA_UFM_combined_cluster.xlsx', header=0)
cols = [
    'udbud_id', 'titel', 'educational_category', 'cluster_label',
    'fagligmiljo_likert', 'arbmedstud_likert', 'medstuderende_likert',
    'udbytte_undervisning_likert', 'socialtmiljo_likert', 'ensom_likert',
    'stress_daglig_likert', 'tilpas_likert',
    'undervisere_engagerede_likert','undervisere_feedback_likert',
    'undervisere_hjaelp_likert','undervisere_kontakt_likert',
    'afbrud','tidsforbrug_p50','tidsforbrug_arbejde',
    'arbejdstid_timer','ledighed_nyudd','maanedloen_nyudd','maanedloen_10aar',
    'url'
]
dat = df_raw[cols]
dat = dat[dat['udbud_id'] == 999999].drop(columns=['udbud_id']).dropna()

# -----------------------------
# VARIABLES
# -----------------------------
all_variables = [
    'fagligmiljo_likert','arbmedstud_likert','medstuderende_likert','udbytte_undervisning_likert',
    'socialtmiljo_likert','ensom_likert','stress_daglig_likert','tilpas_likert',
    'undervisere_engagerede_likert','undervisere_feedback_likert','undervisere_hjaelp_likert','undervisere_kontakt_likert',
    'afbrud','tidsforbrug_p50','tidsforbrug_arbejde',
    'arbejdstid_timer','ledighed_nyudd','maanedloen_nyudd','maanedloen_10aar'
]
default_vars = all_variables[:5]

# -----------------------------
# COLOR PALETTE
# -----------------------------
COLOR_PALETTE = [
    "#d62728", "#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]

# -----------------------------
# HELPERS
# -----------------------------
def create_treemap(color_var='maanedloen_nyudd'):
    leaf = dat.groupby(['educational_category', 'cluster_label','titel'], as_index=False)\
              .agg({color_var:'mean'})
    fig = px.treemap(
        leaf,
        path=['educational_category','cluster_label','titel'],
        values=color_var,
        color=color_var,
        color_continuous_scale='viridis'
    )
    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=400)
    return fig

def build_color_map_for_selected(currently_selected, previous_map=None):
    previous_map = previous_map or {}
    cmap = previous_map.copy()
    next_idx = len(cmap)
    for title in currently_selected:
        if title not in cmap:
            cmap[title] = COLOR_PALETTE[next_idx % len(COLOR_PALETTE)]
            next_idx += 1
    return cmap

def create_parcoords(selected_titles=None, slider_filter=None, selected_vars=None, color_map=None):
    if selected_vars is None: selected_vars = default_vars
    if selected_titles is None: selected_titles = []
    if slider_filter is None: slider_filter = {}
    if color_map is None: color_map = {}

    n_selected = len(selected_titles)
    cmin = 0.0
    cmax = max(1.0, float(n_selected) or 1)

    # Color values: 0.0 = grey, 0.5 = filtered, 1+ = selected
    numeric_line_values = []
    for _, row in dat.iterrows():
        t = row['titel']
        if t in selected_titles:
            numeric_line_values.append(selected_titles.index(t) + 1)
        elif slider_filter:
            match = all(slider_filter[col][0] <= row[col] <= slider_filter[col][1]
                        for col in slider_filter)
            numeric_line_values.append(0.5 if match else 0.0)
        else:
            numeric_line_values.append(0.0)

    dimensions = []
    for col in selected_vars:
        vals = dat[col]
        dim = dict(
            range=[1,5] if vals.max() <= 5 else [vals.min(), vals.max()],
            label=col.replace('_', ' '),
            values=vals
        )
        dimensions.append(dim)

    # THIS IS THE KEY: always include full grey at 0 and 1
    colorscale = [[0.0, "#E8E8E8"], [1.0, "#E8E8E8"]]  # ← forces grey even on first render

    if slider_filter:
        colorscale.insert(1, [0.5 / cmax, "#87CEFA"])
    if n_selected > 0:
        for idx, t in enumerate(selected_titles, start=1):
            pos = float(idx) / cmax
            colorscale.insert(-1, [pos, color_map.get(t, "#E8E8E8")])  # insert before final grey

    fig = go.Figure(go.Parcoords(
        line=dict(
            color=numeric_line_values,
            colorscale=colorscale,
            cmin=cmin,
            cmax=cmax,
            showscale=False
        ),
        dimensions=dimensions
    ))
    fig.update_layout(margin=dict(l=80, r=80, t=40, b=40), height=600)
    return fig, color_map

# 100% GREY INITIAL FIGURE — guaranteed, no matter what
initial_parcoords, _ = create_parcoords([], {}, default_vars, {})
# Extra safety: force the colorscale to pure grey
initial_parcoords.data[0].line.colorscale = [[0, "#E8E8E8"], [1, "#E8E8E8"]]
initial_parcoords.data[0].line.cmin = 0
initial_parcoords.data[0].line.cmax = 1

# -----------------------------
# APP
# -----------------------------
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H2("Uddannelsesdashboard – Altid grå + maks-sliders", 
            style={'textAlign': 'center', 'margin': '20px'}),

    html.Div([dcc.Dropdown(
        id='treemap-variable-selector',
        options=[{'label': v.replace('_', ' '), 'value': v} for v in all_variables],
        value='maanedloen_nyudd',
        clearable=False,
        style={'width': '95%'}
    )], style={'margin': '10px'}),

    dcc.Graph(id='treemap', figure=create_treemap()),

    html.Div([dcc.Dropdown(
        id='line-selector',
        options=[{'label': t, 'value': t} for t in sorted(dat['titel'].unique())],
        multi=True,
        placeholder="Vælg uddannelser...",
        style={'width': '95%'}
    )], style={'margin': '10px'}),

    html.Div([dcc.Dropdown(
        id='variable-selector',
        options=[{'label': v.replace('_', ' '), 'value': v} for v in all_variables],
        value=default_vars,
        multi=True,
        placeholder="Vælg variabler til parallel coordinates...",
        style={'width': '95%'}
    )], style={'margin': '10px'}),

    html.Div(id='legend-container',
             style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '15px',
                    'padding': '15px', 'background': '#f9f9f9', 'borderRadius': '8px',
                    'margin': '10px', 'minHeight': '50px'}),

    html.Div([
        dcc.Graph(id='parallel-plot',
                  figure=initial_parcoords,  # ← 100% grey from first pixel
                  style={'width': '72%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        html.Div(id='slider-container',
                 style={'width': '26%', 'display': 'inline-block', 'verticalAlign': 'top',
                        'paddingLeft': '20px', 'maxHeight': '600px', 'overflowY': 'auto'})
    ]),

    html.Div(id='matching-titles-output', style={'margin': '30px 10px'}),
    dcc.Store(id='color-store', data={})
])

# -----------------------------
# CALLBACKS
# -----------------------------
@app.callback(
    Output('treemap', 'figure'),
    Input('treemap-variable-selector', 'value')
)
def update_treemap(color_var):
    return create_treemap(color_var)

@app.callback(
    Output('line-selector', 'value'),
    Input('treemap', 'clickData'),
    State('line-selector', 'value')
)
def treemap_click(clickData, current):
    if current is None: current = []
    if clickData and clickData.get('points'):
        title = clickData['points'][0].get('label')
        if title and title in dat['titel'].values and title not in current:
            current = current + [title]
    return current

@app.callback(
    Output('parallel-plot', 'figure'),
    Output('slider-container', 'children'),
    Output('color-store', 'data'),
    Output('legend-container', 'children'),
    Input('line-selector', 'value'),
    Input('variable-selector', 'value'),
    Input({'type': 'slider', 'index': ALL}, 'value'),
    State({'type': 'slider', 'index': ALL}, 'id'),
    State('color-store', 'data')
)
def update_main(selected_titles, selected_vars, slider_vals, slider_ids, previous_color_map):
    if selected_titles is None: selected_titles = []
    if selected_vars is None: selected_vars = default_vars
    previous_color_map = previous_color_map or {}

    color_map = build_color_map_for_selected(selected_titles, previous_color_map)

    current_sliders = {}
    if slider_ids and slider_vals:
        for sid, val in zip(slider_ids, slider_vals):
            if val:
                current_sliders[sid['index']] = val

    slider_filter = {}
    sliders_ui = []

    for col in selected_vars:
        is_likert = col not in ['afbrud','tidsforbrug_p50','tidsforbrug_arbejde',
                                'arbejdstid_timer','ledighed_nyudd','maanedloen_nyudd','maanedloen_10aar']

        # BOTH handles start at maximum
        default_val = [5, 5] if is_likert else [dat[col].max(), dat[col].max()]
        value = current_sliders.get(col, default_val)

        # Only filter if moved from max
        if value != default_val:
            slider_filter[col] = tuple(value)

        if is_likert:
            sliders_ui.append(html.Div([
                html.Label(col.replace('_', ' '), style={'fontWeight': '600'}),
                dcc.RangeSlider(
                    id={'type': 'slider', 'index': col},
                    min=1, max=5, step=0.1,
                    value=value,
                    marks={i: str(i) for i in range(1,6)},
                )
            ], style={'marginBottom': '25px'}))
        else:
            mn, mx = dat[col].min(), dat[col].max()
            step = max((mx - mn) / 100, 0.01)
            marks = {int(v): f"{int(v):,}" for v in [20000,40000,60000,80000] if mn <= v <= mx}
            sliders_ui.append(html.Div([
                html.Label(col.replace('_', ' '), style={'fontWeight': '600'}),
                dcc.RangeSlider(
                    id={'type': 'slider', 'index': col},
                    min=mn, max=mx, step=step,
                    value=value,
                    marks=marks,
                    tooltip={"placement": "bottom", "always_visible": True}
                )
            ], style={'marginBottom': '25px'}))

    fig, _ = create_parcoords(selected_titles, slider_filter, selected_vars, color_map)

    if selected_titles:
        legend_items = [
            html.Div([
                html.Div(style={
                    'width': '18px', 'height': '18px', 'background': color_map.get(t, '#E8E8E8'),
                    'borderRadius': '4px', 'marginRight': '10px', 'boxShadow': '0 1px 3px rgba(0,0,0,0.2)'
                }),
                html.Span(t, style={'fontSize': '14px', 'verticalAlign': 'middle'})
            ], style={'display': 'flex', 'alignItems': 'center'})
            for t in selected_titles
        ]
        legend = html.Div(legend_items, style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '15px'})
    else:
        legend = html.Div("Ingen uddannelser valgt endnu.", style={'color': '#888', 'fontStyle': 'italic', 'fontSize': '15px'})

    return fig, sliders_ui, color_map, legend

@app.callback(
    Output('matching-titles-output', 'children'),
    Input('line-selector', 'value'),
    Input({'type': 'slider', 'index': ALL}, 'value'),
    State({'type': 'slider', 'index': ALL}, 'id'),
    State('color-store', 'data')
)
def update_links(selected_titles, slider_vals, slider_ids, color_map):
    if selected_titles is None: selected_titles = []
    color_map = color_map or {}
    slider_filter = {}
    if slider_ids and slider_vals:
        for sid, val in zip(slider_ids, slider_vals):
            if val and val[0] != val[1]:
                col = sid['index']
                is_likert = col not in ['afbrud','tidsforbrug_p50','tidsforbrug_arbejde',
                                        'arbejdstid_timer','ledighed_nyudd','maanedloen_nyudd','maanedloen_10aar']
                default_max = 5 if is_likert else dat[col].max()
                if val != [default_max, default_max]:
                    slider_filter[col] = val

    filtered = dat.copy()
    if slider_filter:
        for col, (lo, hi) in slider_filter.items():
            filtered = filtered[(filtered[col] >= lo) & (filtered[col] <= hi)]
    slider_matches = filtered[['titel','url']].drop_duplicates().to_dict('records') if not filtered.empty else []
    selected_matches = dat[dat['titel'].isin(selected_titles)][['titel','url']].drop_duplicates().to_dict('records')

    def make_link(rec, color=None):
        url = rec['url'] if str(rec['url']).startswith('http') else 'https://' + str(rec['url'])
        return html.A(rec['titel'], href=url, target="_blank",
                      style={'color': color or '#87CEFA', 'textDecoration': 'none', 'fontWeight': '500', 'marginRight': '15px'})

    return html.Div([
        html.Div([html.Strong("Valgte uddannelser:"), html.Div([make_link(r, color_map.get(r['titel'])) for r in selected_matches] or "Ingen")]),
        html.Br(),
        html.Div([html.Strong("Matcher filtre (lyseblå):"), html.Div([make_link(r) for r in slider_matches] or "Ingen matcher")])
    ], style={'lineHeight': '2'})

# -----------------------------
# RUN
# -----------------------------
if __name__ == '__main__':
    app.run_server(debug=True)