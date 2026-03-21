import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import date, timedelta
import requests
import numpy as np

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
SPREADSHEET_ID = "1qhdazuPU5B36vwRyc8Be3h9fgXok1dSuDT8mvMBD2eI"
SHEET_NAME     = "Resultados Shopee"
SCOPES         = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

st.set_page_config(
    page_title="Dashboard de Performance",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #0f0d0b !important;
    color: #f6e8d8 !important;
}
[data-testid="stAppViewContainer"] {
    background-image: url("https://raw.githubusercontent.com/brennoeccard/dashboard-performance-shopee/main/logo_bg.png");
    background-repeat: no-repeat;
    background-position: center center;
    background-size: 35%;
    background-attachment: fixed;
}
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(15,13,11,0.94);
    z-index: 0;
    pointer-events: none;
}
[data-testid="stMain"] { position: relative; z-index: 1; }
[data-testid="stSidebar"] {
    background-color: #110e0c !important;
    border-right: 1px solid #3a2c28 !important;
}
[data-testid="stSidebar"] * { color: #f6e8d8 !important; }
[data-testid="stSidebar"] button {
    background-color: #3a2c28 !important;
    color: #f6e8d8 !important;
    border: 1px solid #bd6d34 !important;
}
[data-testid="stSidebar"] button:hover { background-color: #bd6d34 !important; }
.main { background-color: #0f0d0b; }
.metric-card {
    background: linear-gradient(135deg, #1e1410, #221a16);
    border-radius: 12px;
    padding: 16px 20px;
    border-left: 4px solid #bd6d34;
    margin-bottom: 4px;
}
.metric-card.green  { border-left-color: #7a9e4e; }
.metric-card.red    { border-left-color: #c0392b; }
.metric-card.yellow { border-left-color: #d4a017; }
.metric-card.purple { border-left-color: #9c5834; }
.metric-card.orange { border-left-color: #bd6d34; }
.metric-label { color: #c5936d; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
.metric-value { color: #f6e8d8; font-size: 22px; font-weight: 700; margin-top: 4px; }
.metric-delta-pos { color: #7a9e4e; font-size: 11px; margin-top: 2px; }
.metric-delta-neg { color: #c0392b; font-size: 11px; margin-top: 2px; }
.metric-delta-neu { color: #c5936d; font-size: 11px; margin-top: 2px; }
.section-title {
    color: #f6e8d8;
    font-size: 18px;
    font-weight: 600;
    margin: 24px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #3a2c28;
}
.canal-card {
    background: linear-gradient(135deg, #1e1410, #221a16);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 8px;
    border: 1px solid #3a2c28;
}
.canal-title { color: #bd6d34; font-size: 14px; font-weight: 700; margin-bottom: 8px; }
.canal-metric { color: #c5936d; font-size: 11px; }
.canal-value { color: #f6e8d8; font-size: 18px; font-weight: 600; }
.alert-banner {
    background: linear-gradient(135deg, #2d1010, #3d1515);
    border: 1px solid #c0392b;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 16px;
    color: #e74c3c;
    font-weight: 600;
}
.footer {
    margin-top: 40px;
    padding: 20px;
    border-top: 1px solid #3a2c28;
    text-align: center;
    color: #c5936d;
    font-size: 12px;
}
[data-testid="stExpander"] {
    background-color: #1a1210 !important;
    border: 1px solid #3a2c28 !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] summary {
    color: #c5936d !important;
    font-size: 13px !important;
}
input[type="text"], [data-testid="stDateInput"] input {
    background-color: #1a1210 !important;
    color: #f6e8d8 !important;
    border-color: #3a2c28 !important;
    font-size: 12px !important;
}
[data-testid="stDateInput"] {
    background-color: #1a1210 !important;
}
</style>
""", unsafe_allow_html=True)

PLOTLY_THEME = dict(
    plot_bgcolor="#0f0d0b",
    paper_bgcolor="#0f0d0b",
    font_color="#f6e8d8",
    title_font_color="#f6e8d8",
    legend=dict(font=dict(color="#f6e8d8", size=12),
                bgcolor="rgba(30,18,16,0.8)",
                bordercolor="#3a2c28", borderwidth=1),
    xaxis=dict(color="#c5936d", gridcolor="#2a1f1a"),
    yaxis=dict(color="#c5936d", gridcolor="#2a1f1a"),
)

# ─────────────────────────────────────────────
#  LOGIN
# ─────────────────────────────────────────────
def check_login():
    try:
        users = dict(st.secrets["users"])
    except Exception:
        users = {"brenno": "destr@vA!"}

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        col1, col2, col3 = st.columns([1, 1.2, 1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("""
            <div style='text-align:center; margin-bottom:24px; padding:24px;
                        background:linear-gradient(135deg,#1a1210,#221a16);
                        border-radius:16px; border:1px solid #3a2c28;'>
                <div style='font-size:48px;'>🔓</div>
                <h2 style='color:#f6e8d8; margin:8px 0 4px 0; font-size:28px;'>DESTRAVA</h2>
                <p style='color:#bd6d34; margin:0; font-size:13px;'>por Carol Matos · Analytics</p>
            </div>
            """, unsafe_allow_html=True)
            with st.form("login_form"):
                usuario = st.text_input("Utilizador", placeholder="ex: brenno")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Entrar", use_container_width=True)
                if submitted:
                    if usuario in users and users[usuario] == password:
                        st.session_state.logged_in = True
                        st.session_state.usuario = usuario
                        st.rerun()
                    else:
                        st.error("Utilizador ou password incorrectos.")
        return False
    return True

# ─────────────────────────────────────────────
#  GOOGLE AUTH
# ─────────────────────────────────────────────
@st.cache_resource
def autenticar():
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    except Exception:
        creds = Credentials.from_service_account_file(
            "/Users/anacarol/automacao/automacao-planilhas-490816-ee73c7ff4bf2.json", scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)

# ─────────────────────────────────────────────
#  LER DADOS
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def ler_dados():
    service = autenticar()
    resultado = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_NAME}!A1:P").execute()
    valores = resultado.get("values", [])
    if len(valores) < 2:
        return pd.DataFrame()
    cabecalho = valores[0]
    linhas = valores[1:]
    max_cols = len(cabecalho)
    linhas_norm = [l + [""] * (max_cols - len(l)) for l in linhas]
    df = pd.DataFrame(linhas_norm, columns=cabecalho)
    col_map = {df.columns[0]:"Data", df.columns[1]:"Sub_id2", df.columns[2]:"Sub_id1",
               df.columns[3]:"Sub_id3", df.columns[4]:"Cliques", df.columns[5]:"Vendas",
               df.columns[6]:"CTR", df.columns[7]:"Comissao", df.columns[8]:"Investimento",
               df.columns[9]:"Impressoes", df.columns[10]:"Alcance", df.columns[11]:"Cliques_Meta",
               df.columns[12]:"CTR_Meta", df.columns[13]:"CTR_Geral",
               df.columns[14]:"Lucro", df.columns[15]:"ROI"}
    df = df.rename(columns=col_map)
    def to_num(col):
        return pd.to_numeric(
            df[col].astype(str).str.replace("R\\$","",regex=True).str.replace("%","")
                   .str.replace("\\.","",regex=True).str.replace(",",".").str.strip(),
            errors="coerce").fillna(0)
    for col in ["Cliques","Vendas","Comissao","Investimento","Impressoes","Alcance","Cliques_Meta","Lucro","ROI"]:
        df[col] = to_num(col)
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["Data"])
    df["Sub_id2"] = df["Sub_id2"].fillna("").str.strip()
    df["Sub_id1"] = df["Sub_id1"].fillna("").str.strip()
    df["Sub_id3"] = df["Sub_id3"].fillna("").str.strip()
    return df

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def fmt_brl(val):
    return "R$ {:,.2f}".format(val).replace(",","X").replace(".",",").replace("X",".")

def fmt_pct(val):
    return "{:.2f}%".format(val).replace(".",",")

def fmt_num(val):
    return "{:,}".format(int(val)).replace(",",".")

def card(label, value, color="blue", delta_html_str="", sparkline_fig=None):
    html = (
        '<div class="metric-card ' + color + '">'
        '<div class="metric-label">' + label + '</div>'
        '<div class="metric-value">' + str(value) + '</div>'
        + (delta_html_str if delta_html_str else "") +
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    if sparkline_fig:
        st.plotly_chart(sparkline_fig, use_container_width=True, config={"displayModeBar": False})

def calcular(df):
    cliques = df["Cliques"].sum()
    vendas = df["Vendas"].sum()
    comissao = df["Comissao"].sum()
    invest = df["Investimento"].sum()
    impressoes = df["Impressoes"].sum()
    alcance = df["Alcance"].sum()
    cliques_meta = df["Cliques_Meta"].sum()
    lucro_total = comissao - invest
    lucro_camp = df[df["Sub_id2"].str.lower()=="pago"]["Comissao"].sum() - invest
    roi = (comissao - invest) / invest if invest > 0 else 0
    ctr_shopee = (vendas / cliques * 100) if cliques > 0 else 0
    ctr_meta = (cliques_meta / alcance * 100) if alcance > 0 else 0
    ctr_cv = (vendas / cliques_meta * 100) if cliques_meta > 0 else 0
    freq = impressoes / alcance if alcance > 0 else 0
    cpm_imp = (invest / impressoes * 1000) if impressoes > 0 else 0
    cpm_alc = (invest / alcance * 1000) if alcance > 0 else 0
    cpc = invest / cliques_meta if cliques_meta > 0 else 0
    cac = invest / vendas if vendas > 0 else 0
    return dict(cliques=cliques, vendas=vendas, comissao=comissao, invest=invest,
                impressoes=impressoes, alcance=alcance, cliques_meta=cliques_meta,
                lucro_total=lucro_total, lucro_camp=lucro_camp, roi=roi,
                ctr_shopee=ctr_shopee, ctr_meta=ctr_meta, ctr_cv=ctr_cv,
                freq=freq, cpm_imp=cpm_imp, cpm_alc=cpm_alc, cpc=cpc, cac=cac)

def sparkline(df_d, col, color="#bd6d34"):
    df14 = df_d.tail(14)
    fig = go.Figure(go.Scatter(
        x=df14["Data"], y=df14[col],
        mode="lines", line=dict(color=color, width=1.5),
        fill="tozeroy", fillcolor="rgba(189,109,52,0.15)",
    ))
    fig.update_layout(height=50, margin=dict(l=0,r=0,t=0,b=0),
                      xaxis=dict(visible=False), yaxis=dict(visible=False),
                      plot_bgcolor="#0f0d0b", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
    return fig

def delta_html(val, ref):
    if not ref or ref == 0:
        return '<span class="metric-delta-neu">sem ref. anterior</span>'
    pct = (val - ref) / abs(ref) * 100
    if pct > 0:
        return '<span class="metric-delta-pos">▲ {:.1f}% vs semana ant.</span>'.format(pct)
    elif pct < 0:
        return '<span class="metric-delta-neg">▼ {:.1f}% vs semana ant.</span>'.format(abs(pct))
    return '<span class="metric-delta-neu">= igual semana ant.</span>'

def semana_anterior(df, d_ini, d_fim):
    delta = d_fim - d_ini
    ant_fim = d_ini - timedelta(days=1)
    ant_ini = ant_fim - delta
    return df[(df["Data"].dt.date >= ant_ini) & (df["Data"].dt.date <= ant_fim)]

def verificar_alerta_roi(df):
    df_pago = df[df["Sub_id2"].str.lower()=="pago"].copy()
    if df_pago.empty: return False
    df_d = df_pago.groupby("Data").agg(C=("Comissao","sum"), I=("Investimento","sum")).reset_index().sort_values("Data").tail(3)
    df_d["ROI"] = (df_d["C"] - df_d["I"]) / df_d["I"].replace(0, np.nan)
    return (df_d["ROI"] < 0).all()

def funil_ctr(m, m_ant, m_all, num, den, label_n, label_d):
    cur = m[num] / m[den] * 100 if m[den] > 0 else 0
    ant = m_ant[num] / m_ant[den] * 100 if m_ant and m_ant[den] > 0 else None
    ini = m_all[num] / m_all[den] * 100 if m_all and m_all[den] > 0 else None
    return cur, ant, ini

# ─────────────────────────────────────────────
#  APP
# ─────────────────────────────────────────────
def main():
    if not check_login():
        return

    with st.sidebar:
        # Atalhos no topo
        st.markdown('<div style="color:#c5936d;font-size:11px;font-weight:600;margin-bottom:8px;">ATALHOS</div>', unsafe_allow_html=True)
        st.markdown("""
        <a href="#evolucao" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">📈 Evolucao Temporal</a>
        <a href="#canais" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">📊 Comparacao Canais</a>
        <a href="#campeoes" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">🏆 Itens Campeoes</a>
        <a href="#funil" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">🔽 Funil de Conversao</a>
        <a href="#metricas-pago" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">📉 Metricas Pago</a>
        <a href="#insights-ia" style="display:block;color:#bd6d34;font-size:12px;text-decoration:none;background:#2a1f1a;padding:6px 12px;border-radius:8px;border:1px solid #bd6d34;margin-bottom:4px;text-align:center;">🤖 Insights IA</a>
        """, unsafe_allow_html=True)
        # Utilizador e acções em baixo
        st.markdown("---")
        st.markdown('<div style="color:#c5936d;font-size:11px;">👤 {}</div>'.format(
            st.session_state.get("usuario","")), unsafe_allow_html=True)
        if st.button("🔄 Actualizar dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    st.markdown("""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:8px;">
        <div>
            <h1 style="color:#f6e8d8;margin:0;font-size:28px;">📊 Dashboard de Performance</h1>
            <p style="color:#c5936d;margin:0;font-size:13px;">Destrava · por Carol Matos</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Anchor bar
    st.markdown("""
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:16px;
                padding:8px 16px;background:#1a1210;border-radius:8px;border:1px solid #3a2c28;">
        <span style="color:#c5936d;font-size:11px;font-weight:600;">IR PARA:</span>
        <a href="#evolucao" style="color:#c5936d;font-size:11px;text-decoration:none;background:#1a1210;padding:3px 10px;border-radius:20px;border:1px solid #3a2c28;">📈 Evolucao</a>
        <a href="#canais" style="color:#c5936d;font-size:11px;text-decoration:none;background:#1a1210;padding:3px 10px;border-radius:20px;border:1px solid #3a2c28;">📊 Canais</a>
        <a href="#campeoes" style="color:#c5936d;font-size:11px;text-decoration:none;background:#1a1210;padding:3px 10px;border-radius:20px;border:1px solid #3a2c28;">🏆 Campeoes</a>
        <a href="#funil" style="color:#c5936d;font-size:11px;text-decoration:none;background:#1a1210;padding:3px 10px;border-radius:20px;border:1px solid #3a2c28;">🔽 Funil</a>
        <a href="#metricas-pago" style="color:#c5936d;font-size:11px;text-decoration:none;background:#1a1210;padding:3px 10px;border-radius:20px;border:1px solid #3a2c28;">📉 Metricas Pago</a>
        <a href="#insights-ia" style="color:#bd6d34;font-size:11px;text-decoration:none;background:#2a1f1a;padding:3px 10px;border-radius:20px;border:1px solid #bd6d34;">🤖 Insights IA</a>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("A carregar dados..."):
        df_raw = ler_dados()

    if df_raw.empty:
        st.error("Sem dados. Verifica a planilha.")
        return

    # ── FILTROS ──
    data_min = df_raw["Data"].min().date()
    data_max = df_raw["Data"].max().date()
    hoje = date.today()

    if "preset" not in st.session_state:
        st.session_state.preset = "all"

    preset = st.session_state.get("preset", "all")
    if preset == "hoje":      d_ini_def, d_fim_def = hoje, hoje
    elif preset == "ontem":   d_ini_def, d_fim_def = hoje - timedelta(days=1), hoje - timedelta(days=1)
    elif preset == "7d":      d_ini_def, d_fim_def = data_max - timedelta(days=6), data_max
    elif preset == "14d":     d_ini_def, d_fim_def = data_max - timedelta(days=13), data_max
    elif preset == "28d":     d_ini_def, d_fim_def = data_max - timedelta(days=27), data_max
    elif preset == "30d":     d_ini_def, d_fim_def = data_max - timedelta(days=29), data_max
    else:                     d_ini_def, d_fim_def = data_min, data_max

    sid2_opts = sorted([x for x in df_raw["Sub_id2"].unique() if x.strip()])
    sid1_opts = sorted([x for x in df_raw["Sub_id1"].unique() if x.strip()])
    sid3_opts = sorted([x for x in df_raw["Sub_id3"].unique() if x.strip()])

    with st.expander("🎛️ Filtros", expanded=False):
        st.markdown('<div style="color:#bd6d34;font-size:12px;font-weight:700;margin-bottom:6px;">📅 Periodo</div>', unsafe_allow_html=True)
        b1,b2,b3,b4,b5,b6,b7 = st.columns(7)
        with b1:
            if st.button("Hoje",    use_container_width=True, key="bh"):  st.session_state.preset="hoje";  st.rerun()
        with b2:
            if st.button("Ontem",   use_container_width=True, key="bo"):  st.session_state.preset="ontem"; st.rerun()
        with b3:
            if st.button("7 dias",  use_container_width=True, key="b7"):  st.session_state.preset="7d";    st.rerun()
        with b4:
            if st.button("14 dias", use_container_width=True, key="b14"): st.session_state.preset="14d";   st.rerun()
        with b5:
            if st.button("28 dias", use_container_width=True, key="b28"): st.session_state.preset="28d";   st.rerun()
        with b6:
            if st.button("30 dias", use_container_width=True, key="b30"): st.session_state.preset="30d";   st.rerun()
        with b7:
            if st.button("Tudo",    use_container_width=True, key="ba"):  st.session_state.preset="all";   st.rerun()

        datas = st.date_input("", value=(d_ini_def, d_fim_def), min_value=data_min, max_value=data_max, label_visibility="collapsed")
        if isinstance(datas, tuple) and len(datas) == 2:
            d_ini, d_fim = datas
        else:
            d_ini, d_fim = d_ini_def, d_fim_def

        st.markdown("<hr style='border-color:#3a2c28;margin:10px 0;'>", unsafe_allow_html=True)
        st.markdown('<div style="color:#bd6d34;font-size:12px;font-weight:700;margin-bottom:4px;">Canal (Sub_id2)</div>', unsafe_allow_html=True)
        sid2_sel = st.multiselect("", sid2_opts, default=[], placeholder="Todos os canais", label_visibility="collapsed", key="ms2")

        st.markdown("<hr style='border-color:#3a2c28;margin:10px 0;'>", unsafe_allow_html=True)
        st.markdown('<div style="color:#bd6d34;font-size:12px;font-weight:700;margin-bottom:4px;">Sub_id1</div>', unsafe_allow_html=True)
        sid1_sel = st.multiselect("", sid1_opts, default=[], placeholder="Todos", label_visibility="collapsed", key="ms1")

        st.markdown("<hr style='border-color:#3a2c28;margin:10px 0;'>", unsafe_allow_html=True)
        st.markdown('<div style="color:#bd6d34;font-size:12px;font-weight:700;margin-bottom:4px;">Sub_id3</div>', unsafe_allow_html=True)
        sid3_sel = st.multiselect("", sid3_opts, default=[], placeholder="Todos", label_visibility="collapsed", key="ms3")

    if not sid2_sel: sid2_sel = sid2_opts
    if not sid1_sel: sid1_sel = sid1_opts
    if not sid3_sel: sid3_sel = sid3_opts

    mask = ((df_raw["Data"].dt.date >= d_ini) & (df_raw["Data"].dt.date <= d_fim))
    if sid2_sel != sid2_opts: mask = mask & df_raw["Sub_id2"].isin(sid2_sel)
    if sid1_sel != sid1_opts: mask = mask & df_raw["Sub_id1"].isin(sid1_sel)
    if sid3_sel != sid3_opts: mask = mask & df_raw["Sub_id3"].isin(sid3_sel)
    df = df_raw[mask].copy()
    df_viz = df[df["Sub_id2"].str.strip() != ""].copy()
    df_ant = semana_anterior(df_raw, d_ini, d_fim)

    if df.empty:
        st.warning("Sem dados para os filtros seleccionados.")
        return

    m     = calcular(df)
    m_ant = calcular(df_ant) if not df_ant.empty else None
    df_pago  = df[df["Sub_id2"].str.lower()=="pago"]
    df_org   = df[df["Sub_id2"].str.lower()=="organico"]
    df_story = df[df["Sub_id2"].str.lower()=="story"]
    m_pago   = calcular(df_pago)  if len(df_pago)  > 0 else None
    m_org    = calcular(df_org)   if len(df_org)   > 0 else None
    m_story  = calcular(df_story) if len(df_story) > 0 else None

    df_daily = df.groupby("Data").agg(
        Vendas=("Vendas","sum"), Comissao=("Comissao","sum"),
        Cliques=("Cliques","sum"), Investimento=("Investimento","sum"),
    ).reset_index().sort_values("Data")
    df_daily["ROI_calc"] = df_daily.apply(
        lambda r: (r["Comissao"]-r["Investimento"])/r["Investimento"] if r["Investimento"]>0 else 0, axis=1)
    df_daily["CTR_calc"] = df_daily.apply(
        lambda r: r["Vendas"]/r["Cliques"]*100 if r["Cliques"]>0 else 0, axis=1)

    # ── ALERTA ROI ──
    if verificar_alerta_roi(df):
        st.markdown('<div class="alert-banner">⚠️ ALERTA: ROI negativo nos ultimos 3 dias consecutivos na campanha paga!</div>', unsafe_allow_html=True)

    # ── KPIs GERAIS ──
    st.markdown('<div class="section-title">💰 KPIs Gerais</div>', unsafe_allow_html=True)
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    m_ant_v = m_ant if m_ant else {}
    with c1:
        card("Comissao Total", fmt_brl(m["comissao"]), "blue",
             delta_html(m["comissao"], m_ant_v.get("comissao",0)),
             sparkline(df_daily,"Comissao","#bd6d34"))
    with c2:
        cor = "green" if m["lucro_total"]>=0 else "red"
        card("Lucro Total", fmt_brl(m["lucro_total"]), cor,
             delta_html(m["lucro_total"], m_ant_v.get("lucro_total",0)),
             sparkline(df_daily,"Comissao","#9c5834"))
    with c3:
        roi_val = m["roi"]
        cor_roi = "green" if roi_val>1 else ("yellow" if roi_val>=0 else "red")
        card("ROI", "{:.2f}".format(roi_val), cor_roi, "",
             sparkline(df_daily,"ROI_calc","#d4a017"))
    with c4:
        card("Vendas", fmt_num(m["vendas"]), "purple",
             delta_html(m["vendas"], m_ant_v.get("vendas",0)),
             sparkline(df_daily,"Vendas","#9c5834"))
    with c5:
        card("Cliques Shopee", fmt_num(m["cliques"]), "yellow",
             delta_html(m["cliques"], m_ant_v.get("cliques",0)),
             sparkline(df_daily,"Cliques","#d2b095"))
    with c6:
        card("CTR Shopee", fmt_pct(m["ctr_shopee"]), "blue", "",
             sparkline(df_daily,"CTR_calc","#bd6d34"))

    # ── KPIs POR CANAL ──
    st.markdown('<div class="section-title">📂 Performance por Canal</div>', unsafe_allow_html=True)
    cc1,cc2,cc3 = st.columns(3)

    def canal_card(col, mc, mc_ant, nome, emoji):
        with col:
            if mc:
                def trend(cur, a):
                    if not mc_ant or a==0: return ""
                    pct = (cur-a)/abs(a)*100
                    cor = "#7a9e4e" if pct>0 else "#c0392b"
                    arr = "▲" if pct>0 else "▼"
                    return '<span style="color:{};font-size:10px;">{} {:.1f}%</span>'.format(cor, arr, abs(pct))
                a = mc_ant if mc_ant else {}
                st.markdown("""
                <div class="canal-card">
                    <div class="canal-title">{emoji} {nome}</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                        <div><div class="canal-metric">Vendas</div>
                             <div class="canal-value">{v}</div>{tv}</div>
                        <div><div class="canal-metric">Comissao</div>
                             <div class="canal-value">{c}</div>{tc}</div>
                        <div><div class="canal-metric">Cliques</div>
                             <div class="canal-value">{cl}</div></div>
                        <div><div class="canal-metric">CTR</div>
                             <div class="canal-value">{ctr}</div></div>
                    </div>
                </div>""".format(
                    emoji=emoji, nome=nome,
                    v=fmt_num(mc["vendas"]), tv=trend(mc["vendas"], a.get("vendas",0)),
                    c=fmt_brl(mc["comissao"]), tc=trend(mc["comissao"], a.get("comissao",0)),
                    cl=fmt_num(mc["cliques"]), ctr=fmt_pct(mc["ctr_shopee"])
                ), unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="canal-card">
                    <div class="canal-title">{} {}</div>
                    <div style="color:#8892a4;">Sem dados no periodo</div>
                </div>""".format(emoji, nome), unsafe_allow_html=True)

    df_ant_pago  = df_ant[df_ant["Sub_id2"].str.lower()=="pago"]  if not df_ant.empty else pd.DataFrame()
    df_ant_org   = df_ant[df_ant["Sub_id2"].str.lower()=="organico"] if not df_ant.empty else pd.DataFrame()
    df_ant_story = df_ant[df_ant["Sub_id2"].str.lower()=="story"]  if not df_ant.empty else pd.DataFrame()
    m_ant_pago   = calcular(df_ant_pago)  if not df_ant_pago.empty  else None
    m_ant_org    = calcular(df_ant_org)   if not df_ant_org.empty   else None
    m_ant_story  = calcular(df_ant_story) if not df_ant_story.empty else None

    canal_card(cc1, m_pago,  m_ant_pago,  "Pago",     "📣")
    canal_card(cc2, m_org,   m_ant_org,   "Organico", "🌱")
    canal_card(cc3, m_story, m_ant_story, "Story",    "📖")

    # ── KPIs CAMPANHA PAGO ──
    if m_pago:
        st.markdown('<div class="section-title">📣 KPIs Campanha (Pago)</div>', unsafe_allow_html=True)
        lucro_camp = m_pago["comissao"] - m_pago["invest"]
        roi_camp = (m_pago["comissao"]-m_pago["invest"])/m_pago["invest"] if m_pago["invest"]>0 else 0
        cor_roi = "green" if roi_camp>1 else ("yellow" if roi_camp>=0 else "red")
        k1,k2,k3,k4 = st.columns(4)
        with k1: card("Vendas Pago",    fmt_num(m_pago["vendas"]),   "purple")
        with k2: card("Comissao Pago",  fmt_brl(m_pago["comissao"]), "blue")
        with k3: card("Investimento",   fmt_brl(m_pago["invest"]),   "red")
        with k4: card("Lucro Campanha", fmt_brl(lucro_camp), cor_roi)
        k5,k6,k7,k8,k9 = st.columns(5)
        with k5: card("CPM Impressoes", fmt_brl(m_pago["cpm_imp"]),  "yellow")
        with k6: card("CPM Alcance",    fmt_brl(m_pago["cpm_alc"]),  "yellow")
        with k7: card("CPC",            fmt_brl(m_pago["cpc"]),      "blue")
        with k8: card("CAC",            fmt_brl(m_pago["cac"]),      "purple")
        with k9: card("Frequencia",     "{:.2f}x".format(m_pago["freq"]), "orange")

    st.markdown("---")

    # ── EVOLUCAO TEMPORAL ──
    st.markdown('<div id="evolucao" class="section-title">📈 Evolucao Temporal</div>', unsafe_allow_html=True)
    metricas_disp = {"Comissao":"Comissao","Vendas":"Vendas","Cliques Shopee":"Cliques","Investimento":"Investimento"}
    col_sel = st.multiselect("Metricas para cruzar", list(metricas_disp.keys()), default=["Comissao","Vendas"])
    if col_sel:
        fig_linha = go.Figure()
        cores = ["#bd6d34","#c5936d","#d2b095","#9c5834","#562d1d"]
        for i, nome in enumerate(col_sel):
            col_real = metricas_disp[nome]
            cor = cores[i % len(cores)]
            fig_linha.add_trace(go.Scatter(x=df_daily["Data"], y=df_daily[col_real],
                name=nome, mode="lines+markers", line=dict(color=cor, width=2), marker=dict(size=4)))
            mm7 = df_daily[col_real].rolling(7, min_periods=1).mean()
            fig_linha.add_trace(go.Scatter(x=df_daily["Data"], y=mm7,
                name=nome+" MM7", mode="lines", line=dict(color=cor, width=1, dash="dash"), opacity=0.6))
        fig_linha.update_layout(title="Evolucao + Media Movel 7 dias", hovermode="x unified", **PLOTLY_THEME)
        st.plotly_chart(fig_linha, use_container_width=True)

    # ── COMPARACAO POR CANAL ──
    st.markdown('<div id="canais" class="section-title">📊 Comparacao por Canal</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    df_canal = df_viz.groupby("Sub_id2").agg(Vendas=("Vendas","sum"), Comissao=("Comissao","sum"), Cliques=("Cliques","sum")).reset_index()
    with col1:
        fig_bar = px.bar(df_canal, x="Sub_id2", y="Comissao", title="Comissao por Canal",
                         color="Sub_id2", text="Comissao",
                         color_discrete_sequence=["#bd6d34","#9c5834","#c5936d","#d2b095"])
        fig_bar.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
        fig_bar.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig_bar, use_container_width=True)
    with col2:
        fig_pizza = px.pie(df_canal, names="Sub_id2", values="Vendas", title="Distribuicao de Vendas",
                           color_discrete_sequence=["#bd6d34","#9c5834","#c5936d"])
        fig_pizza.update_traces(textinfo="percent+label")
        fig_pizza.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig_pizza, use_container_width=True)

    # ── ITENS CAMPEOES ──
    st.markdown('<div id="campeoes" class="section-title">🏆 Itens Campeoes</div>', unsafe_allow_html=True)
    df_sid3 = df[df["Sub_id3"]!=""].groupby("Sub_id3").agg(
        Comissao=("Comissao","sum"), Vendas=("Vendas","sum"), Cliques=("Cliques","sum")).reset_index()
    df_sid3["CTR"] = (df_sid3["Vendas"]/df_sid3["Cliques"]*100).fillna(0)

    col1,col2 = st.columns(2)
    with col1:
        top5 = df_sid3.nlargest(5,"Comissao").copy()
        top5["label"] = top5.apply(lambda r: "R$ {:,.2f} | {:,.0f} vendas | CTR {:.1f}%".format(r["Comissao"],r["Vendas"],r["CTR"]), axis=1)
        fig = px.bar(top5, x="Comissao", y="Sub_id3", orientation="h",
                     title="Top 5 por Comissao", text="label",
                     color_discrete_sequence=["#9c5834"],
                     hover_data={"Vendas":True,"CTR":":.2f"})
        fig.update_traces(textposition="outside")
        fig.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        top5v = df_sid3.nlargest(5,"Vendas")
        fig = px.bar(top5v, x="Vendas", y="Sub_id3", orientation="h",
                     title="Top 5 por Vendas", text="Vendas",
                     color_discrete_sequence=["#c5936d"])
        fig.update_traces(texttemplate="%{text:.0f}", textposition="outside")
        fig.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig, use_container_width=True)

    col3,col4 = st.columns(2)
    with col3:
        top5c = df_sid3.nlargest(5,"Cliques")
        fig = px.bar(top5c, x="Cliques", y="Sub_id3", orientation="h",
                     title="Top 5 por Cliques", text="Cliques",
                     color_discrete_sequence=["#d2b095"])
        fig.update_traces(texttemplate="%{text:.0f}", textposition="outside")
        fig.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig, use_container_width=True)
    with col4:
        top5ctr = df_sid3.nlargest(5,"CTR")
        fig = px.bar(top5ctr, x="CTR", y="Sub_id3", orientation="h",
                     title="Top 5 por CTR (%)", text="CTR",
                     color_discrete_sequence=["#bd6d34"])
        fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
        fig.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig, use_container_width=True)

    # ── SCATTER ──
    st.markdown('<div class="section-title">🔍 Analise Micro - Cliques vs Vendas</div>', unsafe_allow_html=True)
    df_sid1 = df.groupby(["Sub_id1","Sub_id2"]).agg(Cliques=("Cliques","sum"), Vendas=("Vendas","sum"), Comissao=("Comissao","sum")).reset_index()
    df_sid1["CTR_pct"] = (df_sid1["Vendas"]/df_sid1["Cliques"]*100).fillna(0).round(2)
    fig_sc = px.scatter(df_sid1, x="Cliques", y="Vendas", color="Sub_id2", size="Comissao",
                        hover_name="Sub_id1",
                        hover_data={"Comissao":":.2f","CTR_pct":":.2f","Cliques":True,"Vendas":True},
                        title="Cliques vs Vendas (tamanho = Comissao)",
                        color_discrete_sequence=["#bd6d34","#9c5834","#c5936d"],
                        size_max=50, labels={"CTR_pct":"CTR (%)","Comissao":"Comissao (R$)"})
    fig_sc.update_layout(**PLOTLY_THEME)
    st.plotly_chart(fig_sc, use_container_width=True)

    # ── CORRELACAO ──
    st.markdown('<div class="section-title">🔗 Matriz de Correlacao</div>', unsafe_allow_html=True)
    df_corr = df_daily[["Vendas","Comissao","Cliques","Investimento"]].corr()
    fig_corr = px.imshow(df_corr, text_auto=".2f", title="Correlacao entre Metricas",
                         color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
    fig_corr.update_layout(**PLOTLY_THEME)
    st.plotly_chart(fig_corr, use_container_width=True)

    # ── FUNIL ──
    if m_pago and m_pago["impressoes"] > 0:
        st.markdown('<div id="funil" class="section-title">🔽 Funil de Conversao (Pago)</div>', unsafe_allow_html=True)

        df_pago_all = df_raw[df_raw["Sub_id2"].str.lower()=="pago"]
        m_pago_all  = calcular(df_pago_all) if not df_pago_all.empty else None

        if "modo_ctr" not in st.session_state:
            st.session_state.modo_ctr = "anterior"
        modo_ctr = st.session_state.modo_ctr

        # Definir cards e highlight conforme modo
        if modo_ctr == "anterior":
            cards_f = [
                ("Impressoes -> Alcance",
                 "Frequencia de alcance. Ideal > 60%. Baixo = audiencia muito restrita.",
                 "alcance","impressoes"),
                ("Alcance -> Cliques",
                 "CTR do criativo. Ideal > 1%. Baixo = criativo fraco ou saturado.",
                 "cliques_meta","alcance"),
                ("Cliques -> Vendas",
                 "Taxa de conversao final. Baixo = problema na pagina do produto ou preco.",
                 "vendas","cliques_meta"),
            ]
            highlighted = []
        else:
            cards_f = [
                ("Impressoes -> Alcance",
                 "Alcance vs total de impressoes. Referencia base do funil.",
                 "alcance","impressoes"),
                ("Impressoes -> Cliques",
                 "Eficiencia global do criativo vs total de impressoes.",
                 "cliques_meta","impressoes"),
                ("Impressoes -> Vendas",
                 "O mais importante: de tudo que viram, quantos compraram.",
                 "vendas","impressoes"),
            ]
            highlighted = []

        col_funil, col_steps = st.columns([1.2, 1])
        with col_funil:
            fl = ["Vendas","Cliques Meta","Alcance","Impressoes"]
            fv = [m_pago["vendas"], m_pago["cliques_meta"], m_pago["alcance"], m_pago["impressoes"]]
            fp = [m_pago["vendas"]/m_pago["impressoes"]*100 if m_pago["impressoes"]>0 else 0,
                  m_pago["cliques_meta"]/m_pago["impressoes"]*100 if m_pago["impressoes"]>0 else 0,
                  m_pago["alcance"]/m_pago["impressoes"]*100 if m_pago["impressoes"]>0 else 0, 100]

            # Highlight baseado nos cards visiveis
            if modo_ctr == "anterior":
                highlight_pairs = [("Impressoes","Alcance"),("Alcance","Cliques Meta"),("Cliques Meta","Vendas")]
            else:
                highlight_pairs = [("Impressoes","Alcance"),("Impressoes","Cliques Meta"),("Impressoes","Vendas")]
            highlighted_bars = set()
            for a, b in highlight_pairs:
                highlighted_bars.add(a)
                highlighted_bars.add(b)

            cores_base = {"Impressoes":"#bd6d34","Alcance":"#9c5834","Cliques Meta":"#c5936d","Vendas":"#d2b095"}
            cores_hl   = {"Impressoes":"#f6a050","Alcance":"#c07840","Cliques Meta":"#e8b090","Vendas":"#f0d8b8"}
            fig_f = go.Figure()
            for l,v,p in zip(fl,fv,fp):
                cor = cores_hl[l] if l in highlighted_bars else cores_base[l]
                lw  = 2 if l in highlighted_bars else 0
                fig_f.add_trace(go.Bar(x=[p], y=[l], orientation="h",
                    marker_color=cor, marker_line_color="#f6e8d8", marker_line_width=lw,
                    text="{:,.0f}  ({:.2f}%)".format(v,p), textposition="inside",
                    name=l, showlegend=False))
            fig_f.update_layout(
                title="Funil - % do total de impressoes ({})".format("CTR Anterior" if modo_ctr=="anterior" else "CTR Inicial"),
                barmode="overlay", **PLOTLY_THEME, height=240, margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig_f, use_container_width=True)
            st.markdown(
                '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:-8px;">' +
                "".join(['<span style="font-size:10px;color:#c5936d;"><span style="color:{};font-size:14px;">■</span> {}</span>'.format(cores_base[k],k) for k in cores_base]) +
                '</div>', unsafe_allow_html=True)

        with col_steps:
            st.markdown(
                '<div style="color:#c5936d;font-size:11px;margin-bottom:8px;">'
                '<b style="color:#f6e8d8;">{}</b> | <b style="color:#bd6d34;">Delta</b> = vs semana anterior'
                '</div>'.format("CTR Anterior: conversao entre steps consecutivos" if modo_ctr=="anterior" else "CTR Inicial: todos os steps vs Impressoes"),
                unsafe_allow_html=True)

            for titulo, dica, num, den in cards_f:
                cur = m_pago[num]/m_pago[den]*100 if m_pago[den]>0 else 0
                ant_val = (m_ant_pago[num]/m_ant_pago[den]*100 if m_ant_pago and m_ant_pago[den]>0 else None)

                parts = []
                if ant_val is not None:
                    diff = cur - ant_val
                    sinal = "+" if diff>0 else ""
                    cor = "#7a9e4e" if diff>0 else "#c0392b"
                    arr = "▲" if diff>0 else "▼"
                    parts.append('<span style="color:{};font-size:10px;">{} {}{}pp vs ant. ({:.3f}%)</span>'.format(cor,arr,sinal,round(diff,3),ant_val))
                delta_str = parts[0] if parts else '<span style="color:#c5936d;font-size:10px;">sem referencia anterior</span>'

                st.markdown(
                    '<div class="metric-card" style="margin-bottom:6px;padding:10px 14px;" title="{dica}">'
                    '<div class="metric-label" style="font-size:10px;">{titulo}</div>'
                    '<div class="metric-value" style="font-size:18px;">{cur:.3f}%</div>'
                    '{delta}'
                    '</div>'.format(dica=dica, titulo=titulo, cur=cur, delta=delta_str),
                    unsafe_allow_html=True)

            # Botao delicado abaixo dos cards
            st.markdown("""
            <style>
            div[data-testid="stButton"] button.ctr-toggle {
                background: transparent !important;
                border: 1px solid #3a2c28 !important;
                color: #c5936d !important;
                font-size: 11px !important;
                padding: 3px 10px !important;
                border-radius: 20px !important;
            }
            </style>
            """, unsafe_allow_html=True)
            label_btn = "↩ Ver CTR Inicial" if modo_ctr == "anterior" else "↩ Ver CTR Anterior"
            if st.button(label_btn, key="toggle_ctr"):
                st.session_state.modo_ctr = "inicial" if modo_ctr == "anterior" else "anterior"
                st.rerun()

    # ── EVOLUCAO METRICAS PAGO ──
    if len(df_pago) > 0:
        st.markdown('<div id="metricas-pago" class="section-title">📉 Evolucao Metricas Pago</div>', unsafe_allow_html=True)
        df_pd = df_pago.groupby("Data").agg(
            Investimento=("Investimento","sum"), Impressoes=("Impressoes","sum"),
            Alcance=("Alcance","sum"), Cliques_Meta=("Cliques_Meta","sum"), Vendas=("Vendas","sum")
        ).reset_index()
        df_pd["CPM_Imp"] = (df_pd["Investimento"]/df_pd["Impressoes"]*1000).fillna(0)
        df_pd["CPC"] = (df_pd["Investimento"]/df_pd["Cliques_Meta"]).fillna(0)
        df_pd["CAC"] = (df_pd["Investimento"]/df_pd["Vendas"]).fillna(0)
        met_pago = st.selectbox("Metrica Pago", ["CPM_Imp","CPC","CAC"])
        fig_pago = px.line(df_pd, x="Data", y=met_pago, title="Evolucao de {}".format(met_pago),
                           markers=True, text=met_pago, color_discrete_sequence=["#bd6d34"])
        fig_pago.update_traces(texttemplate="R$ %{text:.2f}", textposition="top center")
        fig_pago.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig_pago, use_container_width=True)

    # ── TABELA ──
    st.markdown('<div class="section-title">📋 Dados Detalhados</div>', unsafe_allow_html=True)
    cols_t = ["Data","Sub_id2","Sub_id1","Sub_id3","Cliques","Vendas","Comissao","Investimento"]
    df_t = df[cols_t].copy()
    df_t["Data"] = df_t["Data"].dt.strftime("%Y-%m-%d")
    df_t = df_t.sort_values("Comissao", ascending=False).reset_index(drop=True)
    busca = st.text_input("🔍 Pesquisar", placeholder="Ex: pago, 260302fronha...")
    if busca:
        df_t = df_t[df_t.apply(lambda r: busca.lower() in str(r).lower(), axis=1)]
    st.dataframe(df_t.style.format({"Comissao":"R$ {:.2f}","Investimento":"R$ {:.2f}"}),
                 use_container_width=True, height=400)
    st.caption("{} linhas".format(len(df_t)))

    # ── DOWNLOAD ──
    html_report = """<html><head><style>
    body{{font-family:Arial;padding:20px;color:#333;}}
    h1{{color:#562d1d;}} table{{width:100%;border-collapse:collapse;}}
    th{{background:#562d1d;color:white;padding:8px;}} td{{padding:6px;border-bottom:1px solid #eee;}}
    </style></head><body>
    <h1>Relatorio de Performance - Destrava</h1>
    <p>Periodo: {} a {}</p>
    <p>Comissao: {} | Lucro: {} | ROI: {:.2f} | Vendas: {}</p>
    {}
    </body></html>""".format(d_ini, d_fim, fmt_brl(m["comissao"]), fmt_brl(m["lucro_total"]),
                             m["roi"], fmt_num(m["vendas"]), df_t.to_html(index=False))
    st.download_button("📥 Download Relatorio HTML",
                       data=html_report.encode("utf-8"),
                       file_name="relatorio_{}_{}.html".format(d_ini, d_fim),
                       mime="text/html")

    # ── INSIGHTS IA ──
    st.markdown('<div id="insights-ia" class="section-title">🤖 DESTRAVA AI - Insights & Recomendacoes</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">
        <div style="background:#1a1210;border:1px solid #bd6d34;border-radius:10px;padding:16px;">
            <div style="color:#bd6d34;font-size:13px;font-weight:700;margin-bottom:6px;">Campanha Paga</div>
            <div style="color:#c5936d;font-size:12px;line-height:1.5;">
                Analise tecnica de CPM, CPC, CAC, frequencia e funil de conversao.
                Identifica saturacao de criativo, anomalias de CAC/CPC vs benchmarks,
                e recomenda acoes especificas de optimizacao de campanha.
            </div>
        </div>
        <div style="background:#1a1210;border:1px solid #9c5834;border-radius:10px;padding:16px;">
            <div style="color:#9c5834;font-size:13px;font-weight:700;margin-bottom:6px;">Visao Geral (todos os canais)</div>
            <div style="color:#c5936d;font-size:12px;line-height:1.5;">
                Comparacao tecnica de ROI, CTR e eficiencia entre pago, organico e story.
                Identifica o canal com melhor custo-beneficio e recomenda
                onde alocar recursos na proxima semana.
            </div>
        </div>
    </div>
    <div style="color:#c5936d;font-size:11px;margin-bottom:12px;">
        (*) Cada analise consome aprox. $0.01 de creditos Anthropic.
    </div>
    """, unsafe_allow_html=True)

    btn1, btn2, _ = st.columns([1, 1, 2])
    with btn1:
        gerar_camp = st.button("Analisar Campanha Paga", use_container_width=True)
    with btn2:
        gerar_geral = st.button("Analisar Todos os Canais", use_container_width=True)

    if gerar_camp and m_pago and m_pago["impressoes"] > 0:
        with st.spinner("A analisar com IA..."):
            try:
                api_key = st.secrets.get("anthropic", {}).get("api_key", "")
                ant_txt = ""
                if m_ant_pago:
                    ant_txt = (
                        "Periodo anterior: "
                        "Invest={:.2f} Vendas={:.0f} Comissao={:.2f} "
                        "CPM={:.2f} CPC={:.2f} CAC={:.2f} "
                        "CTR_Meta={:.2f}% CTR_Conv={:.2f}% Freq={:.2f}x ROI={:.2f}"
                    ).format(
                        m_ant_pago["invest"], m_ant_pago["vendas"], m_ant_pago["comissao"],
                        m_ant_pago["cpm_imp"], m_ant_pago["cpc"], m_ant_pago["cac"],
                        m_ant_pago["ctr_meta"], m_ant_pago["ctr_cv"], m_ant_pago["freq"], m_ant_pago["roi"]
                    )

                dados_atuais = (
                    "Periodo: {} a {}\n"
                    "Invest: {:.2f} | Vendas: {:.0f} | Comissao: {:.2f} | Lucro: {:.2f} | ROI: {:.2f}\n"
                    "CPM_imp: {:.2f} | CPM_alc: {:.2f} | CPC: {:.2f} | CAC: {:.2f} | Freq: {:.2f}x\n"
                    "CTR_Meta: {:.2f}% | CTR_Conv: {:.2f}%\n"
                    "Funil: {:.0f} imp -> {:.0f} alc -> {:.0f} cliques -> {:.0f} vendas\n"
                    "{}"
                ).format(
                    d_ini, d_fim,
                    m_pago["invest"], m_pago["vendas"], m_pago["comissao"],
                    m_pago["comissao"]-m_pago["invest"], m_pago["roi"],
                    m_pago["cpm_imp"], m_pago["cpm_alc"], m_pago["cpc"], m_pago["cac"], m_pago["freq"],
                    m_pago["ctr_meta"], m_pago["ctr_cv"],
                    m_pago["impressoes"], m_pago["alcance"], m_pago["cliques_meta"], m_pago["vendas"],
                    ant_txt
                )

                prompt = (
                    "Es especialista senior em Meta Ads e marketing de afiliados Shopee. "
                    "Usa linguagem tecnica - o utilizador e gestor de trafego experiente. "
                    "Analisa os dados abaixo e fornece SEMPRE: "
                    "1. Diagnostico tecnico (2 frases com metricas especificas). "
                    "2. 2-3 alertas criticos (saturacao, anomalias, thresholds). "
                    "3. 2-3 acoes concretas (mesmo que seja manter o que esta a funcionar). "
                    "Dados: " + dados_atuais
                )

                resp = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"Content-Type":"application/json",
                             "x-api-key":api_key,
                             "anthropic-version":"2023-06-01"},
                    json={"model":"claude-sonnet-4-20250514","max_tokens":1000,
                          "messages":[{"role":"user","content":prompt}]},
                    timeout=30
                )
                rj = resp.json()
                if "error" in rj:
                    raise Exception(rj["error"]["message"])
                analise = rj["content"][0]["text"]
                html_ai = (
                    '<div style="background:linear-gradient(135deg,#1a1210,#221a16);'
                    'border-radius:12px;padding:20px;margin-top:12px;'
                    'border-left:4px solid #bd6d34;border:1px solid #3a2c28;">'
                    '<div style="color:#bd6d34;font-size:13px;font-weight:700;margin-bottom:12px;">'
                    'Campanha Paga - {} a {}</div>'
                    '<div style="color:#f6e8d8;font-size:14px;line-height:1.8;">{}</div>'
                    '</div>'
                ).format(d_ini, d_fim, analise.replace("\n","<br>"))
                st.markdown(html_ai, unsafe_allow_html=True)
            except Exception as e:
                st.error("Erro IA: {}".format(str(e)))

    if gerar_geral:
        with st.spinner("A analisar todos os canais..."):
            try:
                api_key = st.secrets.get("anthropic", {}).get("api_key", "")
                dados_geral = (
                    "Periodo: {} a {}\n"
                    "Comissao: {:.2f} | Lucro: {:.2f} | ROI: {:.2f} | Vendas: {:.0f} | CTR: {:.2f}%\n"
                    "Pago: {:.0f} vendas | comissao: {:.2f} | ROI: {:.2f}\n"
                    "Organico: {:.0f} vendas | comissao: {:.2f}\n"
                    "Story: {:.0f} vendas | comissao: {:.2f}"
                ).format(
                    d_ini, d_fim,
                    m["comissao"], m["lucro_total"], m["roi"], m["vendas"], m["ctr_shopee"],
                    m_pago["vendas"] if m_pago else 0, m_pago["comissao"] if m_pago else 0,
                    m_pago["roi"] if m_pago else 0,
                    m_org["vendas"] if m_org else 0, m_org["comissao"] if m_org else 0,
                    m_story["vendas"] if m_story else 0, m_story["comissao"] if m_story else 0,
                )

                prompt_g = (
                    "Es especialista senior em marketing de afiliados Shopee. "
                    "Usa linguagem tecnica - gestor de trafego experiente. "
                    "Analisa os dados e fornece SEMPRE: "
                    "1. Diagnostico geral (2 frases com metricas). "
                    "2. Melhor canal e justificacao tecnica (ROI, CTR, CAC comparados). "
                    "3. 2-3 acoes concretas (mesmo que seja manter o que esta a funcionar). "
                    "Dados: " + dados_geral
                )

                resp2 = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"Content-Type":"application/json",
                             "x-api-key":api_key,
                             "anthropic-version":"2023-06-01"},
                    json={"model":"claude-sonnet-4-20250514","max_tokens":800,
                          "messages":[{"role":"user","content":prompt_g}]},
                    timeout=30
                )
                rj2 = resp2.json()
                if "error" in rj2:
                    raise Exception(rj2["error"]["message"])
                analise2 = rj2["content"][0]["text"]
                html_ai2 = (
                    '<div style="background:linear-gradient(135deg,#1a1210,#221a16);'
                    'border-radius:12px;padding:20px;margin-top:12px;'
                    'border-left:4px solid #9c5834;border:1px solid #3a2c28;">'
                    '<div style="color:#9c5834;font-size:13px;font-weight:700;margin-bottom:12px;">'
                    'Todos os Canais - {} a {}</div>'
                    '<div style="color:#f6e8d8;font-size:14px;line-height:1.8;">{}</div>'
                    '</div>'
                ).format(d_ini, d_fim, analise2.replace("\n","<br>"))
                st.markdown(html_ai2, unsafe_allow_html=True)
            except Exception as e:
                st.error("Erro IA: {}".format(str(e)))

    st.markdown("""
    <div class="footer">
        🔓 <strong style="color:#bd6d34;">DESTRAVA</strong>
        <span style="color:#c5936d;"> por Carol Matos · Analytics Dashboard</span>
        <br><span style="color:#562d1d;font-size:10px;">Dados actualizados a cada 5 min</span>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
