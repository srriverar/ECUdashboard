"""
Herramientas de modelo de red — Sistema Nacional Interconectado (SNI) de Ecuador
Datos basados en informes CENACE 2022-2026, ARCONEL, CELEC EP, Plan Maestro de Electricidad.
Fuentes: cenace.gob.ec, arconel.gob.ec, datosabiertos.gob.ec
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# =============================================================================
# DATOS DEL SISTEMA NACIONAL INTERCONECTADO (SNI)
# =============================================================================

# Capacidad instalada por año (MW) — Fuente: CENACE/ARCONEL
CAPACIDAD_POR_ANO = {
    2022: {"hidro": 5200, "termico": 3439, "eolica": 169, "solar": 30,
            "biomasa": 270, "biogas": 35, "importacion": 525, "total": 9668},
    2023: {"hidro": 5300, "termico": 3439, "eolica": 179, "solar": 41,
            "biomasa": 279, "biogas": 35, "importacion": 525, "total": 9898},
    2024: {"hidro": 5400, "termico": 3540, "eolica": 207, "solar": 41,
            "biomasa": 279, "biogas": 35, "importacion": 525, "total": 10027},
    2025: {"hidro": 5550, "termico": 3900, "eolica": 250, "solar": 80,
            "biomasa": 285, "biogas": 40, "importacion": 525, "total": 10630},
    2026: {"hidro": 5700, "termico": 4200, "eolica": 350, "solar": 200,
            "biomasa": 290, "biogas": 45, "importacion": 525, "total": 11310},
}

# Generación por fuente por año (GWh) — Fuente: CENACE Informes Anuales
GENERACION_POR_ANO = {
    2022: {"Hidro": 24100, "Termo": 4200, "Eólica": 380, "Solar": 45,
            "Biomasa": 550, "Biogás": 60, "Import_COL": 800, "Import_PER": 5,
            "Total": 30140},
    2023: {"Hidro": 23500, "Termo": 4800, "Eólica": 400, "Solar": 55,
            "Biomasa": 580, "Biogás": 65, "Import_COL": 1100, "Import_PER": 3,
            "Total": 30503},
    2024: {"Hidro": 22956, "Termo": 6643, "Eólica": 450, "Solar": 60,
            "Biomasa": 600, "Biogás": 70, "Import_COL": 1267, "Import_PER": 3,
            "Total": 32049},
    2025: {"Hidro": 25200, "Termo": 4500, "Eólica": 520, "Solar": 100,
            "Biomasa": 620, "Biogás": 75, "Import_COL": 900, "Import_PER": 5,
            "Total": 31920},
    2026: {"Hidro": 24800, "Termo": 4100, "Eólica": 680, "Solar": 250,
            "Biomasa": 640, "Biogás": 80, "Import_COL": 700, "Import_PER": 10,
            "Total": 31260},
}

# Demanda pico histórica (MW) — Fuente: CENACE
DEMANDA_PICO = {
    2022: 4500, 2023: 4800, 2024: 5063, 2025: 5110, 2026: 5250
}

# =============================================================================
# CENTRALES HIDROELÉCTRICAS PRINCIPALES
# =============================================================================

CENTRALES_HIDRO = pd.DataFrame([
    {"central": "Coca Codo Sinclair", "potencia_mw": 1500, "rio": "Coca",
     "provincia": "Napo/Sucumbíos", "ano": 2016, "operador": "CELEC EP",
     "tipo": "Fil de agua", "aporte_pct": 31.7},
    {"central": "Paute-Molino", "potencia_mw": 1100, "rio": "Paute",
     "provincia": "Azuay", "ano": 1983, "operador": "CELEC EP",
     "tipo": "Embalse", "aporte_pct": 16.7},
    {"central": "Sopladora", "potencia_mw": 487, "rio": "Paute",
     "provincia": "Azuay", "ano": 2016, "operador": "CELEC EP",
     "tipo": "Embalse", "aporte_pct": 8.5},
    {"central": "Minas San Francisco", "potencia_mw": 270, "rio": "Jubones",
     "provincia": "Azuay/El Oro", "ano": 2018, "operador": "CELEC EP",
     "tipo": "Fil de agua", "aporte_pct": 4.7},
    {"central": "Mazar", "potencia_mw": 170, "rio": "Paute",
     "provincia": "Azuay", "ano": 1990, "operador": "CELEC EP",
     "tipo": "Embalse regulador", "aporte_pct": 3.0},
    {"central": "Delsitanisagua", "potencia_mw": 176, "rio": "Zamora",
     "provincia": "Zamora Chinchipe", "ano": 2017, "operador": "CELEC EP",
     "tipo": "Fil de agua", "aporte_pct": 3.1},
    {"central": "Agoyán", "potencia_mw": 156, "rio": "Pastaza",
     "provincia": "Pastaza", "ano": 1988, "operador": "CELEC EP",
     "tipo": "Fil de agua", "aporte_pct": 2.7},
    {"central": "San Francisco", "potencia_mw": 212, "rio": "Pastaza",
     "provincia": "Pastaza", "ano": 2008, "operador": "CELEC EP",
     "tipo": "Fil de agua", "aporte_pct": 3.7},
    {"central": "Manduriacu", "potencia_mw": 55, "rio": "Guayllabamba",
     "provincia": "Imbabura", "ano": 2018, "operador": "CELEC EP",
     "tipo": "Fil de agua", "aporte_pct": 1.0},
    {"central": "Toachi-Pilatón", "potencia_mw": 254, "rio": "Toachi",
     "provincia": "Santo Domingo/Pichincha", "ano": 2022, "operador": "CELEC EP",
     "tipo": "Embalse", "aporte_pct": 4.4},
    {"central": "Marcel Laniado (Daule Peripa)", "potencia_mw": 213, "rio": "Daule",
     "provincia": "Manabí", "ano": 1988, "operador": "CELEC EP",
     "tipo": "Embalse", "aporte_pct": 3.7},
    {"central": "Baba", "potencia_mw": 42, "rio": "Baba",
     "provincia": "Los Ríos", "ano": 2019, "operador": "CELEC EP",
     "tipo": "Fil de agua", "aporte_pct": 0.7},
    {"central": "Cumbayá", "potencia_mw": 20, "rio": "San Pedro",
     "provincia": "Pichincha", "ano": 1958, "operador": "EEQ",
     "tipo": "Fil de agua", "aporte_pct": 0.3},
])

# =============================================================================
# CENTRALES TÉRMICAS PRINCIPALES
# =============================================================================

CENTRALES_TERMICAS = pd.DataFrame([
    {"central": "Esmeraldas I", "potencia_mw": 158, "combustible": "Fuel Oil",
     "provincia": "Esmeraldas", "estado": "Operativa"},
    {"central": "Esmeraldas II (Termoesmeraldas)", "potencia_mw": 234, "combustible": "Fuel Oil",
     "provincia": "Esmeraldas", "estado": "Operativa"},
    {"central": "G. G. de Coca", "potencia_mw": 180, "combustible": "Diésel",
     "provincia": "Sucumbíos", "estado": "Operativa"},
    {"central": "Troncal", "potencia_mw": 100, "combustible": "Diésel",
     "provincia": "Azuay", "estado": "Operativa"},
    {"central": "Pascuales (barcaza)", "potencia_mw": 100, "combustible": "Fuel Oil",
     "provincia": "Guayas", "estado": "Operativa"},
    {"central": "Cevallos", "potencia_mw": 98, "combustible": "Fuel Oil",
     "provincia": "Manabí", "estado": "Parcial"},
    {"central": "G. G. Jaramijó", "potencia_mw": 180, "combustible": "Gas Natural",
     "provincia": "Manabí", "estado": "Operativa"},
    {"central": "Progen (Guayaquil)", "potencia_mw": 150, "combustible": "Gas Natural",
     "provincia": "Guayas", "estado": "En pruebas"},
    {"central": "Nobis (barcaza)", "potencia_mw": 100, "combustible": "Fuel Oil",
     "provincia": "Guayas", "estado": "Operativa"},
])

# =============================================================================
# EMBALSES PRINCIPALES
# =============================================================================

EMBALSES = {
    "Mazar": {
        "cota_min": 2098.0, "cota_max": 2153.0,
        "capacidad_mwh": 450000, "central": "Paute Integral",
        "niveles_historicos": {2022: 85, 2023: 72, 2024: 38, 2025: 68, 2026: 74}
    },
    "Paute (Molino)": {
        "cota_min": 1640.0, "cota_max": 1715.0,
        "capacidad_mwh": 280000, "central": "Paute Integral",
        "niveles_historicos": {2022: 82, 2023: 65, 2024: 42, 2025: 70, 2026: 76}
    },
    "Daule Peripa": {
        "cota_min": 105.0, "cota_max": 140.0,
        "capacidad_mwh": 120000, "central": "Marcel Laniado de Wind",
        "niveles_historicos": {2022: 78, 2023: 60, 2024: 45, 2025: 65, 2026: 72}
    },
    "Sopladora": {
        "cota_min": 1580.0, "cota_max": 1680.0,
        "capacidad_mwh": 150000, "central": "Sopladora",
        "niveles_historicos": {2022: 80, 2023: 68, 2024: 40, 2025: 72, 2026: 78}
    },
}

# =============================================================================
# INTERCONEXIONES INTERNACIONALES
# =============================================================================

INTERCONEXIONES = {
    "EC-CO (230kV)": {
        "pais": "Colombia", "voltaje": "230 kV", "capacidad_mw": 525,
        "lineas": "Pomasqui-Jamondino (doble circuito)",
        "tipo": "AC", "estado": "Operativa",
        "flujo_historico": {2022: 800, 2023: 1100, 2024: 1267, 2025: 900, 2026: 700}
    },
    "EC-PE (230kV)": {
        "pais": "Perú", "voltaje": "230 kV", "capacidad_mw": 110,
        "lineas": "Machala-Zorritos",
        "tipo": "AC", "estado": "Operativa",
        "flujo_historico": {2022: 5, 2023: 3, 2024: 3, 2025: 5, 2026: 10}
    },
    "EC-PE (500kV)": {
        "pais": "Perú", "voltaje": "500 kV", "capacidad_mw": 600,
        "lineas": "Chorrillos-Pasaje-Frontera (284 km EC)",
        "tipo": "AC", "estado": "En construcción (2029)",
        "flujo_historico": {2022: 0, 2023: 0, 2024: 0, 2025: 0, 2026: 0}
    },
}

# =============================================================================
# TRANSMISIÓN
# =============================================================================

TRANSMISION = {
    "500 kV": {"km": 461, "subestaciones": 5},
    "230 kV": {"km": 3016, "subestaciones": 42},
    "138 kV": {"km": 2189, "subestaciones": 28},
    "total_km": 5666,
    "total_subestaciones": 75,
}

# =============================================================================
# RENOVABLES NO CONVENCIONALES (IBR)
# =============================================================================

PROYECTOS_IBR = pd.DataFrame([
    {"proyecto": "Parque Eólico Villonaco", "tipo": "Eólica", "potencia_mw": 16.5,
     "provincia": "Loja", "ano": 2017, "estado": "Operativo"},
    {"proyecto": "Parque Eólico Minas (Fase I)", "tipo": "Eólica", "potencia_mw": 39.6,
     "provincia": "Loja", "ano": 2023, "estado": "Operativo"},
    {"proyecto": "Parque Eólico Minas (Fase II)", "tipo": "Eólica", "potencia_mw": 50.0,
     "provincia": "Loja", "ano": 2024, "estado": "Operativo"},
    {"proyecto": "Parque Eólico Chiriboga", "tipo": "Eólica", "potencia_mw": 49.5,
     "provincia": "Pichincha", "ano": 2025, "estado": "En construcción"},
    {"proyecto": "Parque Solar El Aromo", "tipo": "Solar", "potencia_mw": 200.0,
     "provincia": "Manabí", "ano": 2025, "estado": "En construcción"},
    {"proyecto": "Parque Solar La Trinidad", "tipo": "Solar", "potencia_mw": 50.0,
     "provincia": "Imbabura", "ano": 2024, "estado": "Operativo"},
    {"proyecto": "Parque Solar Jaramijó", "tipo": "Solar", "potencia_mw": 50.0,
     "provincia": "Manabí", "ano": 2025, "estado": "En pruebas"},
    {"proyecto": "Parque Eólico Saraguro", "tipo": "Eólica", "potencia_mw": 30.0,
     "provincia": "Loja", "ano": 2026, "estado": "Proyectado"},
])

# =============================================================================
# ACTORES DEL SECTOR ELÉCTRICO
# =============================================================================

ACTORES = {
    "CENACE": {
        "rol": "Operador Nacional de Electricidad",
        "funcion": "Despacho, operación del SNI, planificación operativa",
        "url": "https://www.cenace.gob.ec"
    },
    "ARCONEL": {
        "rol": "Agencia de Regulación y Control de Electricidad",
        "funcion": "Regulación, tarifas, control, normativa",
        "url": "https://arconel.gob.ec"
    },
    "CELEC EP": {
        "rol": "Corporación Eléctrica del Ecuador",
        "funcion": "Generación hidroeléctrica y térmica pública, transmisión",
        "url": "https://www.celec.gob.ec"
    },
    "CNEL EP": {
        "rol": "Corporación Nacional de Electricidad",
        "funcion": "Distribución (8 unidades de negocio)",
        "url": "https://www.cnelep.gob.ec"
    },
    "EEQ": {
        "rol": "Empresa Eléctrica Quito",
        "funcion": "Distribución DMQ y valles",
        "url": "https://www.eeq.com.ec"
    },
    "Transelectric": {
        "rol": "Empresa de Transmisión",
        "funcion": "Operación del SNT (230/500 kV)",
        "url": "https://www.transelectric.com.ec"
    },
}

# =============================================================================
# EMPRESAS DISTRIBUIDORAS
# =============================================================================

DISTRIBUIDORAS = pd.DataFrame([
    {"empresa": "CNEL Manabí", "provincias": "Manabí", "clientes_miles": 410},
    {"empresa": "CNEL Guayas-Los Ríos", "provincias": "Guayas, Los Ríos", "clientes_miles": 1050},
    {"empresa": "CNEL El Oro", "provincias": "El Oro", "clientes_miles": 180},
    {"empresa": "CNEL Santo Domingo", "provincias": "Santo Domingo de los Tsáchilas", "clientes_miles": 130},
    {"empresa": "CNEL Bolívar", "provincias": "Bolívar", "clientes_miles": 60},
    {"empresa": "CNEL Chimborazo", "provincias": "Chimborazo", "clientes_miles": 110},
    {"empresa": "CNEL Tungurahua", "provincias": "Tungurahua", "clientes_miles": 150},
    {"empresa": "CNEL Ambato", "provincias": "Cotopaxi, Pastaza", "clientes_miles": 120},
    {"empresa": "EEQ", "provincias": "Pichincha (DMQ)", "clientes_miles": 820},
    {"empresa": "EMELNORTE", "provincias": "Imbabura, Carchi, Esmeraldas, Sucumbíos", "clientes_miles": 350},
    {"empresa": "EMELSUR (CENEL)", "provincias": "Loja, Zamora, Azuay, Cañar, Morona", "clientes_miles": 340},
    {"empresa": "EMASE", "provincias": "Azuay (Cuenca)", "clientes_miles": 190},
])

# =============================================================================
# CRISIS ENERGÉTICA 2024 — DATOS CLAVE
# =============================================================================

CRISIS_2024 = {
    "causa": "Sequía severa + El Niño + infraestructura insuficiente",
    "inicio": "Septiembre 2024",
    "fin_racionamiento": "Febrero 2025",
    "racionamiento_max": "14 horas/día",
    "deficit_mw": 1080,
    "hidro_min_pct": 49,
    "hidro_normal_pct": 82,
    "mazar_cota_min_alcanzada": 2102,
    "colombia_corte_exportaciones": "Abril 2024 (racionamiento propio)",
    "termica_disponible": 853,
    "termica_instalada": 3439,
    "eventos": [
        {"fecha": "2024-09-27", "evento": "Inicio racionamiento oficial",
         "detalle": "Gobierno Lasso/Noboa implementa cortes 3-4h diarias"},
        {"fecha": "2024-10-15", "evento": "Racionamiento extendido a 8h",
         "detalle": "Déficit supera 1,000 MW, cortes 8h/día en provincias"},
        {"fecha": "2024-11-01", "evento": "Racionamiento máximo 14h",
         "detalle": "Hidro baja a 49%, térmicas no cubren déficit"},
        {"fecha": "2024-11-15", "evento": "Mazar en cota crítica",
         "detalle": "Cota 2110.62 m (min 2098), operación intermitente"},
        {"fecha": "2024-12-15", "evento": "Lluvias mejoran situación",
         "detalle": "Generación hidro sube a 61%, se reducen cortes"},
        {"fecha": "2025-01-01", "evento": "Recuperación parcial",
         "detalle": "Hidro 91%, gobierno anuncia fin de apagones"},
        {"fecha": "2025-05-07", "evento": "Récord demanda 5,110 MW",
         "detalle": "Demanda pico histórica, cubierta 90% con hidro"},
    ]
}

# =============================================================================
# EMISIONES DE CO2
# =============================================================================

EMISIONES_HISTORICA = pd.DataFrame([
    {"ano": 2018, "co2_mtcO2": 5.2, "intensidad_gkwh": 208, "hidro_pct": 82},
    {"ano": 2019, "co2_mtcO2": 4.8, "intensidad_gkwh": 192, "hidro_pct": 83},
    {"ano": 2020, "co2_mtcO2": 4.1, "intensidad_gkwh": 178, "hidro_pct": 85},
    {"ano": 2021, "co2_mtcO2": 3.5, "intensidad_gkwh": 152, "hidro_pct": 88},
    {"ano": 2022, "co2_mtcO2": 4.0, "intensidad_gkwh": 165, "hidro_pct": 80},
    {"ano": 2023, "co2_mtcO2": 4.5, "intensidad_gkwh": 185, "hidro_pct": 77},
    {"ano": 2024, "co2_mtcO2": 6.2, "intensidad_gkwh": 252, "hidro_pct": 65},
    {"ano": 2025, "co2_mtcO2": 4.2, "intensidad_gkwh": 170, "hidro_pct": 79},
    {"ano": 2026, "co2_mtcO2": 3.8, "intensidad_gkwh": 155, "hidro_pct": 82},
])

# =============================================================================
# PRECIOS Y MERCADO
# =============================================================================

PRECIOS_HISTORICOS = pd.DataFrame([
    {"ano": 2022, "precio_promedio_usd_mwh": 52, "tarifa_residencial": 0.09,
     "tarifa_comercial": 0.11, "tarifa_industrial": 0.08},
    {"ano": 2023, "precio_promedio_usd_mwh": 58, "tarifa_residencial": 0.09,
     "tarifa_comercial": 0.11, "tarifa_industrial": 0.08},
    {"ano": 2024, "precio_promedio_usd_mwh": 78, "tarifa_residencial": 0.10,
     "tarifa_comercial": 0.12, "tarifa_industrial": 0.09},
    {"ano": 2025, "precio_promedio_usd_mwh": 62, "tarifa_residencial": 0.10,
     "tarifa_comercial": 0.12, "tarifa_industrial": 0.09},
    {"ano": 2026, "precio_promedio_usd_mwh": 55, "tarifa_residencial": 0.10,
     "tarifa_comercial": 0.12, "tarifa_industrial": 0.09},
])

# =============================================================================
# FACTORES DE CAPACIDAD
# =============================================================================

FACTORES_CAPACIDAD = {
    "Hidro (embalse)": {"fc_anual": 0.45, "fc_pico": 0.85},
    "Hidro (fil de agua)": {"fc_anual": 0.55, "fc_pico": 0.70},
    "Coca Codo Sinclair": {"fc_anual": 0.52, "fc_pico": 0.90},
    "Paute Integral": {"fc_anual": 0.38, "fc_pico": 0.80},
    "Termo (gas)": {"fc_anual": 0.25, "fc_pico": 0.95},
    "Termo (fuel oil)": {"fc_anual": 0.20, "fc_pico": 0.90},
    "Eólica": {"fc_anual": 0.28, "fc_pico": 0.75},
    "Solar": {"fc_anual": 0.18, "fc_pico": 0.85},
    "Biomasa/Bagazo": {"fc_anual": 0.55, "fc_pico": 0.80},
}

# =============================================================================
# OSCILACIONES ELECTROMECÁNICAS (SNI Ecuador)
# =============================================================================

MODOS_OSCILACION = pd.DataFrame([
    {"modo": "Inter-área Norte-Sur", "frecuencia_hz": 0.55, "amortiguamiento": 0.04,
     "descripcion": "Oscilación entre generación norte (CCS, Agoyán) y carga sur (Paute)",
     "riesgo": "Medio"},
    {"modo": "Local CCS", "frecuencia_hz": 1.2, "amortiguamiento": 0.06,
     "descripcion": "Modo local de la zona Coca Codo Sinclair - Quito",
     "riesgo": "Bajo"},
    {"modo": "Inter-área EC-CO", "frecuencia_hz": 0.35, "amortiguamiento": 0.03,
     "descripcion": "Oscilación interconexión Ecuador-Colombia",
     "riesgo": "Alto"},
    {"modo": "Local Paute", "frecuencia_hz": 0.9, "amortiguamiento": 0.05,
     "descripcion": "Modo local del Complejo Paute Integral",
     "riesgo": "Medio"},
])

# =============================================================================
# FUENTES DE DATOS
# =============================================================================

FONTES_DADOS = {
    "CENACE — Operador Nacional": "https://www.cenace.gob.ec",
    "ARCONEL — Regulador": "https://arconel.gob.ec",
    "CELEC EP — Generadora": "https://www.celec.gob.ec",
    "Datos Abiertos Ecuador": "https://datosabiertos.gob.ec/dataset/?organization=cenace",
    "CENACE — Info Operativa RT": "http://www.cenace.org.ec/docs/InformacionOperativa.htm",
    "INEC — Estadísticas Eléctricas": "https://anda.inec.gob.ec",
    "Min. Ambiente y Energía": "https://www.ambienteyenergia.gob.ec",
    "Nature Energy — VRE Ecuador": "https://www.nature.com/articles/s44221-026-00617-w",
    "Revista Energía CENACE": "https://revistaenergia.cenace.gob.ec",
    "Transelectric": "https://www.celec.gob.ec/transelectric",
}

# =============================================================================
# CONTINGENCIAS Y PROTECCIÓN SISTÉMICA (SPS)
# =============================================================================

SPS_INFO = {
    "implementacion": "Marzo 2015",
    "funcion": "Detectar contingencias críticas predefinidas y ejecutar acciones remediales "
               "automáticas para evitar colapso total o parcial del SNI",
    "criterios": [
        "Salida intempestiva de un circuito del anillo de 230 kV",
        "Salida de los dos circuitos de una línea de 230 kV (N-2)",
        "Falla de barras de subestaciones críticas",
        "Salida de grandes centrales de generación",
        "Pérdida de interconexión internacional",
    ],
    "tiempo_actuacion": "< 100 ms (ciclo de protección)",
    "monitoreo": "Datos de corriente, voltaje y estado de interruptores cada 1 segundo",
    "centro_control": "CENACE — Centro Nacional de Control de Energía (Quito)",
}

CONTINGENCIAS_CRITICAS = pd.DataFrame([
    {"id": "C-001", "tipo": "N-2", "elemento": "L/T Santa Rosa – Totoras 230 kV (doble circuito)",
     "zona": "Guayas", "consecuencia": "Inestabilidad angular, sobrecargas en anillo 230 kV",
     "accion_remedial": "Desconexión de carga 150-300 MW en zona Guayas",
     "riesgo": "ALTO", "SPS": "Sí"},
    {"id": "C-002", "tipo": "N-2", "elemento": "L/T Pomasqui – Jamondino 230 kV (doble circuito, interconexión CO)",
     "zona": "Carchi/Frontera", "consecuencia": "Separación de sistemas EC-CO, oscilación de potencia",
     "accion_remedial": "Rechazo generación CCS + desconexión carga norte",
     "riesgo": "ALTO", "SPS": "Sí"},
    {"id": "C-003", "tipo": "N-1", "elemento": "L/T El Inga – Tisaleo 500 kV",
     "zona": "Pichincha/Cotopaxi", "consecuencia": "Sobrecarga anillo 230 kV norte, bajo voltaje Quito",
     "accion_remedial": "Desconexión de carga DMQ 100-200 MW",
     "riesgo": "ALTO", "SPS": "Sí"},
    {"id": "C-004", "tipo": "N-1", "elemento": "ATK Dos Cerritos 230/138 kV",
     "zona": "Guayas", "consecuencia": "Pérdida 57 MW + sobrecarga Pascuales-Chongón",
     "accion_remedial": "Generación forzada Santa Elena II/III",
     "riesgo": "MEDIO", "SPS": "Sí"},
    {"id": "C-005", "tipo": "N-2", "elemento": "L/T Santo Domingo – Quevedo + Baba 230 kV",
     "zona": "Santo Domingo/Los Ríos", "consecuencia": "Inestabilidad CCS + Toachi Pilatón",
     "accion_remedial": "Rechazo generación CCS 400-600 MW",
     "riesgo": "CRÍTICO", "SPS": "Sí"},
    {"id": "C-006", "tipo": "N-1", "elemento": "L/T San Gregorio – Quevedo 230 kV",
     "zona": "Los Ríos", "consecuencia": "Voltajes por debajo del límite de emergencia",
     "accion_remedial": "Desconexión de carga por bajo voltaje zona Quevedo",
     "riesgo": "MEDIO", "SPS": "Sí"},
    {"id": "C-007", "tipo": "N-1", "elemento": "L/T Yanacocha – Cuenca 138 kV (circuito)",
     "zona": "Azuay", "consecuencia": "Sobrecarga >120% del circuito restante",
     "accion_remedial": "Generación forzada en zona sur + reducción de demanda Cuenca",
     "riesgo": "ALTO", "SPS": "Pendiente"},
    {"id": "C-008", "tipo": "N-1", "elemento": "L/T Trinitaria – Salitral – Pascuales 138 kV",
     "zona": "Guayas", "consecuencia": "Corredor más crítico: sobrecarga y bajo voltaje Guayaquil",
     "accion_remedial": "Corte de carga rotativo Guayaquil 200-400 MW",
     "riesgo": "CRÍTICO", "SPS": "Sí"},
    {"id": "C-009", "tipo": "N-2", "elemento": "Salida coincidente Agoyán + San Francisco",
     "zona": "Pastaza/Oriente", "consecuencia": "Colapso nororiental, pérdida 368 MW",
     "accion_remedial": "Activación emergencia térmica + importación Colombia",
     "riesgo": "CRÍTICO", "SPS": "Parcial"},
    {"id": "C-010", "tipo": "N-1", "elemento": "Central CCS (1,500 MW) — pérdida total",
     "zona": "Napo/Sucumbíos", "consecuencia": "Déficit 30% del sistema, UFLS activado",
     "accion_remedial": "UFLS + ERAC + despacho térmico emergencia",
     "riesgo": "CRÍTICO", "SPS": "Sí"},
])

SUBESTACIONES_CRITICAS = pd.DataFrame([
    {"subestacion": "SE Pascuales", "voltaje": "230/138/69 kV", "zona": "Guayaquil",
     "trafo_reserva": "No", "riesgo": "CRÍTICO",
     "detalle": "Alimenta 30% de carga Guayaquil. Sin redundancia."},
    {"subestacion": "SE Trinitaria", "voltaje": "230/138 kV", "zona": "Guayaquil Sur",
     "trafo_reserva": "No", "riesgo": "CRÍTICO",
     "detalle": "Corredor Trinitaria-Salitral-Pascuales: punto más débil del SNI."},
    {"subestacion": "SE Salitral", "voltaje": "230/138 kV", "zona": "Guayaquil Centro",
     "trafo_reserva": "No", "riesgo": "ALTO",
     "detalle": "Enlace débil del corredor crítico. Sobrecarga en N-1."},
    {"subestacion": "SE Dos Cerritos", "voltaje": "230/138/69 kV", "zona": "Guayas",
     "trafo_reserva": "Parcial", "riesgo": "ALTO",
     "detalle": "ATK sin reserva completa. Falla provoca pérdida de 57 MW."},
    {"subestacion": "SE El Inga", "voltaje": "230/500 kV", "zona": "Pichincha (Quito)",
     "trafo_reserva": "Sí (500kV)", "riesgo": "MEDIO",
     "detalle": "Cabecera del troncal 500 kV. Redundante con Tisaleo."},
    {"subestacion": "SE Pomasqui", "voltaje": "230/500 kV", "zona": "Pichincha",
     "trafo_reserva": "Sí", "riesgo": "MEDIO",
     "detalle": "Interconexión Colombia. Doble circuito con Jamondino."},
    {"subestacion": "SE Santa Rosa", "voltaje": "230/138 kV", "zona": "El Oro",
     "trafo_reserva": "No", "riesgo": "ALTO",
     "detalle": "Contingencia N-2 más crítica antes del 500 kV con Perú."},
    {"subestacion": "SE Tisaleo", "voltaje": "500/230 kV", "zona": "Cotopaxi",
     "trafo_reserva": "Sí", "riesgo": "BAJO",
     "detalle": "Punto central del troncal 500 kV. Bien redundada."},
    {"subestacion": "SE Chorrillos", "voltaje": "500/230 kV", "zona": "Guayas (Guayaquil)",
     "trafo_reserva": "Sí", "riesgo": "MEDIO",
     "detalle": "Cabecera futura interconexión 500 kV con Perú (2029)."},
    {"subestacion": "SE Molino", "voltaje": "230/138 kV", "zona": "Azuay",
     "trafo_reserva": "No", "riesgo": "ALTO",
     "detalle": "Evacuación del Complejo Paute. Sin redundancia ante N-1."},
    {"subestacion": "SE Zhoray", "voltaje": "230/138 kV", "zona": "Azuay (Cuenca)",
     "trafo_reserva": "Parcial", "riesgo": "MEDIO",
     "detalle": "2do circuito Zhoray-Sinincay en construcción (2025)."},
    {"subestacion": "SE Machala", "voltaje": "230/138 kV", "zona": "El Oro",
     "trafo_reserva": "No", "riesgo": "ALTO",
     "detalle": "Interconexión actual con Perú (110 MW). Sin redundancia."},
])

RIESGOS_OPERATIVOS_2026 = pd.DataFrame([
    {"riesgo": "Corredor Trinitaria-Salitral-Pascuales 138 kV",
     "zona": "Guayaquil", "nivel": "CRÍTICO",
     "descripcion": "Zona más crítica del SNI. Sin mantenimiento posible sin desconectar carga.",
     "impacto": "Cualquier falla → apagones Guayaquil 2-4 horas"},
    {"riesgo": "Salida coincidente centrales Esclusas-Trinitaria-Salitral",
     "zona": "Guayas", "nivel": "CRÍTICO",
     "descripcion": "Mantenimientos coincidentes dejan zona sin respaldo local.",
     "impacto": "Colapso zona suroccidental"},
    {"riesgo": "Zona El Oro: bajo factor de potencia CNEL El Oro",
     "zona": "El Oro", "nivel": "ALTO",
     "descripcion": "Bajo FP + generación local limitada. Vulnerable ante contingencias.",
     "impacto": "Colapsos regionales ante N-1"},
    {"riesgo": "Zona Nororiental: mantenimiento Agoyán + San Francisco",
     "zona": "Pastaza/Morona", "nivel": "ALTO",
     "descripcion": "Salida simultánea 368 MW sin recursos para garantizar continuidad.",
     "impacto": "Colapso nororiental del país"},
    {"riesgo": "Imposibilidad de mantenimientos en SNT",
     "zona": "Nacional", "nivel": "ALTO",
     "descripcion": "Sistema degradado: cualquier desconexión requiere corte de carga.",
     "impacto": "Degradación progresiva de infraestructura"},
])

# Corredores de transmisión principales con datos de flujo
CORREDORES_TRANSMISION = pd.DataFrame([
    {"corredor": "CCS–El Inga–Tisaleo 500 kV", "voltaje": "500 kV",
     "capacidad_mw": 1500, "flujo_tipico_mw": 1200, "flujo_max_mw": 1450,
     "uso_pct": 80, "critico": "Sí"},
    {"corredor": "Tisaleo–Chorrillos 500 kV", "voltaje": "500 kV",
     "capacidad_mw": 1200, "flujo_tipico_mw": 900, "flujo_max_mw": 1100,
     "uso_pct": 75, "critico": "Sí"},
    {"corredor": "Santa Rosa–Totoras 230 kV", "voltaje": "230 kV",
     "capacidad_mw": 400, "flujo_tipico_mw": 350, "flujo_max_mw": 390,
     "uso_pct": 88, "critico": "Sí"},
    {"corredor": "Trinitaria–Salitral–Pascuales 138 kV", "voltaje": "138 kV",
     "capacidad_mw": 250, "flujo_tipico_mw": 230, "flujo_max_mw": 248,
     "uso_pct": 92, "critico": "CRÍTICO"},
    {"corredor": "Pomasqui–Jamondino 230 kV (EC-CO)", "voltaje": "230 kV",
     "capacidad_mw": 525, "flujo_tipico_mw": 280, "flujo_max_mw": 420,
     "uso_pct": 53, "critico": "Medio"},
    {"corredor": "Molino–Zhoray–Milagro 230 kV", "voltaje": "230 kV",
     "capacidad_mw": 800, "flujo_tipico_mw": 650, "flujo_max_mw": 750,
     "uso_pct": 81, "critico": "Sí"},
    {"corredor": "Santo Domingo–Quevedo 230 kV", "voltaje": "230 kV",
     "capacidad_mw": 500, "flujo_tipico_mw": 380, "flujo_max_mw": 450,
     "uso_pct": 76, "critico": "Medio"},
    {"corredor": "Yanacocha–Cuenca 138 kV", "voltaje": "138 kV",
     "capacidad_mw": 120, "flujo_tipico_mw": 100, "flujo_max_mw": 115,
     "uso_pct": 83, "critico": "Sí"},
    {"corredor": "Machala–Zorritos 230 kV (EC-PE)", "voltaje": "230 kV",
     "capacidad_mw": 110, "flujo_tipico_mw": 15, "flujo_max_mw": 80,
     "uso_pct": 14, "critico": "No"},
])

# =============================================================================
# PRECIOS NODALES — Modelo simplificado del SNI Ecuador
# =============================================================================

NODOS_PRECIO = {
    "Pomasqui":    {"zona": "Norte (Sierra)", "lat": 0.04, "lon": -78.46, "tipo": "500/230 kV",
                    "carga_mw": 450, "gen_local_mw": 200, "factor_perdida": 0.012},
    "El Inga":     {"zona": "Centro (Quito)", "lat": -0.24, "lon": -78.45, "tipo": "230 kV",
                    "carga_mw": 1650, "gen_local_mw": 100, "factor_perdida": 0.018},
    "Tisaleo":     {"zona": "Centro (Cotopaxi)", "lat": -0.92, "lon": -78.63, "tipo": "500 kV",
                    "carga_mw": 350, "gen_local_mw": 50, "factor_perdida": 0.008},
    "Milagro":     {"zona": "Costa Central", "lat": -2.13, "lon": -79.59, "tipo": "230 kV",
                    "carga_mw": 400, "gen_local_mw": 150, "factor_perdida": 0.015},
    "Pascuales":   {"zona": "Guayaquil Norte", "lat": -2.01, "lon": -79.93, "tipo": "230/138 kV",
                    "carga_mw": 1200, "gen_local_mw": 300, "factor_perdida": 0.022},
    "Trinitaria":  {"zona": "Guayaquil Sur", "lat": -2.18, "lon": -79.90, "tipo": "230/138 kV",
                    "carga_mw": 800, "gen_local_mw": 100, "factor_perdida": 0.028},
    "Dos Cerritos":{"zona": "Guayas", "lat": -1.89, "lon": -79.72, "tipo": "230/138 kV",
                    "carga_mw": 300, "gen_local_mw": 80, "factor_perdida": 0.020},
    "Molino":      {"zona": "Sur (Azuay)", "lat": -2.88, "lon": -78.95, "tipo": "230 kV",
                    "carga_mw": 200, "gen_local_mw": 1100, "factor_perdida": 0.005},
    "Zhoray":      {"zona": "Sur (Cuenca)", "lat": -2.92, "lon": -79.05, "tipo": "230 kV",
                    "carga_mw": 450, "gen_local_mw": 170, "factor_perdida": 0.010},
    "Santa Rosa":  {"zona": "El Oro", "lat": -3.45, "lon": -79.96, "tipo": "230 kV",
                    "carga_mw": 250, "gen_local_mw": 60, "factor_perdida": 0.025},
    "Santo Domingo":{"zona": "Santo Domingo", "lat": -0.25, "lon": -79.17, "tipo": "230 kV",
                    "carga_mw": 380, "gen_local_mw": 200, "factor_perdida": 0.014},
    "Coca Codo":   {"zona": "Oriente (CCS)", "lat": 0.15, "lon": -77.45, "tipo": "500 kV",
                    "carga_mw": 50, "gen_local_mw": 1500, "factor_perdida": 0.003},
}

# Costos marginales de generación por zona (USD/MWh)
COSTOS_MARGINALES = {
    "Hidro CCS": 15.0, "Hidro Paute": 18.0, "Hidro otras": 22.0,
    "Térmico gas": 55.0, "Térmico fuel": 85.0, "Térmico diésel": 110.0,
    "Eólica": 5.0, "Solar": 8.0, "Import Colombia": 120.0,
}

# =============================================================================
# CONGESTIÓN — Flujos de potencia y capacidad de líneas
# =============================================================================

LINEAS_TRANSMISION = pd.DataFrame([
    {"linea": "L/T CCS–El Inga 500 kV (Cto 1)", "de": "Coca Codo", "a": "El Inga",
     "voltaje": "500 kV", "longitud_km": 260, "capacidad_mw": 800,
     "flujo_normal_mw": 650, "flujo_pico_mw": 750, "flujo_emerg_mw": 780,
     "uso_normal_pct": 81, "uso_pico_pct": 94, "reactancia_pu": 0.0180,
     "resistencia_pu": 0.0018, "critico": "ALTO"},
    {"linea": "L/T CCS–El Inga 500 kV (Cto 2)", "de": "Coca Codo", "a": "El Inga",
     "voltaje": "500 kV", "longitud_km": 260, "capacidad_mw": 800,
     "flujo_normal_mw": 550, "flujo_pico_mw": 680, "flujo_emerg_mw": 720,
     "uso_normal_pct": 69, "uso_pico_pct": 85, "reactancia_pu": 0.0180,
     "resistencia_pu": 0.0018, "critico": "MEDIO"},
    {"linea": "L/T El Inga–Tisaleo 500 kV", "de": "El Inga", "a": "Tisaleo",
     "voltaje": "500 kV", "longitud_km": 85, "capacidad_mw": 1200,
     "flujo_normal_mw": 900, "flujo_pico_mw": 1050, "flujo_emerg_mw": 1150,
     "uso_normal_pct": 75, "uso_pico_pct": 88, "reactancia_pu": 0.0060,
     "resistencia_pu": 0.0006, "critico": "ALTO"},
    {"linea": "L/T Tisaleo–Chorrillos 500 kV", "de": "Tisaleo", "a": "Chorrillos",
     "voltaje": "500 kV", "longitud_km": 310, "capacidad_mw": 1000,
     "flujo_normal_mw": 720, "flujo_pico_mw": 880, "flujo_emerg_mw": 950,
     "uso_normal_pct": 72, "uso_pico_pct": 88, "reactancia_pu": 0.0220,
     "resistencia_pu": 0.0022, "critico": "ALTO"},
    {"linea": "L/T Pomasqui–Jamondino 230 kV (Cto 1)", "de": "Pomasqui", "a": "Jamondino (CO)",
     "voltaje": "230 kV", "longitud_km": 212, "capacidad_mw": 265,
     "flujo_normal_mw": 150, "flujo_pico_mw": 240, "flujo_emerg_mw": 260,
     "uso_normal_pct": 57, "uso_pico_pct": 91, "reactancia_pu": 0.0450,
     "resistencia_pu": 0.0045, "critico": "MEDIO"},
    {"linea": "L/T Pomasqui–Jamondino 230 kV (Cto 2)", "de": "Pomasqui", "a": "Jamondino (CO)",
     "voltaje": "230 kV", "longitud_km": 212, "capacidad_mw": 265,
     "flujo_normal_mw": 130, "flujo_pico_mw": 220, "flujo_emerg_mw": 250,
     "uso_normal_pct": 49, "uso_pico_pct": 83, "reactancia_pu": 0.0450,
     "resistencia_pu": 0.0045, "critico": "MEDIO"},
    {"linea": "L/T Santa Rosa–Totoras 230 kV (Cto 1)", "de": "Santa Rosa", "a": "Totoras",
     "voltaje": "230 kV", "longitud_km": 145, "capacidad_mw": 200,
     "flujo_normal_mw": 170, "flujo_pico_mw": 192, "flujo_emerg_mw": 198,
     "uso_normal_pct": 85, "uso_pico_pct": 96, "reactancia_pu": 0.0320,
     "resistencia_pu": 0.0032, "critico": "CRÍTICO"},
    {"linea": "L/T Santa Rosa–Totoras 230 kV (Cto 2)", "de": "Santa Rosa", "a": "Totoras",
     "voltaje": "230 kV", "longitud_km": 145, "capacidad_mw": 200,
     "flujo_normal_mw": 165, "flujo_pico_mw": 188, "flujo_emerg_mw": 195,
     "uso_normal_pct": 83, "uso_pico_pct": 94, "reactancia_pu": 0.0320,
     "resistencia_pu": 0.0032, "critico": "CRÍTICO"},
    {"linea": "L/T Trinitaria–Salitral 138 kV", "de": "Trinitaria", "a": "Salitral",
     "voltaje": "138 kV", "longitud_km": 25, "capacidad_mw": 120,
     "flujo_normal_mw": 108, "flujo_pico_mw": 117, "flujo_emerg_mw": 119,
     "uso_normal_pct": 90, "uso_pico_pct": 98, "reactancia_pu": 0.0080,
     "resistencia_pu": 0.0012, "critico": "CRÍTICO"},
    {"linea": "L/T Salitral–Pascuales 138 kV", "de": "Salitral", "a": "Pascuales",
     "voltaje": "138 kV", "longitud_km": 18, "capacidad_mw": 130,
     "flujo_normal_mw": 115, "flujo_pico_mw": 126, "flujo_emerg_mw": 128,
     "uso_normal_pct": 88, "uso_pico_pct": 97, "reactancia_pu": 0.0060,
     "resistencia_pu": 0.0009, "critico": "CRÍTICO"},
    {"linea": "L/T Molino–Zhoray 230 kV", "de": "Molino", "a": "Zhoray",
     "voltaje": "230 kV", "longitud_km": 35, "capacidad_mw": 500,
     "flujo_normal_mw": 380, "flujo_pico_mw": 450, "flujo_emerg_mw": 480,
     "uso_normal_pct": 76, "uso_pico_pct": 90, "reactancia_pu": 0.0080,
     "resistencia_pu": 0.0008, "critico": "ALTO"},
    {"linea": "L/T Zhoray–Milagro 230 kV", "de": "Zhoray", "a": "Milagro",
     "voltaje": "230 kV", "longitud_km": 180, "capacidad_mw": 400,
     "flujo_normal_mw": 280, "flujo_pico_mw": 360, "flujo_emerg_mw": 390,
     "uso_normal_pct": 70, "uso_pico_pct": 90, "reactancia_pu": 0.0400,
     "resistencia_pu": 0.0040, "critico": "ALTO"},
    {"linea": "L/T Santo Domingo–Quevedo 230 kV (Cto 1)", "de": "Santo Domingo", "a": "Quevedo",
     "voltaje": "230 kV", "longitud_km": 120, "capacidad_mw": 250,
     "flujo_normal_mw": 190, "flujo_pico_mw": 230, "flujo_emerg_mw": 245,
     "uso_normal_pct": 76, "uso_pico_pct": 92, "reactancia_pu": 0.0270,
     "resistencia_pu": 0.0027, "critico": "ALTO"},
    {"linea": "L/T Santo Domingo–Quevedo 230 kV (Cto 2)", "de": "Santo Domingo", "a": "Quevedo",
     "voltaje": "230 kV", "longitud_km": 120, "capacidad_mw": 250,
     "flujo_normal_mw": 180, "flujo_pico_mw": 220, "flujo_emerg_mw": 240,
     "uso_normal_pct": 72, "uso_pico_pct": 88, "reactancia_pu": 0.0270,
     "resistencia_pu": 0.0027, "critico": "MEDIO"},
    {"linea": "L/T Yanacocha–Cuenca 138 kV (Cto 1)", "de": "Yanacocha", "a": "Cuenca",
     "voltaje": "138 kV", "longitud_km": 60, "capacidad_mw": 60,
     "flujo_normal_mw": 48, "flujo_pico_mw": 56, "flujo_emerg_mw": 58,
     "uso_normal_pct": 80, "uso_pico_pct": 93, "reactancia_pu": 0.0150,
     "resistencia_pu": 0.0020, "critico": "ALTO"},
    {"linea": "L/T Yanacocha–Cuenca 138 kV (Cto 2)", "de": "Yanacocha", "a": "Cuenca",
     "voltaje": "138 kV", "longitud_km": 60, "capacidad_mw": 60,
     "flujo_normal_mw": 50, "flujo_pico_mw": 57, "flujo_emerg_mw": 59,
     "uso_normal_pct": 83, "uso_pico_pct": 95, "reactancia_pu": 0.0150,
     "resistencia_pu": 0.0020, "critico": "CRÍTICO"},
    {"linea": "L/T Machala–Zorritos 230 kV (EC-PE)", "de": "Machala", "a": "Zorritos (PE)",
     "voltaje": "230 kV", "longitud_km": 53, "capacidad_mw": 110,
     "flujo_normal_mw": 15, "flujo_pico_mw": 50, "flujo_emerg_mw": 80,
     "uso_normal_pct": 14, "uso_pico_pct": 45, "reactancia_pu": 0.0120,
     "resistencia_pu": 0.0012, "critico": "BAJO"},
    {"linea": "L/T Dos Cerritos–Pascuales 230 kV", "de": "Dos Cerritos", "a": "Pascuales",
     "voltaje": "230 kV", "longitud_km": 45, "capacidad_mw": 350,
     "flujo_normal_mw": 250, "flujo_pico_mw": 320, "flujo_emerg_mw": 340,
     "uso_normal_pct": 71, "uso_pico_pct": 91, "reactancia_pu": 0.0100,
     "resistencia_pu": 0.0010, "critico": "ALTO"},
    {"linea": "L/T Pascuales–Chongón 138 kV", "de": "Pascuales", "a": "Chongón",
     "voltaje": "138 kV", "longitud_km": 35, "capacidad_mw": 100,
     "flujo_normal_mw": 82, "flujo_pico_mw": 94, "flujo_emerg_mw": 98,
     "uso_normal_pct": 82, "uso_pico_pct": 94, "reactancia_pu": 0.0090,
     "resistencia_pu": 0.0013, "critico": "ALTO"},
])

# Eventos de congestión registrados
EVENTOS_CONGESTION = pd.DataFrame([
    {"fecha": "2024-09-15", "linea": "Trinitaria–Salitral 138 kV",
     "tipo": "Sobrecarga", "uso_pct": 102, "duracion_min": 45,
     "accion": "Corte de carga rotativo Guayaquil Sur (80 MW)", "causa": "Pico demanda + baja gen. local"},
    {"fecha": "2024-10-03", "linea": "Santa Rosa–Totoras 230 kV Cto 1",
     "tipo": "N-1 → N-2", "uso_pct": 98, "duracion_min": 120,
     "accion": "SPS activado: desconexión 150 MW zona El Oro", "causa": "Salida Cto 2 por mantenimiento"},
    {"fecha": "2024-11-12", "linea": "CCS–El Inga 500 kV Cto 1",
     "tipo": "Sobrecarga", "uso_pct": 96, "duracion_min": 30,
     "accion": "Reducción despacho CCS → térmica Quito", "causa": "Pico demanda DMQ + exportación norte"},
    {"fecha": "2025-01-20", "linea": "Yanacocha–Cuenca 138 kV Cto 2",
     "tipo": "N-1 → sobrecarga", "uso_pct": 120, "duracion_min": 90,
     "accion": "Generación forzada Delsitanisagua + corte Cuenca", "causa": "Salida Cto 1 por falla"},
    {"fecha": "2025-05-07", "linea": "El Inga–Tisaleo 500 kV",
     "tipo": "Sobrecarga pico", "uso_pct": 95, "duracion_min": 25,
     "accion": "Despacho térmico emergencia Quito", "causa": "Récord demanda 5,110 MW"},
    {"fecha": "2026-03-28", "linea": "Molino–Zhoray 230 kV",
     "tipo": "Sobrecarga", "uso_pct": 92, "duracion_min": 60,
     "accion": "Redistribución flujos vía Milagro", "causa": "Mazar en cota baja + alta demanda sur"},
    {"fecha": "2026-04-26", "linea": "Salitral–Pascuales 138 kV",
     "tipo": "Sobrecarga pico", "uso_pct": 99, "duracion_min": 15,
     "accion": "Corte preventivo 50 MW zona Guayaquil", "causa": "Pico vespertino + gen. solar baja"},
    {"fecha": "2026-07-15", "linea": "Dos Cerritos–Pascuales 230 kV",
     "tipo": "N-1 contingencia", "uso_pct": 93, "duracion_min": 40,
     "accion": "SPS activado: generación forzada Santa Elena", "causa": "Salida ATK Dos Cerritos"},
])

# Resumen de congestión por zona
CONGESTION_ZONAL = pd.DataFrame([
    {"zona": "Guayaquil (138 kV)", "lineas_criticas": 3,
     "uso_promedio_pct": 90, "uso_maximo_pct": 99,
     "horas_congestion_dia": 6, "MW_cortados_ano": 2800,
     "costo_congestion_musd": 12.5, "refuerzo_necesario": "Nuevo corredor 230 kV"},
    {"zona": "El Oro (230 kV)", "lineas_criticas": 2,
     "uso_promedio_pct": 84, "uso_maximo_pct": 96,
     "horas_congestion_dia": 3, "MW_cortados_ano": 1200,
     "costo_congestion_musd": 5.4, "refuerzo_necesario": "500 kV Chorrillos–Pasaje (2029)"},
    {"zona": "Sierra Norte (500 kV)", "lineas_criticas": 2,
     "uso_promedio_pct": 78, "uso_maximo_pct": 94,
     "horas_congestion_dia": 2, "MW_cortados_ano": 400,
     "costo_congestion_musd": 2.1, "refuerzo_necesario": "Refuerzo CCS-El Inga 2do circuito"},
    {"zona": "Sierra Sur (230 kV)", "lineas_criticas": 3,
     "uso_promedio_pct": 76, "uso_maximo_pct": 95,
     "horas_congestion_dia": 3, "MW_cortados_ano": 800,
     "costo_congestion_musd": 3.6, "refuerzo_necesario": "Zhoray–Sinincay 2do circuito (2025)"},
    {"zona": "Costa (230 kV)", "lineas_criticas": 2,
     "uso_promedio_pct": 72, "uso_maximo_pct": 92,
     "horas_congestion_dia": 2, "MW_cortados_ano": 500,
     "costo_congestion_musd": 2.2, "refuerzo_necesario": "Refuerzo Sto. Domingo–Quevedo"},
    {"zona": "Oriente (500 kV)", "lineas_criticas": 1,
     "uso_promedio_pct": 75, "uso_maximo_pct": 88,
     "horas_congestion_dia": 1, "MW_cortados_ano": 200,
     "costo_congestion_musd": 1.0, "refuerzo_necesario": "Evacuación CCS redundante"},
    {"zona": "Interconexión CO (230 kV)", "lineas_criticas": 1,
     "uso_promedio_pct": 53, "uso_maximo_pct": 91,
     "horas_congestion_dia": 1, "MW_cortados_ano": 150,
     "costo_congestion_musd": 1.8, "refuerzo_necesario": "500 kV futuro Pomasqui–frontera"},
])

# Precios nodales promedio por nodo (USD/MWh) — calculados con congestión
PRECIOS_NODALES_HISTORICOS = pd.DataFrame([
    {"ano": 2022, "promedio_sistema": 52, "Pomasqui": 50, "El Inga": 54, "Tisaleo": 51,
     "Pascuales": 58, "Trinitaria": 62, "Molino": 45, "Zhoray": 48, "Coca Codo": 42,
     "Santa Rosa": 60, "Milagro": 56},
    {"ano": 2023, "promedio_sistema": 58, "Pomasqui": 55, "El Inga": 60, "Tisaleo": 57,
     "Pascuales": 65, "Trinitaria": 70, "Molino": 50, "Zhoray": 53, "Coca Codo": 46,
     "Santa Rosa": 68, "Milagro": 62},
    {"ano": 2024, "promedio_sistema": 78, "Pomasqui": 75, "El Inga": 82, "Tisaleo": 76,
     "Pascuales": 95, "Trinitaria": 110, "Molino": 65, "Zhoray": 70, "Coca Codo": 55,
     "Santa Rosa": 105, "Milagro": 88},
    {"ano": 2025, "promedio_sistema": 62, "Pomasqui": 60, "El Inga": 65, "Tisaleo": 61,
     "Pascuales": 72, "Trinitaria": 80, "Molino": 52, "Zhoray": 56, "Coca Codo": 48,
     "Santa Rosa": 78, "Milagro": 68},
    {"ano": 2026, "promedio_sistema": 55, "Pomasqui": 53, "El Inga": 58, "Tisaleo": 54,
     "Pascuales": 65, "Trinitaria": 72, "Molino": 47, "Zhoray": 50, "Coca Codo": 44,
     "Santa Rosa": 70, "Milagro": 60},
])

# =============================================================================
# COLORES
# =============================================================================

GEN_COLORS = {
    "Hidro": "#2E86AB", "Termo": "#C73E1D", "Eólica": "#6A994E",
    "Solar": "#F18F01", "Biomasa": "#8B5E3C", "Biogás": "#57CC99",
    "Import_COL": "#7B2D8E", "Import_PER": "#D4A373",
    "Importación": "#7B2D8E",
}

# =============================================================================
# FUNCIONES DE GENERACIÓN DE DATOS
# =============================================================================

def generate_generation_mix(ano: int = 2026) -> pd.DataFrame:
    """Genera DataFrame de mix de generación para un año dado."""
    if ano not in GENERACION_POR_ANO:
        ano = 2026
    data = GENERACION_POR_ANO[ano]
    rows = []
    for fonte, gwh in data.items():
        if fonte == "Total":
            continue
        rows.append({
            "fonte": fonte,
            "geracao_gwh": gwh,
            "pct": round(gwh / data["Total"] * 100, 1),
        })
    return pd.DataFrame(rows)


def generate_demand_profile(dias: int = 30, pico_mw: float = 5100) -> pd.DataFrame:
    """Genera perfil de demanda diario sintético."""
    np.random.seed(42)
    fechas = pd.date_range(end=datetime.now(), periods=dias * 24, freq="h")
    hours = np.array(fechas.hour)
    # Perfil típico: valle 2-5h, rampa 6-10h, pico 18-21h
    base = pico_mw * 0.6
    perfil = base + pico_mw * 0.4 * (
        0.3 * np.sin(np.pi * (hours - 6) / 12).clip(0) +
        0.7 * np.exp(-0.5 * ((hours - 19) / 2) ** 2)
    )
    ruido = np.random.normal(0, pico_mw * 0.02, len(fechas))
    demanda = (perfil + ruido).clip(pico_mw * 0.35)
    return pd.DataFrame({"fecha": fechas, "demanda_mw": np.round(demanda, 1)})


def generate_reservoir_levels(embalse: str, ano: int = 2026) -> pd.DataFrame:
    """Genera niveles de embalse mensuales."""
    np.random.seed(42)
    meses = pd.date_range(f"{ano}-01-01", periods=12, freq="MS")
    emb = EMBALSES.get(embalse, EMBALSES["Mazar"])
    nivel_base = emb["niveles_historicos"].get(ano, 70)
    # Estiaje Jun-Nov (sierra sur), lluvias Dic-May
    estiaje = np.array([15, 20, 10, -5, -15, -20, -18, -12, -5, 5, 15, 18])
    niveles = (nivel_base + estiaje + np.random.normal(0, 3, 12)).clip(5, 100)
    return pd.DataFrame({"mes": meses, "nivel_pct": niveles.round(1)})


def get_last_n_days_dates(n: int = 30):
    """Retorna fechas inicio/fin para consulta de n días."""
    fin = datetime.now()
    inicio = fin - timedelta(days=n)
    return inicio.strftime("%Y-%m-%d"), fin.strftime("%Y-%m-%d")
