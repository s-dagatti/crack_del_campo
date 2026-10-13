import streamlit as st
import pandas as pd

from utils.data_loader import cargar_datos
from utils.metrics import calcular_scores

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Crack del Campo",
    page_icon="🚜",
    layout="wide"
)

# --------------------------------------------------
# CARGA
# --------------------------------------------------

df = cargar_datos()

df = calcular_scores(df)

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.title("Filtros")

sucursales = sorted(
    df["sucursal"].dropna().unique()
)

clientes = sorted(
    df["cliente"].dropna().unique()
)

sucursal = st.sidebar.multiselect(
    "Sucursal",
    options=sucursales,
    default=sucursales
)

cliente = st.sidebar.multiselect(
    "Cliente",
    options=clientes,
    default=[]
)

fecha_min = pd.to_datetime(df["fecha"]).min()
fecha_max = pd.to_datetime(df["fecha"]).max()

periodo = st.sidebar.slider(
    "Periodo",
    min_value=fecha_min.to_pydatetime(),
    max_value=fecha_max.to_pydatetime(),
    value=(
        fecha_min.to_pydatetime(),
        fecha_max.to_pydatetime()
    )
)

# --------------------------------------------------
# FILTROS
# --------------------------------------------------

df_filtrado = df.copy()

df_filtrado = df_filtrado[
    df_filtrado["sucursal"].isin(sucursal)
]

if cliente:

    df_filtrado = df_filtrado[
        df_filtrado["cliente"].isin(cliente)
    ]

df_filtrado = df_filtrado[
    (
        df_filtrado["fecha"]
        >= pd.to_datetime(periodo[0])
    )
    &
    (
        df_filtrado["fecha"]
        <= pd.to_datetime(periodo[1])
    )
]

# --------------------------------------------------
# TABS PRINCIPALES
# --------------------------------------------------

tab_general, tab_informes, tab_clientes = st.tabs(
    [
        "📊 Tablero General",
        "📄 Generación Informe",
        "👥 Datos Clientes"
    ]
)

# ==================================================
# TAB GENERAL
# ==================================================

with tab_general:

    tab_basic, tab_elite = st.tabs(
        [
            "🚜 Basic",
            "🏆 Elite"
        ]
    )

    # ----------------------------------------------
    # BASIC
    # ----------------------------------------------

    with tab_basic:

        basic = df_filtrado[
            df_filtrado["categoria"] == "Basic"
        ]

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Participantes",
            basic["numero_serie"].nunique()
        )

        c2.metric(
            "AutoTrac",
            f"{basic['autotrac'].mean():.1f}%"
        )

        c3.metric(
            "Score Basic",
            f"{basic['score_basic'].mean():.1f}"
        )

        c4.metric(
            "Clientes",
            basic["cliente"].nunique()
        )

        ranking_basic = (
            basic
            .sort_values(
                "score_basic",
                ascending=False
            )
        )

        st.subheader(
            "Ranking Categoría Basic"
        )

        st.dataframe(
            ranking_basic[
                [
                    "operario",
                    "cliente",
                    "sucursal",
                    "autotrac",
                    "score_basic"
                ]
            ],
            use_container_width=True
        )

    # ----------------------------------------------
    # ELITE
    # ----------------------------------------------

    with tab_elite:

        elite = df_filtrado[
            df_filtrado["categoria"] == "Elite"
        ]

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "Participantes",
            elite["numero_serie"].nunique()
        )

        c2.metric(
            "Score Elite",
            f"{elite['score_elite'].mean():.1f}"
        )

        c3.metric(
            "AutoTrac",
            f"{elite['autotrac'].mean():.1f}%"
        )

        c4.metric(
            "Turn Automation",
            f"{elite['turn_automation'].mean():.1f}%"
        )

        c5.metric(
            "Ocio Controlable",
            f"{elite['ocio_controlable'].mean():.1f}%"
        )

        ranking_elite = (
            elite
            .sort_values(
                "score_elite",
                ascending=False
            )
        )

        st.subheader(
            "Ranking Categoría Elite"
        )

        st.dataframe(
            ranking_elite[
                [
                    "operario",
                    "cliente",
                    "score_elite",
                    "autotrac",
                    "turn_automation",
                    "ocio_controlable"
                ]
            ],
            use_container_width=True
        )

# ==================================================
# INFORMES
# ==================================================

with tab_informes:

    st.info(
        "Próxima versión"
    )

# ==================================================
# CLIENTES
# ==================================================

with tab_clientes:

    tab_c_basic, tab_c_elite = st.tabs(
        [
            "Basic",
            "Elite"
        ]
    )

    with tab_c_basic:

        st.dataframe(
            df_filtrado[
                df_filtrado["categoria"] == "Basic"
            ],
            use_container_width=True
        )

    with tab_c_elite:

        st.dataframe(
            df_filtrado[
                df_filtrado["categoria"] == "Elite"
            ],
            use_container_width=True
        )
