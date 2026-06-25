import streamlit as st
import pandas as pd
from fpdf import FPDF

st.set_page_config(page_title="Valorizaciones", page_icon="📄", layout="centered")

# Estilo para mejorar visualización en móviles
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    stButton>button { width: 100%; }
    </style>
""", unsafe_allow_html=True)

st.title("📄 Creador de Valorizaciones")
st.write("Registra los datos para generar el PDF de inmediato.")

# --- DATOS GENERALES ---
st.subheader("Datos del Cliente")
cliente = st.text_input("Cliente", value="CONSORCIO CUSCO.")
ruc = st.text_input("RUC", value="20612606481")
proyecto = st.text_input("Proyecto", value="AMPLIACION DE PRODUCCION DE AGUA CUSCO")
equipo = st.text_input("Equipo", value="CAMION GRUA 21 TON")
periodo = st.text_input("Periodo", value="01/12/2025 HASTA 23/12/2025")
costo_hora = st.number_input("Costo por Hora (S/.)", min_value=0.0, value=185.0, step=5.0)

# --- TABLA INTERACTIVA ---
st.subheader("Historial de Horas")
st.info("Para añadir filas, escribe en la última línea que tiene el signo '+'.")

# Formato inicial idéntico a tu plantilla de origen
df_inicial = pd.DataFrame([
    {"Fecha": "01-12-25", "Hora Inicio": 2516.00, "Hora Final": 2524.90, "Obs": ""}
])
df_editado = st.data_editor(df_inicial, num_rows="dynamic", use_container_width=True)

# --- PROCESAMIENTO Y GENERACIÓN ---
if st.button("Calcular y Generar PDF", use_container_width=True):
    try:
        # Forzar conversión a números para evitar fallos de escritura manual
        df_editado["Hora Inicio"] = pd.to_numeric(df_editado["Hora Inicio"]).fillna(0.0)
        df_editado["Hora Final"] = pd.to_numeric(df_editado["Hora Final"]).fillna(0.0)
        
        # Calcular total por cada fila
        df_editado["Total Horas"] = df_editado["Hora Final"] - df_editado["Hora Inicio"]
        total_horas = df_editado["Total Horas"].sum()
        
        # Fórmulas de liquidación
        pago_soles = total_horas * costo_hora
        igv = pago_soles * 0.18
        total_general = pago_soles + igv
        detraccion = total_general * 0.10
        total_a_pagar = total_general - detraccion

        st.success("¡Cálculos procesados correctamente!")
        
        # --- DISEÑO DEL ARCHIVO PDF (FPDF2) ---
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        
        # Título principal
        pdf.cell(0, 10, "VALORIZACION DE SERVICIO", ln=True, align="C")
        pdf.ln(5)
        
        # Bloque de Metadatos
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"CLIENTE: {cliente}", ln=True)
        pdf.cell(0, 6, f"RUC: {ruc}", ln=True)
        pdf.cell(0, 6, f"PROYECTO: {proyecto}", ln=True)
        pdf.cell(0, 6, f"EQUIPO: {equipo}", ln=True)
        pdf.cell(0, 6, f"PERIODO: {periodo}", ln=True)
        pdf.ln(8)
        
        # Cabecera de la Tabla
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(25, 7, "Fecha", border=1, align="C")
        pdf.cell(30, 7, "Hora Inicio", border=1, align="C")
        pdf.cell(30, 7, "Hora Final", border=1, align="C")
        pdf.cell(30, 7, "Total Horas", border=1, align="C")
        pdf.cell(55, 7, "Observaciones", border=1, align="C")
        pdf.ln()
        
        # Filas de la Tabla
        pdf.set_font("Helvetica", "", 9)
        for _, row in df_editado.iterrows():
            pdf.cell(25, 6, str(row["Fecha"]), border=1, align="C")
            pdf.cell(30, 6, f"{row['Hora Inicio']:.2f}", border=1, align="C")
            pdf.cell(30, 6, f"{row['Hora Final']:.2f}", border=1, align="C")
            pdf.cell(30, 6, f"{row['Total Horas']:.2f}", border=1, align="C")
            pdf.cell(55, 6, str(row["Obs"]), border=1, align="C")
            pdf.ln()
            
        # Bloque de Cierre y Resumen Financiero
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 10)
        
        pdf.cell(115, 6, "Total Horas Maquina:", align="R")
        pdf.cell(30, 6, f"{total_horas:.2f}", ln=True, align="R")
        
        pdf.cell(115, 6, "Costo por Hora:", align="R")
        pdf.cell(30, 6, f"S/. {costo_hora:.2f}", ln=True, align="R")
        
        pdf.cell(115, 6, "Pago Soles:", align="R")
        pdf.cell(30, 6, f"S/. {pago_soles:,.2f}", ln=True, align="R")
        
        pdf.cell(115, 6, "IGV (18%):", align="R")
        pdf.cell(30, 6, f"S/. {igv:,.2f}", ln=True, align="R")
        
        pdf.cell(115, 6, "Total General:", align="R")
        pdf.cell(30, 6, f"S/. {total_general:,.2f}", ln=True, align="R")
        
        pdf.set_text_color(200, 0, 0) # Color rojo para la detracción
        pdf.cell(115, 6, "Detraccion (10%):", align="R")
        pdf.cell(30, 6, f"S/. {detraccion:,.2f}", ln=True, align="R")
        
        pdf.set_text_color(0, 102, 204) # Color azul para el monto neto final
        pdf.cell(115, 6, "Total a Pagar:", align="R")
        pdf.cell(30, 6, f"S/. {total_a_pagar:,.2f}", ln=True, align="R")

        # Conversión del documento para descarga web
        pdf_bytes = pdf.output(dest="S")
        
        st.ln(5)
        st.download_button(
            label="📥 Descargar PDF en iPhone",
            data=bytes(pdf_bytes),
            file_name=f"Valorizacion_{cliente.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Revisa los datos ingresados. Error técnico: {e}")
