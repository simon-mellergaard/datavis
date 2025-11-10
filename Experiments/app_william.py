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
# VARIABLES FOR PARCOORDS
# -----------------------------
all_variables = [
    'fagligmiljo_likert','arbmedstud_likert','medstuderende_likert','udbytte_undervisning_likert',
    'socialtmiljo_likert','ensom_likert','stress_daglig_likert','tilpas_likert',
    'undervisere_engagerede_likert','undervisere_feedback_likert','undervisere_hjaelp_likert','undervisere_kontakt_likert',
    'afbrud','tidsforbrug_p50','tidsforbrug_arbejde',
    'arbejdstid_timer','ledighed_nyudd','maanedloen_nyudd','maanedloen_10aar'
]

default_vars = all_variables[:5]  # Start with first 5 variables

# -----------------------------
# BUILD TREEMAP
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
    fig.update_layout(margin=dict(t=10,l=10,r=10,b=10), height=400)
    return fig

# -----------------------------
# CREATE PARCOORDS FIGURE
# -----------------------------
def create_parcoords(selected_titles=[], slider_filter={}, selected_vars=None):
    if selected_vars is None:
        selected_vars = default_vars

    # Build line colors
    line_colors = []
    for _, row in dat.iterrows():
        if row['titel'] in selected_titles:
            line_colors.append(1.0)
        elif slider_filter:
            match = True
            for col, (low, high) in slider_filter.items():
                if not (low <= row[col] <= high):
                    match = False
                    break
            line_colors.append(0.6 if match else 0.0)
        else:
            line_colors.append(0.0)

    # Build dimensions dynamically
    dimensions = []
    for col in selected_vars:
        values = dat[col]
        if values.max() > 5:  # Continuous
            dim = dict(range=[values.min(), values.max()], label=col, values=values)
        else:  # Likert 1-5
            dim = dict(range=[1,5], label=col, values=values)
        dimensions.append(dim)

    fig = go.Figure(
        go.Parcoords(
            line=dict(color=line_colors, colorscale=[[0,'lightgrey'],[0.6,'#87CEFA'],[1,'firebrick']], cmin=0, cmax=1),
            dimensions=dimensions
        )
    )
    fig.update_layout(margin=dict(l=80,r=80,t=40,b=40), height=600)
    return fig

# -----------------------------
# DASH APP
# -----------------------------
app = dash.Dash(__name__)

# Dropdown to select variables for treemap coloring (single selection)
treemap_variable_selector = dcc.Dropdown(
    id='treemap-variable-selector',
    options=[{'label': v, 'value': v} for v in all_variables],
    value='maanedloen_nyudd',
    multi=False,
    placeholder="Select variable for treemap color"
)

# Dropdown to select variables for parallel coordinates
variable_selector = dcc.Dropdown(
    id='variable-selector',
    options=[{'label': v, 'value': v} for v in all_variables],
    value=default_vars,
    multi=True,
    placeholder="Select variables for parallel coordinates"
)

# Sliders will be generated dynamically based on selected variables
def generate_sliders(selected_vars):
    slider_components = []
    for col in selected_vars:
        if col not in ['afbrud','tidsforbrug_p50','tidsforbrug_arbejde','arbejdstid_timer','ledighed_nyudd','maanedloen_nyudd','maanedloen_10aar']:
            # Likert 1-5
            slider_components.append(
                html.Div([
                    html.Label(col),
                    dcc.RangeSlider(
                        id={'type':'slider','index':col},
                        min=1,
                        max=5,
                        step=0.1,
                        value=[1,1],
                        marks={i:str(i) for i in range(1,6)}
                    )
                ], style={'margin-bottom':'10px','width':'180px'})
            )
        else:
            # Continuous
            min_val = dat[col].min()
            max_val = dat[col].max()
            step_val = (max_val-min_val)/50
            marks = {int(i): str(int(i)) for i in [20000,30000,40000,50000,60000] if i <= max_val}
            slider_components.append(
                html.Div([
                    html.Label(col),
                    dcc.RangeSlider(
                        id={'type':'slider','index':col},
                        min=min_val,
                        max=max_val,
                        step=step_val,
                        value=[min_val,min_val],
                        marks=marks
                    )
                ], style={'margin-bottom':'10px','width':'180px'})
            )
    return slider_components

# -----------------------------
# LAYOUT
# -----------------------------
app.layout = html.Div([
    html.Label("Vælg variabel for treemap farve:"),
    treemap_variable_selector,
    dcc.Graph(id='treemap', figure=create_treemap()),
    html.Label("Søg og vælg uddannelser at fremhæve:"),
    dcc.Dropdown(
        id='line-selector',
        options=[{'label': t, 'value': t} for t in sorted(dat['titel'].unique())],
        multi=True,
        placeholder="Søg efter titel..."
    ),
    html.Label("Vælg variabler for parallel coordinates:"),
    variable_selector,
    html.Div([dcc.Graph(id='parallel-plot', style={'width':'75%','display':'inline-block'}),
              html.Div(id='slider-container', style={'width':'22%','float':'right','margin-left':'2%'})
             ]),
    html.Div(id='matching-titles-output', style={'margin-top':'20px'})
], style={'max-width':'1200px','margin':'0 auto'})

# -----------------------------
# CALLBACKS
# -----------------------------
@app.callback(
    Output('treemap','figure'),
    Input('treemap-variable-selector','value')
)
def update_treemap(color_var):
    return create_treemap(color_var)

@app.callback(
    Output('line-selector','value'),
    Input('treemap','clickData'),
    State('line-selector','value')
)
def treemap_click(clickData, selected_titles):
    if selected_titles is None:
        selected_titles = []
    if clickData and 'points' in clickData:
        clicked = clickData['points'][0]['label']
        if clicked in dat['titel'].values and clicked not in selected_titles:
            selected_titles.append(clicked)
    return selected_titles

@app.callback(
    Output('parallel-plot','figure'),
    Output('slider-container','children'),
    Input('line-selector','value'),
    Input({'type':'slider','index':ALL}, 'value'),
    Input('variable-selector', 'value'),
    State({'type':'slider','index':ALL}, 'id'),
    State({'type':'slider','index':ALL}, 'value')
)
def update_parcoords(selected_titles, slider_values, selected_vars, slider_ids, slider_states):
    prev_values = {s['index']: v for s, v in zip(slider_ids, slider_states)} if slider_ids else {}
    sliders = []
    slider_filter = {}

    for col in selected_vars:
        val = prev_values.get(col, [1,1] if col not in ['afbrud','tidsforbrug_p50','tidsforbrug_arbejde','arbejdstid_timer','ledighed_nyudd','maanedloen_nyudd','maanedloen_10aar'] else [dat[col].min(), dat[col].min()])
        if val[0] != val[1]:
            slider_filter[col] = val

        if col not in ['afbrud','tidsforbrug_p50','tidsforbrug_arbejde','arbejdstid_timer','ledighed_nyudd','maanedloen_nyudd','maanedloen_10aar']:
            sliders.append(
                html.Div([html.Label(col), dcc.RangeSlider(id={'type':'slider','index':col}, min=1, max=5, step=0.1, value=val, marks={i:str(i) for i in range(1,6)})], style={'margin-bottom':'10px','width':'180px'})
            )
        else:
            min_val, max_val = dat[col].min(), dat[col].max()
            step_val = (max_val - min_val)/50
            marks = {int(i): str(int(i)) for i in [20000,30000,40000,50000,60000] if i <= max_val}
            sliders.append(
                html.Div([html.Label(col), dcc.RangeSlider(id={'type':'slider','index':col}, min=min_val, max=max_val, step=step_val, value=val, marks=marks)], style={'margin-bottom':'10px','width':'180px'})
            )

    fig = create_parcoords(selected_titles or [], slider_filter, selected_vars)
    return fig, sliders

@app.callback(
    Output('matching-titles-output','children'),
    Input('line-selector','value'),
    Input({'type':'slider','index':ALL}, 'value'),
    State({'type':'slider','index':ALL}, 'id')
)
def print_matching_titles(selected_titles, slider_values, slider_ids):
    slider_filter = {s['index']: val for s, val in zip(slider_ids, slider_values) if val[0] != val[1]}
    if slider_filter:
        filtered = dat.copy()
        for col, (low, high) in slider_filter.items():
            filtered = filtered[(filtered[col] >= low) & (filtered[col] <= high)]
        slider_matches = filtered[['titel','url']].to_dict('records')
    else:
        slider_matches = []

    selected_records = dat[dat['titel'].isin(selected_titles)][['titel','url']].to_dict('records') if selected_titles else []

    def create_links(records, color):
        links = []
        for r in records:
            url = r['url']
            if not url.startswith('http'):
                url = 'https://' + url
            links.append(html.Div(html.A(r['titel'], href=url, target="_blank", style={'color':color})))
        return links or [html.Div("None")]

    return html.Div([
        html.B("Matching titles from selection:"),
        html.Div(create_links(selected_records, 'firebrick')),
        html.B("Matching titles from sliders:"),
        html.Div(create_links(slider_matches, '#87CEFA'))
    ])

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == '__main__':
    app.run_server(debug=True)
