# Códigos abiertos y datos del SNI de Ecuador para mejorar el *Ecuador Energy Dashboard*

**Fecha de revisión:** 10-sep-2026 · **Alcance:** repositorios GitHub, APIs públicas y datos abiertos verificados *en vivo* desde este entorno (se indica ✅ cuando el acceso fue probado y funciona hoy).

> Resumen ejecutivo: la app original (`srriverar/ECUdashboard`, 18 pestañas) es 100 % sintética/hard-coded. El mayor salto de calidad es **ingestar datos reales**. Encontré **tres fuentes abiertas, sin clave, con API programática** que cubren las pestañas *Carga*, *Generación*, *Hidrología* e *Intercambio*, y ya las integré en `ecuador_sni/` (probado: 0 excepciones en las 3 pestañas). El resto del inventario (13 repos + 9 fuentes de datos) se mapea abajo a pestañas concretas.

---

## 1. Lo que ya quedó integrado (código listo para Streamlit Cloud)

| Archivo nuevo | Fuente real | Qué entrega | Pestañas |
|---|---|---|---|
| `tools/cenace_client.py` ✅ | CENACE `InformacionOperativa.htm` (18 figuras Plotly incrustadas, arrays float64 en base64) | Curvas 48×30 min de hoy y ayer (Hidráulica, Térmica, Renovable, Importación, Exportación, Producción total, **Demanda nacional**); energía acumulada hoy/ayer/mes/año por fuente; producción por central hidro (Coca Codo, Paute, Sopladora, Mazar, Agoyán…); Térmica/Gas Natural/Renovable; **demanda por las 19 distribuidoras** y CNEL vs EE | Carga, Generación, Resumen, Racionamiento |
| `tools/celecsur_client.py` ✅ (**hallazgo nuevo**) | CELEC Sur — API REST Oracle ORDS abierta `https://generacioncsr.celec.gob.ec:8443/ords/csr/sardomcsr/` (descubierta en el bundle JS de *graficasproduccion*) | **Cota y caudal horarios y medias diarias** de Mazar (mrid 30031/30538), Amaluza-Molino (24019/24811), Sopladora (90919/90537) y Minas San Francisco (650919/650538); recursos `csrEnerDia/Mes/Anio` (energía por central), `csrCaudCuen*` (caudales de cuenca), `pointValuesMesH24/AnioAvg…` | Hidrología, Racionamiento, Crisis 2024 |
| `tools/xm_client.py` ✅ | XM Colombia — API SINERGOX vía `pydataxm` (repo `EquipoAnaliticaXM/API_XM`) | Energía horaria **importada/exportada por el enlace “ECUADOR 230”** (kWh → MW), últimos 31 días por llamada; también `ImportMonedaUSD/ExportMonedaUSD` (precio implícito del intercambio) | Intercambio, Mercado |
| `tools/live_panels.py` | — | Tres paneles Streamlit con validaciones de coherencia (balance producción≈demanda ±8 %, rangos físicos de cotas, ≤550 MW en el enlace); si la fuente falla se avisa y **no se inventan números** | — |
| `app.py` (parcheado) | — | Llama a los paneles al inicio de *Carga*, *Hidrología* e *Intercambio*; el contenido sintético original queda debajo rotulado “Modelo didáctico” | — |

Valores leídos hoy 10-sep-2026 ~16:30 EC (para que compruebes): demanda 5 140 MW (pico ayer 5 467 MW), hidro 82 %, térmica 838 MW, importación 3 MW; cota Mazar **2 143,4 m** (82 % de llenado; caía 0,30 m/día → cota crítica 2 115 m ≈ 13-dic-2026 si nada cambia — coincide con la prensa de hoy); importación desde Colombia 76 GWh en 12 días con pico 457 MW y caída a ~0 desde el 7-sep.

Instalación: `requirements.txt` añade `pydataxm` y `urllib3`. Certificado SSL de CENACE incompleto → `verify=False` (misma decisión que Electricity Maps).

---

## 2. Repositorios GitHub sobre el sistema eléctrico ecuatoriano

### 2.1 Directamente reutilizables (Python)

| # | Repositorio | Qué contiene | Cómo mejora la app |
|---|---|---|---|
| 1 | **electricitymaps/electricitymaps-contrib** → `electricitymap/contrib/parsers/EC.py` (mar-2026) | Parser oficial de Electricity Maps para Ecuador: mismo enfoque Plotly/bdata sobre CENACE, `fetch_production` y `fetch_consumption`; `config/zones/EC.yaml` con capacidades por tecnología (Ember) | Referencia de robustez del parser; las capacidades de `EC.yaml` sirven para validar `CAPACIDAD_INSTALADA` de `ecu_grid_model.py` |
| 2 | **DiegoFernandoLojanTenesaca/ecuador-energy-anomalies** | Scrapers CENACE/ARCERNNR/Ember-OWID, pipeline de limpieza, detectores **Isolation Forest + STL + CUSUM** validados contra la crisis 2024; `data/raw/ecuador_electricity_real.csv` (mensual 2019-2026: generación por fuente, demanda, CO₂, importaciones) | Pestaña *Eventos/ML*: sustituir la detección TKEO sintética por consenso IF+STL+CUSUM sobre series reales; pestaña *Emisiones*: intensidad gCO₂/kWh mensual real |
| 3 | **Fernando3161/EcuadorElectricGrid** | Notebooks PyPSA del SNI: pronóstico de demanda 2018-2027 (3 escenarios), perfiles, generación futura (PME), evaluación topológica de red 500/230/138/69 kV (`ec_network_eval.py`), clustering; PDFs del Plan de Expansión de Transmisión y Generación | Pestañas *Contingencias*, *Congestión*, *Nodales*: base para un modelo PyPSA/pandapower real del SNI en vez de `LINEAS_TRANSMISION` hard-coded |
| 4 | **kdcaizac-dev/modelo-optimizacion-sni-cenace** y **kdcaizac-dev/optimizador-cenace-sni** | Despacho LP en 3 fases (simplex dos fases, transporte con pérdidas iterativas, escenarios de estiaje Normal/Bajo/Severo/Extremo), dashboard Streamlit, tests; CSV de nodos, arcos, plantas, orden de mérito térmico, caudales de estiaje, bloques de demanda | Pestaña *Mercado* y *Racionamiento*: precios sombra nodales y activación térmica por escenario de estiaje |
| 5 | **csanchezc5/Pronostico-de-demanda-electrica-en-Ecuador** | `demanda_mensual_SNI_2020_2024.csv` (de Informes Anuales CENACE), notebooks ARIMA/SARIMA, Prophet, LSTM y comparación | Pestaña *Carga*: proyección 2027-2030 basada en modelo y datos, no en tabla fija |
| 6 | **Henrylm4/Ecuador-Power-Demand-Historical-Tracker** | Tracker diario de demanda por empresa (`demanda_empresas_cenace.csv`), OCR de imágenes CENACE (obsoleto: la página ya es Plotly) | Histórico de demanda por distribuidora para complementar `fig5` del nuevo cliente |
| 7 | **adrianarodriguezp/dashboard_hidroelectricas** | Boletín hidrológico automatizado (caudales/niveles de 10+ centrales: Coca Codo, Mazar, Amaluza, Daule-Peripa, Pisayambo, Delsitanisagua…), comparativas 2024-25-26, mapas HTML, cron; lee un **FTP de CENACE** (credenciales privadas) | Diseño de la pestaña *Hidrología* multi-cuenca; usar la API CELEC Sur (abierta) donde el FTP no sea accesible |
| 8 | **fundestpuente/SIC25-…-CORTES-ENERGETICOS-EN-ECUADOR** | Análisis de demanda y efectos de los cortes 2024 (Samsung Innovation Campus): loaders, gráficos, dashboard integrado | Pestaña *Racionamiento*: horas de corte por provincia y energía no suministrada |
| 9 | **srriverar/ECUdashboard** | La app original (idéntica al `app.json` adjunto) | Base parcheada aquí |

### 2.2 Cortes de luz / distribuidoras (JS/TS, útiles como fuente de datos)

| Repositorio | Qué aporta |
|---|---|
| **Savecoders/cnel-outage-schedule** (Astro/TS), **lennynT02/API-Cortes-Luz**, **jopeee75/CortesdeluzEc**, **Erick-Toala/apagones-app-react-native**, **brian593/SinLuzApp**, **AlenSaavedra/PowerCheck-EC** (Spring) | Consumen la API pública de CNEL de horarios de corte por cuenta/CI (tipos `api-schedule.type.ts` documentan el JSON). Permitirían una pestaña *Racionamiento* con **cronogramas reales** cuando hay cortes |
| **lxndr-rl/energizame** | Alertas WhatsApp de cortes; scraping de EEQ/CNEL |
| **ivelec1981/sisdat-forecast** (Next/TS) | Proyección de demanda por sector/empresa estilo SISDAT; datos de transmisión y unifilar en `src/lib/data/*.ts` reutilizables como JSON |
| **degos30/Arconel**, **jallangap/ConsolidadoArconel**, **manunoly/sqlArconel**, **RobertoSuarez/meter-reader** | Consolidación de formularios SISDAT/ARCONEL y tarifas; útiles para la pestaña *Mercado* (pliego tarifario) |

### 2.3 Modelos académicos abiertos con datos de Ecuador

| Recurso | Uso |
|---|---|
| **VUB-HYDR/REVUB** + Zenodo 10.5281/zenodo.15854447 (Sterl 2026, *Nature Water*: “Variable renewables fortify Ecuador’s power system…”) | Modelo Python de operación hidro-VRE con **parámetros reales del Complejo Paute** (batimetría, turbinas, caudales CELEC de Paute y Jubones, ciclos de Mazar 2023-24 y paradas forzadas de Molino 2024). Ideal para la pestaña *ENOS/Sequía* y *IBR* (hibridación solar/eólica) |
| **SPLATteam/Model-Supply-Regions-MSR-Toolset** (IRENA) | Regiones de suministro solar/eólico para Ecuador usadas en el mismo estudio |
| **pypsa-meets-earth/pypsa-earth** + `earth-osm` | Construye la red 500/230/138 kV de Ecuador desde OpenStreetMap y perfiles renovables (ERA5/atlite) → sustituye `LINEAS_TRANSMISION` y `NODOS_PRECIO` sintéticos por topología georreferenciada |
| **EquipoAnaliticaXM/API_XM** (`pydataxm`) | Ya integrado; además precio de bolsa colombiano (`PrecBolsNaci`) para la pestaña *Mercado* |
| Revista Técnica **energía** (CENACE) — Gallo, Pérez, Salinas: herramienta Python LGBM/RF/ARIMA de pronóstico de demanda a corto plazo del SNI | Metodología (no repo público) para la proyección 48 h en la pestaña *Carga* |

---

## 3. Datos abiertos oficiales del SNI (no GitHub)

| Fuente | Contenido | Acceso probado |
|---|---|---|
| CENACE Información Operativa (`cenace.gob.ec/info-operativa/InformacionOperativa.htm`) | Tiempo real 30 min + acumulados | ✅ (parser incluido) |
| CELEC Sur API ORDS (`generacioncsr.celec.gob.ec:8443/ords/csr/sardomcsr/*`) | Cotas, caudales, energía Paute/Mazar/Sopladora/Minas SF | ✅ (cliente incluido) |
| XM API SINERGOX (`pydataxm`) | TIE Colombia-Ecuador horario, precios | ✅ |
| **datosabiertos.gob.ec/dataset/?organization=cenace** (39 datasets CKAN, CC0) | Producción trimestral por central (CSV/XLSX 2022-2024), potencia efectiva despachada, capacidad instalada | ⚠️ El portal devuelve 403 a clientes no navegador desde esta red; funciona desde navegador. Endpoint CKAN: `/api/3/action/package_search?fq=organization:cenace` |
| ARCERNNR **SISDAT-BI** (`sisdatbi.controlrecursosyenergia.gob.ec`) y Estadística Anual y Multianual del Sector Eléctrico | Balance Nacional de Energía Eléctrica, centrales, pérdidas, tarifas | ✅ portal (Power BI, sin API) |
| Informe Anual CENACE 2024 (PDF) | 30 859 GWh producción neta; 20 019 GWh hidro; 6 643 térmica; 2 928 no convencional; 1 267 importación; pico 5 063 MW | ✅ |
| INEC ANDA catálogo 867 | Metadatos y formularios SISDAT | ✅ |
| Ember / OWID (vía repo #2) | Series mensuales por tecnología 2019-2026 | ✅ |
| CNEL API horarios de corte (vía repos 2.2) | Cronogramas por cuenta | — (solo activa en racionamiento) |

---

## 4. Plan de mejoras por pestaña (priorizado)

1. **Carga / Resumen (hecho)** — métricas reales, curva del día, pico de ayer, 19 distribuidoras.
2. **Hidrología (hecho)** — cota/caudal reales + tendencia y “días a cota crítica”. Siguiente: agregar Coca Codo, Agoyán, Daule-Peripa desde el FTP CENACE si se obtiene acceso (repo #7 muestra el formato).
3. **Intercambio (hecho)** — flujo horario real desde XM. Siguiente: Perú (COES publica `www.coes.org.pe` con API pública `/api/…` de intercambios) y precio implícito USD/MWh.
4. **Generación** — reemplazar `generate_generation_mix` por `rt['acumulados']` + `hidro_plantas` (ya disponibles en el dict).
5. **Racionamiento / Crisis 2024** — energía no suministrada desde repo #8 y detectores del repo #2; cronogramas CNEL.
6. **Eventos ML** — Isolation Forest + STL + CUSUM (repo #2) sobre la demanda 30 min de CENACE acumulada día a día (guardar en `data/processed/` con un cron de GitHub Actions).
7. **Contingencias / Nodales / Congestión** — red real vía PyPSA-Earth/earth-osm o repo #3; despacho LP del repo #4 para precios sombra.
8. **ENOS / Sequía / IBR** — REVUB con parámetros reales de Paute (Zenodo 15854447).
9. **Mercado** — precio de bolsa XM (`PrecBolsNaci`) + costo marginal CENACE de los informes; tarifas ARCERNNR (repos 2.2).
10. **WAMS / Estabilidad** — no existe dato PMU abierto de Ecuador; mantener simulación, pero calibrar `INERCIA_SNI` con el mix real horario (H equivalente = Σ H_i·S_i / S_total usando `hidro_mw`, `termo_mw`, `renov_mw`).

---

## 5. Advertencias y límites

- CENACE marca sus datos como *preliminares del SCADA, sujetos a revisión*; el año acumulado se publica en **GWh** y los demás períodos en **MWh** (ya manejado en `unidades`).
- La API de CELEC Sur no está documentada públicamente: puede cambiar sin aviso; el cliente falla de forma controlada.
- Los `mrid` se identificaron por rango físico y consistencia con prensa (Mazar 2 143,7 m el 9-sep según CELEC); confirmar con CELEC Sur si se usa para decisiones.
- El repositorio #7 contiene un `memory.md` que menciona un token filtrado en su historial: **no reutilizar** sus credenciales; usar sólo la lógica.
