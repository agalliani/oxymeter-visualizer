import streamlit as st
import pandas as pd
import folium
import plotly.graph_objs as go
from fitparse import FitFile
import streamlit_folium as st_folium
from geopy.distance import geodesic

# Funzione per caricare i dati GPS da un file TSV
def load_gps_data(tsv_file):
    df = pd.read_csv(tsv_file, sep='\t')
    try:
        df['Datetime'] = pd.to_datetime(df['Datetime'], format='%d/%m/%Y %H:%M:%S')
    except (ValueError, TypeError) as e:
        st.error(f"Errore durante la conversione del Datetime: {e}")
        raise
    return df

# Funzione per caricare i dati da un file .fit
def load_fit_data(fit_file):
    fitfile = FitFile(fit_file)
    records = []
    for record in fitfile.get_messages("record"):
        record_data = {}
        for data in record:
            record_data[data.name] = data.value
        records.append(record_data)
    df = pd.DataFrame(records)
    if 'timestamp' in df.columns:
        df['Datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    return df

# Funzione per creare una mappa con un percorso
def create_map_with_route(df):
    if df.empty:
        st.error("Il DataFrame è vuoto. Assicurati che il file contenga dati.")
        return None
    start_lat, start_lon = df.iloc[0][['Latitude', 'Longitude']]
    m = folium.Map(location=[start_lat, start_lon], zoom_start=13)
    folium.PolyLine(
        locations=df[['Latitude', 'Longitude']].values,
        color='blue',
        weight=2.5,
        opacity=1
    ).add_to(m)
    return m

# Calcolare i chilometri percorsi
def calculate_distance(df):
    distance = 0.0
    if len(df) > 1:
        prev_location = (df.iloc[0]['Latitude'], df.iloc[0]['Longitude'])
        for index, row in df.iterrows():
            current_location = (row['Latitude'], row['Longitude'])
            distance += geodesic(prev_location, current_location).kilometers
            prev_location = current_location
    return distance

# Calcolare altre statistiche
def calculate_statistics(df):
    if df.empty:
        return {
            'Nome': ['Km Percorsi', 'Data e Ora Inizio', 'Data e Ora Fine', 'Quota Massima', 'Dislivello Positivo', 'Durata Totale'],
            'Dati': ['0.00 km', 'N/A', 'N/A', 'N/A', '0.00 m', 'N/A']
        }
    
    distance = calculate_distance(df)
    start_datetime = df['Datetime'].min()
    end_datetime = df['Datetime'].max()
    max_altitude = df['BMEAltitude(m)'].max() if 'BMEAltitude(m)' in df.columns else None
    min_altitude = df['BMEAltitude(m)'].min() if 'BMEAltitude(m)' in df.columns else None
    positive_elevation_gain = max(0, (max_altitude - min_altitude)) if min_altitude is not None and max_altitude is not None else 0
    
    # Calcolare la durata
    duration = end_datetime - start_datetime
    hours, remainder = divmod(duration.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)
    
    return {
        'Nome': [
            'Km Percorsi',
            'Data e Ora Inizio',
            'Data e Ora Fine',
            'Quota Massima',
            'Dislivello Positivo',
            'Durata Totale'
        ],
        'Dati': [
            f"{distance:.2f} km",
            f"{start_datetime.date()} {start_datetime.time()}",
            f"{end_datetime.date()} {end_datetime.time()}",
            f"{max_altitude:.2f} m" if max_altitude is not None else "N/A",
            f"{positive_elevation_gain:.2f} m",
            f"{int(hours)} ore e {int(minutes)} minuti"
        ]
    }

# Funzione per plottare i dati dell'ossigeno o del battito cardiaco
def plot_time_series(df, column, title):
    if column in df.columns:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df[column], mode='lines', name=column))
        fig.update_layout(
            title=title,
            xaxis_title="Tempo",
            yaxis_title=f"Valore di {column}",
            autosize=True
        )
        return fig
    else:
        return None

# Funzione per plottare l'ossigeno confrontato con il battito cardiaco
def plot_oxygen_vs_heart_rate(df):
    if 'AirO2(%)' in df.columns and 'heart_rate' in df.columns:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['heart_rate'], y=df['AirO2(%)'], mode='markers', name='Ossigeno (%) vs Battito Cardiaco (bpm)', marker=dict(color='blue')))
        fig.update_layout(
            title='Ossigeno vs Battito Cardiaco',
            xaxis_title="Battito Cardiaco (bpm)",
            yaxis_title="Ossigeno (%)",
            autosize=True
        )
        return fig
    else:
        return None

# Interfaccia Streamlit
st.title("Carica e visualizza i dati")

uploaded_tsv_file = st.file_uploader("Carica File TSV", type="tsv")
uploaded_fit_file = st.file_uploader("Carica File FIT", type="fit")

gps_data = pd.DataFrame()
fit_data = pd.DataFrame()

if uploaded_tsv_file is not None:
    try:
        gps_data = load_gps_data(uploaded_tsv_file)
        st.success("Dati GPS caricati con successo!")
        map_obj = create_map_with_route(gps_data)
        if map_obj:
            st_folium.st_folium(map_obj, width=700, height=500)

        # Mostrare le statistiche
        stats = calculate_statistics(gps_data)
        stats_df = pd.DataFrame(stats)
        st.write("Tabella Riassuntiva:")
        st.dataframe(stats_df, use_container_width=True)


    except Exception as e:
        st.error(f"Errore durante il caricamento del file TSV: {e}")

if uploaded_fit_file is not None:
    try:
        fit_data = load_fit_data(uploaded_fit_file)
        st.success("Dati FIT caricati con successo!")
    except Exception as e:
        st.error(f"Errore durante il caricamento del file FIT: {e}")

if not gps_data.empty or not fit_data.empty:
    selected_plots = st.multiselect(
        'Seleziona i grafici da visualizzare:',
        ['Grafico dell\'ossigeno nel tempo', 'Grafico del battito cardiaco nel tempo', 
         'Grafico dell\'ossigeno confrontato con il battito cardiaco']
    )

    if 'Grafico dell\'ossigeno nel tempo' in selected_plots:
        #st.write("Grafico dell'ossigeno nel tempo:")
        if not gps_data.empty and 'AirO2(%)' in gps_data.columns:
            fig = plot_time_series(gps_data, 'AirO2(%)', 'Ossigeno nel Tempo')
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        elif not fit_data.empty and 'AirO2(%)' in fit_data.columns:
            fig = plot_time_series(fit_data, 'AirO2(%)', 'Ossigeno nel Tempo')
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Colonna 'AirO2(%)' non trovata")

    if 'Grafico del battito cardiaco nel tempo' in selected_plots:
        #st.write("Grafico del battito cardiaco nel tempo:")
        if not fit_data.empty and 'heart_rate' in fit_data.columns:
            fig = plot_time_series(fit_data, 'heart_rate', 'Battito Cardiaco nel Tempo')
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        elif not gps_data.empty and 'heart_rate' in gps_data.columns:
            fig = plot_time_series(gps_data, 'heart_rate', 'Battito Cardiaco nel Tempo')
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Colonna 'heart_rate' non trovata")

    if 'Grafico dell\'ossigeno confrontato con il battito cardiaco' in selected_plots:
        #st.write("Grafico dell'ossigeno confrontato con il battito cardiaco:")
        if not gps_data.empty and 'AirO2(%)' in gps_data.columns and 'heart_rate' in gps_data.columns:
            fig = plot_oxygen_vs_heart_rate(gps_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        elif not fit_data.empty and 'AirO2(%)' in fit_data.columns and 'heart_rate' in fit_data.columns:
            fig = plot_oxygen_vs_heart_rate(fit_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        elif not gps_data.empty and not fit_data.empty:
            combined_data = pd.merge(gps_data, fit_data, on='Datetime', how='outer')
            fig = plot_oxygen_vs_heart_rate(combined_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Colonne 'AirO2(%)' e 'heart_rate' non trovate")
