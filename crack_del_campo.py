import pandas as pd
import streamlit as st

from utils.data_loader import cargar_datos
from utils.metrics import calcular_scores


# =====================================================
# CONFIGURACIÓN
# =====================================================

st.set_page_config(
    page_title="Crack del Campo",
    page_icon="🚜",
    layout="wide",
)

st.title("🚜 Crack del Campo FY27")
st.caption("Seguimiento de participantes - Tractores")


# =====================================================
# FUNCIONES
# =====================================================

@st.cache_data(ttl=3600)
def load_data():
    datos = cargar_datos()
    datos = calcular_scores(datos)

    return datos


def promedio_seguro(df, columna):
    if df.empty or columna not in df.columns:
        return 0.0

    valores = pd.to_numeric(
        df[columna],
        errors="coerce",
    )

    resultado = valores.mean()

    if pd.isna(resultado):
        return 0.0

    return float(resultado)


def participantes_unicos(df):
    """
    Construye una fila por número de serie para evitar que
    el histórico semanal duplique participantes en el ranking.

    Por ahora conserva el registro más reciente disponible.
    """

    if df.empty:
        return df.copy()

    resultado = df.copy()

    columnas_fecha = [
        "fecha",
        "fecha_de_terminacion",
        "fecha_fin",
        "fecha_de_inicio",
        "fecha_inicio",
    ]

    columna_fecha = next(
        (
            columna
            for columna in columnas_fecha
            if columna in resultado.columns
        ),
        None,
    )

    if columna_fecha:
        resultado[columna_fecha] = pd.to_datetime(
            resultado[columna_fecha],
            errors="coerce",
            dayfirst=True,
        )

        resultado = resultado.sort_values(
            columna_fecha,
            ascending=False,
        )

    return resultado.drop_duplicates(
        subset=["numero_serie"],
        keep="first",
    )


def mostrar_tabla_vacia(mensaje):
    st.info(mensaje)


# =====================================================
# CARGA DE DATOS
# =====================================================

try:
    df = load_data()

except Exception as error:
    st.error(
        "No se pudieron cargar las fuentes de datos del tablero."
    )

    with st.expander("Detalle técnico"):
        st.exception(error)

    st.stop()


columnas_obligatorias = [
    "numero_serie",
    "sucursal",
    "cliente",
    "operario",
    "categoria",
    "autotrac",
    "score_basic",
    "score_elite",
]

columnas_faltantes = [
    columna
    for columna in columnas_obligatorias
    if columna not in df.columns
]

if columnas_faltantes:
    st.error(
        "Faltan columnas necesarias para mostrar el tablero: "
        + ", ".join(columnas_faltantes)
    )

    with st.expander("Columnas disponibles"):
        st.write(df.columns.tolist())

    st.stop()


# =====================================================
# NORMALIZACIÓN DE CATEGORÍAS
# =====================================================

df["categoria"] = (
    df["categoria"]
    .fillna("SIN CATEGORÍA")
    .astype(str)
    .str.strip()
    .str.upper()
)

df["categoria"] = df["categoria"].replace(
    {
        "BASE": "BASIC",
        "BÁSICO": "BASIC",
        "BASICO": "BASIC",
        "GUIADO BÁSICO": "BASIC",
        "GUIADO BASICO": "BASIC",
        "AVANZADO": "ELITE",
        "GUIADO AVANZADO": "ELITE",
    }
)


# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("Filtros")

sucursales = sorted(
    df["sucursal"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

sucursal_seleccionada = st.sidebar.selectbox(
    "Sucursal",
    options=["Todas"] + sucursales,
    index=0,
)

# Primero filtra sucursales para que el selector de clientes
# muestre solamente clientes asociados a ellas.
df_sidebar = df.copy()

if sucursal_seleccionada!= "Todas":
    df_sidebar = df_sidebar[
        df_sidebar["sucursal"]
        == sucursal_seleccionada
    ]

clientes = sorted(
    df_sidebar["cliente"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

clientes_seleccionados = st.sidebar.multiselect(
    "Cliente",
    options=clientes,
    default=[],
)


# =====================================================
# FILTRO DE FECHAS
# =====================================================

columnas_fecha_posibles = [
    "fecha",
    "fecha_de_terminacion",
    "fecha_fin",
]

columna_fecha = next(
    (
        columna
        for columna in columnas_fecha_posibles
        if columna in df.columns
    ),
    None,
)

periodo_seleccionado = None

if columna_fecha:
    df[columna_fecha] = pd.to_datetime(
        df[columna_fecha],
        errors="coerce",
        dayfirst=True,
    )

    fecha_minima = df[columna_fecha].min()
    fecha_maxima = df[columna_fecha].max()

    if (
        pd.notna(fecha_minima)
        and pd.notna(fecha_maxima)
    ):
        periodo_seleccionado = st.sidebar.date_input(
            "Periodo",
            value=(
                fecha_minima.date(),
                fecha_maxima.date(),
            ),
            min_value=fecha_minima.date(),
            max_value=fecha_maxima.date(),
        )


# =====================================================
# APLICACIÓN DE FILTROS
# =====================================================

df_filtrado = df.copy()

if sucursal_seleccionada!= "Todas":
    df_filtrado = df_filtrado[
        df_filtrado["sucursal"]
        == sucursal_seleccionada
    ]

if clientes_seleccionados:
    df_filtrado = df_filtrado[
        df_filtrado["cliente"].isin(
            clientes_seleccionados
        )
    ]

if (
    columna_fecha
    and periodo_seleccionado
    and isinstance(periodo_seleccionado, tuple)
    and len(periodo_seleccionado) == 2
):
    fecha_desde = pd.Timestamp(
        periodo_seleccionado[0]
    )

    fecha_hasta = (
        pd.Timestamp(periodo_seleccionado[1])
        + pd.Timedelta(days=1)
        - pd.Timedelta(microseconds=1)
    )

    df_filtrado = df_filtrado[
        df_filtrado[columna_fecha].between(
            fecha_desde,
            fecha_hasta,
            inclusive="both",
        )
    ]

st.sidebar.caption(
    f"{df_filtrado['numero_serie'].nunique()} máquinas seleccionadas"
)


# =====================================================
# TABS PRINCIPALES
# =====================================================

tab_general, tab_informe, tab_clientes = st.tabs(
    [
        "📊 Tablero General",
        "📄 Generación Informe",
        "👥 Datos Clientes",
    ]
)


# =====================================================
# TAB GENERAL
# =====================================================

with tab_general:
    basic_tab, elite_tab = st.tabs(
        [
            "🚜 Basic",
            "🏆 Elite",
        ]
    )

    # =================================================
    # BASIC
    # =================================================

    with basic_tab:
        basic_historico = df_filtrado[
            df_filtrado["categoria"] == "BASIC"
        ].copy()

        basic = participantes_unicos(
            basic_historico
        )

        st.subheader("Categoría Basic")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Participantes",
            basic["numero_serie"].nunique(),
        )

        c2.metric(
            "Clientes",
            basic["cliente"].nunique(),
        )

        c3.metric(
            "AutoTrac promedio",
            f"{promedio_seguro(basic, 'autotrac'):.1f}%",
        )

        c4.metric(
            "Score Basic",
            f"{promedio_seguro(basic, 'score_basic'):.1f}",
        )

        st.divider()
        st.subheader("Ranking Basic")

        if basic.empty:
            mostrar_tabla_vacia(
                "No hay participantes Basic para los filtros seleccionados."
            )

        else:
            ranking_basic = (
                basic
                .sort_values(
                    "score_basic",
                    ascending=False,
                )
                .reset_index(drop=True)
            )

            ranking_basic.insert(
                0,
                "posición",
                range(
                    1,
                    len(ranking_basic) + 1,
                ),
            )

            tabla_basic = ranking_basic[
                [
                    "posición",
                    "operario",
                    "cliente",
                    "sucursal",
                    "numero_serie",
                    "autotrac",
                    "score_basic",
                ]
            ].copy()

            tabla_basic = tabla_basic.rename(
                columns={
                    "posición": "Posición",
                    "operario": "Operario",
                    "cliente": "Cliente",
                    "sucursal": "Sucursal",
                    "numero_serie": "N.º de serie",
                    "autotrac": "AutoTrac (%)",
                    "score_basic": "Score Basic",
                }
            )

            st.dataframe(
                tabla_basic,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "AutoTrac (%)": st.column_config.NumberColumn(
                        format="%.1f%%"
                    ),
                    "Score Basic": st.column_config.NumberColumn(
                        format="%.1f"
                    ),
                },
            )

    # =================================================
    # ELITE
    # =================================================

    with elite_tab:
        elite_historico = df_filtrado[
            df_filtrado["categoria"] == "ELITE"
        ].copy()

        elite = participantes_unicos(
            elite_historico
        )

        st.subheader("Categoría Elite")

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "Participantes",
            elite["numero_serie"].nunique(),
        )

        c2.metric(
            "Score Elite",
            f"{promedio_seguro(elite, 'score_elite'):.1f}",
        )

        c3.metric(
            "AutoTrac",
            f"{promedio_seguro(elite, 'autotrac'):.1f}%",
        )

        c4.metric(
            "Turn Automation",
            f"{promedio_seguro(elite, 'turn_automation'):.1f}%",
        )

        c5.metric(
            "Ocio controlable",
            f"{promedio_seguro(elite, 'ocio_controlable'):.1f}%",
        )

        st.divider()
        st.subheader("Ranking Elite")

        if elite.empty:
            mostrar_tabla_vacia(
                "No hay participantes Elite para los filtros seleccionados."
            )

        else:
            ranking_elite = (
                elite
                .sort_values(
                    "score_elite",
                    ascending=False,
                )
                .reset_index(drop=True)
            )

            ranking_elite.insert(
                0,
                "posición",
                range(
                    1,
                    len(ranking_elite) + 1,
                ),
            )

            tabla_elite = ranking_elite[
                [
                    "posición",
                    "operario",
                    "cliente",
                    "sucursal",
                    "numero_serie",
                    "autotrac",
                    "turn_automation",
                    "autopath",
                    "implement_guidance",
                    "efficiency_manager",
                    "field_cruise",
                    "ocio_controlable",
                    "score_elite",
                ]
            ].copy()

            tabla_elite = tabla_elite.rename(
                columns={
                    "posición": "Posición",
                    "operario": "Operario",
                    "cliente": "Cliente",
                    "sucursal": "Sucursal",
                    "numero_serie": "N.º de serie",
                    "autotrac": "AutoTrac (%)",
                    "turn_automation": "Turn Automation (%)",
                    "autopath": "AutoPath (%)",
                    "implement_guidance": "Implement Guidance (%)",
                    "efficiency_manager": "Efficiency Manager (%)",
                    "field_cruise": "Field Cruise (%)",
                    "ocio_controlable": "Ocio controlable (%)",
                    "score_elite": "Score Elite",
                }
            )

            st.dataframe(
                tabla_elite,
                use_container_width=True,
                hide_index=True,
            )


# =====================================================
# TAB INFORME
# =====================================================

with tab_informe:
    st.info(
        "Próximamente: generación automática de informes."
    )


# =====================================================
# TAB DATOS DE CLIENTES
# =====================================================

with tab_clientes:
    basic_clientes, elite_clientes = st.tabs(
        [
            "Basic",
            "Elite",
        ]
    )

    columnas_clientes = [
        columna
        for columna in [
            "operario",
            "cliente",
            "sucursal",
            "numero_serie",
            "organizacion",
            "org_id",
            "categoria",
        ]
        if columna in df_filtrado.columns
    ]

    with basic_clientes:
        datos_basic = (
            df_filtrado[
                df_filtrado["categoria"] == "BASIC"
            ]
            .drop_duplicates(
                subset=["numero_serie"]
            )
        )

        st.dataframe(
            datos_basic[columnas_clientes],
            use_container_width=True,
            hide_index=True,
        )

    with elite_clientes:
        datos_elite = (
            df_filtrado[
                df_filtrado["categoria"] == "ELITE"
            ]
            .drop_duplicates(
                subset=["numero_serie"]
            )
        )

        st.dataframe(
            datos_elite[columnas_clientes],
            use_container_width=True,
            hide_index=True,
        )
