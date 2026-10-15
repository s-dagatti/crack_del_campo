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

# Cambiar esta versión obliga a Streamlit a reconstruir
# el dataframe cuando se modifica la lógica del tablero.
CACHE_VERSION = "ranking_periodo_v3"


@st.cache_data(ttl=3600)
def load_data(cache_version):
    """
    Carga las fuentes, normaliza las categorías y calcula
    los scores semanales.
    """

    # El parámetro se utiliza para invalidar la caché.
    _ = cache_version

    datos = cargar_datos()

    validar_columnas_carga = [
        "categoria",
    ]

    faltantes = [
        columna
        for columna in validar_columnas_carga
        if columna not in datos.columns
    ]

    if faltantes:
        raise ValueError(
            "No se puede normalizar la categoría. "
            "Faltan las columnas: "
            + ", ".join(faltantes)
        )

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
    """
    Calcula el promedio numérico de una columna.

    Devuelve 0 cuando el dataframe está vacío, la columna
    no existe o no contiene valores numéricos.
    """

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


def construir_evolucion_semanal(
    df,
    metricas,
    nombres_metricas=None,
):
    """
    Construye la evolución semanal promedio de una categoría.

    Reglas:
    - Devuelve una fila por semana.
    - Utiliza fecha_fin como fecha representativa.
    - Las métricas ausentes aportan 0.
    - Calcula el promedio de las máquinas incluidas en
      la población seleccionada.
    """

    if df.empty:
        return pd.DataFrame()

    if "fecha_fin" not in df.columns:
        return pd.DataFrame()

    resultado = df.copy()

    resultado["fecha_fin"] = pd.to_datetime(
        resultado["fecha_fin"],
        errors="coerce",
        dayfirst=True,
    ).dt.normalize()

    resultado = resultado[
        resultado["fecha_fin"].notna()
    ].copy()

    if resultado.empty:
        return pd.DataFrame()

    metricas_disponibles = [
        metrica
        for metrica in metricas
        if metrica in resultado.columns
    ]

    if not metricas_disponibles:
        return pd.DataFrame()

    # Una tecnología sin dato representa que no hubo
    # actividad durante esa semana.
    for metrica in metricas_disponibles:
        resultado[metrica] = (
            pd.to_numeric(
                resultado[metrica],
                errors="coerce",
            )
            .fillna(0.0)
            .clip(lower=0, upper=100)
        )

    evolucion = (
        resultado
        .groupby(
            "fecha_fin",
            as_index=False,
            dropna=False,
        )[metricas_disponibles]
        .mean()
        .sort_values(
            "fecha_fin",
            ascending=True,
        )
    )

    if nombres_metricas:
        evolucion = evolucion.rename(
            columns=nombres_metricas
        )

    evolucion = evolucion.set_index(
        "fecha_fin"
    )

    evolucion.index.name = "Semana"

    return evolucion


def consolidar_periodo(df):
    """
    Consolida todas las semanas seleccionadas en una fila
    por número de serie.

    Reglas:
    - Las tecnologías se promedian durante el período.
    - Un valor tecnológico ausente aporta 0.
    - Las dimensiones descriptivas conservan el dato de
      la fila más reciente.
    - Los scores se recalculan con las métricas promedio.
    - La intervención se clasifica según el score promedio
      del período seleccionado.
    """

    if df.empty:
        return df.copy()

    resultado = df.copy()

    # =================================================
    # FECHAS
    # =================================================

    for columna_fecha in [
        "fecha_inicio",
        "fecha_fin",
    ]:
        if columna_fecha in resultado.columns:
            resultado[columna_fecha] = pd.to_datetime(
                resultado[columna_fecha],
                errors="coerce",
                dayfirst=True,
            ).dt.normalize()

    # La fila más reciente queda primero. De esta forma,
    # "first" conserva los datos descriptivos más actuales.
    if "fecha_fin" in resultado.columns:
        resultado = resultado.sort_values(
            "fecha_fin",
            ascending=False,
            na_position="last",
        )

    # =================================================
    # MÉTRICAS DEL PERÍODO
    # =================================================

    metricas_promedio = [
        "autotrac",
        "turn_automation",
        "autopath",
        "implement_guidance",
        "efficiency_manager",
        "field_cruise",
        "cancelada",
        "sin_definir",
        "ignorada",
        "ocio_controlable",
        "score_ociosidad",
    ]

    metricas_disponibles = [
        columna
        for columna in metricas_promedio
        if columna in resultado.columns
    ]

    # Un valor ausente durante una semana aporta 0
    # al promedio del período.
    for columna in metricas_disponibles:
        resultado[columna] = (
            pd.to_numeric(
                resultado[columna],
                errors="coerce",
            )
            .fillna(0.0)
            .clip(lower=0, upper=100)
        )

    # =================================================
    # DIMENSIONES DESCRIPTIVAS
    # =================================================

    dimensiones = [
        "operario",
        "cliente",
        "sucursal",
        "organizacion",
        "org_id",
        "categoria",
        "maquina",
        "modelo",
        "tipo",
        "telefono",
        "pais",
        "provincia",
        "ciudad",
    ]

    dimensiones_disponibles = [
        columna
        for columna in dimensiones
        if columna in resultado.columns
    ]

    agregaciones = {
        columna: "mean"
        for columna in metricas_disponibles
    }

    agregaciones.update(
        {
            columna: "first"
            for columna in dimensiones_disponibles
        }
    )

    # Las fechas del consolidado muestran el rango real
    # cubierto por cada máquina.
    if "fecha_inicio" in resultado.columns:
        agregaciones["fecha_inicio"] = "min"

    if "fecha_fin" in resultado.columns:
        agregaciones["fecha_fin"] = "max"

    consolidado = (
        resultado
        .groupby(
            "numero_serie",
            as_index=False,
            dropna=False,
        )
        .agg(agregaciones)
    )

    # Recalcula los scores y la intervención utilizando
    # los promedios del período.
    consolidado = calcular_scores(
        consolidado
    )

    return consolidado


def filtrar_historico_por_poblacion(
    historico,
    consolidado,
):
    """
    Restringe el histórico a las máquinas presentes en
    el dataframe consolidado final.

    Esto permite que la evolución temporal use la misma
    población que los KPI y el ranking.
    """

    if historico.empty:
        return historico.copy()

    if consolidado.empty:
        return historico.iloc[0:0].copy()

    if (
        "numero_serie" not in historico.columns
        or "numero_serie" not in consolidado.columns
    ):
        return historico.iloc[0:0].copy()

    series_seleccionadas = (
        consolidado["numero_serie"]
        .dropna()
        .unique()
        .tolist()
    )

    return historico[
        historico["numero_serie"].isin(
            series_seleccionadas
        )
    ].copy()


def mostrar_tabla_vacia(mensaje):
    st.info(mensaje)


# =====================================================
# CARGA DE DATOS
# =====================================================

try:
    df = load_data(
        CACHE_VERSION
    )

except Exception as error:
    st.error(
        "No se pudieron cargar las fuentes de datos del tablero."
    )

    with st.expander("Detalle técnico"):
        st.exception(error)

    st.stop()


# =====================================================
# VALIDACIÓN DEL DATAFRAME
# =====================================================

columnas_obligatorias = [
    "numero_serie",
    "sucursal",
    "cliente",
    "operario",
    "categoria",
    "fecha_inicio",
    "fecha_fin",
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
        st.write(
            df.columns.tolist()
        )

    st.stop()


# =====================================================
# NORMALIZACIÓN FINAL
# =====================================================

df["categoria"] = (
    df["categoria"]
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

df["sucursal"] = (
    df["sucursal"]
    .fillna("")
    .astype(str)
    .str.strip()
)

df["cliente"] = (
    df["cliente"]
    .fillna("")
    .astype(str)
    .str.strip()
)

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


# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("Filtros")


# =====================================================
# FILTRO DE SUCURSAL
# =====================================================

sucursales = sorted(
    df["sucursal"]
    .loc[lambda serie: serie.ne("")]
    .unique()
    .tolist()
)

sucursal_seleccionada = st.sidebar.selectbox(
    "Sucursal",
    options=[
        "Todas",
        *sucursales,
    ],
    index=0,
)


# =====================================================
# FILTRO DE CLIENTES
# =====================================================

df_sidebar = df.copy()

if sucursal_seleccionada!= "Todas":
    df_sidebar = df_sidebar[
        df_sidebar["sucursal"]
        == sucursal_seleccionada
    ]

clientes = sorted(
    df_sidebar["cliente"]
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
# APLICACIÓN DE FILTROS HISTÓRICOS
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
# PERÍODO
# =====================================================

if (
    periodo_seleccionado
    and isinstance(
        periodo_seleccionado,
        (tuple, list),
    )
    and len(periodo_seleccionado) == 2
):
    fecha_desde = pd.Timestamp(
        periodo_seleccionado[0]
    ).normalize()

    fecha_hasta = pd.Timestamp(
        periodo_seleccionado[1]
    ).normalize()

    # Incluye cualquier semana que se superponga
    # con el rango seleccionado.
    df_filtrado = df_filtrado[
        (
            df_filtrado["fecha_inicio"]
            <= fecha_hasta
        )
        & (
            df_filtrado["fecha_fin"]
            >= fecha_desde
        )
    ].copy()


# =====================================================
# HISTÓRICO POR CATEGORÍA
# =====================================================

basic_historico = df_filtrado[
    df_filtrado["categoria"] == "BASIC"
].copy()

elite_historico = df_filtrado[
    df_filtrado["categoria"] == "ELITE"
].copy()


# =====================================================
# CONSOLIDACIÓN DEL PERÍODO
# =====================================================

basic_periodo = consolidar_periodo(
    basic_historico
)

elite_periodo = consolidar_periodo(
    elite_historico
)


# =====================================================
# INTERVENCIÓN DEL PERÍODO
# =====================================================

# Este filtro se aplica después de consolidar las semanas,
# porque la intervención debe depender del score promedio
# del período y no de una semana individual.
if intervencion_seleccionada!= "Todas":
    if (
        not basic_periodo.empty
        and "necesidad_intervencion"
        in basic_periodo.columns
    ):
        basic_periodo = basic_periodo[
            basic_periodo[
                "necesidad_intervencion"
            ]
            == intervencion_seleccionada
        ].copy()

    if (
        not elite_periodo.empty
        and "necesidad_intervencion"
        in elite_periodo.columns
    ):
        elite_periodo = elite_periodo[
            elite_periodo[
                "necesidad_intervencion"
            ]
            == intervencion_seleccionada
        ].copy()


# =====================================================
# ALINEACIÓN DE HISTÓRICOS
# =====================================================

# La evolución utiliza la misma población seleccionada
# para los KPI, rankings y tablas de clientes.
basic_historico = filtrar_historico_por_poblacion(
    basic_historico,
    basic_periodo,
)

elite_historico = filtrar_historico_por_poblacion(
    elite_historico,
    elite_periodo,
)


# =====================================================
# RESUMEN DE FILTROS
# =====================================================

series_basic = (
    basic_periodo["numero_serie"]
    if "numero_serie" in basic_periodo.columns
    else pd.Series(dtype="string")
)

series_elite = (
    elite_periodo["numero_serie"]
    if "numero_serie" in elite_periodo.columns
    else pd.Series(dtype="string")
)

maquinas_seleccionadas = (
    pd.concat(
        [
            series_basic,
            series_elite,
        ],
        ignore_index=True,
    )
    .dropna()
    .nunique()
)

st.sidebar.caption(
    f"{maquinas_seleccionadas} "
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
        # Una fila por máquina con el promedio del período.
        basic = basic_periodo.copy()

        st.subheader("Categoría Basic")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Participantes",
            (
                basic["numero_serie"].nunique()
                if "numero_serie" in basic.columns
                else 0
            ),
        )

        c2.metric(
            "Clientes",
            (
                basic["cliente"].nunique()
                if "cliente" in basic.columns
                else 0
            ),
        )

        c3.metric(
            "AutoTrac promedio",
            (
                f"{promedio_seguro(basic, 'autotrac'):.1f}%"
            ),
        )

        c4.metric(
            "Score Basic",
            (
                f"{promedio_seguro(basic, 'score_basic'):.1f}"
            ),
        )

        # =================================================
        # EVOLUCIÓN TEMPORAL BASIC
        # =================================================

        st.divider()
        st.subheader(
            "Evolución temporal Basic"
        )

        evolucion_basic = construir_evolucion_semanal(
            basic_historico,
            metricas=[
                "autotrac",
                "score_basic",
            ],
            nombres_metricas={
                "autotrac": "AutoTrac",
                "score_basic": "Score Basic",
            },
        )

        if evolucion_basic.empty:
            st.info(
                "No hay datos históricos disponibles "
                "para construir la evolución temporal "
                "de la categoría Basic."
            )

        else:
            st.line_chart(
                evolucion_basic,
                use_container_width=True,
            )

            if len(evolucion_basic) == 1:
                st.caption(
                    "Actualmente hay una sola semana "
                    "disponible. La evolución se completará "
                    "automáticamente cuando se incorporen "
                    "nuevos períodos."
                )

            with st.expander(
                "Ver datos semanales Basic"
            ):
                st.dataframe(
                    evolucion_basic.reset_index(),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Semana": (
                            st.column_config.DateColumn(
                                format="DD/MM/YYYY"
                            )
                        ),
                        "AutoTrac": (
                            st.column_config.NumberColumn(
                                format="%.1f%%"
                            )
                        ),
                        "Score Basic": (
                            st.column_config.NumberColumn(
                                format="%.1f"
                            )
                        ),
                    },
                )

        # =================================================
        # RANKING BASIC
        # =================================================

        st.divider()
        st.subheader("Ranking Basic")

        if basic.empty:
            mostrar_tabla_vacia(
                "No hay participantes Basic para "
                "los filtros seleccionados."
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
                "fecha_inicio",
                "fecha_fin",
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
                    "No se puede construir el ranking "
                    "Basic. Faltan las columnas: "
                    + ", ".join(
                        faltantes_ranking_basic
                    )
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
                        "fecha_inicio": "Desde",
                        "fecha_fin": "Hasta",
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
                        "Desde": (
                            st.column_config.DateColumn(
                                format="DD/MM/YYYY"
                            )
                        ),
                        "Hasta": (
                            st.column_config.DateColumn(
                                format="DD/MM/YYYY"
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
        # Una fila por máquina con el promedio del período.
        elite = elite_periodo.copy()

        st.subheader("Categoría Elite")

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "Participantes",
            (
                elite["numero_serie"].nunique()
                if "numero_serie" in elite.columns
                else 0
            ),
        )

        c2.metric(
            "Score Elite",
            (
                f"{promedio_seguro(elite, 'score_elite'):.1f}"
            ),
        )

        c3.metric(
            "AutoTrac",
            (
                f"{promedio_seguro(elite, 'autotrac'):.1f}%"
            ),
        )

        c4.metric(
            "Turn Automation",
            (
                f"{promedio_seguro(elite, 'turn_automation'):.1f}%"
            ),
        )

        c5.metric(
            "Ocio controlable",
            (
                f"{promedio_seguro(elite, 'ocio_controlable'):.1f}%"
            ),
        )

        # =================================================
        # EVOLUCIÓN TEMPORAL ELITE
        # =================================================

        st.divider()
        st.subheader(
            "Evolución temporal Elite"
        )

        evolucion_elite = construir_evolucion_semanal(
            elite_historico,
            metricas=[
                "score_elite",
                "autotrac",
                "turn_automation",
                "autopath",
                "implement_guidance",
                "efficiency_manager",
                "field_cruise",
                "ocio_controlable",
            ],
            nombres_metricas={
                "score_elite": "Score Elite",
                "autotrac": "AutoTrac",
                "turn_automation": (
                    "Turn Automation"
                ),
                "autopath": "AutoPath",
                "implement_guidance": (
                    "Implement Guidance"
                ),
                "efficiency_manager": (
                    "Efficiency Manager"
                ),
                "field_cruise": (
                    "Field Cruise"
                ),
                "ocio_controlable": (
                    "Ocio controlable"
                ),
            },
        )

        if evolucion_elite.empty:
            st.info(
                "No hay datos históricos disponibles "
                "para construir la evolución temporal "
                "de la categoría Elite."
            )

        else:
            st.line_chart(
                evolucion_elite,
                use_container_width=True,
            )

            if len(evolucion_elite) == 1:
                st.caption(
                    "Actualmente hay una sola semana "
                    "disponible. La evolución se completará "
                    "automáticamente cuando se incorporen "
                    "nuevos períodos."
                )

            with st.expander(
                "Ver datos semanales Elite"
            ):
                st.dataframe(
                    evolucion_elite.reset_index(),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Semana": (
                            st.column_config.DateColumn(
                                format="DD/MM/YYYY"
                            )
                        ),
                        "Score Elite": (
                            st.column_config.NumberColumn(
                                format="%.1f"
                            )
                        ),
                        "AutoTrac": (
                            st.column_config.NumberColumn(
                                format="%.1f%%"
                            )
                        ),
                        "Turn Automation": (
                            st.column_config.NumberColumn(
                                format="%.1f%%"
                            )
                        ),
                        "AutoPath": (
                            st.column_config.NumberColumn(
                                format="%.1f%%"
                            )
                        ),
                        "Implement Guidance": (
                            st.column_config.NumberColumn(
                                format="%.1f%%"
                            )
                        ),
                        "Efficiency Manager": (
                            st.column_config.NumberColumn(
                                format="%.1f%%"
                            )
                        ),
                        "Field Cruise": (
                            st.column_config.NumberColumn(
                                format="%.1f%%"
                            )
                        ),
                        "Ocio controlable": (
                            st.column_config.NumberColumn(
                                format="%.1f%%"
                            )
                        ),
                    },
                )

        # =================================================
        # RANKING ELITE
        # =================================================

        st.divider()
        st.subheader("Ranking Elite")

        if elite.empty:
            mostrar_tabla_vacia(
                "No hay participantes Elite para "
                "los filtros seleccionados."
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
                "fecha_inicio",
                "fecha_fin",
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
                    "No se puede construir el ranking "
                    "Elite. Faltan las columnas: "
                    + ", ".join(
                        faltantes_ranking_elite
                    )
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
                        "fecha_inicio": "Desde",
                        "fecha_fin": "Hasta",
                        "autotrac": "AutoTrac (%)",
                        "turn_automation": (
                            "Turn Automation (%)"
                        ),
                        "autopath": (
                            "AutoPath (%)"
                        ),
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
                        "Desde": (
                            st.column_config.DateColumn(
                                format="DD/MM/YYYY"
                            )
                        ),
                        "Hasta": (
                            st.column_config.DateColumn(
                                format="DD/MM/YYYY"
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

    columnas_clientes_deseadas = [
        "operario",
        "cliente",
        "sucursal",
        "numero_serie",
        "organizacion",
        "org_id",
        "categoria",
        "fecha_inicio",
        "fecha_fin",
        "necesidad_intervencion",
    ]

    # =================================================
    # CLIENTES BASIC
    # =================================================

    with basic_clientes:
        datos_basic = basic_periodo.copy()

        columnas_basic_clientes = [
            columna
            for columna in columnas_clientes_deseadas
            if columna in datos_basic.columns
        ]

        if datos_basic.empty:
            mostrar_tabla_vacia(
                "No hay clientes Basic para "
                "los filtros seleccionados."
            )

        else:
            st.dataframe(
                datos_basic[
                    columnas_basic_clientes
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "fecha_inicio": (
                        st.column_config.DateColumn(
                            "Desde",
                            format="DD/MM/YYYY",
                        )
                    ),
                    "fecha_fin": (
                        st.column_config.DateColumn(
                            "Hasta",
                            format="DD/MM/YYYY",
                        )
                    ),
                    "necesidad_intervencion": (
                        st.column_config.TextColumn(
                            "Intervención",
                            width="medium",
                        )
                    ),
                },
            )

    # =================================================
    # CLIENTES ELITE
    # =================================================

    with elite_clientes:
        datos_elite = elite_periodo.copy()

        columnas_elite_clientes = [
            columna
            for columna in columnas_clientes_deseadas
            if columna in datos_elite.columns
        ]

        if datos_elite.empty:
            mostrar_tabla_vacia(
                "No hay clientes Elite para "
                "los filtros seleccionados."
            )

        else:
            st.dataframe(
                datos_elite[
                    columnas_elite_clientes
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "fecha_inicio": (
                        st.column_config.DateColumn(
                            "Desde",
                            format="DD/MM/YYYY",
                        )
                    ),
                    "fecha_fin": (
                        st.column_config.DateColumn(
                            "Hasta",
                            format="DD/MM/YYYY",
                        )
                    ),
                    "necesidad_intervencion": (
                        st.column_config.TextColumn(
                            "Intervención",
                            width="medium",
                        )
                    ),
                },
            )
