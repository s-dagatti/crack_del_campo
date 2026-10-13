import pandas as pd


def cargar_clientes():

    return pd.read_excel(
        "data/base_de_clientes.xlsx"
    )


def cargar_ociosidad():

    return pd.read_excel(
        "data/motivos_ociosos.xlsx"
    )


def cargar_uso_tec():

    return pd.read_csv(
        "datos_consolidados_conci.csv",
        low_memory=False
    )
