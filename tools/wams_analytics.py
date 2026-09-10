"""
Analítica WAMS/PMU y simuladores — Sistema Nacional Interconectado (SNI) de Ecuador
Basado en investigaciones de Torres Contreras (U. Cuenca) y Rueda Torres (TU Delft).
Simuladores: subfrecuencia, sobrefrecuencia, estabilidad de tensión, ENOS/drought.
"""
import pandas as pd
import numpy as np

# =============================================================================
# RED DE SINCRÓFASOS (PMU) — SNI Ecuador
# =============================================================================

PMU_NETWORK = {
    "PMUs instalados": 35,
    "PMUs planificados (2027)": 60,
    "Cobertura_actual": "500 kV + principales 230 kV",
    "Centro_control": "CENACE — CENACE Nacional (Quito)",
    "PDCs": ["PDC Principal Quito", "PDC Guayaquil", "PDC Cuenca"],
    "Tasa_muestreo": "60 muestras/s (clase M)",
    "estaciones": [
        {"nombre": "SE Pomasqui", "lat": 0.04, "lon": -78.46, "voltaje": "230/500 kV"},
        {"nombre": "SE El Inga", "lat": -0.24, "lon": -78.45, "voltaje": "230 kV"},
        {"nombre": "SE Santa Rosa", "lat": -0.30, "lon": -79.20, "voltaje": "230 kV"},
        {"nombre": "SE Milagro", "lat": -2.13, "lon": -79.59, "voltaje": "230 kV"},
        {"nombre": "SE Pascuales", "lat": -2.01, "lon": -79.93, "voltaje": "230 kV"},
        {"nombre": "SE Quevedo", "lat": -1.03, "lon": -79.46, "voltaje": "230 kV"},
        {"nombre": "SE Santo Domingo", "lat": -0.25, "lon": -79.17, "voltaje": "230 kV"},
        {"nombre": "SE Machala", "lat": -3.26, "lon": -79.96, "voltaje": "230 kV"},
        {"nombre": "SE Tisaleo", "lat": -1.27, "lon": -78.63, "voltaje": "230 kV"},
        {"nombre": "SE Molino", "lat": -2.88, "lon": -78.95, "voltaje": "230 kV"},
        {"nombre": "SE Zhoray", "lat": -2.92, "lon": -79.05, "voltaje": "230 kV"},
        {"nombre": "SE Coca Codo", "lat": 0.15, "lon": -77.45, "voltaje": "500 kV"},
    ],
}

# =============================================================================
# ALGORITMOS WAMS (Phasor Analytics)
# =============================================================================

ALGORITMOS_WAMS = [
    {"nombre": "DFT recursiva", "aplicacion": "Estimación de fasores en tiempo real",
     "ventaja": "Bajo costo computacional", "precision": "±0.05% TVE"},
    {"nombre": "TKEO (Teager-Kaiser)", "aplicacion": "Detección de eventos transitorios",
     "ventaja": "Sensibilidad a cambios bruscos", "precision": "<10 ms detección"},
    {"nombre": "Prony", "aplicacion": "Identificación de modos oscilatorios",
     "ventaja": "Alta resolución espectral", "precision": "±0.02 Hz"},
    {"nombre": "ERA (Eigensystem Realization)", "aplicacion": "Modelos de orden reducido",
     "ventaja": "Captura modos dominantes", "precision": "±5% amortiguamiento"},
    {"nombre": "Koopman/EDMD", "aplicacion": "Estimación dinámica de estado",
     "ventaja": "Linealización de sistemas no lineales", "precision": "Alta convergencia"},
    {"nombre": "1D-ConvLSTM", "aplicacion": "Detección SSO con deep learning",
     "ventaja": "Detección en multi-energía", "precision": "95%+ F1"},
]

# =============================================================================
# INERCIA DEL SISTEMA — Datos históricos y por zona
# =============================================================================

INERCIA_SNI = {
    "Norte (CCS+Agoyán)": {
        "H_sistema_s": 4.5, "H_minimo_s": 3.0,
        "capacidad_mw": 2200, "carga_mw": 1800,
        "IBR_pct_2026": 8
    },
    "Centro (Quito)": {
        "H_sistema_s": 4.0, "H_minimo_s": 2.5,
        "capacidad_mw": 1500, "carga_mw": 1600,
        "IBR_pct_2026": 5
    },
    "Sur (Paute Integral)": {
        "H_sistema_s": 3.2, "H_minimo_s": 2.0,
        "capacidad_mw": 2100, "carga_mw": 1200,
        "IBR_pct_2026": 3
    },
    "Costa (Guayaquil)": {
        "H_sistema_s": 3.8, "H_minimo_s": 2.5,
        "capacidad_mw": 1800, "carga_mw": 1800,
        "IBR_pct_2026": 12
    },
}

INERCIA_HISTORICA = pd.DataFrame([
    {"ano": 2015, "H_sistema_s": 5.8, "IBR_pct": 1, "hidro_pct": 85},
    {"ano": 2016, "H_sistema_s": 5.5, "IBR_pct": 1, "hidro_pct": 86},
    {"ano": 2017, "H_sistema_s": 5.3, "IBR_pct": 1, "hidro_pct": 88},
    {"ano": 2018, "H_sistema_s": 5.1, "IBR_pct": 1, "hidro_pct": 82},
    {"ano": 2019, "H_sistema_s": 5.0, "IBR_pct": 2, "hidro_pct": 83},
    {"ano": 2020, "H_sistema_s": 4.9, "IBR_pct": 2, "hidro_pct": 85},
    {"ano": 2021, "H_sistema_s": 4.8, "IBR_pct": 3, "hidro_pct": 88},
    {"ano": 2022, "H_sistema_s": 4.6, "IBR_pct": 4, "hidro_pct": 80},
    {"ano": 2023, "H_sistema_s": 4.5, "IBR_pct": 5, "hidro_pct": 77},
    {"ano": 2024, "H_sistema_s": 4.4, "IBR_pct": 5, "hidro_pct": 65},
    {"ano": 2025, "H_sistema_s": 4.3, "IBR_pct": 6, "hidro_pct": 79},
    {"ano": 2026, "H_sistema_s": 4.2, "IBR_pct": 7, "hidro_pct": 82},
])

# =============================================================================
# SIMULADORES
# =============================================================================

def simulate_frequency_event(perdida_mw: float, H_s: float,
                              carga_total_mw: float, droop: float = 0.05):
    """
    Simula evento de subfrecuencia o sobrefrecuencia en el SNI.
    Modelo swing simplificado: df/dt = (P_acc - D*f) / (2*H*S)

    Args:
        perdida_mw: MW perdidos (neg=sub, pos=over)
        H_s: Constante de inercia del sistema (segundos)
        carga_total_mw: Carga total del sistema (MW)
        droop: Regulación primaria (p.u.)

    Returns:
        (DataFrame con trayectoria f(t), dict de métricas)
    """
    f0 = 60.0
    dt = 0.05  # 50ms
    t_max = 30  # segundos
    pasos = int(t_max / dt)
    S_base = carga_total_mw

    P_deficit = -perdida_mw / S_base  # p.u.
    f = f0
    tiempos, freqs, rocofs = [], [], []

    for i in range(pasos):
        t = i * dt
        tiempos.append(t)
        freqs.append(f)

        df_pu = f / f0 - 1.0
        P_acc = P_deficit - droop * df_pu
        rocof = P_acc * f0 / (2 * H_s)
        rocofs.append(rocof)
        f = f + rocof * dt

        # UFLS/LSM activation
        if f < 59.3 and P_deficit < 0:
            P_deficit *= 0.7  # Shed 30%
        if f > 60.5 and P_deficit > 0:
            P_deficit *= 0.6  # Gen curtailment

    freq_arr = np.array(freqs)
    rocof_arr = np.array(rocofs)
    nadir = freq_arr.min() if perdida_mw > 0 else f0
    peak = freq_arr.max() if perdida_mw < 0 else f0
    rocof_max = abs(rocof_arr[0])

    df = pd.DataFrame({"t_s": tiempos, "f_hz": np.round(freq_arr, 4),
                        "rocof_hzs": np.round(rocof_arr, 4)})

    metrics = {
        "extreme_hz": round(nadir, 3) if perdida_mw > 0 else round(peak, 3),
        "rocof_max_hzs": round(rocof_max, 3),
        "nadir_s": round(tiempos[int(np.argmin(freq_arr))], 1),
        "tipo": "Subfrecuencia" if perdida_mw > 0 else "Sobrefrecuencia",
        "ufls_triggered": nadir < 59.5,
        "erac_activated": nadir < 59.3 or peak > 60.5,
    }
    return df, metrics


def simulate_voltage_stability(carga_pct: float, gen_disp_mw: float,
                                v_pu_inicial: float = 1.0):
    """
    Simulador de estabilidad de tensión (P-V curve simplificada).
    Basado en la metodología de Torres Contreras (margen de carga).

    Args:
        carga_pct: Porcentaje de carga del sistema (50-150%)
        gen_disp_mw: Generación disponible (MW)
        v_pu_inicial: Tensión inicial (p.u.)

    Returns:
        dict con resultados
    """
    P_max = gen_disp_mw * 1.15  # Punto de colapso (15% de margen de seguridad)
    P_carga = gen_disp_mw * carga_pct / 100

    # Curva P-V simplificada (nariz) - fórmula más realista
    P_range = np.linspace(0, P_max, 200)
    # Curva superior: V = V0 * sqrt(1 - 0.3*(P/Pmax)^2)
    V_upper = v_pu_inicial * np.sqrt(np.maximum(0, 1 - 0.3 * (P_range / P_max) ** 2))
    V_lower = v_pu_inicial * 0.4 * (P_range / P_max) ** 0.5

    # Margen de carga
    margen = max(0, (P_max - P_carga) / P_max * 100)
    # Tensión de operación más realista
    p_ratio = min(1.0, P_carga / P_max)
    V_operacion = v_pu_inicial * np.sqrt(max(0, 1 - 0.3 * p_ratio ** 2))

    colapso = V_operacion < 0.7 or margen < 5

    return {
        "P_carga_mw": round(P_carga, 0),
        "P_max_mw": round(P_max, 0),
        "margen_pct": round(margen, 1),
        "V_operacion_pu": round(V_operacion, 3),
        "colapso": colapso,
        "riesgo": "CRÍTICO" if margen < 10 else "ALTO" if margen < 20 else
                  "MEDIO" if margen < 35 else "BAJO",
        "P_curve": P_range,
        "V_upper": V_upper,
    }


def simulate_enos_drought(enos_type: str, hidro_pct: float,
                           demanda_mw: float, termo_disp_mw: float,
                           import_col_mw: float = 400):
    """
    Simulador de impacto ENOS (El Niño/La Niña) en el SNI de Ecuador.
    Modela el efecto de la sequía en la generación hidroeléctrica.

    Args:
        enos_type: "el_nino_fuerte", "el_nino_moderado", "neutral", "la_nina"
        hidro_pct: Porcentaje hidro en la matriz (%)
        demanda_mw: Demanda del sistema (MW)
        termo_disp_mw: Capacidad térmica disponible (MW)
        import_col_mw: Importación desde Colombia (MW)

    Returns:
        dict con resultados
    """
    # Factores de reducción hidro según ENOS
    factores = {
        "el_nino_fuerte": 0.55,
        "el_nino_moderado": 0.72,
        "neutral": 1.0,
        "la_nina": 1.10,
    }
    factor = factores.get(enos_type, 1.0)

    # Capacidad hidro efectiva
    cap_hidro_total = 5500  # MW aprox 2026
    gen_hidro_efectiva = cap_hidro_total * factor * 0.45  # FC promedio

    # Balance energético
    gen_total = gen_hidro_efectiva + termo_disp_mw * 0.7 + import_col_mw
    deficit = max(0, demanda_mw - gen_total)
    superavit = max(0, gen_total - demanda_mw)

    # Racionamiento estimado
    if deficit > 0:
        horas_corte = min(24, deficit / demanda_mw * 24 * 2.5)
    else:
        horas_corte = 0

    # Nivel embalse Mazar proyectado
    mazar_nivel = {
        "el_nino_fuerte": 35,
        "el_nino_moderado": 55,
        "neutral": 75,
        "la_nina": 90,
    }

    return {
        "gen_hidro_mw": round(gen_hidro_efectiva, 0),
        "gen_termo_mw": round(termo_disp_mw * 0.7, 0),
        "gen_import_mw": import_col_mw,
        "gen_total_mw": round(gen_total, 0),
        "demanda_mw": demanda_mw,
        "deficit_mw": round(deficit, 0),
        "superavit_mw": round(superavit, 0),
        "horas_corte": round(horas_corte, 1),
        "mazar_nivel_pct": mazar_nivel.get(enos_type, 70),
        "factor_hidro": factor,
        "riesgo": "CRÍTICO" if deficit > 500 else
                  "ALTO" if deficit > 200 else
                  "MEDIO" if deficit > 0 else "BAJO",
    }


def simulate_tnep_ac(nodos: int, lineas_candidatas: int,
                      ib_penetration: float, almacenamiento_mw: int = 0):
    """
    Simulador simplificado de TNEP AC (Torres Contreras methodology).
    Muestra el impacto de expansión de transmisión considerando modelo AC.

    Args:
        nodos: Número de nodos del sistema
        lineas_candidatas: Líneas candidatas a construir
        ib_penetration: Penetración de IBR (0-100%)
        almacenamiento_mw: Capacidad de BESS (MW)

    Returns:
        dict con resultados
    """
    # Simplificación del modelo AC TNEP
    congestiones_iniciales = max(0, int(nodos * 0.15 * (1 + ib_penetration/100)))
    perdidas_iniciales = 8.5 + ib_penetration * 0.05  # %

    # Efecto de líneas candidatas
    lineas_necesarias = min(lineas_candidatas,
                            int(congestiones_iniciales * 0.8 + 2))
    congestiones_post = max(0, congestiones_iniciales - int(lineas_necesarias * 0.7))
    perdidas_post = max(3.0, perdidas_iniciales - lineas_necesarias * 0.3)

    # Efecto de almacenamiento
    if almacenamiento_mw > 0:
        perdidas_post = max(2.5, perdidas_post - almacenamiento_mw * 0.002)
        congestiones_post = max(0, congestiones_post - int(almacenamiento_mw / 50))

    # Compensación reactiva necesaria
    comp_reactiva_mvar = int(ib_penetration * 2.5 + nodos * 0.5)

    # Inversión estimada (USD millones)
    inversion_lineas = lineas_necesarias * 45  # ~$45M por línea 230kV
    inversion_comp = comp_reactiva_mvar * 0.05  # ~$50k/MVAr
    inversion_bess = almacenamiento_mw * 0.35  # ~$350k/MW

    return {
        "congestiones_iniciales": congestiones_iniciales,
        "congestiones_post": congestiones_post,
        "perdidas_inicial_pct": round(perdidas_iniciales, 2),
        "perdidas_post_pct": round(perdidas_post, 2),
        "lineas_necesarias": lineas_necesarias,
        "comp_reactiva_mvar": comp_reactiva_mvar,
        "inversion_total_musd": round(inversion_lineas + inversion_comp + inversion_bess, 1),
        "inversion_lineas_musd": round(inversion_lineas, 1),
        "inversion_comp_musd": round(inversion_comp, 1),
        "inversion_bess_musd": round(inversion_bess, 1),
        "beneficio_congestion_pct": round(
            (1 - congestiones_post / max(1, congestiones_iniciales)) * 100, 1),
    }
