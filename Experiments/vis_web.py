import streamlit as st
import pandas as pd
import plotly.express as px

# Set page config
st.set_page_config(page_title="UFM Education Dashboard", layout="wide")

# Load and process data
@st.cache_data
def load_data():
    # Import data
    df_raw = pd.read_excel('../Data/DATA_UFM_combined.xlsx', header=0)

    # Columns to keep
    cols = [
        'udbud_id', 'titel', 'educational_category', 'displaydocclass', 'hovedinsttx',
        'instregiontx', 'instkommunetx', 'optagne', 'kvote_1_kvotient',
        'fagligmiljo_likert', 'arbmedstud_likert', 'medstuderende_likert',
        'udbytte_undervisning_likert', 'socialtmiljo_likert', 'ensom_likert',
        'stress_daglig_likert', 'tilpas_likert', 'undervisere_engagerede_likert',
        'undervisere_feedback_likert', 'undervisere_hjaelp_likert',
        'undervisere_kontakt_likert', 'afbrud', 'tidsforbrug_p50',
        'tidsforbrug_arbejde', 'uddaktivitet_opgaver_pct', 'uddaktivitet_praktik_pct',
        'uddaktivitet_udlandsophold_pct', 'uddaktivitet_undervisning_pct',
        'undervisningsform_p1', 'arbejdstid_timer', 'ledighed_nyudd',
        'maanedloen_nyudd', 'maanedloen_10aar', 'ruster_til_job_likert',
        'relevans_overens_udd_job_likert',
    ]

    data = df_raw[cols]

    # Filter for national level education data
    data_whole_edu = data[data['udbud_id'] == 999999]

    # Load and merge mapping
    mapping = pd.read_excel("../Data/education_cluster_mapping.xlsx")
    mapping['titel'] = mapping['titel'].astype(str).str.strip()
    data_whole_edu['titel'] = data_whole_edu['titel'].astype(str).str.strip()
    data_whole_edu = data_whole_edu.merge(mapping, on='titel', how='left')
    
    return data_whole_edu

# Load data
data_whole_edu = load_data()

# Prepare data for treemap
dat = data_whole_edu[['titel', 'educational_category', 'cluster_label', 
                       'maanedloen_10aar', 'socialtmiljo_likert']].dropna()

# Create treemap
fig = px.treemap(
    dat, 
    path=['educational_category', 'cluster_label', 'titel'], 
    values='maanedloen_10aar',
    color='socialtmiljo_likert',
    color_continuous_scale='RdBu',
    title='Treemap of Titles by Educational Category'
)
fig.update_traces(root_color="lightgrey")
fig.update_layout(margin=dict(t=50, l=25, r=25, b=25), height=700)

# Display
st.plotly_chart(fig, use_container_width=True)