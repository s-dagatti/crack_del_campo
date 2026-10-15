import pandas as pd
import streamlit as st


from utils.metrics import calcular_scores

from utils.data_loader import (
    COLUMN_MAPPING_CLIENTES,
    cargar_datos,
    normalizar_encabezados,
)

from utils.github_clientes import (
    cargar_clientes_github,
    guardar_clientes_github,
    normalizar_numero_serie_valor,
)

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

def valor_informado(serie):
    """
    Devuelve una máscara booleana que identifica valores
    realmente informados.

    Considera vacíos:
    - NaN;
    - texto vacío;
    - 'nan';
    - 'none';
    - 'sin asignar';
    - 'sin datos';
    - 'sin dato'.
    """

    texto = (
        serie
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    valores_vacios = [
        "",
        "nan",
        "none",
        "null",
        "sin asignar",
        "sin datos",
        "sin dato",
        "no informado",
    ]

    return ~texto.isin(
        valores_vacios
    )


def calcular_completitud_clientes(df):
    """
    Calcula indicadores de completitud para el listado
    de participantes.

    Un registro se considera completo cuando contiene:
    - organización;
    - Organization ID;
    - sucursal;
    - número de serie;
    - nombre del operario;
    - categoría;
    - teléfono del operario.
    """

    campos_requeridos = [
        "organizacion",
        "org_id",
        "sucursal",
        "numero_serie",
        "operario",
        "categoria",
        "telefono_operario",
    ]

    total = len(df)

    if total == 0:
        return {
            "total": 0,
            "registros_completos": 0,
            "porcentaje_completo": 0.0,
            "telefonos_cargados": 0,
            "porcentaje_telefonos": 0.0,
        }

    mascara_completa = pd.Series(
        True,
        index=df.index,
        dtype="bool",
    )

    for columna in campos_requeridos:
        if columna not in df.columns:
            mascara_completa &= False

        else:
            mascara_completa &= valor_informado(
                df[columna]
            )

    registros_completos = int(
        mascara_completa.sum()
    )

    if "telefono_operario" in df.columns:
        telefonos_cargados = int(
            valor_informado(
                df["telefono_operario"]
            ).sum()
        )

    else:
        telefonos_cargados = 0

    porcentaje_completo = (
        registros_completos
        / total
        * 100
    )

    porcentaje_telefonos = (
        telefonos_cargados
        / total
        * 100
    )

    return {
        "total": total,
        "registros_completos": registros_completos,
        "porcentaje_completo": porcentaje_completo,
        "telefonos_cargados": telefonos_cargados,
        "porcentaje_telefonos": porcentaje_telefonos,
    }


def mostrar_resumen_completitud(df):
    """
    Muestra los KPI de completitud del listado.
    """

    indicadores = calcular_completitud_clientes(
        df
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Máquinas",
        indicadores["total"],
    )

    c2.metric(
        "Registros completos",
        (
            f"{indicadores['registros_completos']} "
            f"de {indicadores['total']}"
        ),
    )

    c3.metric(
        "Información completa",
        (
            f"{indicadores['porcentaje_completo']:.1f}%"
        ),
    )

    c4.metric(
        "Celular de operario",
        (
            f"{indicadores['telefonos_cargados']} "
            f"de {indicadores['total']} "
            f"({indicadores['porcentaje_telefonos']:.1f}%)"
        ),
    )
    
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
        "telefono_operario",
        "telefono_cliente",
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
# EDICIÓN DE PARTICIPANTES
# =====================================================

COLUMNAS_CLIENTES_EDITABLES = [
    "numero_serie",
    "organizacion",
    "org_id",
    "sucursal",
    "operario",
    "cliente",
    "telefono_operario",
    "telefono_cliente",
    "pais",
    "provincia",
    "ciudad",
    "categoria",
]


def preparar_clientes_edicion(df_original):
    """
    Normaliza la estructura del CSV para que pueda ser
    utilizada por los formularios de edición.

    Las columnas no reconocidas se conservan.
    """

    df = normalizar_encabezados(
        df_original,
        COLUMN_MAPPING_CLIENTES,
    )

    for columna in COLUMNAS_CLIENTES_EDITABLES:
        if columna not in df.columns:
            df[columna] = ""

    for columna in df.columns:
        df[columna] = (
            df[columna]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    df["numero_serie"] = (
        df["numero_serie"]
        .apply(normalizar_numero_serie_valor)
    )

    df["categoria"] = (
        df["categoria"]
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

    return df


def valor_registro(registro, columna):
    """
    Devuelve un valor de texto seguro para utilizar como
    valor inicial de un campo de formulario.
    """

    if columna not in registro.index:
        return ""

    valor = registro[columna]

    if pd.isna(valor):
        return ""

    return str(valor).strip()


def guardar_cambios_clientes(
    df_clientes,
    sha,
    separador,
    mensaje,
):
    """
    Guarda el CSV, limpia la caché y muestra el resultado
    después de recargar la aplicación.
    """

    guardar_clientes_github(
        dataframe=df_clientes,
        sha=sha,
        separador=separador,
        mensaje_commit=mensaje,
    )

    load_data.clear()

    st.session_state[
        "mensaje_edicion_clientes"
    ] = "Los cambios se guardaron correctamente en GitHub."

    st.rerun()


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
# FILTRO DE ORGANIZACIONES
# =====================================================

# La lista de organizaciones depende de la sucursal
# seleccionada.
df_sidebar = df.copy()

if sucursal_seleccionada!= "Todas":
    df_sidebar = df_sidebar[
        df_sidebar["sucursal"]
        == sucursal_seleccionada
    ]

organizaciones = sorted(
    df_sidebar["organizacion"]
    .fillna("")
    .astype(str)
    .str.strip()
    .loc[lambda serie: serie.ne("")]
    .unique()
    .tolist()
)

organizaciones_seleccionadas = st.sidebar.multiselect(
    "Organización",
    options=organizaciones,
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
                "organizacion",
                "org_id",
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
                    "No se puede construir el ranking Basic. "
                    "Faltan las columnas: "
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
                        "organizacion": "Organización",
                        "org_id": "Organization ID",
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
                        "Organización": (
                            st.column_config.TextColumn(
                                width="medium",
                            )
                        ),
                        "Organization ID": (
                            st.column_config.TextColumn(
                                width="medium",
                            )
                        ),
                        "Operario": (
                            st.column_config.TextColumn(
                                width="medium",
                            )
                        ),
                        "Cliente": (
                            st.column_config.TextColumn(
                                width="medium",
                            )
                        ),
                        "Sucursal": (
                            st.column_config.TextColumn(
                                width="small",
                            )
                        ),
                        "N.º de serie": (
                            st.column_config.TextColumn(
                                width="medium",
                            )
                        ),
                        "Desde": (
                            st.column_config.DateColumn(
                                format="DD/MM/YYYY",
                            )
                        ),
                        "Hasta": (
                            st.column_config.DateColumn(
                                format="DD/MM/YYYY",
                            )
                        ),
                        "AutoTrac (%)": (
                            st.column_config.NumberColumn(
                                format="%.1f%%",
                            )
                        ),
                        "Score Basic": (
                            st.column_config.NumberColumn(
                                format="%.1f",
                            )
                        ),
                        "Intervención": (
                            st.column_config.TextColumn(
                                width="medium",
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
                "organizacion",
                "org_id",
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
                    "No se puede construir el ranking Elite. "
                    "Faltan las columnas: "
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
                        "organizacion": "Organización",
                        "org_id": "Organization ID",
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
                        "Organización": (
                            st.column_config.TextColumn(
                                width="medium",
                            )
                        ),
                        "Organization ID": (
                            st.column_config.TextColumn(
                                width="medium",
                            )
                        ),
                        "Operario": (
                            st.column_config.TextColumn(
                                width="medium",
                            )
                        ),
                        "Cliente": (
                            st.column_config.TextColumn(
                                width="medium",
                            )
                        ),
                        "Sucursal": (
                            st.column_config.TextColumn(
                                width="small",
                            )
                        ),
                        "N.º de serie": (
                            st.column_config.TextColumn(
                                width="medium",
                            )
                        ),
                        "Desde": (
                            st.column_config.DateColumn(
                                format="DD/MM/YYYY",
                            )
                        ),
                        "Hasta": (
                            st.column_config.DateColumn(
                                format="DD/MM/YYYY",
                            )
                        ),
                        "AutoTrac (%)": (
                            st.column_config.NumberColumn(
                                format="%.1f%%",
                            )
                        ),
                        "Turn Automation (%)": (
                            st.column_config.NumberColumn(
                                format="%.1f%%",
                            )
                        ),
                        "AutoPath (%)": (
                            st.column_config.NumberColumn(
                                format="%.1f%%",
                            )
                        ),
                        "Implement Guidance (%)": (
                            st.column_config.NumberColumn(
                                format="%.1f%%",
                            )
                        ),
                        "Efficiency Manager (%)": (
                            st.column_config.NumberColumn(
                                format="%.1f%%",
                            )
                        ),
                        "Field Cruise (%)": (
                            st.column_config.NumberColumn(
                                format="%.1f%%",
                            )
                        ),
                        "Ocio controlable (%)": (
                            st.column_config.NumberColumn(
                                format="%.1f%%",
                            )
                        ),
                        "Score Elite": (
                            st.column_config.NumberColumn(
                                format="%.1f",
                            )
                        ),
                        "Intervención": (
                            st.column_config.TextColumn(
                                width="medium",
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
    basic_clientes, elite_clientes, edicion_clientes = st.tabs(
        [
            "Basic",
            "Elite",
            "Edición",
        ]
    )

    columnas_clientes_deseadas = [
        "organizacion",
        "org_id",
        "sucursal",
        "numero_serie",
        "operario",
        "categoria",
        "telefono_operario",
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
            st.subheader(
                "Participantes Basic"
            )
    
            mostrar_resumen_completitud(
                datos_basic
            )
    
            st.caption(
                "Un registro se considera completo cuando tiene "
                "organización, Organization ID, sucursal, número "
                "de serie, operario, categoría y celular del "
                "operario."
            )
    
            st.dataframe(
                datos_basic[
                    columnas_basic_clientes
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "organizacion": (
                        st.column_config.TextColumn(
                            "Organización"
                        )
                    ),
                    "org_id": (
                        st.column_config.TextColumn(
                            "Organization ID"
                        )
                    ),
                    "sucursal": (
                        st.column_config.TextColumn(
                            "Sucursal"
                        )
                    ),
                    "numero_serie": (
                        st.column_config.TextColumn(
                            "N.º de serie"
                        )
                    ),
                    "operario": (
                        st.column_config.TextColumn(
                            "Operario"
                        )
                    ),
                    "categoria": (
                        st.column_config.TextColumn(
                            "Categoría"
                        )
                    ),
                    "telefono_operario": (
                        st.column_config.TextColumn(
                            "Celular del operario"
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
            st.subheader(
                "Participantes Elite"
            )
    
            mostrar_resumen_completitud(
                datos_elite
            )
    
            st.caption(
                "Un registro se considera completo cuando tiene "
                "organización, Organization ID, sucursal, número "
                "de serie, operario, categoría y celular del "
                "operario."
            )
    
            st.dataframe(
                datos_elite[
                    columnas_elite_clientes
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "organizacion": (
                        st.column_config.TextColumn(
                            "Organización"
                        )
                    ),
                    "org_id": (
                        st.column_config.TextColumn(
                            "Organization ID"
                        )
                    ),
                    "sucursal": (
                        st.column_config.TextColumn(
                            "Sucursal"
                        )
                    ),
                    "numero_serie": (
                        st.column_config.TextColumn(
                            "N.º de serie"
                        )
                    ),
                    "operario": (
                        st.column_config.TextColumn(
                            "Operario"
                        )
                    ),
                    "categoria": (
                        st.column_config.TextColumn(
                            "Categoría"
                        )
                    ),
                    "telefono_operario": (
                        st.column_config.TextColumn(
                            "Celular del operario"
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
    # EDICIÓN
    # =================================================

    with edicion_clientes:
        st.subheader(
            "Administración de máquinas inscriptas"
        )

        st.caption(
            "Los cambios realizados en esta sección se guardan "
            "directamente en data/base_de_clientes.csv dentro "
            "del repositorio de GitHub."
        )

        mensaje_guardado = st.session_state.pop(
            "mensaje_edicion_clientes",
            None,
        )

        if mensaje_guardado:
            st.success(
                mensaje_guardado
            )

        try:
            clientes_raw, clientes_sha, separador_csv = (
                cargar_clientes_github()
            )

            clientes_edicion = preparar_clientes_edicion(
                clientes_raw
            )

        except Exception as error:
            st.error(
                "No fue posible cargar la base editable "
                "de participantes."
            )

            with st.expander(
                "Detalle técnico de la carga"
            ):
                st.exception(error)

            st.stop()

        editar_tab, agregar_tab, eliminar_tab = st.tabs(
            [
                "Editar máquina",
                "Agregar máquina",
                "Eliminar máquina",
            ]
        )

        # =============================================
        # EDITAR MÁQUINA
        # =============================================
        
        with editar_tab:
            if clientes_edicion.empty:
                st.info(
                    "No hay máquinas disponibles para editar."
                )
        
            else:
                st.markdown(
                    "#### Buscar máquina"
                )
        
                texto_busqueda = st.text_input(
                    (
                        "Buscar por número de serie, cliente, "
                        "organización u operario"
                    ),
                    placeholder=(
                        "Ej.: 1RW..., nombre del cliente, "
                        "organización u operario"
                    ),
                    key="buscar_maquina_edicion",
                )
        
                clientes_resultado = (
                    clientes_edicion.copy()
                )
        
                if texto_busqueda.strip():
                    busqueda = texto_busqueda.strip()
        
                    columnas_busqueda = [
                        columna
                        for columna in [
                            "numero_serie",
                            "cliente",
                            "organizacion",
                            "operario",
                        ]
                        if columna in clientes_resultado.columns
                    ]
        
                    mascara_busqueda = pd.Series(
                        False,
                        index=clientes_resultado.index,
                        dtype="bool",
                    )
        
                    for columna in columnas_busqueda:
                        mascara_busqueda |= (
                            clientes_resultado[columna]
                            .fillna("")
                            .astype(str)
                            .str.contains(
                                busqueda,
                                case=False,
                                regex=False,
                                na=False,
                            )
                        )
        
                    clientes_resultado = (
                        clientes_resultado[
                            mascara_busqueda
                        ]
                        .copy()
                    )
        
                if not texto_busqueda.strip():
                    st.info(
                        "Escribí un número de serie, nombre del "
                        "cliente, organización u operario para "
                        "buscar una máquina."
                    )
        
                elif clientes_resultado.empty:
                    st.warning(
                        "No se encontraron máquinas que coincidan "
                        "con la búsqueda."
                    )
        
                else:
                    st.caption(
                        f"{len(clientes_resultado)} "
                        "coincidencia(s)"
                    )
        
                    opciones_edicion = {}
        
                    for indice, fila in (
                        clientes_resultado.iterrows()
                    ):
                        serie = valor_registro(
                            fila,
                            "numero_serie",
                        )
        
                        cliente = valor_registro(
                            fila,
                            "cliente",
                        )
        
                        organizacion = valor_registro(
                            fila,
                            "organizacion",
                        )
        
                        operario = valor_registro(
                            fila,
                            "operario",
                        )
        
                        etiqueta = " · ".join(
                            [
                                serie or "Sin serie",
                                cliente or "Sin cliente",
                                organizacion or (
                                    "Sin organización"
                                ),
                                operario or "Sin operario",
                            ]
                        )
        
                        etiqueta_unica = etiqueta
        
                        if etiqueta_unica in opciones_edicion:
                            etiqueta_unica = (
                                f"{etiqueta} · Registro {indice}"
                            )
        
                        opciones_edicion[
                            etiqueta_unica
                        ] = indice
        
                    etiqueta_seleccionada = st.selectbox(
                        "Seleccionar una máquina",
                        options=list(
                            opciones_edicion.keys()
                        ),
                        key="resultado_busqueda_edicion",
                    )
        
                    indice_registro = opciones_edicion[
                        etiqueta_seleccionada
                    ]
        
                    registro = clientes_edicion.loc[
                        indice_registro
                    ].copy()
        
                    serie_editar = valor_registro(
                        registro,
                        "numero_serie",
                    )
        
                    st.divider()
        
                    with st.form(
                        key=f"form_editar_{indice_registro}"
                    ):
                        st.markdown(
                            "#### Datos de inscripción"
                        )
        
                        columna_1, columna_2 = st.columns(2)
        
                        with columna_1:
                            numero_serie_editado = st.text_input(
                                "Número de serie",
                                value=valor_registro(
                                    registro,
                                    "numero_serie",
                                ),
                            )
        
                            organizacion_editada = st.text_input(
                                "Organización",
                                value=valor_registro(
                                    registro,
                                    "organizacion",
                                ),
                            )
        
                            org_id_editado = st.text_input(
                                "Organization ID",
                                value=valor_registro(
                                    registro,
                                    "org_id",
                                ),
                            )
        
                            sucursal_editada = st.text_input(
                                "Sucursal",
                                value=valor_registro(
                                    registro,
                                    "sucursal",
                                ),
                            )
        
                            operario_editado = st.text_input(
                                "Nombre del operario",
                                value=valor_registro(
                                    registro,
                                    "operario",
                                ),
                            )
        
                            telefono_operario_editado = (
                                st.text_input(
                                    "Teléfono del operario",
                                    value=valor_registro(
                                        registro,
                                        "telefono_operario",
                                    ),
                                )
                            )
        
                        with columna_2:
                            cliente_editado = st.text_input(
                                "Nombre del cliente",
                                value=valor_registro(
                                    registro,
                                    "cliente",
                                ),
                            )
        
                            telefono_cliente_editado = (
                                st.text_input(
                                    "Teléfono del cliente",
                                    value=valor_registro(
                                        registro,
                                        "telefono_cliente",
                                    ),
                                )
                            )
        
                            pais_editado = st.text_input(
                                "País",
                                value=valor_registro(
                                    registro,
                                    "pais",
                                ),
                            )
        
                            provincia_editada = st.text_input(
                                "Provincia",
                                value=valor_registro(
                                    registro,
                                    "provincia",
                                ),
                            )
        
                            ciudad_editada = st.text_input(
                                "Ciudad",
                                value=valor_registro(
                                    registro,
                                    "ciudad",
                                ),
                            )
        
                            categoria_actual = (
                                valor_registro(
                                    registro,
                                    "categoria",
                                )
                            )
        
                            indice_categoria = (
                                1
                                if categoria_actual == "ELITE"
                                else 0
                            )
        
                            categoria_editada = st.selectbox(
                                "Categoría",
                                options=[
                                    "BASIC",
                                    "ELITE",
                                ],
                                index=indice_categoria,
                            )
        
                        guardar_edicion = (
                            st.form_submit_button(
                                "Guardar cambios",
                                type="primary",
                                use_container_width=True,
                            )
                        )
        
                    if guardar_edicion:
                        serie_nueva = (
                            normalizar_numero_serie_valor(
                                numero_serie_editado
                            )
                        )
        
                        if not serie_nueva:
                            st.error(
                                "El número de serie es obligatorio."
                            )
        
                        else:
                            mascara_otras_filas = (
                                clientes_edicion.index
                                != indice_registro
                            )
        
                            serie_duplicada = (
                                clientes_edicion.loc[
                                    mascara_otras_filas,
                                    "numero_serie",
                                ]
                                .eq(serie_nueva)
                                .any()
                            )
        
                            if serie_duplicada:
                                st.error(
                                    "Ya existe otra máquina con "
                                    "ese número de serie."
                                )
        
                            else:
                                clientes_edicion.loc[
                                    indice_registro,
                                    "numero_serie",
                                ] = serie_nueva
        
                                clientes_edicion.loc[
                                    indice_registro,
                                    "organizacion",
                                ] = organizacion_editada.strip()
        
                                clientes_edicion.loc[
                                    indice_registro,
                                    "org_id",
                                ] = org_id_editado.strip()
        
                                clientes_edicion.loc[
                                    indice_registro,
                                    "sucursal",
                                ] = sucursal_editada.strip()
        
                                clientes_edicion.loc[
                                    indice_registro,
                                    "operario",
                                ] = operario_editado.strip()
        
                                clientes_edicion.loc[
                                    indice_registro,
                                    "telefono_operario",
                                ] = (
                                    telefono_operario_editado.strip()
                                )
        
                                clientes_edicion.loc[
                                    indice_registro,
                                    "cliente",
                                ] = cliente_editado.strip()
        
                                clientes_edicion.loc[
                                    indice_registro,
                                    "telefono_cliente",
                                ] = (
                                    telefono_cliente_editado.strip()
                                )
        
                                clientes_edicion.loc[
                                    indice_registro,
                                    "pais",
                                ] = pais_editado.strip()
        
                                clientes_edicion.loc[
                                    indice_registro,
                                    "provincia",
                                ] = provincia_editada.strip()
        
                                clientes_edicion.loc[
                                    indice_registro,
                                    "ciudad",
                                ] = ciudad_editada.strip()
        
                                clientes_edicion.loc[
                                    indice_registro,
                                    "categoria",
                                ] = categoria_editada
        
                                try:
                                    guardar_cambios_clientes(
                                        df_clientes=(
                                            clientes_edicion
                                        ),
                                        sha=clientes_sha,
                                        separador=separador_csv,
                                        mensaje=(
                                            "Actualiza participante "
                                            f"{serie_editar}"
                                        ),
                                    )
        
                                except Exception as error:
                                    st.error(
                                        "No se pudieron guardar "
                                        "los cambios."
                                    )
        
                                    with st.expander(
                                        "Detalle técnico"
                                    ):
                                        st.exception(error)

        # =============================================
        # AGREGAR MÁQUINA
        # =============================================

        with agregar_tab:
            with st.form(
                key="form_agregar_maquina",
                clear_on_submit=False,
            ):
                st.markdown(
                    "#### Nueva inscripción"
                )

                columna_1, columna_2 = st.columns(2)

                with columna_1:
                    nueva_serie = st.text_input(
                        "Número de serie *"
                    )

                    nueva_organizacion = st.text_input(
                        "Organización"
                    )

                    nuevo_org_id = st.text_input(
                        "Organization ID"
                    )

                    nueva_sucursal = st.text_input(
                        "Sucursal"
                    )

                    nuevo_operario = st.text_input(
                        "Nombre del operario"
                    )

                    nuevo_telefono_operario = st.text_input(
                        "Teléfono del operario"
                    )

                with columna_2:
                    nuevo_cliente = st.text_input(
                        "Nombre del cliente"
                    )

                    nuevo_telefono_cliente = st.text_input(
                        "Teléfono del cliente"
                    )

                    nuevo_pais = st.text_input(
                        "País"
                    )

                    nueva_provincia = st.text_input(
                        "Provincia"
                    )

                    nueva_ciudad = st.text_input(
                        "Ciudad"
                    )

                    nueva_categoria = st.selectbox(
                        "Categoría",
                        options=[
                            "BASIC",
                            "ELITE",
                        ],
                    )

                agregar_maquina = st.form_submit_button(
                    "Agregar máquina",
                    type="primary",
                    use_container_width=True,
                )

            if agregar_maquina:
                serie_normalizada = (
                    normalizar_numero_serie_valor(
                        nueva_serie
                    )
                )

                if not serie_normalizada:
                    st.error(
                        "El número de serie es obligatorio."
                    )

                elif (
                    clientes_edicion["numero_serie"]
                    .eq(serie_normalizada)
                    .any()
                ):
                    st.error(
                        "Ya existe una máquina con ese "
                        "número de serie."
                    )

                else:
                    nueva_fila = {
                        columna: ""
                        for columna in clientes_edicion.columns
                    }

                    nueva_fila.update(
                        {
                            "numero_serie": serie_normalizada,
                            "organizacion": (
                                nueva_organizacion.strip()
                            ),
                            "org_id": nuevo_org_id.strip(),
                            "sucursal": nueva_sucursal.strip(),
                            "operario": nuevo_operario.strip(),
                            "telefono_operario": (
                                nuevo_telefono_operario.strip()
                            ),
                            "cliente": nuevo_cliente.strip(),
                            "telefono_cliente": (
                                nuevo_telefono_cliente.strip()
                            ),
                            "pais": nuevo_pais.strip(),
                            "provincia": (
                                nueva_provincia.strip()
                            ),
                            "ciudad": nueva_ciudad.strip(),
                            "categoria": nueva_categoria,
                        }
                    )

                    clientes_actualizados = pd.concat(
                        [
                            clientes_edicion,
                            pd.DataFrame(
                                [nueva_fila]
                            ),
                        ],
                        ignore_index=True,
                    )

                    try:
                        guardar_cambios_clientes(
                            df_clientes=clientes_actualizados,
                            sha=clientes_sha,
                            separador=separador_csv,
                            mensaje=(
                                "Agrega participante "
                                f"{serie_normalizada}"
                            ),
                        )

                    except Exception as error:
                        st.error(
                            "No se pudo agregar la máquina."
                        )

                        with st.expander(
                            "Detalle técnico"
                        ):
                            st.exception(error)

        # =============================================
        # ELIMINAR MÁQUINA
        # =============================================

        with eliminar_tab:
            if clientes_edicion.empty:
                st.info(
                    "No hay máquinas disponibles "
                    "para eliminar."
                )

            else:
                opciones_eliminar = sorted(
                    clientes_edicion[
                        "numero_serie"
                    ]
                    .dropna()
                    .loc[
                        lambda serie:
                        serie.astype(str).str.strip().ne("")
                    ]
                    .astype(str)
                    .unique()
                    .tolist()
                )

                serie_eliminar = st.selectbox(
                    "Número de serie a eliminar",
                    options=opciones_eliminar,
                    key="serie_eliminar",
                )

                registro_eliminar = (
                    clientes_edicion[
                        clientes_edicion["numero_serie"]
                        == serie_eliminar
                    ]
                    .iloc[0]
                )

                st.warning(
                    "Esta operación eliminará la inscripción "
                    "del CSV de participantes."
                )

                st.write(
                    {
                        "Número de serie": serie_eliminar,
                        "Operario": valor_registro(
                            registro_eliminar,
                            "operario",
                        ),
                        "Cliente": valor_registro(
                            registro_eliminar,
                            "cliente",
                        ),
                        "Sucursal": valor_registro(
                            registro_eliminar,
                            "sucursal",
                        ),
                        "Categoría": valor_registro(
                            registro_eliminar,
                            "categoria",
                        ),
                    }
                )

                confirmar_eliminacion = st.checkbox(
                    "Confirmo que deseo eliminar esta máquina",
                    key=(
                        f"confirmar_eliminar_"
                        f"{serie_eliminar}"
                    ),
                )

                eliminar_maquina = st.button(
                    "Eliminar máquina",
                    type="primary",
                    disabled=not confirmar_eliminacion,
                    use_container_width=True,
                )

                if eliminar_maquina:
                    clientes_actualizados = (
                        clientes_edicion[
                            clientes_edicion[
                                "numero_serie"
                            ]
                            != serie_eliminar
                        ]
                        .copy()
                        .reset_index(drop=True)
                    )

                    try:
                        guardar_cambios_clientes(
                            df_clientes=clientes_actualizados,
                            sha=clientes_sha,
                            separador=separador_csv,
                            mensaje=(
                                "Elimina participante "
                                f"{serie_eliminar}"
                            ),
                        )

                    except Exception as error:
                        st.error(
                            "No se pudo eliminar la máquina."
                        )

                        with st.expander(
                            "Detalle técnico"
                        ):
                            st.exception(error)
