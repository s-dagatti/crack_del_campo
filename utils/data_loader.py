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
# ALIAS DE COLUMNAS
# Los nombres se comparan después de normalizarlos:
# minúsculas, sin tildes y con guiones bajos.
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
    "operario": "operario",
    "operador": "operario",
    "nombre_completo_del_operador": "operario",

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


COLUMN_MAPPING_USO_TEC = {
    # Identificación
    "numero_de_serie": "numero_serie",
    "numero_de_serie_de_la_maquina": "numero_serie",
    "nro_de_serie": "numero_serie",
    "nro_serie": "numero_serie",
    "serie": "numero_serie",
    "serial_number": "numero_serie",
    "machine_serial_number": "numero_serie",

    "organization_id": "org_id",
    "identificador_de_organizacion": "org_id",
    "id_organizacion": "org_id",
    "org_id": "org_id",

    "organization_name": "organizacion",
    "organizacion": "organizacion",

    # Fechas
    "fecha": "fecha",
    "date": "fecha",
    "period_end": "fecha",
    "fecha_fin": "fecha",

    # Tecnologías
    "autotrac": "autotrac",
    "autotrac_pct": "autotrac",
    "autotrac_porcentaje": "autotrac",

    "turn_automation": "turn_automation",
    "turn_automation_pct": "turn_automation",
    "turn_automation_porcentaje": "turn_automation",

    "autopath": "autopath",
    "autopath_pct": "autopath",
    "autopath_porcentaje": "autopath",

    "implement_guidance": "implement_guidance",
    "implement_guidance_pct": "implement_guidance",
    "implement_guidance_porcentaje": "implement_guidance",

    "efficiency_manager": "efficiency_manager",
    "efficiency_manager_pct": "efficiency_manager",
    "ef_manager": "efficiency_manager",
    "ef_manager_pct": "efficiency_manager",

    "field_cruise": "field_cruise",
    "field_cruise_pct": "field_cruise",
    "f_cruise": "field_cruise",
    "f_cruise_pct": "field_cruise",
}


COLUMN_MAPPING_OCIOSIDAD = {
    # Identificación
    "numero_de_serie": "numero_serie",
    "numero_de_serie_de_la_maquina": "numero_serie",
    "nro_de_serie": "numero_serie",
    "nro_serie": "numero_serie",
    "serie": "numero_serie",

    "organizacion": "organizacion",
    "identificador_de_organizacion": "org_id",
    "id_organizacion": "org_id",

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

    # Fechas, si están disponibles
    "fecha_inicio": "fecha_inicio",
    "fecha_fin": "fecha_fin",
}


# =====================================================
# FUNCIONES AUXILIARES
# =====================================================

def normalizar_nombre_columna(nombre):
    """
    Convierte un encabezado a minúsculas, elimina tildes
    y reemplaza espacios y símbolos por guiones bajos.
    """

    nombre = str(nombre).strip()

    nombre = unicodedata.normalize("NFKD", nombre)
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
    """
    Normaliza primero todos los encabezados y luego aplica
    el diccionario de alias correspondiente.
    """

    df = df.copy()

    df.columns = [
        normalizar_nombre_columna(columna)
        for columna in df.columns
    ]

    df.rename(columns=mapping, inplace=True)

    return df


def leer_csv_flexible(origen):
    """
    Lee archivos CSV detectando automáticamente si el separador
    es coma, punto y coma u otro delimitador compatible.
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
            f"Faltan columnas en {nombre_fuente}: {faltantes}. "
            f"Columnas disponibles: {df.columns.tolist()}"
        )


def normalizar_numero_serie(df):
    """
    Deja la clave de vinculación como texto limpio y en mayúsculas.
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
    )

    # Evita unir filas sin número de serie.
    df = df[
        df["numero_serie"].notna()
        & df["numero_serie"].ne("")
        & df["numero_serie"].ne("NAN")
    ].copy()

    return df


def convertir_porcentaje(serie):
    """
    Acepta valores como:
    85
    85%
    0,85
    0.85

    Los porcentajes con símbolo se convierten a escala 0-100.
    Los decimales sin símbolo se mantienen como vienen para no
    modificar datos ambiguos automáticamente.
    """

    texto = serie.astype("string").str.strip()

    tiene_porcentaje = texto.str.contains(
        "%",
        regex=False,
        na=False,
    )

    texto = (
        texto
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.replace(r"\s+", "", regex=True)
    )

    valores = pd.to_numeric(texto, errors="coerce")

    # Si había símbolo %, el número ya representa 0-100.
    valores.loc[tiene_porcentaje] = valores.loc[tiene_porcentaje]

    return valores


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
            df[columna] = convertir_porcentaje(df[columna])

    return df


# =====================================================
# CARGA DE FUENTES
# =====================================================

def cargar_clientes():
    if not CLIENTES_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró la base de clientes: {CLIENTES_FILE}"
        )

    df = leer_csv_flexible(CLIENTES_FILE)

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

    return df


def cargar_uso_tecnologia():
    try:
        df = leer_csv_flexible(USO_TEC_URL)

    except Exception as error:
        raise RuntimeError(
            f"No fue posible leer el CSV de uso-tec-v2: {error}"
        ) from error

    df = normalizar_encabezados(
        df,
        COLUMN_MAPPING_USO_TEC,
    )

    validar_columnas(
        df,
        ["numero_serie"],
        "datos_consolidados_conci.csv",
    )

    df = normalizar_numero_serie(df)
    df = normalizar_porcentajes(df)

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(
            df["fecha"],
            errors="coerce",
            dayfirst=True,
        )

    return df


def cargar_ociosidad():
    if not OCIOSOS_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró la base de ociosidad: {OCIOSOS_FILE}"
        )

    df = leer_csv_flexible(OCIOSOS_FILE)

    df = normalizar_encabezados(
        df,
        COLUMN_MAPPING_OCIOSIDAD,
    )

    validar_columnas(
        df,
        [
            "numero_serie",
            "cancelada",
            "sin_definir",
            "ignorada",
        ],
        "motivos_ociosos.csv",
    )

    df = normalizar_numero_serie(df)
    df = normalizar_porcentajes(df)

    for columna_fecha in ["fecha_inicio", "fecha_fin"]:
        if columna_fecha in df.columns:
            df[columna_fecha] = pd.to_datetime(
                df[columna_fecha],
                errors="coerce",
                dayfirst=True,
            )

    return df


# =====================================================
# CÁLCULO DE OCIOSIDAD
# =====================================================

def calcular_ociosidad(df):
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
            .fillna(0)
        )

    df["ocio_controlable"] = (
        df["cancelada"]
        + df["sin_definir"]
        + df["ignorada"]
    )

    df["ocio_controlable"] = (
        df["ocio_controlable"]
        .clip(lower=0, upper=100)
    )

    df["score_ociosidad"] = (
        100 - df["ocio_controlable"]
    ).clip(lower=0, upper=100)

    return df


# =====================================================
# CONSTRUCCIÓN DEL DATAFRAME MAESTRO
# =====================================================

def construir_dataframe_maestro():
    clientes = cargar_clientes()
    uso_tec = cargar_uso_tecnologia()
    ociosidad = cargar_ociosidad()

    ociosidad = calcular_ociosidad(ociosidad)

    # Evita duplicar organización y org_id.
    columnas_uso = [
        columna
        for columna in uso_tec.columns
        if columna not in {
            "organizacion",
            "org_id",
        }
    ]

    uso_tec_merge = uso_tec[columnas_uso].copy()

    # Unión entre participantes y datos tecnológicos.
    df = clientes.merge(
        uso_tec_merge,
        on="numero_serie",
        how="left",
        suffixes=("_clientes", "_uso"),
    )

    columnas_ociosidad = [
        "numero_serie",
        "cancelada",
        "sin_definir",
        "ignorada",
        "ocio_controlable",
        "score_ociosidad",
    ]

    for columna in ["fecha_inicio", "fecha_fin"]:
        if columna in ociosidad.columns:
            columnas_ociosidad.append(columna)

    # Unión con el histórico de motivos ociosos.
    df = df.merge(
        ociosidad[columnas_ociosidad],
        on="numero_serie",
        how="left",
    )

    # =================================================
    # UNIFICACIÓN DE COLUMNAS DUPLICADAS
    # =================================================

    # Sucursal
    if "sucursal_x" in df.columns:
        df["sucursal"] = df["sucursal_x"]

    elif "sucursal_clientes" in df.columns:
        df["sucursal"] = df["sucursal_clientes"]

    elif "sucursal_y" in df.columns:
        df["sucursal"] = df["sucursal_y"]

    elif "sucursal_uso" in df.columns:
        df["sucursal"] = df["sucursal_uso"]

    # Máquina
    if "maquina_x" in df.columns:
        df["maquina"] = df["maquina_x"]

    elif "maquina_clientes" in df.columns:
        df["maquina"] = df["maquina_clientes"]

    elif "maquina_y" in df.columns:
        df["maquina"] = df["maquina_y"]

    elif "maquina_uso" in df.columns:
        df["maquina"] = df["maquina_uso"]

    # Tipo
    if "tipo_x" in df.columns:
        df["tipo"] = df["tipo_x"]

    elif "tipo_clientes" in df.columns:
        df["tipo"] = df["tipo_clientes"]

    elif "tipo_y" in df.columns:
        df["tipo"] = df["tipo_y"]

    elif "tipo_uso" in df.columns:
        df["tipo"] = df["tipo_uso"]

    # Categoría del desafío.
    if "categoria" not in df.columns:
        if "crack_campo" in df.columns:
            df["categoria"] = df["crack_campo"]
        else:
            df["categoria"] = "Sin categoría"

    # La organización funciona inicialmente como nombre del cliente.
    if "cliente" not in df.columns:
        if "organizacion" in df.columns:
            df["cliente"] = df["organizacion"]
        else:
            df["cliente"] = "Sin cliente"

    # La base actual no está devolviendo operario.
    if "operario" not in df.columns:
        df["operario"] = "Sin asignar"

    # Limpieza de textos.
    for columna in [
        "sucursal",
        "cliente",
        "operario",
        "categoria",
    ]:
        if columna in df.columns:
            df[columna] = (
                df[columna]
                .astype("string")
                .str.strip()
            )

    # Convierte nombres alternativos de categoría.
    df["categoria"] = (
        df["categoria"]
        .fillna("Sin categoría")
        .astype(str)
        .str.strip()
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

        df[columna] = (
            pd.to_numeric(
                df[columna],
                errors="coerce",
            )
            .fillna(0.0)
        )

    # Elimina las versiones duplicadas.
    df = df.drop(
        columns=[
            "sucursal_x",
            "sucursal_y",
            "sucursal_clientes",
            "sucursal_uso",
            "maquina_x",
            "maquina_y",
            "maquina_clientes",
            "maquina_uso",
            "tipo_x",
            "tipo_y",
            "tipo_clientes",
            "tipo_uso",
        ],
        errors="ignore",
    )

    # ===============================
    # COLUMNAS ESTÁNDAR DASHBOARD
    # ===============================
    
    if "sucursal_x" in df.columns:
        df["sucursal"] = df["sucursal_x"]
    
    if "crack_campo" in df.columns:
        df["categoria"] = df["crack_campo"]
    
    if "organizacion" in df.columns:
        df["cliente"] = df["organizacion"]
    
    if "operario" not in df.columns:
        df["operario"] = "Sin asignar"

    return df

# =====================================================
# FUNCIÓN PRINCIPAL
# =====================================================

def cargar_datos():
    return construir_dataframe_maestro()
