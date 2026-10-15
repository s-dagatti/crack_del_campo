# utils/metrics.py

import pandas as pd


# =====================================================
# CONFIGURACIÓN DE SCORES
# =====================================================

METRICAS_BASIC = [
    "autotrac",
]

METRICAS_ELITE = [
    "autotrac",
    "turn_automation",
    "autopath",
    "implement_guidance",
    "efficiency_manager",
    "field_cruise",
    "score_ociosidad",
]


# =====================================================
# FUNCIONES AUXILIARES
# =====================================================

def obtener_metrica_para_score(df, columna):
    """
    Devuelve una serie numérica preparada para calcular scores.

    Reglas:
    - Si la columna no existe, aporta 0.
    - Si el valor es nulo o no numérico, aporta 0.
    - Los valores se limitan a una escala de 0 a 100.
    """

    if columna not in df.columns:
        return pd.Series(
            0.0,
            index=df.index,
            dtype="float64",
        )

    return (
        pd.to_numeric(
            df[columna],
            errors="coerce",
        )
        .fillna(0.0)
        .clip(lower=0, upper=100)
    )


# =====================================================
# CÁLCULO DE SCORES
# =====================================================

def calcular_scores(df):
    """
    Calcula los scores Basic y Elite por cada fila semanal.

    Los valores ausentes se consideran 0 exclusivamente
    para el cálculo de los scores. Las columnas tecnológicas
    originales conservan sus valores y sus NaN.
    """

    df = df.copy()

    # =================================================
    # SCORE BASIC
    # =================================================

    autotrac = obtener_metrica_para_score(
        df,
        "autotrac",
    )

    df["score_basic"] = autotrac

    # =================================================
    # SCORE ELITE
    # =================================================

    turn_automation = obtener_metrica_para_score(
        df,
        "turn_automation",
    )

    autopath = obtener_metrica_para_score(
        df,
        "autopath",
    )

    implement_guidance = obtener_metrica_para_score(
        df,
        "implement_guidance",
    )

    efficiency_manager = obtener_metrica_para_score(
        df,
        "efficiency_manager",
    )

    field_cruise = obtener_metrica_para_score(
        df,
        "field_cruise",
    )

    score_ociosidad = obtener_metrica_para_score(
        df,
        "score_ociosidad",
    )

    df["score_elite"] = (
        autotrac
        + turn_automation
        + autopath
        + implement_guidance
        + efficiency_manager
        + field_cruise
        + score_ociosidad
    ) / len(METRICAS_ELITE)

    # Garantiza una escala final entre 0 y 100.
    df["score_basic"] = df["score_basic"].clip(
        lower=0,
        upper=100,
    )

    df["score_elite"] = df["score_elite"].clip(
        lower=0,
        upper=100,
    )

    return df
