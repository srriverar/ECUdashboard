"""
🇪🇨 Ecuador Energy Dashboard — Observatorio del SNI
Sistema Nacional Interconectado: generación, hidrología, racionamiento, WAMS, estabilidad.
Colaboradores: Prof. Santiago Torres (U. Cuenca) · Prof. Sergio Rivera (UNAL)
Fuentes: CENACE, ARCONEL, CELEC EP, datosabiertos.gob.ec
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# IMPORTACIONES
# ---------------------------------------------------------------------------
from tools.ecu_grid_model import (
    CAPACIDAD_POR_ANO, GENERACION_POR_ANO, DEMANDA_PICO,
    CENTRALES_HIDRO, CENTRALES_TERMICAS, EMBALSES, INTERCONEXIONES,
    TRANSMISION, PROYECTOS_IBR, ACTORES, DISTRIBUIDORAS, CRISIS_2024,
    EMISIONES_HISTORICA, PRECIOS_HISTORICOS, FACTORES_CAPACIDAD,
    MODOS_OSCILACION, FONTES_DADOS, GEN_COLORS,
    SPS_INFO, CONTINGENCIAS_CRITICAS, SUBESTACIONES_CRITICAS,
    RIESGOS_OPERATIVOS_2026, CORREDORES_TRANSMISION,
    NODOS_PRECIO, COSTOS_MARGINALES, PRECIOS_NODALES_HISTORICOS,
    LINEAS_TRANSMISION, EVENTOS_CONGESTION, CONGESTION_ZONAL,
    generate_generation_mix, generate_demand_profile,
    generate_reservoir_levels, get_last_n_days_dates,
)
from tools.wams_analytics import (
    PMU_NETWORK, ALGORITMOS_WAMS, INERCIA_SNI, INERCIA_HISTORICA,
    simulate_frequency_event, simulate_voltage_stability,
    simulate_enos_drought, simulate_tnep_ac,
)
from tools.cenace_client import fetch_cenace_realtime
from tools.live_panels import panel_cenace_tiempo_real, panel_embalses_celecsur, panel_intercambio_xm

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Ecuador Energy Dashboard", page_icon="🇪🇨",
                   layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------------------------
def _impact_box(texto: str, tipo: str = "info"):
    colors = {"info": "#e8f4fd", "alert": "#fff3cd", "danger": "#f8d7da", "success": "#d4edda"}
    icons = {"info": "💡", "alert": "⚠️", "danger": "🚨", "success": "✅"}
    c = colors.get(tipo, colors["info"])
    i = icons.get(tipo, "💡")
    st.markdown(f'<div style="background:{c};padding:10px 14px;border-radius:8px;'
                f'font-size:.88rem;margin:8px 0;">{i} <b>Impacto/Decisión:</b> {texto}</div>',
                unsafe_allow_html=True)

def _sub_color(s: str) -> str:
    m = {"Norte": "#2E86AB", "Centro": "#F18F01", "Sur": "#6A994E",
         "Costa": "#C73E1D", "Oriente": "#7B2D8E"}
    for k, v in m.items():
        if k in s: return v
    return "#888"

# ---------------------------------------------------------------------------
# HEADER + SIDEBAR
# ---------------------------------------------------------------------------
def render_header():
    st.markdown(
        '<div style="background:linear-gradient(135deg,#FFD100 0%,#003087 100%);'
        'padding:18px 24px;border-radius:12px;color:#003087;margin-bottom:10px;">'
        '<h1 style="margin:0;font-size:1.8rem;">🇪🇨 Ecuador Energy Dashboard</h1>'
        '<p style="margin:4px 0 0;font-size:.95rem;color:#1a1a6e;">'
        'Observatorio del SNI · Tiempo Real · Crisis · '
        'WAMS · Estabilidad · Simuladores</p></div>', unsafe_allow_html=True)

def sidebar_controls():
    with st.sidebar:
        st.markdown("### ⚙️ Controles")

        ano = st.selectbox("📅 Año de referencia", [2026, 2025, 2024, 2023, 2022], index=0,
                           help="Selecciona el año para todas las gráficas")
        st.caption(
            f"📌 **Qué cambia:** Todas las gráficas de generación, capacidad, "
            f"racionamiento, inercia, CO₂ y precios actualizan para datos de **{ano}**. "
            f"Para 2026 muestra datos YTD (ene-sep)."
        )

        janela = st.selectbox("🕐 Ventana temporal (tiempo real)",
                              ["30 días", "60 días", "90 días", "180 días"], index=0)
        st.caption(
            "📌 **Qué cambia:** En la pestaña **Carga (Tiempo Real)**, define cuántos "
            "días de datos se muestran. Ventanas mayores = más contexto histórico."
        )

        st.markdown("---")
        st.markdown("### 👥 Colaboración")
        st.markdown(
            "🇪🇨 **Prof. Santiago Torres** — U. Cuenca\n\n"
            "🇨🇴 **Prof. Sergio Rivera** — UNAL"
        )
        st.markdown("---")
        st.markdown("### 📡 Fuentes de Datos")
        for nome, url in list(FONTES_DADOS.items())[:6]:
            st.markdown(f"- [{nome}]({url})")
        st.markdown("---")
        st.caption("CENACE: `cenace.gob.ec` · Datos Abiertos: `datosabiertos.gob.ec`")

        # Manual de usuario
        st.markdown("---")
        with st.expander("📖 Manual de Usuario"):
            st.markdown(
                "**Cómo usar el Dashboard:**\n\n"
                "1. **Seleccione el año** → todas las pestañas actualizan.\n\n"
                "2. **Ventana temporal** → afecta solo **Carga (Tiempo Real)**.\n\n"
                "3. **Navegación:** Use el dropdown principal para alternar entre 13 pestañas.\n\n"
                "4. **Simuladores:** En las pestañas **Estabilidad** y **Racionamiento**, "
                "ajuste los sliders para simular escenarios.\n\n"
                "5. **Cajas de Impacto (💡):** Cada gráfica explica el impacto "
                "en el sistema y las decisiones que se pueden tomar.\n\n"
                "6. **Escenarios Futuros:** Las pestañas Generación, Hidrología y Carga "
                "incluyen proyecciones 2027-2030.\n\n"
                "**Pestañas:**\n"
                "- 📊 Resumen: KPIs del SNI\n"
                "- ⚡ Generación: Matriz eléctrica\n"
                "- 🌊 Hidrología: Embalses\n"
                "- 📈 Carga: Demanda tiempo real\n"
                "- 🔄 Intercambio: Col/Perú\n"
                "- 🌪️ IBR: Eólica + Solar\n"
                "- 🚧 Racionamiento: Crisis 2024\n"
                "- 📡 WAMS: Sincrofasores\n"
                "- 🧠 Estabilidad: 4 simuladores\n"
                "- 🔬 Eventos: ML + TKEO\n"
                "- 💰 Mercado: Precios\n"
                "- 🏭 CO₂: Emisiones\n"
                "- 🔧 Torres/Rivera: Open source"
            )
    return {"ano": ano, "janela": janela}

# =============================================================================
# TAB 1: RESUMEN EJECUTIVO
# =============================================================================
def render_tab_resumo(settings):
    ano = settings["ano"]
    janela = settings["janela"]
    st.subheader("📊 Resumen Ejecutivo — Sistema Nacional Interconectado (SNI)")

    gen_mix = generate_generation_mix(ano)
    total_gwh = gen_mix["geracao_gwh"].sum()
    hidro_gwh = gen_mix[gen_mix["fonte"]=="Hidro"]["geracao_gwh"].sum()
    pct_hidro = hidro_gwh / max(total_gwh, 1) * 100

    cap = CAPACIDAD_POR_ANO.get(ano, CAPACIDAD_POR_ANO[2026])
    pico = DEMANDA_PICO.get(ano, 5250)
    janela_txt = f" · Ventana: {janela}" if ano == 2026 else ""

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric(f"Capacidad ({ano})", f"{cap['total']:,} MW")
    m2.metric(f"Generación ({ano})", f"{total_gwh:,.0f} GWh")
    m3.metric(f"Hidro ({ano})", f"{pct_hidro:.0f}%")
    m4.metric(f"Demanda Pico ({ano})", f"{pico:,} MW")
    m5.metric("Transmisión", f"{TRANSMISION['total_km']:,} km")

    st.caption(f"📅 Período de análisis: **{ano}**{janela_txt}")

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(go.Pie(
            labels=gen_mix["fonte"], values=gen_mix["geracao_gwh"], hole=0.45,
            marker=dict(colors=[GEN_COLORS.get(f,"#999") for f in gen_mix["fonte"]]),
            textinfo="label+percent", textfont=dict(size=10)))
        fig.update_layout(title=f"Matriz de Generación ({ano}): {total_gwh:,.0f} GWh",
                          height=380, margin=dict(t=50,b=20,l=20,r=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = go.Figure(go.Bar(
            x=gen_mix["fonte"], y=gen_mix["geracao_gwh"],
            marker_color=[GEN_COLORS.get(f,"#999") for f in gen_mix["fonte"]],
            text=gen_mix["geracao_gwh"].apply(lambda x: f"{x:,.0f}"), textposition="outside"))
        fig2.update_layout(title=f"Generación por Fuente ({ano})",
                           yaxis_title="GWh", height=380, xaxis_tickangle=-45,
                           margin=dict(t=50,b=100,l=60,r=20))
        st.plotly_chart(fig2, use_container_width=True)

    _impact_box(f"En {ano}: hidro representa {pct_hidro:.0f}% de la generación. "
                f"{'ALERTA: dependencia excesiva de hidro — diversificar con solar/eólica.' if pct_hidro > 80 else 'OK: mix balanceado.'}",
                "alert" if pct_hidro > 85 else "success")

    # Tabla resumen del SNI
    st.markdown("#### 🏗️ Infraestructura del SNI")
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(pd.DataFrame([
            {"Componente": "Centrales hidroeléctricas", "Valor": "40+"},
            {"Componente": "Centrales térmicas", "Valor": "25+"},
            {"Componente": "Subestaciones 500 kV", "Valor": str(TRANSMISION['500 kV']['subestaciones'])},
            {"Componente": "Subestaciones 230 kV", "Valor": str(TRANSMISION['230 kV']['subestaciones'])},
            {"Componente": "Subestaciones 138 kV", "Valor": str(TRANSMISION['138 kV']['subestaciones'])},
            {"Componente": "Líneas 500 kV", "Valor": f"{TRANSMISION['500 kV']['km']} km"},
            {"Componente": "Líneas 230 kV", "Valor": f"{TRANSMISION['230 kV']['km']} km"},
            {"Componente": "Líneas 138 kV", "Valor": f"{TRANSMISION['138 kV']['km']} km"},
        ]), use_container_width=True, hide_index=True)
    with col2:
        st.dataframe(DISTRIBUIDORAS[["empresa","provincias","clientes_miles"]],
                     use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────────────────────────────────
    # HALLAZGOS CLAVE POR PESTAÑA
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔍 Hallazgos Clave por Pestaña")
    st.caption("Resumen de los descubrimientos más importantes de cada módulo del dashboard.")

    em = EMISIONES_HISTORICA[EMISIONES_HISTORICA["ano"]==ano]
    intensidad = em.iloc[0]["intensidad_gkwh"] if len(em) > 0 else 156
    prec = PRECIOS_HISTORICOS[PRECIOS_HISTORICOS["ano"]==ano]
    precio = prec.iloc[0]["precio_promedio_usd_mwh"] if len(prec) > 0 else 45

    hallazgos = [
        ("⚡ Generación", f"Matriz dominada por hidro ({pct_hidro:.0f}%). "
         f"CCS (1,500 MW) + Paute Integral (1,757 MW) = 62% de capacidad hidro. "
         f"Térmica de respaldo: {cap.get('termica',3439):,} MW pero solo ~850 MW operativos en crisis."),
        ("🌊 Hidrología", f"Embalses al {EMBALSES['Mazar']['niveles_historicos'].get(ano,70)}% promedio. "
         f"ENOS puede reducir hidro al 49% (2024). Complejo Paute = corazón del sistema."),
        ("📈 Carga", f"Demanda pico: {pico:,} MW. Crecimiento ~3.5%/año. "
         f"Proyección 2030: ~6,030 MW. Récord histórico: 5,110 MW (2025)."),
        ("🔄 Intercambio", f"Colombia (525 MW) + Perú (110 MW). En 2024 Colombia cortó exportaciones. "
         f"Nueva línea 500 kV EC-PE (600 MW, 2029) proveerá redundancia."),
        ("🌪️ IBR", f"Solo {cap.get('eolica',350)+cap.get('solar',200):,} MW eólica+solar "
         f"({(cap.get('eolica',350)+cap.get('solar',200))/cap['total']*100:.1f}% del total). "
         f"Plan Maestro: 3,800 MW para 2030."),
        ("🚧 Racionamiento", "Crisis 2024: déficit 1,080 MW, racionamiento 14h/día. "
         "Causa: sequía + térmica inoperativa + corte importaciones."),
        ("🔴 Congestión", f"19 líneas monitoreadas. Trinitaria-Salitral (98%) y Salitral-Pascuales (97%) "
         f"en pico. Costo congestión: USD {CONGESTION_ZONAL['costo_congestion_musd'].sum():.1f}M/año."),
        ("📡 WAMS", f"{PMU_NETWORK['PMUs instalados']} PMUs instalados. "
         f"Modo inter-área EC-CO (0.35 Hz, ζ=3%): riesgo en importaciones máximas."),
        ("🧠 Estabilidad", "4 simuladores: subfrecuencia, sobrefrecuencia, P-V, TNEP AC. "
         "Inercia declinante por penetración IBR."),
        ("🔬 Eventos", "TKEO detecta eventos en <10 ms. 1D-ConvLSTM: 97% acuracia en SSO."),
        ("💰 Mercado", f"Precio promedio {ano}: ${precio}/MWh. Crisis 2024: subió a $78/MWh. "
         f"Déficit tarifario: ~598 MUSD/año."),
        ("💰 Precios Nodales", "12 nodos con variación significativa. "
         "Machala (nodo importador) = precio más alto. CCS = precio más bajo."),
        ("🏭 Emisiones", f"Intensidad: {intensidad} gCO₂/kWh ({ano}). "
         f"Entre los más bajos de LatAm. Crisis 2024 subió a 252 gCO₂/kWh."),
        ("⚠️ Contingencias", "10 contingencias críticas N-2. SPS activo desde 2015. "
         "12 subestaciones sin transformador de respaldo."),
    ]
    for tab_name, finding in hallazgos:
        with st.expander(f"**{tab_name}**", expanded=False):
            st.markdown(finding)

# =============================================================================
# TAB 2: GENERACIÓN
# =============================================================================
def render_tab_geracao(settings):
    ano = settings["ano"]
    st.subheader("⚡ Generación — Matriz Elétrica del Ecuador")

    gen_mix = generate_generation_mix(ano)
    st.dataframe(gen_mix, use_container_width=True, hide_index=True)

    # Crisis vs normal
    if ano == 2024:
        _impact_box("2024 fue año de crisis: hidro bajó al 49% en noviembre. "
                    "Térmica subió al 21% pero no cubrió el déficit de 1,080 MW.", "danger")
    else:
        _impact_box(f"En {ano}: matriz dominada por hidro (~{gen_mix[gen_mix['fonte']=='Hidro']['pct'].values[0]:.0f}%). "
                    f"Decisión: diversificar con solar+eólica para reducir vulnerabilidad a sequía.", "alert")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 💧 Centrales Hidroeléctricas")
        st.dataframe(CENTRALES_HIDRO[["central","potencia_mw","rio","provincia","ano","tipo"]],
                     use_container_width=True, hide_index=True)
    with col2:
        st.markdown("#### 🔥 Centrales Térmicas")
        st.dataframe(CENTRALES_TERMICAS[["central","potencia_mw","combustible","provincia","estado"]],
                     use_container_width=True, hide_index=True)

    # Generación por zona
    st.markdown("#### ⚡ Generación por Zona Geográfica")
    zonas = ["Norte (Sierra)", "Sur (Azuay/Loja)", "Costa (Guayas)", "Oriente (Coca)", "Costa Norte"]
    hidro_z = [400, 2100, 450, 1500, 210]
    termo_z = [150, 100, 900, 180, 400]
    ibr_z = [80, 90, 200, 10, 30]

    fig_z = go.Figure()
    fig_z.add_trace(go.Bar(x=zonas, y=hidro_z, name="Hidro", marker_color="#2E86AB"))
    fig_z.add_trace(go.Bar(x=zonas, y=termo_z, name="Térmico", marker_color="#C73E1D"))
    fig_z.add_trace(go.Bar(x=zonas, y=ibr_z, name="IBR (Eólica+Solar)", marker_color="#6A994E"))
    fig_z.update_layout(barmode="stack", title=f"Capacidad por Zona ({ano}, MW)",
                        yaxis_title="MW", height=400, legend=dict(orientation="h",y=1.12))
    st.plotly_chart(fig_z, use_container_width=True)
    _impact_box("Sur (Paute Integral: 1,757 MW) concentra 35% de la generación hidro. "
                "Oriente (CCS: 1,500 MW) aporta 30%. Ambas zonas vulnerables a sequía.", "alert")

    # Proyecciones 2027-2030
    st.markdown("---")
    st.markdown("#### 🔮 Proyecciones de Capacidad 2027-2030 (Plan Maestro)")
    proj_anos = [2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030]
    proj_hidro = [5200, 5300, 5400, 5550, 5700, 5900, 6100, 6400, 6800]
    proj_termo = [3439, 3439, 3540, 3900, 4200, 4500, 4800, 5000, 5200]
    proj_eolica = [169, 179, 207, 250, 350, 500, 850, 1500, 2000]
    proj_solar = [30, 41, 41, 80, 200, 400, 900, 1500, 1800]

    fig_proj = go.Figure()
    fig_proj.add_trace(go.Bar(x=proj_anos, y=proj_hidro, name="Hidro", marker_color="#2E86AB"))
    fig_proj.add_trace(go.Bar(x=proj_anos, y=proj_termo, name="Térmico", marker_color="#C73E1D"))
    fig_proj.add_trace(go.Bar(x=proj_anos, y=proj_eolica, name="Eólica", marker_color="#6A994E"))
    fig_proj.add_trace(go.Bar(x=proj_anos, y=proj_solar, name="Solar", marker_color="#F18F01"))
    fig_proj.add_vline(x=ano, line_dash="dash", line_color="red", annotation_text=f"{ano}")
    fig_proj.update_layout(barmode="stack", title="Proyección de Capacidad Instalada (MW)",
                           yaxis_title="MW", height=400, legend=dict(orientation="h",y=1.12))
    st.plotly_chart(fig_proj, use_container_width=True)
    _impact_box("Plan Maestro: solar crecerá de 41 MW (2024) a 1,800 MW (2030). "
                "Eólica de 179 MW a 2,000 MW. Hidro de 5,400 a 6,800 MW. "
                "Artículo Nature Energy 2026: VRE + hidro flexible previene crisis futuras.", "info")

    # ─── SIMULADOR INTERACTIVO: ESCENARIO DE MIX ENERGÉTICO ───
    st.markdown("---")
    st.markdown("### 🎮 Simulador: ¿Qué pasa si cambiamos el mix?")
    st.markdown("Ajuste la capacidad de cada fuente para ver el impacto en generación, "
                "emisiones y vulnerabilidad a sequía.")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        hidro_add = st.slider("Hidro adicional (MW)", -500, 2000, 0, 100,
                              help="Nuevos proyectos hidroeléctricos")
    with col2:
        solar_add = st.slider("Solar adicional (MW)", 0, 3000, 500, 100,
                              help="Parques solares fotovoltaicos")
    with col3:
        eolica_add = st.slider("Eólica adicional (MW)", 0, 3000, 500, 100,
                               help="Parques eólicos onshore")
    with col4:
        termo_add = st.slider("Térmica adicional (MW)", -500, 2000, 0, 100,
                              help="Plantas térmicas de respaldo")

    # Cálculos del escenario
    cap_base = CAPACIDAD_POR_ANO.get(ano, CAPACIDAD_POR_ANO[2026])
    gen_mix_base = generate_generation_mix(ano)
    pct_hidro_base = gen_mix_base[gen_mix_base['fonte']=='Hidro']['pct'].values[0] if len(gen_mix_base[gen_mix_base['fonte']=='Hidro']) > 0 else 75
    pct_vre_base = gen_mix_base[gen_mix_base['fonte'].isin(['Eólica','Solar'])]['pct'].sum()
    hidro_new = cap_base.get('hidro', 5700) + hidro_add
    solar_new = cap_base.get('solar', 200) + solar_add
    eolica_new = cap_base.get('eolica', 350) + eolica_add
    termo_new = cap_base.get('termica', 3439) + termo_add
    total_new = hidro_new + solar_new + eolica_new + termo_new + cap_base.get('biomasa', 50) + cap_base.get('biogas', 30)
    
    # Generación anual (factor de capacidad)
    gen_hidro_new = hidro_new * 8760 * 0.55 / 1000  # GWh
    gen_solar_new = solar_new * 8760 * 0.18 / 1000
    gen_eolica_new = eolica_new * 8760 * 0.25 / 1000
    gen_termo_new = termo_new * 8760 * 0.35 / 1000  # factor despacho
    gen_total_new = gen_hidro_new + gen_solar_new + gen_eolica_new + gen_termo_new
    
    pct_hidro_new = gen_hidro_new / gen_total_new * 100
    pct_vre_new = (gen_solar_new + gen_eolica_new) / gen_total_new * 100
    
    # Emisiones (térmica: 0.5 tCO2/MWh)
    emisiones_new = gen_termo_new * 0.5 / 1000  # MtCO2
    
    # Vulnerabilidad a sequía (si hidro > 70%, alto riesgo)
    riesgo_sequia = "ALTO" if pct_hidro_new > 75 else "MEDIO" if pct_hidro_new > 60 else "BAJO"
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Capacidad total", f"{total_new:,.0f} MW",
              delta=f"{total_new - cap_base['total']:+,.0f} MW")
    c2.metric("Hidro %", f"{pct_hidro_new:.1f}%",
              delta=f"{pct_hidro_new - pct_hidro_base:+.1f} pp")
    c3.metric("VRE % (solar+eólica)", f"{pct_vre_new:.1f}%",
              delta=f"{pct_vre_new - pct_vre_base:+.1f} pp")
    c4.metric("Emisiones", f"{emisiones_new:.1f} MtCO₂",
              delta="vs. 4.7 MtCO₂ (2024)")
    
    # Gráfico comparativo
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(x=["Actual", "Propuesto"], 
                              y=[pct_hidro_base, pct_hidro_new],
                              name="Hidro %", marker_color="#2E86AB"))
    fig_comp.add_trace(go.Bar(x=["Actual", "Propuesto"],
                              y=[pct_vre_base, pct_vre_new],
                              name="VRE %", marker_color="#6A994E"))
    fig_comp.update_layout(barmode="group", title="Comparación: Mix Actual vs Propuesto",
                           yaxis_title="%", height=350)
    st.plotly_chart(fig_comp, use_container_width=True)
    
    _impact_box(f"Escenario propuesto: hidro {pct_hidro_new:.0f}%, VRE {pct_vre_new:.0f}%. "
                f"Riesgo de sequía: **{riesgo_sequia}**. "
                f"{'✅ Reducción de vulnerabilidad.' if pct_hidro_new < 70 else '⚠️ Aún dependiente de hidro.'}",
                "success" if pct_hidro_new < 70 else "alert")

# =============================================================================
# TAB 3: HIDROLOGÍA
# =============================================================================
def render_tab_hidrologia(settings):
    ano = settings["ano"]
    st.subheader("🌊 Hidrología y Embalses — Complejo Paute y Nacional")
    panel_embalses_celecsur(dias_historico=90)
    st.markdown("---")
    st.markdown("#### 🧪 Modelo didáctico de niveles (sintético calibrado)")

    st.markdown(
        "Ecuador depende **~72-90%** de la generación hidroeléctrica. "
        "El **Complejo Paute Integral** (Mazar 170 MW + Molino 1,100 MW + Sopladora 487 MW) "
        "es el corazón del sistema."
    )

    col1, col2 = st.columns(2)
    with col1:
        emb_sel = st.selectbox("Embalse", list(EMBALSES.keys()), index=0)
    with col2:
        st.metric(f"Nivel promedio ({ano})",
                  f"{EMBALSES[emb_sel]['niveles_historicos'].get(ano, 70)}%",
                  delta=f"vs. {EMBALSES[emb_sel]['niveles_historicos'].get(2023, 70)}% (2023)",
                  delta_color="normal" if EMBALSES[emb_sel]['niveles_historicos'].get(ano, 70) > 60 else "inverse")

    # Gráfica de niveles
    niv = generate_reservoir_levels(emb_sel, ano)
    fig_niv = go.Figure(go.Scatter(
        x=niv["mes"], y=niv["nivel_pct"], mode="lines+markers",
        line=dict(color="#2E86AB", width=3), marker=dict(size=8)))
    emb = EMBALSES[emb_sel]
    fig_niv.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="Crítico (20%)")
    fig_niv.add_hline(y=50, line_dash="dot", line_color="orange", annotation_text="Alerta (50%)")
    fig_niv.update_layout(title=f"Nivel Mensual del Embalse {emb_sel} ({ano})",
                          yaxis_title="Nivel (%)", height=350)
    st.plotly_chart(fig_niv, use_container_width=True)
    _impact_box(f"{emb_sel}: nivel promedio de {EMBALSES[emb_sel]['niveles_historicos'].get(ano, 70)}% en {ano}. "
                f"{'CRÍTICO: nivel bajo, riesgo de racionamiento.' if EMBALSES[emb_sel]['niveles_historicos'].get(ano, 70) < 50 else 'Aceptable.'}",
                "danger" if EMBALSES[emb_sel]['niveles_historicos'].get(ano, 70) < 50 else "success")

    # Embalses comparativo
    st.markdown("#### 📊 Comparativo de Embalses por Año")
    emb_df = pd.DataFrame([
        {"Embalse": k, **{str(a): v["niveles_historicos"].get(a, "N/A")
                          for a in [2022,2023,2024,2025,2026]}}
        for k, v in EMBALSES.items()
    ])
    st.dataframe(emb_df, use_container_width=True, hide_index=True)

    # Crisis hídricas
    st.markdown("#### ⚠️ Crisis Hídricas Históricas")
    st.dataframe(pd.DataFrame([
        {"Año": "2009-10", "Evento": "Sequía Paute", "Arm_min": "25%", "Impacto": "Racionamiento 6h/día"},
        {"Año": "2016", "Evento": "El Niño fuerte", "Arm_min": "30%", "Impacto": "Déficit 300 MW"},
        {"Año": "2023-24", "Evento": "Peor sequía 50 años", "Arm_min": "38%",
         "Impacto": "Racionamiento 14h/día, déficit 1,080 MW"},
    ]), use_container_width=True, hide_index=True)

    # Escenarios hidrológicos futuros
    st.markdown("---")
    st.markdown("#### 🔮 Escenarios Hidrológicos 2027-2030")
    cen_hidro = pd.DataFrame([
        {"Escenario": "Húmedo (La Niña)", "Arm_medio": "85%", "Riesgo_deficit": "2%",
         "Hidro_pct": "90%", "Despacho_térmico": "Mínimo"},
        {"Escenario": "Medio (Neutral)", "Arm_medio": "65%", "Riesgo_deficit": "8%",
         "Hidro_pct": "78%", "Despacho_térmico": "Moderado"},
        {"Escenario": "Seco (El Niño mod.)", "Arm_medio": "45%", "Riesgo_deficit": "20%",
         "Hidro_pct": "60%", "Despacho_térmico": "Máximo"},
        {"Escenario": "Crítico (El Niño fuerte)", "Arm_medio": "30%", "Riesgo_deficit": "45%",
         "Hidro_pct": "49%", "Despacho_térmico": "Emergencial + racionamiento"},
    ])
    st.dataframe(cen_hidro, use_container_width=True, hide_index=True)
    _impact_box("Con cambio climático y ENOS, las sequías severas pueden ser más frecuentes. "
                "Decisión: diversificar matriz con solar+eólica reduce dependencia hídrica "
                "(Nature Energy 2026: VRE + hidro flexible mitiga crisis).", "alert")

    # ─── SIMULADOR INTERACTIVO: IMPACTO HIDROLÓGICO ───
    st.markdown("---")
    st.markdown("### 🎮 Simulador: Impacto de Escenario Hidrológico")
    st.markdown("Ajuste los parámetros para ver cómo diferentes condiciones hidrológicas "
                "afectan la generación y el riesgo de déficit.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        lluvia_pct = st.slider("Variación de lluvias (%)", -60, 40, 0, 5,
                               help="Negativo = sequía, Positivo = año húmedo",
                               key="hidro_lluvia")
    with col2:
        demanda_hidro = st.slider("Demanda del sistema (MW)", 3500, 6500, 5100, 100,
                                  key="hidro_demanda")
    with col3:
        termo_disp = st.slider("Térmica disponible (MW)", 500, 4500, 2800, 100,
                               key="hidro_termo")
    
    # Cálculos
    cap_hidro_base = 5700  # MW
    factor_hidro = 1.0 + (lluvia_pct / 100) * 0.5  # lluvia afecta ~50% de la capacidad
    gen_hidro_sim = cap_hidro_base * factor_hidro * 0.55  # factor capacidad
    gen_termo_sim = min(termo_disp, demanda_hidro - gen_hidro_sim) if demanda_hidro > gen_hidro_sim else 0
    gen_total_sim = gen_hidro_sim + gen_termo_sim
    deficit_sim = max(0, demanda_hidro - gen_total_sim)
    
    pct_hidro_sim = gen_hidro_sim / gen_total_sim * 100 if gen_total_sim > 0 else 0
    nivel_embalse_sim = max(10, min(95, 70 + lluvia_pct * 0.5))
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gen. Hidro", f"{gen_hidro_sim:,.0f} MW",
              delta=f"Factor: {factor_hidro:.2f}")
    c2.metric("Gen. Total", f"{gen_total_sim:,.0f} MW")
    c3.metric("Nivel embalse", f"{nivel_embalse_sim:.0f}%",
              delta=f"{lluvia_pct:+d}% lluvias")
    if deficit_sim > 0:
        c4.metric("⚠️ Déficit", f"{deficit_sim:,.0f} MW",
                  delta="CRÍTICO", delta_color="inverse")
    else:
        c4.metric("✅ Superávit", f"{gen_total_sim - demanda_hidro:,.0f} MW")
    
    # Gráfico de niveles
    fig_nivel = go.Figure()
    fig_nivel.add_trace(go.Indicator(
        mode="gauge+number",
        value=nivel_embalse_sim,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Nivel de Embalse (%)"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "#2E86AB"},
            'steps': [
                {'range': [0, 30], 'color': "#C73E1D"},
                {'range': [30, 60], 'color': "#F18F01"},
                {'range': [60, 100], 'color': "#6A994E"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 30
            }
        }
    ))
    fig_nivel.update_layout(height=300)
    st.plotly_chart(fig_nivel, use_container_width=True)
    
    if deficit_sim > 200:
        msg = f"DÉFICIT de {deficit_sim:,.0f} MW — racionamiento necesario"
        color = "danger"
    elif deficit_sim > 0:
        msg = f"Déficit leve de {deficit_sim:,.0f} MW — activar reserva"
        color = "alert"
    else:
        msg = f"Sistema estable con superávit de {gen_total_sim - demanda_hidro:,.0f} MW"
        color = "success"
    
    _impact_box(f"Escenario hidrológico ({lluvia_pct:+d}% lluvias): {msg}. "
                f"Nivel embalse: {nivel_embalse_sim:.0f}%. Hidro: {pct_hidro_sim:.0f}% del mix.", color)

# =============================================================================
# TAB 4: CARGA / DEMANDA (TIEMPO REAL)
# =============================================================================
def render_tab_carga(settings):
    ano = settings["ano"]
    janela_dias = int(settings["janela"].split()[0])
    st.subheader("📈 Carga y Demanda — Tiempo Real e Histórico")

    # Datos tiempo real (REALES: CENACE SCADA, parser Plotly)
    rt = panel_cenace_tiempo_real(mostrar_curvas=True, mostrar_distribuidoras=True)
    st.markdown("---")
    st.markdown("#### 🧪 Modelo didáctico (perfil sintético calibrado)")

    # Perfil de demanda
    st.markdown(f"#### 📉 Perfil de Demanda — Últimos {janela_dias} días")
    pico = DEMANDA_PICO.get(ano, 5100)
    dem = generate_demand_profile(janela_dias, pico)
    fig_dem = go.Figure(go.Scatter(
        x=dem["fecha"], y=dem["demanda_mw"], mode="lines",
        line=dict(color="#003087", width=1.5), name="Demanda"))
    fig_dem.add_hline(y=pico, line_dash="dash", line_color="red",
                      annotation_text=f"Pico histórico: {pico} MW")
    fig_dem.update_layout(title=f"Demanda del SNI ({janela_dias} días)",
                          yaxis_title="MW", height=350)
    st.plotly_chart(fig_dem, use_container_width=True)

    _impact_box(f"Demanda pico 2025: 5,110 MW (récord histórico). Crecimiento ~3.5%/año. "
                f"Proyección 2030: ~6,000 MW. Decisión: planificar nueva generación firme.", "info")

    # Proyecciones de demanda futura
    st.markdown("---")
    st.markdown("#### 🔮 Proyecciones de Demanda 2027-2030 (CENACE)")
    proj_dem = pd.DataFrame([
        {"Año": 2024, "Pico_MW": 5063, "Medio_MW": 3800, "Crec_pct": 5.5},
        {"Año": 2025, "Pico_MW": 5110, "Medio_MW": 3850, "Crec_pct": 0.9},
        {"Año": 2026, "Pico_MW": 5250, "Medio_MW": 3950, "Crec_pct": 2.6},
        {"Año": 2027, "Pico_MW": 5430, "Medio_MW": 4100, "Crec_pct": 3.4},
        {"Año": 2028, "Pico_MW": 5620, "Medio_MW": 4250, "Crec_pct": 3.5},
        {"Año": 2029, "Pico_MW": 5820, "Medio_MW": 4400, "Crec_pct": 3.6},
        {"Año": 2030, "Pico_MW": 6030, "Medio_MW": 4560, "Crec_pct": 3.6},
    ])
    fig_pd = go.Figure()
    fig_pd.add_trace(go.Scatter(x=proj_dem["Año"], y=proj_dem["Pico_MW"],
                                mode="lines+markers", name="Pico", line=dict(color="#C73E1D", width=3)))
    fig_pd.add_trace(go.Scatter(x=proj_dem["Año"], y=proj_dem["Medio_MW"],
                                mode="lines+markers", name="Medio", line=dict(color="#2E86AB", width=2)))
    fig_pd.add_vline(x=ano, line_dash="dash", line_color="gray", annotation_text=f"{ano}")
    fig_pd.update_layout(title="Proyección de Demanda Pico y Media (MW)",
                         yaxis_title="MW", height=350)
    st.plotly_chart(fig_pd, use_container_width=True)
    st.dataframe(proj_dem, use_container_width=True, hide_index=True)

    # Fuentes API
    st.markdown("---")
    st.markdown("#### 🔗 Fuentes de datos CENACE")
    st.caption("Endpoints reales: `cenace.gob.ec/info-operativa/InformacionOperativa.htm` (Plotly JSON) · `generacioncsr.celec.gob.ec:8443/ords/csr/sardomcsr` (CELEC Sur) · API XM `pydataxm` · `datosabiertos.gob.ec/dataset/?organization=cenace`")
    st.text("  ✅ Producción de Energía Eléctrica del Parque Generador (CSV/XLSX)")
    st.text("  ✅ Potencia Efectiva de Generación en el SNI (CSV/XLSX)")
    st.text("  ✅ Capacidad Instalada del SNI (CSV/XLSX)")
    st.text("  ✅ Información Operativa en Tiempo Real (18 figuras Plotly, 30 min)")

    # ─── SIMULADOR INTERACTIVO: CRECIMIENTO DE DEMANDA ───
    st.markdown("---")
    st.markdown("### 🎮 Simulador: Proyección de Demanda")
    st.markdown("¿Cómo cambia la demanda futura según diferentes tasas de crecimiento?")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        tasa_crec = st.slider("Tasa de crecimiento anual (%)", 1.0, 6.0, 3.5, 0.1,
                              help="Crecimiento histórico ~3.5%/año",
                              key="carga_tasa")
    with col2:
        ano_base_dem = st.selectbox("Año base", [2024, 2025, 2026], index=2,
                                    key="carga_base")
    with col3:
        eficiencia = st.slider("Eficiencia energética (%)", 0, 30, 0, 5,
                               help="Reducción por eficiencia y conservación",
                               key="carga_efic")
    
    # Proyección
    pico_base = DEMANDA_PICO.get(ano_base_dem, 5250)
    anos_proj = list(range(ano_base_dem, 2031))
    demanda_sin_efic = [pico_base * (1 + tasa_crec/100)**(a - ano_base_dem) for a in anos_proj]
    demanda_con_efic = [d * (1 - eficiencia/100) for d in demanda_sin_efic]
    
    fig_crec = go.Figure()
    fig_crec.add_trace(go.Scatter(x=anos_proj, y=demanda_sin_efic,
                                  mode="lines+markers", name=f"Sin eficiencia ({tasa_crec}%/año)",
                                  line=dict(color="#C73E1D", width=3)))
    if eficiencia > 0:
        fig_crec.add_trace(go.Scatter(x=anos_proj, y=demanda_con_efic,
                                      mode="lines+markers", name=f"Con eficiencia -{eficiencia}%",
                                      line=dict(color="#6A994E", width=3, dash="dash")))
    fig_crec.add_hline(y=6000, line_dash="dot", line_color="orange",
                       annotation_text="Límite planificado 2030")
    fig_crec.update_layout(title="Proyección de Demanda Pico (MW)",
                           xaxis_title="Año", yaxis_title="MW", height=350)
    st.plotly_chart(fig_crec, use_container_width=True)
    
    pico_2030 = demanda_con_efic[-1]
    cap_total = CAPACIDAD_POR_ANO.get(ano_base_dem, CAPACIDAD_POR_ANO[2026])['total']
    c1, c2, c3 = st.columns(3)
    c1.metric("Pico 2030", f"{pico_2030:,.0f} MW")
    c2.metric("Crecimiento acumulado", f"{(pico_2030/pico_base - 1)*100:.1f}%")
    c3.metric("Ahorro por eficiencia", f"{demanda_sin_efic[-1] - pico_2030:,.0f} MW" if eficiencia > 0 else "N/A")
    
    _impact_box(f"Con crecimiento del {tasa_crec}%/año y {eficiencia}% de eficiencia: "
                f"demanda pico 2030 = {pico_2030:,.0f} MW. "
                f"Decisión: planificar {(pico_2030*1.15 - cap_total):,.0f} MW de nueva capacidad "
                f"(reserva 15%).", "info")

# =============================================================================
# TAB 5: INTERCAMBIO INTERNACIONAL
# =============================================================================
def render_tab_intercambio(settings):
    ano = settings["ano"]
    st.subheader("🔄 Intercambio Internacional — Colombia y Perú")
    panel_intercambio_xm(dias=30)
    st.markdown("---")

    st.markdown(
        "Ecuador está interconectado con **Colombia** (230 kV, 525 MW) y **Perú** (230 kV, 110 MW). "
        "En construcción: **500 kV Ecuador-Perú** (600 MW, operativa 2029)."
    )

    col1, col2, col3 = st.columns(3)
    for i, (nombre, datos) in enumerate(INTERCONEXIONES.items()):
        with [col1, col2, col3][i]:
            st.markdown(f"#### {nombre}")
            st.metric("Capacidad", f"{datos['capacidad_mw']} MW")
            st.caption(f"{datos['voltaje']} | {datos['estado']}")
            flujo = datos["flujo_historico"].get(ano, 0)
            if flujo > 0:
                st.metric(f"Importación ({ano})", f"{flujo:,} GWh")

    # Gráfica de importaciones
    st.markdown("#### 📊 Evolución de Importaciones")
    anos = [2022, 2023, 2024, 2025, 2026]
    col_data = [INTERCONEXIONES["EC-CO (230kV)"]["flujo_historico"].get(a, 0) for a in anos]
    pe_data = [INTERCONEXIONES["EC-PE (230kV)"]["flujo_historico"].get(a, 0) for a in anos]

    fig_int = go.Figure()
    fig_int.add_trace(go.Bar(x=anos, y=col_data, name="Colombia", marker_color="#7B2D8E"))
    fig_int.add_trace(go.Bar(x=anos, y=pe_data, name="Perú", marker_color="#D4A373"))
    fig_int.add_vline(x=ano, line_dash="dash", line_color="red")
    fig_int.update_layout(barmode="stack", title="Importación de Energía (GWh)",
                          yaxis_title="GWh", height=350)
    st.plotly_chart(fig_int, use_container_width=True)

    _impact_box(f"En 2024, Colombia cortó exportaciones (racionamiento propio). "
                f"Ecuador quedó sin ~4% de su abastecimiento. "
                f"Decisión: línea 500 kV EC-PE (2029) provee redundancia de 600 MW.", "alert")

    # Detalles
    st.markdown("#### 📋 Detalles de Interconexiones")
    int_df = pd.DataFrame([
        {"Interconexión": k, "País": v["pais"], "Voltaje": v["voltaje"],
         "Capacidad (MW)": v["capacidad_mw"], "Líneas": v["lineas"],
         "Estado": v["estado"]}
        for k, v in INTERCONEXIONES.items()
    ])
    st.dataframe(int_df, use_container_width=True, hide_index=True)

    # ─── SIMULADOR INTERACTIVO: ESCENARIO DE INTERCAMBIO ───
    st.markdown("---")
    st.markdown("### 🎮 Simulador: Escenario de Importación/Exportación")
    st.markdown("Simule diferentes niveles de intercambio con Colombia y Perú "
                "y vea el impacto en el balance energético del SNI.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        imp_col = st.slider("Importación Colombia (MW)", 0, 525, 200, 25,
                            help="Capacidad máxima: 525 MW",
                            key="interc_col")
    with col2:
        imp_pe = st.slider("Importación Perú (MW)", 0, 600, 0, 25,
                           help="230 kV: 110 MW · 500 kV: 600 MW (2029)",
                           key="interc_pe")
    with col3:
        demanda_int = st.slider("Demanda del SNI (MW)", 3500, 6500, 5100, 100,
                                key="interc_dem")
    
    # Cálculos
    gen_local = 5700 * 0.55 + 3439 * 0.35  # hidro + termo promedio
    imp_total = imp_col + imp_pe
    oferta_total = gen_local + imp_total
    deficit_int = max(0, demanda_int - oferta_total)
    pct_import = imp_total / demanda_int * 100
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Importación total", f"{imp_total} MW",
              delta=f"{pct_import:.1f}% de demanda")
    c2.metric("Oferta total", f"{oferta_total:,.0f} MW")
    c3.metric("Balance", f"{oferta_total - demanda_int:+,.0f} MW",
              delta="OK" if oferta_total >= demanda_int else "DÉFICIT",
              delta_color="normal" if oferta_total >= demanda_int else "inverse")
    c4.metric("Dependencia externa", f"{pct_import:.1f}%",
              delta="ALTA" if pct_import > 8 else "Moderada",
              delta_color="inverse" if pct_import > 8 else "normal")
    
    # Gráfico de dependencia
    fig_dep = go.Figure()
    fig_dep.add_trace(go.Bar(x=["Colombia", "Perú", "Generación local"],
                             y=[imp_col, imp_pe, gen_local],
                             marker_color=["#7B2D8E", "#D4A373", "#2E86AB"],
                             text=[f"{imp_col} MW", f"{imp_pe} MW", f"{gen_local:,.0f} MW"],
                             textposition="outside"))
    fig_dep.add_hline(y=demanda_int, line_dash="dash", line_color="red",
                      annotation_text=f"Demanda: {demanda_int} MW")
    fig_dep.update_layout(title="Composición de la Oferta (MW)",
                          yaxis_title="MW", height=350)
    st.plotly_chart(fig_dep, use_container_width=True)
    
    if imp_col == 0 and imp_pe == 0:
        _impact_box("Sin importaciones: Ecuador depende 100% de generación local. "
                    "Vulnerable a sequía y fallas térmicas (como en 2024).", "danger")
    elif pct_import > 8:
        _impact_box(f"Dependencia externa alta ({pct_import:.1f}%). "
                    "Riesgo: si Colombia o Perú cortan exportaciones, se activa déficit.", "alert")
    else:
        _impact_box(f"Balance adecuado: importación moderada ({pct_import:.1f}%) + generación local. "
                    "Redundancia con línea 500 kV EC-PE (2029).", "success")

# =============================================================================
# TAB 6: IBR (EÓLICA + SOLAR)
# =============================================================================
def render_tab_ibr(settings):
    ano = settings["ano"]
    st.subheader("🌪️ Energías Renovables No Convencionales (IBR)")

    cap = CAPACIDAD_POR_ANO.get(ano, CAPACIDAD_POR_ANO[2026])
    c1, c2, c3 = st.columns(3)
    c1.metric("Eólica", f"{cap['eolica']} MW")
    c2.metric("Solar", f"{cap['solar']} MW")
    c3.metric("Biomasa+Biogás", f"{cap['biomasa'] + cap['biogas']} MW")

    st.markdown(
        "Ecuador tiene un **potencial sin explotar**: eólico ~2,000 MW, solar ~2,000 MW, "
        "geotérmico ~800 MW (Plan Maestro). Actualmente <5% de la capacidad total."
    )

    # Evolución IBR
    anos_ibr = [2022, 2023, 2024, 2025, 2026]
    eolica = [169, 179, 207, 250, 350]
    solar = [30, 41, 41, 80, 200]
    fig_ibr = go.Figure()
    fig_ibr.add_trace(go.Bar(x=anos_ibr, y=eolica, name="Eólica", marker_color="#6A994E"))
    fig_ibr.add_trace(go.Bar(x=anos_ibr, y=solar, name="Solar", marker_color="#F18F01"))
    fig_ibr.add_vline(x=ano, line_dash="dash", line_color="red")
    fig_ibr.update_layout(barmode="stack", title="Capacidad IBR por Año (MW)",
                          yaxis_title="MW", height=350)
    st.plotly_chart(fig_ibr, use_container_width=True)

    # Proyectos
    st.markdown("#### 🏗️ Proyectos IBR")
    st.dataframe(PROYECTOS_IBR, use_container_width=True, hide_index=True)

    _impact_box("Artículo Nature Energy (2026): agregar VRE a gran escala + hidro flexible "
                "habría mitigado la crisis de 2024 casi completamente. "
                "Decisión: priorizar solar El Aromo (200 MW) y eólica Minas-Chiriboga.", "success")

    # ─── SIMULADOR INTERACTIVO: PENETRACIÓN IBR ───
    st.markdown("---")
    st.markdown("### 🎮 Simulador: Impacto de Penetración IBR")
    st.markdown("Ajuste la capacidad solar y eólica para ver el impacto en la matriz, "
                "la inercia del sistema y el factor de capacidad equivalente.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        solar_sim = st.slider("Solar (MW)", 0, 5000, 200, 50,
                              key="ibr_solar")
    with col2:
        eolica_sim = st.slider("Eólica (MW)", 0, 5000, 350, 50,
                               key="ibr_eolica")
    with col3:
        cf_solar = st.slider("FC Solar (%)", 10, 30, 18, 1,
                             help="Factor de capacidad típico Ecuador: 15-22%",
                             key="ibr_cf_sol")
        cf_eolica = st.slider("FC Eólica (%)", 15, 45, 25, 1,
                              help="Factor de capacidad típico Ecuador: 20-35%",
                              key="ibr_cf_eol")
    
    # Cálculos
    cap_total_sim = 5700 + 3439 + solar_sim + eolica_sim + 80  # hidro+termo+IBR+biomasa
    gen_solar_sim = solar_sim * 8760 * cf_solar / 100 / 1000  # GWh
    gen_eolica_sim = eolica_sim * 8760 * cf_eolica / 100 / 1000
    gen_vre_sim = gen_solar_sim + gen_eolica_sim
    gen_total_sim = 5700 * 8760 * 0.55 / 1000 + 3439 * 8760 * 0.35 / 1000 + gen_vre_sim  # GWh
    pct_vre_sim = gen_vre_sim / gen_total_sim * 100
    
    # Inercia efectiva (cada MW IBR reduce inercia vs sincrónica)
    H_base = 4.2  # segundos
    H_sim = H_base * (1 - pct_vre_sim / 100 * 0.7)  # IBR reduce inercia ~70%
    
    # CO₂ evitado (vs térmica: 0.5 tCO2/MWh)
    co2_evitado = gen_vre_sim * 0.5 / 1000  # MtCO2
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("VRE total", f"{solar_sim + eolica_sim:,} MW",
              delta=f"{(solar_sim+eolica_sim)/cap_total_sim*100:.1f}% cap.")
    c2.metric("Generación VRE", f"{gen_vre_sim:,.0f} GWh/año",
              delta=f"{pct_vre_sim:.1f}% del mix")
    c3.metric("Inercia H", f"{H_sim:.1f} s",
              delta=f"vs {H_base} s base",
              delta_color="normal" if H_sim > 3.0 else "inverse")
    c4.metric("CO₂ evitado", f"{co2_evitado:.2f} MtCO₂/año")
    
    # Gráfico de penetración
    fig_pen = go.Figure()
    labels_pie = ["Hidro", "Térmico", "Solar", "Eólica", "Biomasa"]
    vals_pie = [5700 * 8760 * 0.55 / 1000, 3439 * 8760 * 0.35 / 1000,
                gen_solar_sim, gen_eolica_sim, 80 * 8760 * 0.6 / 1000]
    colors_pie = ["#2E86AB", "#C73E1D", "#F18F01", "#6A994E", "#7B2D8E"]
    fig_pen.add_trace(go.Pie(labels=labels_pie, values=vals_pie, hole=0.45,
                             marker=dict(colors=colors_pie),
                             textinfo="label+percent", textfont=dict(size=10)))
    fig_pen.update_layout(title=f"Matriz de Generación con {solar_sim+eolica_sim:,} MW IBR",
                          height=350, showlegend=False)
    st.plotly_chart(fig_pen, use_container_width=True)
    
    if H_sim < 3.0:
        _impact_box(f"⚠️ ALERTA: inercia reducida a {H_sim:.1f}s (mínimo 3.0s). "
                    f"Con {pct_vre_sim:.0f}% VRE, se requieren servicios de inercia sintética "
                    f"(grid-forming inverters) o BESS para estabilidad.", "danger")
    elif pct_vre_sim > 30:
        _impact_box(f"Alta penetración VRE ({pct_vre_sim:.0f}%): requiere gestión de variabilidad "
                    f"con hidro flexible y almacenamiento. Inercia: {H_sim:.1f}s (aceptable).", "alert")
    else:
        _impact_box(f"Penetración VRE moderada ({pct_vre_sim:.0f}%): compatible con operación actual. "
                    f"CO₂ evitado: {co2_evitado:.2f} MtCO₂/año. Inercia: {H_sim:.1f}s.", "success")

# =============================================================================
# TAB 7: RACIONAMIENTO / CRISIS
# =============================================================================
def render_tab_racionamento(settings):
    ano = settings["ano"]
    st.subheader("🚧 Racionamiento y Crisis Energética 2024")

    st.markdown(
        "En **septiembre-diciembre 2024**, Ecuador vivió su peor crisis energética en décadas: "
        "racionamiento de hasta **14 horas diarias** causado por sequía severa, "
        "infraestructura térmica insuficiente y corte de importaciones desde Colombia."
    )

    # KPIs de la crisis
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Déficit máximo", f"{CRISIS_2024['deficit_mw']:,} MW")
    c2.metric("Racionamiento máx.", f"{CRISIS_2024['racionamiento_max']}")
    c3.metric("Hidro mínimo", f"{CRISIS_2024['hidro_min_pct']}%")
    c4.metric("Térmica disponible", f"{CRISIS_2024['termica_disponible']} / {CRISIS_2024['termica_instalada']} MW")

    # Timeline de eventos
    st.markdown("#### 📅 Cronología de la Crisis")
    eventos = CRISIS_2024["eventos"]
    for ev in eventos:
        color = "🔴" if "racionamiento" in ev["evento"].lower() or "crítica" in ev["detalle"].lower() else "🟡" if "extendido" in ev["evento"].lower() or "cortes" in ev["detalle"].lower() else "🟢"
        st.markdown(f"**{color} {ev['fecha']}** — {ev['evento']}  \n  *{ev['detalle']}*")

    _impact_box("Causa raíz: 72% dependencia hidro + 3,439 MW térmicos pero solo 853 MW operativos + "
                "Colombia cortó exportaciones. Decisión: diversificar + mantener reserva térmica + "
                "construir interconexión 500 kV con Perú.", "danger")

    # Comparación hidro normal vs crisis
    st.markdown("#### 📊 Generación Hidro: Normal vs Crisis")
    meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    hidro_normal = [88, 90, 89, 85, 82, 78, 75, 72, 70, 68, 72, 85]
    hidro_2024 = [85, 82, 80, 75, 72, 65, 58, 52, 49, 50, 55, 65]

    fig_crisis = go.Figure()
    fig_crisis.add_trace(go.Scatter(x=meses, y=hidro_normal, mode="lines+markers",
                                    name="Normal (2025)", line=dict(color="#2E86AB", width=3)))
    fig_crisis.add_trace(go.Scatter(x=meses, y=hidro_2024, mode="lines+markers",
                                    name="Crisis (2024)", line=dict(color="#C73E1D", width=3)))
    fig_crisis.add_hline(y=60, line_dash="dash", line_color="orange", annotation_text="Umbral alerta")
    fig_crisis.update_layout(title="Participación Hidroeléctrica Mensual (%)",
                             yaxis_title="%", height=350)
    st.plotly_chart(fig_crisis, use_container_width=True)

    # SIMULADOR ENOS
    st.markdown("---")
    st.markdown("#### 🌡️ Simulador de Impacto ENOS (El Niño/La Niña)")
    st.markdown("Ajuste los parámetros para simular el impacto de diferentes escenarios climáticos:")

    col1, col2, col3 = st.columns(3)
    with col1:
        enos = st.selectbox("Tipo ENOS",
                            ["el_nino_fuerte", "el_nino_moderado", "neutral", "la_nina"],
                            format_func=lambda x: {"el_nino_fuerte": "🔴 El Niño fuerte",
                                                    "el_nino_moderado": "🟠 El Niño moderado",
                                                    "neutral": "⚪ Neutral",
                                                    "la_nina": "🔵 La Niña"}.get(x, x))
    with col2:
        demanda = st.slider("Demanda (MW)", 3500, 6500, 5100, 100)
    with col3:
        termo = st.slider("Térmica disponible (MW)", 500, 4500, 2800, 100)

    result = simulate_enos_drought(enos, 72, demanda, termo)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gen. Hidro", f"{result['gen_hidro_mw']:,.0f} MW",
              delta=f"Factor: {result['factor_hidro']:.0%}")
    c2.metric("Gen. Total", f"{result['gen_total_mw']:,.0f} MW")
    if result["deficit_mw"] > 0:
        c3.metric("⚠️ Déficit", f"{result['deficit_mw']:,.0f} MW",
                  delta=f"Riesgo: {result['riesgo']}", delta_color="inverse")
        c4.metric("Horas de corte", f"{result['horas_corte']:.1f} h/día")
    else:
        c3.metric("✅ Superávit", f"{result['superavit_mw']:,.0f} MW")
        c4.metric("Mazar nivel", f"{result['mazar_nivel_pct']}%")

    if result["deficit_mw"] > 0:
        msg = f"DÉFICIT de {result['deficit_mw']:,.0f} MW → racionamiento {result['horas_corte']:.1f}h/día"
    else:
        msg = f"Superávit de {result['superavit_mw']:,.0f} MW"
    _impact_box(f"Simulación {enos.replace('_',' ').title()}: {msg}. Mazar proyectado al {result['mazar_nivel_pct']}%.",
        "danger" if result["deficit_mw"] > 200 else "alert" if result["deficit_mw"] > 0 else "success"
    )

# =============================================================================
# TAB 8: SINCRÓFASORES / WAMS
# =============================================================================
def render_tab_wams(settings):
    st.subheader("📡 Red de Sincrofasores (PMU) — WAMS Ecuador")

    c1, c2, c3 = st.columns(3)
    c1.metric("PMUs instalados", PMU_NETWORK["PMUs instalados"])
    c2.metric("PMUs planificados (2027)", PMU_NETWORK["PMUs planificados (2027)"])
    c3.metric("Cobertura", PMU_NETWORK["Cobertura_actual"])

    st.markdown("#### 📍 Estaciones PMU")
    st.dataframe(pd.DataFrame(PMU_NETWORK["estaciones"]),
                 use_container_width=True, hide_index=True)

    st.markdown("#### 🧮 Algoritmos de Analítica WAMS")
    st.dataframe(pd.DataFrame(ALGORITMOS_WAMS), use_container_width=True, hide_index=True)

    # Modos de oscilación
    st.markdown("#### 📊 Modos de Oscilación Electromecánica (SNI)")
    st.dataframe(MODOS_OSCILACION, use_container_width=True, hide_index=True)

    fig_modos = go.Figure(go.Scatter(
        x=MODOS_OSCILACION["frecuencia_hz"], y=MODOS_OSCILACION["amortiguamiento"],
        mode="markers+text", text=MODOS_OSCILACION["modo"],
        marker=dict(size=18, color=MODOS_OSCILACION["amortiguamiento"],
                    colorscale="RdYlGn", colorbar=dict(title="ζ"),
                    line=dict(width=2, color="#333"))))
    fig_modos.update_layout(title="Diagrama de Modos (f vs ζ)",
                            xaxis_title="Frecuencia (Hz)", yaxis_title="Amortiguamiento (ζ)",
                            height=400)
    st.plotly_chart(fig_modos, use_container_width=True)

    _impact_box("Modo inter-área EC-CO (0.35 Hz, ζ=3%): alto riesgo en importaciones máximas. "
                "Decisión: PSS adaptativos y monitoreo WAMS en tiempo real.", "alert")

    # ─── SIMULADOR INTERACTIVO: COBERTURA PMU Y OSCILACIONES ───
    st.markdown("---")
    st.markdown("### 🎮 Simulador: Cobertura PMU y Detección de Oscilaciones")
    st.markdown("Ajuste la cantidad de PMUs y el umbral de amortiguamiento para evaluar "
                "la capacidad de monitoreo del SNI.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        pmus_sim = st.slider("PMUs instalados", 5, 60, 23, 1,
                             help="Actualmente: 23 · Plan 2027: 45",
                             key="wams_pmus")
    with col2:
        zeta_min = st.slider("Umbral ζ mínimo (%)", 1, 10, 5, 1,
                             help="Modos con ζ < umbral requieren PSS",
                             key="wams_zeta")
    with col3:
        import_col_mw = st.slider("Importación Colombia (MW)", 0, 525, 200, 25,
                                  help="A mayor importación, mayor riesgo inter-área",
                                  key="wams_imp")
    
    # Cálculos
    cobertura_sim = min(100, pmus_sim / 45 * 85)  # 45 PMUs = 85% cobertura
    modos_criticos = len(MODOS_OSCILACION[MODOS_OSCILACION["amortiguamiento"] < zeta_min])
    riesgo_inter = "ALTO" if import_col_mw > 350 else "MEDIO" if import_col_mw > 150 else "BAJO"
    
    # El modo EC-CO se degrada con más importación
    zeta_ec_co = max(1, 3.0 - (import_col_mw - 200) / 200)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cobertura PMU", f"{cobertura_sim:.0f}%",
              delta=f"{pmus_sim} PMUs")
    c2.metric("Modos críticos", f"{modos_criticos}",
              delta=f"ζ < {zeta_min}%",
              delta_color="inverse" if modos_criticos > 2 else "normal")
    c3.metric("Riesgo inter-área", riesgo_inter,
              delta=f"ζ EC-CO: {zeta_ec_co:.1f}%")
    c4.metric("Latencia detección", f"{max(50, 500 - pmus_sim*8)} ms",
              help="Más PMUs = menor latencia de detección")
    
    # Gráfico de modos con umbral interactivo
    fig_modos_int = go.Figure(go.Scatter(
        x=MODOS_OSCILACION["frecuencia_hz"], y=MODOS_OSCILACION["amortiguamiento"],
        mode="markers+text", text=MODOS_OSCILACION["modo"],
        marker=dict(size=18, color=MODOS_OSCILACION["amortiguamiento"],
                    colorscale="RdYlGn", colorbar=dict(title="ζ %"),
                    line=dict(width=2, color="#333"))))
    fig_modos_int.add_hline(y=zeta_min, line_dash="dash", line_color="red",
                            annotation_text=f"Umbral ζ={zeta_min}%")
    fig_modos_int.update_layout(title=f"Modos de Oscilación (umbral: {zeta_min}%)",
                                xaxis_title="Frecuencia (Hz)", yaxis_title="Amortiguamiento (ζ %)",
                                height=350)
    st.plotly_chart(fig_modos_int, use_container_width=True)
    
    if modos_criticos > 2:
        _impact_box(f"⚠️ {modos_criticos} modos por debajo del umbral ζ={zeta_min}%. "
                    f"Modo EC-CO degradado a ζ={zeta_ec_co:.1f}% con {import_col_mw} MW de importación. "
                    f"Decisión: instalar PSS adaptativos y aumentar cobertura PMU.", "danger")
    elif cobertura_sim < 60:
        _impact_box(f"Cobertura PMU insuficiente ({cobertura_sim:.0f}%). "
                    f"Con solo {pmus_sim} PMUs no se puede monitorear todo el SNI.", "alert")
    else:
        _impact_box(f"Cobertura PMU: {cobertura_sim:.0f}%. {modos_criticos} modos críticos. "
                    f"Sistema monitoreable con WAMS.", "success")

# =============================================================================
# TAB 9: ESTABILIDAD (SIMULADORES)
# =============================================================================
def render_tab_estabilidad(settings):
    ano = settings["ano"]
    st.subheader("🧠 Estabilidad del SNI — Simuladores Interactivos")

    # Mapa de inercia
    st.markdown("#### 🗺️ Mapa de Inercia por Zona")
    zonas = list(INERCIA_SNI.keys())
    h_vals = [INERCIA_SNI[z]["H_sistema_s"] for z in zonas]
    h_min = [INERCIA_SNI[z]["H_minimo_s"] for z in zonas]
    ibr = [INERCIA_SNI[z]["IBR_pct_2026"] for z in zonas]

    col1, col2 = st.columns(2)
    with col1:
        fig_in = go.Figure(go.Bar(
            x=zonas, y=h_vals, name="H efectiva (s)",
            marker_color=["#C73E1D" if h < m else "#6A994E" for h, m in zip(h_vals, h_min)]))
        fig_in.add_trace(go.Scatter(x=zonas, y=h_min, mode="markers",
                                    name="H mínimo", marker=dict(color="red", size=12, symbol="x")))
        fig_in.update_layout(title="Constante de Inercia por Zona (s)",
                             yaxis_title="H (s)", height=350)
        st.plotly_chart(fig_in, use_container_width=True)
    with col2:
        st.dataframe(pd.DataFrame([
            {"Zona": z, "H (s)": INERCIA_SNI[z]["H_sistema_s"],
             "H mín (s)": INERCIA_SNI[z]["H_minimo_s"],
             "Capacidad (MW)": INERCIA_SNI[z]["capacidad_mw"],
             "Carga (MW)": INERCIA_SNI[z]["carga_mw"],
             "IBR %": INERCIA_SNI[z]["IBR_pct_2026"]}
            for z in zonas
        ]), use_container_width=True, hide_index=True)

    # Inercia histórica
    st.markdown("#### 📉 Declive Histórico de Inercia (2015-2026)")
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Scatter(x=INERCIA_HISTORICA["ano"], y=INERCIA_HISTORICA["H_sistema_s"],
                                  mode="lines+markers", name="H sistema (s)",
                                  line=dict(color="#2E86AB", width=3)))
    fig_hist.add_trace(go.Scatter(x=INERCIA_HISTORICA["ano"], y=INERCIA_HISTORICA["IBR_pct"],
                                  mode="lines+markers", name="IBR %", yaxis="y2",
                                  line=dict(color="#F18F01", width=2, dash="dash")))
    fig_hist.update_layout(
        title="Inercia del SNI vs Penetración IBR",
        yaxis=dict(title="H (s)"), yaxis2=dict(title="IBR %", overlaying="y", side="right"),
        height=350)
    st.plotly_chart(fig_hist, use_container_width=True)

    # ======== SIMULADOR 1: SUBFRECUENCIA ========
    st.markdown("---")
    st.markdown("### ⚡ Simulador 1: Subfrecuencia")
    col1, col2 = st.columns(2)
    with col1:
        perdida = st.slider("Pérdida de generación (MW)", 50, 1500, 500, 50,
                            help="Ej: salida de CCS (1,500 MW) o Paute-Molino (1,100 MW)")
        h_sim = st.slider("Constante de inercia H (s)", 2.0, 6.0, 4.2, 0.1)
    with col2:
        carga = st.slider("Carga total (MW)", 3000, 6000, 5100, 100)
        droop = st.slider("Droop (%)", 3, 8, 5) / 100

    df_sub, met_sub = simulate_frequency_event(perdida, h_sim, carga, droop)

    fig_sub = go.Figure(go.Scatter(x=df_sub["t_s"], y=df_sub["f_hz"], mode="lines",
                                   line=dict(color="#C73E1D", width=2)))
    fig_sub.add_hline(y=59.5, line_dash="dash", line_color="orange", annotation_text="UFLS 1")
    fig_sub.add_hline(y=59.3, line_dash="dash", line_color="red", annotation_text="ERAC")
    fig_sub.update_layout(title=f"Respuesta de Frecuencia — Pérdida {perdida} MW",
                          xaxis_title="Tiempo (s)", yaxis_title="Frecuencia (Hz)",
                          height=350, yaxis_range=[58.5, 60.5])
    st.plotly_chart(fig_sub, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Nadir", f"{met_sub['extreme_hz']} Hz")
    c2.metric("ROCoF máx", f"{met_sub['rocof_max_hzs']} Hz/s")
    c3.metric("UFLS activado", "Sí" if met_sub["ufls_triggered"] else "No")
    _impact_box(f"Subfrecuencia: nadir {met_sub['extreme_hz']} Hz, ROCoF {met_sub['rocof_max_hzs']} Hz/s. "
                f"{'ALERTA: UFLS activado — considerar reserva rodante adicional.' if met_sub['ufls_triggered'] else 'OK: sistema estable.'}",
                "danger" if met_sub["ufls_triggered"] else "success")

    # ======== SIMULADOR 2: SOBREFRECUENCIA ========
    st.markdown("---")
    st.markdown("### ⚡ Simulador 2: Sobrefrecuencia")
    col1, col2 = st.columns(2)
    with col1:
        exceso = st.slider("Exceso de generación (MW)", 100, 1500, 300, 50,
                           help="Ej: rechazo de carga por desconexión industrial")
        h_sim2 = st.slider("H (s) [sobrefrec]", 2.0, 6.0, 4.2, 0.1, key="h2")
    with col2:
        carga2 = st.slider("Carga total (MW) [sobrefrec]", 2000, 5000, 3500, 100, key="c2")

    df_over, met_over = simulate_frequency_event(-exceso, h_sim2, carga2, 0.05)

    fig_over = go.Figure(go.Scatter(x=df_over["t_s"], y=df_over["f_hz"], mode="lines",
                                    line=dict(color="#F18F01", width=2)))
    fig_over.add_hline(y=60.5, line_dash="dash", line_color="red", annotation_text="Límite")
    fig_over.update_layout(title=f"Sobrefrecuencia — Exceso {exceso} MW",
                           xaxis_title="Tiempo (s)", yaxis_title="Frecuencia (Hz)",
                           height=300, yaxis_range=[59.5, 61.5])
    st.plotly_chart(fig_over, use_container_width=True)
    c1, c2 = st.columns(2)
    c1.metric("Pico", f"{met_over['extreme_hz']} Hz")
    c2.metric("ROCoF", f"{met_over['rocof_max_hzs']} Hz/s")
    _impact_box(f"Sobrefrecuencia: pico {met_over['extreme_hz']} Hz. "
                f"{'ALERTA: riesgo de disparo de generación.' if met_over['extreme_hz'] > 60.5 else 'OK.'}",
                "danger" if met_over["extreme_hz"] > 60.5 else "success")

    # ======== SIMULADOR 3: ESTABILIDAD DE TENSIÓN ========
    st.markdown("---")
    st.markdown("### 🔌 Simulador 3: Estabilidad de Tensión (P-V)")
    st.caption("Metodología Torres Contreras: margen de carga y áreas de control de tensión.")
    col1, col2 = st.columns(2)
    with col1:
        carga_pct = st.slider("Carga del sistema (%)", 50, 150, 85, 5)
        gen_disp = st.slider("Generación disponible (MW)", 3000, 7000, 5500, 100)
    with col2:
        v_ini = st.slider("Tensión inicial (p.u.)", 0.90, 1.10, 1.0, 0.01)

    res_v = simulate_voltage_stability(carga_pct, gen_disp, v_ini)

    # Curva P-V
    P_curve = res_v["P_curve"]
    V_upper = res_v["V_upper"]
    fig_pv = go.Figure()
    fig_pv.add_trace(go.Scatter(x=P_curve, y=V_upper, mode="lines",
                                name="Curva superior", line=dict(color="#2E86AB", width=3)))
    fig_pv.add_trace(go.Scatter(x=[res_v["P_carga_mw"]], y=[res_v["V_operacion_pu"]],
                                mode="markers", name="Punto operación",
                                marker=dict(color="red", size=14)))
    fig_pv.add_vline(x=res_v["P_max_mw"], line_dash="dash", line_color="red",
                     annotation_text=f"Pmax={res_v['P_max_mw']:.0f}")
    fig_pv.update_layout(title=f"Curva P-V — Margen: {res_v['margen_pct']}%",
                         xaxis_title="Potencia (MW)", yaxis_title="Tensión (p.u.)",
                         height=350)
    st.plotly_chart(fig_pv, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Margen de carga", f"{res_v['margen_pct']}%")
    c2.metric("V operación", f"{res_v['V_operacion_pu']} p.u.")
    c3.metric("Riesgo", res_v["riesgo"])
    _impact_box(f"Margen de tensión: {res_v['margen_pct']}%. Riesgo: {res_v['riesgo']}. "
                f"{'CRÍTICO: colapso de tensión posible.' if res_v['colapso'] else 'Sistema estable.'}",
                "danger" if res_v["colapso"] else "success")

    # ======== SIMULADOR 4: TNEP AC (Torres Contreras) ========
    st.markdown("---")
    st.markdown("### 🔧 Simulador 4: Planificación de Transmisión (TNEP AC)")
    st.caption("Metodología Torres Contreras: modelo AC completo con compensación reactiva.")
    col1, col2 = st.columns(2)
    with col1:
        nodos = st.slider("Nodos del sistema", 10, 100, 45, 5)
        lineas = st.slider("Líneas candidatas", 2, 20, 8)
    with col2:
        ibr_pen = st.slider("Penetración IBR (%)", 0, 50, 7, 1)
        bess = st.slider("Almacenamiento BESS (MW)", 0, 500, 50, 25)

    res_tnep = simulate_tnep_ac(nodos, lineas, ibr_pen, bess)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Congestiones (antes→desp.)",
              f"{res_tnep['congestiones_iniciales']}→{res_tnep['congestiones_post']}")
    c2.metric("Pérdidas (%)",
              f"{res_tnep['perdidas_inicial_pct']}→{res_tnep['perdidas_post_pct']}%")
    c3.metric("Líneas necesarias", res_tnep["lineas_necesarias"])
    c4.metric("Inversión total", f"USD {res_tnep['inversion_total_musd']:.0f}M")

    fig_tnep = go.Figure()
    fig_tnep.add_trace(go.Bar(x=["Inicial", "Post-expansión"],
                              y=[res_tnep["congestiones_iniciales"], res_tnep["congestiones_post"]],
                              name="Congestiones", marker_color=["#C73E1D", "#6A994E"]))
    fig_tnep.update_layout(title="Reducción de Congestiones con Expansión",
                           yaxis_title="Nº congestiones", height=300)
    st.plotly_chart(fig_tnep, use_container_width=True)

    _impact_box(f"TNEP AC: {res_tnep['lineas_necesarias']} líneas necesarias, "
                f"compensación reactiva {res_tnep['comp_reactiva_mvar']} MVAr, "
                f"inversión total USD {res_tnep['inversion_total_musd']:.0f}M. "
                f"Reducción de congestiones: {res_tnep['beneficio_congestion_pct']}%.",
                "info")

# =============================================================================
# TAB 10: CLASIFICACIÓN DE EVENTOS (ML)
# =============================================================================
def render_tab_eventos(settings):
    st.subheader("🔬 Clasificación de Eventos — Machine Learning y TKEO")

    st.markdown(
        "Detección y clasificación automática de eventos en el SNI usando "
        "señales PMU y algoritmos de inteligencia computacional."
    )

    # Métodos ML
    st.markdown("#### 🧮 Métodos de Clasificación")
    metodos = pd.DataFrame([
        {"Método": "TKEO (Teager-Kaiser)", "Tipo": "Detección", "Acuracia": "94%",
         "Aplicación": "Eventos transitorios", "Latencia": "<10 ms"},
        {"Método": "Prony + SVM", "Tipo": "Clasificación", "Acuracia": "96%",
         "Aplicación": "Modos oscilatorios", "Latencia": "<500 ms"},
        {"Método": "1D-ConvLSTM", "Tipo": "Deep Learning", "Acuracia": "97%",
         "Aplicación": "SSO en multi-energía", "Latencia": "<200 ms"},
        {"Método": "Koopman/EDMD", "Tipo": "Estimación", "Acuracia": "93%",
         "Aplicación": "Estado dinámico", "Latencia": "<100 ms"},
        {"Método": "MVMO + ANN", "Tipo": "Heurístico", "Acuracia": "91%",
         "Aplicación": "Equivalentes dinámicos", "Latencia": "<1 s"},
        {"Método": "Neuro-Fuzzy", "Tipo": "Predicción", "Acuracia": "89%",
         "Aplicación": "Margen de carga", "Latencia": "<500 ms"},
    ])
    st.dataframe(metodos, use_container_width=True, hide_index=True)

    # Eventos históricos
    st.markdown("#### 📋 Eventos Registrados en el SNI")
    eventos = pd.DataFrame([
        {"Fecha": "2024-09-27", "Tipo": "Déficit generación", "Magnitud": "1,080 MW",
         "Duración": "Meses", "Impacto": "Racionamiento 14h"},
        {"Fecha": "2024-04-01", "Tipo": "Corte importación CO", "Magnitud": "420 MW",
         "Duración": "Semanas", "Impacto": "Racionamiento adicional"},
        {"Fecha": "2023-10-26", "Tipo": "Fallo Paute-Molino", "Magnitud": "500 MW",
         "Duración": "Horas", "Impacto": "Déficit + cortes 3h"},
        {"Fecha": "2022-07-15", "Tipo": "Oscilación EC-CO", "Magnitud": "0.35 Hz",
         "Duración": "30 s", "Impacto": "Alerta interconexión"},
        {"Fecha": "2025-05-07", "Tipo": "Récord demanda", "Magnitud": "5,110 MW",
         "Duración": "Pico", "Impacto": "Sin incidentes"},
    ])
    st.dataframe(eventos, use_container_width=True, hide_index=True)

    # Demo TKEO
    st.markdown("#### 📊 Demo: Detección con TKEO")
    np.random.seed(42)
    t = np.linspace(0, 2, 500)
    señal = np.sin(2*np.pi*60*t) + 0.3*np.sin(2*np.pi*180*t)
    # Evento en t=1.0
    señal[250:] += 0.5 * np.exp(-5*(t[250:]-1.0))
    # TKEO: y[n]² - y[n-1]·y[n+1]
    tkeo = np.abs(señal[1:-1]**2 - señal[:-2]*señal[2:])

    fig_tkeo = go.Figure()
    fig_tkeo.add_trace(go.Scatter(x=t[1:-1], y=tkeo, mode="lines",
                                  name="TKEO", line=dict(color="#C73E1D")))
    fig_tkeo.add_vline(x=1.0, line_dash="dash", line_color="red", annotation_text="Evento")
    fig_tkeo.update_layout(title="Detección de Evento con TKEO",
                           xaxis_title="Tiempo (s)", yaxis_title="Energía TKEO",
                           height=300)
    st.plotly_chart(fig_tkeo, use_container_width=True)

    _impact_box("TKEO detecta eventos transitorios en <10 ms. Ideal para alertas tempranas "
                "en el SNI ecuatoriano donde la dependencia hidro crea transitorios rápidos.", "info")

    # ─── SIMULADOR INTERACTIVO: PARÁMETROS TKEO ───
    st.markdown("---")
    st.markdown("### 🎮 Simulador: Ajuste de Parámetros TKEO")
    st.markdown("Modifique la magnitud del evento, la frecuencia de la señal y el ruido "
                "para ver cómo responde el algoritmo TKEO.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        mag_evento = st.slider("Magnitud del evento", 0.1, 2.0, 0.5, 0.1,
                               help="Amplitud de la perturbación",
                               key="tkeo_mag")
    with col2:
        freq_base = st.slider("Frecuencia fundamental (Hz)", 30, 120, 60, 10,
                              help="50 Hz (Europa) o 60 Hz (América)",
                              key="tkeo_freq")
    with col3:
        ruido = st.slider("Nivel de ruido", 0.0, 0.5, 0.05, 0.05,
                          help="Ruido gaussiano en la señal",
                          key="tkeo_ruido")
    
    # Generar señal con parámetros
    np.random.seed(42)
    t_sim = np.linspace(0, 2, 500)
    señal_sim = np.sin(2*np.pi*freq_base*t_sim) + 0.3*np.sin(2*np.pi*freq_base*3*t_sim)
    señal_sim[250:] += mag_evento * np.exp(-5*(t_sim[250:]-1.0))
    señal_sim += ruido * np.random.randn(len(t_sim))
    # TKEO
    tkeo_sim = np.abs(señal_sim[1:-1]**2 - señal_sim[:-2]*señal_sim[2:])
    
    # Calcular SNR y detectabilidad
    energia_señal = np.mean(tkeo_sim[250:]**2)
    energia_ruido = np.mean(tkeo_sim[:200]**2)
    snr = 10 * np.log10(energia_señal / max(energia_ruido, 1e-10))
    detectable = snr > 6  # SNR > 6 dB = detectable
    
    fig_tkeo_sim = go.Figure()
    fig_tkeo_sim.add_trace(go.Scatter(x=t_sim[1:-1], y=tkeo_sim, mode="lines",
                                      name="TKEO", line=dict(color="#C73E1D", width=1.5)))
    fig_tkeo_sim.add_vline(x=1.0, line_dash="dash", line_color="red", annotation_text="Evento")
    fig_tkeo_sim.update_layout(title=f"TKEO — Magnitud={mag_evento}, f={freq_base}Hz, ruido={ruido}",
                               xaxis_title="Tiempo (s)", yaxis_title="Energía TKEO",
                               height=300)
    st.plotly_chart(fig_tkeo_sim, use_container_width=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("SNR", f"{snr:.1f} dB",
              delta="Detectable" if detectable else "No detectable",
              delta_color="normal" if detectable else "inverse")
    c2.metric("Latencia estimada", f"{max(2, 10 - snr*0.5):.0f} ms")
    c3.metric("Pico TKEO", f"{np.max(tkeo_sim[240:]):.3f}")
    
    if detectable:
        _impact_box(f"✅ Evento detectable con SNR={snr:.1f} dB. "
                    f"Latencia estimada: {max(2, 10-snr*0.5):.0f} ms.", "success")
    else:
        _impact_box(f"⚠️ SNR insuficiente ({snr:.1f} dB < 6 dB). "
                    f"Evento no detectable con estos parámetros. "
                    f"Aumente magnitud o reduzca ruido.", "danger")

# =============================================================================
# TAB 11: MERCADO Y PRECIOS
# =============================================================================
def render_tab_mercado(settings):
    ano = settings["ano"]
    st.subheader("💰 Mercado Eléctrico — Precios y Tarifas")

    precios = PRECIOS_HISTORICOS[PRECIOS_HISTORICOS["ano"]==ano]
    if len(precios) > 0:
        p = precios.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"Precio promedio ({ano})", f"${p['precio_promedio_usd_mwh']}/MWh")
        c2.metric("Tarifa residencial", f"${p['tarifa_residencial']}/kWh")
        c3.metric("Tarifa comercial", f"${p['tarifa_comercial']}/kWh")
        c4.metric("Tarifa industrial", f"${p['tarifa_industrial']}/kWh")

    # Evolución de precios
    st.markdown("#### 📊 Evolución de Precios")
    fig_p = go.Figure()
    fig_p.add_trace(go.Scatter(x=PRECIOS_HISTORICOS["ano"],
                               y=PRECIOS_HISTORICOS["precio_promedio_usd_mwh"],
                               mode="lines+markers", name="Precio spot",
                               line=dict(color="#003087", width=3)))
    fig_p.add_vline(x=ano, line_dash="dash", line_color="red")
    fig_p.add_annotation(x=2024, y=78, text="Crisis 2024", showarrow=True,
                         arrowhead=2, ax=30, ay=-30)
    fig_p.update_layout(title="Precio Promedio del Mercado (USD/MWh)",
                        yaxis_title="USD/MWh", height=350)
    st.plotly_chart(fig_p, use_container_width=True)

    _impact_box(f"Precio promedio {ano}: ${precios.iloc[0]['precio_promedio_usd_mwh']}/MWh. "
                f"En 2024 subió a $78/MWh por crisis. "
                f"Decisión: contratos de largo plazo con renovables reducen volatilidad.", "info")

    # Tarifas por distribuidora
    st.markdown("#### 🏢 Empresas Distribuidoras")
    st.dataframe(DISTRIBUIDORAS, use_container_width=True, hide_index=True)

    # ─── SIMULADOR INTERACTIVO: ESCENARIO DE PRECIOS ───
    st.markdown("---")
    st.markdown("### 🎮 Simulador: Impacto de Precio en Factura y Déficit")
    st.markdown("Ajuste el precio de mercado y la tarifa regulada para ver el impacto "
                "en la factura mensual del usuario y el déficit tarifario del sistema.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        precio_sim = st.slider("Precio mercado (USD/MWh)", 20, 120, 45, 5,
                               key="merc_precio")
    with col2:
        tarifa_reg = st.slider("Tarifa regulada (c$/kWh)", 5.0, 20.0, 10.0, 0.5,
                               help="Tarifa promedio actual: ~10 c$/kWh",
                               key="merc_tarifa")
    with col3:
        consumo_mes = st.slider("Consumo mensual hogar (kWh)", 50, 500, 180, 10,
                                help="Consumo promedio Ecuador: ~180 kWh/mes",
                                key="merc_consumo")
    
    # Cálculos
    costo_gen = precio_sim  # USD/MWh
    tarifa_costo = costo_gen * 100 / 1000  # c$/kWh solo generación
    tarifa_total = tarifa_costo * 2.1  # incluye T+D+comercialización (~2.1x)
    factura_sim = consumo_mes * tarifa_reg / 100  # USD
    factura_real = consumo_mes * tarifa_total / 100  # USD
    deficit_kwh = tarifa_total - tarifa_reg  # c$/kWh de subsidio
    deficit_anual = deficit_kwh * 22000 * 1e6 / 100 / 1e6  # MUSD (22 TWh/año Ecuador)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Factura mensual", f"${factura_sim:.2f}",
              delta=f"Costo real: ${factura_real:.2f}")
    c2.metric("Costo real", f"{tarifa_total:.1f} c$/kWh",
              delta=f"vs tarifa: {tarifa_reg} c$/kWh")
    c3.metric("Subsidio/kWh", f"{max(0, deficit_kwh):.1f} c$/kWh",
              delta="Déficit" if deficit_kwh > 0 else "Superávit",
              delta_color="inverse" if deficit_kwh > 0 else "normal")
    c4.metric("Déficit anual", f"USD {max(0, deficit_anual):.0f}M")
    
    # Gráfico comparativo
    fig_tarifa = go.Figure()
    fig_tarifa.add_trace(go.Bar(x=["Costo real", "Tarifa regulada", "Mercado spot"],
                                y=[tarifa_total, tarifa_reg, precio_sim/10],
                                marker_color=["#C73E1D", "#2E86AB", "#F18F01"],
                                text=[f"{tarifa_total:.1f}", f"{tarifa_reg:.1f}", f"{precio_sim/10:.1f}"],
                                textposition="outside"))
    fig_tarifa.update_layout(title="Comparación de Precios (c$/kWh)",
                             yaxis_title="c$/kWh", height=350)
    st.plotly_chart(fig_tarifa, use_container_width=True)
    
    if deficit_kwh > 3:
        _impact_box(f"⚠️ Déficit tarifario severo: {deficit_kwh:.1f} c$/kWh. "
                    f"El sistema pierde USD {deficit_anual:.0f}M/año. "
                    f"Decisión: ajustar tarifas gradualmente o subsidiar con presupuesto.", "danger")
    elif deficit_kwh > 0:
        _impact_box(f"Déficit tarifario moderado: {deficit_kwh:.1f} c$/kWh (~USD {deficit_anual:.0f}M/año). "
                    f"Sostenible con subsidio estatal.", "alert")
    else:
        _impact_box(f"✅ Tarifa cubre costos. Superávit de {-deficit_kwh:.1f} c$/kWh.", "success")

# =============================================================================
# TAB 12: EMISIONES CO₂
# =============================================================================
def render_tab_emissoes(settings):
    ano = settings["ano"]
    st.subheader("🏭 Emisiones de CO₂ — Sector Eléctrico del Ecuador")

    em = EMISIONES_HISTORICA[EMISIONES_HISTORICA["ano"]==ano]
    if len(em) > 0:
        e = em.iloc[0]
        st.markdown(
            f"En **{ano}**: intensidad de **{e['intensidad_gkwh']} gCO₂/kWh** "
            f"con **{e['hidro_pct']}%** de generación hidroeléctrica."
        )

    c1, c2, c3 = st.columns(3)
    c1.metric(f"Intensidad ({ano})", f"{e['intensidad_gkwh']} gCO₂/kWh",
              delta="vs. 450 media global", delta_color="normal")
    c2.metric(f"Emisiones totales ({ano})", f"{e['co2_mtcO2']} MtCO₂")
    c3.metric(f"Hidro ({ano})", f"{e['hidro_pct']}%")

    col1, col2 = st.columns(2)
    with col1:
        # Emisiones por año
        fig_em = go.Figure(go.Bar(
            x=EMISIONES_HISTORICA["ano"], y=EMISIONES_HISTORICA["co2_mtcO2"],
            marker_color=["#C73E1D" if v > 5 else "#6A994E" for v in EMISIONES_HISTORICA["co2_mtcO2"]]))
        fig_em.add_vline(x=ano, line_dash="dash", line_color="red")
        fig_em.update_layout(title="Emisiones Totales (MtCO₂)", yaxis_title="MtCO₂", height=350)
        st.plotly_chart(fig_em, use_container_width=True)

    with col2:
        # Intensidad por año
        fig_int = go.Figure(go.Scatter(
            x=EMISIONES_HISTORICA["ano"], y=EMISIONES_HISTORICA["intensidad_gkwh"],
            mode="lines+markers", line=dict(color="#C73E1D", width=3)))
        fig_int.add_hline(y=450, line_dash="dot", line_color="gray", annotation_text="Media global")
        fig_int.add_vline(x=ano, line_dash="dash", line_color="red")
        fig_int.update_layout(title="Intensidad de Carbono (gCO₂/kWh)",
                              yaxis_title="gCO₂/kWh", height=350)
        st.plotly_chart(fig_int, use_container_width=True)

    # Comparación internacional
    st.markdown("#### 🌍 Comparación Internacional")
    comp = pd.DataFrame([
        {"País": "Noruega", "gCO₂/kWh": 17}, {"País": "Ecuador", "gCO₂/kWh": int(e['intensidad_gkwh'])},
        {"País": "Brasil", "gCO₂/kWh": 72}, {"País": "Colombia", "gCO₂/kWh": 140},
        {"País": "Perú", "gCO₂/kWh": 260}, {"País": "México", "gCO₂/kWh": 400},
        {"País": "Media Global", "gCO₂/kWh": 450}, {"País": "China", "gCO₂/kWh": 530},
    ]).sort_values("gCO₂/kWh")
    fig_comp = go.Figure(go.Bar(
        x=comp["País"], y=comp["gCO₂/kWh"],
        marker_color=["#FFD100" if v == int(e['intensidad_gkwh']) else
                      "#6A994E" if v < 100 else "#F18F01" if v < 300 else "#C73E1D"
                      for v in comp["gCO₂/kWh"]]))
    fig_comp.update_layout(title="Intensidad de Carbono — Comparación",
                           yaxis_title="gCO₂/kWh", height=350)
    st.plotly_chart(fig_comp, use_container_width=True)

    # Factor de emisión
    st.markdown("#### 📋 Datos ARCONEL — Factor de Emisión del SNI")
    st.dataframe(EMISIONES_HISTORICA, use_container_width=True, hide_index=True)
    st.caption("Fuente: ARCONEL — Factor de emisión de CO₂ del SNI de Ecuador (Informe 2024)")

    _impact_box(f"Intensidad {ano}: {e['intensidad_gkwh']} gCO₂/kWh. "
                f"Ecuador está entre los más bajos de LatAm gracias a la hidro. "
                f"Pero la crisis 2024 subió a 252 gCO₂/kWh. "
                f"Decisión: mantener alta participación hidro + agregar VRE.",
                "success" if e['intensidad_gkwh'] < 180 else "alert")

    # ─── SIMULADOR INTERACTIVO: REDUCCIÓN DE EMISIONES ───
    st.markdown("---")
    st.markdown("### 🎮 Simulador: Trayectoria de Descarbonización")
    st.markdown("Ajuste la participación de cada fuente para ver el impacto en emisiones "
                "y la trayectoria de descarbonización del SNI.")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        hidro_pct_sim = st.slider("Hidro (%)", 40, 95, 75, 5,
                                  key="em_hidro")
    with col2:
        vre_pct_sim = st.slider("VRE (solar+eólica) (%)", 0, 40, 10, 5,
                                key="em_vre")
    with col3:
        termo_pct_sim = st.slider("Térmico (%)", 0, 40, 12, 5,
                                  key="em_termo")
    with col4:
        demanda_gwh = st.slider("Demanda anual (TWh)", 15, 35, 22, 1,
                                help="Demanda actual: ~22 TWh/año",
                                key="em_demanda")
    
    # Normalizar porcentajes
    total_pct = hidro_pct_sim + vre_pct_sim + termo_pct_sim + 3  # +3% biomasa
    if total_pct > 100:
        st.warning(f"⚠️ Total: {total_pct}%. Ajuste los porcentajes (máximo 100%).")
    
    # Cálculos de emisiones
    gen_total_gwh = demanda_gwh * 1000  # GWh
    gen_hidro_gwh = gen_total_gwh * hidro_pct_sim / 100
    gen_vre_gwh = gen_total_gwh * vre_pct_sim / 100
    gen_termo_gwh = gen_total_gwh * termo_pct_sim / 100
    
    # Emisiones: térmica ~0.5 tCO2/MWh, hidro/VRE ~0
    co2_total_sim = gen_termo_gwh * 0.5 / 1000  # MtCO2
    intensidad_sim = co2_total_sim * 1e6 / gen_total_gwh if gen_total_gwh > 0 else 0  # gCO2/kWh
    
    # Meta NDC Ecuador: reducir 20% para 2030 (vs baseline ~6 MtCO2)
    meta_ndc = 6.0 * 0.8  # 4.8 MtCO2
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Emisiones totales", f"{co2_total_sim:.2f} MtCO₂",
              delta=f"vs. 4.7 MtCO₂ (2024)")
    c2.metric("Intensidad", f"{intensidad_sim:.0f} gCO₂/kWh",
              delta=f"vs. {e['intensidad_gkwh']} ({ano})")
    c3.metric("Meta NDC 2030", f"{meta_ndc:.1f} MtCO₂",
              delta="Cumple" if co2_total_sim <= meta_ndc else "No cumple",
              delta_color="normal" if co2_total_sim <= meta_ndc else "inverse")
    c4.metric("Reducción vs 2024", f"{(4.7-co2_total_sim)/4.7*100:+.0f}%")
    
    # Trayectoria de descarbonización
    anos_desc = list(range(2024, 2031))
    em_actual = [4.7, 4.3, 3.9, 3.5, 3.1, 2.7, 2.3]  # trayectoria ideal
    em_sim = [4.7] + [4.7 * (1 - (i/6) * (1 - co2_total_sim/4.7)) for i in range(1, 7)]
    
    fig_desc = go.Figure()
    fig_desc.add_trace(go.Scatter(x=anos_desc, y=em_actual, mode="lines+markers",
                                  name="Trayectoria NDC", line=dict(color="#6A994E", width=3, dash="dash")))
    fig_desc.add_trace(go.Scatter(x=anos_desc, y=em_sim, mode="lines+markers",
                                  name="Escenario simulado", line=dict(color="#C73E1D", width=3)))
    fig_desc.add_hline(y=meta_ndc, line_dash="dot", line_color="orange",
                       annotation_text=f"Meta NDC: {meta_ndc:.1f} MtCO₂")
    fig_desc.update_layout(title="Trayectoria de Descarbonización (MtCO₂)",
                           xaxis_title="Año", yaxis_title="MtCO₂", height=350)
    st.plotly_chart(fig_desc, use_container_width=True)
    
    if co2_total_sim <= meta_ndc:
        _impact_box(f"✅ Escenario cumple meta NDC: {co2_total_sim:.2f} MtCO₂ < {meta_ndc:.1f} MtCO₂. "
                    f"Intensidad: {intensidad_sim:.0f} gCO₂/kWh.", "success")
    else:
        _impact_box(f"⚠️ Escenario NO cumple meta NDC: {co2_total_sim:.2f} > {meta_ndc:.1f} MtCO₂. "
                    f"Reducir térmico o aumentar VRE.", "danger")

# =============================================================================
# TAB 13: HERRAMIENTAS (Torres/Rivera)
# =============================================================================
def render_tab_ferramentas(settings):
    st.subheader("🔧 Herramientas de Investigación — Torres Contreras · Rivera")

    # Torres Contreras
    st.markdown("### 🇪🇨 Prof. Santiago Torres Contreras (U. Cuenca)")
    st.markdown(
        "**Profesor Titular** · DEET, Facultad de Ingeniería, Universidad de Cuenca  \n"
        "**IEEE Senior Member** · Doctorado Unicamp (con C.A. Castro) · Posdoc Unicamp + Cornell + KU Leuven  \n"
        "Ex-Subgerente de Planificación **CELEC EP** (2007-2010)  \n"
        "**656 citas · h-index 13** · [Scholar](https://scholar.google.com/citations?user=4EfR5L8AAAAJ)"
    )
    st.markdown("#### 7 ejes de investigación")
    st.markdown(
        "1. **TNEP con modelo AC** (su marca): metaheurísticas especializadas (IET GTD 2014 —96 citas—, "
        "IEEE TPWRS 2023, PowerTech Kiel 2025)\n"
        "2. **Planificación híbrida AC/DC** con VSC-MTDC, FACTS y almacenamiento (EPSR 2023)\n"
        "3. **Co-planificación G&T** con R. Romero (IEEE Access 2024)\n"
        "4. **Estabilidad de tensión e inteligencia computacional** (IEEE TPWRS 2007)\n"
        "5. **Estimación dinámica de estado con Koopman** (ICECET 2026)\n"
        "6. **Distribución, micro-redes y resiliencia** (EPSR 2024)\n"
        "7. **Hidrógeno verde con excedentes hidro en Ecuador** (Energy 2014, ~75 citas)"
    )
    st.markdown("#### 📄 Publicaciones Clave")
    pubs_torres = pd.DataFrame([
        {"Año": 2014, "Título": "Expansion planning for smart transmission grids using AC model (IET GTD)",
         "Citas": 96, "Tema": "TNEP AC + compensación shunt"},
        {"Año": 2023, "Título": "Comparison metaheuristic vs math-optimization AC TNEP (IEEE TPWRS)",
         "Citas": 15, "Tema": "PowerModels/TNEP vs. metaheurística híbrida"},
        {"Año": 2023, "Título": "Unified AC TEP: VSC-MTDC + FACTS + reactivos (EPSR)",
         "Citas": 12, "Tema": "Planificación híbrida AC/DC"},
        {"Año": 2024, "Título": "AC co-optimization G&TEP (IEEE Access)",
         "Citas": 10, "Tema": "Co-planificación G+T con pérdidas"},
        {"Año": 2024, "Título": "Service restoration with microgrids (EPSR)",
         "Citas": 8, "Tema": "Resiliencia distribución"},
        {"Año": 2026, "Título": "Decoupled Koopman state estimation (ICECET)",
         "Citas": 2, "Tema": "Estimación de estado dinámica"},
    ])
    st.dataframe(pubs_torres, use_container_width=True, hide_index=True)

    st.markdown("#### 🏗️ Proyectos Vigentes")
    st.markdown(
        "- **Planificación óptima convexa integrada G&T** con restricciones de estabilidad (Director)\n"
        "- **Herramienta TNEP con incertidumbre** (Director)\n"
        "- Colaboración **KU Leuven/EnergyVille** (Van Hertem, Ergun)\n"
        "- Colaboración **UNESP-LaPSEE** (Romero, Chillogalli)\n"
        "- Convenios **CELEC EP**, Empresa Eléctrica Centro Sur, CENACE\n\n"
        "**Vías de financiación:** CEDIA, SENESCYT, fondos internos U. Cuenca, OLADE, CYTED, "
        "cooperación Ecuador-Brasil (CAPES)"
    )

    # Sergio Rivera
    st.markdown("### 🇨🇴 Prof. Sergio Rivera (UNAL — Universidad Nacional de Colombia)")
    st.markdown(
        "**Profesor e Investigador** · Departamento de Ingeniería Eléctrica y Electrónica, "
        "**Universidad Nacional de Colombia** (sede Bogotá)  \n"
        "**Investigador destacado en sistemas de potencia** con enfoque en mercados eléctricos, "
        "optimización estocástica, calidad de energía y micro-redes"
    )

    st.markdown("#### 🎓 Trayectoria académica internacional")
    st.markdown(
        "Profesor e investigador en las siguientes universidades:\n\n"
        "- 🇩🇪 **Karlsruhe Institute of Technology — KIT** "
        "(Beca *Helmholtz Visiting Researcher Grant*, Helmholtz Information & Data Science Academy — HIDA)\n"
        "- 🇺🇸 **University of Florida** "
        "(Beca *Fulbright*, Científico Visitante)\n"
        "- 🇩🇪 **Technical University of Dortmund** "
        "(*Gambrinus Fellowship* y Beca DAAD — estancia de investigación para científicos)\n"
        "- 🇩🇪 **Ruhr University Bochum** "
        "(*VIP Program — Visiting International Professor*)\n\n"
        "Realizó **dos postdoctorados** en el área de control y coordinación de redes inteligentes y microredes en:\n\n"
        "- 🇺🇸 **Massachusetts Institute of Technology (MIT)** — "
        "Laboratorio de Investigación en Mecatrónica (MRL at MIT)\n"
        "- 🇦🇪 **Masdar Institute of Science and Technology, Khalifa University (UAE)** — "
        "Laboratory for Intelligent Integrated Networks of Engineering Systems (LIINES)"
    )

    st.markdown("#### 7 ejes de investigación")
    st.markdown(
        "1. **Funciones de Costo de Incertidumbre (UCF)** — Modelos analíticos para cuantificar el costo "
        "de la variabilidad de recursos renovables en mercados eléctricos. Las UCF se aplican en OPF "
        "estocástico y planificación de expansión.\n"
        "2. **OPF estocástico con renovables** — Diseñó los *test beds* de la competencia IEEE PES WGMHO "
        "2018 (co-chair Rivera): OPF estocástico con cargas controlables y OPF dinámico "
        "con renovables y vehículos eléctricos.\n"
        "3. **Calidad de energía y PQ monitoring** — Análisis de perturbaciones, armónicos y flicker "
        "en sistemas de distribución colombianos.\n"
        "4. **Micro-redes comunitarias** — Diseño y optimización de micro-redes para zonas no "
        "interconectadas (ZNI) de Colombia, con enfoque en equidad energética.\n"
        "5. **Planificación de expansión con incertidumbre** — G&TEP con UCF analíticas y CVaR, "
        "integrando almacenamiento y demanda flexible.\n"
        "6. **Mercados eléctricos y poder de mercado** — Análisis de IOR (Index of Opportunity Rent), "
        "elasticidad de demanda y concentración por nodo en el mercado colombiano (XM).\n"
        "7. **Aprendizaje por refuerzo** — Q-learning multiagente para despacho óptimo sin coordinador "
        "centralizado, aplicado a sistemas con alta penetración renovable."
    )

    st.markdown("#### Publicaciones y contribuciones destacadas")
    pubs_rivera = pd.DataFrame([
        {"Año": 2017, "Título": "OPF con UCF analíticas para sistemas con renovables (Ingeniería)",
         "Citas": 45, "Tema": "UCF + OPF estocástico"},
        {"Año": 2018, "Título": "WGMHO Competition test beds: OPF estocástico (IEEE PES)",
         "Citas": 35, "Tema": "Diseño competencias IEEE"},
        {"Año": 2020, "Título": "Micro-redes comunitarias en ZNI Colombia",
         "Citas": 28, "Tema": "Equidad energética"},
        {"Año": 2022, "Título": "G&TEP con CVaR y almacenamiento",
         "Citas": 22, "Tema": "Planificación con riesgo"},
        {"Año": 2024, "Título": "Poder de mercado en XM: IOR y elasticidad",
         "Citas": 15, "Tema": "Mercados eléctricos"},
        {"Año": 2024, "Título": "Dashboard SIN nodal Colombia (app.py)",
         "Citas": 0, "Tema": "Herramienta open source"},
    ])
    st.dataframe(pubs_rivera, use_container_width=True, hide_index=True)

    st.markdown("#### Proyectos y colaboraciones")
    st.markdown(
        "- **Dashboard Colombia** (NZdashboard): 212 celdas, 4 pestañas, módulo nodal completo\n"
        "- **Dashboard Ecuador** (ECUdashboard): este proyecto\n"
        "- **Dashboard Brasil** (BRdashboard): 13 pestañas con simuladores\n"
        "- **WGMHO 2018-19** con Torres (Cuenca)\n"
        "- **MicroGrid Commons**: plataforma open source de micro-redes\n"
        "- **Vías de financiación:** Colciencias/Minciencias, Alianza del Pacífico, "
        "Horizon Europe, Erasmus+ KA171, Marie Skłodowska-Curie, Fulbright, DAAD, Helmholtz/HIDA"
    )

    st.markdown("---")

    # Sinergias conjuntas
    st.markdown("### 🤝 Sinergias Rivera–Torres")
    st.markdown(
        "| Tema | Enlace Natural |\n"
        "|---|---|\n"
        "| **WGMHO 2018-19** (Rivera + Torres) | Competencia WGMHO 2027/28 con UCF + seguridad dinámica |\n"
        "| **TNEP AC** (Torres) + **UCF** (Rivera) | G&TEP completo con incertidumbre |\n"
        "| **Koopman** (Torres 2026) + **WAMS** (Rivera) | Estimación dinámica de estado WAMS Ecuador |\n"
        "| **ENOS/crisis hidrológica** | Dashboard Ecuador-Colombia-NZ (3er país natural) |\n"
        "| **UCF analíticas** (Rivera) | Término de costo en G&TEP de Torres |\n"
        "| **Q-learning** (Rivera) | Despacho descentralizado multiagente |\n"
        "| **Micro-redes** (Rivera) + **Resiliencia** (Torres) | ZNI Colombia + rural Ecuador |\n"
    )

    # Open source
    st.markdown("#### 🖥️ Herramientas Open Source")
    st.markdown(
        "- **MATPOWER/PowerModels.jl**: TNEP AC con relajaciones convexas\n"
        "- **MVVO**: Mean-Variance Mapping Optimization\n"
        "- **DIgSILENT PowerFactory**: modelado a gran escala\n"
        "- **RSCAD/RTDS**: simulación EMT en tiempo real\n"
        "- **Python WAMS**: analítica de sincrofasores (este dashboard)\n"
        "- **MicroGrid Commons**: plataforma de micro-redes (Rivera)\n"
        "- **Dashboard SIN Nodal**: precios nodales Colombia (Rivera)"
    )

# =============================================================================
# MAIN
# =============================================================================
# =============================================================================
# TAB 14: CONTINGENCIAS Y PROTECCIÓN SISTÉMICA (SPS)
# =============================================================================
def render_tab_contingencias(settings):
    ano = settings["ano"]
    st.subheader("⚠️ Contingencias y Protección Sistémica (SPS) del SNI")

    st.markdown(
        "El **Sistema de Protección Sistémica (SPS)** fue implementado por CENACE en **marzo 2015**. "
        "Detecta contingencias críticas predefinidas (N-1 y N-2) y ejecuta **acciones remediales automáticas** "
        "en < 100 ms para evitar colapso total o parcial del SNI."
    )

    # KPIs del SPS
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Contingencias SPS", len(CONTINGENCIAS_CRITICAS[CONTINGENCIAS_CRITICAS["SPS"]=="Sí"]))
    c2.metric("SE críticas sin reserva",
              len(SUBESTACIONES_CRITICAS[SUBESTACIONES_CRITICAS["trafo_reserva"]=="No"]))
    c3.metric("Riesgos operativos 2026", len(RIESGOS_OPERATIVOS_2026))
    c4.metric("Corredores monitoreados", len(CORREDORES_TRANSMISION))

    # Información del SPS
    st.markdown("#### 🛡️ Sistema de Protección Sistémica (SPS)")
    st.markdown(f"- **Implementación:** {SPS_INFO['implementacion']}\n"
                f"- **Función:** {SPS_INFO['funcion']}\n"
                f"- **Tiempo de actuación:** {SPS_INFO['tiempo_actuacion']}\n"
                f"- **Centro de control:** {SPS_INFO['centro_control']}")

    # Criterios SPS
    st.markdown("##### Criterios de activación:")
    for c in SPS_INFO["criterios"]:
        st.markdown(f"- {c}")

    # Tabla de contingencias
    st.markdown("#### 📋 Contingencias Críticas Identificadas (N-1 y N-2)")
    st.dataframe(CONTINGENCIAS_CRITICAS, use_container_width=True, hide_index=True)

    # Mapa de calor de uso de corredores
    st.markdown("---")
    st.markdown("#### 🗺️ Uso de Corredores de Transmisión")
    st.markdown(
        "El Plan de Operación SNI 2024-2026 advierte que el sistema opera **cercano a los límites "
        "de inestabilidad** y permanentemente **expuesto a desconexiones de carga**."
    )

    corr = CORREDORES_TRANSMISION.sort_values("uso_pct", ascending=True)
    fig_corr = go.Figure(go.Bar(
        x=corr["uso_pct"], y=corr["corredor"], orientation="h",
        marker_color=["#C73E1D" if v > 85 else "#F18F01" if v > 70 else "#6A994E"
                      for v in corr["uso_pct"]],
        text=corr["uso_pct"].apply(lambda x: f"{x}%"), textposition="outside"))
    fig_corr.add_vline(x=80, line_dash="dash", line_color="orange", annotation_text="Límite operativo (80%)")
    fig_corr.add_vline(x=90, line_dash="dash", line_color="red", annotation_text="Límite emergencia (90%)")
    fig_corr.update_layout(title="Uso de Corredores vs Capacidad (peor escenario)",
                           xaxis_title="Uso (%)", height=400, margin=dict(t=50,b=40,l=200,r=20))
    st.plotly_chart(fig_corr, use_container_width=True)
    _impact_box("Corredor Trinitaria-Salitral-Pascuales al 92%: cualquier desconexión para mantenimiento "
                "requiere corte de carga. Decisión: construir refuerzos 230 kV en zona Guayaquil.", "danger")

    # Subestaciones críticas
    st.markdown("#### 🔌 Subestaciones Críticas del SNI")
    st.dataframe(SUBESTACIONES_CRITICAS, use_container_width=True, hide_index=True)
    _impact_box("12 subestaciones sin transformador de reserva. Avería → colapso total del servicio "
                "para sus usuarios por tiempo indefinido. Decisión: priorizar adquisición de trafos de reserva.", "danger")

    # Riesgos operativos 2026
    st.markdown("---")
    st.markdown("#### 🚨 Riesgos Operativos Identificados por CENACE (2026)")
    st.dataframe(RIESGOS_OPERATIVOS_2026, use_container_width=True, hide_index=True)
    _impact_box("CENACE advierte: 'imposibilidad de viabilizar mantenimientos en el SNT'. "
                "El sistema se degrada progresivamente. Decisión: inversión urgente en transmisión.", "danger")

    # Simulador de contingencia
    st.markdown("---")
    st.markdown("#### 🎮 Simulador de Contingencia N-1")
    cont_sel = st.selectbox("Seleccionar contingencia",
                            CONTINGENCIAS_CRITICAS["elemento"].tolist(), index=0)
    cont_data = CONTINGENCIAS_CRITICAS[CONTINGENCIAS_CRITICAS["elemento"]==cont_sel].iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Tipo", cont_data["tipo"])
    c2.metric("Zona", cont_data["zona"])
    c3.metric("Riesgo", cont_data["riesgo"])
    st.markdown(f"**Consecuencia:** {cont_data['consecuencia']}")
    st.markdown(f"**Acción remedial:** {cont_data['accion_remedial']}")
    st.markdown(f"**SPS activo:** {'✅ Sí' if cont_data['SPS']=='Sí' else '⚠️ Pendiente/Parcial'}")

# =============================================================================
# TAB 15: PRECIOS NODALES
# =============================================================================
def render_tab_nodales(settings):
    ano = settings["ano"]
    janela = settings["janela"]
    st.subheader("💰 Precios Nodales — Simulación de Costos Marginales por Nodo")

    st.markdown(
        "Modelo simplificado de precios nodales para el SNI de Ecuador. "
        "Calcula el **costo marginal local** en cada subestación principal considerando "
        "generación local, congestión de corredores y pérdidas de transmisión."
    )
    st.caption(f"📅 Ventana de análisis: **{ano}** · Datos históricos 2022-2026 · "
               f"Janela temporal RT: **{janela}** · Fuentes: CENACE, ARCONEL, CNEL EP")

    # Precios del año seleccionado
    prec = PRECIOS_NODALES_HISTORICOS[PRECIOS_NODALES_HISTORICOS["ano"]==ano]
    if len(prec) > 0:
        p = prec.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"Promedio Sistema ({ano})", f"${p['promedio_sistema']}/MWh")
        c2.metric("Nodo más caro", f"Trinitaria: ${p.get('Trinitaria',0)}/MWh",
                  delta=f"+${p.get('Trinitaria',0)-p['promedio_sistema']}/MWh vs promedio")
        c3.metric("Nodo más barato", f"Coca Codo: ${p.get('Coca Codo',0)}/MWh",
                  delta=f"-${p['promedio_sistema']-p.get('Coca Codo',0)}/MWh vs promedio")
        c4.metric("Spread nodal",
                  f"${p.get('Trinitaria',0)-p.get('Coca Codo',0)}/MWh",
                  delta=f"Congestión", delta_color="inverse")

    # Mapa de calor de precios nodales
    st.markdown("#### 🗺️ Mapa de Precios Nodales")
    nodos = list(NODOS_PRECIO.keys())
    precios_ano = {n: p.get(n, 50) for n in nodos if n in p.index}

    fig_map = go.Figure(go.Scatter(
        x=[NODOS_PRECIO[n]["lon"] for n in nodos],
        y=[NODOS_PRECIO[n]["lat"] for n in nodos],
        mode="markers+text",
        marker=dict(size=[20 + precios_ano.get(n, 50) * 0.3 for n in nodos],
                    color=[precios_ano.get(n, 50) for n in nodos],
                    colorscale="RdYlGn_r", colorbar=dict(title="USD/MWh"),
                    showscale=True),
        text=[f"{n}\n${precios_ano.get(n, 50):.0f}" for n in nodos],
        textposition="top center", textfont=dict(size=9)))
    fig_map.update_layout(title=f"Precios Nodales ({ano}, USD/MWh)",
                          xaxis_title="Longitud", yaxis_title="Latitud",
                          height=450, xaxis=dict(range=[-80.5, -77]),
                          yaxis=dict(range=[-4, 1]))
    st.plotly_chart(fig_map, use_container_width=True)
    _impact_box(f"Spread nodal ${p.get('Trinitaria',0)-p.get('Coca Codo',0)}/MWh. "
                f"Trinitaria (Guayaquil Sur) es el nodo más caro por congestión del corredor 138 kV. "
                f"Decisión: refuerzo de transmisión reduce precio local y señal de inversión.", "alert")

    # Evolución temporal
    st.markdown("#### 📊 Evolución de Precios Nodales (2022-2026)")
    fig_ev = go.Figure()
    for nodo in ["El Inga", "Pascuales", "Trinitaria", "Molino", "Coca Codo"]:
        if nodo in PRECIOS_NODALES_HISTORICOS.columns:
            fig_ev.add_trace(go.Scatter(
                x=PRECIOS_NODALES_HISTORICOS["ano"],
                y=PRECIOS_NODALES_HISTORICOS[nodo],
                mode="lines+markers", name=nodo,
                line=dict(width=2.5 if nodo=="Trinitaria" else 1.5)))
    fig_ev.add_trace(go.Scatter(
        x=PRECIOS_NODALES_HISTORICOS["ano"],
        y=PRECIOS_NODALES_HISTORICOS["promedio_sistema"],
        mode="lines", name="Promedio sistema",
        line=dict(width=3, color="#333", dash="dash")))
    fig_ev.add_vline(x=ano, line_dash="dot", line_color="red")
    fig_ev.update_layout(title="Precios Nodales Históricos (USD/MWh)",
                         yaxis_title="USD/MWh", height=380,
                         legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig_ev, use_container_width=True)

    # Tabla detallada
    st.markdown("#### 📋 Detalle por Nodo")
    precio_col = f"Precio {ano} (USD/MWh)"
    nodos_df = pd.DataFrame([
        {"Nodo": n, "Zona": d["zona"], "Voltaje": d["tipo"],
         "Carga (MW)": d["carga_mw"], "Gen. Local (MW)": d["gen_local_mw"],
         "Déficit (MW)": max(0, d["carga_mw"] - d["gen_local_mw"]),
         "Factor Pérdida": d["factor_perdida"],
         precio_col: float(p[n]) if n in p.index and pd.notna(p.get(n)) else np.nan}
        for n, d in NODOS_PRECIO.items()
    ]).sort_values(precio_col, ascending=False)
    st.dataframe(nodos_df, use_container_width=True, hide_index=True)

    # Comparación de precios
    st.markdown("---")
    st.markdown("#### ⚖️ Descomposición del Precio Nodal")
    nodo_sel = st.selectbox("Seleccionar nodo", nodos, index=nodos.index("Trinitaria"))
    nd = NODOS_PRECIO[nodo_sel]

    # Precio = costo base + congestión + pérdidas
    costo_base = 18.0  # USD/MWh (hidro Paute como referencia)
    if ano == 2024:
        costo_base = 35.0  # Crisis: térmica más cara
    congestión = max(0, nd["factor_perdida"] * 1000 - 5) * (1.5 if ano == 2024 else 1.0)
    pérdidas = nd["factor_perdida"] * costo_base * 10
    precio_nodal = costo_base + congestión + pérdidas

    fig_desc = go.Figure(go.Bar(
        x=["Costo base", "Congestión", "Pérdidas"],
        y=[costo_base, congestión, pérdidas],
        marker_color=["#2E86AB", "#C73E1D", "#F18F01"],
        text=[f"${v:.1f}" for v in [costo_base, congestión, pérdidas]],
        textposition="outside"))
    fig_desc.update_layout(title=f"Descomposición Precio Nodal — {nodo_sel} ({ano})",
                           yaxis_title="USD/MWh", height=350)
    st.plotly_chart(fig_desc, use_container_width=True)
    _impact_box(f"{nodo_sel}: precio ${precio_nodal:.1f}/MWh = ${costo_base:.0f} base + "
                f"${congestión:.1f} congestión + ${pérdidas:.1f} pérdidas. "
                f"{'ALERTA: nodo congestionado, inversión en transmisión necesaria.' if congestión > 15 else 'OK.'}",
                "danger" if congestión > 15 else "info")

    # Costos marginales por tecnología
    st.markdown("#### ⚡ Costos Marginales de Generación")
    fig_cm = go.Figure(go.Bar(
        x=list(COSTOS_MARGINALES.keys()), y=list(COSTOS_MARGINALES.values()),
        marker_color=["#2E86AB" if "Hidro" in k else "#C73E1D" if "Térmico" in k else "#6A994E"
                      for k in COSTOS_MARGINALES.keys()],
        text=[f"${v}/MWh" for v in COSTOS_MARGINALES.values()], textposition="outside"))
    fig_cm.update_layout(title="Costos Marginales por Tecnología (USD/MWh)",
                         yaxis_title="USD/MWh", height=350, xaxis_tickangle=-45)
    st.plotly_chart(fig_cm, use_container_width=True)

    # Tabla de precios históricos
    st.markdown("#### 📊 Precios Nodales Históricos")
    st.dataframe(PRECIOS_NODALES_HISTORICOS, use_container_width=True, hide_index=True)

    # ─── SIMULADOR INTERACTIVO: ESCENARIO DE PRECIOS NODALES ───
    st.markdown("---")
    st.markdown("### 🎮 Simulador: Impacto en Precios Nodales")
    st.markdown("Simule cómo cambios en la generación, demanda o congestión afectan "
                "los precios en diferentes nodos del SNI.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        nodo_sim = st.selectbox("Nodo a analizar", list(NODOS_PRECIO.keys()),
                                key="nodal_nodo")
    with col2:
        demanda_factor = st.slider("Factor de demanda", 0.7, 1.3, 1.0, 0.05,
                                   help="0.7 = valle, 1.0 = normal, 1.3 = pico",
                                   key="nodal_dem")
    with col3:
        congestion_mw = st.slider("Congestión en corredor (MW)", 0, 300, 0, 25,
                                  help="MW de congestión que aísla el nodo",
                                  key="nodal_cong")
    
    # Cálculos basados en el nodo seleccionado
    nodo_data = NODOS_PRECIO[nodo_sim]
    # Obtener precio base de PRECIOS_NODALES_HISTORICOS
    p2026 = PRECIOS_NODALES_HISTORICOS[PRECIOS_NODALES_HISTORICOS['ano']==2026].iloc[0]
    precio_base = float(p2026[nodo_sim]) if nodo_sim in p2026.index else 45
    zona = nodo_data.get("zona", "Centro")
    
    # Precio = base × factor_demanda + congestión
    precio_sim = precio_base * demanda_factor + congestion_mw * 0.15
    spread = abs(precio_sim - 45)  # vs precio promedio
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Precio {nodo_sim}", f"${precio_sim:.2f}/MWh",
              delta=f"vs base: ${precio_base}")
    c2.metric("Zona", zona)
    c3.metric("Factor demanda", f"{demanda_factor:.2f}x")
    c4.metric("Congestión", f"{congestion_mw} MW",
              delta=f"+${congestion_mw*0.15:.1f}/MWh")
    
    # Comparación con otros nodos
    nodos_comp = list(NODOS_PRECIO.keys())[:6]  # primeros 6
    precios_comp = [(float(p2026[n]) if n in p2026.index else 45) * demanda_factor 
                    for n in nodos_comp]
    
    fig_nodal_sim = go.Figure()
    fig_nodal_sim.add_trace(go.Bar(x=nodos_comp, y=precios_comp,
                                   marker_color=["#C73E1D" if n == nodo_sim else "#2E86AB" 
                                                 for n in nodos_comp],
                                   text=[f"${p:.1f}" for p in precios_comp],
                                   textposition="outside"))
    fig_nodal_sim.update_layout(title=f"Precios Nodales (demanda x{demanda_factor:.2f})",
                                yaxis_title="USD/MWh", height=350, xaxis_tickangle=-30)
    st.plotly_chart(fig_nodal_sim, use_container_width=True)
    
    if congestion_mw > 150:
        _impact_box(f"Alta congestión ({congestion_mw} MW): precio en {nodo_sim} sube a "
                    f"${precio_sim:.2f}/MWh (+${congestion_mw*0.15:.1f} vs base). "
                    f"Decisión: refuerzo de transmisión para aliviar congestión.", "danger")
    elif demanda_factor > 1.15:
        _impact_box(f"Demanda alta ({demanda_factor:.2f}x): precio en {nodo_sim} = "
                    f"${precio_sim:.2f}/MWh. Activar generación de respaldo.", "alert")
    else:
        _impact_box(f"Escenario normal: precio en {nodo_sim} = ${precio_sim:.2f}/MWh. "
                    f"Zona: {zona}. Sin congestión significativa.", "success")

# =============================================================================
# TAB 16: CONGESTIÓN Y FLUJOS DE POTENCIA
# =============================================================================
def render_tab_congestion(settings):
    ano = settings["ano"]
    janela = settings["janela"]
    st.subheader("🔴 Congestión y Flujos de Potencia — Red de Transmisión del SNI")

    st.markdown(
        "Análisis detallado de los flujos de potencia en las líneas de transmisión del SNI, "
        "sus capacidades térmicas y los eventos de congestión registrados."
    )
    st.caption(f"📅 Ventana de análisis: **{ano}** · Datos históricos 2022-2026 · "
               f"Janela temporal RT: **{janela}** · Fuentes: CENACE, Transelectric, "
               f"Plan de Operación SNI 2024-2026")

    # KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    total_lineas = len(LINEAS_TRANSMISION)
    criticas = len(LINEAS_TRANSMISION[LINEAS_TRANSMISION["critico"].isin(["CRÍTICO", "ALTO"])])
    uso_max = LINEAS_TRANSMISION["uso_pico_pct"].max()
    eventos = len(EVENTOS_CONGESTION)
    costo_total = CONGESTION_ZONAL["costo_congestion_musd"].sum()
    c1.metric("Líneas monitoreadas", f"{total_lineas}")
    c2.metric("Líneas críticas", f"{criticas}", delta="ALTO/CRÍTICO", delta_color="inverse")
    c3.metric("Uso máximo (pico)", f"{uso_max}%", delta="Límite 100%", delta_color="inverse")
    c4.metric("Eventos congestión", f"{eventos}")
    c5.metric("Costo congestión", f"USD {costo_total:.1f}M/año")

    # Uso de líneas
    st.markdown("---")
    st.markdown("#### 📊 Uso de Líneas de Transmisión")
    st.markdown(
        "Cada barra muestra el uso de la línea en condiciones **normales** y **pico**. "
        "Las líneas rojas superan el 85% en pico → riesgo de congestión."
    )

    lineas_sorted = LINEAS_TRANSMISION.sort_values("uso_pico_pct", ascending=True)
    fig_uso = go.Figure()
    fig_uso.add_trace(go.Bar(
        x=lineas_sorted["uso_normal_pct"], y=lineas_sorted["linea"], orientation="h",
        name="Uso normal", marker_color="#6A994E", opacity=0.8))
    fig_uso.add_trace(go.Bar(
        x=lineas_sorted["uso_pico_pct"], y=lineas_sorted["linea"], orientation="h",
        name="Uso pico", marker_color=["#C73E1D" if v > 85 else "#F18F01" if v > 70 else "#6A994E"
                                       for v in lineas_sorted["uso_pico_pct"]], opacity=0.6))
    fig_uso.add_vline(x=80, line_dash="dash", line_color="orange", annotation_text="Límite operativo (80%)")
    fig_uso.add_vline(x=95, line_dash="dash", line_color="red", annotation_text="Emergencia (95%)")
    fig_uso.update_layout(barmode="overlay", title="Uso de Líneas de Transmisión (%)",
                          xaxis_title="Uso (%)", height=600, margin=dict(t=50,b=40,l=300,r=20),
                          legend=dict(orientation="h", y=1.08))
    st.plotly_chart(fig_uso, use_container_width=True)
    _impact_box(f"{len(LINEAS_TRANSMISION[LINEAS_TRANSMISION['uso_pico_pct']>90])} líneas superan "
                f"el 90% de capacidad en pico. Decisión: priorizar refuerzos en Trinitaria-Salitral "
                f"(98%), Salitral-Pascuales (97%) y Yanacocha-Cuenca (95%).", "danger")

    # Tabla detallada de líneas
    st.markdown("#### 📋 Líneas de Transmisión — Detalle Completo")
    col_show = ["linea", "voltaje", "longitud_km", "capacidad_mw", "flujo_normal_mw",
                "flujo_pico_mw", "uso_normal_pct", "uso_pico_pct", "reactancia_pu", "critico"]
    st.dataframe(LINEAS_TRANSMISION[col_show].sort_values("uso_pico_pct", ascending=False),
                 use_container_width=True, hide_index=True)

    # Congestión por zona
    st.markdown("---")
    st.markdown("#### 🗺️ Congestión por Zona")
    fig_zona = go.Figure()
    cong_sorted = CONGESTION_ZONAL.sort_values("costo_congestion_musd", ascending=True)
    fig_zona.add_trace(go.Bar(
        x=cong_sorted["costo_congestion_musd"], y=cong_sorted["zona"], orientation="h",
        name="Costo congestión (M USD/año)",
        marker_color=["#C73E1D" if v > 5 else "#F18F01" if v > 2 else "#6A994E"
                      for v in cong_sorted["costo_congestion_musd"]],
        text=cong_sorted["costo_congestion_musd"].apply(lambda x: f"${x:.1f}M"), textposition="outside"))
    fig_zona.update_layout(title="Costo de Congestión por Zona (M USD/año)",
                           xaxis_title="M USD/año", height=380, margin=dict(t=50,b=40,l=180,r=20))
    st.plotly_chart(fig_zona, use_container_width=True)
    st.dataframe(CONGESTION_ZONAL, use_container_width=True, hide_index=True)
    _impact_box(f"Guayaquil (138 kV) concentra ${CONGESTION_ZONAL[CONGESTION_ZONAL['zona'].str.contains('Guayaquil')]['costo_congestion_musd'].values[0]:.1f}M/año "
                f"en congestión: 6 horas/día con sobrecarga. Decisión: construir nuevo corredor 230 kV "
                f"que alivie el anillo 138 kV.", "danger")

    # Eventos de congestión
    st.markdown("---")
    st.markdown("#### 🚨 Eventos de Congestión Registrados")
    st.dataframe(EVENTOS_CONGESTION, use_container_width=True, hide_index=True)

    # Flujos de potencia
    st.markdown("---")
    st.markdown("#### ⚡ Flujos de Potencia — Corredores Principales")
    st.markdown(
        "Diagrama de flujos de potencia en los corredores principales del SNI. "
        "El grosor de la barra indica la capacidad y el color el nivel de uso."
    )

    corredores = ["L/T CCS–El Inga 500 kV (Cto 1)", "L/T El Inga–Tisaleo 500 kV",
                  "L/T Tisaleo–Chorrillos 500 kV", "L/T Molino–Zhoray 230 kV",
                  "L/T Trinitaria–Salitral 138 kV", "L/T Salitral–Pascuales 138 kV",
                  "L/T Santa Rosa–Totoras 230 kV (Cto 1)", "L/T Dos Cerritos–Pascuales 230 kV"]

    fig_flujos = go.Figure()
    for corr in corredores:
        match = LINEAS_TRANSMISION[LINEAS_TRANSMISION["linea"] == corr]
        if len(match) == 0:
            continue
        row = match.iloc[0]
        fig_flujos.add_trace(go.Bar(
            x=[row["capacidad_mw"], row["flujo_pico_mw"], row["flujo_normal_mw"]],
            y=[corr] * 3, orientation="h",
            name=corr, showlegend=False,
            marker_color=["#BDBDBD", "#F18F01", "#2E86AB"],
            text=[f"Cap: {row['capacidad_mw']}", f"Pico: {row['flujo_pico_mw']}",
                  f"Normal: {row['flujo_normal_mw']}"],
            textposition="outside"))
    fig_flujos.update_layout(barmode="group", title="Flujos de Potencia — Corredores Principales (MW)",
                             xaxis_title="MW", height=450, margin=dict(t=50,b=40,l=280,r=20))
    st.plotly_chart(fig_flujos, use_container_width=True)

    # Simulador de congestión
    st.markdown("---")
    st.markdown("#### 🎮 Simulador de Congestión N-1")
    st.markdown("Simule la salida de una línea y observe el impacto en las líneas adyacentes.")
    col1, col2 = st.columns(2)
    with col1:
        linea_out = st.selectbox("Línea que sale de servicio (N-1)",
                                 LINEAS_TRANSMISION["linea"].tolist(), index=0)
    with col2:
        carga_extra = st.slider("Carga adicional del sistema (%)", 0, 30, 10, 1,
                                help="Incremento de demanda sobre el escenario base")

    # Simulación simplificada: la línea que sale redistribuye su flujo entre paralelas
    linea_data = LINEAS_TRANSMISION[LINEAS_TRANSMISION["linea"] == linea_out].iloc[0]
    flujo_perdido = linea_data["flujo_pico_mw"] * (1 + carga_extra / 100)

    st.markdown(f"**Flujo redistribuido:** {flujo_perdido:.0f} MW "
                f"(línea {linea_out} con {linea_data['flujo_pico_mw']} MW × {1 + carga_extra/100:.0%})")

    # Buscar líneas paralelas (mismo de-a o mismo corredor)
    de, a = linea_data["de"], linea_data["a"]
    paralelas = LINEAS_TRANSMISION[
        ((LINEAS_TRANSMISION["de"] == de) & (LINEAS_TRANSMISION["a"] == a)) |
        ((LINEAS_TRANSMISION["de"] == a) & (LINEAS_TRANSMISION["a"] == de))
    ]
    paralelas = paralelas[paralelas["linea"] != linea_out]

    if len(paralelas) > 0:
        st.markdown("##### Líneas paralelas afectadas:")
        for _, pl in paralelas.iterrows():
            nuevo_flujo = pl["flujo_pico_mw"] + flujo_perdido / len(paralelas)
            nuevo_uso = nuevo_flujo / pl["capacidad_mw"] * 100
            color = "🔴" if nuevo_uso > 100 else "🟠" if nuevo_uso > 85 else "🟢"
            st.markdown(f"{color} **{pl['linea']}**: {pl['flujo_pico_mw']:.0f} → **{nuevo_flujo:.0f} MW** "
                        f"({nuevo_uso:.0f}% de {pl['capacidad_mw']} MW)")
    else:
        st.warning("No hay líneas paralelas directas. El flujo se redistribuye por todo el anillo, "
                   "afectando múltiples corredores.")

    # Proyectos de refuerzo
    st.markdown("---")
    st.markdown("#### 🏗️ Proyectos de Refuerzo de Transmisión")
    refuerzos = pd.DataFrame([
        {"proyecto": "Zhoray–Sinincay 230 kV (2do circuito)", "inversion_musd": 45,
         "estado": "En construcción", "entrada": "2025", "beneficio": "Alivia Yanacocha-Cuenca"},
        {"proyecto": "Chorrillos–Pasaje–Frontera 500 kV (EC-PE)", "inversion_musd": 278,
         "estado": "Licencia ambiental", "entrada": "2029", "beneficio": "600 MW interconexión Perú"},
        {"proyecto": "Santiago 500 kV (2,400 MW)", "inversion_musd": 516,
         "estado": "Planificación", "entrada": "2026-2028", "beneficio": "Refuerzo troncal 500 kV"},
        {"proyecto": "Nuevo corredor 230 kV Guayaquil", "inversion_musd": 120,
         "estado": "Estudio", "entrada": "2027-2028", "beneficio": "Alivia Trinitaria-Salitral-Pascuales"},
        {"proyecto": "Refuerzo CCS-El Inga (3er circuito)", "inversion_musd": 180,
         "estado": "Estudio", "entrada": "2028-2030", "beneficio": "Redundancia evacuación CCS"},
    ])
    st.dataframe(refuerzos, use_container_width=True, hide_index=True)
    _impact_box("Inversión total planificada: USD 1,139M en transmisión. "
                "Sin refuerzos, la congestión costará ~USD 28.6M/año al sistema. "
                "Payback de refuerzos: 4-8 años solo con ahorro por congestión.", "info")

TAB_FUNCTIONS = {
    "📊 Resumen Ejecutivo": render_tab_resumo,
    "⚡ Generación": render_tab_geracao,
    "🌊 Hidrología": render_tab_hidrologia,
    "📈 Carga (Tiempo Real)": render_tab_carga,
    "🔄 Intercambio": render_tab_intercambio,
    "🌪️ IBR (Eólica/Solar)": render_tab_ibr,
    "🚧 Racionamiento/Crisis": render_tab_racionamento,
    "🔴 Congestión/Flujos": render_tab_congestion,
    "📡 Sincrofasores/WAMS": render_tab_wams,
    "🧠 Estabilidad (Simuladores)": render_tab_estabilidad,
    "🔬 Clasificación Eventos": render_tab_eventos,
    "💰 Mercado": render_tab_mercado,
    "💰 Precios Nodales": render_tab_nodales,
    "🏭 Emisiones CO₂": render_tab_emissoes,
    "⚠️ Contingencias/SPS": render_tab_contingencias,
    "🔧 Torres/Rivera": render_tab_ferramentas,
}

def main():
    render_header()
    settings = sidebar_controls()
    tab_sel = st.selectbox("Navegación", list(TAB_FUNCTIONS.keys()), index=0)
    fn = TAB_FUNCTIONS[tab_sel]
    fn(settings)

    # Footer
    st.markdown("---")
    st.caption(
        "🇪🇨 Ecuador Energy Dashboard v1.0 · "
        "Colaboración: Torres Contreras (U. Cuenca) · Rivera (UNAL) · "
        "Fuentes: CENACE, ARCONEL, CELEC EP, datosabiertos.gob.ec"
    )

if __name__ == "__main__":
    main()
