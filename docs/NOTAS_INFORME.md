# Notas para el informe — UTI Extractor

> Prototipo construido en ~1 hora de trabajo asistido por un modelo de lenguaje,
> en el marco del curso de magíster en IA. Todos los datos son sintéticos.

## 1. Problema
Las fichas clínicas de la Unidad de Tratamiento Intermedio (UTI) de un hospital público se
registran como texto libre en el sistema SINA, con abreviaturas locales y estructura variable.
Construir un dataset de investigación a partir de ellas hoy exige revisión manual ficha por
ficha, lo que limita el tamaño de las cohortes y la reproducibilidad.

**Pregunta de diseño:** ¿puede un modelo de lenguaje transformar fichas de texto libre en un
dataset estructurado, con exactitud suficiente para investigación clínica, y a un costo marginal?

**Caso de uso inicial:** insuficiencia cardíaca descompensada (IC). Es frecuente en UTI, tiene
variables bien definidas (FEVI, fenotipo, perfil hemodinámico, factor descompensante, terapias
con dosis y duración) y es extensible a otras patologías cambiando solo el esquema.

## 2. Dataset
- **Fuente:** 10 fichas sintéticas estilo SINA generadas por el modelo a partir de 10 escenarios
  clínicos distintos (ICFEr, ICFEp, ICFElr, cardiorrenal, shock con vasoactivos, VMNI,
  SCA como gatillante, valvulopatía, un fallecido). Nombres y RUT ficticios.
- **Verdad de referencia:** cada ficha nace con su JSON de verdad, generado en la misma
  llamada, lo que permite medir exactitud por variable.
- **Esquema de salida (`schema.py`):** 20 campos de nivel superior en 8 categorías:
  identificación clínica, diagnósticos, antecedentes, comorbilidades, FEVI y fenotipo,
  condición de ingreso y perfil hemodinámico, signos vitales de ingreso, laboratorios,
  medicamentos (dosis, vía, frecuencia, duración, infusión continua), terapias no
  farmacológicas, estadía y desenlace.
- **Dataset final (`output/dataset.xlsx`):** 4 hojas enlazadas por `id_paciente`:
  Pacientes (una fila por paciente), Medicamentos, Terapias y Laboratorios (formato largo).
- **Segunda fuente prevista:** fotografías de sabanillas de signos vitales e infusiones
  (sin datos identificables). El mismo modelo lee imágenes, por lo que la extensión es directa.
  No se implementó en la primera hora.

## 3. Arquitectura
```
fichas .md ──► extract.py ──► JSON validado (Pydantic) ──► dataset.xlsx
                  │                                            │
                  │ modelo de lenguaje (Claude Opus 5.5)        ▼
                  │ + esquema JSON en el prompt            app.py (Streamlit)
                  ▼
           validar.py ◄── data/verdad/*.json  ──► validacion.xlsx
```
- **Python 3.14**, SDK `anthropic`, `pydantic`, `pandas`, `openpyxl`, `streamlit`.
- Sin entrenamiento ni fine-tuning: extracción por instrucciones (zero-shot) con esquema
  explícito. Esto es clave para un hospital: cambiar la patología es cambiar el esquema.

## 4. Decisiones de diseño
1. **Modelo en la nube vs local.** Se eligió API en la nube por calidad en español clínico y
   velocidad de implementación. Para datos reales se requeriría anonimización previa, convenio
   de tratamiento de datos o un modelo local. Se documenta como requisito para la fase siguiente.
2. **Salida estructurada.** La API ofrece salidas con gramática garantizada, pero el esquema
   clínico completo excedió el límite de tamaño de la gramática. Se optó por incluir el JSON
   Schema en el prompt y validar localmente con Pydantic, con reintento automático que
   devuelve al modelo el error de validación. En la práctica no hubo reintentos.
3. **Formato largo para medicamentos y laboratorios.** Una fila por paciente no representa
   relaciones muchos a uno. El formato largo es el estándar para análisis estadístico.
4. **Normalización.** El extractor expande abreviaturas y normaliza fármacos a principio
   activo. Esto hizo que la comparación exacta de texto fallara (HTA vs hipertensión arterial);
   la validación usa expansión de abreviaturas y coincidencia difusa por palabras clave.
5. **Fenotipo y perfil hemodinámico como variables derivadas.** El modelo los infiere con
   reglas explícitas en el prompt (FEVI <=40 ICFEr, etc.). Son ejemplos de "valor agregado"
   del modelo sobre la extracción literal.

## 5. Métricas (10 pacientes, `python validar.py`)
| Métrica | Resultado |
|---|---|
| Exactitud campos simples: edad, sexo, fecha ingreso, FEVI, fenotipo, perfil hemodinámico, 6 signos vitales, días UTI, desenlace (14 campos × 10 pacientes) | **100%** (140/140) |
| Medicamentos (F1 por principio activo) | **1.00** |
| Laboratorios (F1) | **0.99** |
| Comorbilidades (F1) | **0.94** |
| Terapias (F1) | **0.90** |
| Diagnósticos secundarios (F1) | **0.86** |
| Antecedentes (F1) | **0.84** |
| Recall en todas las listas | 0.94 a 1.00 |
| Costo API total (generación + extracción, 20 llamadas) | < 2 USD |
| Tiempo por ficha (extracción) | ~1 min |

Lectura: los campos numéricos y categóricos se extraen sin error. En las listas, el recall es
casi perfecto (el modelo no omite información) y la pérdida de precisión proviene de que el
extractor descompone ítems compuestos de la verdad en varios ítems más específicos
(ej. "IAM 2019 con angioplastía" → dos antecedentes), lo que el emparejamiento uno a uno
penaliza. No se detectaron errores clínicos de contenido en la revisión manual de P01.

## 6. Limitaciones
- Verdad de referencia generada por el mismo modelo: mide consistencia, no exactitud frente a
  un gold standard humano. Siguiente paso: revisión por dos clínicos de una muestra.
- 10 pacientes: suficiente para prototipo, insuficiente para estimar error con precisión.
- Fichas sintéticas son más ordenadas que las reales. Las reales tendrán ruido de copia/pega,
  errores tipográficos y secciones faltantes.
- Datos reales exigen anonimización y aprobación de comité de ética.

## 7. Trabajo futuro (prototipo → app)
1. Lectura de sabanillas fotografiadas: tabla horaria de signos vitales e infusiones.
2. Revisión humana en la interfaz: aceptar/corregir cada campo y guardar la corrección
   (genera un gold standard incremental y permite medir exactitud real).
3. Exportación a REDCap y a formato CDISC/OMOP.
4. Esquemas para otras patologías de UTI (sepsis, EPOC exacerbado, cetoacidosis).
5. Evaluar un modelo local para datos reales sin salida de la red hospitalaria.
