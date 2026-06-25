import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import os
from fpdf import FPDF

st.set_page_config(page_title="Valorizaciones", page_icon="📄", layout="centered")

# Estilos CSS móviles
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1.5rem; }
    stButton>button { width: 100%; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("📄 Creador de Valorizaciones")

# =========================================================================
# PARTE 1: Cabecera de Contrato y Condiciones Comerciales
# =========================================================================
st.subheader("Parte 1: Cabecera de Contrato y Condiciones Comerciales")

cliente = st.text_input("CLIENTE", value="")
ruc = st.text_input("RUC", value="")
proyecto = st.text_input("PROYECTO", value="")
equipo = st.text_input("EQUIPO", value="")

col_p1, col_p2 = st.columns(2)
with col_p1:
    costo_hora = st.number_input("COSTO POR HORA (S/.)", min_value=0.0, value=0.0, step=10.0)
with col_p2:
    horas_minimas_dia = st.number_input("Horas Mínimas Garantizadas por Día (Trato)", min_value=0.0, value=0.0, step=1.0)

st.write("---")
st.write("**Periodo de Trabajo**")
col_desde, col_hasta = st.columns(2)
with col_desde:
    fecha_inicio = st.date_input("Fecha Inicio", value=None, format="DD-MM-YYYY")
with col_hasta:
    fecha_fin = st.date_input("Fecha Fin", value=None, format="DD-MM-YYYY")

# =========================================================================
# PARTE 2: Historial Diario de Operaciones
# =========================================================================
if fecha_inicio and fecha_fin:
    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio no puede ser mayor que la de fin.")
    else:
        st.subheader("Parte 2: Historial Diario de Operaciones")
        
        lista_fechas = []
        fecha_actual = fecha_inicio
        while fecha_actual <= fecha_fin:
            lista_fechas.append(fecha_actual.strftime("%d-%m-%Y"))
            fecha_actual += timedelta(days=1)
        
        rango_key = f"datos_{lista_fechas[0]}_{lista_fechas[-1]}"
        
        if "tabla_datos" not in st.session_state or st.session_state.get("current_key") != rango_key:
            st.session_state["tabla_datos"] = pd.DataFrame({
                "FECHA": lista_fechas,
                "INICIO T1": [time(0, 0)] * len(lista_fechas),
                "FINAL T1": [time(0, 0)] * len(lista_fechas),
                "INICIO T2": [time(0, 0)] * len(lista_fechas),
                "FINAL T2": [time(0, 0)] * len(lista_fechas),
                "OBSERVACIONES": [""] * len(lista_fechas)
            })
            st.session_state["current_key"] = rango_key
        
        columnas_config = {
            "FECHA": st.column_config.TextColumn("FECHA", disabled=True),
            "INICIO T1": st.column_config.TimeColumn("INICIO T1", format="HH:mm"),
            "FINAL T1": st.column_config.TimeColumn("FINAL T1", format="HH:mm"),
            "INICIO T2": st.column_config.TimeColumn("INICIO T2", format="HH:mm"),
            "FINAL T2": st.column_config.TimeColumn("FINAL T2", format="HH:mm"),
            "OBSERVACIONES": st.column_config.TextColumn("OBSERVACIONES", default="")
        }
        
        df_editado = st.data_editor(
            st.session_state["tabla_datos"],
            use_container_width=True,
            hide_index=True,
            column_config=columnas_config,
            key=f"editor_{rango_key}"
        )
        
        st.session_state["tabla_datos"] = df_editado

        def calcular_minutos_turno(h_ini, h_fin):
            if pd.isna(h_ini) or pd.isna(h_fin) or not h_ini or not h_fin:
                return 0
            if h_ini == time(0, 0) and h_fin == time(0, 0):
                return 0
            t_ini = datetime.combine(datetime.min, h_ini)
            t_fin = datetime.combine(datetime.min, h_fin)
            if t_fin < t_ini: 
                t_fin += timedelta(days=1)
            return int((t_fin - t_ini).total_seconds() // 60)

        def formatear_texto_horas(minutos_totales):
            if minutos_totales <= 0:
                return ""
            hrs = minutos_totales // 60
            mins = minutos_totales % 60
            return f"{hrs}H{mins}min" if mins > 0 else f"{hrs}H"

        # =========================================================================
        # PROCESAMIENTO Y PARTE 3: Liquidación Económica Final
        # =========================================================================
        if st.button("Calcular y Lanzar PDF Comercial", use_container_width=True):
            filas_pdf = []
            total_general_minutos = 0
            
            for idx, row in st.session_state["tabla_datos"].iterrows():
                h_ini1 = row["INICIO T1"]
                h_fin1 = row["FINAL T1"]
                h_ini2 = row["INICIO T2"]
                h_fin2 = row["FINAL T2"]
                
                minutos_t1 = calcular_minutos_turno(h_ini1, h_fin1)
                minutos_t2 = calcular_minutos_turno(h_ini2, h_fin2)
                minutos_trabajados_dia = minutos_t1 + minutos_t2
                
                minutos_finales_dia = 0
                if minutos_trabajados_dia == 0:
                    minutos_finales_dia = 0
                else:
                    minutos_minimos_pactados = int(horas_minimas_dia * 60)
                    minutos_finales_dia = max(minutos_trabajados_dia, minutos_minimos_pactados)
                
                total_general_minutos += minutos_finales_dia
                
                def to_ampm(t_obj):
                    if pd.isna(t_obj) or t_obj is None or t_obj == time(0, 0): return ""
                    return t_obj.strftime("%I:%M %p")

                filas_pdf.append({
                    "fecha": row["FECHA"],
                    "ini1": to_ampm(h_ini1), "fin1": to_ampm(h_fin1),
                    "n_t1": formatear_texto_horas(minutos_t1),
                    "ini2": to_ampm(h_ini2), "fin2": to_ampm(h_fin2),
                    "n_t2": formatear_texto_horas(minutos_t2),
                    "total_dia": formatear_texto_horas(minutos_finales_dia) if minutos_finales_dia > 0 else "0H",
                    "obs": str(row["OBSERVACIONES"]) if pd.notna(row["OBSERVACIONES"]) else ""
                })
            
            total_general_horas_decimal = total_general_minutos / 60.0
            sub_total = total_general_horas_decimal * costo_hora
            igv = sub_total * 0.18
            total_factura = sub_total + igv
            detraccion = total_factura * 0.10
            total_a_pagar = total_factura - detraccion
            
            # --- CLASE CUSTOM PDF PARA MARCA DE AGUA Y LOGO ---
            class CustomPDF(FPDF):
                def header(self):
                    # 1. MARCA DE AGUA (GRÚA DE FONDO) CON OPACIDAD SUAVE
                    if os.path.exists("grua_fondo.png"):
                        with self.local_context(fill_opacity=0.12):  # Opacidad súper suave de fondo
                            # Centrado en una página A4 (Ancho 210, Alto 297)
                            self.image("grua_fondo.png", x=15, y=65, w=180)
                    
                    # 2. LOGO CORPORATIVO DE LA EMPRESA EN EL TOP
                    if os.path.exists("logo.png"):
                        # x=30 para dejar espacio, w=150 para que quede centrado y estilizado
                        self.image("logo.png", x=30, y=10, w=150)
                        self.ln(18)  # Espacio debajo del logo
                    else:
                        # Si no hay logo, pone texto de respaldo para que no quede vacío
                        self.set_font("Helvetica", "B", 16)
                        self.cell(0, 10, "CORPORACIÓN CHAPU SAC", ln=True, align="C")
                        self.ln(5)

            pdf = CustomPDF(orientation='P', unit='mm', format='A4')
            pdf.add_page()
            
            # Título principal de la tabla
            pdf.set_fill_color(218, 227, 243)
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "VALORIZACION", border=1, ln=True, align="C", fill=True)
            pdf.ln(6)
            
            # Cabecera informativa Parte 1
            pdf.set_font("Helvetica", "B", 10)
            periodo_texto = f"{fecha_inicio.strftime('%d/%m/%Y')} HASTA {fecha_fin.strftime('%d/%m/%Y')}"
            
            def escribir_meta_pdf(label, valor):
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(28, 5, label, ln=False)
                pdf.cell(4, 5, ":", ln=False, align="C")
                pdf.set_font("Helvetica", "", 10)
                pdf.cell(0, 5, str(valor), ln=True)
                
            escribir_meta_pdf("CLIENTE", cliente)
            escribir_meta_pdf("RUC", ruc)
            escribir_meta_pdf("PROYECTO", proyecto)
            escribir_meta_pdf("EQUIPO", equipo)
            escribir_meta_pdf("PERIODO", periodo_texto)
            pdf.ln(5)
            
            # Anchos del Reporte Vertical (Total exacto = 190mm)
            w_f = 24   # Fecha
            w_h = 20   # Horas
            w_n = 16   # N° Horas Turno
            w_t = 24   # Total Horas Día
            w_o = 30   # Observaciones
            
            # Títulos de Tabla
            pdf.set_fill_color(218, 227, 243)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.cell(w_f, 10, "FECHA", border=1, align="C", fill=True)
            pdf.cell(w_h, 10, "INICIO T1", border=1, align="C", fill=True)
            pdf.cell(w_h, 10, "FINAL T1", border=1, align="C", fill=True)
            pdf.cell(w_n, 10, "N° HORAS", border=1, align="C", fill=True)
            pdf.cell(w_h, 10, "INICIO T2", border=1, align="C", fill=True)
            pdf.cell(w_h, 10, "FINAL T2", border=1, align="C", fill=True)
            pdf.cell(w_n, 10, "N° HORAS", border=1, align="C", fill=True)
            pdf.cell(w_t, 10, "TOTAL HORAS", border=1, align="C", fill=True)
            pdf.cell(w_o, 10, "OBSERVACIONES", border=1, align="C", fill=True)
            pdf.ln()
            
            # Filas de la tabla
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
                
            # Recuadro Amarillo del Total Acumulado
            pdf.cell(136, 7, "", border=0)
            pdf.set_fill_color(255, 255, 0)
            pdf.set_font("Helvetica", "B", 8.5)
            
            texto_acumulado_amarillo = formatear_texto_horas(total_general_minutos) if total_general_minutos > 0 else "0H"
            pdf.cell(w_t, 7, texto_acumulado_amarillo, border=1, align="C", fill=True)
            pdf.cell(w_o, 7, "", border=0, ln=True)
            pdf.ln(8)
            
            # --- PARTE 3: LIQUIDACIÓN ECONÓMICA ---
            w_lbl = 45
            w_val = 25
            
            def dibujar_fila_liquidacion(label, valor, resaltar_amarillo=False):
                pdf.set_fill_color(255, 255, 0) if resaltar_amarillo else pdf.set_fill_color(255, 255, 255)
                pdf.set_font("Helvetica", "B" if resaltar_amarillo else "", 9)
                pdf.cell(w_lbl, 5.5, label, border=1, align="L")
                pdf.cell(w_val, 5.5, valor, border=1, align="R", fill=resaltar_amarillo)
                pdf.ln()

            dibujar_fila_liquidacion("TOTAL, HORA MAQUINA", texto_acumulado_amarillo, resaltar_amarillo=True)
            dibujar_fila_liquidacion("COSTO POR HORA", f"{costo_hora:.2f}")
            dibujar_fila_liquidacion("SUB TOTAL", f"{sub_total:,.2f}", resaltar_amarillo=True)
            dibujar_fila_liquidacion("IGV. 18%", f"{igv:,.2f}")
            dibujar_fila_liquidacion("TOTAL", f"{total_factura:,.2f}", resaltar_amarillo=True)
            dibujar_fila_liquidacion("DETRACCION 10%", f"{detraccion:,.2f}")
            dibujar_fila_liquidacion("TOTAL A PAGAR", f"{total_a_pagar:,.2f}", resaltar_amarillo=True)
            
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
    st.warning("Seleccione las fechas arriba para desplegar la estructura en blanco de la Parte 2.")
