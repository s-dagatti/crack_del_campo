# utils/github_clientes.py

import base64
import csv
from io import StringIO

import pandas as pd
import requests
import streamlit as st


# =====================================================
# CONFIGURACIÓN DE GITHUB
# =====================================================

GITHUB_OWNER = "s-dagatti"
GITHUB_REPO = "crack-del-campo"
GITHUB_BRANCH = "main"
GITHUB_CLIENTES_PATH = "data/base_de_clientes.csv"

GITHUB_API_URL = (
    f"https://api.github.com/repos/"
    f"{GITHUB_OWNER}/{GITHUB_REPO}/contents/"
    f"{GITHUB_CLIENTES_PATH}"
)


# =====================================================
# FUNCIONES AUXILIARES
# =====================================================

def obtener_token_github():
    """
    Obtiene el token desde los secretos de Streamlit.

    La configuración esperada es:

    [github]
    token = "..."
    """

    try:
        token = st.secrets["github"]["token"]

    except Exception as error:
        raise RuntimeError(
            "No se encontró el token de GitHub en los "
            "secretos de Streamlit. La configuración esperada "
            'es: [github] token = "..."'
        ) from error

    token = str(token).strip()

    if not token:
        raise RuntimeError(
            "El token de GitHub está vacío."
        )

    return token


def construir_headers_github():
    """
    Construye los encabezados necesarios para comunicarse
    con la API de GitHub.
    """

    token = obtener_token_github()

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def detectar_separador_csv(contenido):
    """
    Intenta conservar el separador actual del CSV.

    Si no puede detectarlo, utiliza punto y coma.
    """

    muestra = contenido[:5000]

    try:
        dialecto = csv.Sniffer().sniff(
            muestra,
            delimiters=[
                ";",
                ",",
                "\t",
                "|",
            ],
        )

        return dialecto.delimiter

    except csv.Error:
        return ";"


def normalizar_numero_serie_valor(valor):
    """
    Normaliza un número de serie para utilizarlo como clave.

    Ejemplo:
        " 1rw-8295 " -> "1RW8295"
    """

    serie = str(valor).strip().upper()

    serie = "".join(
        caracter
        for caracter in serie
        if caracter.isalnum()
    )

    return serie


# =====================================================
# LECTURA DEL CSV
# =====================================================

def cargar_clientes_github():
    """
    Lee la versión actual del CSV desde GitHub.

    Devuelve:
    - dataframe;
    - SHA actual del archivo;
    - separador detectado.

    El SHA se utiliza para evitar sobrescribir cambios
    realizados por otra persona.
    """

    headers = construir_headers_github()

    respuesta = requests.get(
        GITHUB_API_URL,
        headers=headers,
        params={
            "ref": GITHUB_BRANCH,
        },
        timeout=30,
    )

    if respuesta.status_code == 401:
        raise RuntimeError(
            "GitHub rechazó el token configurado."
        )

    if respuesta.status_code == 403:
        raise RuntimeError(
            "El token no tiene permisos suficientes para "
            "acceder al archivo de clientes."
        )

    if respuesta.status_code == 404:
        raise RuntimeError(
            "No se encontró el archivo de clientes en GitHub. "
            f"Ruta esperada: {GITHUB_CLIENTES_PATH}"
        )

    if not respuesta.ok:
        raise RuntimeError(
            "No fue posible leer el archivo de clientes "
            "desde GitHub."
        )

    datos = respuesta.json()

    contenido_base64 = datos.get("content")
    sha = datos.get("sha")

    if not contenido_base64:
        raise RuntimeError(
            "GitHub devolvió el archivo sin contenido."
        )

    if not sha:
        raise RuntimeError(
            "GitHub no devolvió la versión del archivo."
        )

    contenido = base64.b64decode(
        contenido_base64
    ).decode(
        "utf-8-sig"
    )

    separador = detectar_separador_csv(
        contenido
    )

    dataframe = pd.read_csv(
        StringIO(contenido),
        sep=separador,
        dtype="string",
        keep_default_na=False,
    )

    return dataframe, sha, separador


# =====================================================
# GUARDADO DEL CSV
# =====================================================

def guardar_clientes_github(
    dataframe,
    sha,
    separador,
    mensaje_commit,
):
    """
    Guarda el dataframe en el CSV del repositorio.

    El SHA debe corresponder a la versión que se leyó antes
    de editar. Si otra persona modificó el archivo mientras
    tanto, GitHub rechazará la operación para evitar que se
    pierdan sus cambios.
    """

    if dataframe is None:
        raise ValueError(
            "No se recibió el dataframe de clientes."
        )

    if not sha:
        raise ValueError(
            "No se recibió la versión actual del archivo."
        )

    dataframe_guardar = dataframe.copy()

    contenido_csv = dataframe_guardar.to_csv(
        index=False,
        sep=separador,
        lineterminator="\n",
    )

    contenido_base64 = base64.b64encode(
        contenido_csv.encode("utf-8-sig")
    ).decode("utf-8")

    payload = {
        "message": mensaje_commit,
        "content": contenido_base64,
        "sha": sha,
        "branch": GITHUB_BRANCH,
    }

    headers = construir_headers_github()

    respuesta = requests.put(
        GITHUB_API_URL,
        headers=headers,
        json=payload,
        timeout=30,
    )

    if respuesta.status_code == 401:
        raise RuntimeError(
            "GitHub rechazó el token configurado."
        )

    if respuesta.status_code == 403:
        raise RuntimeError(
            "El token no tiene permiso para modificar "
            "el archivo de clientes."
        )

    if respuesta.status_code in {
        409,
        422,
    }:
        raise RuntimeError(
            "El archivo cambió mientras estabas editando. "
            "Recargá el tablero e intentá nuevamente para "
            "evitar sobrescribir cambios de otra persona."
        )

    if not respuesta.ok:
        raise RuntimeError(
            "GitHub no pudo guardar los cambios en el "
            "archivo de clientes."
        )

    return respuesta.json()
