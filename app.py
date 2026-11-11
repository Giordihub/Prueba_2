"""Bloque 3: interfaz web del prototipo (Streamlit).
Uso: streamlit run app.py
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from schema import FichaExtraida

ROOT = Path(__file__).parent
DIR_FICHAS = ROOT / "data" / "fichas"
DIR_VERDAD = ROOT / "data" / "verdad"
DIR_EXTRAIDOS = ROOT / "output" / "extraidos"
XLSX = ROOT / "output" / "dataset.xlsx"

st.set_page_config(page_title="UTI Extractor", page_icon="🫀", layout="wide")
st.title("🫀 UTI Extractor — IC descompensada")
st.caption("Prototipo: de ficha clínica en texto libre a dataset de investigación. Datos 100% sintéticos.")


@st.cache_data
def cargar_extraidos() -> dict[str, FichaExtraida]:
    return {p.stem: FichaExtraida.model_validate_json(p.read_text(encoding="utf-8"))
            for p in sorted(DIR_EXTRAIDOS.glob("*.json"))}


def completitud(f: FichaExtraida) -> float:
    """% de campos simples del paciente que tienen dato."""
    campos = [f.edad, f.sexo, f.fecha_ingreso, f.fevi, f.fenotipo_ic, f.factor_descompensante,
              f.perfil_hemodinamico, f.dias_estadia_uti, f.desenlace,
              f.signos_vitales_ingreso.pa_sistolica, f.signos_vitales_ingreso.fc,
              f.signos_vitales_ingreso.sat_o2]
    return round(100 * sum(c is not None for c in campos) / len(campos))


extraidos = cargar_extraidos()
if not extraidos:
    st.warning("Aún no hay extracciones. Ejecuta `python extract.py` y recarga la página.")
    st.stop()

tab_paciente, tab_cohorte, tab_dataset = st.tabs(["🧾 Paciente", "📊 Cohorte", "⬇️ Dataset"])

# ---------------- Paciente ----------------
with tab_paciente:
    pid = st.selectbox("Paciente", list(extraidos.keys()))
    f = extraidos[pid]
    col_izq, col_der = st.columns([1, 1])

    with col_izq:
        st.subheader("Ficha original")
        ficha_md = (DIR_FICHAS / f"{pid}.md")
        st.markdown(ficha_md.read_text(encoding="utf-8") if ficha_md.exists() else "_No disponible_")

    with col_der:
        st.subheader("Extracción estructurada")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Edad / Sexo", f"{f.edad or '?'} / {f.sexo or '?'}")
        m2.metric("FEVI", f"{f.fevi:.0f}%" if f.fevi is not None else "—", f.fenotipo_ic or "")
        m3.metric("Días UTI", f.dias_estadia_uti if f.dias_estadia_uti is not None else "—")
        m4.metric("Completitud", f"{completitud(f)}%")

        st.markdown(f"**Diagnóstico principal:** {f.diagnostico_principal}")
        st.markdown(f"**Factor descompensante:** {f.factor_descompensante or '—'}  ·  "
                    f"**Perfil:** {f.perfil_hemodinamico or '—'}  ·  **Desenlace:** {f.desenlace or '—'}")
        st.markdown(f"**Condición al ingreso:** {f.condicion_ingreso}")

        sv = f.signos_vitales_ingreso
        st.markdown(f"**Signos vitales ingreso:** PA {sv.pa_sistolica}/{sv.pa_diastolica} · FC {sv.fc} · "
                    f"FR {sv.fr} · Sat {sv.sat_o2}% · Tº {sv.temperatura} · O2: {sv.soporte_o2 or '—'}")

        c1, c2 = st.columns(2)
        c1.markdown("**Comorbilidades**\n" + "\n".join(f"- {c}" for c in f.comorbilidades) or "—")
        c2.markdown("**Antecedentes**\n" + "\n".join(f"- {a}" for a in f.antecedentes) or "—")

        st.markdown("**Medicamentos y terapias**")
        meds = pd.DataFrame([m.model_dump() for m in f.medicamentos])
        if not meds.empty:
            st.dataframe(meds, hide_index=True, width='stretch')
        ter = pd.DataFrame([t.model_dump() for t in f.terapias])
        if not ter.empty:
            st.dataframe(ter, hide_index=True, width='stretch')

        st.markdown("**Laboratorios**")
        labs = pd.DataFrame([l.model_dump() for l in f.laboratorios])
        if not labs.empty:
            st.dataframe(labs, hide_index=True, width='stretch')

        if f.observaciones:
            st.info(f"Observaciones del modelo: {f.observaciones}")

        verdad = DIR_VERDAD / f"{pid}.json"
        if verdad.exists():
            with st.expander("Comparar con verdad de referencia (JSON)"):
                v = json.loads(verdad.read_text(encoding="utf-8"))
                e = json.loads(f.model_dump_json())
                campos_simples = ["edad", "sexo", "fecha_ingreso", "fevi", "fenotipo_ic",
                                  "factor_descompensante", "perfil_hemodinamico",
                                  "dias_estadia_uti", "desenlace"]
                comp = pd.DataFrame({
                    "campo": campos_simples,
                    "verdad": [str(v.get(c)) for c in campos_simples],
                    "extraido": [str(e.get(c)) for c in campos_simples],
                })
                comp["coincide"] = comp["verdad"].str.lower() == comp["extraido"].str.lower()
                st.dataframe(comp, hide_index=True, width='stretch')

# ---------------- Cohorte ----------------
with tab_cohorte:
    df = pd.DataFrame([{
        "id": f.id_paciente, "edad": f.edad, "sexo": f.sexo, "fevi": f.fevi,
        "fenotipo": f.fenotipo_ic, "perfil": f.perfil_hemodinamico,
        "descompensante": f.factor_descompensante, "n_comorb": len(f.comorbilidades),
        "n_farmacos": len(f.medicamentos), "dias_uti": f.dias_estadia_uti,
        "desenlace": f.desenlace, "completitud_%": completitud(f),
    } for f in extraidos.values()])

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Pacientes", len(df))
    k2.metric("Edad media", f"{df['edad'].mean():.0f} años" if df['edad'].notna().any() else "—")
    k3.metric("FEVI media", f"{df['fevi'].mean():.0f}%" if df['fevi'].notna().any() else "—")
    k4.metric("Mediana días UTI", f"{df['dias_uti'].median():.0f}" if df['dias_uti'].notna().any() else "—")

    g1, g2, g3 = st.columns(3)
    g1.markdown("**Fenotipo de IC**"); g1.bar_chart(df["fenotipo"].value_counts())
    g2.markdown("**Perfil hemodinámico**"); g2.bar_chart(df["perfil"].value_counts())
    g3.markdown("**Desenlace**"); g3.bar_chart(df["desenlace"].value_counts())

    st.markdown("**Fármacos más utilizados**")
    todos_meds = pd.Series([m.nombre for f in extraidos.values() for m in f.medicamentos])
    if not todos_meds.empty:
        st.bar_chart(todos_meds.value_counts().head(12))

    st.markdown("**Tabla de cohorte**")
    st.dataframe(df, hide_index=True, width='stretch')

# ---------------- Dataset ----------------
with tab_dataset:
    st.markdown("El dataset tiene cuatro hojas enlazadas por `id_paciente`: "
                "**Pacientes** (una fila por paciente), **Medicamentos**, **Terapias** y **Laboratorios** "
                "(formato largo, una fila por registro).")
    if XLSX.exists():
        st.download_button("⬇️ Descargar dataset.xlsx", XLSX.read_bytes(), "dataset.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        hojas = pd.read_excel(XLSX, sheet_name=None)
        hoja = st.selectbox("Vista previa de hoja", list(hojas.keys()))
        st.dataframe(hojas[hoja], hide_index=True, width='stretch')
    else:
        st.warning("Aún no existe output/dataset.xlsx. Ejecuta `python extract.py`.")
