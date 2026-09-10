# -*- coding: utf-8 -*-
"""
tools/live_panels.py — Paneles Streamlit con DATOS REALES para el Ecuador Energy Dashboard
=========================================================================================
Tres paneles "drop-in" (cada uno es una función que se llama dentro de una pestaña):

  panel_cenace_tiempo_real()   → pestaña 📈 Carga / 🏭 Generación / 📊 Resumen
  panel_embalses_celecsur()    → pestaña 🌊 Hidrología
  panel_intercambio_xm()       → pestaña 🔄 Intercambio

Reglas de coherencia (requisito del usuario: "SOLO mostrar resultados coherentes"):
  · Si la fuente falla → aviso explícito y NO se muestran números.
  · Balance CENACE: producción total ≈ demanda + exportación (tolerancia 8 %); si no, se avisa.
  · Cotas validadas por rango físico (Mazar 2 090–2 160 m; Amaluza 1 940–1 995 m).
  · Importación XM ≤ 550 MW (capacidad del enlace 230 kV Jamondino–Pomasqui).
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tools.cenace_client import fetch_cenace_realtime

COLORES = {"Hidráulica": "#2E86AB", "Térmica": "#C73E1D", "Renovable": "#3BB273",
           "Importación": "#7B2D8E", "Exportación": "#D4A373",
           "PRODUCCIÓN TOTAL": "#222222", "DEMANDA NACIONAL": "#003087"}


# ───────────────────────────── 1. CENACE tiempo real ──────────────────────────
def panel_cenace_tiempo_real(mostrar_curvas: bool = True, mostrar_distribuidoras: bool = True) -> dict:
    rt = fetch_cenace_realtime()
    st.markdown("#### 🛰️ CENACE — Información operativa en tiempo real (SCADA preliminar)")
    if not rt["ok"]:
        st.error(f"No fue posible leer CENACE ({rt['error']}). No se muestran valores para evitar datos ficticios.")
        return rt
    st.caption(f"Fuente: {rt['fuente']} · fecha página {rt['fecha_pagina']} · último dato {rt['hora_dato']} "
               f"· descargado {rt['timestamp'][:16]}")
    if rt["error"]:
        st.warning(f"⚠️ Chequeo de coherencia: {rt['error']} — se muestran los datos tal como los publica CENACE.")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Demanda nacional", f"{rt['demanda_mw']:,.0f} MW",
              delta=f"{rt['demanda_mw'] - rt['pico_ayer_mw']:+,.0f} vs pico ayer" if np.isfinite(rt['pico_ayer_mw']) else None,
              delta_color="inverse")
    c2.metric("Hidráulica", f"{rt['hidro_mw']:,.0f} MW", f"{rt['hidro_pct']} % de la producción")
    c3.metric("Térmica", f"{rt['termo_mw']:,.0f} MW")
    c4.metric("Renovable (eól+sol+bio)", f"{rt['renov_mw']:,.0f} MW")
    c5.metric("Importación Colombia", f"{rt['import_col_mw']:,.0f} MW",
              f"exporta {rt['export_mw']:,.0f} MW" if rt['export_mw'] > 0 else None)

    if mostrar_curvas and not rt["curva_hoy"].empty:
        tab_h, tab_a = st.tabs(["Hoy (30 min)", "Ayer (día completo)"])
        for tab, key, titulo in ((tab_h, "curva_hoy", "hoy"), (tab_a, "curva_ayer", "ayer")):
            df = rt[key]
            with tab:
                fig = go.Figure()
                for col in ["Hidráulica", "Térmica", "Renovable", "Importación"]:
                    if col in df:
                        fig.add_trace(go.Scatter(x=df.index, y=df[col], name=col, stackgroup="prod",
                                                 line=dict(width=0.5, color=COLORES.get(col))))
                if "DEMANDA NACIONAL" in df:
                    fig.add_trace(go.Scatter(x=df.index, y=df["DEMANDA NACIONAL"], name="Demanda nacional",
                                             line=dict(color=COLORES["DEMANDA NACIONAL"], width=2.5)))
                fig.update_layout(title=f"Producción por fuente y demanda — {titulo}", yaxis_title="MW",
                                  height=380, hovermode="x unified", legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig, use_container_width=True)
                d = df.get("DEMANDA NACIONAL", pd.Series(dtype=float)).dropna()
                if not d.empty:
                    st.caption(f"Pico {titulo}: **{d.max():,.0f} MW** a las {d.idxmax()} · mínimo {d.min():,.0f} MW a las {d.idxmin()} "
                               f"· energía {titulo}: {d.sum() / 2 / 1000:,.1f} GWh ({len(d)} medias horas)")

    ac = rt["acumulados"]
    if ac:
        st.markdown("##### Energía acumulada por fuente (como la publica CENACE)")
        filas = []
        for per, nom in (("hoy", "Hoy (parcial)"), ("ayer", "Ayer"), ("mes", "Mes en curso"), ("anio", "Año en curso")):
            if per in ac:
                d = ac[per]; tot = sum(v for k, v in d.items() if "EXPORT" not in k.upper())
                filas.append({"Período": nom, "Unidad": rt["unidades"][per],
                              **{k.title(): round(v, 1) for k, v in d.items()},
                              "Hidro %": round(100 * d.get("HIDROELÉCTRICA", 0) / tot, 1) if tot else np.nan})
        st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

    hp = rt["hidro_plantas"].get("ayer") or rt["hidro_plantas"].get("hoy")
    if hp:
        fig = go.Figure(go.Bar(x=list(hp.keys()), y=list(hp.values()), marker_color="#2E86AB",
                               text=[f"{v:,.0f}" for v in hp.values()], textposition="outside"))
        fig.update_layout(title="Producción hidroeléctrica por central — ayer (MWh)", height=330, yaxis_title="MWh")
        st.plotly_chart(fig, use_container_width=True)

    if mostrar_distribuidoras and not rt["distribuidoras"].empty:
        dd = rt["distribuidoras"]
        fig = go.Figure(go.Bar(y=dd["distribuidora"], x=dd["mw"], orientation="h", marker_color="#003087",
                               text=[f"{v:,.0f} MW" for v in dd["mw"]], textposition="outside"))
        fig.update_layout(title=f"Demanda por distribuidora (MW) — CNEL {rt['cnel_vs_ee'].get('CNEL', 0):,.0f} MW · "
                                f"EE {rt['cnel_vs_ee'].get('ELECTRICAS', 0):,.0f} MW",
                          height=520, yaxis=dict(autorange="reversed"), margin=dict(l=10, r=80))
        st.plotly_chart(fig, use_container_width=True)
    return rt


# ───────────────────────────── 2. CELEC Sur embalses ──────────────────────────
def panel_embalses_celecsur(dias_historico: int = 90) -> dict:
    from tools.celecsur_client import COTAS_REF, estado_embalses, serie_diaria, serie_horaria
    st.markdown("#### 🏞️ CELEC Sur — Cotas y caudales del Complejo Paute (API abierta, tiempo real)")
    try:
        e = estado_embalses()
    except Exception as ex:
        st.error(f"CELEC Sur no disponible: {ex}")
        return {"ok": False}
    if not e["ok"]:
        st.warning(f"Lectura parcial de CELEC Sur: {e.get('error')}")
    st.caption(f"Fuente: {e['fuente']} · último dato {e['ts']} (hora Ecuador)")

    ref = COTAS_REF["mazar"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cota Mazar", f"{e['cota_mazar']:.2f} m", f"{e['semaforo_mazar']} · llenado {e['llenado_mazar_pct']} %")
    c2.metric("Caudal ingreso Mazar", f"{e['caudal_mazar']:.1f} m³/s")
    c3.metric("Cota Amaluza (Molino)", f"{e['cota_amaluza']:.2f} m",
              f"máx {COTAS_REF['amaluza']['max_normal']:.0f} · mín {COTAS_REF['amaluza']['min_operativa']:.0f}")
    c4.metric("Caudal Amaluza", f"{e['caudal_amaluza']:.1f} m³/s")
    st.caption(f"Sopladora: cota {e['cota_sopladora']:.1f} m · {e['caudal_sopladora']:.0f} m³/s | "
               f"Minas San Francisco: cota {e['cota_minas_sf']:.1f} m · {e['caudal_minas_sf']:.0f} m³/s")

    desde = dt.date.today() - dt.timedelta(days=dias_historico)
    try:
        cm = serie_diaria("cota_mazar", desde)
        qm = serie_diaria("caudal_mazar", desde)
    except Exception as ex:
        st.warning(f"Sin histórico diario: {ex}")
        return e
    if not cm.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=cm["fecha_hora"], y=cm["cota_mazar"], name="Cota Mazar (media diaria)",
                                 line=dict(color="#2E86AB", width=3)))
        fig.add_hline(y=ref["max_normal"], line_dash="dot", line_color="green", annotation_text=f"Máx normal {ref['max_normal']:.0f} m")
        fig.add_hline(y=ref["critica_cortes"], line_dash="dash", line_color="orange", annotation_text=f"Crítica cortes {ref['critica_cortes']:.0f} m")
        fig.add_hline(y=ref["min_operativa"], line_dash="dash", line_color="red", annotation_text=f"Mín operativa {ref['min_operativa']:.0f} m")
        if not qm.empty:
            fig.add_trace(go.Bar(x=qm["fecha_hora"], y=qm["caudal_mazar"], name="Caudal ingreso (m³/s)",
                                 yaxis="y2", marker_color="rgba(59,178,115,0.45)"))
        fig.update_layout(title=f"Embalse Mazar — últimos {dias_historico} días", height=420,
                          yaxis=dict(title="m s.n.m.", range=[ref["min_operativa"] - 5, ref["max_normal"] + 5]),
                          yaxis2=dict(title="m³/s", overlaying="y", side="right", showgrid=False),
                          legend=dict(orientation="h", y=-0.2), hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        tasa = (cm["cota_mazar"].iloc[-1] - cm["cota_mazar"].iloc[max(0, len(cm) - 15)]) / 14
        dias_a_critica = (cm["cota_mazar"].iloc[-1] - ref["critica_cortes"]) / -tasa if tasa < 0 else np.inf
        msg = (f"Tendencia 14 días: **{tasa:+.2f} m/día**. "
               + (f"A este ritmo la cota crítica ({ref['critica_cortes']:.0f} m) se alcanzaría en ≈ **{dias_a_critica:.0f} días** "
                  f"({(dt.date.today() + dt.timedelta(days=int(dias_a_critica))):%d-%b-%Y}) si no cambian caudales ni despacho."
                  if np.isfinite(dias_a_critica) and dias_a_critica < 400 else "El embalse se mantiene o recupera."))
        (st.warning if tasa < -0.15 else st.info)(msg)
    return e


# ───────────────────────────── 3. XM intercambio Colombia ─────────────────────
def panel_intercambio_xm(dias: int = 30) -> dict:
    from tools.xm_client import fetch_tie_ecuador, resumen_tie
    st.markdown("#### 🇨🇴 XM (Colombia) — Transacciones internacionales por el enlace ECUADOR 230 kV")
    try:
        df = fetch_tie_ecuador(dias)
    except Exception as ex:
        st.error(f"API XM no disponible: {ex}")
        return {"ok": False}
    r = resumen_tie(df)
    if not r["ok"]:
        st.warning("XM no devolvió datos para el período.")
        return r
    if r["pico_import_mw"] > 550:
        st.warning("⚠️ Valor de importación supera la capacidad del enlace (≈525 MW): revisar unidades.")
    st.caption(f"Fuente: {r['fuente']} · {r['desde']} → {r['hasta']} (datos horarios en kWh convertidos a MW medios)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Importación EC ({dias} d)", f"{r['import_gwh']:,.1f} GWh")
    c2.metric("Exportación EC", f"{r['export_gwh']:,.2f} GWh")
    c3.metric("Pico horario importado", f"{r['pico_import_mw']:,.0f} MW")
    c4.metric("Horas con importación", f"{r['horas_import']} h")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["fecha_hora"], y=df["import_ec_mw"], name="Colombia → Ecuador",
                             fill="tozeroy", line=dict(color="#7B2D8E")))
    fig.add_trace(go.Scatter(x=df["fecha_hora"], y=-df["export_ec_mw"], name="Ecuador → Colombia",
                             fill="tozeroy", line=dict(color="#D4A373")))
    fig.add_hline(y=525, line_dash="dot", line_color="gray", annotation_text="Capacidad enlace ≈525 MW")
    fig.update_layout(title="Flujo horario por la interconexión (MW)", yaxis_title="MW", height=380,
                      hovermode="x unified", legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, use_container_width=True)
    diario = df.assign(dia=df["fecha_hora"].dt.date).groupby("dia")["import_ec_mw"].sum() / 1000
    st.bar_chart(diario.rename("GWh/día importados"), height=220)
    return r
