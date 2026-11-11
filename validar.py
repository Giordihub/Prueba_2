"""Bloque 4: mide la exactitud de la extracción contra la verdad de referencia.
Compara output/extraidos/Pxx.json vs data/verdad/Pxx.json.

Uso: python validar.py
Salida: tabla por campo en consola y output/validacion.xlsx
"""
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
DIR_VERDAD = ROOT / "data" / "verdad"
DIR_EXTRAIDOS = ROOT / "output" / "extraidos"

CAMPOS_SIMPLES = ["edad", "sexo", "fecha_ingreso", "fevi", "fenotipo_ic", "perfil_hemodinamico",
                  "dias_estadia_uti", "desenlace"]
CAMPOS_SV = ["pa_sistolica", "pa_diastolica", "fc", "fr", "sat_o2", "temperatura"]


ABREVIATURAS = {
    "hta": "hipertension arterial", "dm2": "diabetes mellitus tipo 2", "dm": "diabetes mellitus",
    "erc": "enfermedad renal cronica", "epoc": "enfermedad pulmonar obstructiva cronica",
    "fa": "fibrilacion auricular", "rvr": "respuesta ventricular rapida", "iam": "infarto agudo al miocardio",
    "ic": "insuficiencia cardiaca", "icc": "insuficiencia cardiaca congestiva", "icfer": "insuficiencia cardiaca fraccion eyeccion reducida",
    "icfep": "insuficiencia cardiaca fraccion eyeccion preservada", "oh": "alcohol", "tbq": "tabaquismo",
    "sca": "sindrome coronario agudo", "acv": "accidente cerebrovascular", "tep": "tromboembolismo pulmonar",
    "pcr": "proteina c reactiva", "glicemia": "glucemia", "crea": "creatinina", "hb": "hemoglobina",
    "hcto": "hematocrito", "k": "potasio", "na": "sodio", "vmni": "ventilacion mecanica no invasiva",
    "cvc": "cateter venoso central", "nac": "neumonia adquirida en la comunidad", "dg": "", "tto": "tratamiento",
}
STOPWORDS = {"de", "del", "la", "el", "en", "con", "por", "a", "al", "y", "o", "un", "una", "tipo", "cronica", "cronico"}


def norm(s) -> str:
    """Minúsculas, sin tildes, abreviaturas expandidas, sin puntuación."""
    s = unicodedata.normalize("NFKD", str(s).lower().strip())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9%./ ]", " ", s)
    return " ".join(ABREVIATURAS.get(t, t) for t in s.split())


def tokens(s: str) -> set[str]:
    return {t for t in norm(s).split() if t not in STOPWORDS and len(t) > 1}


def similares(a: str, b: str) -> bool:
    """Igualdad, contención o solapamiento de palabras clave >= 50%."""
    na, nb = norm(a), norm(b)
    if na == nb or na in nb or nb in na:
        return True
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / min(len(ta), len(tb)) >= 0.5


def f1_listas(verdad: list, extraido: list, clave=None) -> tuple[float, float, float]:
    """Precisión, recall y F1 entre dos listas con emparejamiento difuso uno a uno."""
    v = [str(x[clave] if clave else x) for x in verdad]
    e = [str(x[clave] if clave else x) for x in extraido]
    # Dedupe por nombre normalizado (el mismo fármaco con distintas dosis cuenta una vez)
    v = list({norm(x): x for x in v}.values()); e = list({norm(x): x for x in e}.values())
    if not v and not e:
        return 1.0, 1.0, 1.0
    libres = list(e); tp = 0
    for item in v:
        for cand in libres:
            if similares(item, cand):
                tp += 1; libres.remove(cand); break
    p = tp / len(e) if e else 0.0
    r = tp / len(v) if v else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f1


def main() -> None:
    filas_campo, filas_lista = [], []
    pares = [(p, DIR_EXTRAIDOS / p.name) for p in sorted(DIR_VERDAD.glob("*.json"))
             if (DIR_EXTRAIDOS / p.name).exists()]
    if not pares:
        raise SystemExit("No hay pares verdad/extraído para comparar.")

    for pv, pe in pares:
        v, e = json.load(open(pv, encoding="utf-8")), json.load(open(pe, encoding="utf-8"))
        pid = v["id_paciente"]
        for c in CAMPOS_SIMPLES:
            filas_campo.append({"id": pid, "campo": c, "verdad": v.get(c), "extraido": e.get(c),
                                "coincide": norm(v.get(c)) == norm(e.get(c))})
        for c in CAMPOS_SV:
            vv, ee = v["signos_vitales_ingreso"].get(c), e["signos_vitales_ingreso"].get(c)
            filas_campo.append({"id": pid, "campo": f"sv.{c}", "verdad": vv, "extraido": ee,
                                "coincide": vv == ee})
        for lista, clave in [("comorbilidades", None), ("antecedentes", None),
                             ("diagnosticos_secundarios", None),
                             ("medicamentos", "nombre"), ("terapias", "nombre"),
                             ("laboratorios", "nombre")]:
            p, r, f1 = f1_listas(v.get(lista, []), e.get(lista, []), clave)
            filas_lista.append({"id": pid, "lista": lista, "n_verdad": len(v.get(lista, [])),
                                "n_extraido": len(e.get(lista, [])),
                                "precision": round(p, 2), "recall": round(r, 2), "f1": round(f1, 2)})

    df_c = pd.DataFrame(filas_campo)
    df_l = pd.DataFrame(filas_lista)
    res_campo = (df_c.groupby("campo")["coincide"].mean().mul(100).round(0)
                 .rename("exactitud_%").reset_index())
    res_lista = df_l.groupby("lista")[["precision", "recall", "f1"]].mean().round(2).reset_index()

    print(f"\nPacientes evaluados: {len(pares)}")
    print("\n== Exactitud por campo simple (%) ==")
    print(res_campo.to_string(index=False))
    print(f"\nExactitud global campos simples: {df_c['coincide'].mean() * 100:.0f}%")
    print("\n== Listas: precisión / recall / F1 promedio ==")
    print(res_lista.to_string(index=False))

    destino = ROOT / "output" / "validacion.xlsx"
    with pd.ExcelWriter(destino, engine="openpyxl") as xw:
        res_campo.to_excel(xw, sheet_name="Resumen_campos", index=False)
        res_lista.to_excel(xw, sheet_name="Resumen_listas", index=False)
        df_c.to_excel(xw, sheet_name="Detalle_campos", index=False)
        df_l.to_excel(xw, sheet_name="Detalle_listas", index=False)
    print(f"\nDetalle guardado en {destino}")


if __name__ == "__main__":
    main()
