import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import json
import os

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
        margin-bottom: 8px;
    }
    .metric-card.green  { border-left-color: #2ecc71; }
    .metric-card.red    { border-left-color: #e74c3c; }
    .metric-card.yellow { border-left-color: #f1c40f; }
    .metric-card.purple { border-left-color: #9b59b6; }
    .metric-label { color: #8892a4; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { color: #ffffff; font-size: 24px; font-weight: 700; margin-top: 4px; }
    .metric-delta { font-size: 12px; margin-top: 4px; }
    .section-title {
        color: #ffffff;
        font-size: 18px;
        font-weight: 600;
        margin: 24px 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 1px solid #2a2d3e;
    }
    .stSelectbox label, .stMultiSelect label, .stDateInput label { color: #8892a4 !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  AUTENTICAÇÃO
# ─────────────────────────────────────────────
@st.cache_resource
def autenticar():
    # Tenta ler credenciais dos secrets do Streamlit (produção)
    # ou do ficheiro local (desenvolvimento)
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
@st.cache_data(ttl=300)  # cache 5 minutos
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

    # Renomear colunas pelos índices para garantir consistência
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
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_pct(val):
    return f"{val:.2f}%".replace(".", ",")

def fmt_num(val):
    return f"{int(val):,}".replace(",", ".")

def card(label, value, color="blue"):
    st.markdown(f"""
    <div class="metric-card {color}">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
    </div>""", unsafe_allow_html=True)

def calcular(df):
    cliques      = df["Cliques"].sum()
    vendas       = df["Vendas"].sum()
    comissao     = df["Comissao"].sum()
    lucro        = df["Lucro"].sum()
    invest       = df["Investimento"].sum()
    impressoes   = df["Impressoes"].sum()
    alcance      = df["Alcance"].sum()
    cliques_meta = df["Cliques_Meta"].sum()
    roi          = (lucro / invest * 100) if invest > 0 else 0
    ctr_shopee   = (vendas / cliques * 100) if cliques > 0 else 0
    ctr_meta     = (cliques_meta / alcance * 100) if alcance > 0 else 0
    ctr_cv       = (vendas / cliques_meta * 100) if cliques_meta > 0 else 0
    freq         = impressoes / alcance if alcance > 0 else 0
    cpm_imp      = (invest / impressoes * 1000) if impressoes > 0 else 0
    cpm_alc      = (invest / alcance * 1000) if alcance > 0 else 0
    cpc          = invest / cliques_meta if cliques_meta > 0 else 0
    cac          = invest / vendas if vendas > 0 else 0
    return dict(cliques=cliques, vendas=vendas, comissao=comissao, lucro=lucro,
                invest=invest, impressoes=impressoes, alcance=alcance,
                cliques_meta=cliques_meta, roi=roi, ctr_shopee=ctr_shopee,
                ctr_meta=ctr_meta, ctr_cv=ctr_cv, freq=freq,
                cpm_imp=cpm_imp, cpm_alc=cpm_alc, cpc=cpc, cac=cac)


PLOTLY_THEME = dict(
    plot_bgcolor="#0f1117",
    paper_bgcolor="#0f1117",
    font_color="#8892a4",
    title_font_color="#ffffff",
)


# ─────────────────────────────────────────────
#  APP
# ─────────────────────────────────────────────
def main():
    # Header
    st.markdown("# 📊 Dashboard de Performance")
    st.markdown("---")

    # Carregar dados
    with st.spinner("A carregar dados..."):
        df_raw = ler_dados()

    if df_raw.empty:
        st.error("Sem dados disponíveis. Verifica a planilha.")
        return

    # ── SIDEBAR — FILTROS ──
    with st.sidebar:
        st.markdown("## 🎛️ Filtros")

        # Filtro de datas
        data_min = df_raw["Data"].min().date()
        data_max = df_raw["Data"].max().date()
        datas = st.date_input("Período", value=(data_min, data_max),
                              min_value=data_min, max_value=data_max)
        if isinstance(datas, tuple) and len(datas) == 2:
            d_ini, d_fim = datas
        else:
            d_ini, d_fim = data_min, data_max

        # Filtros Sub_ids
        sid2_opts = sorted(df_raw["Sub_id2"].unique())
        sid2_sel  = st.multiselect("Canal (Sub_id2)", sid2_opts, default=sid2_opts)

        sid1_opts = sorted(df_raw["Sub_id1"].unique())
        sid1_sel  = st.multiselect("Sub_id1", sid1_opts, default=sid1_opts)

        sid3_opts = sorted(df_raw["Sub_id3"].unique())
        sid3_sel  = st.multiselect("Sub_id3", sid3_opts, default=sid3_opts)

        st.markdown("---")
        if st.button("🔄 Actualizar dados"):
            st.cache_data.clear()
            st.rerun()

    # Aplicar filtros
    df = df_raw[
        (df_raw["Data"].dt.date >= d_ini) &
        (df_raw["Data"].dt.date <= d_fim) &
        (df_raw["Sub_id2"].isin(sid2_sel)) &
        (df_raw["Sub_id1"].isin(sid1_sel)) &
        (df_raw["Sub_id3"].isin(sid3_sel))
    ]

    if df.empty:
        st.warning("Sem dados para os filtros seleccionados.")
        return

    m = calcular(df)
    df_pago = df[df["Sub_id2"].str.lower() == "pago"]
    m_pago  = calcular(df_pago) if len(df_pago) > 0 else None

    # ── KPIs GERAIS ──
    st.markdown('<div class="section-title">💰 KPIs Gerais</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: card("Comissão", fmt_brl(m["comissao"]), "blue")
    with c2: card("Lucro", fmt_brl(m["lucro"]), "green" if m["lucro"] >= 0 else "red")
    with c3: card("ROI", fmt_pct(m["roi"]), "green" if m["roi"] >= 0 else "red")
    with c4: card("Vendas", fmt_num(m["vendas"]), "purple")
    with c5: card("Cliques", fmt_num(m["cliques"]), "yellow")
    with c6: card("CTR Shopee", fmt_pct(m["ctr_shopee"]), "blue")

    # ── KPIs PAGO ──
    if m_pago:
        st.markdown('<div class="section-title">📣 KPIs Campanha (Pago)</div>', unsafe_allow_html=True)
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        with c1: card("Investimento", fmt_brl(m_pago["invest"]), "red")
        with c2: card("CPM Impressões", fmt_brl(m_pago["cpm_imp"]), "yellow")
        with c3: card("CPM Alcance", fmt_brl(m_pago["cpm_alc"]), "yellow")
        with c4: card("CPC", fmt_brl(m_pago["cpc"]), "blue")
        with c5: card("CAC", fmt_brl(m_pago["cac"]), "purple")
        with c6: card("Frequência", f"{m_pago['freq']:.2f}x", "blue")
        with c7: card("CTR Meta", fmt_pct(m_pago["ctr_meta"]), "green")

    st.markdown("---")

    # ── EVOLUÇÃO TEMPORAL ──
    st.markdown('<div class="section-title">📈 Evolução Temporal</div>', unsafe_allow_html=True)

    df_daily = df.groupby("Data").agg(
        Vendas=("Vendas","sum"),
        Comissao=("Comissao","sum"),
        Lucro=("Lucro","sum"),
        Cliques=("Cliques","sum"),
    ).reset_index()

    metrica_linha = st.selectbox("Métrica", ["Lucro","Comissao","Vendas","Cliques"])
    fig_linha = px.line(df_daily, x="Data", y=metrica_linha,
                        title=f"Evolução de {metrica_linha}",
                        markers=True, color_discrete_sequence=["#4f8ef7"])
    fig_linha.update_layout(**PLOTLY_THEME)
    st.plotly_chart(fig_linha, use_container_width=True)

    # ── COMPARAÇÃO POR CANAL ──
    st.markdown('<div class="section-title">📊 Comparação por Canal</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    df_canal = df.groupby("Sub_id2").agg(
        Vendas=("Vendas","sum"),
        Comissao=("Comissao","sum"),
        Lucro=("Lucro","sum"),
        Cliques=("Cliques","sum"),
    ).reset_index()

    with col1:
        fig_bar = px.bar(df_canal, x="Sub_id2", y="Lucro",
                         title="Lucro por Canal", color="Sub_id2",
                         color_discrete_sequence=px.colors.qualitative.Set2)
        fig_bar.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        fig_pizza = px.pie(df_canal, names="Sub_id2", values="Vendas",
                           title="Distribuição de Vendas por Canal",
                           color_discrete_sequence=px.colors.qualitative.Set2)
        fig_pizza.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig_pizza, use_container_width=True)

    # ── TOP Sub_id3 ──
    st.markdown('<div class="section-title">🏷️ Top Sub_id3</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    df_sid3 = df[df["Sub_id3"] != ""].groupby("Sub_id3").agg(
        Lucro=("Lucro","sum"),
        Vendas=("Vendas","sum"),
        Cliques=("Cliques","sum"),
    ).reset_index()
    df_sid3["CTR"] = (df_sid3["Vendas"] / df_sid3["Cliques"] * 100).fillna(0)

    with col1:
        top_lucro = df_sid3.nlargest(10, "Lucro")
        fig = px.bar(top_lucro, x="Lucro", y="Sub_id3", orientation="h",
                     title="Top 10 por Lucro", color_discrete_sequence=["#2ecc71"])
        fig.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        top_ctr = df_sid3.nlargest(10, "CTR")
        fig = px.bar(top_ctr, x="CTR", y="Sub_id3", orientation="h",
                     title="Top 10 por CTR (%)", color_discrete_sequence=["#4f8ef7"])
        fig.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig, use_container_width=True)

    # ── SCATTER: Cliques vs Vendas ──
    st.markdown('<div class="section-title">🔍 Análise Micro — Cliques vs Vendas por Sub_id1</div>', unsafe_allow_html=True)
    df_sid1 = df.groupby(["Sub_id1","Sub_id2"]).agg(
        Cliques=("Cliques","sum"),
        Vendas=("Vendas","sum"),
        Lucro=("Lucro","sum"),
    ).reset_index()
    fig_scatter = px.scatter(df_sid1, x="Cliques", y="Vendas", color="Sub_id2",
                             size="Lucro", hover_name="Sub_id1",
                             title="Cliques vs Vendas (tamanho = Lucro)",
                             color_discrete_sequence=px.colors.qualitative.Set2)
    fig_scatter.update_layout(**PLOTLY_THEME)
    st.plotly_chart(fig_scatter, use_container_width=True)

    # ── FUNIL PAGO ──
    if m_pago and m_pago["impressoes"] > 0:
        st.markdown('<div class="section-title">🔽 Funil de Conversão (Pago)</div>', unsafe_allow_html=True)
        funil_vals  = [m_pago["impressoes"], m_pago["alcance"],
                       m_pago["cliques_meta"], m_pago["vendas"]]
        funil_nomes = ["Impressões", "Alcance", "Cliques Meta", "Vendas"]
        fig_funil = go.Figure(go.Funnel(
            y=funil_nomes, x=funil_vals,
            textinfo="value+percent initial",
            marker=dict(color=["#4f8ef7","#9b59b6","#f1c40f","#2ecc71"])
        ))
        fig_funil.update_layout(title="Funil: Impressões → Vendas", **PLOTLY_THEME)
        st.plotly_chart(fig_funil, use_container_width=True)

    # ── EVOLUÇÃO CPM/CPC/CAC (Pago) ──
    if len(df_pago) > 0:
        st.markdown('<div class="section-title">📉 Evolução CPM / CPC / CAC (Pago)</div>', unsafe_allow_html=True)
        df_pago_daily = df_pago.groupby("Data").agg(
            Investimento=("Investimento","sum"),
            Impressoes=("Impressoes","sum"),
            Alcance=("Alcance","sum"),
            Cliques_Meta=("Cliques_Meta","sum"),
            Vendas=("Vendas","sum"),
        ).reset_index()
        df_pago_daily["CPM_Imp"] = (df_pago_daily["Investimento"] / df_pago_daily["Impressoes"] * 1000).fillna(0)
        df_pago_daily["CPC"]     = (df_pago_daily["Investimento"] / df_pago_daily["Cliques_Meta"]).fillna(0)
        df_pago_daily["CAC"]     = (df_pago_daily["Investimento"] / df_pago_daily["Vendas"]).fillna(0)

        metrica_pago = st.selectbox("Métrica Pago", ["CPM_Imp","CPC","CAC"])
        fig_pago = px.line(df_pago_daily, x="Data", y=metrica_pago,
                           title=f"Evolução de {metrica_pago} (Pago)",
                           markers=True, color_discrete_sequence=["#e74c3c"])
        fig_pago.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig_pago, use_container_width=True)

    # ── TABELA DETALHADA ──
    st.markdown('<div class="section-title">📋 Dados Detalhados</div>', unsafe_allow_html=True)
    colunas_tabela = ["Data","Sub_id2","Sub_id1","Sub_id3",
                      "Cliques","Vendas","Comissao","Lucro","Investimento"]
    df_tabela = df[colunas_tabela].copy()
    df_tabela["Data"] = df_tabela["Data"].dt.strftime("%Y-%m-%d")
    st.dataframe(df_tabela, use_container_width=True, height=400)

    st.markdown("---")
    st.caption(f"Dados actualizados da planilha Google Sheets · {len(df)} linhas carregadas")


if __name__ == "__main__":
    main()
