# -*- coding: utf-8 -*-
"""
tools/xm_client.py — Intercambio Colombia↔Ecuador desde la API abierta de XM (Colombia)
======================================================================================
XM (operador colombiano) publica sin clave, vía `pydataxm` (pip install pydataxm,
repo: https://github.com/EquipoAnaliticaXM/API_XM), las transacciones internacionales
de electricidad (TIE) por enlace. El enlace con Ecuador se llama "ECUADOR 230"
(Jamondino–Pomasqui 230 kV). Valores horarios en kWh; máx. 31 días por consulta.

  · ExpoEner / Enlace  → energía que Colombia exporta a Ecuador (= importación de Ecuador)
  · ImpoEner / Enlace  → energía que Colombia importa de Ecuador (= exportación de Ecuador)
  · ExportMonedaUSD / Sistema → valor USD de exportaciones (precio implícito)

Uso en la pestaña "Intercambio" del dashboard:
    df = fetch_tie_ecuador(dias=30)        # DataFrame horario MW (kWh/1000)
    resumen = resumen_tie(df)              # GWh import/export, pico MW, horas
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

try:
    import streamlit as st
    _cache = st.cache_data(ttl=3600, show_spinner=False)
except Exception:
    def _cache(f):
        return f

ENLACE_EC = "ECUADOR 230"


def _hourly_to_long(df: pd.DataFrame, nombre: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["fecha_hora", nombre])
    hcols = [c for c in df.columns if c.startswith("Values_Hour")]
    df = df[df["Values_code"].str.upper().str.contains("ECUADOR", na=False)]
    rows = []
    for _, r in df.iterrows():
        d = pd.to_datetime(r["Date"])
        for i, c in enumerate(hcols):
            v = pd.to_numeric(r[c], errors="coerce")
            rows.append((d + pd.Timedelta(hours=i), (v or 0.0) / 1000.0))  # kWh → MWh (=MW medio horario)
    return pd.DataFrame(rows, columns=["fecha_hora", nombre])


@_cache
def fetch_tie_ecuador(dias: int = 30, fin: dt.date | None = None) -> pd.DataFrame:
    """Devuelve DataFrame horario con columnas: fecha_hora, import_ec_mw, export_ec_mw, neto_mw.
    (import_ec = Colombia→Ecuador; export_ec = Ecuador→Colombia)."""
    try:
        from pydataxm.pydataxm import ReadDB
    except ImportError as e:
        raise RuntimeError("pip install pydataxm") from e
    fin = fin or (dt.date.today() - dt.timedelta(days=1))
    dias = max(1, min(int(dias), 31))
    ini = fin - dt.timedelta(days=dias - 1)
    api = ReadDB()
    exp_col = api.request_data("ExpoEner", "Enlace", ini, fin)   # Colombia exporta → EC importa
    imp_col = api.request_data("ImpoEner", "Enlace", ini, fin)   # Colombia importa → EC exporta
    a = _hourly_to_long(exp_col, "import_ec_mw")
    b = _hourly_to_long(imp_col, "export_ec_mw")
    out = a.merge(b, on="fecha_hora", how="outer").fillna(0.0).sort_values("fecha_hora")
    out["neto_mw"] = out["import_ec_mw"] - out["export_ec_mw"]
    return out.reset_index(drop=True)


def resumen_tie(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"ok": False}
    return {
        "ok": True,
        "import_gwh": round(df["import_ec_mw"].sum() / 1000, 2),
        "export_gwh": round(df["export_ec_mw"].sum() / 1000, 2),
        "pico_import_mw": round(df["import_ec_mw"].max(), 1),
        "horas_import": int((df["import_ec_mw"] > 1).sum()),
        "desde": str(df["fecha_hora"].min().date()), "hasta": str(df["fecha_hora"].max().date()),
        "fuente": "XM S.A. E.S.P. — API SINERGOX (pydataxm), enlace ECUADOR 230",
    }


if __name__ == "__main__":
    d = fetch_tie_ecuador(14)
    print(d.tail()); print(resumen_tie(d))
