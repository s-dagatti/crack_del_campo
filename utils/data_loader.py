# utils/data_loader.py

import re
import unicodedata
from pathlib import Path

import pandas as pd


# =====================================================
# RUTAS Y URL
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

CLIENTES_FILE = DATA_DIR / "base_de_clientes.csv"
OCIOSOS_FILE = DATA_DIR / "motivos_ociosos.csv"

USO_TEC_URL = (
    "https://raw.githubusercontent.com/"
    "s-dagatti/uso-tec-v2/main/"
    "datos_consolidados_conci.csv"
)


# =====================================================
# MAPEO BASE DE CLIENTES
# =====================================================

COLUMN_MAPPING_CLIENTES = {
    # Número de serie
    "numero_de_serie": "numero_serie",
    "numero_de_serie_de_la_maquina": "numero_serie",
    "nro_de_serie": "numero_serie",
    "nro_serie": "numero_serie",
    "serie": "numero_serie",
    "serial_number": "numero_serie",
    "machine_serial_number": "numero_serie",

    # Cliente
    "cliente": "cliente",
    "nombre_cliente": "cliente",

    # Organización
    "organizacion": "organizacion",
    "nombre_organizacion": "organizacion",
    "organization_name": "organizacion",

    # ID organización
    "id_organizacion": "org_id",
    "identificador_de_organizacion": "org_id",
    "organization_id": "org_id",
    "org_id": "org_id",

    # Ubicación
    "sucursal": "sucursal",
    "pais": "pais",
    "provincia": "provincia",
    "ciudad": "ciudad",

    # Operario
    "nombre_operario": "operario",
    "nombre_del_operario": "operario",
    "nombre_completo_del_operador": "operario",
    "operario": "operario",
    "operador": "operario",

    # Teléfono
    "telefono": "telefono",
    "numero_de_telefono": "telefono",
    "nro_telefono": "telefono",
    "whatsapp": "telefono",

    # Categoría
    "categoria": "categoria",
    "segmento": "categoria",
    "crack_campo": "categoria",
    "categoria_crack_del_campo": "categoria",
    "segmento_crack_del_campo": "categoria",
}


# =====================================================
# MAPEO USO TECNOLÓGICO
# =====================================================

COLUMN_MAPPING_USO_TEC = {
    # Número de serie
    "numero_de_serie": "numero_serie",
    "numero_de_serie_de_la_maquina": "numero_serie",
    "nro_de_serie": "numero_serie",
    "nro_serie": "numero_serie",
    "serie": "numero_serie",
    "serial_number": "numero_serie",
    "machine_serial_number": "numero_serie",

    # Organización
    "organization_id": "org_id",
    "identificador_de_organizacion": "org_id",
    "id_organizacion": "org_id",
    "org_id": "org_id",

    "organization_name": "organizacion",
    "organizacion": "organizacion",

    # Periodo semanal
    "fecha_de_inicio": "fecha_inicio",
    "fecha_inicio": "fecha_inicio",
    "start_date": "fecha_inicio",
    "period_start": "fecha_inicio",

    "fecha_de_terminacion": "fecha_fin",
    "fecha_de_finalizacion": "fecha_fin",
    "fecha_fin": "fecha_fin",
    "end_date": "fecha_fin",
    "period_end": "fecha_fin",

    # AutoTrac
    "autotrac": "autotrac",
    "autotrac_activo": "autotrac",
    "autotractm_activo": "autotrac",
    "autotrac_pct": "autotrac",
    "autotrac_porcentaje": "autotrac",

    # Turn Automation
    "turn_automation": "turn_automation",
    "automatizacion_de_maniobras_autotrac_activo":
        "turn_automation",
    "automatizacion_de_maniobras_autotractm_activo":
        "turn_automation",
    "turn_automation_pct": "turn_automation",
    "turn_automation_porcentaje": "turn_automation",

    # AutoPath
    "autopath": "autopath",
    "autopath_activo": "autopath",
    "autopathtm_activo": "autopath",
    "autopath_pct": "autopath",
    "autopath_porcentaje": "autopath",

    # Implement Guidance
    "implement_guidance": "implement_guidance",
    "guiado_pasivo_de_implemento_autotrac_activo":
        "implement_guidance",
    "guiado_pasivo_de_implemento_autotractm_activo":
        "implement_guidance",
    "implement_guidance_pct": "implement_guidance",
    "implement_guidance_porcentaje": "implement_guidance",

    # Efficiency Manager
    "efficiency_manager": "efficiency_manager",
    "tiempo_de_activacion_de_efficiency_manager_automatico":
        "efficiency_manager",
    "tiempo_de_activacion_de_efficiency_managertm_automatico":
        "efficiency_manager",
    "efficiency_manager_pct": "efficiency_manager",
    "ef_manager": "efficiency_manager",
    "ef_manager_pct": "efficiency_manager",

    # Field Cruise
    "field_cruise": "field_cruise",
    "fieldcruise_activado": "field_cruise",
    "fieldcruisetm_activado": "field_cruise",
    "field_cruise_pct": "field_cruise",
    "f_cruise": "field_cruise",
    "f_cruise_pct": "field_cruise",
}


# =====================================================
# MAPEO MOTIVOS OCIOSOS
# =====================================================

COLUMN_MAPPING_OCIOSIDAD = {
    # Número de serie
    "numero_de_serie": "numero_serie",
    "numero_de_serie_de_la_maquina": "numero_serie",
    "nro_de_serie": "numero_serie",
    "nro_serie": "numero_serie",
    "serie": "numero_serie",

    # Organización
    "organizacion": "organizacion",
    "identificador_de_organizacion": "org_id",
    "id_organizacion": "org_id",

    # Periodo semanal
    "fecha_de_inicio": "fecha_inicio",
    "fecha_inicio": "fecha_inicio",

    "fecha_de_terminacion": "fecha_fin",
    "fecha_fin": "fecha_fin",

    # Motivos ociosos
    "cancelada_periodo": "cancelada",
    "cancelada": "cancelada",

    "sin_definir_periodo": "sin_definir",
    "sin_definir": "sin_definir",

    "ignorada_periodo": "ignorada",
    "ignorada": "ignorada",

    # Utilización
    "utilizacion_trabajo": "trabajo",
    "utilizacion_transporte": "transporte",
    "utilizacion_ralenti": "ralenti",
}


# =====================================================
# FUNCIONES AUXILIARES
# =====================================================

def normalizar_nombre_columna(nombre):
    """
    Convierte un encabezado a minúsculas, elimina tildes
    y sustituye espacios y símbolos por guiones bajos.
    """

    nombre = str(nombre).strip()

    nombre = unicodedata.normalize(
        "NFKD",
        nombre,
    )

    nombre = "".join(
        caracter
        for caracter in nombre
        if not unicodedata.combining(caracter)
    )

    nombre = nombre.lower()
    nombre = nombre.replace("%", " pct ")
    nombre = re.sub(r"[^a-z0-9]+", "_", nombre)
    nombre = re.sub(r"_+", "_", nombre)

    return nombre.strip("_")


def normalizar_encabezados(df, mapping):
    df = df.copy()

    df.columns = [
        normalizar_nombre_columna(columna)
        for columna in df.columns
    ]

    df = df.rename(columns=mapping)

    return df


def leer_csv_flexible(origen):
    """
    Detecta automáticamente el separador del CSV.
    """

    return pd.read_csv(
        origen,
        sep=None,
        engine="python",
        encoding="utf-8-sig",
    )


def validar_columnas(df, requeridas, nombre_fuente):
    faltantes = [
        columna
        for columna in requeridas
        if columna not in df.columns
    ]

    if faltantes:
        raise ValueError(
            f"Faltan columnas en {nombre_fuente}: "
            f"{faltantes}. Columnas disponibles: "
            f"{df.columns.tolist()}"
        )


def normalizar_numero_serie(df):
    """
    Normaliza exclusivamente el número de serie.
    """

    df = df.copy()

    validar_columnas(
        df,
        ["numero_serie"],
        "normalización del número de serie",
    )

    df["numero_serie"] = (
        df["numero_serie"]
        .astype("string")
        .str.strip()
        .str.upper()
        .str.replace(
            r"[^A-Z0-9]",
            "",
            regex=True,
        )
    )

    df = df[
        df["numero_serie"].notna()
        & df["numero_serie"].ne("")
        & df["numero_serie"].ne("NAN")
        & df["numero_serie"].ne("NONE")
    ].copy()

    return df


def convertir_porcentaje(serie):
    """
    Convierte valores como 85, 85%, 0,85 o 0.85
    a una escala porcentual de 0 a 100.
    """

    texto = (
        serie
        .astype("string")
        .str.strip()
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.replace(r"\s+", "", regex=True)
    )

    valores = pd.to_numeric(
        texto,
        errors="coerce",
    )

    # Valores entre 0 y 1 se interpretan como proporciones.
    mascara_decimal = (
        valores.notna()
        & valores.ge(0)
        & valores.le(1)
    )

    valores.loc[mascara_decimal] = (
        valores.loc[mascara_decimal] * 100
    )

    return valores.clip(
        lower=0,
        upper=100,
    )


def normalizar_porcentajes(df):
    df = df.copy()

    columnas = [
        "autotrac",
        "turn_automation",
        "autopath",
        "implement_guidance",
        "efficiency_manager",
        "field_cruise",
        "cancelada",
        "sin_definir",
        "ignorada",
        "trabajo",
        "transporte",
        "ralenti",
    ]

    for columna in columnas:
        if columna in df.columns:
            df[columna] = convertir_porcentaje(
                df[columna]
            )

    return df


def normalizar_fechas(df):
    df = df.copy()

    for columna in [
        "fecha_inicio",
        "fecha_fin",
    ]:
        if columna in df.columns:
            df[columna] = pd.to_datetime(
                df[columna],
                errors="coerce",
                dayfirst=True,
            ).dt.normalize()

    return df


# =====================================================
# CARGA DE PARTICIPANTES
# =====================================================

def cargar_clientes():
    if not CLIENTES_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró la base de clientes: "
            f"{CLIENTES_FILE}"
        )

    df = leer_csv_flexible(
        CLIENTES_FILE
    )

    df = normalizar_encabezados(
        df,
        COLUMN_MAPPING_CLIENTES,
    )

    validar_columnas(
        df,
        ["numero_serie"],
        "base_de_clientes.csv",
    )

    df = normalizar_numero_serie(df)

    # La dimensión de clientes debe tener una sola fila
    # por número de serie.
    df = df.drop_duplicates(
        subset=["numero_serie"],
        keep="first",
    )

    return df


# =====================================================
# CARGA DE USO TECNOLÓGICO
# =====================================================

def cargar_uso_tecnologia():
    try:
        df = leer_csv_flexible(
            USO_TEC_URL
        )

    except Exception as error:
        raise RuntimeError(
            "No fue posible leer el CSV de uso-tec-v2: "
            f"{error}"
        ) from error

    df = normalizar_encabezados(
        df,
        COLUMN_MAPPING_USO_TEC,
    )

    validar_columnas(
        df,
        [
            "numero_serie",
            "fecha_inicio",
            "fecha_fin",
            "autotrac",
            "turn_automation",
            "autopath",
            "implement_guidance",
            "efficiency_manager",
            "field_cruise",
        ],
        "datos_consolidados_conci.csv",
    )

    df = normalizar_numero_serie(df)
    df = normalizar_fechas(df)
    df = normalizar_porcentajes(df)

    metricas = [
        "autotrac",
        "turn_automation",
        "autopath",
        "implement_guidance",
        "efficiency_manager",
        "field_cruise",
    ]

    dimensiones_adicionales = [
        columna
        for columna in [
            "maquina",
            "modelo",
            "tipo",
            "sucursal",
        ]
        if columna in df.columns
    ]

    agregaciones = {
        columna: "mean"
        for columna in metricas
    }

    agregaciones.update(
        {
            columna: "first"
            for columna in dimensiones_adicionales
        }
    )

    # Una fila por máquina y semana.
    df = (
        df
        .groupby(
            [
                "numero_serie",
                "fecha_inicio",
                "fecha_fin",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(agregaciones)
    )

    return df


# =====================================================
# CARGA DE MOTIVOS OCIOSOS
# =====================================================

def cargar_ociosidad():
    if not OCIOSOS_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró la base de ociosidad: "
            f"{OCIOSOS_FILE}"
        )

    df = leer_csv_flexible(
        OCIOSOS_FILE
    )

    df = normalizar_encabezados(
        df,
        COLUMN_MAPPING_OCIOSIDAD,
    )

    validar_columnas(
        df,
        [
            "numero_serie",
            "fecha_inicio",
            "fecha_fin",
            "cancelada",
            "sin_definir",
            "ignorada",
        ],
        "motivos_ociosos.csv",
    )

    df = normalizar_numero_serie(df)
    df = normalizar_fechas(df)
    df = normalizar_porcentajes(df)

    return df


# =====================================================
# CÁLCULO DE OCIOSIDAD
# =====================================================

def calcular_ociosidad(df):
    """
    Calcula los indicadores de ociosidad sobre la propia
    tabla de motivos ociosos.

    Esta función no realiza merges.
    """

    df = df.copy()

    columnas_ociosas = [
        "cancelada",
        "sin_definir",
        "ignorada",
    ]

    for columna in columnas_ociosas:
        if columna not in df.columns:
            df[columna] = 0.0

        df[columna] = (
            pd.to_numeric(
                df[columna],
                errors="coerce",
            )
            .fillna(0.0)
        )

    # Cálculo definido para el desafío:
    # cancelada / (cancelada + sin definir + ignorada)
    denominador = (
        df["cancelada"]
        + df["sin_definir"]
        + df["ignorada"]
    )

    df["ocio_controlable"] = 0.0

    mascara_valida = denominador.gt(0)

    df.loc[
        mascara_valida,
        "ocio_controlable",
    ] = (
        df.loc[mascara_valida, "cancelada"]
        / denominador.loc[mascara_valida]
        * 100
    )

    df["ocio_controlable"] = (
        df["ocio_controlable"]
        .clip(lower=0, upper=100)
    )

    df["score_ociosidad"] = (
        100 - df["ocio_controlable"]
    ).clip(lower=0, upper=100)

    # Una fila por máquina y semana.
    df = (
        df
        .groupby(
            [
                "numero_serie",
                "fecha_inicio",
                "fecha_fin",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            {
                "cancelada": "mean",
                "sin_definir": "mean",
                "ignorada": "mean",
                "ocio_controlable": "mean",
                "score_ociosidad": "mean",
            }
        )
    )

    return df


# =====================================================
# CONSTRUCCIÓN DEL DATAFRAME MAESTRO
# =====================================================

def construir_dataframe_maestro():
    clientes = cargar_clientes()
    uso_tec = cargar_uso_tecnologia()
    ociosidad = cargar_ociosidad()

    ociosidad = calcular_ociosidad(
        ociosidad
    )

    # Primero genera una fila por participante y semana.
    df = clientes.merge(
        uso_tec,
        on="numero_serie",
        how="left",
        suffixes=("_clientes", "_uso"),
    )

    # Después incorpora la ociosidad de esa misma semana.
    df = df.merge(
        ociosidad,
        on=[
            "numero_serie",
            "fecha_inicio",
            "fecha_fin",
        ],
        how="left",
        validate="many_to_one",
    )

    # =================================================
    # UNIFICACIÓN DE SUCURSAL
    # =================================================

    if "sucursal_clientes" in df.columns:
        df["sucursal"] = df[
            "sucursal_clientes"
        ]

        if "sucursal_uso" in df.columns:
            df["sucursal"] = (
                df["sucursal"]
                .fillna(df["sucursal_uso"])
            )

    elif "sucursal_uso" in df.columns:
        df["sucursal"] = df["sucursal_uso"]

    elif "sucursal" not in df.columns:
        df["sucursal"] = "Sin sucursal"

    # =================================================
    # COLUMNAS ESTÁNDAR
    # =================================================

    if "cliente" not in df.columns:
        if "organizacion" in df.columns:
            df["cliente"] = df["organizacion"]
        else:
            df["cliente"] = "Sin cliente"

    if "operario" not in df.columns:
        df["operario"] = "Sin asignar"

    if "categoria" not in df.columns:
        df["categoria"] = "Sin categoría"

    for columna in [
        "sucursal",
        "cliente",
        "operario",
        "categoria",
    ]:
        df[columna] = (
            df[columna]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # =================================================
    # NORMALIZACIÓN DE CATEGORÍAS
    # =================================================

    df["categoria"] = (
        df["categoria"]
        .replace("", "SIN CATEGORÍA")
        .str.upper()
    )

    df["categoria"] = df["categoria"].replace(
        {
            "BASE": "BASIC",
            "BÁSICO": "BASIC",
            "BASICO": "BASIC",
            "GUIADO BÁSICO": "BASIC",
            "GUIADO BASICO": "BASIC",
            "AVANZADO": "ELITE",
            "GUIADO AVANZADO": "ELITE",
        }
    )

    # =================================================
    # VARIABLES NUMÉRICAS
    # =================================================

    columnas_numericas = [
        "autotrac",
        "turn_automation",
        "autopath",
        "implement_guidance",
        "efficiency_manager",
        "field_cruise",
        "cancelada",
        "sin_definir",
        "ignorada",
        "ocio_controlable",
        "score_ociosidad",
    ]

    for columna in columnas_numericas:
        if columna not in df.columns:
            df[columna] = 0.0

        df[columna] = pd.to_numeric(
            df[columna],
            errors="coerce",
        )

    # No convertimos inmediatamente los datos tecnológicos
    # ausentes en cero. NaN significa que no existe información
    # para esa máquina y semana.
    columnas_ociosidad = [
        "cancelada",
        "sin_definir",
        "ignorada",
        "ocio_controlable",
        "score_ociosidad",
    ]

    for columna in columnas_ociosidad:
        df[columna] = df[columna].fillna(0.0)

    # =================================================
    # LIMPIEZA FINAL
    # =================================================

    df = df.drop(
        columns=[
            "sucursal_clientes",
            "sucursal_uso",
        ],
        errors="ignore",
    )

    df = df.sort_values(
        [
            "numero_serie",
            "fecha_inicio",
            "fecha_fin",
        ],
        ascending=True,
        na_position="last",
    )

    return df.reset_index(drop=True)


# =====================================================
# FUNCIÓN PRINCIPAL
# =====================================================

def cargar_datos():
    return construir_dataframe_maestro()
