import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import webbrowser

# -----------------------------
# LOAD DATA
# -----------------------------
df_raw = pd.read_excel('../Data/DATA_UFM_combined_cluster.xlsx', header=0)

cols = [
    'udbud_id', 'titel', 'educational_category', 'cluster_label',
    'fagligmiljo_likert', 'arbmedstud_likert', 'medstuderende_likert',
    'udbytte_undervisning_likert','socialtmiljo_likert','ensom_likert',
    'stress_daglig_likert','tilpas_likert',
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
default_vars = all_variables[:5]

# -----------------------------
# TREEMAP
# -----------------------------
def create_treemap(color_var='maanedloen_nyudd'):
    leaf = dat.groupby(['educational_category', 'cluster_label','titel'], as_index=False).agg({color_var:'mean'})
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
# PARALLEL COORDS (Scatter)
# -----------------------------
def create_parallel_scatter(selected_titles, selected_vars):
    if not selected_vars or not selected_titles:
        return go.Figure()

    x_coords = list(range(len(selected_vars)))
    fig = go.Figure()

    # Add Likert vertical lines
    for i, var in enumerate(selected_vars):
        for y in range(1,6):
            fig.add_shape(
                type='line',
                x0=i, x1=i, y0=y, y1=y,
                line=dict(color='lightgrey', width=1),
            )
        fig.add_annotation(
            x=i, y=5.2, text=var, showarrow=False, yanchor='bottom'
        )

    # Add one trace per selected title
    df_sel = dat[dat['titel'].isin(selected_titles)]
    for _, row in df_sel.iterrows():
        y_values = [row[feat] for feat in selected_vars]
        fig.add_trace(
            go.Scatter(
                x=x_coords,
                y=y_values,
                mode='lines+markers',
                name=row['titel'],
                text=[f"{feat}: {row[feat]}<br>Title: {row['titel']}" for feat in selected_vars],
                hoverinfo='text',
                line=dict(width=2),
                marker=dict(size=6),
                customdata=[row['url']] * len(selected_vars)  # store URL
            )
        )

    fig.update_layout(
        xaxis=dict(tickvals=x_coords, ticktext=['']*len(selected_vars), showgrid=False),
        yaxis=dict(title='Value', range=[3,5], dtick=1, showgrid=True),
        height=600,
        margin=dict(l=80,r=80,t=40,b=40),
        dragmode=False,  # disable drag/zoom
        hovermode='closest'
    )
    return fig

# -----------------------------
# DASH APP
# -----------------------------
app = dash.Dash(__name__)

app.layout = html.Div([
    html.Label("Vælg variabel for treemap farve:"),
    dcc.Dropdown(
        id='treemap-variable-selector',
        options=[{'label': v, 'value': v} for v in all_variables],
        value='maanedloen_nyudd',
        multi=False
    ),
    dcc.Graph(id='treemap', figure=create_treemap()),

    html.Label("Søg og vælg uddannelser at fremhæve:"),
    dcc.Dropdown(
        id='line-selector',
        options=[{'label': t, 'value': t} for t in sorted(dat['titel'].unique())],
        multi=True
    ),

    html.Label("Vælg variabler for parallel coordinates:"),
    dcc.Dropdown(
        id='variable-selector',
        options=[{'label': v, 'value': v} for v in all_variables],
        value=default_vars,
        multi=True
    ),

    dcc.Graph(
        id='parallel-plot',
        config={'displayModeBar': True, 'displaylogo': False, 'modeBarButtonsToRemove': ['lasso2d', 'select2d', 'zoom', 'pan', 'zoomIn', 'zoomOut', 'autoScale', 'resetScale']}
    )
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
    Input('line-selector','value'),
    Input('variable-selector','value')
)
def update_parallel(selected_titles, selected_vars):
    return create_parallel_scatter(selected_titles or [], selected_vars or [])

# -----------------------------
# CLIENT-SIDE: OPEN URL ON CTRL+CLICK
# -----------------------------
app.clientside_callback(
    """
    function(clickData) {
        if (clickData && clickData.points && clickData.points.length > 0) {
            const point = clickData.points[0];
            if (window.event && window.event.ctrlKey && point.customdata) {
                window.open(point.customdata, '_blank');
            }
        }
        return null;
    }
    """,
    Output('treemap','clickData'),
    Input('parallel-plot','clickData')
)

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == '__main__':
    app.run_server(debug=True)


#I now want vertical lines for each axis, automatic zoom in to min/max for each axis /clickable links to UG somewhere (maybe ctrl + click)
#then afterwards what jonas did for treemap - i.e geographical + grades - and simplify so it's only likert scales