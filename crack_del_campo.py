import streamlit as st
import pandas as pd

from utils.data_loader import cargar_datos
from utils.metrics import calcular_scores

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="Crack del Campo",
    page_icon="🚜",
    layout="wide"
)

st.title("🚜 Crack del Campo FY27")
st.caption("Seguimiento de participantes - Tractores")

# =====================================================
# DATOS
# =====================================================

@st.cache_data
def load_data():

    df = cargar_datos()
    df = calcular_scores(df)

    return df


df = load_data()

st.subheader("DEBUG")

st.write("Columnas encontradas:")

st.write(df.columns.tolist())

st.stop()

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("Filtros")

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
    options=clientes
)

# =====================================================
# FILTROS
# =====================================================

df_filtrado = df.copy()

if sucursal:

    df_filtrado = df_filtrado[
        df_filtrado["sucursal"].isin(sucursal)
    ]

if cliente:

    df_filtrado = df_filtrado[
        df_filtrado["cliente"].isin(cliente)
    ]

# =====================================================
# TABS PRINCIPALES
# =====================================================

tab_general, tab_informe, tab_clientes = st.tabs(
    [
        "📊 Tablero General",
        "📄 Generación Informe",
        "👥 Datos Clientes"
    ]
)

# =====================================================
# TAB GENERAL
# =====================================================

with tab_general:

    basic_tab, elite_tab = st.tabs(
        [
            "🚜 Basic",
            "🏆 Elite"
        ]
    )

    # ==========================================
    # BASIC
    # ==========================================

    with basic_tab:

        basic = df_filtrado[
            df_filtrado["categoria"].str.upper()
            == "BASIC"
        ]

        st.subheader("Categoría Basic")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Participantes",
            basic["numero_serie"].nunique()
        )

        c2.metric(
            "Clientes",
            basic["cliente"].nunique()
        )

        c3.metric(
            "AutoTrac Promedio",
            f"{basic['autotrac'].mean():.1f}%"
        )

        c4.metric(
            "Score Basic",
            f"{basic['score_basic'].mean():.1f}"
        )

        st.divider()

        ranking_basic = (
            basic
            .sort_values(
                "score_basic",
                ascending=False
            )
        )

        st.subheader("Ranking Basic")

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
            use_container_width=True,
            hide_index=True
        )

    # ==========================================
    # ELITE
    # ==========================================

    with elite_tab:

        elite = df_filtrado[
            df_filtrado["categoria"].str.upper()
            == "ELITE"
        ]

        st.subheader("Categoría Elite")

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

        st.divider()

        ranking_elite = (
            elite
            .sort_values(
                "score_elite",
                ascending=False
            )
        )

        st.subheader("Ranking Elite")

        st.dataframe(
            ranking_elite[
                [
                    "operario",
                    "cliente",
                    "sucursal",
                    "autotrac",
                    "turn_automation",
                    "ocio_controlable",
                    "score_elite"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

# =====================================================
# TAB INFORMES
# =====================================================

with tab_informe:

    st.info(
        "Próximamente: generación automática de informes."
    )

# =====================================================
# TAB CLIENTES
# =====================================================

with tab_clientes:

    basic_clientes, elite_clientes = st.tabs(
        [
            "Basic",
            "Elite"
        ]
    )

    with basic_clientes:

        st.dataframe(
            df_filtrado[
                df_filtrado["categoria"].str.upper()
                == "BASIC"
            ],
            use_container_width=True
        )

    with elite_clientes:

        st.dataframe(
            df_filtrado[
                df_filtrado["categoria"].str.upper()
                == "ELITE"
            ],
            use_container_width=True
        )
