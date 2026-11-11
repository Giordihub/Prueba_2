"""Bloque 2: extrae variables estructuradas de cada ficha en data/fichas/*.md
y construye el dataset en output/dataset.xlsx (hojas Pacientes, Medicamentos,
Terapias, Laboratorios) más un JSON por paciente en output/extraidos/.

Uso:  python extract.py            # procesa todas las fichas
      python extract.py P03        # procesa una sola
"""
import json
import sys
from pathlib import Path

import pandas as pd

from llm import get_client, parse_json
from schema import FichaExtraida

ROOT = Path(__file__).parent
DIR_FICHAS = ROOT / "data" / "fichas"
DIR_OUT = ROOT / "output"
DIR_EXTRAIDOS = DIR_OUT / "extraidos"

SYSTEM = """Eres un asistente de investigación clínica experto en cardiología e intensivo.
Tu tarea es leer una ficha clínica de UTI escrita en español chileno, con abreviaturas
locales, y extraer variables estructuradas para un dataset de investigación sobre
insuficiencia cardíaca descompensada.

Reglas:
- Extrae solo lo que está escrito o se deduce directamente de la ficha. No inventes.
- Si un dato no aparece, usa null. Anota en `observaciones` lo que no encontraste o fue ambiguo.
- Normaliza nombres de fármacos a principio activo en minúsculas y exámenes a nombres estándar.
- Expande abreviaturas en diagnósticos y comorbilidades (HTA -> hipertensión arterial).
- Signos vitales: los del ingreso a UTI, no los de la evolución.
- Duración de fármacos y terapias: cuéntala desde la evolución diaria (inicio a suspensión o
  último día registrado).
- Fenotipo IC según FEVI: <=40 ICFEr, 41-49 ICFElr, >=50 ICFEp.
- Perfil hemodinámico según congestión (húmedo/seco) y perfusión (caliente/frío) descritas.
- Fechas en formato AAAA-MM-DD."""


def extraer(pid: str, texto: str, client) -> FichaExtraida:
    user = (f"Identificador de la ficha: {pid}\n\n<ficha>\n{texto}\n</ficha>\n\n"
            "Extrae las variables del esquema.")
    ficha = parse_json(client, system=SYSTEM, modelo=FichaExtraida, user=user)
    ficha.id_paciente = pid
    return ficha


def construir_excel(fichas: list[FichaExtraida], destino: Path) -> None:
    pacientes, meds, terapias, labs = [], [], [], []
    for f in fichas:
        sv = f.signos_vitales_ingreso
        pacientes.append({
            "id_paciente": f.id_paciente, "edad": f.edad, "sexo": f.sexo,
            "fecha_ingreso": f.fecha_ingreso,
            "diagnostico_principal": f.diagnostico_principal,
            "diagnosticos_secundarios": "; ".join(f.diagnosticos_secundarios),
            "antecedentes": "; ".join(f.antecedentes),
            "comorbilidades": "; ".join(f.comorbilidades),
            "n_comorbilidades": len(f.comorbilidades),
            "fevi": f.fevi, "fenotipo_ic": f.fenotipo_ic,
            "factor_descompensante": f.factor_descompensante,
            "perfil_hemodinamico": f.perfil_hemodinamico,
            "condicion_ingreso": f.condicion_ingreso,
            "pa_sistolica": sv.pa_sistolica, "pa_diastolica": sv.pa_diastolica,
            "fc": sv.fc, "fr": sv.fr, "sat_o2": sv.sat_o2, "temperatura": sv.temperatura,
            "soporte_o2": sv.soporte_o2,
            "dias_estadia_uti": f.dias_estadia_uti, "desenlace": f.desenlace,
            "observaciones": f.observaciones,
        })
        for m in f.medicamentos:
            meds.append({"id_paciente": f.id_paciente, **m.model_dump()})
        for t in f.terapias:
            terapias.append({"id_paciente": f.id_paciente, **t.model_dump()})
        for lab in f.laboratorios:
            labs.append({"id_paciente": f.id_paciente, **lab.model_dump()})

    with pd.ExcelWriter(destino, engine="openpyxl") as xw:
        pd.DataFrame(pacientes).to_excel(xw, sheet_name="Pacientes", index=False)
        pd.DataFrame(meds).to_excel(xw, sheet_name="Medicamentos", index=False)
        pd.DataFrame(terapias).to_excel(xw, sheet_name="Terapias", index=False)
        pd.DataFrame(labs).to_excel(xw, sheet_name="Laboratorios", index=False)


def main(solo: str | None = None) -> None:
    DIR_EXTRAIDOS.mkdir(parents=True, exist_ok=True)
    client = get_client()
    archivos = sorted(DIR_FICHAS.glob(f"{solo or '*'}.md"))
    if not archivos:
        raise SystemExit("No hay fichas en data/fichas/. Ejecuta primero generar_sinteticos.py")

    fichas = []
    for path in archivos:
        pid = path.stem
        destino = DIR_EXTRAIDOS / f"{pid}.json"
        if destino.exists() and not solo:
            fichas.append(FichaExtraida.model_validate_json(destino.read_text(encoding="utf-8")))
            print(f"{pid}: ya extraída, se reutiliza")
            continue
        print(f"{pid}: extrayendo...", end=" ", flush=True)
        ficha = extraer(pid, path.read_text(encoding="utf-8"), client)
        destino.write_text(ficha.model_dump_json(indent=2), encoding="utf-8")
        fichas.append(ficha)
        print(f"ok ({len(ficha.medicamentos)} fármacos, {len(ficha.laboratorios)} labs, "
              f"{len(ficha.terapias)} terapias)")

    # Al final siempre reconstruimos el Excel con todo lo que haya en output/extraidos
    todas = [FichaExtraida.model_validate_json(p.read_text(encoding="utf-8"))
             for p in sorted(DIR_EXTRAIDOS.glob("*.json"))]
    construir_excel(todas, DIR_OUT / "dataset.xlsx")
    print(f"\nDataset: {DIR_OUT / 'dataset.xlsx'}  ({len(todas)} pacientes)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
