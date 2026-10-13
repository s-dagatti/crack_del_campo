# utils/data_loader.py

import pandas as pd
from pathlib import Path

# =====================================================
# PATHS
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent

CLIENTES_FILE = BASE_DIR / "data" / "base_de_clientes.csv"
OCIOSOS_FILE = BASE_DIR / "data" / "motivos_ociosos.csv"
USO_TEC_URL = (
    "https://raw.githubusercontent.com/"
    "s-dagatti/uso-tec-v2/main/"
    "datos_consolidados_conci.csv"
)


# =====================================================
# MAPEO USO TEC
# =====================================================

COLUMN_MAPPING_USO_TEC = {

    # identificación
    "Número de serie": "numero_serie",
    "Serial Number": "numero_serie",
    "Machine Serial Number": "numero_serie",

    "Organization ID": "org_id",
    "Organization Name": "organizacion",

    "Fecha": "fecha",
    "Date": "fecha",

    # tecnologías
    "AutoTrac %": "autotrac",
    "AutoTrac": "autotrac",

    "Turn Automation %": "turn_automation",
    "Turn Automation": "turn_automation",

    "AutoPath %": "autopath",
    "AutoPath": "autopath",

    "Implement Guidance %": "implement_guidance",
    "Implement Guidance": "implement_guidance",

    "Efficiency Manager %": "efficiency_manager",
    "Efficiency Manager": "efficiency_manager",

    "Field Cruise %": "field_cruise",
    "Field Cruise": "field_cruise",
}


# =====================================================
# MAPEO OCIOSIDAD
# =====================================================

COLUMN_MAPPING_OCIOSIDAD = {

    "Número de serie de la máquina":
        "numero_serie",

    "Organización":
        "organizacion",

    "Identificador de organización":
        "org_id",

    "Cancelada Período":
        "cancelada",

    "Sin definir Período":
        "sin_definir",

    "Ignorada Período":
        "ignorada",

    "Utilización Trabajo":
        "trabajo",

    "Utilización Transporte":
        "transporte",

    "Utilización Ralentí":
        "ralenti"
}


# =====================================================
# LECTURA
# =====================================================

def cargar_clientes():

    print(f"Clientes: {CLIENTES_FILE}")

    df = pd.read_csv(
        CLIENTES_FILE,
        sep=",",
        low_memory=False
    )

    df.columns = (
        df.columns
        .str.strip()
    )

    return df


def cargar_uso_tecnologia():

    try:

        df = pd.read_csv(
            USO_TEC_URL,
            low_memory=False
        )

        df.columns = (
            df.columns
            .str.strip()
        )

        df.rename(
            columns=COLUMN_MAPPING_USO_TEC,
            inplace=True
        )

        return df

    except Exception as e:

        raise Exception(
            f"Error leyendo uso-tec-v2: {e}"
        )


def cargar_ociosidad():

    print(f"Ociosidad: {OCIOSOS_FILE}")

    df = pd.read_csv(
        OCIOSOS_FILE,
        sep=",",
        low_memory=False
    )

    df.columns = (
        df.columns
        .str.strip()
    )

    df.rename(
        columns=COLUMN_MAPPING_OCIOSIDAD,
        inplace=True
    )

    return df

# =====================================================
# LIMPIEZA
# =====================================================

def normalizar_porcentajes(df):

    columnas = [
        "autotrac",
        "turn_automation",
        "autopath",
        "implement_guidance",
        "efficiency_manager",
        "field_cruise",
        "cancelada",
        "sin_definir",
        "ignorada"
    ]

    for col in columnas:

        if col in df.columns:

            df[col] = (
                pd.to_numeric(
                    df[col],
                    errors="coerce"
                )
                .fillna(0)
            )

    return df


# =====================================================
# OCIOSIDAD
# =====================================================

def calcular_ociosidad(df):

    df["ocio_controlable"] = (

        df["cancelada"]

        + df["sin_definir"]

        + df["ignorada"]

    )

    df["score_ociosidad"] = (

        100

        - df["ocio_controlable"]

    )

    return df


# =====================================================
# MERGE GENERAL
# =====================================================

def construir_dataframe_maestro():
    print("==== ARCHIVOS ====")
    print(CLIENTES_FILE)
    print(CLIENTES_FILE.exists())
    
    print(OCIOSOS_FILE)
    print(OCIOSOS_FILE.exists())
    
    print(USO_TEC_URL)

    clientes = cargar_clientes()

    uso_tec = cargar_uso_tecnologia()

    ociosidad = cargar_ociosidad()

    uso_tec = normalizar_porcentajes(
        uso_tec
    )

    ociosidad = normalizar_porcentajes(
        ociosidad
    )

    ociosidad = calcular_ociosidad(
        ociosidad
    )

    # ------------------------------
    # merge clientes + uso tec
    # ------------------------------

    df = clientes.merge(

        uso_tec,

        on="numero_serie",

        how="left"

    )

    # ------------------------------
    # merge ociosidad
    # ------------------------------

    df = df.merge(

        ociosidad[
            [
                "numero_serie",
                "cancelada",
                "sin_definir",
                "ignorada",
                "ocio_controlable",
                "score_ociosidad"
            ]
        ],

        on="numero_serie",

        how="left"

    )

    return df


# =====================================================
# CARGA PRINCIPAL
# =====================================================

def cargar_datos():

    df = construir_dataframe_maestro()

    return df
