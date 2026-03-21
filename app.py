import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import numpy as np
from datetime import datetime, timedelta
import io

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

# ─────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Force dark mode always */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
        background-color: #0f0d0b !important;
        color: #f6e8d8 !important;
    }
    /* Subtle background image */
    [data-testid="stAppViewContainer"] {
        background-image: url("https://raw.githubusercontent.com/brennoeccard/dashboard-performance-shopee/main/logo_bg.png");
        background-repeat: no-repeat;
        background-position: center center;
        background-size: 40%;
        background-attachment: fixed;
        opacity: 1;
    }
    /* Overlay to darken the bg image */
    [data-testid="stAppViewContainer"]::before {
        content: "";
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(15, 13, 11, 0.93);
        z-index: 0;
        pointer-events: none;
    }
    [data-testid="stMain"] { position: relative; z-index: 1; }
    /* Sidebar fix */
    [data-testid="stSidebar"] {
        background-color: #110e0c !important;
        border-right: 1px solid #3a2c28 !important;
    }
    [data-testid="stSidebar"] * {
        color: #f6e8d8 !important;
    }
    /* Sidebar buttons */
    [data-testid="stSidebar"] button {
        background-color: #3a2c28 !important;
        color: #f6e8d8 !important;
        border: 1px solid #bd6d34 !important;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #bd6d34 !important;
        color: #f6e8d8 !important;
    }
    /* Expander filter bar */
    [data-testid="stExpander"] {
        background-color: #1a1210 !important;
        border: 1px solid #3a2c28 !important;
        border-radius: 8px !important;
    }
    [data-testid="stExpander"] summary {
        color: #f6e8d8 !important;
    }
    [data-testid="stSidebar"] .stMultiSelect > div,
    [data-testid="stSidebar"] .stDateInput > div,
    [data-testid="stSidebar"] input {
        background-color: #1a1210 !important;
        color: #f6e8d8 !important;
        border-color: #3a2c28 !important;
    }
    /* Multiselect tags */
    [data-testid="stSidebar"] span[data-baseweb="tag"] {
        background-color: #3a2c28 !important;
        color: #f6e8d8 !important;
    }
    .main { background-color: #0f0d0b; }
    .metric-card {
        background: linear-gradient(135deg, #1a1210, #221a16);
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
        background: linear-gradient(135deg, #1a1210, #221a16);
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
    .roi-green  { color: #7a9e4e; font-size: 22px; font-weight: 700; }
    .roi-yellow { color: #d4a017; font-size: 22px; font-weight: 700; }
    .roi-red    { color: #c0392b; font-size: 22px; font-weight: 700; }
    .footer {
        margin-top: 40px;
        padding: 20px;
        border-top: 1px solid #3a2c28;
        text-align: center;
        color: #c5936d;
        font-size: 12px;
    }
    .stSelectbox label, .stMultiSelect label, .stDateInput label { color: #c5936d !important; }
    [data-testid="stSidebar"] { background-color: #110e0c; border-right: 1px solid #3a2c28; }
</style>
""", unsafe_allow_html=True)

PLOTLY_THEME = dict(
    plot_bgcolor="#0f0d0b",
    paper_bgcolor="#0f0d0b",
    font_color="#f6e8d8",
    title_font_color="#f6e8d8",
    legend=dict(
        font=dict(color="#f6e8d8", size=12),
        bgcolor="rgba(30,18,16,0.8)",
        bordercolor="#3a2c28",
        borderwidth=1,
    ),
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
            <div style='text-align:center; margin-bottom:24px; padding:20px;
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
                submitted = st.form_submit_button("→ Entrar", use_container_width=True)
                if submitted:
                    if usuario in users and users[usuario] == password:
                        st.session_state.logged_in = True
                        st.session_state.usuario = usuario
                        st.rerun()
                    else:
                        st.error("❌ Utilizador ou password incorrectos.")
        return False
    return True

# ─────────────────────────────────────────────
#  AUTENTICAÇÃO GOOGLE
# ─────────────────────────────────────────────
@st.cache_resource
def autenticar():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    except Exception:
        creds = Credentials.from_service_account_file(
            "/Users/anacarol/automacao/automacao-planilhas-490816-ee73c7ff4bf2.json",
            scopes=SCOPES
        )
    return build("sheets", "v4", credentials=creds)

# ─────────────────────────────────────────────
#  LER DADOS
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def ler_dados():
    service = autenticar()
    resultado = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A1:P",
    ).execute()
    valores = resultado.get("values", [])
    if len(valores) < 2:
        return pd.DataFrame()

    cabecalho = valores[0]
    linhas    = valores[1:]
    max_cols  = len(cabecalho)
    linhas_norm = [l + [""] * (max_cols - len(l)) for l in linhas]
    df = pd.DataFrame(linhas_norm, columns=cabecalho)

    col_map = {
        df.columns[0]:  "Data",
        df.columns[1]:  "Sub_id2",
        df.columns[2]:  "Sub_id1",
        df.columns[3]:  "Sub_id3",
        df.columns[4]:  "Cliques",
        df.columns[5]:  "Vendas",
        df.columns[6]:  "CTR",
        df.columns[7]:  "Comissao",
        df.columns[8]:  "Investimento",
        df.columns[9]:  "Impressoes",
        df.columns[10]: "Alcance",
        df.columns[11]: "Cliques_Meta",
        df.columns[12]: "CTR_Meta",
        df.columns[13]: "CTR_Geral",
        df.columns[14]: "Lucro",
        df.columns[15]: "ROI",
    }
    df = df.rename(columns=col_map)

    def to_num(col):
        return pd.to_numeric(
            df[col].astype(str)
                   .str.replace("R\\$", "", regex=True)
                   .str.replace("%", "")
                   .str.replace("\\.", "", regex=True)
                   .str.replace(",", ".")
                   .str.strip(),
            errors="coerce"
        ).fillna(0)

    for col in ["Cliques","Vendas","Comissao","Investimento",
                "Impressoes","Alcance","Cliques_Meta","Lucro","ROI"]:
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
    return f"R$ {val:,.2f}".replace(",","X").replace(".",",").replace("X",".")

def fmt_pct(val):
    return f"{val:.2f}%".replace(".",",")

def fmt_num(val):
    return f"{int(val):,}".replace(",",".")

def fmt_roi(val):
    cor = "roi-green" if val > 1 else ("roi-yellow" if val >= 0 else "roi-red")
    return f'<span class="{cor}">{val:.2f}</span>'

def delta_html(val, ref):
    if ref == 0:
        return '<span class="metric-delta-neu">— sem ref.</span>'
    pct = (val - ref) / abs(ref) * 100
    if pct > 0:
        return f'<span class="metric-delta-pos">▲ {pct:.1f}% vs semana ant.</span>'
    elif pct < 0:
        return f'<span class="metric-delta-neg">▼ {abs(pct):.1f}% vs semana ant.</span>'
    else:
        return '<span class="metric-delta-neu">= igual semana ant.</span>'

def card(label, value, color="blue", delta_html_str="", sparkline_fig=None):
    st.markdown(f"""
    <div class="metric-card {color}">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html_str}
    </div>""", unsafe_allow_html=True)
    if sparkline_fig:
        st.plotly_chart(sparkline_fig, use_container_width=True, config={"displayModeBar": False})

def calcular(df):
    cliques      = df["Cliques"].sum()
    vendas       = df["Vendas"].sum()
    comissao     = df["Comissao"].sum()
    invest       = df["Investimento"].sum()
    impressoes   = df["Impressoes"].sum()
    alcance      = df["Alcance"].sum()
    cliques_meta = df["Cliques_Meta"].sum()
    lucro_total  = comissao - invest
    lucro_camp   = df[df["Sub_id2"].str.lower()=="pago"]["Comissao"].sum() - invest
    roi          = (comissao - invest) / invest if invest > 0 else 0
    ctr_shopee   = (vendas / cliques * 100)      if cliques > 0      else 0
    ctr_meta     = (cliques_meta / alcance * 100) if alcance > 0     else 0
    ctr_cv       = (vendas / cliques_meta * 100)  if cliques_meta > 0 else 0
    freq         = impressoes / alcance           if alcance > 0      else 0
    cpm_imp      = (invest / impressoes * 1000)   if impressoes > 0   else 0
    cpm_alc      = (invest / alcance * 1000)      if alcance > 0      else 0
    cpc          = invest / cliques_meta          if cliques_meta > 0 else 0
    cac          = invest / vendas                if vendas > 0       else 0
    return dict(
        cliques=cliques, vendas=vendas, comissao=comissao, invest=invest,
        impressoes=impressoes, alcance=alcance, cliques_meta=cliques_meta,
        lucro_total=lucro_total, lucro_camp=lucro_camp, roi=roi,
        ctr_shopee=ctr_shopee, ctr_meta=ctr_meta, ctr_cv=ctr_cv,
        freq=freq, cpm_imp=cpm_imp, cpm_alc=cpm_alc, cpc=cpc, cac=cac,
    )

def sparkline(df_daily, col, color="#bd6d34"):
    df14 = df_daily.tail(14)
    fig = go.Figure(go.Scatter(
        x=df14["Data"], y=df14[col],
        mode="lines", line=dict(color=color, width=1.5),
        fill="tozeroy", fillcolor="rgba(189,109,52,0.15)",
    ))
    fig.update_layout(
        height=50, margin=dict(l=0,r=0,t=0,b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        plot_bgcolor="#0f1117", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig

def verificar_alerta_roi(df):
    """Verifica se ROI < 0 por 3 dias consecutivos."""
    df_pago = df[df["Sub_id2"].str.lower()=="pago"].copy()
    if df_pago.empty:
        return False
    df_daily = df_pago.groupby("Data").agg(
        Comissao=("Comissao","sum"), Investimento=("Investimento","sum")
    ).reset_index().sort_values("Data").tail(3)
    df_daily["ROI"] = (df_daily["Comissao"] - df_daily["Investimento"]) / df_daily["Investimento"].replace(0, np.nan)
    return (df_daily["ROI"] < 0).all()

def semana_anterior(df, data_ini, data_fim):
    delta = data_fim - data_ini
    ant_fim = data_ini - timedelta(days=1)
    ant_ini = ant_fim - delta
    return df[(df["Data"].dt.date >= ant_ini) & (df["Data"].dt.date <= ant_fim)]

# ─────────────────────────────────────────────
#  APP PRINCIPAL
# ─────────────────────────────────────────────
def main():
    if not check_login():
        return

    st.markdown("""
    <div style="display:flex; align-items:center; gap:16px; margin-bottom:8px;">
        <div>
            <h1 style="color:#f6e8d8; margin:0; font-size:28px;">📊 Dashboard de Performance</h1>
            <p style="color:#c5936d; margin:0; font-size:13px;">Destrava · por Carol Matos</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    with st.spinner("A carregar dados..."):
        df_raw = ler_dados()

    if df_raw.empty:
        st.error("Sem dados disponíveis. Verifica a planilha.")
        return

    # ── TOP BAR: utilizador + logout ──
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.get('usuario','')}")
        if st.button("🔄 Actualizar dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # ── FILTROS NO TOPO ──
    data_min = df_raw["Data"].min().date()
    data_max = df_raw["Data"].max().date()

    with st.expander("🎛️ Filtros", expanded=False):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            datas = st.date_input("Período", value=(data_min, data_max),
                                  min_value=data_min, max_value=data_max)
        with fc2:
            sid2_opts = sorted([x for x in df_raw["Sub_id2"].unique() if x.strip()])
            sid2_sel  = st.multiselect("Canal (Sub_id2)", sid2_opts, default=[],
                                       placeholder="Todos os canais")
        with fc3:
            sid1_opts = sorted([x for x in df_raw["Sub_id1"].unique() if x.strip()])
            sid1_sel  = st.multiselect("Sub_id1", sid1_opts, default=[],
                                       placeholder="Todos os Sub_id1")
        with fc4:
            sid3_opts = sorted([x for x in df_raw["Sub_id3"].unique() if x.strip()])
            sid3_sel  = st.multiselect("Sub_id3", sid3_opts, default=[],
                                       placeholder="Todos os Sub_id3")

    if isinstance(datas, tuple) and len(datas) == 2:
        d_ini, d_fim = datas
    else:
        d_ini, d_fim = data_min, data_max

    # Aplicar filtros — se nada seleccionado, mostrar tudo sem excepção
    mask = (
        (df_raw["Data"].dt.date >= d_ini) &
        (df_raw["Data"].dt.date <= d_fim)
    )
    if sid2_sel: mask = mask & (df_raw["Sub_id2"].isin(sid2_sel))
    if sid1_sel: mask = mask & (df_raw["Sub_id1"].isin(sid1_sel))
    if sid3_sel: mask = mask & (df_raw["Sub_id3"].isin(sid3_sel))

    df = df_raw[mask].copy()
    # df_viz: apenas para gráficos de canal (remove brancos)
    df_viz = df[df["Sub_id2"].str.strip() != ""].copy()
    df_ant = semana_anterior(df_raw, d_ini, d_fim)

    if df.empty:
        st.warning("Sem dados para os filtros seleccionados.")
        return

    m     = calcular(df)
    m_ant = calcular(df_ant) if not df_ant.empty else None

    df_pago = df[df["Sub_id2"].str.lower()=="pago"]
    df_org  = df[df["Sub_id2"].str.lower()=="organico"]
    df_story= df[df["Sub_id2"].str.lower()=="story"]
    m_pago  = calcular(df_pago)  if len(df_pago)  > 0 else None
    m_org   = calcular(df_org)   if len(df_org)   > 0 else None
    m_story = calcular(df_story) if len(df_story) > 0 else None

    # Dados diários para sparklines
    df_daily = df.groupby("Data").agg(
        Vendas=("Vendas","sum"), Comissao=("Comissao","sum"),
        Cliques=("Cliques","sum"), Investimento=("Investimento","sum"),
    ).reset_index().sort_values("Data")

    # ── ALERTA ROI ──
    if verificar_alerta_roi(df):
        st.markdown("""
        <div class="alert-banner">
            ⚠️ ALERTA: ROI negativo nos últimos 3 dias consecutivos na campanha paga!
            Revê o investimento e os resultados urgentemente.
        </div>
        """, unsafe_allow_html=True)

    # ── KPIs GERAIS ──
    st.markdown('<div class="section-title">💰 KPIs Gerais</div>', unsafe_allow_html=True)
    c1,c2,c3,c4,c5,c6 = st.columns(6)

    with c1:
        d = delta_html(m["comissao"], m_ant["comissao"]) if m_ant else ""
        card("Comissão Total", fmt_brl(m["comissao"]), "blue", d,
             sparkline(df_daily,"Comissao","#bd6d34"))
    with c2:
        d = delta_html(m["lucro_total"], m_ant["lucro_total"]) if m_ant else ""
        cor = "green" if m["lucro_total"] >= 0 else "red"
        card("Lucro Total", fmt_brl(m["lucro_total"]), cor, d,
             sparkline(df_daily,"Comissao","#9c5834"))
    with c3:
        roi_val = m["roi"]
        cor_roi = "green" if roi_val > 1 else ("yellow" if roi_val >= 0 else "red")
        card("ROI", f"{roi_val:.2f}", cor_roi)
    with c4:
        d = delta_html(m["vendas"], m_ant["vendas"]) if m_ant else ""
        card("Vendas", fmt_num(m["vendas"]), "purple", d,
             sparkline(df_daily,"Vendas","#c5936d"))
    with c5:
        d = delta_html(m["cliques"], m_ant["cliques"]) if m_ant else ""
        card("Cliques Shopee", fmt_num(m["cliques"]), "yellow", d,
             sparkline(df_daily,"Cliques","#d2b095"))
    with c6:
        ctr = m["ctr_shopee"]
        card("CTR Shopee", fmt_pct(ctr), "blue")

    # ── KPIs POR CANAL ──
    st.markdown('<div class="section-title">📂 Performance por Canal</div>', unsafe_allow_html=True)
    cc1, cc2, cc3 = st.columns(3)

    def canal_card(col, m_canal, nome, emoji, cor):
        with col:
            if m_canal:
                st.markdown(f"""
                <div class="canal-card">
                    <div class="canal-title">{emoji} {nome}</div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
                        <div><div class="canal-metric">Vendas</div>
                             <div class="canal-value">{fmt_num(m_canal['vendas'])}</div></div>
                        <div><div class="canal-metric">Comissão</div>
                             <div class="canal-value">{fmt_brl(m_canal['comissao'])}</div></div>
                        <div><div class="canal-metric">Cliques</div>
                             <div class="canal-value">{fmt_num(m_canal['cliques'])}</div></div>
                        <div><div class="canal-metric">CTR</div>
                             <div class="canal-value">{fmt_pct(m_canal['ctr_shopee'])}</div></div>
                    </div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="canal-card">
                    <div class="canal-title">{emoji} {nome}</div>
                    <div style="color:#8892a4;">Sem dados no período</div>
                </div>""", unsafe_allow_html=True)

    canal_card(cc1, m_pago,  "Pago",      "📣", "red")
    canal_card(cc2, m_org,   "Orgânico",  "🌱", "green")
    canal_card(cc3, m_story, "Story",     "📖", "purple")

    # ── KPIs CAMPANHA PAGO ──
    if m_pago:
        st.markdown('<div class="section-title">📣 KPIs Campanha (Pago)</div>', unsafe_allow_html=True)

        # Lucro campanha
        lucro_camp = m_pago["comissao"] - m_pago["invest"]
        roi_camp   = (m_pago["comissao"] - m_pago["invest"]) / m_pago["invest"] if m_pago["invest"] > 0 else 0
        cor_roi    = "green" if roi_camp > 1 else ("yellow" if roi_camp >= 0 else "red")

        k1,k2,k3,k4 = st.columns(4)
        with k1: card("Vendas Pago",    fmt_num(m_pago["vendas"]),   "purple")
        with k2: card("Comissão Pago",  fmt_brl(m_pago["comissao"]), "blue")
        with k3: card("Investimento",   fmt_brl(m_pago["invest"]),   "red")
        with k4: card("Lucro Campanha", fmt_brl(lucro_camp), cor_roi)

        k5,k6,k7,k8,k9 = st.columns(5)
        with k5: card("CPM Impressões", fmt_brl(m_pago["cpm_imp"]),  "yellow")
        with k6: card("CPM Alcance",    fmt_brl(m_pago["cpm_alc"]),  "yellow")
        with k7: card("CPC",            fmt_brl(m_pago["cpc"]),      "blue")
        with k8: card("CAC",            fmt_brl(m_pago["cac"]),      "purple")
        with k9: card("Frequência",     f"{m_pago['freq']:.2f}x",    "orange")

    st.markdown("---")

    # ── EVOLUÇÃO TEMPORAL ──
    st.markdown('<div class="section-title">📈 Evolução Temporal</div>', unsafe_allow_html=True)

    metricas_disp = {
        "Comissão": "Comissao",
        "Vendas": "Vendas",
        "Cliques Shopee": "Cliques",
        "Investimento": "Investimento",
    }

    col_sel = st.multiselect(
        "Selecciona métricas para cruzar",
        list(metricas_disp.keys()),
        default=["Comissão","Vendas"]
    )

    if col_sel:
        fig_linha = go.Figure()
        cores = ["#bd6d34","#c5936d","#d2b095","#9c5834","#562d1d"]
        for i, nome in enumerate(col_sel):
            col_real = metricas_disp[nome]
            cor = cores[i % len(cores)]
            # Linha principal
            fig_linha.add_trace(go.Scatter(
                x=df_daily["Data"], y=df_daily[col_real],
                name=nome, mode="lines+markers",
                line=dict(color=cor, width=2),
                marker=dict(size=4),
            ))
            # Média móvel 7 dias
            mm7 = df_daily[col_real].rolling(7, min_periods=1).mean()
            fig_linha.add_trace(go.Scatter(
                x=df_daily["Data"], y=mm7,
                name=f"{nome} (MM7)", mode="lines",
                line=dict(color=cor, width=1, dash="dash"),
                opacity=0.6,
            ))
        fig_linha.update_layout(title="Evolução Temporal + Média Móvel 7 dias",
                                hovermode="x unified", **PLOTLY_THEME)
        st.plotly_chart(fig_linha, use_container_width=True)

    # ── COMPARAÇÃO POR CANAL ──
    st.markdown('<div class="section-title">📊 Comparação por Canal</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    df_canal = df_viz.groupby("Sub_id2").agg(
        Vendas=("Vendas","sum"),
        Comissao=("Comissao","sum"),
        Cliques=("Cliques","sum"),
    ).reset_index()

    with col1:
        fig_bar = px.bar(df_canal, x="Sub_id2", y="Comissao",
                         title="Comissão por Canal", color="Sub_id2",
                         text="Comissao",
                         color_discrete_sequence=["#bd6d34","#9c5834","#c5936d","#d2b095","#562d1d","#f6e8d8"])
        fig_bar.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
        fig_bar.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        fig_pizza = px.pie(df_canal, names="Sub_id2", values="Vendas",
                           title="Distribuição de Vendas por Canal",
                           color_discrete_sequence=["#bd6d34","#9c5834","#c5936d","#d2b095","#562d1d","#f6e8d8"])
        fig_pizza.update_traces(textinfo="percent+label")
        fig_pizza.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig_pizza, use_container_width=True)

    # ── TOP Sub_id3 ──
    st.markdown('<div class="section-title">🏷️ Top & Bottom Sub_id3</div>', unsafe_allow_html=True)

    df_sid3 = df[df["Sub_id3"] != ""].groupby("Sub_id3").agg(
        Comissao=("Comissao","sum"),
        Vendas=("Vendas","sum"),
        Cliques=("Cliques","sum"),
    ).reset_index()
    df_sid3["CTR"] = (df_sid3["Vendas"] / df_sid3["Cliques"] * 100).fillna(0)

    col1, col2 = st.columns(2)
    with col1:
        top5 = df_sid3.nlargest(5,"Comissao")
        fig = px.bar(top5, x="Comissao", y="Sub_id3", orientation="h",
                     title="🏆 Top 5 por Comissão", text="Comissao",
                     color_discrete_sequence=["#9c5834"])
        fig.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
        fig.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        top5_vendas = df_sid3.nlargest(5,"Vendas")
        fig = px.bar(top5_vendas, x="Vendas", y="Sub_id3", orientation="h",
                     title="🏆 Top 5 por Vendas", text="Vendas",
                     color_discrete_sequence=["#9c5834"])
        fig.update_traces(texttemplate="%{text}", textposition="outside")
        fig.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        top5_cliques = df_sid3.nlargest(5,"Cliques")
        fig = px.bar(top5_cliques, x="Cliques", y="Sub_id3", orientation="h",
                     title="👆 Top 5 por Cliques", text="Cliques",
                     color_discrete_sequence=["#c5936d"])
        fig.update_traces(texttemplate="%{text}", textposition="outside")
        fig.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        top5_ctr = df_sid3.nlargest(5,"CTR")
        fig = px.bar(top5_ctr, x="CTR", y="Sub_id3", orientation="h",
                     title="🎯 Top 5 por CTR (%)", text="CTR",
                     color_discrete_sequence=["#d2b095"])
        fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
        fig.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig, use_container_width=True)

    # ── SCATTER: Cliques vs Vendas ──
    st.markdown('<div class="section-title">🔍 Análise Micro — Cliques vs Vendas por Sub_id1</div>', unsafe_allow_html=True)
    df_sid1 = df.groupby(["Sub_id1","Sub_id2"]).agg(
        Cliques=("Cliques","sum"),
        Vendas=("Vendas","sum"),
        Comissao=("Comissao","sum"),
    ).reset_index()
    fig_scatter = px.scatter(
        df_sid1, x="Cliques", y="Vendas", color="Sub_id2",
        size="Comissao", hover_name="Sub_id1",
        title="Cliques vs Vendas (tamanho = Comissão)",
        color_discrete_sequence=["#bd6d34","#9c5834","#c5936d","#d2b095","#562d1d","#f6e8d8"],
        size_max=50,
    )
    fig_scatter.update_traces(textposition="top center")
    fig_scatter.update_layout(**PLOTLY_THEME)
    st.plotly_chart(fig_scatter, use_container_width=True)

    # ── CORRELAÇÃO ──
    st.markdown('<div class="section-title">🔗 Matriz de Correlação</div>', unsafe_allow_html=True)
    df_corr = df_daily[["Vendas","Comissao","Cliques","Investimento"]].corr()
    fig_corr = px.imshow(
        df_corr, text_auto=".2f",
        title="Correlação entre Métricas",
        color_continuous_scale="RdBu_r",
        zmin=-1, zmax=1,
    )
    fig_corr.update_layout(**PLOTLY_THEME)
    st.plotly_chart(fig_corr, use_container_width=True)

    # ── FUNIL PAGO ──
    if m_pago and m_pago["impressoes"] > 0:
        st.markdown('<div class="section-title">🔽 Funil de Conversão (Pago)</div>', unsafe_allow_html=True)
        # Calcular período anterior para comparação
        df_pago_ant = df_ant[df_ant["Sub_id2"].str.lower()=="pago"] if not df_ant.empty else pd.DataFrame()
        m_pago_ant  = calcular(df_pago_ant) if not df_pago_ant.empty else None

        steps     = ["Impressões","Alcance","Cliques Meta","Vendas"]
        vals_cur  = [m_pago["impressoes"],m_pago["alcance"],m_pago["cliques_meta"],m_pago["vendas"]]
        vals_ant  = [m_pago_ant["impressoes"],m_pago_ant["alcance"],
                     m_pago_ant["cliques_meta"],m_pago_ant["vendas"]] if m_pago_ant else None

        fig_funil = go.Figure(go.Funnel(
            y=steps, x=vals_cur,
            textinfo="value+percent initial",
            marker=dict(color=["#bd6d34","#9c5834","#c5936d","#d2b095"]),
            name="Período actual",
        ))

        if vals_ant:
            fig_funil.add_trace(go.Funnel(
                y=steps, x=vals_ant,
                textinfo="value",
                marker=dict(color=["#3a2c28","#3a2c28","#3a2c28","#3a2c28"]),
                name="Período anterior",
                opacity=0.5,
            ))

        fig_funil.update_layout(title="Funil de Conversão · Actual vs Período Anterior",
                                funnelmode="overlay", **PLOTLY_THEME)
        st.plotly_chart(fig_funil, use_container_width=True)

        # Alertas de variação significativa no funil
        if vals_ant and vals_ant[0] > 0:
            alertas = []
            labels_steps = ["Impressões→Alcance","Alcance→Cliques Meta","Cliques Meta→Vendas"]
            for i in range(len(steps)-1):
                ctr_cur = vals_cur[i+1]/vals_cur[i]*100 if vals_cur[i] > 0 else 0
                ctr_ant = vals_ant[i+1]/vals_ant[i]*100 if vals_ant[i] > 0 else 0
                diff    = ctr_cur - ctr_ant
                if abs(diff) >= 1.0:
                    emoji = "📈" if diff > 0 else "📉"
                    cor   = "green" if diff > 0 else "red"
                    alertas.append((emoji, labels_steps[i], ctr_ant, ctr_cur, diff, cor))

            if alertas:
                st.markdown("**Variações significativas no funil:**")
                cols_al = st.columns(len(alertas))
                for idx, (emoji, label, ant, cur, diff, cor) in enumerate(alertas):
                    with cols_al[idx]:
                        sinal = "+" if diff > 0 else ""
                        card(f"{emoji} {label}",
                             f"{cur:.1f}%",
                             cor,
                             f'<span class="metric-delta-{"pos" if diff>0 else "neg"}">{sinal}{diff:.1f}pp vs anterior ({ant:.1f}%)</span>')

    # ── EVOLUÇÃO CPM/CPC/CAC ──
    if len(df_pago) > 0:
        st.markdown('<div class="section-title">📉 Evolução Métricas Pago</div>', unsafe_allow_html=True)
        df_pd = df_pago.groupby("Data").agg(
            Investimento=("Investimento","sum"),
            Impressoes=("Impressoes","sum"),
            Alcance=("Alcance","sum"),
            Cliques_Meta=("Cliques_Meta","sum"),
            Vendas=("Vendas","sum"),
        ).reset_index()
        df_pd["CPM_Imp"] = (df_pd["Investimento"]/df_pd["Impressoes"]*1000).fillna(0)
        df_pd["CPC"]     = (df_pd["Investimento"]/df_pd["Cliques_Meta"]).fillna(0)
        df_pd["CAC"]     = (df_pd["Investimento"]/df_pd["Vendas"]).fillna(0)

        metrica_pago = st.selectbox("Métrica Pago", ["CPM_Imp","CPC","CAC"])
        fig_pago = px.line(df_pd, x="Data", y=metrica_pago,
                           title=f"Evolução de {metrica_pago}",
                           markers=True, text=metrica_pago,
                           color_discrete_sequence=["#562d1d"])
        fig_pago.update_traces(texttemplate="R$ %{text:.2f}", textposition="top center")
        fig_pago.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig_pago, use_container_width=True)

    # ── TABELA DETALHADA ──
    st.markdown('<div class="section-title">📋 Dados Detalhados</div>', unsafe_allow_html=True)
    colunas_tabela = ["Data","Sub_id2","Sub_id1","Sub_id3",
                      "Cliques","Vendas","Comissao","Investimento"]
    df_tabela = df[colunas_tabela].copy()
    df_tabela["Data"] = df_tabela["Data"].dt.strftime("%Y-%m-%d")
    st.dataframe(df_tabela, use_container_width=True, height=400)

    # ── DOWNLOAD PDF ──
    st.markdown('<div class="section-title">📥 Download</div>', unsafe_allow_html=True)
    
    # Gerar HTML para PDF
    html_content = f"""
    <html><head>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; color: #333; }}
        h1 {{ color: #1a1a2e; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
        th {{ background: #1a1a2e; color: white; padding: 8px; text-align: left; }}
        td {{ padding: 6px 8px; border-bottom: 1px solid #eee; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(3,1fr); gap: 16px; margin: 16px 0; }}
        .kpi {{ background: #f5f5f5; border-radius: 8px; padding: 12px; }}
        .kpi-label {{ color: #666; font-size: 11px; }}
        .kpi-value {{ font-size: 20px; font-weight: bold; color: #1a1a2e; }}
    </style>
    </head><body>
    <h1>📊 Relatório de Performance — Shopee</h1>
    <p>Período: {d_ini} a {d_fim}</p>
    <div class="kpi-grid">
        <div class="kpi"><div class="kpi-label">COMISSÃO TOTAL</div>
             <div class="kpi-value">{fmt_brl(m['comissao'])}</div></div>
        <div class="kpi"><div class="kpi-label">LUCRO TOTAL</div>
             <div class="kpi-value">{fmt_brl(m['lucro_total'])}</div></div>
        <div class="kpi"><div class="kpi-label">ROI</div>
             <div class="kpi-value">{m['roi']:.2f}</div></div>
        <div class="kpi"><div class="kpi-label">VENDAS</div>
             <div class="kpi-value">{fmt_num(m['vendas'])}</div></div>
        <div class="kpi"><div class="kpi-label">CLIQUES</div>
             <div class="kpi-value">{fmt_num(m['cliques'])}</div></div>
        <div class="kpi"><div class="kpi-label">CTR SHOPEE</div>
             <div class="kpi-value">{fmt_pct(m['ctr_shopee'])}</div></div>
    </div>
    <h2>Dados Detalhados</h2>
    {df_tabela.to_html(index=False)}
    </body></html>
    """

    st.download_button(
        label="📥 Download Relatório HTML",
        data=html_content.encode("utf-8"),
        file_name=f"relatorio_{d_ini}_{d_fim}.html",
        mime="text/html",
    )

    st.markdown("""
    <div class="footer">
        🔓 <strong style="color:#bd6d34;">DESTRAVA</strong>
        <span style="color:#c5936d;"> · por Carol Matos · Analytics Dashboard</span>
        <br><span style="color:#562d1d; font-size:10px;">Dados actualizados a cada 5 min</span>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
