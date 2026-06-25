import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF

# Configuración de página adaptada para visualización móvil
st.set_page_config(page_title="Valorizaciones", page_icon="📄", layout="centered")

# Estilos CSS para optimizar el espacio en el iPhone de tu tía
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1.5rem; }
    div[data-testid="stNotification"] { padding: 0.5rem; }
    stButton>button { width: 100%; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("📄 Creador de Valorizaciones")
st.write("Complete los campos requeridos. La tabla se generará automáticamente según las fechas.")

# --- 1. DATOS GENERALES (COMPLETAMENTE VACÍOS) ---
st.subheader("Datos del Cliente y Proyecto")
cliente = st.text_input("Cliente", value="")
ruc = st.text_input("RUC", value="")
proyecto = st.text_input("Proyecto", value="")
equipo = st.text_input("Equipo", value="")
costo_hora = st.number_input("Costo por Hora (S/.)", min_value=0.0, value=0.0, step=10.0)

# --- 2. GENERADOR AUTOMÁTICO DE RANGO DE FECHAS ---
st.subheader("Configuración del Periodo y Turnos")
col_desde, col_hasta = st.columns(2)
with col_desde:
    fecha_inicio = st.date_input("Fecha Inicio", value=None, format="DD-MM-YYYY")
with col_hasta:
    fecha_fin = st.date_input("Fecha Fin", value=None, format="DD-MM-YYYY")

cantidad_turnos = st.selectbox("Cantidad de turnos a registrar por día", options=[1, 2, 3, 4], index=0)

# --- 3. CONSTRUCCIÓN DINÁMICA DE LA TABLA ---
if fecha_inicio and fecha_fin:
    if fecha_inicio > fecha_fin:
        st.error("Error: La fecha de inicio no puede ser mayor que la fecha de fin.")
    else:
        # Generar la lista de fechas en el rango
        lista_fechas = []
        fecha_actual = fecha_inicio
        while fecha_actual <= fecha_fin:
            lista_fechas.append(fecha_actual.strftime("%d-%m-%y"))
            fecha_actual += timedelta(days=1)
        
        # Configurar las columnas de la tabla interactiva
        columnas_config = {
            "Fecha": st.column_config.TextColumn("Fecha", disabled=True)
        }
        
        # Crear la estructura de datos base
        datos_base = {"Fecha": lista_fechas}
        
        for t in range(1, cantidad_turnos + 1):
            datos_base[f"Hora Inicio (T{t})"] = [None] * len(lista_fechas)
            datos_base[f"Hora Final (T{t})"] = [None] * len(lista_fechas)
            
            # Forzar el uso del selector de hora (rodillo nativo en iOS)
            columnas_config[f"Hora Inicio (T{t})"] = st.column_config.TimeColumn(f"Inicio T{t}", format="hh:mm a")
            columnas_config[f"Hora Final (T{t})"] = st.column_config.TimeColumn(f"Final T{t}", format="hh:mm a")
        
        datos_base["Observaciones"] = [""] * len(lista_fechas)
        columnas_config["Observaciones"] = st.column_config.TextColumn("Observaciones", default="")
        
        df_base = pd.DataFrame(datos_base)
        
        st.subheader("Historial de Horas")
        st.info("Pulse sobre cada casilla de Inicio/Final para abrir el reloj nativo de su iPhone.")
        
        # Mostrar tabla editable
        df_editado = st.data_editor(
            df_base,
            use_container_width=True,
            hide_index=True,
            column_config=columnas_config
        )
        
        # --- 4. PROCESAMIENTO MATEMÁTICO ---
        if st.button("Calcular y Generar PDF", use_container_width=True):
            lista_totales_dias = []
            filas_para_pdf = []
            
            # Recorrer cada día para calcular las horas transcurridas
            for idx, row in df_editado.iterrows():
                suma_horas_dia = 0.0
                registro_fila_pdf = {"Fecha": row["Fecha"]}
                
                for t in range(1, cantidad_turnos + 1):
                    h_ini = row[f"Hora Inicio (T{t})"]
                    h_fin = row[f"Hora Final (T{t})"]
                    
                    total_turno = 0.0
                    str_turno = ""
                    
                    if pd.notna(h_ini) and pd.notna(h_fin):
                        # Convertir a objetos datetime para restar
                        t_ini = datetime.combine(datetime.min, h_ini)
                        t_fin = datetime.combine(datetime.min, h_fin)
                        
                        # Manejo si el turno pasa de la medianoche
                        if t_fin < t_ini:
                            t_fin += timedelta(days=1)
                            
                        diferencia = t_fin - t_ini
                        total_segundos = diferencia.total_seconds()
                        total_turno = total_segundos / 3600.0  # Convertir a horas decimales
                        
                        # Formatear el texto visual (Ej: 3h 30min)
                        mins_totales = int(total_segundos // 60)
                        hrs_vis = mins_totales // 60
                        mins_vis = mins_totales % 60
                        str_turno = f"{hrs_vis}h {mins_vis}min"
                        
                    suma_horas_dia += total_turno
                    registro_fila_pdf[f"T{t}_ini"] = h_ini.strftime("%I:%M %p") if pd.notna(h_ini) else ""
                    registro_fila_pdf[f"T{t}_fin"] = h_fin.strftime("%I:%M %p") if pd.notna(h_fin) else ""
                    registro_fila_pdf[f"T{t}_tot"] = str_turno
                
                lista_totales_dias.append(suma_horas_dia)
                registro_fila_pdf["Total_Dia"] = suma_horas_dia
                registro_fila_pdf["Obs"] = row["Observaciones"] if pd.notna(row["Observaciones"]) else ""
                filas_para_pdf.append(registro_fila_pdf)
            
            # Cálculos de la liquidación económica final
            total_hora_maquina = sum(lista_totales_dias)
            sub_total = total_hora_maquina * costo_hora
            igv = sub_total * 0.18
            total_general = sub_total + igv
            detraccion = total_general * 0.10
            total_a_pagar = total_general - detraccion
            
            st.success("¡Cálculos completados de forma exacta!")
            
            # --- 5. CONSTRUCCIÓN DEL PDF HORIZONTAL (LANDSCAPE) ---
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 16)
            
            # Encabezado principal
            pdf.cell(0, 10, "VALORIZACION DE SERVICIO", ln=True, align="C")
            pdf.ln(5)
            
            # Metadatos del cliente
            pdf.set_font("Helvetica", "", 10)
            periodo_str = f"{fecha_inicio.strftime('%d/%m/%Y')} HASTA {fecha_fin.strftime('%d/%m/%Y')}"
            pdf.cell(0, 5, f"CLIENTE: {cliente}", ln=True)
            pdf.cell(0, 5, f"RUC: {ruc}", ln=True)
            pdf.cell(0, 5, f"PROYECTO: {proyecto}", ln=True)
            pdf.cell(0, 5, f"EQUIPO: {equipo}", ln=True)
            pdf.cell(0, 5, f"PERIODO: {periodo_str}", ln=True)
            pdf.ln(5)
            
            # Dinámica de ancho de columnas para formato Horizontal (A4 horizontal = 297mm ancho)
            # Dejamos margen izquierdo y derecho estándar de 10mm -> Disponible: 277mm
            ancho_fecha = 22
            ancho_obs = 45
            ancho_total_dia = 25
            ancho_disponible_turnos = 277 - ancho_fecha - ancho_obs - ancho_total_dia
            ancho_por_columna_turno = ancho_disponible_turnos / (cantidad_turnos * 3)
            
            # Dibujar Cabecera de la Tabla
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(ancho_fecha, 8, "Fecha", border=1, align="C")
            for t in range(1, cantidad_turnos + 1):
                pdf.cell(ancho_por_columna_turno, 8, f"Inicio T{t}", border=1, align="C")
                pdf.cell(ancho_por_columna_turno, 8, f"Final T{t}", border=1, align="C")
                pdf.cell(ancho_por_columna_turno, 8, f"Total T{t}", border=1, align="C")
            pdf.cell(ancho_total_dia, 8, "Suma Día (h)", border=1, align="C")
            pdf.cell(ancho_obs, 8, "Observaciones", border=1, align="C")
            pdf.ln()
            
            # Dibujar Filas de la Tabla
            pdf.set_font("Helvetica", "", 8)
            for f in filas_para_pdf:
                pdf.cell(ancho_fecha, 6, f["Fecha"], border=1, align="C")
                for t in range(1, cantidad_turnos + 1):
                    pdf.cell(ancho_por_columna_turno, 6, f[f"T{t}_ini"], border=1, align="C")
                    pdf.cell(ancho_por_columna_turno, 6, f[f"T{t}_fin"], border=1, align="C")
                    pdf.cell(ancho_por_columna_turno, 6, f[f"T{t}_tot"], border=1, align="C")
                pdf.cell(ancho_total_dia, 6, f"{f['Total_Dia']:.2f}", border=1, align="C")
                pdf.cell(ancho_obs, 6, f["Obs"], border=1, align="L")
                pdf.ln()
                
            # Bloque de Liquidación Final Resumen (Alineado a la derecha)
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 10)
            
            labels_valores = [
                ("TOTAL, HORA MAQUINA:", f"{total_hora_maquina:.2f}"),
                ("COSTO POR HORA:", f"{costo_hora:.2f}"),
                ("SUB TOTAL:", f"{sub_total:,.2f}"),
                ("IGV. 18%:", f"{igv:,.2f}"),
                ("TOTAL:", f"{total_general:,.2f}"),
                ("DETRACCION 10%:", f"{detraccion:,.2f}"),
                ("TOTAL A PAGAR:", f"{total_a_pagar:,.2f}")
            ]
            
            for label, valor in labels_valores:
                pdf.cell(210, 5, label, align="R")
                # Resaltar colores específicos para que coincida de forma ejecutiva
                if label == "TOTAL A PAGAR:":
                    pdf.set_text_color(0, 102, 204)  # Azul corporativo
                elif label == "DETRACCION 10%:":
                    pdf.set_text_color(200, 0, 0)    # Rojo tributario
                else:
                    pdf.set_text_color(0, 0, 0)
                    
                pdf.cell(35, 5, valor, ln=True, align="R")
            
            # Salida de datos en bytes limpia para la web
            pdf_bytes = pdf.output(dest="S")
            
            st.ln(5)
            st.download_button(
                label="📥 Descargar PDF Horizontal en iPhone",
                data=bytes(pdf_bytes),
                file_name=f"Valorizacion_{cliente.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
else:
    st.warning("Por favor, seleccione una Fecha de Inicio y Fecha de Fin para desplegar el historial.")
