"""Bloque 1: genera N fichas clínicas sintéticas (estilo SINA, Markdown) con su
verdad de referencia en JSON, para pacientes con IC descompensada en UTI.

Uso:  python generar_sinteticos.py [n_pacientes]
Salida: data/fichas/Pxx.md  y  data/verdad/Pxx.json
"""
import json
import sys
from pathlib import Path

from pydantic import BaseModel, Field

from llm import get_client, parse_json
from schema import FichaExtraida

ROOT = Path(__file__).parent
DIR_FICHAS = ROOT / "data" / "fichas"
DIR_VERDAD = ROOT / "data" / "verdad"

# Escenarios para asegurar diversidad clínica entre los 10 pacientes.
ESCENARIOS = [
    "Hombre 68 años, ICFEr (FEVI 25%), perfil caliente-húmedo, abandono de tratamiento. Evoluciona bien con diuréticos EV.",
    "Mujer 79 años, ICFEp (FEVI 58%), HTA mal controlada y FA con RVR como gatillante. Requiere control de frecuencia.",
    "Hombre 55 años, ICFEr (FEVI 20%), perfil frío-húmedo, requiere dobutamina en BIC y traslado a UCI.",
    "Mujer 72 años, ICFElr (FEVI 45%), neumonía como descompensante, VMNI las primeras 48 h.",
    "Hombre 61 años, ICFEr (FEVI 30%), ERC etapa 4, síndrome cardiorrenal, hiperkalemia, evaluación por nefrología.",
    "Mujer 84 años, ICFEp, DM2 insulinorrequiriente, anasarca, respuesta lenta a diuréticos, requiere asociar tiazida.",
    "Hombre 48 años, miocardiopatía dilatada OH, ICFEr (FEVI 18%), hipotensión, noradrenalina por 72 h.",
    "Mujer 66 años, ICFEr (FEVI 35%), SCA sin SDST como gatillante, troponina elevada, coronariografía diferida.",
    "Hombre 75 años, EPOC + ICFEp, dificultad diagnóstica, NT-proBNP intermedio, oxigenoterapia por naricera.",
    "Mujer 58 años, valvulopatía mitral severa, ICFEr (FEVI 38%), fallece en UTI al día 5.",
]

SYSTEM = """Eres un médico intensivista chileno que redacta fichas clínicas en el sistema SINA
de un hospital público. Escribes en español, con el estilo real de una ficha: abreviaturas
locales (HTA, DM2, ERC, FA, RVR, ICC, EPA, VMNI, BIC, EV, VO, SF, PAM, Sat, FR, FC, Tº,
Rx Tx, ECG, Eco, FEVI, NT-proBNP, crea, BUN, K, Na, GSA, PCR, Hcto), frases telegráficas,
signos vitales escritos como 'PA 100/60 FC 112 FR 26 Sat 89% amb', indicaciones con dosis
y frecuencia ('furosemida 40 mg EV c/8h'), y evoluciones diarias. Todos los datos son
SINTÉTICOS: nombres inventados, RUT inventado con formato XX.XXX.XXX-X, sin ninguna
persona real."""

PROMPT = """Genera la ficha clínica sintética del paciente {pid} en UTI (unidad de tratamiento
intermedio) con diagnóstico de insuficiencia cardíaca descompensada.

Escenario a seguir: {escenario}

La ficha en Markdown debe tener estas secciones: Identificación (nombre y RUT ficticios),
Motivo de ingreso, Antecedentes, Anamnesis, Examen físico de ingreso con signos vitales,
Laboratorio e imágenes, Diagnósticos, Indicaciones (medicamentos con dosis, vía y frecuencia;
drogas vasoactivas con dosis en mcg/kg/min si corresponde), y Evolución diaria (3 a 6 días)
donde se ajustan dosis, se suspenden o inician fármacos y terapias, y termina con el desenlace.
Fechas concretas del año 2025. Extensión aproximada: 500 a 800 palabras.

Luego completa la verdad de referencia (campo `verdad`) con exactamente lo que dice la ficha,
usando id_paciente = "{pid}". La duración en días de medicamentos y terapias debe calcularse
desde la evolución. Si un dato no aparece en la ficha, déjalo null."""


class FichaSintetica(BaseModel):
    ficha_markdown: str = Field(description="La ficha clínica completa en Markdown")
    verdad: FichaExtraida


def generar(pid: str, escenario: str, client) -> FichaSintetica:
    return parse_json(client, system=SYSTEM, modelo=FichaSintetica,
                      user=PROMPT.format(pid=pid, escenario=escenario))


def main(n: int) -> None:
    DIR_FICHAS.mkdir(parents=True, exist_ok=True)
    DIR_VERDAD.mkdir(parents=True, exist_ok=True)
    client = get_client()
    for i in range(n):
        pid = f"P{i + 1:02d}"
        destino = DIR_FICHAS / f"{pid}.md"
        if destino.exists():
            print(f"{pid}: ya existe, se omite")
            continue
        print(f"{pid}: generando...", end=" ", flush=True)
        ficha = generar(pid, ESCENARIOS[i % len(ESCENARIOS)], client)
        destino.write_text(ficha.ficha_markdown, encoding="utf-8")
        (DIR_VERDAD / f"{pid}.json").write_text(
            ficha.verdad.model_dump_json(indent=2), encoding="utf-8")
        print(f"ok ({len(ficha.ficha_markdown.split())} palabras, "
              f"{len(ficha.verdad.medicamentos)} fármacos, {len(ficha.verdad.laboratorios)} labs)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
