  
import io  
import textwrap  
import matplotlib.pyplot as plt  
import pandas as pd  
import streamlit as st  
from matplotlib.backends.backend\_pdf import PdfPages  
from utils.metrics import calcular\_scores  
from utils.data\_loader import (  
    COLUMN\_MAPPING\_CLIENTES,  
    cargar\_datos,  
    normalizar\_encabezados,  
)  
from utils.github\_clientes import (  
    cargar\_clientes\_github,  
    guardar\_clientes\_github,  
    normalizar\_numero\_serie\_valor,  
)  
\# =====================================================  
\# CONFIGURACIÓN  
\# =====================================================  
st.set\_page\_config(  
    page\_title="Crack del Campo \| Tractores",  
    page\_icon="🚜",  
    layout="wide",  
)  
st.title("Crack del Campo \| Tractores")  
st.caption("Seguimiento de participantes")  
\# =====================================================  
\# FUNCIONES  
\# =====================================================  
\# Cambiar esta versión obliga a Streamlit a reconstruir  
\# el dataframe cuando se modifica la lógica del tablero.  
CACHE\_VERSION = "ranking\_periodo\_v6\_basic\_igual\_autotrac"  
@st.cache\_data(ttl=3600)  
def load\_data(cache\_version):  
    """  
    Carga las fuentes, normaliza las categorías y calcula  
    los scores semanales.  
    """  
    \# El parámetro se utiliza para invalidar la caché.  
    \_ = cache\_version  
    datos = cargar\_datos()  
    validar\_columnas\_carga = \[  
        "categoria",  
    \]  
    faltantes = \[  
        columna  
        for columna in validar\_columnas\_carga  
        if columna not in datos.columns  
    \]  
    if faltantes:  
        raise ValueError(  
            "No se puede normalizar la categoría. "  
            "Faltan las columnas: "  
            \+ ", ".join(faltantes)  
        )  
    \# La categoría debe normalizarse antes de calcular  
    \# la necesidad de intervención.  
    datos\["categoria"\] = (  
        datos\["categoria"\]  
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
    datos = calcular\_scores\_ajustados(datos)  
    return datos  
def promedio\_seguro(df, columna):  
    """  
    Calcula el promedio numérico de una columna.  
    Devuelve 0 cuando el dataframe está vacío, la columna  
    no existe o no contiene valores numéricos.  
    """  
    if df.empty or columna not in df.columns:  
        return 0.0  
    valores = pd.to\_numeric(  
        df\[columna\],  
        errors="coerce",  
    )  
    resultado = valores.mean()  
    if pd.isna(resultado):  
        return 0.0  
    return float(resultado)  
def porcentaje\_tecnologia(df, columna):  
    """  
    Calcula el promedio de uso de una tecnología.  
    Reglas:  
    \- Los valores nulos representan semanas sin actividad  
      y no participan del promedio.  
    \- Un cero informado representa actividad sin uso de  
      la tecnología y sí participa del promedio.  
    \- Devuelve None cuando no existe ningún dato válido.  
    """  
    if df.empty or columna not in df.columns:  
        return None  
    valores = pd.to\_numeric(  
        df\[columna\],  
        errors="coerce",  
    ).dropna()  
    if valores.empty:  
        return None  
    return float(  
        valores.clip(lower=0, upper=100).mean()  
    )  
def formatear\_porcentaje\_tecnologia(valor):  
    """  
    Presenta un indicador tecnológico sin confundir una  
    semana sin actividad con un uso real de cero por ciento.  
    """  
    if valor is None or pd.isna(valor):  
        return "Sin actividad"  
    return f"{valor:.1f}%"  
def formatear\_score\_tecnologia(df, columna):  
    """  
    Formatea un score calculado con componentes tecnológicos.  
    Evita mostrar 0 cuando todo el período está sin actividad.  
    """  
    valor = porcentaje\_tecnologia(df, columna)  
    if valor is None:  
        return "Sin actividad"  
    return f"{valor:.1f}"  
METRICAS\_TECNOLOGIA\_ELITE = \[  
    "autotrac",  
    "turn\_automation",  
    "autopath",  
    "implement\_guidance",  
    "efficiency\_manager",  
    "field\_cruise",  
\]  
def ajustar\_scores\_tecnologia(df):  
    """  
    Ajusta los scores sin convertir tecnologías nulas en cero.  
    Reglas:  
    \- BASIC: score\_basic es exactamente igual a AutoTrac.  
    \- ELITE: score\_elite es el promedio de los componentes  
      tecnológicos realmente informados.  
    \- El control del ocio participa como 100 - ocio\_controlable  
      solamente cuando ocio\_controlable está informado.  
    \- Un cero real sí participa del score.  
    \- Si no existe ningún componente válido, el score queda nulo.  
    """  
    if df.empty:  
        return df.copy()  
    resultado = df.copy()  
    if "categoria" not in resultado.columns:  
        return resultado  
    categorias = (  
        resultado\["categoria"\]  
        .fillna("")  
        .astype(str)  
        .str.strip()  
        .str.upper()  
    )  
    mascara\_basic = categorias.eq("BASIC")  
    mascara\_elite = categorias.eq("ELITE")  
    \# BASIC: el score debe coincidir exactamente con AutoTrac.  
    if "autotrac" in resultado.columns:  
        autotrac = pd.to\_numeric(  
            resultado\["autotrac"\],  
            errors="coerce",  
        ).clip(lower=0, upper=100)  
        resultado.loc\[  
            mascara\_basic,  
            "score\_basic",  
        \] = autotrac.loc\[mascara\_basic\]  
    \# ELITE: cada componente nulo se excluye del denominador.  
    componentes\_elite = pd.DataFrame(  
        index=resultado.index,  
    )  
    for columna in METRICAS\_TECNOLOGIA\_ELITE:  
        if columna in resultado.columns:  
            componentes\_elite\[columna\] = pd.to\_numeric(  
                resultado\[columna\],  
                errors="coerce",  
            ).clip(lower=0, upper=100)  
    if "ocio\_controlable" in resultado.columns:  
        ocio\_controlable = pd.to\_numeric(  
            resultado\["ocio\_controlable"\],  
            errors="coerce",  
        ).clip(lower=0, upper=100)  
        componentes\_elite\["control\_ocio"\] = (  
            100 - ocio\_controlable  
        )  
    if not componentes\_elite.empty:  
        score\_elite = componentes\_elite.mean(  
            axis=1,  
            skipna=True,  
        )  
        \# DataFrame.mean devuelve NaN cuando todos los componentes  
        \# de una fila son nulos, que es el comportamiento buscado.  
        resultado.loc\[  
            mascara\_elite,  
            "score\_elite",  
        \] = score\_elite.loc\[mascara\_elite\]  
    return resultado  
def calcular\_scores\_ajustados(df):  
    """  
    Ejecuta la lógica general de scores y luego aplica las reglas  
    tecnológicas del tablero sin perder los valores nulos originales.  
    Se restauran las métricas desde el dataframe de entrada por si  
    calcular\_scores convierte internamente algún nulo en cero.  
    """  
    if df.empty:  
        return df.copy()  
    datos\_originales = df.copy()  
    resultado = calcular\_scores(  
        df.copy()  
    )  
    columnas\_a\_preservar = (  
        METRICAS\_TECNOLOGIA\_ELITE  
        \+ \["ocio\_controlable"\]  
    )  
    for columna in columnas\_a\_preservar:  
        if columna in datos\_originales.columns:  
            resultado\[columna\] = pd.to\_numeric(  
                datos\_originales\[columna\],  
                errors="coerce",  
            ).clip(lower=0, upper=100)  
    return ajustar\_scores\_tecnologia(  
        resultado  
    )  
def valor\_informado(serie):  
    """  
    Devuelve una máscara booleana que identifica valores  
    realmente informados.  
    Considera vacíos:  
    \- NaN;  
    \- texto vacío;  
    \- 'nan';  
    \- 'none';  
    \- 'sin asignar';  
    \- 'sin datos';  
    \- 'sin dato'.  
    """  
    texto = (  
        serie  
        .fillna("")  
        .astype(str)  
        .str.strip()  
        .str.lower()  
    )  
    valores\_vacios = \[  
        "",  
        "nan",  
        "none",  
        "null",  
        "sin asignar",  
        "sin datos",  
        "sin dato",  
        "no informado",  
    \]  
    return ~texto.isin(  
        valores\_vacios  
    )  
def calcular\_completitud\_clientes(df):  
    """  
    Calcula indicadores de completitud para el listado  
    de participantes.  
    Un registro se considera completo cuando contiene:  
    \- organización;  
    \- Organization ID;  
    \- sucursal;  
    \- número de serie;  
    \- nombre del operario;  
    \- categoría;  
    \- teléfono del operario.  
    """  
    campos\_requeridos = \[  
        "organizacion",  
        "org\_id",  
        "sucursal",  
        "numero\_serie",  
        "operario",  
        "categoria",  
        "telefono\_operario",  
    \]  
    total = len(df)  
    if total == 0:  
        return {  
            "total": 0,  
            "registros\_completos": 0,  
            "porcentaje\_completo": 0.0,  
            "telefonos\_cargados": 0,  
            "porcentaje\_telefonos": 0.0,  
        }  
    mascara\_completa = pd.Series(  
        True,  
        index=df.index,  
        dtype="bool",  
    )  
    for columna in campos\_requeridos:  
        if columna not in df.columns:  
            mascara\_completa &= False  
        else:  
            mascara\_completa &= valor\_informado(  
                df\[columna\]  
            )  
    registros\_completos = int(  
        mascara\_completa.sum()  
    )  
    if "telefono\_operario" in df.columns:  
        telefonos\_cargados = int(  
            valor\_informado(  
                df\["telefono\_operario"\]  
            ).sum()  
        )  
    else:  
        telefonos\_cargados = 0  
    porcentaje\_completo = (  
        registros\_completos  
        / total  
        \* 100  
    )  
    porcentaje\_telefonos = (  
        telefonos\_cargados  
        / total  
        \* 100  
    )  
    return {  
        "total": total,  
        "registros\_completos": registros\_completos,  
        "porcentaje\_completo": porcentaje\_completo,  
        "telefonos\_cargados": telefonos\_cargados,  
        "porcentaje\_telefonos": porcentaje\_telefonos,  
    }  
def mostrar\_resumen\_completitud(df):  
    """  
    Muestra los KPI de completitud del listado.  
    """  
    indicadores = calcular\_completitud\_clientes(  
        df  
    )  
    c1, c2, c3, c4 = st.columns(4)  
    c1.metric(  
        "Máquinas",  
        indicadores\["total"\],  
    )  
    c2.metric(  
        "Registros completos",  
        (  
            f"{indicadores\['registros\_completos'\]} "  
            f"de {indicadores\['total'\]}"  
        ),  
    )  
    c3.metric(  
        "Información completa",  
        (  
            f"{indicadores\['porcentaje\_completo'\]:.1f}%"  
        ),  
    )  
    c4.metric(  
        "Celular de operario",  
        (  
            f"{indicadores\['telefonos\_cargados'\]} "  
            f"de {indicadores\['total'\]} "  
            f"({indicadores\['porcentaje\_telefonos'\]:.1f}%)"  
        ),  
    )  
def construir\_evolucion\_semanal(  
    df,  
    metricas,  
    nombres\_metricas=None,  
):  
    """  
    Construye la evolución semanal promedio de una categoría.  
    Reglas:  
    \- Devuelve una fila por semana.  
    \- Utiliza fecha\_fin como fecha representativa.  
    \- Las métricas ausentes se excluyen del promedio.  
    \- Calcula el promedio de las máquinas incluidas en  
      la población seleccionada.  
    """  
    if df.empty:  
        return pd.DataFrame()  
    if "fecha\_fin" not in df.columns:  
        return pd.DataFrame()  
    resultado = df.copy()  
    resultado\["fecha\_fin"\] = pd.to\_datetime(  
        resultado\["fecha\_fin"\],  
        errors="coerce",  
        dayfirst=True,  
    ).dt.normalize()  
    resultado = resultado\[  
        resultado\["fecha\_fin"\].notna()  
    \].copy()  
    if resultado.empty:  
        return pd.DataFrame()  
    metricas\_disponibles = \[  
        metrica  
        for metrica in metricas  
        if metrica in resultado.columns  
    \]  
    if not metricas\_disponibles:  
        return pd.DataFrame()  
    \# Una tecnología sin dato indica que no hubo actividad  
    \# durante esa semana. Se mantiene como NaN para que no  
    \# participe del promedio.  
    for metrica in metricas\_disponibles:  
        resultado\[metrica\] = (  
            pd.to\_numeric(  
                resultado\[metrica\],  
                errors="coerce",  
            )  
            .clip(lower=0, upper=100)  
        )  
    evolucion = (  
        resultado  
        .groupby(  
            "fecha\_fin",  
            as\_index=False,  
            dropna=False,  
        )\[metricas\_disponibles\]  
        .mean()  
        .sort\_values(  
            "fecha\_fin",  
            ascending=True,  
        )  
    )  
    if nombres\_metricas:  
        evolucion = evolucion.rename(  
            columns=nombres\_metricas  
        )  
    evolucion = evolucion.set\_index(  
        "fecha\_fin"  
    )  
    evolucion.index.name = "Semana"  
    return evolucion  
def consolidar\_periodo(df):  
    """  
    Consolida todas las semanas seleccionadas en una fila  
    por número de serie.  
    Reglas:  
    \- Las tecnologías se promedian durante el período.  
    \- Un valor tecnológico ausente se excluye del promedio.  
    \- Las dimensiones descriptivas conservan el dato de  
      la fila más reciente.  
    \- Los scores se recalculan con las métricas promedio.  
    \- La intervención se clasifica según el score promedio  
      del período seleccionado.  
    """  
    if df.empty:  
        return df.copy()  
    resultado = df.copy()  
    \# =================================================  
    \# FECHAS  
    \# =================================================  
    for columna\_fecha in \[  
        "fecha\_inicio",  
        "fecha\_fin",  
    \]:  
        if columna\_fecha in resultado.columns:  
            resultado\[columna\_fecha\] = pd.to\_datetime(  
                resultado\[columna\_fecha\],  
                errors="coerce",  
                dayfirst=True,  
            ).dt.normalize()  
    \# La fila más reciente queda primero. De esta forma,  
    \# "first" conserva los datos descriptivos más actuales.  
    if "fecha\_fin" in resultado.columns:  
        resultado = resultado.sort\_values(  
            "fecha\_fin",  
            ascending=False,  
            na\_position="last",  
        )  
    \# =================================================  
    \# MÉTRICAS DEL PERÍODO  
    \# =================================================  
    metricas\_promedio = \[  
        "autotrac",  
        "turn\_automation",  
        "autopath",  
        "implement\_guidance",  
        "efficiency\_manager",  
        "field\_cruise",  
        "cancelada",  
        "sin\_definir",  
        "ignorada",  
        "ocio\_controlable",  
        "score\_ociosidad",  
    \]  
    metricas\_disponibles = \[  
        columna  
        for columna in metricas\_promedio  
        if columna in resultado.columns  
    \]  
    \# Un valor ausente indica una semana sin actividad.  
    \# Se mantiene como NaN para excluirlo del promedio  
    \# del período.  
    for columna in metricas\_disponibles:  
        resultado\[columna\] = (  
            pd.to\_numeric(  
                resultado\[columna\],  
                errors="coerce",  
            )  
            .clip(lower=0, upper=100)  
        )  
    \# =================================================  
    \# DIMENSIONES DESCRIPTIVAS  
    \# =================================================  
    dimensiones = \[  
        "operario",  
        "cliente",  
        "sucursal",  
        "organizacion",  
        "org\_id",  
        "categoria",  
        "maquina",  
        "modelo",  
        "tipo",  
        "telefono",  
        "telefono\_operario",  
        "telefono\_cliente",  
        "pais",  
        "provincia",  
        "ciudad",  
    \]  
    dimensiones\_disponibles = \[  
        columna  
        for columna in dimensiones  
        if columna in resultado.columns  
    \]  
    agregaciones = {  
        columna: "mean"  
        for columna in metricas\_disponibles  
    }  
    agregaciones.update(  
        {  
            columna: "first"  
            for columna in dimensiones\_disponibles  
        }  
    )  
    \# Las fechas del consolidado muestran el rango real  
    \# cubierto por cada máquina.  
    if "fecha\_inicio" in resultado.columns:  
        agregaciones\["fecha\_inicio"\] = "min"  
    if "fecha\_fin" in resultado.columns:  
        agregaciones\["fecha\_fin"\] = "max"  
    consolidado = (  
        resultado  
        .groupby(  
            "numero\_serie",  
            as\_index=False,  
            dropna=False,  
        )  
        .agg(agregaciones)  
    )  
    \# Recalcula los scores y la intervención utilizando  
    \# los promedios del período.  
    consolidado = calcular\_scores\_ajustados(  
        consolidado  
    )  
    return consolidado  
def filtrar\_historico\_por\_poblacion(  
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
        return historico.iloc\[0:0\].copy()  
    if (  
        "numero\_serie" not in historico.columns  
        or "numero\_serie" not in consolidado.columns  
    ):  
        return historico.iloc\[0:0\].copy()  
    series\_seleccionadas = (  
        consolidado\["numero\_serie"\]  
        .dropna()  
        .unique()  
        .tolist()  
    )  
    return historico\[  
        historico\["numero\_serie"\].isin(  
            series\_seleccionadas  
        )  
    \].copy()  
def mostrar\_tabla\_vacia(mensaje):  
    st.info(mensaje)  
\# =====================================================  
\# GENERACIÓN DE INFORMES  
\# =====================================================  
METRICAS\_ELITE\_INFORME = {  
    "autotrac": "AutoTrac",  
    "turn\_automation": "Turn Automation",  
    "autopath": "AutoPath",  
    "implement\_guidance": "Implement Guidance",  
    "efficiency\_manager": "Efficiency Manager",  
    "field\_cruise": "Field Cruise",  
}  
def texto\_seguro(valor, predeterminado="Sin informar"):  
    """Convierte un valor en texto apto para pantalla e informe."""  
    if pd.isna(valor):  
        return predeterminado  
    texto = str(valor).strip()  
    return texto if texto else predeterminado  
def filtrar\_periodo\_informe(df\_original, periodo):  
    """  
    Aplica solamente el período elegido.  
    No aplica sucursal, organización ni intervención porque el informe  
    necesita calcular las posiciones contra toda la población.  
    """  
    resultado = df\_original.copy()  
    if (  
        periodo  
        and isinstance(periodo, (tuple, list))  
        and len(periodo) == 2  
    ):  
        desde = pd.Timestamp(periodo\[0\]).normalize()  
        hasta = pd.Timestamp(periodo\[1\]).normalize()  
        resultado = resultado\[  
            (resultado\["fecha\_inicio"\] \<= hasta)  
            & (resultado\["fecha\_fin"\] \>= desde)  
        \].copy()  
    return resultado  
def valor\_numerico(registro, columna, predeterminado=0.0):  
    """Lee de forma segura una métrica numérica del participante."""  
    if columna not in registro.index:  
        return float(predeterminado)  
    valor = pd.to\_numeric(  
        pd.Series(\[registro\[columna\]\]),  
        errors="coerce",  
    ).iloc\[0\]  
    if pd.isna(valor):  
        return float(predeterminado)  
    return float(valor)  
def valor\_tecnologia\_registro(registro, columna):  
    """  
    Lee una tecnología sin convertir la falta de actividad  
    en un cero artificial.  
    """  
    if columna not in registro.index:  
        return None  
    valor = pd.to\_numeric(  
        pd.Series(\[registro\[columna\]\]),  
        errors="coerce",  
    ).iloc\[0\]  
    if pd.isna(valor):  
        return None  
    return float(min(max(valor, 0), 100))  
def calcular\_posiciones\_informe(  
    poblacion,  
    numero\_serie,  
    columna\_score,  
    sucursal,  
):  
    """Calcula posición nacional Conci y posición en la sucursal."""  
    if poblacion.empty or columna\_score not in poblacion.columns:  
        return {  
            "general": None,  
            "total\_general": 0,  
            "sucursal": None,  
            "total\_sucursal": 0,  
        }  
    ranking\_general = poblacion.copy()  
    ranking\_general\[columna\_score\] = pd.to\_numeric(  
        ranking\_general\[columna\_score\],  
        errors="coerce",  
    ).fillna(0.0)  
    ranking\_general\["posicion\_informe"\] = (  
        ranking\_general\[columna\_score\]  
        .rank(method="min", ascending=False)  
        .astype(int)  
    )  
    coincidencia\_general = ranking\_general\[  
        ranking\_general\["numero\_serie"\] == numero\_serie  
    \]  
    posicion\_general = (  
        int(coincidencia\_general\["posicion\_informe"\].iloc\[0\])  
        if not coincidencia\_general.empty  
        else None  
    )  
    ranking\_sucursal = ranking\_general\[  
        ranking\_general\["sucursal"\] == sucursal  
    \].copy()  
    ranking\_sucursal\["posicion\_informe"\] = (  
        ranking\_sucursal\[columna\_score\]  
        .rank(method="min", ascending=False)  
        .astype(int)  
    )  
    coincidencia\_sucursal = ranking\_sucursal\[  
        ranking\_sucursal\["numero\_serie"\] == numero\_serie  
    \]  
    posicion\_sucursal = (  
        int(coincidencia\_sucursal\["posicion\_informe"\].iloc\[0\])  
        if not coincidencia\_sucursal.empty  
        else None  
    )  
    return {  
        "general": posicion\_general,  
        "total\_general": len(ranking\_general),  
        "sucursal": posicion\_sucursal,  
        "total\_sucursal": len(ranking\_sucursal),  
    }  
def construir\_evolucion\_participante(  
    historico,  
    numero\_serie,  
    categoria,  
):  
    """Devuelve la evolución semanal de una máquina."""  
    participante = historico\[  
        historico\["numero\_serie"\] == numero\_serie  
    \].copy()  
    if categoria == "BASIC":  
        return construir\_evolucion\_semanal(  
            participante,  
            metricas=\["autotrac", "score\_basic"\],  
            nombres\_metricas={  
                "autotrac": "AutoTrac",  
                "score\_basic": "Score Basic",  
            },  
        )  
    return construir\_evolucion\_semanal(  
        participante,  
        metricas=\[  
            "score\_elite",  
            \*METRICAS\_ELITE\_INFORME.keys(),  
            "ocio\_controlable",  
        \],  
        nombres\_metricas={  
            "score\_elite": "Score Elite",  
            \*\*{  
                columna: nombre  
                for columna, nombre  
                in METRICAS\_ELITE\_INFORME.items()  
            },  
            "ocio\_controlable": "Ocio controlable",  
        },  
    )  
def recomendaciones\_basic(registro, evolucion):  
    """Genera recomendaciones Basic a partir del desempeño observado."""  
    recomendaciones = \[\]  
    autotrac = valor\_tecnologia\_registro(  
        registro,  
        "autotrac",  
    )  
    valores\_autotrac = pd.Series(dtype="float64")  
    if "AutoTrac" in evolucion.columns:  
        valores\_autotrac = pd.to\_numeric(  
            evolucion\["AutoTrac"\],  
            errors="coerce",  
        ).dropna()  
    if len(valores\_autotrac) \>= 2:  
        valor\_actual = float(valores\_autotrac.iloc\[-1\])  
        valor\_anterior = float(valores\_autotrac.iloc\[-2\])  
        if valor\_actual \< valor\_anterior:  
            recomendaciones.append(  
                "Revisar la disminución semanal de AutoTrac y acordar "  
                "una acción concreta para recuperar su utilización."  
            )  
        elif valor\_actual \> valor\_anterior:  
            recomendaciones.append(  
                "Sostener las prácticas de la última semana que "  
                "permitieron mejorar la utilización de AutoTrac."  
            )  
        else:  
            recomendaciones.append(  
                "Definir un objetivo de mejora semanal para salir del "  
                "nivel estable de utilización de AutoTrac."  
            )  
    elif autotrac is None:  
        recomendaciones.append(  
            "No hubo actividad válida de AutoTrac en el período "  
            "seleccionado; esperar una semana con uso del tractor "  
            "antes de evaluar su desempeño."  
        )  
    else:  
        recomendaciones.append(  
            "Continuar incorporando semanas para medir la tendencia "  
            "y fijar un objetivo de mejora de AutoTrac."  
        )  
    if autotrac is None:  
        return recomendaciones  
    if autotrac \< 100:  
        recomendaciones.append(  
            "Identificar las labores aptas en las que todavía no se usa "  
            "AutoTrac y priorizar su adopción durante el próximo período."  
        )  
    else:  
        recomendaciones.append(  
            "Mantener la utilización completa de AutoTrac y verificar "  
            "su continuidad en las próximas semanas."  
        )  
    return recomendaciones  
def recomendaciones\_elite(registro):  
    """Prioriza los componentes Elite con menor resultado."""  
    valores = \[\]  
    for columna, nombre in METRICAS\_ELITE\_INFORME.items():  
        valor = valor\_tecnologia\_registro(  
            registro,  
            columna,  
        )  
        if valor is None:  
            continue  
        valores.append(  
            (  
                valor,  
                nombre,  
                (  
                    f"Priorizar {nombre}: revisar su utilización con "  
                    "el operario y definir una meta para el próximo período."  
                ),  
            )  
        )  
    ocio = valor\_numerico(registro, "ocio\_controlable")  
    valores.append(  
        (  
            100.0 - ocio,  
            "Control del ocio",  
            "Revisar las causas del ocio controlable y acordar acciones "  
            "para reducirlo durante el próximo período.",  
        )  
    )  
    valores.sort(key=lambda item: item\[0\])  
    if not valores:  
        return \[  
            "No hubo actividad tecnológica válida en el período "  
            "seleccionado; esperar nuevos datos antes de definir "  
            "prioridades de adopción."  
        \]  
    return \[item\[2\] for item in valores\[:3\]\]  
def crear\_radar\_elite(registro):  
    """Crea el radar Elite; en ocio, un valor mayor significa mejor control."""  
    etiquetas = list(METRICAS\_ELITE\_INFORME.values())  
    valores = \[  
        (  
            valor\_tecnologia\_registro(registro, columna)  
            if valor\_tecnologia\_registro(registro, columna) is not None  
            else float("nan")  
        )  
        for columna in METRICAS\_ELITE\_INFORME  
    \]  
    etiquetas.append("Control del ocio")  
    valores.append(  
        100.0 - valor\_numerico(  
            registro,  
            "ocio\_controlable",  
        )  
    )  
    cantidad = len(etiquetas)  
    angulos = \[  
        indice / float(cantidad) \* 2 \* 3.141592653589793  
        for indice in range(cantidad)  
    \]  
    angulos += angulos\[:1\]  
    valores\_cerrados = valores + valores\[:1\]  
    figura, eje = plt.subplots(  
        figsize=(8, 6),  
        subplot\_kw={"polar": True},  
    )  
    eje.plot(  
        angulos,  
        valores\_cerrados,  
        color="#2E7D32",  
        linewidth=2,  
    )  
    eje.fill(  
        angulos,  
        valores\_cerrados,  
        color="#66BB6A",  
        alpha=0.35,  
    )  
    eje.set\_xticks(angulos\[:-1\])  
    eje.set\_xticklabels(etiquetas, fontsize=9)  
    eje.set\_ylim(0, 100)  
    eje.set\_yticks(\[20, 40, 60, 80, 100\])  
    eje.set\_yticklabels(  
        \["20", "40", "60", "80", "100"\],  
        fontsize=8,  
    )  
    eje.set\_title(  
        "Desempeño por componente Elite",  
        pad=24,  
        fontsize=14,  
        fontweight="bold",  
    )  
    figura.tight\_layout()  
    return figura  
def crear\_figura\_evolucion(evolucion, categoria):  
    """Crea una figura reutilizable para pantalla y PDF."""  
    if evolucion.empty:  
        return None  
    figura, eje = plt.subplots(figsize=(9, 4.8))  
    for columna in evolucion.columns:  
        eje.plot(  
            evolucion.index,  
            evolucion\[columna\],  
            marker="o",  
            linewidth=2,  
            label=columna,  
        )  
    eje.set\_title(f"Evolución semanal {categoria.title()}")  
    eje.set\_xlabel("Semana")  
    eje.set\_ylabel("Resultado")  
    eje.set\_ylim(0, 100)  
    eje.grid(alpha=0.25)  
    eje.legend(loc="best")  
    figura.autofmt\_xdate()  
    figura.tight\_layout()  
    return figura  
def agregar\_texto\_pdf(figura, x, y, texto, ancho=92, \*\*kwargs):  
    """Agrega texto envuelto a una figura y devuelve la próxima altura."""  
    lineas = textwrap.wrap(str(texto), width=ancho) or \[""\]  
    figura.text(x, y, "\\\\n".join(lineas), \*\*kwargs)  
    return y - (0.027 \* len(lineas))  
def generar\_pdf\_informe(  
    registro,  
    categoria,  
    posiciones,  
    evolucion,  
    recomendaciones,  
    figura\_radar=None,  
    figura\_evolucion=None,  
):  
    """Genera el PDF descargable en memoria."""  
    buffer = io.BytesIO()  
    columna\_score = (  
        "score\_basic"  
        if categoria == "BASIC"  
        else "score\_elite"  
    )  
    score = valor\_numerico(registro, columna\_score)  
    with PdfPages(buffer) as pdf:  
        portada = plt.figure(figsize=(8.27, 11.69))  
        portada.patch.set\_facecolor("white")  
        y = 0.94  
        y = agregar\_texto\_pdf(  
            portada,  
            0.08,  
            y,  
            "Crack del Campo \| Informe de participante",  
            fontsize=18,  
            fontweight="bold",  
            color="#1B5E20",  
        )  
        y -= 0.02  
        datos = \[  
            ("Categoría", categoria.title()),  
            ("Organización", texto\_seguro(registro.get("organizacion"))),  
            ("Cliente", texto\_seguro(registro.get("cliente"))),  
            ("Operario", texto\_seguro(registro.get("operario"))),  
            ("Sucursal", texto\_seguro(registro.get("sucursal"))),  
            ("N.º de serie", texto\_seguro(registro.get("numero\_serie"))),  
            ("Período", (  
                f"{registro.get('fecha\_inicio'):%d/%m/%Y} al "  
                f"{registro.get('fecha\_fin'):%d/%m/%Y}"  
                if (  
                    pd.notna(registro.get("fecha\_inicio"))  
                    and pd.notna(registro.get("fecha\_fin"))  
                )  
                else "Sin informar"  
            )),  
        \]  
        for etiqueta, valor in datos:  
            portada.text(  
                0.08,  
                y,  
                f"{etiqueta}:",  
                fontsize=10,  
                fontweight="bold",  
            )  
            portada.text(0.27, y, str(valor), fontsize=10)  
            y -= 0.033  
        y -= 0.015  
        portada.text(  
            0.08,  
            y,  
            f"Score {categoria.title()}: {score:.1f}",  
            fontsize=15,  
            fontweight="bold",  
            color="#2E7D32",  
        )  
        y -= 0.05  
        posicion\_general = (  
            f"{posiciones\['general'\]} de "  
            f"{posiciones\['total\_general'\]}"  
            if posiciones\["general"\] is not None  
            else "Sin posición"  
        )  
        posicion\_sucursal = (  
            f"{posiciones\['sucursal'\]} de "  
            f"{posiciones\['total\_sucursal'\]}"  
            if posiciones\["sucursal"\] is not None  
            else "Sin posición"  
        )  
        portada.text(  
            0.08,  
            y,  
            f"Posición en Conci: {posicion\_general}",  
            fontsize=11,  
        )  
        y -= 0.035  
        portada.text(  
            0.08,  
            y,  
            f"Posición en la sucursal: {posicion\_sucursal}",  
            fontsize=11,  
        )  
        y -= 0.055  
        portada.text(  
            0.08,  
            y,  
            "Indicadores del período",  
            fontsize=13,  
            fontweight="bold",  
        )  
        y -= 0.04  
        if categoria == "BASIC":  
            indicadores = \[  
                (  
                    "AutoTrac",  
                    formatear\_porcentaje\_tecnologia(  
                        valor\_tecnologia\_registro(  
                            registro,  
                            "autotrac",  
                        )  
                    ),  
                ),  
                ("Score Basic", f"{score:.1f}"),  
            \]  
        else:  
            indicadores = \[  
                (  
                    nombre,  
                    formatear\_porcentaje\_tecnologia(  
                        valor\_tecnologia\_registro(  
                            registro,  
                            columna,  
                        )  
                    ),  
                )  
                for columna, nombre  
                in METRICAS\_ELITE\_INFORME.items()  
            \]  
            indicadores.append(  
                (  
                    "Ocio controlable",  
                    f"{valor\_numerico(registro, 'ocio\_controlable'):.1f}%",  
                )  
            )  
            indicadores.append(  
                ("Score Elite", f"{score:.1f}")  
            )  
        for nombre, valor in indicadores:  
            portada.text(  
                0.10,  
                y,  
                f"• {nombre}: {valor}",  
                fontsize=10,  
            )  
            y -= 0.028  
        y -= 0.02  
        portada.text(  
            0.08,  
            y,  
            "Recomendaciones",  
            fontsize=13,  
            fontweight="bold",  
        )  
        y -= 0.04  
        for numero, recomendacion in enumerate(  
            recomendaciones,  
            start=1,  
        ):  
            y = agregar\_texto\_pdf(  
                portada,  
                0.10,  
                y,  
                f"{numero}. {recomendacion}",  
                ancho=86,  
                fontsize=10,  
            )  
            y -= 0.018  
        portada.text(  
            0.08,  
            0.04,  
            "Informe generado desde el tablero Crack del Campo.",  
            fontsize=8,  
            color="#666666",  
        )  
        pdf.savefig(portada, bbox\_inches="tight")  
        plt.close(portada)  
        if figura\_evolucion is not None:  
            pdf.savefig(figura\_evolucion, bbox\_inches="tight")  
        if figura\_radar is not None:  
            pdf.savefig(figura\_radar, bbox\_inches="tight")  
    buffer.seek(0)  
    return buffer.getvalue()  
\# =====================================================  
\# EDICIÓN DE PARTICIPANTES  
\# =====================================================  
COLUMNAS\_CLIENTES\_EDITABLES = \[  
    "numero\_serie",  
    "organizacion",  
    "org\_id",  
    "sucursal",  
    "operario",  
    "cliente",  
    "telefono\_operario",  
    "telefono\_cliente",  
    "pais",  
    "provincia",  
    "ciudad",  
    "categoria",  
\]  
def preparar\_clientes\_edicion(df\_original):  
    """  
    Normaliza la estructura del CSV para que pueda ser  
    utilizada por los formularios de edición.  
    Las columnas no reconocidas se conservan.  
    """  
    df = normalizar\_encabezados(  
        df\_original,  
        COLUMN\_MAPPING\_CLIENTES,  
    )  
    for columna in COLUMNAS\_CLIENTES\_EDITABLES:  
        if columna not in df.columns:  
            df\[columna\] = ""  
    for columna in df.columns:  
        df\[columna\] = (  
            df\[columna\]  
            .fillna("")  
            .astype(str)  
            .str.strip()  
        )  
    df\["numero\_serie"\] = (  
        df\["numero\_serie"\]  
        .apply(normalizar\_numero\_serie\_valor)  
    )  
    df\["categoria"\] = (  
        df\["categoria"\]  
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
def valor\_registro(registro, columna):  
    """  
    Devuelve un valor de texto seguro para utilizar como  
    valor inicial de un campo de formulario.  
    """  
    if columna not in registro.index:  
        return ""  
    valor = registro\[columna\]  
    if pd.isna(valor):  
        return ""  
    return str(valor).strip()  
def guardar\_cambios\_clientes(  
    df\_clientes,  
    sha,  
    separador,  
    mensaje,  
):  
    """  
    Guarda el CSV, limpia la caché y muestra el resultado  
    después de recargar la aplicación.  
    """  
    guardar\_clientes\_github(  
        dataframe=df\_clientes,  
        sha=sha,  
        separador=separador,  
        mensaje\_commit=mensaje,  
    )  
    load\_data.clear()  
    st.session\_state\[  
        "mensaje\_edicion\_clientes"  
    \] = "Los cambios se guardaron correctamente en GitHub."  
    st.rerun()  
\# =====================================================  
\# CARGA DE DATOS  
\# =====================================================  
try:  
    df = load\_data(  
        CACHE\_VERSION  
    )  
except Exception as error:  
    st.error(  
        "No se pudieron cargar las fuentes de datos del tablero."  
    )  
    with st.expander("Detalle técnico"):  
        st.exception(error)  
    st.stop()  
\# =====================================================  
\# VALIDACIÓN DEL DATAFRAME  
\# =====================================================  
columnas\_obligatorias = \[  
    "numero\_serie",  
    "organizacion",  
    "sucursal",  
    "cliente",  
    "operario",  
    "categoria",  
    "fecha\_inicio",  
    "fecha\_fin",  
    "autotrac",  
    "score\_basic",  
    "score\_elite",  
    "necesidad\_intervencion",  
\]  
columnas\_faltantes = \[  
    columna  
    for columna in columnas\_obligatorias  
    if columna not in df.columns  
\]  
if columnas\_faltantes:  
    st.error(  
        "Faltan columnas necesarias para mostrar el tablero: "  
        \+ ", ".join(columnas\_faltantes)  
    )  
    with st.expander("Columnas disponibles"):  
        st.write(  
            df.columns.tolist()  
        )  
    st.stop()  
\# =====================================================  
\# NORMALIZACIÓN FINAL  
\# =====================================================  
df\["categoria"\] = (  
    df\["categoria"\]  
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
df\["sucursal"\] = (  
    df\["sucursal"\]  
    .fillna("")  
    .astype(str)  
    .str.strip()  
)  
df\["organizacion"\] = (  
    df\["organizacion"\]  
    .fillna("")  
    .astype(str)  
    .str.strip()  
)  
df\["cliente"\] = (  
    df\["cliente"\]  
    .fillna("")  
    .astype(str)  
    .str.strip()  
)  
df\["fecha\_inicio"\] = pd.to\_datetime(  
    df\["fecha\_inicio"\],  
    errors="coerce",  
    dayfirst=True,  
).dt.normalize()  
df\["fecha\_fin"\] = pd.to\_datetime(  
    df\["fecha\_fin"\],  
    errors="coerce",  
    dayfirst=True,  
).dt.normalize()  
\# =====================================================  
\# SIDEBAR  
\# =====================================================  
st.sidebar.header("Filtros")  
\# =====================================================  
\# FILTRO DE SUCURSAL  
\# =====================================================  
sucursales = sorted(  
    df\["sucursal"\]  
    .loc\[lambda serie: serie.ne("")\]  
    .unique()  
    .tolist()  
)  
sucursal\_seleccionada = st.sidebar.selectbox(  
    "Sucursal",  
    options=\[  
        "Todas",  
        \*sucursales,  
    \],  
    index=0,  
)  
\# =====================================================  
\# FILTRO DE ORGANIZACIONES  
\# =====================================================  
\# La lista de organizaciones depende de la sucursal  
\# seleccionada.  
df\_sidebar = df.copy()  
if sucursal\_seleccionada!= "Todas":  
    df\_sidebar = df\_sidebar\[  
        df\_sidebar\["sucursal"\]  
        == sucursal\_seleccionada  
    \]  
organizaciones = sorted(  
    df\_sidebar\["organizacion"\]  
    .fillna("")  
    .astype(str)  
    .str.strip()  
    .loc\[lambda serie: serie.ne("")\]  
    .unique()  
    .tolist()  
)  
organizaciones\_seleccionadas = st.sidebar.multiselect(  
    "Organización",  
    options=organizaciones,  
    default=\[\],  
)  
\# =====================================================  
\# FILTRO DE NECESIDAD DE INTERVENCIÓN  
\# =====================================================  
opciones\_intervencion = \[  
    "Todas",  
    "INTERVENCIÓN NECESARIA",  
    "INTERVENCIÓN MODERADA",  
    "NO REQUIERE INTERVENCIÓN",  
\]  
intervencion\_seleccionada = st.sidebar.selectbox(  
    "Necesidad de intervención",  
    options=opciones\_intervencion,  
    index=0,  
)  
\# =====================================================  
\# FILTRO DE FECHAS  
\# =====================================================  
periodo\_seleccionado = None  
fecha\_minima = df\["fecha\_inicio"\].min()  
fecha\_maxima = df\["fecha\_fin"\].max()  
if (  
    pd.notna(fecha\_minima)  
    and pd.notna(fecha\_maxima)  
):  
    periodo\_seleccionado = st.sidebar.date\_input(  
        "Periodo",  
        value=(  
            fecha\_minima.date(),  
            fecha\_maxima.date(),  
        ),  
        min\_value=fecha\_minima.date(),  
        max\_value=fecha\_maxima.date(),  
    )  
\# =====================================================  
\# APLICACIÓN DE FILTROS HISTÓRICOS  
\# =====================================================  
df\_filtrado = df.copy()  
\# =====================================================  
\# SUCURSAL  
\# =====================================================  
if sucursal\_seleccionada!= "Todas":  
    df\_filtrado = df\_filtrado\[  
        df\_filtrado\["sucursal"\]  
        == sucursal\_seleccionada  
    \]  
\# =====================================================  
\# ORGANIZACIONES  
\# =====================================================  
if organizaciones\_seleccionadas:  
    df\_filtrado = df\_filtrado\[  
        df\_filtrado\["organizacion"\].isin(  
            organizaciones\_seleccionadas  
        )  
    \]  
\# =====================================================  
\# PERÍODO  
\# =====================================================  
if (  
    periodo\_seleccionado  
    and isinstance(  
        periodo\_seleccionado,  
        (tuple, list),  
    )  
    and len(periodo\_seleccionado) == 2  
):  
    fecha\_desde = pd.Timestamp(  
        periodo\_seleccionado\[0\]  
    ).normalize()  
    fecha\_hasta = pd.Timestamp(  
        periodo\_seleccionado\[1\]  
    ).normalize()  
    \# Incluye cualquier semana que se superponga  
    \# con el rango seleccionado.  
    df\_filtrado = df\_filtrado\[  
        (  
            df\_filtrado\["fecha\_inicio"\]  
            \<= fecha\_hasta  
        )  
        & (  
            df\_filtrado\["fecha\_fin"\]  
            \>= fecha\_desde  
        )  
    \].copy()  
\# =====================================================  
\# HISTÓRICO POR CATEGORÍA  
\# =====================================================  
basic\_historico = df\_filtrado\[  
    df\_filtrado\["categoria"\] == "BASIC"  
\].copy()  
elite\_historico = df\_filtrado\[  
    df\_filtrado\["categoria"\] == "ELITE"  
\].copy()  
\# =====================================================  
\# CONSOLIDACIÓN DEL PERÍODO  
\# =====================================================  
basic\_periodo = consolidar\_periodo(  
    basic\_historico  
)  
elite\_periodo = consolidar\_periodo(  
    elite\_historico  
)  
\# =====================================================  
\# INTERVENCIÓN DEL PERÍODO  
\# =====================================================  
\# Este filtro se aplica después de consolidar las semanas,  
\# porque la intervención debe depender del score promedio  
\# del período y no de una semana individual.  
if intervencion\_seleccionada!= "Todas":  
    if (  
        not basic\_periodo.empty  
        and "necesidad\_intervencion"  
        in basic\_periodo.columns  
    ):  
        basic\_periodo = basic\_periodo\[  
            basic\_periodo\[  
                "necesidad\_intervencion"  
            \]  
            == intervencion\_seleccionada  
        \].copy()  
    if (  
        not elite\_periodo.empty  
        and "necesidad\_intervencion"  
        in elite\_periodo.columns  
    ):  
        elite\_periodo = elite\_periodo\[  
            elite\_periodo\[  
                "necesidad\_intervencion"  
            \]  
            == intervencion\_seleccionada  
        \].copy()  
\# =====================================================  
\# ALINEACIÓN DE HISTÓRICOS  
\# =====================================================  
\# La evolución utiliza la misma población seleccionada  
\# para los KPI, rankings y tablas de clientes.  
basic\_historico = filtrar\_historico\_por\_poblacion(  
    basic\_historico,  
    basic\_periodo,  
)  
elite\_historico = filtrar\_historico\_por\_poblacion(  
    elite\_historico,  
    elite\_periodo,  
)  
\# =====================================================  
\# RESUMEN DE FILTROS  
\# =====================================================  
series\_basic = (  
    basic\_periodo\["numero\_serie"\]  
    if "numero\_serie" in basic\_periodo.columns  
    else pd.Series(dtype="string")  
)  
series\_elite = (  
    elite\_periodo\["numero\_serie"\]  
    if "numero\_serie" in elite\_periodo.columns  
    else pd.Series(dtype="string")  
)  
maquinas\_seleccionadas = (  
    pd.concat(  
        \[  
            series\_basic,  
            series\_elite,  
        \],  
        ignore\_index=True,  
    )  
    .dropna()  
    .nunique()  
)  
st.sidebar.caption(  
    f"{maquinas\_seleccionadas} "  
    "máquinas seleccionadas"  
)  
\# =====================================================  
\# TABS PRINCIPALES  
\# =====================================================  
tab\_general, tab\_informe, tab\_clientes = st.tabs(  
    \[  
        "Tablero General",  
        "Generación Informe",  
        "Datos Clientes",  
    \]  
)  
\# =====================================================  
\# TAB GENERAL  
\# =====================================================  
with tab\_general:  
    basic\_tab, elite\_tab = st.tabs(  
        \[  
            "Basic",  
            "Elite",  
        \]  
    )  
    \# =================================================  
    \# BASIC  
    \# =================================================  
    with basic\_tab:  
        \# Una fila por máquina con el promedio del período.  
        basic = basic\_periodo.copy()  
        st.subheader("Categoría Basic")  
        c1, c2, c3, c4 = st.columns(4)  
        c1.metric(  
            "Participantes",  
            (  
                basic\["numero\_serie"\].nunique()  
                if "numero\_serie" in basic.columns  
                else 0  
            ),  
        )  
        c2.metric(  
            "Clientes",  
            (  
                basic\["cliente"\].nunique()  
                if "cliente" in basic.columns  
                else 0  
            ),  
        )  
        c3.metric(  
            "AutoTrac promedio",  
            formatear\_porcentaje\_tecnologia(  
                porcentaje\_tecnologia(  
                    basic,  
                    "autotrac",  
                )  
            ),  
        )  
        c4.metric(  
            "Score Basic",  
            # En Basic, el score es exactamente el mismo valor  
            # que AutoTrac. Se lee directamente desde AutoTrac  
            # para evitar diferencias por datos precalculados.  
            formatear\_score\_tecnologia(  
                basic,  
                "autotrac",  
            ),  
        )  
        \# =================================================  
        \# EVOLUCIÓN TEMPORAL BASIC  
        \# =================================================  
        st.divider()  
        st.subheader(  
            "Evolución temporal Basic"  
        )  
        evolucion\_basic = construir\_evolucion\_semanal(  
            basic\_historico,  
            metricas=\[  
                "autotrac",  
                "score\_basic",  
            \],  
            nombres\_metricas={  
                "autotrac": "AutoTrac",  
                "score\_basic": "Score Basic",  
            },  
        )  
        if evolucion\_basic.empty:  
            st.info(  
                "No hay datos históricos disponibles "  
                "para construir la evolución temporal "  
                "de la categoría Basic."  
            )  
        else:  
            st.line\_chart(  
                evolucion\_basic,  
                use\_container\_width=True,  
            )  
            if len(evolucion\_basic) == 1:  
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
                    evolucion\_basic.reset\_index(),  
                    use\_container\_width=True,  
                    hide\_index=True,  
                    column\_config={  
                        "Semana": (  
                            st.column\_config.DateColumn(  
                                format="DD/MM/YYYY"  
                            )  
                        ),  
                        "AutoTrac": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f%%"  
                            )  
                        ),  
                        "Score Basic": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f"  
                            )  
                        ),  
                    },  
                )  
        \# =================================================  
        \# RANKING BASIC  
        \# =================================================  
        st.divider()  
        st.subheader("Ranking Basic")  
        if basic.empty:  
            mostrar\_tabla\_vacia(  
                "No hay participantes Basic para "  
                "los filtros seleccionados."  
            )  
        else:  
            ranking\_basic = (  
                basic  
                .sort\_values(  
                    "score\_basic",  
                    ascending=False,  
                )  
                .reset\_index(drop=True)  
            )  
            ranking\_basic.insert(  
                0,  
                "posición",  
                range(  
                    1,  
                    len(ranking\_basic) + 1,  
                ),  
            )  
            columnas\_ranking\_basic = \[  
                "posición",  
                "organizacion",  
                "org\_id",  
                "operario",  
                "cliente",  
                "sucursal",  
                "numero\_serie",  
                "fecha\_inicio",  
                "fecha\_fin",  
                "autotrac",  
                "score\_basic",  
                "necesidad\_intervencion",  
            \]  
            faltantes\_ranking\_basic = \[  
                columna  
                for columna in columnas\_ranking\_basic  
                if columna not in ranking\_basic.columns  
            \]  
            if faltantes\_ranking\_basic:  
                st.error(  
                    "No se puede construir el ranking Basic. "  
                    "Faltan las columnas: "  
                    \+ ", ".join(  
                        faltantes\_ranking\_basic  
                    )  
                )  
                with st.expander(  
                    "Columnas disponibles en el ranking Basic"  
                ):  
                    st.write(  
                        ranking\_basic.columns.tolist()  
                    )  
            else:  
                tabla\_basic = ranking\_basic\[  
                    columnas\_ranking\_basic  
                \].copy()  
                tabla\_basic = tabla\_basic.rename(  
                    columns={  
                        "posición": "Posición",  
                        "organizacion": "Organización",  
                        "org\_id": "Organization ID",  
                        "operario": "Operario",  
                        "cliente": "Cliente",  
                        "sucursal": "Sucursal",  
                        "numero\_serie": "N.º de serie",  
                        "fecha\_inicio": "Desde",  
                        "fecha\_fin": "Hasta",  
                        "autotrac": "AutoTrac (%)",  
                        "score\_basic": "Score Basic",  
                        "necesidad\_intervencion": (  
                            "Intervención"  
                        ),  
                    }  
                )  
                st.dataframe(  
                    tabla\_basic,  
                    use\_container\_width=True,  
                    hide\_index=True,  
                    column\_config={  
                        "Posición": (  
                            st.column\_config.NumberColumn(  
                                format="%d",  
                                width="small",  
                            )  
                        ),  
                        "Organización": (  
                            st.column\_config.TextColumn(  
                                width="medium",  
                            )  
                        ),  
                        "Organization ID": (  
                            st.column\_config.TextColumn(  
                                width="medium",  
                            )  
                        ),  
                        "Operario": (  
                            st.column\_config.TextColumn(  
                                width="medium",  
                            )  
                        ),  
                        "Cliente": (  
                            st.column\_config.TextColumn(  
                                width="medium",  
                            )  
                        ),  
                        "Sucursal": (  
                            st.column\_config.TextColumn(  
                                width="small",  
                            )  
                        ),  
                        "N.º de serie": (  
                            st.column\_config.TextColumn(  
                                width="medium",  
                            )  
                        ),  
                        "Desde": (  
                            st.column\_config.DateColumn(  
                                format="DD/MM/YYYY",  
                            )  
                        ),  
                        "Hasta": (  
                            st.column\_config.DateColumn(  
                                format="DD/MM/YYYY",  
                            )  
                        ),  
                        "AutoTrac (%)": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f%%",  
                            )  
                        ),  
                        "Score Basic": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f",  
                            )  
                        ),  
                        "Intervención": (  
                            st.column\_config.TextColumn(  
                                width="medium",  
                            )  
                        ),  
                    },  
                )  
    \# =================================================  
    \# ELITE  
    \# =================================================  
    with elite\_tab:  
        \# Una fila por máquina con el promedio del período.  
        elite = elite\_periodo.copy()  
        st.subheader("Categoría Elite")  
        c1, c2, c3, c4, c5 = st.columns(5)  
        c1.metric(  
            "Participantes",  
            (  
                elite\["numero\_serie"\].nunique()  
                if "numero\_serie" in elite.columns  
                else 0  
            ),  
        )  
        c2.metric(  
            "Score Elite",  
            formatear\_score\_tecnologia(  
                elite,  
                "score\_elite",  
            ),  
        )  
        c3.metric(  
            "AutoTrac",  
            formatear\_porcentaje\_tecnologia(  
                porcentaje\_tecnologia(  
                    elite,  
                    "autotrac",  
                )  
            ),  
        )  
        c4.metric(  
            "Turn Automation",  
            formatear\_porcentaje\_tecnologia(  
                porcentaje\_tecnologia(  
                    elite,  
                    "turn\_automation",  
                )  
            ),  
        )  
        c5.metric(  
            "Ocio controlable",  
            (  
                f"{promedio\_seguro(elite, 'ocio\_controlable'):.1f}%"  
            ),  
        )  
        \# =================================================  
        \# EVOLUCIÓN TEMPORAL ELITE  
        \# =================================================  
        st.divider()  
        st.subheader(  
            "Evolución temporal Elite"  
        )  
        evolucion\_elite = construir\_evolucion\_semanal(  
            elite\_historico,  
            metricas=\[  
                "score\_elite",  
                "autotrac",  
                "turn\_automation",  
                "autopath",  
                "implement\_guidance",  
                "efficiency\_manager",  
                "field\_cruise",  
                "ocio\_controlable",  
            \],  
            nombres\_metricas={  
                "score\_elite": "Score Elite",  
                "autotrac": "AutoTrac",  
                "turn\_automation": (  
                    "Turn Automation"  
                ),  
                "autopath": "AutoPath",  
                "implement\_guidance": (  
                    "Implement Guidance"  
                ),  
                "efficiency\_manager": (  
                    "Efficiency Manager"  
                ),  
                "field\_cruise": (  
                    "Field Cruise"  
                ),  
                "ocio\_controlable": (  
                    "Ocio controlable"  
                ),  
            },  
        )  
        if evolucion\_elite.empty:  
            st.info(  
                "No hay datos históricos disponibles "  
                "para construir la evolución temporal "  
                "de la categoría Elite."  
            )  
        else:  
            st.line\_chart(  
                evolucion\_elite,  
                use\_container\_width=True,  
            )  
            if len(evolucion\_elite) == 1:  
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
                    evolucion\_elite.reset\_index(),  
                    use\_container\_width=True,  
                    hide\_index=True,  
                    column\_config={  
                        "Semana": (  
                            st.column\_config.DateColumn(  
                                format="DD/MM/YYYY"  
                            )  
                        ),  
                        "Score Elite": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f"  
                            )  
                        ),  
                        "AutoTrac": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f%%"  
                            )  
                        ),  
                        "Turn Automation": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f%%"  
                            )  
                        ),  
                        "AutoPath": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f%%"  
                            )  
                        ),  
                        "Implement Guidance": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f%%"  
                            )  
                        ),  
                        "Efficiency Manager": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f%%"  
                            )  
                        ),  
                        "Field Cruise": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f%%"  
                            )  
                        ),  
                        "Ocio controlable": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f%%"  
                            )  
                        ),  
                    },  
                )  
        \# =================================================  
        \# RANKING ELITE  
        \# =================================================  
        st.divider()  
        st.subheader("Ranking Elite")  
        if elite.empty:  
            mostrar\_tabla\_vacia(  
                "No hay participantes Elite para "  
                "los filtros seleccionados."  
            )  
        else:  
            ranking\_elite = (  
                elite  
                .sort\_values(  
                    "score\_elite",  
                    ascending=False,  
                )  
                .reset\_index(drop=True)  
            )  
            ranking\_elite.insert(  
                0,  
                "posición",  
                range(  
                    1,  
                    len(ranking\_elite) + 1,  
                ),  
            )  
            columnas\_ranking\_elite = \[  
                "posición",  
                "organizacion",  
                "org\_id",  
                "operario",  
                "cliente",  
                "sucursal",  
                "numero\_serie",  
                "fecha\_inicio",  
                "fecha\_fin",  
                "autotrac",  
                "turn\_automation",  
                "autopath",  
                "implement\_guidance",  
                "efficiency\_manager",  
                "field\_cruise",  
                "ocio\_controlable",  
                "score\_elite",  
                "necesidad\_intervencion",  
            \]  
            faltantes\_ranking\_elite = \[  
                columna  
                for columna in columnas\_ranking\_elite  
                if columna not in ranking\_elite.columns  
            \]  
            if faltantes\_ranking\_elite:  
                st.error(  
                    "No se puede construir el ranking Elite. "  
                    "Faltan las columnas: "  
                    \+ ", ".join(  
                        faltantes\_ranking\_elite  
                    )  
                )  
                with st.expander(  
                    "Columnas disponibles en el ranking Elite"  
                ):  
                    st.write(  
                        ranking\_elite.columns.tolist()  
                    )  
            else:  
                tabla\_elite = ranking\_elite\[  
                    columnas\_ranking\_elite  
                \].copy()  
                tabla\_elite = tabla\_elite.rename(  
                    columns={  
                        "posición": "Posición",  
                        "organizacion": "Organización",  
                        "org\_id": "Organization ID",  
                        "operario": "Operario",  
                        "cliente": "Cliente",  
                        "sucursal": "Sucursal",  
                        "numero\_serie": "N.º de serie",  
                        "fecha\_inicio": "Desde",  
                        "fecha\_fin": "Hasta",  
                        "autotrac": "AutoTrac (%)",  
                        "turn\_automation": (  
                            "Turn Automation (%)"  
                        ),  
                        "autopath": "AutoPath (%)",  
                        "implement\_guidance": (  
                            "Implement Guidance (%)"  
                        ),  
                        "efficiency\_manager": (  
                            "Efficiency Manager (%)"  
                        ),  
                        "field\_cruise": (  
                            "Field Cruise (%)"  
                        ),  
                        "ocio\_controlable": (  
                            "Ocio controlable (%)"  
                        ),  
                        "score\_elite": "Score Elite",  
                        "necesidad\_intervencion": (  
                            "Intervención"  
                        ),  
                    }  
                )  
                st.dataframe(  
                    tabla\_elite,  
                    use\_container\_width=True,  
                    hide\_index=True,  
                    column\_config={  
                        "Posición": (  
                            st.column\_config.NumberColumn(  
                                format="%d",  
                                width="small",  
                            )  
                        ),  
                        "Organización": (  
                            st.column\_config.TextColumn(  
                                width="medium",  
                            )  
                        ),  
                        "Organization ID": (  
                            st.column\_config.TextColumn(  
                                width="medium",  
                            )  
                        ),  
                        "Operario": (  
                            st.column\_config.TextColumn(  
                                width="medium",  
                            )  
                        ),  
                        "Cliente": (  
                            st.column\_config.TextColumn(  
                                width="medium",  
                            )  
                        ),  
                        "Sucursal": (  
                            st.column\_config.TextColumn(  
                                width="small",  
                            )  
                        ),  
                        "N.º de serie": (  
                            st.column\_config.TextColumn(  
                                width="medium",  
                            )  
                        ),  
                        "Desde": (  
                            st.column\_config.DateColumn(  
                                format="DD/MM/YYYY",  
                            )  
                        ),  
                        "Hasta": (  
                            st.column\_config.DateColumn(  
                                format="DD/MM/YYYY",  
                            )  
                        ),  
                        "AutoTrac (%)": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f%%",  
                            )  
                        ),  
                        "Turn Automation (%)": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f%%",  
                            )  
                        ),  
                        "AutoPath (%)": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f%%",  
                            )  
                        ),  
                        "Implement Guidance (%)": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f%%",  
                            )  
                        ),  
                        "Efficiency Manager (%)": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f%%",  
                            )  
                        ),  
                        "Field Cruise (%)": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f%%",  
                            )  
                        ),  
                        "Ocio controlable (%)": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f%%",  
                            )  
                        ),  
                        "Score Elite": (  
                            st.column\_config.NumberColumn(  
                                format="%.1f",  
                            )  
                        ),  
                        "Intervención": (  
                            st.column\_config.TextColumn(  
                                width="medium",  
                            )  
                        ),  
                    },  
                )  
\# =====================================================  
\# TAB INFORME  
\# =====================================================  
with tab\_informe:  
    st.subheader("Generación de informe")  
    st.caption(  
        "Buscá una máquina por cliente, operario o número de serie. "  
        "Las posiciones se calculan contra participantes de la misma "  
        "categoría durante el período seleccionado."  
    )  
    historico\_informe = filtrar\_periodo\_informe(  
        df,  
        periodo\_seleccionado,  
    )  
    basic\_informe = consolidar\_periodo(  
        historico\_informe\[  
            historico\_informe\["categoria"\] == "BASIC"  
        \].copy()  
    )  
    elite\_informe = consolidar\_periodo(  
        historico\_informe\[  
            historico\_informe\["categoria"\] == "ELITE"  
        \].copy()  
    )  
    poblacion\_informe = pd.concat(  
        \[basic\_informe, elite\_informe\],  
        ignore\_index=True,  
    )  
    if poblacion\_informe.empty:  
        st.info(  
            "No hay participantes disponibles en el período "  
            "seleccionado."  
        )  
    else:  
        columnas\_busqueda = \[  
            columna  
            for columna in \[  
                "cliente",  
                "operario",  
                "numero\_serie",  
            \]  
            if columna in poblacion\_informe.columns  
        \]  
        consulta = st.text\_input(  
            "Buscar participante",  
            placeholder=(  
                "Escribí cliente, operario o número de serie"  
            ),  
        ).strip()  
        if not consulta:  
            st.info(  
                "Ingresá un dato en el buscador para seleccionar "  
                "el participante."  
            )  
        else:  
            mascara\_busqueda = pd.Series(  
                False,  
                index=poblacion\_informe.index,  
            )  
            for columna in columnas\_busqueda:  
                mascara\_busqueda \|= (  
                    poblacion\_informe\[columna\]  
                    .fillna("")  
                    .astype(str)  
                    .str.contains(  
                        consulta,  
                        case=False,  
                        regex=False,  
                    )  
                )  
            resultados = poblacion\_informe\[  
                mascara\_busqueda  
            \].copy()  
            if resultados.empty:  
                st.warning(  
                    "No se encontraron coincidencias para la búsqueda."  
                )  
            else:  
                resultados\["etiqueta\_informe"\] = resultados.apply(  
                    lambda fila: (  
                        f"{texto\_seguro(fila.get('cliente'))} \| "  
                        f"{texto\_seguro(fila.get('operario'))} \| "  
                        f"Serie {texto\_seguro(fila.get('numero\_serie'))} \| "  
                        f"{texto\_seguro(fila.get('categoria'))} \| "  
                        f"{texto\_seguro(fila.get('sucursal'))}"  
                    ),  
                    axis=1,  
                )  
                indice\_seleccionado = st.selectbox(  
                    "Seleccionar resultado",  
                    options=resultados.index.tolist(),  
                    format\_func=lambda indice: resultados.loc\[  
                        indice,  
                        "etiqueta\_informe",  
                    \],  
                )  
                registro = resultados.loc\[  
                    indice\_seleccionado  
                \].copy()  
                categoria\_informe = texto\_seguro(  
                    registro.get("categoria"),  
                    predeterminado="",  
                ).upper()  
                numero\_serie\_informe = registro\[  
                    "numero\_serie"  
                \]  
                sucursal\_informe = texto\_seguro(  
                    registro.get("sucursal"),  
                    predeterminado="",  
                )  
                columna\_score\_informe = (  
                    # En Basic, el ranking y el informe usan  
                    # directamente AutoTrac como score.  
                    "autotrac"  
                    if categoria\_informe == "BASIC"  
                    else "score\_elite"  
                )  
                poblacion\_categoria = (  
                    basic\_informe  
                    if categoria\_informe == "BASIC"  
                    else elite\_informe  
                )  
                posiciones = calcular\_posiciones\_informe(  
                    poblacion\_categoria,  
                    numero\_serie\_informe,  
                    columna\_score\_informe,  
                    sucursal\_informe,  
                )  
                evolucion\_informe = (  
                    construir\_evolucion\_participante(  
                        historico\_informe\[  
                            historico\_informe\["categoria"\]  
                            == categoria\_informe  
                        \],  
                        numero\_serie\_informe,  
                        categoria\_informe,  
                    )  
                )  
                st.divider()  
                st.markdown(  
                    f"### {texto\_seguro(registro.get('cliente'))}"  
                )  
                st.caption(  
                    f"Operario: "  
                    f"{texto\_seguro(registro.get('operario'))} · "  
                    f"Serie: {texto\_seguro(numero\_serie\_informe)} · "  
                    f"Sucursal: "  
                    f"{texto\_seguro(registro.get('sucursal'))} · "  
                    f"Categoría: {categoria\_informe.title()}"  
                )  
                score\_informe = valor\_numerico(  
                    registro,  
                    columna\_score\_informe,  
                )  
                c1, c2, c3, c4 = st.columns(4)  
                c1.metric(  
                    f"Score {categoria\_informe.title()}",  
                    f"{score\_informe:.1f}",  
                )  
                c2.metric(  
                    "Posición Conci",  
                    (  
                        f"{posiciones\['general'\]} de "  
                        f"{posiciones\['total\_general'\]}"  
                        if posiciones\["general"\] is not None  
                        else "Sin posición"  
                    ),  
                )  
                c3.metric(  
                    "Posición sucursal",  
                    (  
                        f"{posiciones\['sucursal'\]} de "  
                        f"{posiciones\['total\_sucursal'\]}"  
                        if posiciones\["sucursal"\] is not None  
                        else "Sin posición"  
                    ),  
                )  
                c4.metric(  
                    "Intervención",  
                    texto\_seguro(  
                        registro.get(  
                            "necesidad\_intervencion"  
                        )  
                    ),  
                )  
                figura\_radar = None  
                figura\_evolucion = None  
                if categoria\_informe == "BASIC":  
                    figura\_evolucion = crear\_figura\_evolucion(  
                        evolucion\_informe,  
                        categoria\_informe,  
                    )  
                    st.markdown("#### Indicadores Basic")  
                    ultimo\_autotrac = valor\_tecnologia\_registro(  
                        registro,  
                        "autotrac",  
                    )  
                    delta\_autotrac = None  
                    delta\_score = None  
                    if len(evolucion\_informe) \>= 2:  
                        if "AutoTrac" in evolucion\_informe:  
                            valores\_autotrac = pd.to\_numeric(  
                                evolucion\_informe\["AutoTrac"\],  
                                errors="coerce",  
                            ).dropna()  
                            if len(valores\_autotrac) \>= 2:  
                                delta\_autotrac = (  
                                    valores\_autotrac.iloc\[-1\]  
                                    \- valores\_autotrac.iloc\[-2\]  
                                )  
                        if "Score Basic" in evolucion\_informe:  
                            delta\_score = (  
                                evolucion\_informe\[  
                                    "Score Basic"  
                                \].iloc\[-1\]  
                                \- evolucion\_informe\[  
                                    "Score Basic"  
                                \].iloc\[-2\]  
                            )  
                    metrica1, metrica2 = st.columns(2)  
                    metrica1.metric(  
                        "AutoTrac",  
                        formatear\_porcentaje\_tecnologia(  
                            ultimo\_autotrac  
                        ),  
                        (  
                            f"{delta\_autotrac:+.1f} puntos"  
                            if delta\_autotrac is not None  
                            else None  
                        ),  
                    )  
                    metrica2.metric(  
                        "Score Basic",  
                        f"{score\_informe:.1f}",  
                        (  
                            f"{delta\_score:+.1f} puntos"  
                            if delta\_score is not None  
                            else None  
                        ),  
                    )  
                    st.markdown(  
                        "#### Evolución de las últimas semanas"  
                    )  
                    if figura\_evolucion is None:  
                        st.info(  
                            "No hay semanas suficientes para mostrar "  
                            "la evolución."  
                        )  
                    else:  
                        st.pyplot(  
                            figura\_evolucion,  
                            use\_container\_width=True,  
                        )  
                    recomendaciones = recomendaciones\_basic(  
                        registro,  
                        evolucion\_informe,  
                    )  
                else:  
                    st.markdown("#### Indicadores Elite")  
                    figura\_radar = crear\_radar\_elite(registro)  
                    columna\_radar, columna\_detalle = st.columns(  
                        \[2, 1\]  
                    )  
                    with columna\_radar:  
                        st.pyplot(  
                            figura\_radar,  
                            use\_container\_width=True,  
                        )  
                        st.caption(  
                            "Para facilitar la lectura, el radar muestra "  
                            "Control del ocio = 100 - ocio controlable."  
                        )  
                    with columna\_detalle:  
                        for columna, nombre in (  
                            METRICAS\_ELITE\_INFORME.items()  
                        ):  
                            st.metric(  
                                nombre,  
                                formatear\_porcentaje\_tecnologia(  
                                    valor\_tecnologia\_registro(  
                                        registro,  
                                        columna,  
                                    )  
                                ),  
                            )  
                        st.metric(  
                            "Ocio controlable",  
                            (  
                                f"{valor\_numerico(registro, 'ocio\_controlable'):.1f}%"  
                            ),  
                        )  
                    recomendaciones = recomendaciones\_elite(  
                        registro  
                    )  
                st.markdown("#### Recomendaciones para mejorar")  
                for recomendacion in recomendaciones:  
                    st.markdown(f"- {recomendacion}")  
                pdf\_informe = generar\_pdf\_informe(  
                    registro=registro,  
                    categoria=categoria\_informe,  
                    posiciones=posiciones,  
                    evolucion=evolucion\_informe,  
                    recomendaciones=recomendaciones,  
                    figura\_radar=figura\_radar,  
                    figura\_evolucion=figura\_evolucion,  
                )  
                nombre\_serie\_archivo = (  
                    texto\_seguro(numero\_serie\_informe, "sin\_serie")  
                    .replace(" ", "\_")  
                    .replace("/", "-")  
                )  
                st.divider()  
                st.download\_button(  
                    "📄 Descargar informe PDF",  
                    data=pdf\_informe,  
                    file\_name=(  
                        f"informe\_crack\_del\_campo\_"  
                        f"{nombre\_serie\_archivo}.pdf"  
                    ),  
                    mime="application/pdf",  
                    use\_container\_width=True,  
                    type="primary",  
                )  
                if figura\_evolucion is not None:  
                    plt.close(figura\_evolucion)  
                if figura\_radar is not None:  
                    plt.close(figura\_radar)  
\# =====================================================  
\# TAB DATOS DE CLIENTES  
\# =====================================================  
with tab\_clientes:  
    basic\_clientes, elite\_clientes, edicion\_clientes = st.tabs(  
        \[  
            "Basic",  
            "Elite",  
            "Edición",  
        \]  
    )  
    columnas\_clientes\_deseadas = \[  
        "organizacion",  
        "org\_id",  
        "sucursal",  
        "numero\_serie",  
        "operario",  
        "categoria",  
        "telefono\_operario",  
        "necesidad\_intervencion",  
    \]  
    \# =================================================  
    \# CLIENTES BASIC  
    \# =================================================  
    with basic\_clientes:  
        datos\_basic = basic\_periodo.copy()  
        columnas\_basic\_clientes = \[  
            columna  
            for columna in columnas\_clientes\_deseadas  
            if columna in datos\_basic.columns  
        \]  
        if datos\_basic.empty:  
            mostrar\_tabla\_vacia(  
                "No hay clientes Basic para "  
                "los filtros seleccionados."  
            )  
        else:  
            st.subheader(  
                "Participantes Basic"  
            )  
            mostrar\_resumen\_completitud(  
                datos\_basic  
            )  
            st.caption(  
                "Un registro se considera completo cuando tiene "  
                "organización, Organization ID, sucursal, número "  
                "de serie, operario, categoría y celular del "  
                "operario."  
            )  
            st.dataframe(  
                datos\_basic\[  
                    columnas\_basic\_clientes  
                \],  
                use\_container\_width=True,  
                hide\_index=True,  
                column\_config={  
                    "organizacion": (  
                        st.column\_config.TextColumn(  
                            "Organización"  
                        )  
                    ),  
                    "org\_id": (  
                        st.column\_config.TextColumn(  
                            "Organization ID"  
                        )  
                    ),  
                    "sucursal": (  
                        st.column\_config.TextColumn(  
                            "Sucursal"  
                        )  
                    ),  
                    "numero\_serie": (  
                        st.column\_config.TextColumn(  
                            "N.º de serie"  
                        )  
                    ),  
                    "operario": (  
                        st.column\_config.TextColumn(  
                            "Operario"  
                        )  
                    ),  
                    "categoria": (  
                        st.column\_config.TextColumn(  
                            "Categoría"  
                        )  
                    ),  
                    "telefono\_operario": (  
                        st.column\_config.TextColumn(  
                            "Celular del operario"  
                        )  
                    ),  
                    "necesidad\_intervencion": (  
                        st.column\_config.TextColumn(  
                            "Intervención",  
                            width="medium",  
                        )  
                    ),  
                },  
            )  
    \# =================================================  
    \# CLIENTES ELITE  
    \# =================================================  
    with elite\_clientes:  
        datos\_elite = elite\_periodo.copy()  
        columnas\_elite\_clientes = \[  
            columna  
            for columna in columnas\_clientes\_deseadas  
            if columna in datos\_elite.columns  
        \]  
        if datos\_elite.empty:  
            mostrar\_tabla\_vacia(  
                "No hay clientes Elite para "  
                "los filtros seleccionados."  
            )  
        else:  
            st.subheader(  
                "Participantes Elite"  
            )  
            mostrar\_resumen\_completitud(  
                datos\_elite  
            )  
            st.caption(  
                "Un registro se considera completo cuando tiene "  
                "organización, Organization ID, sucursal, número "  
                "de serie, operario, categoría y celular del "  
                "operario."  
            )  
            st.dataframe(  
                datos\_elite\[  
                    columnas\_elite\_clientes  
                \],  
                use\_container\_width=True,  
                hide\_index=True,  
                column\_config={  
                    "organizacion": (  
                        st.column\_config.TextColumn(  
                            "Organización"  
                        )  
                    ),  
                    "org\_id": (  
                        st.column\_config.TextColumn(  
                            "Organization ID"  
                        )  
                    ),  
                    "sucursal": (  
                        st.column\_config.TextColumn(  
                            "Sucursal"  
                        )  
                    ),  
                    "numero\_serie": (  
                        st.column\_config.TextColumn(  
                            "N.º de serie"  
                        )  
                    ),  
                    "operario": (  
                        st.column\_config.TextColumn(  
                            "Operario"  
                        )  
                    ),  
                    "categoria": (  
                        st.column\_config.TextColumn(  
                            "Categoría"  
                        )  
                    ),  
                    "telefono\_operario": (  
                        st.column\_config.TextColumn(  
                            "Celular del operario"  
                        )  
                    ),  
                    "necesidad\_intervencion": (  
                        st.column\_config.TextColumn(  
                            "Intervención",  
                            width="medium",  
                        )  
                    ),  
                },  
            )  
    \# =================================================  
    \# EDICIÓN  
    \# =================================================  
    with edicion\_clientes:  
        st.subheader(  
            "Administración de máquinas inscriptas"  
        )  
        st.caption(  
            "Los cambios realizados en esta sección se guardan "  
            "directamente en data/base\_de\_clientes.csv dentro "  
            "del repositorio de GitHub."  
        )  
        mensaje\_guardado = st.session\_state.pop(  
            "mensaje\_edicion\_clientes",  
            None,  
        )  
        if mensaje\_guardado:  
            st.success(  
                mensaje\_guardado  
            )  
        try:  
            clientes\_raw, clientes\_sha, separador\_csv = (  
                cargar\_clientes\_github()  
            )  
            clientes\_edicion = preparar\_clientes\_edicion(  
                clientes\_raw  
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
        editar\_tab, agregar\_tab, eliminar\_tab = st.tabs(  
            \[  
                "Editar máquina",  
                "Agregar máquina",  
                "Eliminar máquina",  
            \]  
        )  
        \# =============================================  
        \# EDITAR MÁQUINA  
        \# =============================================  
        with editar\_tab:  
            if clientes\_edicion.empty:  
                st.info(  
                    "No hay máquinas disponibles para editar."  
                )  
            else:  
                st.markdown(  
                    "#### Buscar máquina"  
                )  
                texto\_busqueda = st.text\_input(  
                    (  
                        "Buscar por número de serie, cliente, "  
                        "organización u operario"  
                    ),  
                    placeholder=(  
                        "Ej.: 1RW..., nombre del cliente, "  
                        "organización u operario"  
                    ),  
                    key="buscar\_maquina\_edicion",  
                )  
                clientes\_resultado = (  
                    clientes\_edicion.copy()  
                )  
                if texto\_busqueda.strip():  
                    busqueda = texto\_busqueda.strip()  
                    columnas\_busqueda = \[  
                        columna  
                        for columna in \[  
                            "numero\_serie",  
                            "cliente",  
                            "organizacion",  
                            "operario",  
                        \]  
                        if columna in clientes\_resultado.columns  
                    \]  
                    mascara\_busqueda = pd.Series(  
                        False,  
                        index=clientes\_resultado.index,  
                        dtype="bool",  
                    )  
                    for columna in columnas\_busqueda:  
                        mascara\_busqueda \|= (  
                            clientes\_resultado\[columna\]  
                            .fillna("")  
                            .astype(str)  
                            .str.contains(  
                                busqueda,  
                                case=False,  
                                regex=False,  
                                na=False,  
                            )  
                        )  
                    clientes\_resultado = (  
                        clientes\_resultado\[  
                            mascara\_busqueda  
                        \]  
                        .copy()  
                    )  
                if not texto\_busqueda.strip():  
                    st.info(  
                        "Escribí un número de serie, nombre del "  
                        "cliente, organización u operario para "  
                        "buscar una máquina."  
                    )  
                elif clientes\_resultado.empty:  
                    st.warning(  
                        "No se encontraron máquinas que coincidan "  
                        "con la búsqueda."  
                    )  
                else:  
                    st.caption(  
                        f"{len(clientes\_resultado)} "  
                        "coincidencia(s)"  
                    )  
                    opciones\_edicion = {}  
                    for indice, fila in (  
                        clientes\_resultado.iterrows()  
                    ):  
                        serie = valor\_registro(  
                            fila,  
                            "numero\_serie",  
                        )  
                        cliente = valor\_registro(  
                            fila,  
                            "cliente",  
                        )  
                        organizacion = valor\_registro(  
                            fila,  
                            "organizacion",  
                        )  
                        operario = valor\_registro(  
                            fila,  
                            "operario",  
                        )  
                        etiqueta = " · ".join(  
                            \[  
                                serie or "Sin serie",  
                                cliente or "Sin cliente",  
                                organizacion or (  
                                    "Sin organización"  
                                ),  
                                operario or "Sin operario",  
                            \]  
                        )  
                        etiqueta\_unica = etiqueta  
                        if etiqueta\_unica in opciones\_edicion:  
                            etiqueta\_unica = (  
                                f"{etiqueta} · Registro {indice}"  
                            )  
                        opciones\_edicion\[  
                            etiqueta\_unica  
                        \] = indice  
                    etiqueta\_seleccionada = st.selectbox(  
                        "Seleccionar una máquina",  
                        options=list(  
                            opciones\_edicion.keys()  
                        ),  
                        key="resultado\_busqueda\_edicion",  
                    )  
                    indice\_registro = opciones\_edicion\[  
                        etiqueta\_seleccionada  
                    \]  
                    registro = clientes\_edicion.loc\[  
                        indice\_registro  
                    \].copy()  
                    serie\_editar = valor\_registro(  
                        registro,  
                        "numero\_serie",  
                    )  
                    st.divider()  
                    with st.form(  
                        key=f"form\_editar\_{indice\_registro}"  
                    ):  
                        st.markdown(  
                            "#### Datos de inscripción"  
                        )  
                        columna\_1, columna\_2 = st.columns(2)  
                        with columna\_1:  
                            numero\_serie\_editado = st.text\_input(  
                                "Número de serie",  
                                value=valor\_registro(  
                                    registro,  
                                    "numero\_serie",  
                                ),  
                            )  
                            organizacion\_editada = st.text\_input(  
                                "Organización",  
                                value=valor\_registro(  
                                    registro,  
                                    "organizacion",  
                                ),  
                            )  
                            org\_id\_editado = st.text\_input(  
                                "Organization ID",  
                                value=valor\_registro(  
                                    registro,  
                                    "org\_id",  
                                ),  
                            )  
                            sucursal\_editada = st.text\_input(  
                                "Sucursal",  
                                value=valor\_registro(  
                                    registro,  
                                    "sucursal",  
                                ),  
                            )  
                            operario\_editado = st.text\_input(  
                                "Nombre del operario",  
                                value=valor\_registro(  
                                    registro,  
                                    "operario",  
                                ),  
                            )  
                            telefono\_operario\_editado = (  
                                st.text\_input(  
                                    "Teléfono del operario",  
                                    value=valor\_registro(  
                                        registro,  
                                        "telefono\_operario",  
                                    ),  
                                )  
                            )  
                        with columna\_2:  
                            cliente\_editado = st.text\_input(  
                                "Nombre del cliente",  
                                value=valor\_registro(  
                                    registro,  
                                    "cliente",  
                                ),  
                            )  
                            telefono\_cliente\_editado = (  
                                st.text\_input(  
                                    "Teléfono del cliente",  
                                    value=valor\_registro(  
                                        registro,  
                                        "telefono\_cliente",  
                                    ),  
                                )  
                            )  
                            pais\_editado = st.text\_input(  
                                "País",  
                                value=valor\_registro(  
                                    registro,  
                                    "pais",  
                                ),  
                            )  
                            provincia\_editada = st.text\_input(  
                                "Provincia",  
                                value=valor\_registro(  
                                    registro,  
                                    "provincia",  
                                ),  
                            )  
                            ciudad\_editada = st.text\_input(  
                                "Ciudad",  
                                value=valor\_registro(  
                                    registro,  
                                    "ciudad",  
                                ),  
                            )  
                            categoria\_actual = (  
                                valor\_registro(  
                                    registro,  
                                    "categoria",  
                                )  
                            )  
                            indice\_categoria = (  
                                1  
                                if categoria\_actual == "ELITE"  
                                else 0  
                            )  
                            categoria\_editada = st.selectbox(  
                                "Categoría",  
                                options=\[  
                                    "BASIC",  
                                    "ELITE",  
                                \],  
                                index=indice\_categoria,  
                            )  
                        guardar\_edicion = (  
                            st.form\_submit\_button(  
                                "Guardar cambios",  
                                type="primary",  
                                use\_container\_width=True,  
                            )  
                        )  
                    if guardar\_edicion:  
                        serie\_nueva = (  
                            normalizar\_numero\_serie\_valor(  
                                numero\_serie\_editado  
                            )  
                        )  
                        if not serie\_nueva:  
                            st.error(  
                                "El número de serie es obligatorio."  
                            )  
                        else:  
                            mascara\_otras\_filas = (  
                                clientes\_edicion.index  
                                != indice\_registro  
                            )  
                            serie\_duplicada = (  
                                clientes\_edicion.loc\[  
                                    mascara\_otras\_filas,  
                                    "numero\_serie",  
                                \]  
                                .eq(serie\_nueva)  
                                .any()  
                            )  
                            if serie\_duplicada:  
                                st.error(  
                                    "Ya existe otra máquina con "  
                                    "ese número de serie."  
                                )  
                            else:  
                                clientes\_edicion.loc\[  
                                    indice\_registro,  
                                    "numero\_serie",  
                                \] = serie\_nueva  
                                clientes\_edicion.loc\[  
                                    indice\_registro,  
                                    "organizacion",  
                                \] = organizacion\_editada.strip()  
                                clientes\_edicion.loc\[  
                                    indice\_registro,  
                                    "org\_id",  
                                \] = org\_id\_editado.strip()  
                                clientes\_edicion.loc\[  
                                    indice\_registro,  
                                    "sucursal",  
                                \] = sucursal\_editada.strip()  
                                clientes\_edicion.loc\[  
                                    indice\_registro,  
                                    "operario",  
                                \] = operario\_editado.strip()  
                                clientes\_edicion.loc\[  
                                    indice\_registro,  
                                    "telefono\_operario",  
                                \] = (  
                                    telefono\_operario\_editado.strip()  
                                )  
                                clientes\_edicion.loc\[  
                                    indice\_registro,  
                                    "cliente",  
                                \] = cliente\_editado.strip()  
                                clientes\_edicion.loc\[  
                                    indice\_registro,  
                                    "telefono\_cliente",  
                                \] = (  
                                    telefono\_cliente\_editado.strip()  
                                )  
                                clientes\_edicion.loc\[  
                                    indice\_registro,  
                                    "pais",  
                                \] = pais\_editado.strip()  
                                clientes\_edicion.loc\[  
                                    indice\_registro,  
                                    "provincia",  
                                \] = provincia\_editada.strip()  
                                clientes\_edicion.loc\[  
                                    indice\_registro,  
                                    "ciudad",  
                                \] = ciudad\_editada.strip()  
                                clientes\_edicion.loc\[  
                                    indice\_registro,  
                                    "categoria",  
                                \] = categoria\_editada  
                                try:  
                                    guardar\_cambios\_clientes(  
                                        df\_clientes=(  
                                            clientes\_edicion  
                                        ),  
                                        sha=clientes\_sha,  
                                        separador=separador\_csv,  
                                        mensaje=(  
                                            "Actualiza participante "  
                                            f"{serie\_editar}"  
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
        \# =============================================  
        \# AGREGAR MÁQUINA  
        \# =============================================  
        with agregar\_tab:  
            with st.form(  
                key="form\_agregar\_maquina",  
                clear\_on\_submit=False,  
            ):  
                st.markdown(  
                    "#### Nueva inscripción"  
                )  
                columna\_1, columna\_2 = st.columns(2)  
                with columna\_1:  
                    nueva\_serie = st.text\_input(  
                        "Número de serie \*"  
                    )  
                    nueva\_organizacion = st.text\_input(  
                        "Organización"  
                    )  
                    nuevo\_org\_id = st.text\_input(  
                        "Organization ID"  
                    )  
                    nueva\_sucursal = st.text\_input(  
                        "Sucursal"  
                    )  
                    nuevo\_operario = st.text\_input(  
                        "Nombre del operario"  
                    )  
                    nuevo\_telefono\_operario = st.text\_input(  
                        "Teléfono del operario"  
                    )  
                with columna\_2:  
                    nuevo\_cliente = st.text\_input(  
                        "Nombre del cliente"  
                    )  
                    nuevo\_telefono\_cliente = st.text\_input(  
                        "Teléfono del cliente"  
                    )  
                    nuevo\_pais = st.text\_input(  
                        "País"  
                    )  
                    nueva\_provincia = st.text\_input(  
                        "Provincia"  
                    )  
                    nueva\_ciudad = st.text\_input(  
                        "Ciudad"  
                    )  
                    nueva\_categoria = st.selectbox(  
                        "Categoría",  
                        options=\[  
                            "BASIC",  
                            "ELITE",  
                        \],  
                    )  
                agregar\_maquina = st.form\_submit\_button(  
                    "Agregar máquina",  
                    type="primary",  
                    use\_container\_width=True,  
                )  
            if agregar\_maquina:  
                serie\_normalizada = (  
                    normalizar\_numero\_serie\_valor(  
                        nueva\_serie  
                    )  
                )  
                if not serie\_normalizada:  
                    st.error(  
                        "El número de serie es obligatorio."  
                    )  
                elif (  
                    clientes\_edicion\["numero\_serie"\]  
                    .eq(serie\_normalizada)  
                    .any()  
                ):  
                    st.error(  
                        "Ya existe una máquina con ese "  
                        "número de serie."  
                    )  
                else:  
                    nueva\_fila = {  
                        columna: ""  
                        for columna in clientes\_edicion.columns  
                    }  
                    nueva\_fila.update(  
                        {  
                            "numero\_serie": serie\_normalizada,  
                            "organizacion": (  
                                nueva\_organizacion.strip()  
                            ),  
                            "org\_id": nuevo\_org\_id.strip(),  
                            "sucursal": nueva\_sucursal.strip(),  
                            "operario": nuevo\_operario.strip(),  
                            "telefono\_operario": (  
                                nuevo\_telefono\_operario.strip()  
                            ),  
                            "cliente": nuevo\_cliente.strip(),  
                            "telefono\_cliente": (  
                                nuevo\_telefono\_cliente.strip()  
                            ),  
                            "pais": nuevo\_pais.strip(),  
                            "provincia": (  
                                nueva\_provincia.strip()  
                            ),  
                            "ciudad": nueva\_ciudad.strip(),  
                            "categoria": nueva\_categoria,  
                        }  
                    )  
                    clientes\_actualizados = pd.concat(  
                        \[  
                            clientes\_edicion,  
                            pd.DataFrame(  
                                \[nueva\_fila\]  
                            ),  
                        \],  
                        ignore\_index=True,  
                    )  
                    try:  
                        guardar\_cambios\_clientes(  
                            df\_clientes=clientes\_actualizados,  
                            sha=clientes\_sha,  
                            separador=separador\_csv,  
                            mensaje=(  
                                "Agrega participante "  
                                f"{serie\_normalizada}"  
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
        \# =============================================  
        \# ELIMINAR MÁQUINA  
        \# =============================================  
        with eliminar\_tab:  
            if clientes\_edicion.empty:  
                st.info(  
                    "No hay máquinas disponibles "  
                    "para eliminar."  
                )  
            else:  
                opciones\_eliminar = sorted(  
                    clientes\_edicion\[  
                        "numero\_serie"  
                    \]  
                    .dropna()  
                    .loc\[  
                        lambda serie:  
                        serie.astype(str).str.strip().ne("")  
                    \]  
                    .astype(str)  
                    .unique()  
                    .tolist()  
                )  
                serie\_eliminar = st.selectbox(  
                    "Número de serie a eliminar",  
                    options=opciones\_eliminar,  
                    key="serie\_eliminar",  
                )  
                registro\_eliminar = (  
                    clientes\_edicion\[  
                        clientes\_edicion\["numero\_serie"\]  
                        == serie\_eliminar  
                    \]  
                    .iloc\[0\]  
                )  
                st.warning(  
                    "Esta operación eliminará la inscripción "  
                    "del CSV de participantes."  
                )  
                st.write(  
                    {  
                        "Número de serie": serie\_eliminar,  
                        "Operario": valor\_registro(  
                            registro\_eliminar,  
                            "operario",  
                        ),  
                        "Cliente": valor\_registro(  
                            registro\_eliminar,  
                            "cliente",  
                        ),  
                        "Sucursal": valor\_registro(  
                            registro\_eliminar,  
                            "sucursal",  
                        ),  
                        "Categoría": valor\_registro(  
                            registro\_eliminar,  
                            "categoria",  
                        ),  
                    }  
                )  
                confirmar\_eliminacion = st.checkbox(  
                    "Confirmo que deseo eliminar esta máquina",  
                    key=(  
                        f"confirmar\_eliminar\_"  
                        f"{serie\_eliminar}"  
                    ),  
                )  
                eliminar\_maquina = st.button(  
                    "Eliminar máquina",  
                    type="primary",  
                    disabled=not confirmar\_eliminacion,  
                    use\_container\_width=True,  
                )  
                if eliminar\_maquina:  
                    clientes\_actualizados = (  
                        clientes\_edicion\[  
                            clientes\_edicion\[  
                                "numero\_serie"  
                            \]  
                            != serie\_eliminar  
                        \]  
                        .copy()  
                        .reset\_index(drop=True)  
                    )  
                    try:  
                        guardar\_cambios\_clientes(  
                            df\_clientes=clientes\_actualizados,  
                            sha=clientes\_sha,  
                            separador=separador\_csv,  
                            mensaje=(  
                                "Elimina participante "  
                                f"{serie\_eliminar}"  
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
