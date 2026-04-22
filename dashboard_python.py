from supabase import create_client
from pathlib import Path
import pandas as pd
import calendar
import streamlit as st
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import re

# ----------------
# FUNCIONES
# ----------------


def extraer_cantidad_y_texto(texto):
    if pd.isna(texto):
        return "", 1

    texto = str(texto)

    match = re.search(r"(pz|pieza|pzas)\s*[:=]?\s*(\d+)", texto.lower())

    if match:
        cantidad = int(match.group(2))

        texto_limpio = re.sub(
            r"(pz|pieza|pzas)\s*[:=]?\s*\d+",
            "",
            texto,
            flags=re.IGNORECASE
        ).strip()

        return texto_limpio, cantidad
    return texto.strip(), 1


def cargar_correctivos():
    response = supabase.table("correctivos").select("*").execute()
    df = pd.DataFrame(response.data)

    if not df.empty:
        df.columns = df.columns.str.upper()
    return df


# ------------------
# LOGIN SUPABASE
# ------------------
SUPABASE_URL = "https://glklobvwkfoijdujzsnc.supabase.co"
SUPABASE_KEY = "sb_publishable_Ib0dzKbW0r7w9ZZxLYIVKg__jEACD3o"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

ADMINS = "ethanmijail22@gmail.com"

if "user" not in st.session_state:
    st.session_state.user = None

# SELECTOR
modo = st.radio("Acceso", ["Invitado", "Admin"], horizontal=True)

if "intentos_login" not in st.session_state:
    st.session_state.intentos_login = 0

if "bloqueado" not in st.session_state:
    st.session_state.bloqueado = False
# ------------------
# MODO INVITADO
# ------------------
if modo == "Invitado":
    es_admin = False
    st.info("Modo invitado: solo visualización.")
# --------------------
# MODO ADMINISTRADOR
# --------------------
else:
    if st.session_state.bloqueado:
        st.error("Acceso Admin bloqueado. Usa modo invitado.")
        es_admin = False
        st.stop()

    if st.session_state.user is None:
        st.subheader("🔐 Login Admin")

        email = st.text_input("Correo")
        password = st.text_input("Contraseña", type="password")

        if st.button("Ingresar"):
            try:
                res = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })

                if res.user and res.user.email in ADMINS:
                    st.session_state.user = res.user
                    st.session_state.intentos_login = 0
                    st.success("Acceso concedido")
                    st.rerun()
                else:
                    raise Exception("No tienes permisos de administrador.")
            except:
                st.session_state.intentos_login += 1

                intentos_restantes = 3 - st.session_state.intentos_login

                if intentos_restantes > 0:
                    st.error(
                        f"Credenciales incorrectas. Intentos restantes: {intentos_restantes}")
                else:
                    st.session_state.bloqueado = True
                    st.error(
                        "🔒 Demasiados intentos. Solo modo invitado disponible.")
                    st.rerun()
        st.stop()
    es_admin = True

col_logout = st.columns([6, 1])[1]

with col_logout:
    if st.session_state.get("user"):
        if st.button("🔒 Salir"):
            st.session_state.user = None
            st.session_state.intentos_login = 0
            st.session_state.bloqueado = False
            st.rerun()
# ----------------------------
# EMPIEZA DASHBOARD
# ----------------------------

st.set_page_config(page_title="Dashboard de Mantenimiento", layout="wide")
st.markdown("""
<style>
    .main {
        background-color: #f7f9fc;
    }
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 1.2rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    h1, h2, h3 {
        color: #12344d;
        font-family: 'Segoe UI', sans-serif;
    }
    
    .card {
        background: white;
        padding: 18px 20px;
        border-radius: 14px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        border-left: 6px solid #0052cc;
        margin-bottom: 12px;
    }
    
    .card-title {
        font-size: 15px;
        color: #5f6b7a;
        margin-bottom: 8px;
        font-weight: 600;
    }
    .card-value {
        font-size: 34px;
        font-weight: 700;
        color: #12344d;
    }
    
    .section-box {
        background: white;
        padding: 16px;
        border-radius: 14px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        margin-bottom: 18px;
    }
</style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1.2, 4.8])

with col1:
    st.markdown("<div style='padding-top:25px'></div>", unsafe_allow_html=True)
    st.image("acciona_logo.png", width=170)

with col2:
    st.title("Dashboard de Mantenimiento")
    st.caption("MTTR / MTBF con resumen mensual y análisis por comedor")

BASE_DIR = Path(__file__).resolve().parent

ruta = BASE_DIR / "mttr_mtbf.xlsx"

# -----------------------------
# LEER ARCHIVO
# -----------------------------
df = pd.read_excel(ruta, engine="openpyxl")
# -----------------------------
# LEER ARCHIVO OTs (Maximo)
# ------------------------------
ruta_carpeta_ot = BASE_DIR / "OTS_MAXIMO"

archivos_ot = list(ruta_carpeta_ot.glob("*.xlsx"))

lista_df_ot = []

for archivo in archivos_ot:

    df_temp = pd.read_excel(archivo, engine="openpyxl")
    df_temp.columns = df_temp.columns.str.strip().str.upper()
    lista_df_ot.append(df_temp)

df_ot = pd.concat(lista_df_ot, ignore_index=True)
# -------------------------------
# LEER ARCHIVO DESDE SUPABASE
# -------------------------------
df_correctivos = cargar_correctivos()

# -------------------------------
# VALIDAR VACIO
# -------------------------------
if df_correctivos.empty:
    df_correctivos = pd.DataFrame()
    df_correctivos_abiertos = pd.DataFrame()
else:
    # ----------------------------
    # CONVERTIR FECHAS
    # ----------------------------

    df_correctivos["FECHA_INICIO"] = pd.to_datetime(
        df_correctivos["FECHA_INICIO"], errors="coerce"
    )

    df_correctivos["FECHA_CIERRE"] = pd.to_datetime(
        df_correctivos["FECHA_CIERRE"], errors="coerce"
    )

    hoy_sql = datetime.now().date().isoformat()

    # --------------------------------------
    # DETECTAR LOS QUE SE DEBEN DE ACTUALIZAR
    # --------------------------------------
    pendientes_update = df_correctivos[
        (df_correctivos["ESTATUS"] == "REALIZADO") &
        (df_correctivos["FECHA_CIERRE"].isna())
    ]
    # ---------------------
    # GUARDAR EN SUPABASE
    # ---------------------
    for _, row in pendientes_update.iterrows():
        supabase.table("correctivos").update({
            "fecha_cierre": hoy_sql
        }).eq("id", int(row["ID"])).execute()

    # ------------------------------
    # VOLVER A LEER DATOS ACTUALIZADOS
    # ------------------------------
    df_correctivos = cargar_correctivos()
    df_correctivos.columns = df_correctivos.columns.str.upper()

    # --------------------------
    # CALCULAR DIAS ABIERTOS
    # --------------------------
    hoy = pd.Timestamp.now().normalize()

    df_correctivos["FECHA_INICIO"] = pd.to_datetime(
        df_correctivos["FECHA_INICIO"], errors="coerce"
    )
    df_correctivos["FECHA_CIERRE"] = pd.to_datetime(
        df_correctivos["FECHA_CIERRE"], errors="coerce"
    )

    df_correctivos["DIAS_ABIERTOS"] = (
        (df_correctivos["FECHA_CIERRE"].fillna(hoy)
         - df_correctivos["FECHA_INICIO"])
        .dt.days
    )

    # --------------------------
    # LIMPIEZA DE TIPOS
    # ---------------------------
    if "CANTIDAD" in df_correctivos.columns:
        df_correctivos["CANTIDAD"] = pd.to_numeric(
            df_correctivos["CANTIDAD"], errors="coerce"
        )

    # --------------------------
    # FILTRAR ABIERTOS
    # --------------------------
    df_correctivos_abiertos = df_correctivos[
        df_correctivos["ESTATUS"].str.upper() != "REALIZADO"
    ].copy()

# --------------------------
# SEMAFORO TAB5 CORRECTIVOS
# --------------------------


def resaltar_dias(valor):
    if pd.isna(valor):
        return ""
    elif valor >= 30:
        return "background-color: #ff4d4f; color: white;"  # rojo
    elif valor >= 15:
        return "background-color: #faad14; color: black;"  # amarillo
    else:
        return "background-color: #52c41a; color: white;"  # verde


# CONVERTIR FECHA
df_ot["SCHEDULED FINISH"] = pd.to_datetime(
    df_ot["SCHEDULED FINISH"],
    format="%m/%d/%y %I:%M %p",
    errors="coerce"
)

# SACAR MES
meses_num = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
    5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
    9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
}

df_ot["MES"] = df_ot["SCHEDULED FINISH"].dt.month.map(meses_num)

# CLASIFICAR AREA


def clasificar_area_pcon(texto):
    texto = str(texto).upper()

    if "IFSI" in texto:
        return "SCI"
    elif "IFCO" in texto:
        return "COMEDORES"
    elif "IFDE" in texto:
        return "DESASOLVE"
    elif "IFTE" in texto:
        return "TECHOS"
    elif "IFFA" in texto:
        return "CONSERVACION"
    else:
        return "VIAS"


df_ot["AREA"] = df_ot["PCON LOCATION"].apply(clasificar_area_pcon)

df.columns = df.columns.str.strip().str.upper()

# VALIDAR QUE EXISTA COMEDOR
if "COMEDOR" not in df.columns:
    st.error(f"Columnas disponibles: {df.columns.tolist()}")
    st.stop()

# Normalizar texto
for col in ["AREA", "DESCRIPCION", "TIPO_DE_FALLA", "RESPONSABLE", "TECNICO", "COMEDOR", "MES"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.upper()

meses = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4,
    "MAYO": 5, "JUNIO": 6, "JULIO": 7, "AGOSTO": 8,
    "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12
}

df["NUM_MES"] = df["MES"].map(meses)

# -----------------------------
# FILTROS
# -----------------------------
st.sidebar.header("Filtros")


def multiselect_con_todos(label, opciones, key):
    opciones = sorted(opciones)
    opciones_con_todos = ["TODOS"] + opciones

    # Valor por defecto
    default = st.session_state.get(key, ["TODOS"])

    seleccion = st.sidebar.multiselect(
        label,
        opciones_con_todos,
        default=default,
        key=key
    )

    if "TODOS" in seleccion or not seleccion:
        return opciones
    return seleccion


# Boton para restablecer filtros
if st.sidebar.button("Restablecer filtros"):
    st.session_state["filtro_mes"] = ["TODOS"]
    st.session_state["filtro_area"] = ["TODOS"]
    st.session_state["filtro_comedor"] = ["TODOS"]
    st.rerun()

st.sidebar.divider()


# Opciones disponibles
meses_disponibles = sorted(
    df["MES"].dropna().unique(),
    key=lambda x: meses.get(x, 99)
)
areas_disponibles = sorted(df["AREA"].dropna().unique())
comedores_disponibles = sorted(df["COMEDOR"].dropna().unique())

# Filtros con opcion de TODOS
meses_sel = multiselect_con_todos(
    "Mes", meses_disponibles, "filtro_mes"
)
areas_sel = multiselect_con_todos(
    "Area", areas_disponibles, "filtro_area"
)
comedores_sel = multiselect_con_todos(
    "Comedores", comedores_disponibles, "filtro_comedor"
)

df_filtrado = df[
    df["MES"].isin(meses_sel) &
    df["AREA"].isin(areas_sel) &
    df["COMEDOR"].isin(comedores_sel)
].copy()

df_ot_filtrado = df_ot[df_ot["MES"].isin(meses_sel)].copy()

if df_filtrado.empty:
    st.warning("No hay datos con los filtros seleccionados.")
    st.stop()

# -----------------------------
# RESUMEN MENSUAL
# -----------------------------
resumen = df_filtrado.groupby(["MES", "NUM_MES"]).agg(
    FALLAS=("MES", "count"),
    tiempo_total_min=("TIEMPO_REPARACION_(MIN)", "sum")
).reset_index()

resumen["MTTR_MIN"] = resumen["tiempo_total_min"] / resumen["FALLAS"]
resumen["MTTR_HR"] = resumen["MTTR_MIN"] / 60
resumen["DIAS_MES"] = resumen["NUM_MES"].apply(
    lambda x: calendar.monthrange(2026, int(x))[1])
resumen["HORAS_OPERACION"] = resumen["DIAS_MES"] * 24
resumen["MTBF_HR"] = resumen["HORAS_OPERACION"] / resumen["FALLAS"]
resumen["MTBF_MIN"] = resumen["MTBF_HR"] * 60

resumen = resumen.sort_values("NUM_MES")

for col in ["tiempo_total_min", "MTTR_MIN", "MTTR_HR", "MTBF_HR", "MTBF_MIN"]:
    resumen[col] = resumen[col].round(2)

reporte = resumen[[
    "MES", "FALLAS", "tiempo_total_min", "MTTR_MIN", "MTTR_HR", "MTBF_HR", "MTBF_MIN"
]]

reporte["MTTR_TENDENCIA"] = reporte["MTTR_MIN"].rolling(3).mean().round(2)
reporte["MTBF_TENDENCIA"] = reporte["MTBF_MIN"].rolling(3).mean().round(2)

# -----------------------------
# KPIS GENERALES
# -----------------------------
fallas_totales = int(len(df_filtrado))
tiempo_total = float(df_filtrado["TIEMPO_REPARACION_(MIN)"].sum())
mttr_general_min = round(tiempo_total / fallas_totales, 2)

horas_operacion_total = 0
for num_mes in resumen["NUM_MES"].unique():
    dias = calendar.monthrange(2026, int(num_mes))[1]
    horas_operacion_total += dias * 24

mtbf_general_min = round((horas_operacion_total / fallas_totales) * 60, 2)

ots_area = df_ot_filtrado["AREA"].value_counts().reset_index()
ots_area.columns = ["AREA", "TOTAL_OT"]

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Resumen Ejecutivo",
    "MTTR / MTBF",
    "Órdenes de Trabajo",
    "Detalle",
    "Correctivos Abiertos"
])

with tab1:
    st.subheader("Indicadores Generales")
    k1, k2, k3, k4 = st.columns(4)
    total_ots = int(len(df_ot_filtrado))

    with k1:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Fallas totales</div>
            <div class="card-value">{fallas_totales}</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">MTTR promedio (min)</div>
            <div class="card-value">{mttr_general_min}</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">MTBF promedio (min)</div>
            <div class="card-value">{mtbf_general_min}</div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">OTs totales</div>
            <div class="card-value">{total_ots}</div>
        </div>
        """, unsafe_allow_html=True)

# Semaforo MTTR
    if mttr_general_min > 60:
        st.error("MTTR alto 🚨")
    elif mttr_general_min > 50:
        st.warning("MTTR medio ⚠️")
    else:
        st.success("MTTR controlado ✅")

# Semáforo MTBF
    if mtbf_general_min < 900:
        st.error("MTBF bajo 🚨")
    elif mtbf_general_min < 1050:
        st.warning("MTBF medio ⚠️")
    else:
        st.success("MTBF controlado ✅")

# Insights automáticos
    mes_peor_mttr = reporte.sort_values("MTTR_MIN", ascending=False).iloc[0]
    mes_peor_mtbf = reporte.sort_values("MTBF_MIN", ascending=False).iloc[0]

    st.info(
        f"El mes con mayor MTTR fue {mes_peor_mttr['MES']} con {mes_peor_mttr['MTTR_MIN']} min."
    )

    st.info(
        f"El mes con menor MTBF fue {mes_peor_mtbf['MES']} con {mes_peor_mtbf['MTBF_MIN']} min."
    )

# -----------------------------
# RESUMEN MENSUAL
# -----------------------------
with tab2:
    st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.subheader("Resumen mensual")

    st.dataframe(
        reporte,
        use_container_width=True,
        hide_index=True,
        column_config={
            "MES": st.column_config.TextColumn("Mes"),
            "FALLAS": st.column_config.NumberColumn(
                "Fallas", format="%d"
            ),
            "tiempo_total_min": st.column_config.NumberColumn(
                "Tiempo total (min)", format="%.2f"
            ),
            "MTTR_MIN": st.column_config.NumberColumn(
                "MTTR (min)", format="%.2f"
            ),
            "MTTR_HR": st.column_config.NumberColumn(
                "MTTR (hr)", format="%.2f"
            ),
            "MTBF_MIN": st.column_config.NumberColumn(
                "MTBF (min)", format="%.2f"
            ),
            "MTBF_HR": st.column_config.NumberColumn(
                "MTBF (hr)", format="%.2f"
            ),
            "MTTR_TENDENCIA": st.column_config.NumberColumn(
                "Tendencia MTTR", format="%.2f"
            ),
            "MTBF_TENDENCIA": st.column_config.NumberColumn(
                "Tendencia MTBF", format="%.2f"
            )
        }
    )

    st.markdown('</div>', unsafe_allow_html=True)
# -----------------------------
# MTTR POR ÁREA
# -----------------------------
    resumen_area = df_filtrado.groupby("AREA").agg(
        FALLAS=("AREA", "count"),
        tiempo_total_min=("TIEMPO_REPARACION_(MIN)", "sum")
    ).reset_index()

    resumen_area["MTTR_MIN"] = resumen_area["tiempo_total_min"] / \
        resumen_area["FALLAS"]
    resumen_area["MTTR_MIN"] = resumen_area["MTTR_MIN"].round(2)
    resumen_area = resumen_area.sort_values("FALLAS", ascending=False)

# -----------------------------
# MTBF POR COMEDOR
# -----------------------------
    resumen_comedor = df_filtrado.groupby("COMEDOR").agg(
        FALLAS=("COMEDOR", "count"),
        tiempo_total_min=("TIEMPO_REPARACION_(MIN)", "sum")
    ).reset_index()

    resumen_comedor["HORAS_OPERACION"] = horas_operacion_total
    resumen_comedor["MTBF_MIN"] = (
        (resumen_comedor["HORAS_OPERACION"] / resumen_comedor["FALLAS"]) * 60).round(2)
    resumen_comedor["MTTR_MIN"] = (
        resumen_comedor["tiempo_total_min"] / resumen_comedor["FALLAS"]).round(2)
    resumen_comedor = resumen_comedor.sort_values("FALLAS", ascending=False)

    st.markdown('<div class="section-box">', unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("MTTR por área")
        st.dataframe(
            resumen_area[["AREA", "FALLAS", "tiempo_total_min", "MTTR_MIN"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "AREA": st.column_config.TextColumn("Área"),
                "FALLAS": st.column_config.NumberColumn(
                    "Fallas", format="%d"
                ),
                "tiempo_total_min": st.column_config.NumberColumn(
                    "Tiempo total (min)", format="%.2f"
                ),
                "MTTR_MIN": st.column_config.NumberColumn(
                    "MTTR (min)", format="%.2f"
                )
            }
        )

    with c2:
        st.subheader("Indicadores por comedor")
        st.dataframe(
            resumen_comedor[["COMEDOR", "FALLAS", "MTTR_MIN", "MTBF_MIN"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "COMEDOR": st.column_config.TextColumn("Comedor"),
                "FALLAS": st.column_config.NumberColumn(
                    "Fallas", format="%d"
                ),
                "MTTR_MIN": st.column_config.NumberColumn(
                    "MTTR (min)", format="%.2f"
                ),
                "MTBF_MIN": st.column_config.NumberColumn(
                    "MTBF (min)", format="%.2f"
                )
            }
        )
    st.markdown('</div>', unsafe_allow_html=True)
# -----------------------------
# GRÁFICAS MÁS PEQUEÑAS
# -----------------------------
    st.markdown('<div class="section-box">', unsafe_allow_html=True)

    g1, g2 = st.columns(2)

    with g1:
        st.subheader("MTTR por mes")

        fig_mttr = px.line(
            reporte,
            x="MES",
            y=["MTTR_MIN", "MTTR_TENDENCIA"],
            markers=True,
            title="MTTR por Mes"
        )
        fig_mttr.update_layout(
            xaxis_title="Mes",
            yaxis_title="MTTR (Min)",
            template="plotly_white",
            hovermode="x unified",
            height=380,
            legend_title="Indicator"
        )
        st.plotly_chart(fig_mttr, use_container_width=True)

    with g2:
        st.subheader("MTBF por mes")

        fig_mtbf = px.line(
            reporte,
            x="MES",
            y=["MTBF_MIN", "MTBF_TENDENCIA"],
            markers=True,
            title="MTBF por Mes"
        )

        fig_mtbf.update_layout(
            xaxis_title="Mes",
            yaxis_title="MTBF (Min)",
            template="plotly_white",
            hovermode="x unified",
            height=380,
            legend_title="Indicator"
        )

        st.plotly_chart(fig_mtbf, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-box">', unsafe_allow_html=True)

    g3, g4 = st.columns(2)

    with g3:
        st.subheader("Fallas por área")

        fig_area = px.bar(
            resumen_area,
            x="AREA",
            y="FALLAS",
            text="FALLAS",
            color="AREA",
            color_discrete_sequence=px.colors.sequential.Blues,
            title="Numero de Fallas por Área"
        )

        fig_area.update_traces(textposition="outside")

        fig_area.update_layout(
            xaxis_title="Area",
            yaxis_title="Fallas",
            template="plotly_white",
            showlegend=False,
            height=380
        )

        st.plotly_chart(fig_area, use_container_width=True)

    with g4:
        st.subheader("Fallas por comedor")

        fig_comedor = px.bar(
            resumen_comedor,
            x="COMEDOR",
            y="FALLAS",
            text="FALLAS",
            color="COMEDOR",
            color_discrete_sequence=px.colors.sequential.Blues,
            title="Numero de fallas por comedor"
        )

        fig_comedor.update_traces(textposition="outside")

        fig_comedor.update_layout(
            xaxis_title="Comedor",
            yaxis_title="Fallas",
            template="plotly_white",
            showlegend=False,
            height=380
        )

        st.plotly_chart(fig_comedor, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
# -----------------------------
# GRAFICO DE DONA
# -----------------------------
with tab3:
    st.subheader("Ordenes de trabajo por area")

    st. markdown("""
    <style>
    [data-testid="stDataFrame"] td {
        font-size: 20px !important;
        font-weight: 600 !important;
    }
             
    [data-testid="stDataFrame"] th {
        font-size: 22px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-box">', unsafe_allow_html=True)

    c5, c6, = st.columns([1, 1])
    with c5:

        total = ots_area["TOTAL_OT"].sum()

        fila_total = pd.DataFrame({
            "AREA": ["TOTAL"],
            "TOTAL_OT": [total]
        })

        ots_area_final = pd.concat([ots_area, fila_total], ignore_index=True)

        def resaltar_total(row):
            if row["AREA"] == "TOTAL":
                return ["background-color: #e6f0ff; font-weight: bold"] * len(row)
            else:
                return [""] * len(row)

        tabla_ots = (
            ots_area_final.style
            .apply(resaltar_total, axis=1)
            .set_table_styles([
                {
                    "selector": "th",
                    "props": [
                        ("background-color", "#003366"),
                        ("color", "white"),
                        ("font-size", "22px"),
                        ("font-weight", "bold"),
                        ("text-align", "left")
                    ]
                },
                {
                    "selector": "td",
                    "props": [
                        ("font-size", "20px"),
                        ("font-weight", "bold")
                    ]
                }
            ])
            .hide(axis="index")
        )

        st.markdown(tabla_ots.to_html(), unsafe_allow_html=True)
    with c6:
        fig_dona = px.pie(
            ots_area,
            names="AREA",
            values="TOTAL_OT",
            hole=0.55,
            title="Distribución de OTs por área"
        )

        fig_dona.update_traces(
            textposition="inside",
            textinfo="percent+label"
        )

        fig_dona.update_layout(
            height=420,
            showlegend=True,
            legend_title="Area",
            margin=dict(t=60, b=20, l=20, r=20)
        )
        st.plotly_chart(fig_dona, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# TOP FALLAS
# -----------------------------
top_fallas = df_filtrado["TIPO_DE_FALLA"].value_counts().reset_index()
top_fallas.columns = ["TIPO_DE_FALLA", "TOTAL"]

with tab4:
    st.markdown('<div class="section-box">', unsafe_allow_html=True)

    st.subheader("Top fallas")
    st.dataframe(top_fallas, use_container_width=True)

    st.subheader("Detalle de fallas")
    st.dataframe(df_filtrado, use_container_width=True)

    st.subheader("Detalle de ordenes de trabajo")
    st.dataframe(df_ot_filtrado, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------
# CORRECTIVOS ABIERTOS
# -------------------------------
with tab5:

    if es_admin:
        st.subheader("📩 Subir archivo de Máximo")

        archivo = st.file_uploader("Carga tu CSV", type=["csv"])

        if archivo is not None:
            df_maximo = pd.read_csv(archivo)

            st.write("Vista previo:", df_maximo.head())

            # --------------------------------------
            # LIMPIAR Y MAPEAR
            # --------------------------------------
            df_maximo.columns = df_maximo.columns.str.lower().str.strip()
            df_maximo["wonum"] = df_maximo["wonum"].astype(str)

            resultado = df_maximo["longdesc"].apply(extraer_cantidad_y_texto)

            df_carga = pd.DataFrame({
                "numero_cm": df_maximo["wonum"],
                "refaccion_solicitada": resultado.apply(lambda x: x[0]),
                "cantidad": resultado.apply(lambda x: x[1]),
                "fecha_inicio": pd.to_datetime(
                    df_maximo["rptdate"], errors="coerce"
                ),
                "estatus": "PENDIENTE"
            })

            st.write("Datos listos para subir:", df_carga.head())

            # -----------------------
            # CONTROL DE BOTÓN
            # -----------------------
            if "sync_done" not in st.session_state:
                st.session_state.sync_done = False

            if st.button("🔄️ Sincronizar con sistema") and not st.session_state.sync_done:
                st.session_state.sync_done = True

                # -----------------------
                # LIMPIEZA FINAL (CLAVE)
                # -----------------------
                df_carga["numero_cm"] = df_carga["numero_cm"].astype(
                    str).str.strip().str.upper()

                df_carga["refaccion_solicitada"] = df_carga["refaccion_solicitada"].astype(
                    str)

                df_carga["cantidad"] = pd.to_numeric(
                    df_carga["cantidad"], errors="coerce"
                ).fillna(1).astype(int)

                df_carga["fecha_inicio"] = pd.to_datetime(
                    df_carga["fecha_inicio"], errors="coerce"
                )

                df_carga["fecha_inicio"] = df_carga["fecha_inicio"].dt.strftime(
                    "%Y-%m-%d")

                # -----------------------
                # CERRAR LOS QUE YA NO EXISTEN
                # -----------------------
                existentes = supabase.table(
                    "correctivos").select("numero_cm").execute()
                df_db = pd.DataFrame(existentes.data)

                if not df_db.empty:
                    df_db["numero_cm"] = df_db["numero_cm"].astype(
                        str).str.strip().str.upper()

                    set_db = set(df_db["numero_cm"])
                    set_csv = set(df_carga["numero_cm"])

                    cm_a_cerrar = set_db - set_csv

                    hoy = datetime.now().date().isoformat()

                    for cm in cm_a_cerrar:
                        supabase.table("correctivos").update({
                            "estatus": "REALIZADO",
                            "fecha_cierre": hoy
                        }).eq("numero_cm", cm).execute()
                else:
                    cm_a_cerrar = []
                # -----------------------
                # OBTENER DB ACTUAL
                # -----------------------
                existentes = supabase.table(
                    "correctivos").select("numero_cm").execute()
                df_db = pd.DataFrame(existentes.data)

                if not df_db.empty:
                    df_db["numero_cm"] = df_db["numero_cm"].astype(
                        str).str.strip().str.upper()
                    set_db = set(df_db["numero_cm"])
                else:
                    set_db = set()

                set_csv = set(df_carga["numero_cm"])

                # -----------------------
                # CERRAR LOS QUE YA NO EXISTEN
                # -----------------------
                cm_a_cerrar = set_db - set_csv

                hoy = datetime.now().date().isoformat()

                for cm in cm_a_cerrar:
                    supabase.table("correctivos").update({
                        "estatus": "REALIZADO",
                        "fecha_cierre": hoy
                    }).eq("numero_cm", cm).execute()

                # -----------------------
                # UPSERT (LA CLAVE DE TODO)
                # -----------------------
                supabase.table("correctivos").upsert(
                    df_carga.to_dict(orient="records"),
                    on_conflict="numero_cm"
                ).execute()

                # -----------------------
                # RESULTADO
                # -----------------------
                st.success(f"""
                ✅ Registros cargados: {len(df_carga)}
                ❌ CM cerrados: {len(cm_a_cerrar)}
                """)

                st.session_state.sync_done = False
                st.rerun()

    st.markdown('<div class="section-box">', unsafe_allow_html=True)
    col_ref1, col_ref2 = st.columns([1, 3])

    with col_ref1:
        if st.button("🔄️ Actualizar datos"):
            st.rerun()

    with col_ref2:
        st.caption(
            f"Ultima actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.subheader("Correctivos Abiertos")

    if not df_correctivos_abiertos.empty:
        total_correctivos = len(df_correctivos_abiertos)
        st.metric("Total de correctivos abiertos", total_correctivos)

        df_mostrar = df_correctivos_abiertos.copy()

        # ---------------------------
        # BOTONES DE ADMIN
        # ---------------------------
        if es_admin:
            st.subheader(" Gestion Manual")

            selected_cm = st.selectbox(
                "Selecciona Numero CM",
                df_mostrar["NUMERO_CM"].unique()
            )

            col1, col2 = st.columns(2)

            # Cerrar
            with col1:
                if st.button("Cerrar correctivo"):
                    supabase.table("correctivos").update({
                        "estatus": "REALIZADO",
                        "fecha_cierre": datetime.now().date().isoformat()
                    }).eq("numero_cm", selected_cm).execute()

                    st.success("Correctivo cerrado")
                    st.rerun()

            # REABRIR
            with col2:
                if st.button("Reabrir correctivo"):
                    supabase.table("correctivos").update({
                        "estatus": "PENDIENTE",
                        "fecha_cierre": None
                    }).eq("numero_cm", selected_cm).execute()

                    st.success("Correctivo reabierto")
                    st.rerun()

        # SEMAFORO
        df_mostrar["SEMAFORO"] = df_mostrar["DIAS_ABIERTOS"].apply(
            lambda x: "‼️" if x >= 30 else "⚠️" if x >= 15 else "✅"
        )

        # ORDENAR
        df_mostrar = df_mostrar.sort_values(
            by="DIAS_ABIERTOS",
            ascending=False,
            na_position="last"
        )

        st.markdown("""
        <style>
        
        /* Lineas tipo tabla */
        .fila {
            border-bottom: 1px solid #e6e6e6;
            padding: 6px 0;
        }
        
        /* Encabezados */
        .header {
            font-weight: 700;
            border-bottom: 2px solid #cfcfcf;
            padding-bottom: 6px;
            margin-bottom: 4px;
        }
        
        /* Numeros grandes (cantidad y dias) */
        .big-number {
            font-size: 20 px;
            font-weight: 700;
            color: #1a1a1a;
        }
        
        /* Iconos mas pequeños */
        .small-btn button{
            font-size: 12px !important;
            padding: 4px 6px !important;
            height: 28px !important;
            width: 28px !important;
        }
        
        </style>
        """, unsafe_allow_html=True)

        # -------------------
        # ENCABEZADOS NUEVOS
        # -------------------
        h1, h2, h3, h4, h5, h6, h7, h8 = st.columns([2, 4, 1, 2, 1, 1, 1, 1])

        h1.markdown('<div class="header">CM</div>', unsafe_allow_html=True)
        h2.markdown('<div class="header">Refacción</div>',
                    unsafe_allow_html=True)
        h3.markdown('<div class="header">Cantidad</div>',
                    unsafe_allow_html=True)
        h4.markdown('<div class="header">Días</div>', unsafe_allow_html=True)
        h5.markdown('<div class="header">Estado</div>', unsafe_allow_html=True)
        h6.markdown('<div class="header">Acciona</div>',
                    unsafe_allow_html=True)
        h7.markdown('<div class="header">Ford</div>', unsafe_allow_html=True)
        h8.markdown('<div class="header">Proveedor</div>',
                    unsafe_allow_html=True)

        st.divider()

        for _, row in df_mostrar.iterrows():

            cm = row["NUMERO_CM"]
            responsable_actual = str(row.get("RESPONSABLE", "")).upper()

            col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(
                [2, 4, 1, 2, 1, 1, 1, 1])

            with col1:
                st.write(cm)

            with col2:
                st.write(row.get("REFACCION_SOLICITADA", ""))

            with col3:
                st.markdown(
                    f'<div class="big-number">{int(row.get("CANTIDAD", 0))}</div>', unsafe_allow_html=True)

            with col4:
                st.markdown(
                    f'<div class="big-number">{int(row.get("DIAS_ABIERTOS", 0))}</div>', unsafe_allow_html=True)

            with col5:
                st.write(row.get("SEMAFORO", ""))

            # --------------------
            # FUNCION PARA GUARDAR
            # --------------------
            def actualizar_responsable(valor):
                supabase.table("correctivos").update({
                    "responsable": valor
                }).eq("numero_cm", cm).execute()
                st.rerun()

            def boton(valor):
                activo = responsable_actual == valor

                if es_admin:
                    with st.container():
                        st.markdown('<div class="small-btn">',
                                    unsafe_allow_html=True)
                        if st.button("🟢" if activo else "⚪", key=f"{cm}_{valor}"):
                            actualizar_responsable(valor)
                        st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.write("🟢" if activo else "⚪")

            with col6:
                boton("ACCIONA")

            with col7:
                boton("CLIENTE FORD")

            with col8:
                boton("PROVEEDOR")
    else:
        st.info("No hay correctivos abiertos.")

    st.markdown('</div>', unsafe_allow_html=True)
