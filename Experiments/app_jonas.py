import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import numpy as np

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

SIZE_METRICS = {
    'optagne': ('optagne_num', 'sum', 'Optagne (sum)'),
    'maanedloen_nyudd': ('maanedloen_nyudd_n', 'mean', 'Løn (nyudd.) (gennemsnit)'),
    'ledighed_nyudd': ('ledighed_nyudd_n', 'mean', 'Ledighed (nyudd.) (gennemsnit)')
}
SIZE_OPTIONS = [{'label': v[2], 'value': k} for k, v in SIZE_METRICS.items()]

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

# ---------- Theme ----------
CUSTOM_BG = "#0f1115"
PLOT_BG   = "#0f1115"

# brighter text color for readability
FONT_COL  = "#ffffff"

CUSTOM_CARD = {
    "padding":"8px",
    "backgroundColor":"#11151b",
    "border":"1px solid #2a2f3a",
    "borderRadius":"8px"
}

# ---------- Radar (Likert; raw values) ----------
radar_vars = [
    ('fagligmiljo_likert', 'Fagligt miljø'),
    ('socialtmiljo_likert', 'Socialt miljø'),
    ('stress_daglig_likert', 'Stress'),
    ('ensom_likert', 'Ensomhed'),
    ('ruster_til_job_likert', 'Ruster til job')
]
likert_values = []
for col, _ in radar_vars:
    if col in df.columns:
        likert_values.append(df[col].values)
likert_values = np.concatenate([v[~pd.isna(v)] for v in likert_values]) if len(likert_values)>0 else np.array([1,5])
rad_min = float(np.nanmax([1, np.nanmin(likert_values)]))
rad_max = float(np.nanmin([5, np.nanmax(likert_values)]))
if rad_min >= rad_max: rad_min, rad_max = 1.0, 5.0

# ---------- Color helper ----------
def bar_colors(n):
    t = [i/(n-1) if n>1 else 0 for i in range(n)]
    return px.colors.sample_colorscale(px.colors.sequential.Blues_r, t)

# ---------- KPI bar helper (FIX ADDED) ----------
def build_simple_bar(metric, titles, title_txt, tickprefix=""):
    sel_titles = [t for t in titles if t in AVAILABLE_SET]
    sel = df[df['titel'].isin(sel_titles)]
    fig = go.Figure()
    if not sel.empty and metric in sel.columns:
        colors = bar_colors(len(sel))
        fig.add_trace(go.Bar(
            x=sel['titel'], y=sel[metric],
            marker=dict(color=colors),
            hovertemplate="<b>%{x}</b><br>" + title_txt + ": %{y:.2f}<extra></extra>"
        ))
    fig.update_layout(
        title=title_txt,
        template="plotly_dark", paper_bgcolor=CUSTOM_BG, plot_bgcolor=PLOT_BG, font_color=FONT_COL,
        margin=dict(t=40, l=40, r=20, b=70),
        xaxis=dict(tickangle=20),
        yaxis=dict(tickprefix=tickprefix)
    )
    return fig

# ---------- Radar builder ----------
def build_radar_raw(titles):
    fig = go.Figure()
    theta = [lbl for _, lbl in radar_vars]
    theta_closed = theta + [theta[0]]
    for t in titles:
        row = df[df['titel'] == t]
        if row.empty: continue
        r = []
        for col, _lbl in radar_vars:
            val = row[col].iloc[0] if col in row.columns else np.nan
            r.append(0.0 if pd.isna(val) else float(val))
        r_closed = r + [r[0]]
        fig.add_trace(go.Scatterpolar(
            r=r_closed, theta=theta_closed, mode='lines+markers',
            name=t, fill='toself'
        ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=CUSTOM_BG, plot_bgcolor=PLOT_BG, font_color=FONT_COL,
        title="Radar (rå Likert-værdier)",
        polar=dict(
            bgcolor="#12151c",
            radialaxis=dict(visible=True, range=[rad_min, rad_max],
                            tickvals=[1,2,3,4,5], gridcolor="#2a2f3a"),
            angularaxis=dict(gridcolor="#2a2f3a")
        ),
        legend=dict(orientation='v', x=1.02, xanchor='left', y=1),
        margin=dict(t=40, l=30, r=30, b=30),
    )
    return fig

# ---------- Flow helpers ----------
def _norm_udbud(x):
    try: return str(int(x))
    except Exception: return str(x)

def _parse_ref(s):
    if pd.isna(s): return None
    s = str(s)
    if ":" in s:
        a,u = s.split(":",1)
        return (a.strip(), _norm_udbud(u.strip()))
    return None

df_raw_lu = df_raw.copy()
df_raw_lu['artikel_id'] = df_raw_lu['artikel_id'].astype(str)
df_raw_lu['udbud_id_str'] = df_raw_lu['udbud_id'].apply(_norm_udbud)
raw_idx = df_raw_lu.set_index(['artikel_id','udbud_id_str'])

def build_flow_df(selected_bachelors):
    if not selected_bachelors:
        return pd.DataFrame(columns=['bachelor','kandidat','weight','ledighed_nyudd','maanedloen_nyudd','maanedloen_10aar'])
    rows = []
    rank_weights = {'hyppigsteid1':3, 'hyppigsteid2':2, 'hyppigsteid3':1}
    for b in selected_bachelors:
        bro = df[(df['titel']==b) & (df['displaydocclass']=='Bacheloruddannelse') & (df['udbud_id']==999999)]
        if bro.empty:
            bro = df[(df['titel']==b) & (df['displaydocclass']=='Bacheloruddannelse')]
        if bro.empty: continue
        bro = bro.iloc[0]
        pairs, weights = [], []
        if 'kandidat_refs' in df.columns and isinstance(bro.get('kandidat_refs'), str) and bro['kandidat_refs'].strip():
            for part in bro['kandidat_refs'].split('|'):
                part = part.strip()
                if ':' in part:
                    a,u = part.split(':',1)
                    pairs.append((a.strip(), _norm_udbud(u.strip())))
                    weights.append(1)
        else:
            for c,w in rank_weights.items():
                t = _parse_ref(bro.get(c))
                if t:
                    pairs.append(t); weights.append(w)
        for (a,u), w in zip(pairs, weights):
            if (a,u) in raw_idx.index:
                r = raw_idx.loc[(a,u)]
                if 'Kandidat' in str(r['displaydocclass']):
                    rows.append({
                        'bachelor': b,
                        'kandidat': str(r['titel']).strip(),
                        'weight': w,
                        'ledighed_nyudd': r.get('ledighed_nyudd', np.nan),
                        'maanedloen_nyudd': r.get('maanedloen_nyudd', np.nan),
                        'maanedloen_10aar': r.get('maanedloen_10aar', np.nan)
                    })
    flow = pd.DataFrame(rows)
    if flow.empty: return flow
    flow = (flow.groupby(['bachelor','kandidat'], as_index=False)
                 .agg({'weight':'sum',
                       'ledighed_nyudd':'mean',
                       'maanedloen_nyudd':'mean',
                       'maanedloen_10aar':'mean'}))
    return flow

def build_sankey(flow: pd.DataFrame, selected_bachelors, top_k=20):
    if flow.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark",
                          paper_bgcolor=CUSTOM_BG, plot_bgcolor=PLOT_BG, font_color=FONT_COL)
        return fig
    agg = (flow.groupby('kandidat', as_index=False)['weight'].sum()
                 .sort_values('weight', ascending=False))
    keep_k = set(agg['kandidat'].head(top_k))
    flow2 = flow[flow['kandidat'].isin(keep_k)].copy()
    if flow2.empty: flow2 = flow.copy()

    bachelors = list(dict.fromkeys([b for b in selected_bachelors if b]))
    kandidater = sorted(flow2['kandidat'].unique().tolist())
    labels = bachelors + kandidater
    idx = {lab:i for i, lab in enumerate(labels)}

    sources = [idx[row['bachelor']] for _, row in flow2.iterrows()]
    targets = [idx[row['kandidat']] for _, row in flow2.iterrows()]
    values  = [row['weight'] for _, row in flow2.iterrows()]

    node_colors_left  = px.colors.sample_colorscale(px.colors.sequential.Blues_r,
                                                    [i/max(1, len(bachelors)-1) for i in range(len(bachelors))]) if bachelors else []
    node_colors_right = px.colors.sample_colorscale(px.colors.sequential.Blues,
                                                    [i/max(1, len(kandidater)-1) for i in range(len(kandidater))]) if kandidater else []
    node_colors = node_colors_left + node_colors_right

    custom = np.c_[flow2['ledighed_nyudd'], flow2['maanedloen_nyudd'], flow2['maanedloen_10aar']]
    link_hover = ("<b>%{source.label}</b> → <b>%{target.label}</b><br>"
                  "Vægt: %{value:.0f}"
                  "<br>Ledighed (nyudd.): %{customdata[0]:.1f}%"
                  "<br>Løn (nyudd.): %{customdata[1]:.0f}"
                  "<br>Løn (10 år): %{customdata[2]:.0f}<extra></extra>")

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, color=node_colors, pad=12, thickness=16,
                  line=dict(color="#2a2f3a", width=1)),
        link=dict(source=sources, target=targets, value=values,
                  customdata=custom, hovertemplate=link_hover)
    ))
    fig.update_layout(
        title="Flow chart: Bachelor → Kandidat (tykkelse = vægt)",
        template="plotly_dark", paper_bgcolor=CUSTOM_BG, plot_bgcolor=PLOT_BG, font_color=FONT_COL,
        margin=dict(t=50, l=10, r=20, b=20), height=480
    )
    return fig

# ---------- Detail panel helpers ----------
DETAIL_GROUPS = {
    "Undervisningsform": ['undervisningsform_p1','undervisningsform_p2','undervisningsform_p3','undervisningsform_p4','undervisningsform_p5'],
    "Jobskabende": ['jobskabende_p1','jobskabende_p2','jobskabende_p3','jobskabende_p4','jobskabende_p5'],
    "Kompetencer (udd.)": ['kompetencerudd_p1','kompetencerudd_p2','kompetencerudd_p3','kompetencerudd_p4','kompetencerudd_p5'],
}
DETAIL_NUMERIC = ['kvote_1_kvotient','standby_8']

def mode_str(s: pd.Series):
    s = s.dropna().astype(str)
    return s.value_counts().idxmax() if not s.empty else ""

def mean_fmt(s: pd.Series):
    v = to_num(s); v = v.dropna()
    return float(v.mean()) if not v.empty else None

def build_detail_table(df_all, edu_title):
    providers = df_all[(df_all['titel'].astype(str)==str(edu_title)) & (df_all['udbud_id']!=999999)].copy()
    if providers.empty:
        providers = df_all[df_all['titel'].astype(str)==str(edu_title)].copy()

    strings = { lbl: mode_str(providers.get(col, pd.Series(dtype=object))) for col, lbl in [
        ('foerstejob1tx','Første job #1'),
        ('foerstejob2tx','Første job #2'),
        ('foerstejob3tx','Første job #3'),
        ('foerstejob4tx','Første job #4'),
    ] }

    groups_out = {}
    for gname, cols in DETAIL_GROUPS.items():
        items = []
        for c in cols:
            if c in providers.columns:
                m = mean_fmt(providers[c])
                if m is not None: items.append((c, m))
                else:
                    ms = mode_str(providers[c])
                    if ms: items.append((c, ms))
        if items: groups_out[gname] = items

    numeric = {}
    for col in DETAIL_NUMERIC:
        if col in providers.columns:
            m = mean_fmt(providers[col])
            if m is not None: numeric[col] = m

    rows = [html.Tr([html.Th("Uddannelse"), html.Td(edu_title)])]
    for k,v in numeric.items():
        label = "Kvote 1 kvotient" if k=="kvote_1_kvotient" else ("Standby (8)" if k=="standby_8" else k)
        rows.append(html.Tr([html.Th(label), html.Td(f"{v:.2f}")]))

    if any(strings.values()):
        rows.append(html.Tr([html.Th("Første job (typisk)"),
                             html.Td(", ".join([s for s in strings.values() if s]))]))

    if 'kvote_1_kvotient' in providers.columns:
        tmp = providers.copy()
        tmp['kvote_num'] = to_num(tmp['kvote_1_kvotient'])
        tmp = tmp[tmp['kvote_num'].notna()]

        grp_keys = [c for c in ['hovedinsttx', 'instkommunetx'] if c in tmp.columns]
        if grp_keys:
            tmp = (tmp.sort_values('kvote_num', ascending=False)
                      .groupby(grp_keys, as_index=False).first())

        kv_rows = []
        for _, r in tmp.iterrows():
            inst = str(r.get('hovedinsttx', '') or '').strip()
            kommune = str(r.get('instkommunetx', '') or '').strip()
            kv_val = float(r['kvote_num'])
            label = f"{inst} ({kommune}) — {kv_val:.2f}" if kommune else f"{inst} — {kv_val:.2f}"
            kv_rows.append(html.Li(label))
        if kv_rows:
            rows.append(html.Tr([html.Th("Kvote 1 pr. sted"),
                                 html.Td(html.Ul(kv_rows))]))

    table = html.Table([html.Tbody(rows)], style={"width":"100%","borderCollapse":"collapse"})

    keep_cols = ['hovedinsttx','instkommunetx','instregiontx','udbud_id','artikel_id','titel',
                 'kvote_1_kvotient','standby_8','inst_lat','inst_lon']
    keep_cols = [c for c in keep_cols if c in providers.columns]
    providers_small = providers[keep_cols].copy()
    return table, providers_small

# ---- Municipality fallback for map (lat, lon) ----
MUNICIPALITY_COORDS = {
    "København": (55.6761, 12.5683),
    "Aarhus":    (56.1629, 10.2039),
    "Odense":    (55.4038, 10.4023),
    "Aalborg":   (57.0488,  9.9217),
    "Esbjerg":   (55.4767,  8.4520),
    "Roskilde":  (55.6415, 12.0803),
    "Kolding":   (55.4904,  9.4721),
}

def _ensure_latlon_from_municipality(df_in: pd.DataFrame) -> pd.DataFrame:
    df = df_in.copy()
    if 'inst_lat' not in df.columns: df['inst_lat'] = np.nan
    if 'inst_lon' not in df.columns: df['inst_lon'] = np.nan
    if 'instkommunetx' in df.columns:
        mask = df['inst_lat'].isna() | df['inst_lon'].isna()
        for idx in df[mask].index:
            muni = str(df.at[idx, 'instkommunetx']) if pd.notna(df.at[idx, 'instkommunetx']) else None
            if muni in MUNICIPALITY_COORDS:
                lat, lon = MUNICIPALITY_COORDS[muni]
                if pd.isna(df.at[idx, 'inst_lat']): df.at[idx, 'inst_lat'] = lat
                if pd.isna(df.at[idx, 'inst_lon']): df.at[idx, 'inst_lon'] = lon
    return df

def build_providers_map(providers_df):
    if providers_df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark",
                          paper_bgcolor=CUSTOM_BG, plot_bgcolor=PLOT_BG,
                          margin=dict(t=0,l=0,r=0,b=0), font_color=FONT_COL)
        return fig

    providers_geo = _ensure_latlon_from_municipality(providers_df)
    if 'kvote_1_kvotient' in providers_geo.columns:
        providers_geo['kvote_num'] = to_num(providers_geo['kvote_1_kvotient'])
    if 'standby_8' in providers_geo.columns:
        providers_geo['standby_num'] = to_num(providers_geo['standby_8'])

    providers_geo = providers_geo.dropna(subset=['inst_lat','inst_lon'])
    if providers_geo.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Ingen koordinater (inst_lat/inst_lon) og ingen kendt kommune-match.",
            showarrow=False, font=dict(color=FONT_COL, size=12),
            x=0.5, y=0.5, xref="paper", yref="paper"
        )
        fig.update_layout(template="plotly_dark",
                          paper_bgcolor=CUSTOM_BG, plot_bgcolor=PLOT_BG,
                          margin=dict(t=0,l=0,r=0,b=0), font_color=FONT_COL)
        return fig

    hover_cols = [c for c in ['instkommunetx','instregiontx','titel'] if c in providers_geo.columns]
    if 'kvote_num' in providers_geo.columns:   hover_cols.append('kvote_num')
    if 'standby_num' in providers_geo.columns: hover_cols.append('standby_num')

    fig = px.scatter_mapbox(
        providers_geo,
        lat='inst_lat', lon='inst_lon',
        hover_name='hovedinsttx',
        hover_data=hover_cols,
        zoom=6, height=520
    )

    lats = providers_geo['inst_lat'].astype(float)
    lons = providers_geo['inst_lon'].astype(float)
    lat_span = float(lats.max() - lats.min()) if len(lats) else 0.0
    lon_span = float(lons.max() - lons.min()) if len(lons) else 0.0
    center_lat = float(lats.mean()) if len(lats) else 56.0
    center_lon = float(lons.mean()) if len(lons) else 10.5

    base_zoom = 6.0
    if max(lat_span, lon_span) < 0.8: base_zoom = 7.5
    elif max(lat_span, lon_span) > 6: base_zoom = 5.2

    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox=dict(center=dict(lat=center_lat if not np.isnan(center_lat) else 56.0,
                                lon=center_lon if not np.isnan(center_lon) else 10.5),
                    zoom=base_zoom),
        paper_bgcolor=CUSTOM_BG, plot_bgcolor=PLOT_BG, font_color=FONT_COL,
        margin=dict(t=0,l=0,r=0,b=0)
    )

    has_k = 'kvote_num' in providers_geo.columns
    has_s = 'standby_num' in providers_geo.columns
    hover_t = "<b>%{hovertext}</b><br>"
    if 'instkommunetx' in providers_geo.columns: hover_t += "Kommune: %{customdata[0]}<br>"
    if 'instregiontx' in providers_geo.columns:
        idx = hover_cols.index('instregiontx'); hover_t += f"Region: %{{customdata[{idx}]}}<br>"
    if has_k:
        idx = hover_cols.index('kvote_num'); hover_t += f"Kvote 1: %{{customdata[{idx}]:.2f}}<br>"
    if has_s:
        idx = hover_cols.index('standby_num'); hover_t += f"Standby (8): %{{customdata[{idx}]:.2f}}<br>"
    hover_t += "<extra></extra>"

    fig.update_traces(hovertemplate=hover_t, marker=dict(size=12))
    return fig

# ---------- Treemap builder (CITY + METRIC)  [FIXED AGG] ----------
def build_city_treemap(city_value, metric_key):
    if metric_key not in SIZE_METRICS:
        metric_key = 'optagne'
    metric_col, how, metric_label = SIZE_METRICS[metric_key]

    # filter by city (or all)
    if city_value and city_value != '__ALL__':
        df_sel = df_prov[df_prov['instkommunetx'] == city_value].copy()
    else:
        df_sel = df_prov.copy()

    # require taxonomy + metric
    df_sel = df_sel.dropna(subset=['educational_category','cluster_label','titel'])
    df_sel = df_sel[~df_sel[metric_col].isna()]

    if df_sel.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", paper_bgcolor=CUSTOM_BG, plot_bgcolor=PLOT_BG,
                          font_color=FONT_COL, margin=dict(t=30,l=20,r=20,b=20))
        fig.add_annotation(text="Ingen data for valgte filter.", showarrow=False,
                           x=0.5,y=0.5,xref="paper",yref="paper",
                           font=dict(color=FONT_COL))
        return fig

    # aggregate by title within taxonomy using sum or mean (no FutureWarning)
    if how == 'sum':
        grouped = (df_sel
                   .groupby(['educational_category','cluster_label','titel'], as_index=False)[metric_col]
                   .sum()
                   .rename(columns={metric_col: 'size'}))
    else:  # 'mean'
        grouped = (df_sel
                   .groupby(['educational_category','cluster_label','titel'], as_index=False)[metric_col]
                   .mean()
                   .rename(columns={metric_col: 'size'}))

    grouped = grouped[np.isfinite(grouped['size'])]
    grouped = grouped[grouped['size'] > 0]

    title_txt = f"{metric_label} — " + (city_value if city_value != '__ALL__' else "Alle kommuner")

    fig = px.treemap(
        grouped,
        path=['educational_category','cluster_label','titel'],
        values='size',
        color='size',
        color_continuous_scale=px.colors.sequential.Blues
    )
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=CUSTOM_BG, plot_bgcolor=PLOT_BG, font_color=FONT_COL,
        margin=dict(t=50,l=30,r=50,b=20), title=title_txt
    )
    fig.update_coloraxes(colorbar=dict(title=metric_label,
                                       tickfont=dict(color=FONT_COL),
                                       titlefont=dict(color=FONT_COL)))
    fig.update_traces(root_color="#1c1f26",
                      marker_colorbar=dict(tickfont=dict(color=FONT_COL),
                                           titlefont=dict(color=FONT_COL),
                                           outlinecolor="#2a2f3a"))
    return fig

# ---------- Dash app ----------
app = Dash(__name__)
titles_options = [{"label": t, "value": t} for t in AVAILABLE_TITLES]

# ---------- Layout ----------
app.layout = html.Div(
    style={"padding": "12px", "backgroundColor": CUSTOM_BG, "color": FONT_COL, "minHeight": "100vh"},
    children=[
        # Top row: City Treemap + selectors
        html.Div([
            # Left: filters + treemap
            html.Div([
                html.Div([
                    html.Div("Filtrér efter kommune:", style={"marginBottom": "6px", "fontWeight": "600"}),
                    dcc.Dropdown(
                        CITY_OPTIONS,
                        id="city_select",
                        value="__ALL__",
                        clearable=False,
                        style={
                            "marginBottom": "10px",
                            "backgroundColor": "#1f2630",
                            "color": FONT_COL,
                            "border": "1px solid #2a2f3a",
                        },
                        className="dark-dropdown",
                    ),
                    html.Div("Vælg størrelse for klynger:", style={"marginBottom": "6px", "fontWeight": "600"}),
                    dcc.Dropdown(
                        SIZE_OPTIONS,
                        id="size_metric",
                        value="optagne",
                        clearable=False,
                        style={
                            "marginBottom": "10px",
                            "backgroundColor": "#1f2630",
                            "color": FONT_COL,
                            "border": "1px solid #2a2f3a",
                        },
                        className="dark-dropdown",
                    ),
                ], style={**CUSTOM_CARD, "marginBottom": "10px"}),
                dcc.Graph(id="treemap", style={"height": "560px", "width": "100%"}),
            ], style={"flex": "1 1 800px", "minWidth": "600px"}),

            # Right: 3 education selectors
            html.Div([
                html.Div("Vælg op til 3 uddannelser:", style={"marginBottom": "8px", "fontWeight": "600"}),
                dcc.Dropdown(
                    titles_options,
                    id="edu1",
                    placeholder="Uddannelse A",
                    clearable=True,
                    style={
                        "marginBottom": "10px",
                        "backgroundColor": "#1f2630",
                        "color": FONT_COL,
                        "border": "1px solid #2a2f3a",
                    },
                    className="dark-dropdown",
                ),
                dcc.Dropdown(
                    titles_options,
                    id="edu2",
                    placeholder="Uddannelse B",
                    clearable=True,
                    style={
                        "marginBottom": "10px",
                        "backgroundColor": "#1f2630",
                        "color": FONT_COL,
                        "border": "1px solid #2a2f3a",
                    },
                    className="dark-dropdown",
                ),
                dcc.Dropdown(
                    titles_options,
                    id="edu3",
                    placeholder="Uddannelse C",
                    clearable=True,
                    style={
                        "backgroundColor": "#1f2630",
                        "color": FONT_COL,
                        "border": "1px solid #2a2f3a",
                    },
                    className="dark-dropdown",
                ),
                html.Div(
                    "Tip: Radar viser rå Likert (1–5). Løn/ledighed i søjlerne til højre.",
                    style={"marginTop": "12px", "color": FONT_COL, "fontSize": "12px"},
                ),
            ], style={"flex": "0 0 360px", "maxWidth": "360px", **CUSTOM_CARD}),
        ], style={"display": "flex", "gap": "16px", "alignItems": "flex-start", "flexWrap": "wrap"}),

        html.Hr(style={"borderColor": "#2a2f3a"}),

        # Radar + KPI
        html.Div([
            html.Div([dcc.Graph(id="radar", style={"height": "560px"})],
                     style={"flex": "3 1 0px", "minWidth": "520px"}),
            html.Div([
                html.Div(id="bachelor_notice",
                         style={**CUSTOM_CARD, "display": "none", "marginBottom": "8px"}),
                dcc.Graph(id="bar_afbrud",   style={"height": "200px", "marginBottom": "10px"}),
                dcc.Graph(id="bar_ledighed", style={"height": "200px", "marginBottom": "10px"}),
                dcc.Graph(id="bar_loen_ny",  style={"height": "200px"}),
            ], style={"flex": "2 1 0px", **CUSTOM_CARD}),
        ], style={"display": "flex", "gap": "16px", "alignItems": "stretch", "flexWrap": "wrap"}),

        html.Hr(style={"borderColor": "#2a2f3a"}),

        # Multi-bachelor exploration (bar + SANKEY)
        html.Div("Udforsk kandidat-retninger (vælg flere bachelorer)",
                 style={"fontWeight": "600", "marginBottom": "6px"}),
        dcc.Dropdown(
            options=[{"label": t, "value": t} for t in bachelor_titles_multi],
            id="bachelor_multi",
            placeholder="Vælg en eller flere bacheloruddannelser",
            multi=True,
            clearable=True,
            style={
                "maxWidth": "900px",
                "backgroundColor": "#1f2630",
                "color": FONT_COL,
                "border": "1px solid #2a2f3a",
                "marginBottom": "12px",
            },
            className="dark-dropdown",
        ),
        html.Div([
            html.Div([dcc.Graph(id="kandidat_bar", style={"height": "480px"})],
                     style={"flex": "1 1 520px", "minWidth": "420px"}),
            html.Div([dcc.Graph(id="kandidat_flow", style={"height": "480px"})],
                     style={"flex": "1 1 520px", "minWidth": "420px"}),
        ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap"}),

        # --- Detail panel ---
        html.Hr(style={"borderColor": "#2a2f3a"}),
        html.Div("Detaljer for valgt uddannelse (udbydere + info)",
                 style={"fontWeight": "600", "marginBottom": "6px"}),
        dcc.Dropdown(
            options=AVAILABLE_OPTIONS,
            id="detail_select",
            placeholder="Vælg uddannelse (ikke nationalt niveau)",
            clearable=True,
            style={
                "maxWidth": "900px",
                "backgroundColor": "#1f2630",
                "color": FONT_COL,
                "border": "1px solid #2a2f3a",
                "marginBottom": "12px",
            },
            className="dark-dropdown",
        ),
        html.Div([
            html.Div(
                id="detail_table",
                style={
                    "flex": "1 1 520px",
                    "minWidth": "420px",
                    "padding": "8px",
                    "backgroundColor": "#11151b",
                    "border": "1px solid #2a2f3a",
                    "borderRadius": "8px",
                    "color": FONT_COL,
                },
            ),
            html.Div([dcc.Graph(id="detail_map", style={"height": "520px"})],
                     style={"flex": "1 1 520px", "minWidth": "420px"}),
        ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap"}),
    ]
)


# ---------- Callbacks ----------
@app.callback(
    Output("treemap","figure"),
    Input("city_select","value"),
    Input("size_metric","value")
)
def update_treemap(city_value, metric_key):
    return build_city_treemap(city_value, metric_key)

@app.callback(
    [Output("radar", "figure"),
     Output("bachelor_notice", "children"),
     Output("bachelor_notice", "style"),
     Output("bar_afbrud","figure"),
     Output("bar_ledighed","figure"),
     Output("bar_loen_ny","figure")],
    Input("edu1", "value"),
    Input("edu2", "value"),
    Input("edu3", "value"),
)
def update_main(a, b, c):
    selected = [x for x in [a, b, c] if x in AVAILABLE_SET]
    radar_fig = build_radar_raw(selected) if selected else build_radar_raw([])

    notice_titles = []
    for t in selected:
        row = df[df['titel']==t]
        if not row.empty and str(row.iloc[0]['displaydocclass']) == 'Bacheloruddannelse':
            notice_titles.append(t)
    if notice_titles:
        msg = html.Div([
            html.Div("Bemærk:", style={"fontWeight":"700","marginBottom":"4px"}),
            html.Div(
                "Du har valgt en universitets-bachelor: "
                + ", ".join(notice_titles)
                + ". Yderligere uddannelse (kandidat) kan være nødvendig. "
                  "Brug værktøjet nedenfor til at se relevante kandidatuddannelser.",
                style={"lineHeight":"1.5"}
            )
        ])
        style = {**CUSTOM_CARD, "display":"block", "borderLeft":"4px solid #4C9BE8"}
    else:
        msg = ""
        style = {**CUSTOM_CARD, "display":"none"}

    bar_afbrud   = build_simple_bar("afbrud", selected, "Afbrud (%)")
    bar_ledighed = build_simple_bar("ledighed_nyudd", selected, "Ledighed (nyudd.) (%)")
    bar_loen_ny  = build_simple_bar("maanedloen_nyudd", selected, "Løn (nyudd.)", tickprefix="kr ")

    return radar_fig, msg, style, bar_afbrud, bar_ledighed, bar_loen_ny

@app.callback(
    [Output("kandidat_bar","figure"), Output("kandidat_flow","figure")],
    Input("bachelor_multi","value")
)
def update_multi_charts(selected):
    empty = go.Figure()
    empty.update_layout(template="plotly_dark", paper_bgcolor=CUSTOM_BG, plot_bgcolor=PLOT_BG, font_color=FONT_COL)

    if not selected:
        return empty, empty
    selected = [s for s in selected if s in bachelor_titles_multi]
    if not selected:
        return empty, empty

    flow = build_flow_df(selected)
    if flow.empty:
        return empty, empty

    agg = (flow.groupby('kandidat', as_index=False)
                .agg({'weight':'sum','ledighed_nyudd':'mean','maanedloen_nyudd':'mean','maanedloen_10aar':'mean'})
                .sort_values('weight', ascending=False))
    bar = go.Figure(go.Bar(
        x=agg['weight'], y=agg['kandidat'], orientation='h',
        marker=dict(color=bar_colors(len(agg))),
        hovertemplate=("<b>%{y}</b><br>Vægt: %{x:.0f}<br>"
                       "Ledighed (nyudd.): %{customdata[0]:.1f}<br>"
                       "Løn (nyudd.): %{customdata[1]:.0f}<br>"
                       "Løn (10 år): %{customdata[2]:.0f}<extra></extra>"),
        customdata=np.c_[agg['ledighed_nyudd'], agg['maanedloen_nyudd'], agg['maanedloen_10aar']]
    ))
    bar.update_layout(
        title="Top kandidat-retninger (samlet for valgte bachelorer)",
        template="plotly_dark", paper_bgcolor=CUSTOM_BG, plot_bgcolor=PLOT_BG, font_color=FONT_COL,
        margin=dict(t=50, l=10, r=20, b=40), yaxis=dict(automargin=True)
    )

    sankey = build_sankey(flow, selected, top_k=20)
    return bar, sankey

@app.callback(
    [Output("detail_table","children"), Output("detail_map","figure")],
    Input("detail_select","value")
)
def update_detail_panel(edu_title):
    if not edu_title or edu_title not in AVAILABLE_SET:
        empty_table = html.Div(
            "Vælg en uddannelse ovenfor for at se detaljer.",
            style={"color":FONT_COL}
        )
        empty_fig = go.Figure()
        empty_fig.update_layout(template="plotly_dark", paper_bgcolor=CUSTOM_BG, plot_bgcolor=PLOT_BG, font_color=FONT_COL)
        return empty_table, empty_fig
    table, providers_small = build_detail_table(df_raw, edu_title)
    map_fig = build_providers_map(providers_small)
    return table, map_fig

if __name__ == "__main__":
    app.run_server(debug=True)
