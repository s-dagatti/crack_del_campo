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

# La versión obliga a Streamlit a recalcular los datos cuando
# cambia la lógica de scores o intervención.
CACHE_VERSION = "scores_intervencion_v2"


@st.cache_data(ttl=3600)
def load_data(cache_version):
    datos = cargar_datos()

    # La categoría debe normalizarse antes de calcular
    # la necesidad de intervención.
    datos["categoria"] = (
        datos["categoria"]
        .fillna("SIN CATEGORÍA")
        .astype(str)
        .str.strip()
        .str.upper()
        .replace(
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
    )

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
    df = load_data(CACHE_VERSION)

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
    "necesidad_intervencion",
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


# =====================================================
# FILTRO DE SUCURSAL
# =====================================================

sucursales = sorted(
    df["sucursal"]
    .dropna()
    .astype(str)
    .str.strip()
    .loc[lambda serie: serie.ne("")]
    .unique()
    .tolist()
)

sucursal_seleccionada = st.sidebar.selectbox(
    "Sucursal",
    options=["Todas"] + sucursales,
    index=0,
)


# =====================================================
# FILTRO DE CLIENTES
# =====================================================

# La lista de clientes depende de la sucursal seleccionada.
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
    .str.strip()
    .loc[lambda serie: serie.ne("")]
    .unique()
    .tolist()
)

clientes_seleccionados = st.sidebar.multiselect(
    "Cliente",
    options=clientes,
    default=[],
)


# =====================================================
# FILTRO DE NECESIDAD DE INTERVENCIÓN
# =====================================================

opciones_intervencion = [
    "Todas",
    "INTERVENCIÓN NECESARIA",
    "INTERVENCIÓN MODERADA",
    "NO REQUIERE INTERVENCIÓN",
]

intervencion_seleccionada = st.sidebar.selectbox(
    "Necesidad de intervención",
    options=opciones_intervencion,
    index=0,
)
# =====================================================
# FILTRO DE FECHAS
# =====================================================

periodo_seleccionado = None

if (
    "fecha_inicio" in df.columns
    and "fecha_fin" in df.columns
):
    df["fecha_inicio"] = pd.to_datetime(
        df["fecha_inicio"],
        errors="coerce",
        dayfirst=True,
    ).dt.normalize()

    df["fecha_fin"] = pd.to_datetime(
        df["fecha_fin"],
        errors="coerce",
        dayfirst=True,
    ).dt.normalize()

    fecha_minima = df["fecha_inicio"].min()
    fecha_maxima = df["fecha_fin"].max()

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


# =====================================================
# SUCURSAL
# =====================================================

if sucursal_seleccionada!= "Todas":
    df_filtrado = df_filtrado[
        df_filtrado["sucursal"]
        == sucursal_seleccionada
    ]


# =====================================================
# CLIENTES
# =====================================================

if clientes_seleccionados:
    df_filtrado = df_filtrado[
        df_filtrado["cliente"].isin(
            clientes_seleccionados
        )
    ]


# =====================================================
# PERIODO
# =====================================================

if (
    periodo_seleccionado
    and isinstance(
        periodo_seleccionado,
        (tuple, list),
    )
    and len(periodo_seleccionado) == 2
    and "fecha_inicio" in df_filtrado.columns
    and "fecha_fin" in df_filtrado.columns
):
    fecha_desde = pd.Timestamp(
        periodo_seleccionado[0]
    ).normalize()

    fecha_hasta = pd.Timestamp(
        periodo_seleccionado[1]
    ).normalize()

    # Incluye las semanas que se superponen con el rango.
    df_filtrado = df_filtrado[
        (
            df_filtrado["fecha_inicio"]
            <= fecha_hasta
        )
        & (
            df_filtrado["fecha_fin"]
            >= fecha_desde
        )
    ]


# =====================================================
# NECESIDAD DE INTERVENCIÓN
# =====================================================

if intervencion_seleccionada!= "Todas":
    df_filtrado = df_filtrado[
        df_filtrado["necesidad_intervencion"]
        == intervencion_seleccionada
    ]


# =====================================================
# RESUMEN DE FILTROS
# =====================================================

st.sidebar.caption(
    f"{df_filtrado['numero_serie'].nunique()} "
    "máquinas seleccionadas"
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
        
            columnas_ranking_basic = [
                "posición",
                "operario",
                "cliente",
                "sucursal",
                "numero_serie",
                "autotrac",
                "score_basic",
                "necesidad_intervencion",
            ]
        
            faltantes_ranking_basic = [
                columna
                for columna in columnas_ranking_basic
                if columna not in ranking_basic.columns
            ]
        
            if faltantes_ranking_basic:
                st.error(
                    "No se puede construir el ranking Basic. "
                    "Faltan las columnas: "
                    + ", ".join(faltantes_ranking_basic)
                )
        
                with st.expander(
                    "Columnas disponibles en el ranking Basic"
                ):
                    st.write(
                        ranking_basic.columns.tolist()
                    )
        
            else:
                tabla_basic = ranking_basic[
                    columnas_ranking_basic
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
                        "necesidad_intervencion": (
                            "Intervención"
                        ),
                    }
                )
        
                st.dataframe(
                    tabla_basic,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Posición": (
                            st.column_config.NumberColumn(
                                format="%d",
                                width="small",
                            )
                        ),
                        "AutoTrac (%)": (
                            st.column_config.NumberColumn(
                                format="%.1f%%"
                            )
                        ),
                        "Score Basic": (
                            st.column_config.NumberColumn(
                                format="%.1f"
                            )
                        ),
                        "Intervención": (
                            st.column_config.TextColumn(
                                width="medium"
                            )
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
        
            columnas_ranking_elite = [
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
                "necesidad_intervencion",
            ]
        
            faltantes_ranking_elite = [
                columna
                for columna in columnas_ranking_elite
                if columna not in ranking_elite.columns
            ]
        
            if faltantes_ranking_elite:
                st.error(
                    "No se puede construir el ranking Elite. "
                    "Faltan las columnas: "
                    + ", ".join(faltantes_ranking_elite)
                )
        
                with st.expander(
                    "Columnas disponibles en el ranking Elite"
                ):
                    st.write(
                        ranking_elite.columns.tolist()
                    )
        
            else:
                tabla_elite = ranking_elite[
                    columnas_ranking_elite
                ].copy()
        
                tabla_elite = tabla_elite.rename(
                    columns={
                        "posición": "Posición",
                        "operario": "Operario",
                        "cliente": "Cliente",
                        "sucursal": "Sucursal",
                        "numero_serie": "N.º de serie",
                        "autotrac": "AutoTrac (%)",
                        "turn_automation": (
                            "Turn Automation (%)"
                        ),
                        "autopath": "AutoPath (%)",
                        "implement_guidance": (
                            "Implement Guidance (%)"
                        ),
                        "efficiency_manager": (
                            "Efficiency Manager (%)"
                        ),
                        "field_cruise": (
                            "Field Cruise (%)"
                        ),
                        "ocio_controlable": (
                            "Ocio controlable (%)"
                        ),
                        "score_elite": "Score Elite",
                        "necesidad_intervencion": (
                            "Intervención"
                        ),
                    }
                )
        
                st.dataframe(
                    tabla_elite,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Posición": (
                            st.column_config.NumberColumn(
                                format="%d",
                                width="small",
                            )
                        ),
                        "AutoTrac (%)": (
                            st.column_config.NumberColumn(
                                format="%.1f%%"
                            )
                        ),
                        "Turn Automation (%)": (
                            st.column_config.NumberColumn(
                                format="%.1f%%"
                            )
                        ),
                        "AutoPath (%)": (
                            st.column_config.NumberColumn(
                                format="%.1f%%"
                            )
                        ),
                        "Implement Guidance (%)": (
                            st.column_config.NumberColumn(
                                format="%.1f%%"
                            )
                        ),
                        "Efficiency Manager (%)": (
                            st.column_config.NumberColumn(
                                format="%.1f%%"
                            )
                        ),
                        "Field Cruise (%)": (
                            st.column_config.NumberColumn(
                                format="%.1f%%"
                            )
                        ),
                        "Ocio controlable (%)": (
                            st.column_config.NumberColumn(
                                format="%.1f%%"
                            )
                        ),
                        "Score Elite": (
                            st.column_config.NumberColumn(
                                format="%.1f"
                            )
                        ),
                        "Intervención": (
                            st.column_config.TextColumn(
                                width="medium"
                            )
                        ),
                    },
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
            "necesidad_intervencion",
        ]
        if columna in df_filtrado.columns
    ]

    with basic_clientes:
        datos_basic = participantes_unicos(
            df_filtrado[
                df_filtrado["categoria"] == "BASIC"
            ].copy()
        )
    
        if datos_basic.empty:
            mostrar_tabla_vacia(
                "No hay clientes Basic para los filtros seleccionados."
            )
    
        else:
            st.dataframe(
                datos_basic[columnas_clientes],
                use_container_width=True,
                hide_index=True,
            )
    
    
    with elite_clientes:
        datos_elite = participantes_unicos(
            df_filtrado[
                df_filtrado["categoria"] == "ELITE"
            ].copy()
        )
    
        if datos_elite.empty:
            mostrar_tabla_vacia(
                "No hay clientes Elite para los filtros seleccionados."
            )
    
        else:
            st.dataframe(
                datos_elite[columnas_clientes],
                use_container_width=True,
                hide_index=True,
            )
