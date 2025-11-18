import panel as pn
import plotly.express as px
import plotly.express as px
import pandas as pd

# Import data
df_raw = pd.read_excel('../Data/DATA_UFM_combined.xlsx', header=0)
# Columns to keep
cols = [
    ################## EDUCATION INFORMATION ###########################

    # Names of the education
    'udbud_id',
    'titel',
    'educational_category',
    'displaydocclass',
    'hovedinsttx',

    # Region
    'instregiontx',
    'instkommunetx',

    # Grades coefficients
    'optagne',
    'kvote_1_kvotient',

    ####################### EDUCATIONAL VARIABLES ########################

    # Likert data
    'fagligmiljo_likert',               # Faglit miljø
    'arbmedstud_likert',                # Fagligt miljø
    'medstuderende_likert',             # Fagligt miljø
    'udbytte_undervisning_likert',      # Fagligt miljø
    'socialtmiljo_likert',              # Social miljø og trivsel
    'ensom_likert',                     # Social miljø og trivsel
    'stress_daglig_likert',             # Social miljø og trivsel
    'tilpas_likert',                    # Social miljø og trivsel
    'undervisere_engagerede_likert',    # Undervisere
    'undervisere_feedback_likert',      # Undervisere
    'undervisere_hjaelp_likert',        # Undervisere
    'undervisere_kontakt_likert',       # Undervisere

    # continuous data
    'afbrud',                           # frafald
    'tidsforbrug_p50',                  # tidsforbrug studie
    'tidsforbrug_arbejde',              # tidsforbrug studiejob

    # Undervisnings aktivitet
    'uddaktivitet_opgaver_pct',
    'uddaktivitet_praktik_pct',
    'uddaktivitet_udlandsophold_pct',
    'uddaktivitet_undervisning_pct',

    # Undervisningsform
    'undervisningsform_p1',             # Primær undervisningsform

    ########################## Job data ##################################

    # continuous data
    'arbejdstid_timer',
    'ledighed_nyudd',
    'maanedloen_nyudd',
    'maanedloen_10aar',

    # Likert data
    'ruster_til_job_likert',
    'relevans_overens_udd_job_likert',
]

data = df_raw[cols]

# Remove all udbud_id==999999, as this is the education on national level
data_whole_edu = data[data['udbud_id'] == 999999]
data = data[data['udbud_id'] != 999999]

# Remove the udbud_id column
data = data.drop(columns=['udbud_id'])

data_na = data.copy()
# Remove all rows with missing values
data = data.dropna()

# Load mapping and join on 'titel' into the existing `data` dataframe
path = "../Data/education_cluster_mapping.xlsx"

mapping = pd.read_excel(path)

mapping['titel'] = mapping['titel'].astype(str).str.strip()
data_whole_edu['titel'] = data_whole_edu['titel'].astype(str).str.strip()
# Left-join mapping into data (keeps all rows from data)
data_whole_edu = data_whole_edu.merge(mapping, on='titel', how='left', suffixes=('', '_map'))

dat = data_whole_edu[['titel', 'educational_category', 'cluster_label', 'displaydocclass', 'maanedloen_nyudd', 'maanedloen_10aar', 'socialtmiljo_likert']]
dat = dat.dropna()

# Create the treemap
fig = px.treemap(dat, path=['educational_category', 'cluster_label', 'titel'], values='maanedloen_10aar',
                 color='socialtmiljo_likert',
                 color_continuous_scale='RdBu',
                 title='Treemap of Titles by Educational Category')
fig.update_traces(root_color="lightgrey")
fig.update_layout(margin = dict(t=50, l=25, r=25, b=25))



# Create a Panel pane that wraps the Plotly figure
plot = pn.pane.Plotly(fig, sizing_mode="stretch_both")

# (Optional) Add widgets or layout if you want
title = pn.pane.Markdown("# Its a treemap")
layout = pn.Column(title, plot)

# Serve the app
layout.servable() # panel serve app_simon.py

