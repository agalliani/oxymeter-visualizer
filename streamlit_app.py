import streamlit as st
import pandas as pd
import folium
import matplotlib.pyplot as plt
import mplcursors
import io
from fitparse import FitFile

# Funzione per caricare i dati GPS da un file TSV
def load_gps_data(tsv_file):
    df = pd.read_csv(tsv_file, sep='\t')
    try:
        # Prova a convertire il "Datetime" in formato datetime
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

# Funzione per plottare i dati dell'ossigeno o del battito cardiaco
def plot_time_series(df, column, title):
    fig, ax = plt.subplots(figsize=(10, 6))
    if column in df.columns:
        ax.plot(df['Datetime'], df[column], label=column)
        ax.set_xlabel("Tempo")
        ax.set_ylabel("Valore")
        ax.set_title(title)
        ax.legend()
        st.pyplot(fig)
    else:
        st.warning(f"La colonna {column} non è nel DataFrame.")

# Funzione per plottare l'ossigeno confrontato con il battito cardiaco
def plot_oxygen_vs_heart_rate(df):
    fig, ax = plt.subplots(figsize=(10, 6))
    if 'AirO2(%)' in df.columns and 'heart_rate' in df.columns:
        ax.plot(df['Datetime'], df['AirO2(%)'], label='Ossigeno', color='blue')
        ax.plot(df['timestamp'], df['heart_rate'], label='Battito Cardiaco', color='red')
        ax.set_xlabel("Tempo")
        ax.set_ylabel("Valore")
        ax.set_title('Ossigeno vs Battito Cardiaco')
        ax.legend()
        st.pyplot(fig)
    else:
        st.warning("Le colonne 'AirO2(%)' o 'heart_rate' non sono nel DataFrame.")

# Interfaccia Streamlit
st.title("Carica e Visualizza Percorso GPS e Dati FIT")

uploaded_tsv_file = st.file_uploader("Carica File TSV", type="tsv")
uploaded_fit_file = st.file_uploader("Carica File FIT", type="fit")

if uploaded_tsv_file is not None:
    try:
        gps_data = load_gps_data(uploaded_tsv_file)
        st.write("Dati GPS caricati con successo!")
        map_obj = create_map_with_route(gps_data)
        if map_obj:
            map_html = io.BytesIO()
            map_obj.save(map_html, close_file=False)
            st.components.v1.html(map_html.getvalue().decode(), height=600)
        
        if 'AirO2(%)' in gps_data.columns:
            st.write("Grafico dell'ossigeno nel tempo:")
            plot_time_series(gps_data, 'AirO2(%)', 'Ossigeno nel Tempo')
        else:
            st.warning("Colonna 'AirO2(%)' non trovata nei dati GPS.")
        
    except Exception as e:
        st.error(f"Errore durante il caricamento del file TSV: {e}")

if uploaded_fit_file is not None:
    try:
        fit_data = load_fit_data(uploaded_fit_file)
        st.write("Dati FIT caricati con successo!")
        st.write("Dati FIT:")
        st.dataframe(fit_data)
        
        if 'heart_rate' in fit_data.columns:
            st.write("Grafico del battito cardiaco nel tempo:")
            plot_time_series(fit_data, 'heart_rate', 'Battito Cardiaco nel Tempo')
        else:
            st.warning("Colonna 'heart_rate' non trovata nei dati FIT.")
        
    except Exception as e:
        st.error(f"Errore durante il caricamento del file FIT: {e}")

if uploaded_tsv_file is not None and uploaded_fit_file is not None:
    combined_data = pd.concat([gps_data, fit_data], axis=1)
    st.write("Dati combinati:")
    st.dataframe(combined_data)
    
    st.write("Grafico dell'ossigeno nel tempo:")
    if 'AirO2(%)' in combined_data.columns:
        plot_time_series(combined_data, 'AirO2(%)', 'Ossigeno nel Tempo')
    else:
        st.warning("Colonna 'AirO2(%)' non trovata nei dati combinati.")

    st.write("Grafico del battito cardiaco nel tempo:")
    if 'heart_rate' in combined_data.columns:
        plot_time_series(combined_data, 'heart_rate', 'Battito Cardiaco nel Tempo')
    else:
        st.warning("Colonna 'heart_rate' non trovata nei dati combinati.")

    st.write("Grafico dell'ossigeno confrontato con il battito cardiaco:")
    plot_oxygen_vs_heart_rate(combined_data)
