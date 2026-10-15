# utils/metrics.py

import pandas as pd


# =====================================================
# CONFIGURACIÓN
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
    Prepara una columna para calcular el score.

    - Valores ausentes: 0.
    - Valores no numéricos: 0.
    - Valores menores que 0: 0.
    - Valores mayores que 100: 100.

    La columna original del dataframe no se modifica.
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

    Score > 70:
        no requiere intervención.

    Score entre 55 y 70, inclusive:
        intervención moderada.

    Score < 55:
        intervención necesaria.
    """

    score = pd.to_numeric(
        score,
        errors="coerce",
    )

    if pd.isna(score):
        score = 0.0

    if score > 70:
        return "NO REQUIERE INTERVENCIÓN"

    if score >= 55:
        return "INTERVENCIÓN MODERADA"

    return "INTERVENCIÓN NECESARIA"


def clasificar_intervencion_elite(score):
    """
    Clasifica la necesidad de intervención de Elite.

    Score > 40:
        no requiere intervención.

    Score entre 30 y 40, inclusive:
        intervención moderada.

    Score < 30:
        intervención necesaria.
    """

    score = pd.to_numeric(
        score,
        errors="coerce",
    )

    if pd.isna(score):
        score = 0.0

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
    Calcula:

    - score_basic
    - score_elite
    - intervencion_basic
    - intervencion_elite
    - necesidad_intervencion

    Los valores ausentes de las tecnologías aportan 0
    al cálculo del score, sin modificar las columnas
    tecnológicas originales.
    """

    df = df.copy()

    # =================================================
    # PREPARACIÓN DE MÉTRICAS
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
    # SCORES
    # =================================================

    df["score_basic"] = autotrac

    df["score_elite"] = (
        autotrac
        + turn_automation
        + autopath
        + implement_guidance
        + efficiency_manager
        + field_cruise
        + score_ociosidad
    ) / len(METRICAS_ELITE)

    df["score_basic"] = (
        df["score_basic"]
        .clip(lower=0, upper=100)
    )

    df["score_elite"] = (
        df["score_elite"]
        .clip(lower=0, upper=100)
    )

    # =================================================
    # CLASIFICACIONES POR CATEGORÍA
    # =================================================

    df["intervencion_basic"] = (
        df["score_basic"]
        .apply(clasificar_intervencion_basic)
    )

    df["intervencion_elite"] = (
        df["score_elite"]
        .apply(clasificar_intervencion_elite)
    )

    # =================================================
    # COLUMNA UNIFICADA
    # =================================================

    df["necesidad_intervencion"] = (
        "SIN CLASIFICAR"
    )

    if "categoria" in df.columns:
        categoria_normalizada = (
            df["categoria"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        mascara_basic = categoria_normalizada.eq(
            "BASIC"
        )

        mascara_elite = categoria_normalizada.eq(
            "ELITE"
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
