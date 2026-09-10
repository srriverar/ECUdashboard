# -*- coding: utf-8 -*-
"""
tools/celecsur_client.py — Hidrología y producción del Complejo Paute (CELEC Sur) en tiempo real
===============================================================================================
CELEC EP Unidad de Negocio CELEC Sur publica una app Angular
(https://generacioncsr.celec.gob.ec/graficasproduccion/) alimentada por una API REST
Oracle ORDS **abierta, sin autenticación**:

    https://generacioncsr.celec.gob.ec:8443/ords/csr/sardomcsr/<recurso>

Recursos descubiertos en el bundle JS (main-es2015.*.js):
    pointValues            → serie horaria de un punto (mrid) entre fechaInicio/fechaFin
    pointValuesMesAvg      → promedio diario (por mes)      pointValuesMesH24 → 24 h por día
    pointValuesAnioAvg / AniosAvg / AnioH24 / AniosH24 → agregados anual / multianual
    csrEnerDia / csrEnerMes / csrEnerAnio / csrEnerAnios → energía producida por central
    csrCaudCuenMesAvg / AnioAvg / AniosAvg → caudales de cuenca

Puntos (mrid) verificados el 10-sep-2026 (valor → identificación por rango físico):
    COTA  : 30031 → Embalse Mazar (2 143 m s.n.m.; rango 2 098–2 153)
            24019 → Embalse Amaluza / Paute-Molino (1 985 m; rango 1 950–1 991)
            90919 → Embalse Sopladora (1 314 m)      650919 → Minas San Francisco (787 m)
    CAUDAL: 30538 → Ingreso a Mazar (85 m³/s)        24811 → Ingreso a Amaluza/Molino (174 m³/s)
            90537 → Sopladora (139 m³/s)             650538 → Minas San Francisco / Jubones (44 m³/s)
    Las marcas de tiempo son UTC ("Z"); Ecuador continental = UTC-5.

Cotas de referencia (CELEC/MEM 2024): Mazar mín. operativo 2 098 m (crítico cortes ≈2 115 m),
máx. normal 2 153 m; Amaluza mín. 1 950 m, máx. 1 991 m.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import streamlit as st
    _cache = st.cache_data(ttl=1800, show_spinner=False)
except Exception:
    def _cache(f):
        return f

BASE = "https://generacioncsr.celec.gob.ec:8443/ords/csr/sardomcsr"
PUNTOS = {
    "cota_mazar": 30031, "cota_amaluza": 24019, "cota_sopladora": 90919, "cota_minas_sf": 650919,
    "caudal_mazar": 30538, "caudal_amaluza": 24811, "caudal_sopladora": 90537, "caudal_minas_sf": 650538,
}
COTAS_REF = {
    "mazar": {"min_operativa": 2098.0, "critica_cortes": 2115.0, "max_normal": 2153.0, "vol_util_hm3": 310},
    "amaluza": {"min_operativa": 1950.0, "max_normal": 1991.0, "vol_util_hm3": 120},
}


def _get(recurso: str, **params) -> list[dict]:
    r = requests.get(f"{BASE}/{recurso}", params=params, timeout=30, verify=False,
                     headers={"User-Agent": "Mozilla/5.0 (EcuadorEnergyDashboard)"})
    r.raise_for_status()
    return r.json().get("items", [])


def _params(ini: dt.datetime, fin: dt.datetime, mrid: int | None = None) -> dict:
    p = {"fechaInicio": ini.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
         "fechaFin": fin.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
         "fecha": ini.strftime("%d/%m/%Y %H:%M:%S")}
    if mrid is not None:
        p["mrid"] = mrid
    return p


def _to_df(items: list[dict], nombre: str) -> pd.DataFrame:
    if not items:
        return pd.DataFrame(columns=["fecha_hora", nombre])
    df = pd.DataFrame(items).rename(columns={"loctimestamp": "fecha_hora", "valueedit": nombre})
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"], utc=True).dt.tz_convert("America/Guayaquil").dt.tz_localize(None)
    df[nombre] = pd.to_numeric(df[nombre], errors="coerce")
    return df.sort_values("fecha_hora").reset_index(drop=True)


@_cache
def serie_horaria(punto: str, dias: int = 7) -> pd.DataFrame:
    """Serie horaria de los últimos `dias` días de un punto de PUNTOS.
    `pointValues` devuelve las 24 h del día indicado en `fecha` (01:00→24:00 hora Ecuador,
    expresadas en UTC), así que se consulta día por día."""
    frames = []
    hoy = dt.date.today()
    for i in range(dias, -1, -1):
        d = hoy - dt.timedelta(days=i)
        ini = dt.datetime(d.year, d.month, d.day, 5)          # 00:00 Ecuador = 05:00Z
        fin = ini + dt.timedelta(days=1)
        try:
            frames.append(_to_df(_get("pointValues", **_params(ini, fin, PUNTOS[punto])), punto))
        except Exception:
            pass
    if not frames:
        return pd.DataFrame(columns=["fecha_hora", punto])
    return pd.concat(frames).drop_duplicates("fecha_hora").sort_values("fecha_hora").reset_index(drop=True)


@_cache
def serie_diaria(punto: str, desde: dt.date, hasta: dt.date | None = None) -> pd.DataFrame:
    """Promedios diarios (recurso pointValuesMesAvg, consultado mes a mes)."""
    hasta = hasta or dt.date.today()
    frames = []
    d = desde.replace(day=1)
    while d <= hasta:
        nxt = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        ini = dt.datetime(d.year, d.month, 1, 5)
        fin = dt.datetime(nxt.year, nxt.month, 1, 5)
        try:
            frames.append(_to_df(_get("pointValuesMesAvg", **_params(ini, fin, PUNTOS[punto])), punto))
        except Exception:
            pass
        d = nxt
    if not frames:
        return pd.DataFrame(columns=["fecha_hora", punto])
    out = pd.concat(frames).drop_duplicates("fecha_hora").sort_values("fecha_hora")
    out = out[(out["fecha_hora"].dt.date >= desde) & (out["fecha_hora"].dt.date <= hasta)]
    return out.reset_index(drop=True)


def estado_embalses() -> dict:
    """Último valor de cota/caudal de los 4 embalses + semáforo de Mazar (validado por rango)."""
    out = {"ok": True, "fuente": "CELEC Sur — API ORDS sardomcsr (SCADA, preliminar)", "ts": None}
    for k in PUNTOS:
        try:
            df = serie_horaria(k, 1).dropna()
            out[k] = float(df.iloc[-1, 1]) if not df.empty else float("nan")
            out["ts"] = str(df.iloc[-1, 0]) if not df.empty else out["ts"]
        except Exception as e:
            out[k] = float("nan"); out["ok"] = False; out["error"] = f"{type(e).__name__}: {e}"
    cm = out.get("cota_mazar", float("nan"))
    ref = COTAS_REF["mazar"]
    if not (2090 <= cm <= 2160):          # validación física
        out["semaforo_mazar"] = "sin dato válido"
        out["llenado_mazar_pct"] = float("nan")
    else:
        out["llenado_mazar_pct"] = round(100 * (cm - ref["min_operativa"]) / (ref["max_normal"] - ref["min_operativa"]), 1)
        out["semaforo_mazar"] = ("🟢 normal" if cm >= 2135 else "🟡 alerta" if cm >= ref["critica_cortes"] else "🔴 crítico")
    return out


if __name__ == "__main__":
    e = estado_embalses()
    for k, v in e.items():
        print(f"{k:20s}: {v}")
    d = serie_diaria("cota_mazar", dt.date(2026, 7, 1))
    print(d.tail(5))
