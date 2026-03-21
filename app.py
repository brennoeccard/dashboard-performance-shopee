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
    .main { background-color: #0f1117; }
    .metric-card {
        background: linear-gradient(135deg, #1e2130, #252840);
        border-radius: 12px;
        padding: 16px 20px;
        border-left: 4px solid #4f8ef7;
        margin-bottom: 4px;
    }
    .metric-card.green  { border-left-color: #2ecc71; }
    .metric-card.red    { border-left-color: #e74c3c; }
    .metric-card.yellow { border-left-color: #f1c40f; }
    .metric-card.purple { border-left-color: #9b59b6; }
    .metric-card.orange { border-left-color: #e67e22; }
    .metric-label { color: #8892a4; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { color: #ffffff; font-size: 22px; font-weight: 700; margin-top: 4px; }
    .metric-delta-pos { color: #2ecc71; font-size: 11px; margin-top: 2px; }
    .metric-delta-neg { color: #e74c3c; font-size: 11px; margin-top: 2px; }
    .metric-delta-neu { color: #8892a4; font-size: 11px; margin-top: 2px; }
    .section-title {
        color: #ffffff;
        font-size: 18px;
        font-weight: 600;
        margin: 24px 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 1px solid #2a2d3e;
    }
    .canal-card {
        background: linear-gradient(135deg, #1e2130, #252840);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 8px;
        border: 1px solid #2a2d3e;
    }
    .canal-title { color: #4f8ef7; font-size: 14px; font-weight: 700; margin-bottom: 8px; }
    .canal-metric { color: #8892a4; font-size: 11px; }
    .canal-value { color: #ffffff; font-size: 18px; font-weight: 600; }
    .alert-banner {
        background: linear-gradient(135deg, #3d1010, #4d1515);
        border: 1px solid #e74c3c;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 16px;
        color: #ff6b6b;
        font-weight: 600;
    }
    .roi-green  { color: #2ecc71; font-size: 22px; font-weight: 700; }
    .roi-yellow { color: #f1c40f; font-size: 22px; font-weight: 700; }
    .roi-red    { color: #e74c3c; font-size: 22px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

PLOTLY_THEME = dict(
    plot_bgcolor="#0f1117",
    paper_bgcolor="#0f1117",
    font_color="#8892a4",
    title_font_color="#ffffff",
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
            <div style='text-align:center; margin-bottom:24px;'>
                <span style='font-size:48px;'>📊</span>
                <h2 style='color:#ffffff; margin:8px 0 4px 0;'>Dashboard Performance</h2>
                <p style='color:#8892a4;'>Shopee Affiliate Analytics</p>
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

def sparkline(df_daily, col, color="#4f8ef7"):
    df14 = df_daily.tail(14)
    fig = go.Figure(go.Scatter(
        x=df14["Data"], y=df14[col],
        mode="lines", line=dict(color=color, width=1.5),
        fill="tozeroy", fillcolor=color + "33",
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

    st.markdown("# 📊 Dashboard de Performance")
    st.markdown("---")

    with st.spinner("A carregar dados..."):
        df_raw = ler_dados()

    if df_raw.empty:
        st.error("Sem dados disponíveis. Verifica a planilha.")
        return

    # ── SIDEBAR ──
    with st.sidebar:
        st.markdown("## 🎛️ Filtros")
        data_min = df_raw["Data"].min().date()
        data_max = df_raw["Data"].max().date()
        datas = st.date_input("Período", value=(data_min, data_max),
                              min_value=data_min, max_value=data_max)
        if isinstance(datas, tuple) and len(datas) == 2:
            d_ini, d_fim = datas
        else:
            d_ini, d_fim = data_min, data_max

        sid2_opts = sorted(df_raw["Sub_id2"].unique())
        sid2_sel  = st.multiselect("Canal (Sub_id2)", sid2_opts, default=sid2_opts)
        sid1_opts = sorted(df_raw["Sub_id1"].unique())
        sid1_sel  = st.multiselect("Sub_id1", sid1_opts, default=sid1_opts)
        sid3_opts = sorted(df_raw["Sub_id3"].unique())
        sid3_sel  = st.multiselect("Sub_id3", sid3_opts, default=sid3_opts)

        st.markdown("---")
        if st.button("🔄 Actualizar dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.markdown(f"👤 **{st.session_state.get('usuario','')}**")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # Aplicar filtros
    df = df_raw[
        (df_raw["Data"].dt.date >= d_ini) &
        (df_raw["Data"].dt.date <= d_fim) &
        (df_raw["Sub_id2"].isin(sid2_sel)) &
        (df_raw["Sub_id1"].isin(sid1_sel)) &
        (df_raw["Sub_id3"].isin(sid3_sel))
    ]
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
             sparkline(df_daily,"Comissao","#4f8ef7"))
    with c2:
        d = delta_html(m["lucro_total"], m_ant["lucro_total"]) if m_ant else ""
        cor = "green" if m["lucro_total"] >= 0 else "red"
        card("Lucro Total", fmt_brl(m["lucro_total"]), cor, d,
             sparkline(df_daily,"Comissao","#2ecc71"))
    with c3:
        roi_val = m["roi"]
        cor_roi = "green" if roi_val > 1 else ("yellow" if roi_val >= 0 else "red")
        card("ROI", f"{roi_val:.2f}", cor_roi)
    with c4:
        d = delta_html(m["vendas"], m_ant["vendas"]) if m_ant else ""
        card("Vendas", fmt_num(m["vendas"]), "purple", d,
             sparkline(df_daily,"Vendas","#9b59b6"))
    with c5:
        d = delta_html(m["cliques"], m_ant["cliques"]) if m_ant else ""
        card("Cliques Shopee", fmt_num(m["cliques"]), "yellow", d,
             sparkline(df_daily,"Cliques","#f1c40f"))
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
        cores = ["#4f8ef7","#2ecc71","#f1c40f","#e74c3c","#9b59b6"]
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

    df_canal = df.groupby("Sub_id2").agg(
        Vendas=("Vendas","sum"),
        Comissao=("Comissao","sum"),
        Cliques=("Cliques","sum"),
    ).reset_index()

    with col1:
        fig_bar = px.bar(df_canal, x="Sub_id2", y="Comissao",
                         title="Comissão por Canal", color="Sub_id2",
                         text="Comissao",
                         color_discrete_sequence=px.colors.qualitative.Set2)
        fig_bar.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
        fig_bar.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        fig_pizza = px.pie(df_canal, names="Sub_id2", values="Vendas",
                           title="Distribuição de Vendas por Canal",
                           color_discrete_sequence=px.colors.qualitative.Set2)
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
                     color_discrete_sequence=["#2ecc71"])
        fig.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
        fig.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        bot5 = df_sid3.nsmallest(5,"Comissao")
        fig = px.bar(bot5, x="Comissao", y="Sub_id3", orientation="h",
                     title="📉 Bottom 5 por Comissão", text="Comissao",
                     color_discrete_sequence=["#e74c3c"])
        fig.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
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
        color_discrete_sequence=px.colors.qualitative.Set2,
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
        fig_funil = go.Figure(go.Funnel(
            y=["Impressões","Alcance","Cliques Meta","Vendas"],
            x=[m_pago["impressoes"],m_pago["alcance"],
               m_pago["cliques_meta"],m_pago["vendas"]],
            textinfo="value+percent initial",
            marker=dict(color=["#4f8ef7","#9b59b6","#f1c40f","#2ecc71"])
        ))
        fig_funil.update_layout(title="Funil: Impressões → Vendas", **PLOTLY_THEME)
        st.plotly_chart(fig_funil, use_container_width=True)

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
                           color_discrete_sequence=["#e74c3c"])
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

    st.markdown("---")
    st.caption(f"Dados actualizados a cada 5 min · {len(df)} linhas · Período: {d_ini} a {d_fim}")


if __name__ == "__main__":
    main()
