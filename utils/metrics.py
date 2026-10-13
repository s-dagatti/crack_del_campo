def calcular_ocio_controlable(df):

    df["ocio_controlable"] = (
        df["cancelada"]
        + df["sin_definir"]
        + df["ignorada"]
    )

    return df

def calcular_score_ociosidad(df):

    df["score_ociosidad"] = (
        100 - df["ocio_controlable"]
    )

    return df

def calcular_score_basic(df):

    df["score_basic"] = (
        df["autotrac"]
    )

    return df

def calcular_score_elite(df):

    df["score_elite"] = (
        (
            df["autotrac"]
            + df["turn_automation"]
            + df["autopath"]
            + df["implement_guidance"]
            + df["efficiency_manager"]
            + df["field_cruise"]
            + df["score_ociosidad"]
        )
        / 7
    )

    return df


def calcular_scores(df):

    df["ocio_controlable"] = (
        df["cancelada"]
        + df["sin_definir"]
        + df["ignorada"]
    )

    df["score_ociosidad"] = (
        100 - df["ocio_controlable"]
    )

    df["score_basic"] = (
        df["autotrac"]
    )

    df["score_elite"] = (
        df["autotrac"]
        + df["turn_automation"]
        + df["autopath"]
        + df["implement_guidance"]
        + df["efficiency_manager"]
        + df["field_cruise"]
        + df["score_ociosidad"]
    ) / 7

    return df
