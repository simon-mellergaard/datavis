import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import numpy as np
import panel as pn

# ---------- Import data ----------
df_raw = pd.read_excel('../Data/DATA_UFM_combined_TEST_AREA_filled_V2.xlsx', header=0)

# ---------- Columns to keep ----------
cols = [
    'artikel_id','udbud_id','titel','educational_category','displaydocclass','hovedinsttx',
    'instregiontx','instkommunetx','optagne','kvote_1_kvotient','standby_8',
    'fagligmiljo_likert','arbmedstud_likert','medstuderende_likert','udbytte_undervisning_likert',
    'socialtmiljo_likert','ensom_likert','stress_daglig_likert','tilpas_likert',
    'undervisere_engagerede_likert','undervisere_feedback_likert','undervisere_hjaelp_likert',
    'undervisere_kontakt_likert','afbrud','tidsforbrug_p50','tidsforbrug_arbejde',
    'uddaktivitet_opgaver_pct','uddaktivitet_praktik_pct','uddaktivitet_udlandsophold_pct',
    'uddaktivitet_undervisning_pct',
    'undervisningsform_p1','undervisningsform_p2','undervisningsform_p3','undervisningsform_p4','undervisningsform_p5',
    'foerstejob1tx','foerstejob2tx','foerstejob3tx','foerstejob4tx',
    'jobskabende_p1','jobskabende_p2','jobskabende_p3','jobskabende_p4','jobskabende_p5',
    'kompetencerudd_p1','kompetencerudd_p2','kompetencerudd_p3','kompetencerudd_p4','kompetencerudd_p5',
    'ledighed_nyudd','maanedloen_nyudd','maanedloen_10aar',
    'hyppigsteid1','hyppigsteid2','hyppigsteid3','kandidat_titler','kandidat_refs','cluster_label',
    'inst_lat','inst_lon'
]


cols = [c for c in cols if c in df_raw.columns]
data = df_raw[cols].copy()

# ---------- Load cluster mapping ----------
mapping = pd.read_excel("../Data/education_cluster_mapping.xlsx")
mapping['titel'] = mapping['titel'].astype(str).str.strip()

# ---------- NATIONAL base (used by radar/bars/sankey) ----------
data_whole_edu = data[data['udbud_id'] == 999999].copy()
data_whole_edu['titel'] = data_whole_edu['titel'].astype(str).str.strip()
data_whole_edu = data_whole_edu.merge(mapping, on='titel', how='left').drop_duplicates(subset=['titel'])

df = data_whole_edu.copy()
df = df.dropna(subset=['titel'])
df['titel'] = df['titel'].astype(str).str.strip()

# ---------- PROVIDER-LEVEL base for CITY treemap ----------
def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(',', '.', regex=False), errors='coerce')

df_prov = data[data['udbud_id'] != 999999].copy()
df_prov['titel'] = df_prov['titel'].astype(str).str.strip()
df_prov = df_prov.merge(mapping, on='titel', how='left')

df_prov['optagne_num']        = to_num(df_prov.get('optagne'))
df_prov['maanedloen_nyudd_n'] = to_num(df_prov.get('maanedloen_nyudd'))
df_prov['ledighed_nyudd_n']   = to_num(df_prov.get('ledighed_nyudd'))

CITY_LIST    = sorted(df_prov['instkommunetx'].dropna().astype(str).unique())
CITY_OPTIONS = [{'label': 'Alle kommuner', 'value': '__ALL__'}] + \
               [{'label': c, 'value': c} for c in CITY_LIST]

# The dictionary should consist a list of [clean name, aggregation type, name short]
col_name_info = {
    'optagne': ('Antal optagene', 'sum', 'Optagne'),
    'maanedloen_nyudd': ('Nyuddanet gennemsnitsløn', 'mean', 'Løn (nyudd.) (gennemsnit)'),
    'ledighed_nyudd': ('ledighed_nyudd_n', 'mean', 'Ledighed (nyudd.) (gennemsnit)')
}


# ---------- kandidat_* backfill if missing ----------
def norm_udbud(x):
    try: return str(int(x))
    except Exception: return str(x)

def parse_ref(s):
    if pd.isna(s): return None
    s = str(s)
    if ':' in s:
        a,u = s.split(':',1)
        return (a.strip(), norm_udbud(u.strip()))
    return None

if 'kandidat_titler' not in df.columns or 'kandidat_refs' not in df.columns:
    ref_src = df_raw.copy()
    ref_src['artikel_id'] = ref_src['artikel_id'].astype(str)
    ref_src['udbud_id_str'] = ref_src['udbud_id'].apply(norm_udbud)
    ref_index = ref_src.set_index(['artikel_id','udbud_id_str'])
    kand_titles, kand_refs = [], []
    for _, row in df.iterrows():
        titles, keys = [], []
        for c in ['hyppigsteid1','hyppigsteid2','hyppigsteid3']:
            if c not in df.columns: continue
            t = parse_ref(row.get(c))
            if t and t in ref_index.index:
                target = ref_index.loc[t]
                if 'Kandidat' in str(target['displaydocclass']):
                    title = str(target['titel']).strip()
                    key = f"{t[0]}:{t[1]}"
                    if title and title not in titles: titles.append(title)
                    if key not in keys: keys.append(key)
        kand_titles.append(" | ".join(titles))
        kand_refs.append(" | ".join(keys))
    df['kandidat_titler'] = kand_titles
    df['kandidat_refs']   = kand_refs

# ---------- AVAILABLE TITLES for other selectors ----------
available_titles_all = df_prov.dropna(subset=['educational_category','cluster_label','titel'])['titel'] \
                           .dropna().astype(str).unique()
AVAILABLE_TITLES  = sorted(available_titles_all)
AVAILABLE_OPTIONS = [{"label": t, "value": t} for t in AVAILABLE_TITLES]
AVAILABLE_SET     = set(AVAILABLE_TITLES)

bachelor_titles_multi = sorted(
    set(df.loc[(df['displaydocclass']=='Bacheloruddannelse') & (df['udbud_id']==999999), 'titel']
        .dropna().astype(str).unique()) & AVAILABLE_SET
)

CUSTOM_BG = "#0f1115"
PLOT_BG   = "#0f1115"
FONT_COL  = "#ffffff"


select_size = pn.widgets.Select(name='SIZE MARKER', options=['optagne', 'maanedloen_nyudd'])
select_color = pn.widgets.Select(name='COLOR MARKER', options=['optagne', 'maanedloen_nyudd'])



# ---------- Treemap builder (CITY + METRIC)  [FIXED AGG] ----------
levels = ['titel', 'cluster_label', 'educational_category']
def build_hierarchical_dataframe(df, levels, value_column, color_column=None, addtional_cols=[]):
    """
    Build a hierarchy of levels for Sunburst or Treemap charts.

    Levels are given starting from the bottom to the top of the hierarchy,
    ie the last level corresponds to the root.
    """
    df_list = []
    for i, level in enumerate(levels):
        df_tree = pd.DataFrame(columns=['id', 'label', 'parent', 'value', 'color'])
        # dfg = df.groupby(levels[i:]).mean(numeric_only=True)
        dfg = df.groupby(levels[i:]).sum()
        dfg['tmp'] = df.groupby(levels[i:]).count()[value_column]
        dfg['tmp2'] = df.groupby(levels[i:]).count()[color_column]
        dfg = dfg.reset_index()
        df_tree['label'] = dfg[level].copy()
        # Make ids and parents
        df_tree['id'] = dfg[level].copy()
        for j in range(i+1, len(levels)):
            df_tree['id'] = dfg[levels[j]].copy() + "/" + df_tree['id']
        if i < len(levels) - 1:
            df_tree['parent'] = dfg[levels[i+1]].copy()
            j = i+1
            while j < len(levels) - 1:
                df_tree['parent'] = dfg[levels[j+1]].copy() + "/" + df_tree['parent']
                j += 1
        else:
            df_tree['parent'] = ''
        
        if col_name_info[value_column][1] == 'sum' or i != 0:
            df_tree['value'] = dfg[value_column] 
        else:
            df_tree['value'] = dfg[value_column] / dfg['tmp']
        if col_name_info[color_column][1] == 'sum' or i != 0:
            df_tree['color'] = dfg[color_column]
        else:
            df_tree['color'] = dfg[color_column] / dfg['tmp2']
        for ac in addtional_cols:
            df_tree[ac] = dfg[ac] / dfg['tmp']
        df_list.append(df_tree)
    # total = pd.Series(dict(label='total', parent='',
    #                           value=df[value_column].sum(),
    #                           color=df[color_columns].sum()), name=0)
    # df_list.append(total)
    df_all_trees = pd.concat(df_list, ignore_index=True)
    return df_all_trees

df_tree = df[['titel', 'cluster_label', 'optagne', 'maanedloen_nyudd', 'fagligmiljo_likert', 'educational_category']]
df_tree = df_tree.dropna()





def build_city_treemap(city_value, metric_col, additional_cols=[]):
    all_cols = [metric_col] + additional_cols
    # filter by city (or all)
    if city_value and city_value != '__ALL__':
        df_sel = df_prov[df_prov['instkommunetx'] == city_value].copy()
    else:
        df_sel = df_prov.copy()

    # require taxonomy + metric
    df_sel = df_sel.dropna(subset=['educational_category','cluster_label','titel'])
    df_sel = df_sel[~df_sel[metric_col].isna()]
    df_sel = df_sel.drop_duplicates()
    # aggregate
    grouped = (df_sel
                .groupby(['educational_category','cluster_label','titel'], as_index=False)[all_cols]
                .sum())
                # .rename(columns={metric_col: 'size'}))

    grouped = grouped[np.isfinite(grouped[metric_col])]
    grouped = grouped[grouped[metric_col] > 0]

    title_txt = f"{metric_col} — " + (city_value if city_value != '__ALL__' else "Alle kommuner")
    
    df_new = build_hierarchical_dataframe(grouped, levels, metric_col, metric_col)

    fig = go.Figure(go.Treemap(
        ids=df_new['id'],
        labels=df_new['label'],
        parents=df_new['parent'],
        values=df_new['value'],
        customdata=df_new,
        branchvalues='total',
        marker=dict(
            colors=df_new['color'],
            colorscale='Blues',
            pad=dict(b=1, l=1, r=1, t=18),              # padding around each tile
            line=dict(width=1, color='darkgrey'),  # border line around each tile
            # pattern=dict(shape=["|"], solidity=0.80)
            # pattern=dict(
            #     shape='x' if df_new['id']=='Universitetsuddannelser/IT - teknik - produktion/Actuarial Mathematics' else '',  # Apply 'x' pattern only to Tile C
            # )
            ),
        hovertemplate=f'<b>%{{label}} </b> <br> {col_name_info[metric_col][2]}: %{{value:,.0f}} kr. <br> Faglig miljø: %{{color:.2f}}<extra>this is in the extra thing%{{fullData.name}}</extra>',
        name='',
        # textinfo = "label+value+percent parent+percent entry",
        root_color="lightgrey",
        texttemplate=f'<b>%{{label}}</b><br>{col_name_info[metric_col][2]}: %{{value:,.0f}}<br>The parent: %{{percentParent:.1%}} and custom data is:  %{{customdata[4]}}',
        maxdepth=3,
        
        ))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=CUSTOM_BG, plot_bgcolor=PLOT_BG, font_color=FONT_COL,
        margin=dict(t=50,l=30,r=50,b=20), title=title_txt
    )
    fig.update_coloraxes(colorbar=dict(title=metric_col,
                                       tickfont=dict(color=FONT_COL),
                                       titlefont=dict(color=FONT_COL)))
    fig.update_traces(root_color="#1c1f26",
                      marker_colorbar=dict(tickfont=dict(color=FONT_COL),
                                           titlefont=dict(color=FONT_COL),
                                           outlinecolor="#2a2f3a"))
    print(df_new.head())
    print(len(df_new))
    print(df_sel.head())
    print(len(df_sel))
    return fig

fig = build_city_treemap(city_value='__ALL__', metric_col=select_size.value, additional_cols=['fagligmiljo_likert'])
# fig = build_city_treemap(city_value='__ALL__', metric_col='optagne', additional_cols=['fagligmiljo_likert'])
print(select_size.value)

# Create a Panel pane that wraps the Plotly figure
plot = pn.pane.Plotly(fig, sizing_mode="stretch_both")
# Craetea a panel figure that depends on the select_size value
def update_plot(event):
    new_fig = build_city_treemap(city_value='__ALL__', metric_col=select_size.value, additional_cols=['fagligmiljo_likert'])
    plot.object = new_fig
select_size.param.watch(update_plot, 'value')


# (Optional) Add widgets or layout if you want
title = pn.pane.Markdown("# Its a treemap")
selections = pn.Row(select_size, select_color)
layout = pn.Column(title, selections, plot)

# Make a text field under the plot
text_field = pn.widgets.TextInput(name="Description", placeholder="Enter description here...")

# Add the text field to the layout
layout.append(text_field)

# Add markdown text below
layout.append(pn.pane.Markdown(f"### Additional Information\nYou can add more details about the treemap here.{select_size.value}"))

# Serve the app
layout.servable()




