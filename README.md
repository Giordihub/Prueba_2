# UTI Extractor — de la ficha clínica al dataset de investigación

Prototipo que usa un modelo de lenguaje para transformar fichas clínicas de texto libre de una
Unidad de Tratamiento Intermedio (UTI) en un dataset estructurado de investigación, con una
interfaz web para explorar los resultados. Caso de uso inicial: **insuficiencia cardíaca
descompensada**.

Proyecto desarrollado para un curso de magíster en Inteligencia Artificial. Objetivo del
ejercicio: definir un problema, construir un dataset y levantar una plataforma web de display,
como prototipo de una eventual aplicación, evaluando cuánto se puede avanzar en ~1 hora de
trabajo asistido por un modelo de lenguaje.

> **Todos los datos son sintéticos.** Las fichas fueron generadas por el modelo con nombres y
> RUT ficticios. Ningún dato corresponde a personas reales.

## Problema
Las fichas de UTI se registran como texto libre en el sistema clínico (SINA), con abreviaturas
locales y estructura variable. Construir cohortes de investigación exige revisión manual ficha
por ficha. Este prototipo evalúa si un modelo de lenguaje puede hacer esa extracción con
exactitud suficiente y costo marginal.

## Resultados (10 pacientes sintéticos)
| Métrica | Valor |
|---|---|
| Exactitud en 14 campos simples (edad, sexo, FEVI, fenotipo, perfil hemodinámico, signos vitales, estadía, desenlace) | **100 %** |
| F1 medicamentos (principio activo) | 1.00 |
| F1 laboratorios | 0.99 |
| F1 comorbilidades | 0.94 |
| F1 terapias | 0.90 |
| F1 diagnósticos secundarios | 0.86 |
| F1 antecedentes | 0.84 |
| Costo total de API (20 llamadas) | < 2 USD |

Dataset resultante: `output/dataset.xlsx` con 4 hojas enlazadas por `id_paciente`:
Pacientes (10 filas), Medicamentos (122), Terapias (41), Laboratorios (211).

El análisis completo, las decisiones de diseño, limitaciones y trabajo futuro están en
[`docs/NOTAS_INFORME.md`](docs/NOTAS_INFORME.md).

## Arquitectura
```
data/fichas/*.md ──► extract.py ──► output/extraidos/*.json ──► output/dataset.xlsx
                        │            (validados con Pydantic)          │
                        │ Claude Opus 5.5 + esquema JSON                ▼
                        ▼                                         app.py (Streamlit)
                   validar.py ◄── data/verdad/*.json ──► output/validacion.xlsx
```

| Archivo | Función |
|---|---|
| `schema.py` | Esquema del dataset (Pydantic): 20 campos en 8 categorías clínicas |
| `generar_sinteticos.py` | Genera fichas sintéticas estilo SINA con su verdad de referencia |
| `extract.py` | Extrae variables de cada ficha y construye el Excel |
| `validar.py` | Compara extracción vs verdad de referencia (exactitud, precisión, recall, F1) |
| `app.py` | Interfaz web: vista por paciente, cohorte con gráficos, descarga del dataset |
| `llm.py` | Cliente del modelo y validación JSON con reintento |

## Cómo ejecutarlo
Requiere Python 3.11+ y una clave de API de Anthropic.
```bash
git clone <este repositorio>
cd uti-extractor
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # pegar la clave en ANTHROPIC_API_KEY

python generar_sinteticos.py 10 # (opcional) regenera las fichas sintéticas
python extract.py               # extrae y construye output/dataset.xlsx
python validar.py               # métricas de exactitud
streamlit run app.py            # abre la app en http://localhost:8501
```
Los resultados ya generados están incluidos en `output/`, por lo que la app puede abrirse
sin clave de API.

## Trabajo futuro
1. Lectura de fotografías de sabanillas de signos vitales e infusiones (el modelo acepta imágenes).
2. Revisión y corrección humana de cada campo dentro de la app, generando un gold standard.
3. Prueba con fichas reales anonimizadas, previa aprobación del comité de ética.
4. Exportación a REDCap y extensión a otras patologías de UTI cambiando solo el esquema.
