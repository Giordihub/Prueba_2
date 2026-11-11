"""Esquema de datos para extracción de fichas clínicas de UTI.
Caso de uso inicial: insuficiencia cardíaca descompensada.
Este esquema es el contrato entre el modelo de lenguaje y el dataset final.
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class SignosVitales(BaseModel):
    pa_sistolica: Optional[int] = Field(None, description="Presión arterial sistólica en mmHg")
    pa_diastolica: Optional[int] = Field(None, description="Presión arterial diastólica en mmHg")
    fc: Optional[int] = Field(None, description="Frecuencia cardíaca en lpm")
    fr: Optional[int] = Field(None, description="Frecuencia respiratoria en rpm")
    sat_o2: Optional[int] = Field(None, description="Saturación de O2 en %")
    temperatura: Optional[float] = Field(None, description="Temperatura en °C")
    soporte_o2: Optional[str] = Field(None, description="Soporte de oxígeno al ingreso, ej: 'naricera 3 L/min', 'VMNI', 'ambiental'")


class Laboratorio(BaseModel):
    nombre: str = Field(description="Nombre del examen normalizado, ej: 'creatinina', 'NT-proBNP', 'sodio', 'potasio', 'troponina'")
    valor: Optional[float] = Field(None, description="Valor numérico")
    unidad: Optional[str] = Field(None, description="Unidad, ej: 'mg/dL', 'pg/mL', 'mEq/L'")
    fecha: Optional[str] = Field(None, description="Fecha del examen en formato AAAA-MM-DD si está disponible")


class Medicamento(BaseModel):
    nombre: str = Field(description="Principio activo normalizado, ej: 'furosemida', 'noradrenalina', 'enalapril'")
    dosis: Optional[str] = Field(None, description="Dosis tal como se indicó, ej: '40 mg', '0.1 mcg/kg/min'")
    via: Optional[str] = Field(None, description="Vía: 'EV', 'VO', 'SC', 'infusión continua', etc.")
    frecuencia: Optional[str] = Field(None, description="Frecuencia, ej: 'c/8h', 'BIC', 'día'")
    fecha_inicio: Optional[str] = Field(None, description="Fecha de inicio AAAA-MM-DD si está disponible")
    duracion_dias: Optional[int] = Field(None, description="Duración en días si se puede determinar")
    es_infusion_continua: bool = Field(False, description="True si es droga en bomba de infusión continua")


class Terapia(BaseModel):
    nombre: str = Field(description="Terapia no farmacológica, ej: 'VMNI', 'oxigenoterapia', 'hemodiálisis', 'CVC', 'ultrafiltración'")
    detalle: Optional[str] = Field(None, description="Parámetros o detalle, ej: 'CPAP 8 cmH2O'")
    fecha_inicio: Optional[str] = Field(None, description="Fecha de inicio AAAA-MM-DD si está disponible")
    duracion_dias: Optional[int] = Field(None, description="Duración en días si se puede determinar")


class FichaExtraida(BaseModel):
    """Dataset estructurado de un paciente con IC descompensada en UTI."""
    id_paciente: str = Field(description="Identificador de la ficha, ej: 'P01'")
    edad: Optional[int] = Field(None, description="Edad en años")
    sexo: Optional[Literal["M", "F"]] = None
    fecha_ingreso: Optional[str] = Field(None, description="Fecha de ingreso a UTI, AAAA-MM-DD")

    diagnostico_principal: str = Field(description="Diagnóstico principal del ingreso")
    diagnosticos_secundarios: List[str] = Field(default_factory=list)
    antecedentes: List[str] = Field(default_factory=list, description="Antecedentes médicos, quirúrgicos y hábitos (tabaquismo, OH)")
    comorbilidades: List[str] = Field(default_factory=list, description="Enfermedades crónicas activas: HTA, DM2, ERC, EPOC, FA, etc.")

    fevi: Optional[float] = Field(None, description="Fracción de eyección del VI en % si está documentada")
    fenotipo_ic: Optional[Literal["ICFEr", "ICFElr", "ICFEp", "no_determinado"]] = Field(
        None, description="ICFEr: FEVI<=40, ICFElr: 41-49, ICFEp: >=50, no_determinado si no hay FEVI")
    factor_descompensante: Optional[str] = Field(None, description="Causa de la descompensación, ej: 'abandono de tratamiento', 'infección respiratoria', 'FA con RVR', 'SCA'")

    condicion_ingreso: str = Field(description="Resumen breve de la condición clínica al ingreso")
    perfil_hemodinamico: Optional[Literal["caliente-humedo", "frio-humedo", "caliente-seco", "frio-seco", "no_determinado"]] = None
    signos_vitales_ingreso: SignosVitales

    laboratorios: List[Laboratorio] = Field(default_factory=list)
    medicamentos: List[Medicamento] = Field(default_factory=list)
    terapias: List[Terapia] = Field(default_factory=list)

    dias_estadia_uti: Optional[int] = None
    desenlace: Optional[Literal["traslado_sala", "traslado_uci", "alta_domicilio", "fallecido", "en_curso"]] = None
    observaciones: Optional[str] = Field(None, description="Dudas, datos ambiguos o campos que no se encontraron en la ficha")
