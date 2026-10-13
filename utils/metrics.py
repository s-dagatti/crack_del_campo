def calcular_scores(df):

    df["score_basic"] = df["autotrac"]

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
