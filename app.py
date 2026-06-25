import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from fpdf import FPDF

st.set_page_config(page_title="Valorizaciones", page_icon="📄", layout="centered")

st.title("📄 Creador de Valorizaciones")
st.write("Complete los datos. La tabla se generará automáticamente según las fechas.")

# --- 1. DATOS GENERALES (VACÍOS) ---
st.subheader("Datos del Cliente")
cliente = st.text_input("CLIENTE", value="")
ruc = st.text_input("RUC", value="")
proyecto = st.text_input("PROYECTO", value="")
equipo = st.text_input("EQUIPO", value="")
costo_hora = st.number_input("COSTO POR HORA (S/.)", min_value=0.0, value=0.0, step=10.0)
horas_minimas_dia = st.number_input("Horas Mínimas Garantizadas por Día", min_value=0.0, value=8.0, step=1.0)

# --- 2. CONFIGURACIÓN DE FECHAS ---
st.subheader("Periodo de Trabajo")
col_desde, col_hasta = st.columns(2)
with col_desde:
    fecha_inicio = st.date_input("Fecha Inicio", value=None, format="DD-MM-YYYY")
with col_hasta:
    fecha_fin = st.date_input("Fecha Fin", value=None, format="DD-MM-YYYY")

# --- 3. GENERACIÓN DE TABLA VERTICAL ---
if fecha_inicio and fecha_fin:
    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio no puede ser mayor.")
    else:
        lista_fechas = []
        fecha_actual = fecha_inicio
        while fecha_actual <= fecha_fin:
            lista_fechas.append(fecha_actual.strftime("%d-%m-%Y"))
            fecha_actual += timedelta(days=1)
            
        # Estructura idéntica a tu formato: Vertical con dos turnos
        datos_base = {
            "FECHA": lista_fechas,
            "Hora Inicio (T1)": [None] * len(lista_fechas),
            "Hora Final (T1)": [None] * len(lista_fechas),
            "Hora Inicio (T2)": [None] * len(lista_fechas),
            "Hora Final (T2)": [None] * len(lista_fechas),
            "OBSERVACIONES": [""] * len(lista_fechas)
        }
        
        # Forzar rodillo nativo del iPhone para las horas
        columnas_config = {
            "FECHA": st.column_config.TextColumn("FECHA", disabled=True),
            "Hora Inicio (T1)": st.column_config.TimeColumn("HORA INICIO T1", format="hh:mm a"),
            "Hora Final (T1)": st.column_config.TimeColumn("HORA FINAL T1", format="hh:mm a"),
            "Hora Inicio (T2)": st.column_config.TimeColumn("HORA INICIO T2", format="hh:mm a"),
            "Hora Final (T2)": st.column_config.TimeColumn("HORA FINAL T2", format="hh:mm a"),
            "OBSERVACIONES": st.column_config.TextColumn("OBSERVACIONES", default="")
        }
        
        st.subheader("Historial de turnos")
        st.info("Use las casillas de tiempo para abrir el reloj del iPhone y use la columna OBSERVACIONES para colocar 'Movilización'.")
        
        df_editado = st.data_editor(
            pd.DataFrame(datos_base), 
            use_container_width=True, 
            hide_index=True,
            column_config=columnas_config
        )
        
        # --- 4. PROCESAMIENTO ---
        if st.button("Calcular y Lanzar PDF Comercial", use_container_width=True):
            filas_pdf = []
            total_general_horas = 0.0
            
            for idx, row in df_editado.iterrows():
                h_ini1 = row["Hora Inicio (T1)"]
                h_fin1 = row["Hora Final (T1)"]
                h_ini2 = row["Hora Inicio (T2)"]
                h_fin2 = row["Hora Final (T2)"]
                
                horas_t1 = 0.0
                str_t1 = ""
                if pd.notna(h_ini1) and pd.notna(h_fin1) and isinstance(h_ini1, time) and isinstance(h_fin1, time):
                    t_ini = datetime.combine(datetime.min, h_ini1)
                    t_fin = datetime.combine(datetime.min, h_fin1)
                    if t_fin < t_ini: t_fin += timedelta(days=1)
                    horas_t1 = (t_fin - t_ini).total_seconds() / 3600.0
                    str_t1 = f"{horas_t1:.1f}H" if horas_t1 > 0 else ""
                
                horas_t2 = 0.0
                str_t2 = ""
                if pd.notna(h_ini2) and pd.notna(h_fin2) and isinstance(h_ini2, time) and isinstance(h_fin2, time):
                    t_ini = datetime.combine(datetime.min, h_ini2)
                    t_fin = datetime.combine(datetime.min, h_fin2)
                    if t_fin < t_ini: t_fin += timedelta(days=1)
                    horas_t2 = (t_fin - t_ini).total_seconds() / 3600.0
                    str_t2 = f"{horas_t2:.1f}H" if horas_t2 > 0 else ""
                
                total_trabajado_dia = horas_t1 + horas_t2
                
                # Regla de negocio: Si no trabajó o fue menor al mínimo, se cobra el mínimo diario
                horas_finales_dia = max(total_trabajado_dia, horas_minimas_dia)
                total_general_horas += horas_finales_dia
                
                filas_pdf.append({
                    "fecha": row["FECHA"],
                    "ini1": h_ini1.strftime("%I:%M %p") if (pd.notna(h_ini1) and isinstance(h_ini1, time)) else "",
                    "fin1": h_fin1.strftime("%I:%M %p") if (pd.notna(h_fin1) and isinstance(h_fin1, time)) else "",
                    "n_t1": str_t1,
                    "ini2": h_ini2.strftime("%I:%M %p") if (pd.notna(h_ini2) and isinstance(h_ini2, time)) else "",
                    "fin2": h_fin2.strftime("%I:%M %p") if (pd.notna(h_fin2) and isinstance(h_fin2, time)) else "",
                    "n_t2": str_t2,
                    "total_dia": f"{horas_finales_dia:.1f}H",
                    "obs": row["OBSERVACIONES"] if pd.notna(row["OBSERVACIONES"]) else ""
                })
                
            # Cálculos Financieros
            sub_total = total_general_horas * costo_hora
            igv = sub_total * 0.18
            total_factura = sub_total + igv
            detraccion = total_factura * 0.10
            total_a_pagar = total_factura - detraccion
            
            # --- 5. GENERACIÓN DEL PDF VERTICAL ---
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.add_page()
            
            # Título principal en recuadro idéntico a tu formato
            pdf.set_fill_color(218, 227, 243)
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "VALORIZACION", border=1, ln=True, align="C", fill=True)
            pdf.ln(6)
            
            # Datos de cabecera
            pdf.set_font("Helvetica", "", 10)
            periodo_texto = f"{fecha_inicio.strftime('%d/%m/%Y')} HASTA {fecha_fin.strftime('%d/%m/%Y')}"
            
            def escribir_meta(label, valor):
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(35, 5, label, ln=False)
                pdf.set_font("Helvetica", "", 10)
                pdf.cell(0, 5, f": {valor}", ln=True)
                
            escribir_meta("CLIENTE", cliente)
            escribir_meta("RUC", ruc)
            escribir_meta("PROYECTO", proyecto)
            escribir_meta("EQUIPO", equipo)
            escribir_meta("PERIODO", periodo_texto)
            pdf.ln(5)
            
            # Anchos del formato vertical de la empresa (Total = 190mm)
            w_f = 24   # Fecha
            w_h = 20   # Horas
            w_n = 16   # N° Horas
            w_t = 20   # Total Horas Día
            w_o = 34   # Observaciones
            
            # Cabecera de la tabla
            pdf.set_fill_color(218, 227, 243)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.cell(w_f, 10, "FECHA", border=1, align="C", fill=True)
            pdf.cell(w_h, 10, "HORA INICIO", border=1, align="C", fill=True)
            pdf.cell(w_h, 10, "HORA FINAL", border=1, align="C", fill=True)
            pdf.cell(w_n, 10, "N° DE HORAS", border=1, align="C", fill=True)
            pdf.cell(w_h, 10, "HORA INICIO", border=1, align="C", fill=True)
            pdf.cell(w_h, 10, "HORA FINAL", border=1, align="C", fill=True)
            pdf.cell(w_n, 10, "N° DE HORAS", border=1, align="C", fill=True)
            pdf.cell(w_t, 10, "TOTAL HORAS", border=1, align="C", fill=True)
            pdf.cell(w_o, 10, "OBSERVACIONES", border=1, align="C", fill=True)
            pdf.ln()
            
            # Datos
            pdf.set_font("Helvetica", "", 8)
            for f in filas_pdf:
                pdf.cell(w_f, 7, f["fecha"], border=1, align="C")
                pdf.cell(w_h, 7, f["ini1"], border=1, align="C")
                pdf.cell(w_h, 7, f["fin1"], border=1, align="C")
                pdf.cell(w_n, 7, f["n_t1"], border=1, align="C")
                pdf.cell(w_h, 7, f["ini2"], border=1, align="C")
                pdf.cell(w_h, 7, f["fin2"], border=1, align="C")
                pdf.cell(w_n, 7, f["n_t2"], border=1, align="C")
                pdf.cell(w_t, 7, f["total_dia"], border=1, align="C")
                pdf.cell(w_o, 7, f["obs"], border=1, align="L")
                pdf.ln()
                
            # Recuadro amarillo de Horas Totales acumuladas
            pdf.cell(w_f + (w_h*4) + (w_n*2), 7, "", border=0)
            pdf.set_fill_color(255, 255, 0)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(w_t, 7, f"{total_general_horas:.0f}H", border=1, align="C", fill=True)
            pdf.cell(w_o, 7, "", border=0, ln=True)
            pdf.ln(8)
            
            # --- LIQUIDACIÓN ECONÓMICA EXACTA ---
            w_lbl = 45
            w_val = 25
            
            def fila_liq(label, valor, llenar=False, rgb=None):
                pdf.set_fill_color(255, 255, 0) if llenar else pdf.set_fill_color(255, 255, 255)
                if rgb: pdf.set_text_color(*rgb)
                else: pdf.set_text_color(0, 0, 0)
                pdf.set_font("Helvetica", "B" if llenar else "", 9)
                pdf.cell(w_lbl, 5.5, label, border=1, align="L")
                pdf.cell(w_val, 5.5, valor, border=1, align="R", fill=llenar)
                pdf.ln()

            fila_liq("TOTAL, HORA MAQUINA", f"{total_general_horas:.0f}H", llenar=True)
            fila_liq("COSTO POR HORA", f"{costo_hora:.2f}")
            fila_liq("SUB TOTAL", f"{sub_total:,.2f}", llenar=True)
            fila_liq("IGV. 18%", f"{igv:,.2f}")
            fila_liq("TOTAL", f"{total_factura:,.2f}", llenar=True)
            fila_liq("DETRACCION 10%", f"{detraccion:,.2f}")
            fila_liq("TOTAL A PAGAR", f"{total_a_pagar:,.2f}", llenar=True)
            
            # Conversión de bytes para la descarga
            pdf_bytes = pdf.output(dest="S")
            st.markdown("---")
            st.download_button(
                label="📥 Descargar PDF Comercial Terminado",
                data=bytes(pdf_bytes),
                file_name=f"Valorizacion_{cliente.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
else:
    st.warning("Seleccione las fechas arriba para desplegar el historial en blanco.")
