# utils/metrics.py

import pandas as pd


# =====================================================
# CONFIGURACIÓN DE SCORES
# =====================================================

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
    Devuelve una métrica numérica preparada para el score.

    Reglas:
    - Si la columna no existe, aporta 0.
    - Si el valor está vacío o no es numérico, aporta 0.
    - Los valores se limitan al rango de 0 a 100.
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


def clasificar_intervencion_basic(score):
    """
    Clasifica la necesidad de intervención de Basic.

    Mayor que 70:
        no requiere intervención.

    Entre 55 y 70, inclusive:
        intervención moderada.

    Menor que 55:
        intervención necesaria.
    """

    if pd.isna(score):
        return "SIN CLASIFICAR"

    if score > 70:
        return "NO REQUIERE INTERVENCIÓN"

    if score >= 55:
        return "INTERVENCIÓN MODERADA"

    return "INTERVENCIÓN NECESARIA"


def clasificar_intervencion_elite(score):
    """
    Clasifica la necesidad de intervención de Elite.

    Mayor que 40:
        no requiere intervención.

    Entre 30 y 40, inclusive:
        intervención moderada.

    Menor que 30:
        intervención necesaria.
    """

    if pd.isna(score):
        return "SIN CLASIFICAR"

    if score > 40:
        return "NO REQUIERE INTERVENCIÓN"

    if score >= 30:
        return "INTERVENCIÓN MODERADA"

    return "INTERVENCIÓN NECESARIA"


# =====================================================
# CÁLCULO DE SCORES
# =====================================================

def calcular_scores(df):
    """
    Calcula los scores y la necesidad de intervención
    para cada máquina y periodo semanal.

    Los valores ausentes se consideran 0 exclusivamente
    para calcular los scores.
    """

    df = df.copy()

    # =================================================
    # MÉTRICAS PARA SCORES
    # =================================================

    autotrac = obtener_metrica_para_score(
        df,
        "autotrac",
    )

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

    # =================================================
    # SCORE BASIC
    # =================================================

    df["score_basic"] = autotrac

    # =================================================
    # SCORE ELITE
    # =================================================

    df["score_elite"] = (
        autotrac
        + turn_automation
        + autopath
        + implement_guidance
        + efficiency_manager
        + field_cruise
        + score_ociosidad
    ) / len(METRICAS_ELITE)

    df["score_basic"] = df["score_basic"].clip(
        lower=0,
        upper=100,
    )

    df["score_elite"] = df["score_elite"].clip(
        lower=0,
        upper=100,
    )

    # =================================================
    # NECESIDAD DE INTERVENCIÓN
    # =================================================

    df["intervencion_basic"] = (
        df["score_basic"]
        .apply(clasificar_intervencion_basic)
    )

    df["intervencion_elite"] = (
        df["score_elite"]
        .apply(clasificar_intervencion_elite)
    )

    # Columna unificada para utilizar en el dashboard.
    df["necesidad_intervencion"] = "SIN CLASIFICAR"

    mascara_basic = (
        df["categoria"]
        .astype(str)
        .str.strip()
        .str.upper()
        .eq("BASIC")
    )

    mascara_elite = (
        df["categoria"]
        .astype(str)
        .str.strip()
        .str.upper()
        .eq("ELITE")
    )

    df.loc[
        mascara_basic,
        "necesidad_intervencion",
    ] = df.loc[
        mascara_basic,
        "intervencion_basic",
    ]

    df.loc[
        mascara_elite,
        "necesidad_intervencion",
    ] = df.loc[
        mascara_elite,
        "intervencion_elite",
    ]

    return df
