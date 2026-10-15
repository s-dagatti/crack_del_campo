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
    Prepara una métrica para calcular los scores.

    Un valor ausente o no numérico aporta 0 al score,
    pero no modifica la columna tecnológica original.
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
    Basic:
    - Mayor que 70: no requiere intervención.
    - Entre 55 y 70: intervención moderada.
    - Menor que 55: intervención necesaria.
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
    Elite:
    - Mayor que 40: no requiere intervención.
    - Entre 30 y 40: intervención moderada.
    - Menor que 30: intervención necesaria.
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
    Calcula los scores Basic y Elite y asigna la necesidad
    de intervención correspondiente a cada categoría.
    """

    df = df.copy()

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

    # Score Basic: corresponde a AutoTrac.
    df["score_basic"] = autotrac

    # Score Elite: promedio fijo de siete indicadores.
    # Una tecnología sin actividad aporta 0.
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

    # Clasificaciones separadas.
    df["intervencion_basic"] = (
        df["score_basic"]
        .apply(clasificar_intervencion_basic)
    )

    df["intervencion_elite"] = (
        df["score_elite"]
        .apply(clasificar_intervencion_elite)
    )

    # Clasificación unificada utilizada por el dashboard.
    df["necesidad_intervencion"] = (
        "SIN CLASIFICAR"
    )

    if "categoria" in df.columns:
        categoria = (
            df["categoria"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        mascara_basic = categoria.eq("BASIC")
        mascara_elite = categoria.eq("ELITE")

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
