# utils/github_clientes.py

import base64
import csv
from io import StringIO

import pandas as pd
import requests
import streamlit as st


# =====================================================
# CONFIGURACIÓN
# =====================================================

def obtener_token_github():
    """
    Obtiene el token desde:

    [github]
    token = "..."
    """

    try:
        token = st.secrets["github"]["token"]

    except Exception as error:
        raise RuntimeError(
            "No se encontró el token de GitHub. "
            "La configuración esperada es: "
            '[github] token = "..."'
        ) from error

    token = str(token).strip()

    if not token:
        raise RuntimeError(
            "El token de GitHub está vacío."
        )

    return token


def obtener_configuracion_github_clientes():
    """
    Obtiene la configuración del repositorio de clientes.

    Configuración esperada:

    [github]
    clientes_repo = "s-dagatti/crack_del_campo"
    clientes_branch = "main"
    clientes_path = "data/base_de_clientes.csv"
    """

    try:
        configuracion = st.secrets["github"]

        repositorio_completo = str(
            configuracion["clientes_repo"]
        ).strip()

        branch = str(
            configuracion.get(
                "clientes_branch",
                "main",
            )
        ).strip()

        ruta = str(
            configuracion.get(
                "clientes_path",
                "data/base_de_clientes.csv",
            )
        ).strip()

    except Exception as error:
        raise RuntimeError(
            "Falta la configuración del repositorio de "
            "clientes en los secretos de Streamlit."
        ) from error

    partes = repositorio_completo.split(
        "/",
        maxsplit=1,
    )

    if len(partes)!= 2:
        raise RuntimeError(
            "github.clientes_repo debe tener el formato "
            "'propietario/repositorio'."
        )

    owner = partes[0].strip()
    repo = partes[1].strip()

    if not owner or not repo:
        raise RuntimeError(
            "github.clientes_repo no es válido."
        )

    if not branch:
        raise RuntimeError(
            "github.clientes_branch está vacío."
        )

    if not ruta:
        raise RuntimeError(
            "github.clientes_path está vacío."
        )

    return {
        "owner": owner,
        "repo": repo,
        "branch": branch,
        "path": ruta,
    }


def construir_url_archivo(configuracion):
    """
    Construye la URL de la API para el archivo editable.
    """

    owner = configuracion["owner"]
    repo = configuracion["repo"]
    ruta = configuracion["path"]

    return (
        f"https://api.github.com/repos/"
        f"{owner}/{repo}/contents/{ruta}"
    )


def construir_headers_github():
    token = obtener_token_github()

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


# =====================================================
# UTILIDADES CSV
# =====================================================

def detectar_separador_csv(contenido):
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
    serie = str(valor).strip().upper()

    return "".join(
        caracter
        for caracter in serie
        if caracter.isalnum()
    )


# =====================================================
# LECTURA
# =====================================================

def cargar_clientes_github():
    """
    Lee la versión actual del CSV de participantes.

    Devuelve:
    - dataframe;
    - SHA;
    - separador.
    """

    configuracion = (
        obtener_configuracion_github_clientes()
    )

    github_api_url = construir_url_archivo(
        configuracion
    )

    headers = construir_headers_github()

    respuesta = requests.get(
        github_api_url,
        headers=headers,
        params={
            "ref": configuracion["branch"],
        },
        timeout=30,
    )

    if respuesta.status_code == 401:
        raise RuntimeError(
            "GitHub rechazó el token configurado."
        )

    if respuesta.status_code == 403:
        raise RuntimeError(
            "El token no tiene permisos suficientes "
            "para acceder al repositorio."
        )

    if respuesta.status_code == 404:
        raise RuntimeError(
            "GitHub no encontró el repositorio, la rama "
            "o el archivo. "
            f"Ubicación consultada: "
            f"{configuracion['owner']}/"
            f"{configuracion['repo']}/"
            f"{configuracion['path']} "
            f"(rama: {configuracion['branch']})."
        )

    if not respuesta.ok:
        raise RuntimeError(
            "No fue posible leer el archivo de clientes. "
            f"Estado recibido: {respuesta.status_code}."
        )

    datos = respuesta.json()

    contenido_base64 = datos.get("content")
    sha = datos.get("sha")

    if not contenido_base64:
        raise RuntimeError(
            "GitHub encontró el archivo, pero no devolvió "
            "su contenido."
        )

    if not sha:
        raise RuntimeError(
            "GitHub no devolvió la versión del archivo."
        )

    try:
        contenido = base64.b64decode(
            contenido_base64
        ).decode(
            "utf-8-sig"
        )

    except Exception as error:
        raise RuntimeError(
            "No se pudo decodificar el CSV de clientes."
        ) from error

    separador = detectar_separador_csv(
        contenido
    )

    try:
        dataframe = pd.read_csv(
            StringIO(contenido),
            sep=separador,
            dtype="string",
            keep_default_na=False,
        )

    except Exception as error:
        raise RuntimeError(
            "El archivo fue encontrado, pero no pudo "
            "interpretarse como CSV."
        ) from error

    return dataframe, sha, separador


# =====================================================
# GUARDADO
# =====================================================

def guardar_clientes_github(
    dataframe,
    sha,
    separador,
    mensaje_commit,
):
    """
    Guarda el CSV mediante un commit en GitHub.
    """

    if dataframe is None:
        raise ValueError(
            "No se recibió el dataframe de clientes."
        )

    if not sha:
        raise ValueError(
            "No se recibió la versión actual del archivo."
        )

    configuracion = (
        obtener_configuracion_github_clientes()
    )

    github_api_url = construir_url_archivo(
        configuracion
    )

    contenido_csv = dataframe.to_csv(
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
        "branch": configuracion["branch"],
    }

    respuesta = requests.put(
        github_api_url,
        headers=construir_headers_github(),
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
            "Recargá el tablero e intentá nuevamente."
        )

    if respuesta.status_code == 404:
        raise RuntimeError(
            "GitHub no encontró el repositorio, la rama "
            "o el archivo que se intentó modificar. "
            f"Ubicación: "
            f"{configuracion['owner']}/"
            f"{configuracion['repo']}/"
            f"{configuracion['path']}."
        )

    if not respuesta.ok:
        raise RuntimeError(
            "GitHub no pudo guardar los cambios. "
            f"Estado recibido: {respuesta.status_code}."
        )

    return respuesta.json()
