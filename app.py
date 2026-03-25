import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import date, timedelta
import requests
import numpy as np

SPREADSHEET_ID  = "1qhdazuPU5B36vwRyc8Be3h9fgXok1dSuDT8mvMBD2eI"
SHEET_NAME      = "Resultados Shopee"
SHEET_PAGO      = "Resultados Pago"
SHEET_AWARENESS = "Resultado Awareness"
SCOPES          = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

st.set_page_config(page_title="Dashboard de Performance", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
html,body,[data-testid="stAppViewContainer"],[data-testid="stApp"]{background-color:#0f0d0b!important;color:#f6e8d8!important;}
[data-testid="stAppViewContainer"]::before{content:"";position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(15,13,11,0.94);z-index:0;pointer-events:none;}
[data-testid="stMain"]{position:relative;z-index:1;}
[data-testid="stSidebar"]{background-color:#110e0c!important;border-right:1px solid #3a2c28!important;}
[data-testid="stSidebar"] *{color:#f6e8d8!important;}
[data-testid="stSidebar"] button{background-color:#3a2c28!important;border:1px solid #bd6d34!important;}
[data-testid="stSidebar"] button:hover{background-color:#bd6d34!important;}
.metric-card{background:linear-gradient(135deg,#1e1410,#221a16);border-radius:12px;padding:16px 20px;border-left:4px solid #bd6d34;margin-bottom:4px;}
.metric-card.green{border-left-color:#7a9e4e;}.metric-card.red{border-left-color:#c0392b;}
.metric-card.yellow{border-left-color:#d4a017;}.metric-card.purple{border-left-color:#9c5834;}
.metric-card.orange{border-left-color:#bd6d34;}
.metric-label{color:#c5936d;font-size:11px;text-transform:uppercase;letter-spacing:1px;}
.metric-value{color:#f6e8d8;font-size:22px;font-weight:700;margin-top:4px;}
.metric-delta-pos{color:#7a9e4e;font-size:11px;margin-top:2px;}
.metric-delta-neg{color:#c0392b;font-size:11px;margin-top:2px;}
.metric-delta-neu{color:#c5936d;font-size:11px;margin-top:2px;}
.section-title{color:#f6e8d8;font-size:18px;font-weight:600;margin:24px 0 12px 0;padding-bottom:8px;border-bottom:1px solid #3a2c28;}
.canal-card{background:linear-gradient(135deg,#1e1410,#221a16);border-radius:12px;padding:16px;margin-bottom:8px;border:1px solid #3a2c28;}
.canal-title{color:#bd6d34;font-size:14px;font-weight:700;margin-bottom:8px;}
.canal-metric{color:#c5936d;font-size:11px;}.canal-value{color:#f6e8d8;font-size:18px;font-weight:600;}
.alert-banner{background:linear-gradient(135deg,#2d1010,#3d1515);border:1px solid #c0392b;border-radius:8px;padding:12px 16px;margin-bottom:16px;color:#e74c3c;font-weight:600;}
.footer{margin-top:40px;padding:20px;border-top:1px solid #3a2c28;text-align:center;color:#c5936d;font-size:12px;}
[data-testid="stExpander"]{background-color:#1a1210!important;border:1px solid #3a2c28!important;border-radius:8px!important;}
</style>""", unsafe_allow_html=True)

PLOTLY_THEME = dict(
    plot_bgcolor="#0f0d0b", paper_bgcolor="#0f0d0b", font_color="#f6e8d8",
    legend=dict(font=dict(color="#f6e8d8",size=12),bgcolor="rgba(30,18,16,0.8)",bordercolor="#3a2c28",borderwidth=1),
    xaxis=dict(color="#c5936d",gridcolor="#2a1f1a"),
    yaxis=dict(color="#c5936d",gridcolor="#2a1f1a"),
)

def parse_num(s):
    s = str(s).strip().replace("R$","").replace("%","").strip()
    if not s or s in ["-","nan","None",""]: return 0.0
    if "," in s: s = s.replace(".","").replace(",",".")
    else: s = s.replace(",",".")
    try: return float(s)
    except: return 0.0

def fmt_brl(v): return "R$ {:,.2f}".format(v).replace(",","X").replace(".",",").replace("X",".")
def fmt_pct(v): return "{:.2f}%".format(v).replace(".",",")
def fmt_num(v): return "{:,}".format(int(v)).replace(",",".")

def card(label, value, color="blue", delta_html_str="", sparkline_fig=None):
    html = '<div class="metric-card {}"><div class="metric-label">{}</div><div class="metric-value">{}</div>{}</div>'.format(
        color, label, str(value), delta_html_str or "")
    st.markdown(html, unsafe_allow_html=True)
    if sparkline_fig:
        st.plotly_chart(sparkline_fig, use_container_width=True, config={"displayModeBar":False})

def delta_html(val, ref):
    if not ref or ref == 0: return '<span class="metric-delta-neu">sem ref. anterior</span>'
    pct = (val-ref)/abs(ref)*100
    if pct > 0:   return '<span class="metric-delta-pos">▲ {:.1f}% vs semana ant.</span>'.format(pct)
    elif pct < 0: return '<span class="metric-delta-neg">▼ {:.1f}% vs semana ant.</span>'.format(abs(pct))
    return '<span class="metric-delta-neu">= igual semana ant.</span>'

def sparkline(df_d, col, color="#bd6d34"):
    if col not in df_d.columns or df_d[col].sum()==0: return None
    df14 = df_d.tail(14)
    fig = go.Figure(go.Scatter(x=df14.index if "Data" not in df14.columns else df14["Data"],
        y=df14[col], mode="lines", line=dict(color=color,width=1.5),
        fill="tozeroy", fillcolor="rgba(189,109,52,0.15)"))
    fig.update_layout(height=50, margin=dict(l=0,r=0,t=0,b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        plot_bgcolor="#0f0d0b", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
    return fig

def calcular(df):
    cliques=df["Cliques"].sum(); vendas=df["Vendas"].sum(); comissao=df["Comissao"].sum()
    invest=df["Investimento"].sum() if "Investimento" in df.columns else 0
    impressoes=df["Impressoes"].sum() if "Impressoes" in df.columns else 0
    alcance=df["Alcance"].sum() if "Alcance" in df.columns else 0
    cliques_meta=df["Cliques_Meta"].sum() if "Cliques_Meta" in df.columns else 0
    lucro_total=comissao-invest; roi=(comissao-invest)/invest if invest>0 else 0
    ctr_shopee=(vendas/cliques*100) if cliques>0 else 0
    ctr_meta=(cliques_meta/alcance*100) if alcance>0 else 0
    ctr_cv=(vendas/cliques_meta*100) if cliques_meta>0 else 0
    freq=impressoes/alcance if alcance>0 else 0
    cpm_imp=(invest/impressoes*1000) if impressoes>0 else 0
    cpm_alc=(invest/alcance*1000) if alcance>0 else 0
    cpc=invest/cliques_meta if cliques_meta>0 else 0
    cac=invest/vendas if vendas>0 else 0
    ticket_medio=comissao/vendas if vendas>0 else 0
    return dict(cliques=cliques,vendas=vendas,comissao=comissao,invest=invest,
                impressoes=impressoes,alcance=alcance,cliques_meta=cliques_meta,
                lucro_total=lucro_total,roi=roi,ctr_shopee=ctr_shopee,
                ctr_meta=ctr_meta,ctr_cv=ctr_cv,freq=freq,
                cpm_imp=cpm_imp,cpm_alc=cpm_alc,cpc=cpc,cac=cac,ticket_medio=ticket_medio)

def semana_anterior(df, d_ini, d_fim):
    delta=d_fim-d_ini; ant_fim=d_ini-timedelta(days=1); ant_ini=ant_fim-delta
    return df[(df["Data"].dt.date>=ant_ini)&(df["Data"].dt.date<=ant_fim)]

def verificar_alerta_roi(df_pago_raw_periodo):
    if df_pago_raw_periodo.empty: return False
    dd=df_pago_raw_periodo.groupby("Data").agg(I=("Investimento","sum")).reset_index().sort_values("Data").tail(3)
    return False  # Simplificado por agora

@st.cache_resource
def autenticar():
    try: creds=Credentials.from_service_account_info(st.secrets["gcp_service_account"],scopes=SCOPES)
    except: creds=Credentials.from_service_account_file("/Users/anacarol/automacao/automacao-planilhas-490816-ee73c7ff4bf2.json",scopes=SCOPES)
    return build("sheets","v4",credentials=creds)

@st.cache_data(ttl=300)
def ler_dados():
    """Resultados Shopee A:H = Data,Sub_id2,Sub_id1,Sub_id3,Cliques,Vendas,CTR,Comissao"""
    svc=autenticar()
    res=svc.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID,range=f"{SHEET_NAME}!A1:H").execute()
    vals=res.get("values",[])
    if len(vals)<2: return pd.DataFrame()
    cab=vals[0]; linhas=vals[1:]
    mc=len(cab); ln=[l+[""]*(mc-len(l)) for l in linhas]
    df=pd.DataFrame(ln,columns=cab)
    nomes=["Data","Sub_id2","Sub_id1","Sub_id3","Cliques","Vendas","CTR","Comissao"]
    df=df.rename(columns={df.columns[i]:nomes[i] for i in range(min(len(df.columns),len(nomes)))})
    for col in ["Cliques","Vendas","Comissao"]: df[col]=df[col].apply(parse_num)
    df["Data"]=pd.to_datetime(df["Data"],errors="coerce")
    df=df.dropna(subset=["Data"])
    df["Sub_id2"]=df["Sub_id2"].fillna("").str.strip()
    df["Sub_id1"]=df["Sub_id1"].fillna("").str.strip()
    df["Sub_id3"]=df["Sub_id3"].fillna("").str.strip()
    return df

@st.cache_data(ttl=300)
def ler_pago():
    """Resultados Pago: Data|Sub_id2|Sub_id1|Sub_id3|Investimento|Impressoes|Alcance|Cliques_Meta"""
    svc=autenticar()
    res=svc.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID,range=f"{SHEET_PAGO}!A1:L").execute()
    vals=res.get("values",[])
    if len(vals)<2: return pd.DataFrame()
    cab=vals[0]; linhas=vals[1:]
    mc=max(len(l) for l in [cab]+linhas)
    ln=[l+[""]*(mc-len(l)) for l in linhas]
    df=pd.DataFrame(ln,columns=(cab+["_"]*mc)[:mc])
    r=pd.DataFrame()
    r["Data"]=pd.to_datetime(df.iloc[:,0],dayfirst=True,errors="coerce")
    r["Sub_id2"]=df.iloc[:,1].astype(str).str.strip()
    r["Sub_id1"]=df.iloc[:,2].astype(str).str.strip()
    r["Sub_id3"]=df.iloc[:,3].astype(str).str.strip() if df.shape[1]>3 else ""
    r["Investimento"]=df.iloc[:,4].apply(parse_num) if df.shape[1]>4 else 0.0
    r["Impressoes"]=df.iloc[:,5].apply(parse_num) if df.shape[1]>5 else 0.0
    r["Alcance"]=df.iloc[:,6].apply(parse_num) if df.shape[1]>6 else 0.0
    r["Cliques_Meta"]=df.iloc[:,7].apply(parse_num) if df.shape[1]>7 else 0.0
    r=r.dropna(subset=["Data"])
    r=r[r["Investimento"]>0]
    return r

@st.cache_data(ttl=300)
def ler_awareness():
    """Resultado Awareness: Data|Sub_id2|Investimento|Impressoes|Alcance|Visitas_Perfil|Seguidores|Comentarios"""
    svc=autenticar()
    res=svc.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID,range=f"{SHEET_AWARENESS}!A1:H").execute()
    vals=res.get("values",[])
    if len(vals)<2: return pd.DataFrame()
    cab=vals[0]; linhas=vals[1:]
    mc=max(len(l) for l in [cab]+linhas)
    ln=[l+[""]*(mc-len(l)) for l in linhas]
    df=pd.DataFrame(ln,columns=(cab+["_"]*mc)[:mc])
    r=pd.DataFrame()
    r["Data"]=pd.to_datetime(df.iloc[:,0],dayfirst=True,errors="coerce")
    # col0=Data, col1=Sub_id2, col2=Investimento, col3=Impressoes, col4=Alcance, col5=Visitas, col6=Seguidores, col7=Comentarios
    r["Investimento_aw"]=df.iloc[:,2].apply(parse_num) if df.shape[1]>2 else 0.0
    r["Impressoes_aw"]=df.iloc[:,3].apply(parse_num) if df.shape[1]>3 else 0.0
    r["Alcance_aw"]=df.iloc[:,4].apply(parse_num) if df.shape[1]>4 else 0.0
    r["Visitas_Perfil"]=df.iloc[:,5].apply(parse_num) if df.shape[1]>5 else 0.0
    r["Seguidores"]=df.iloc[:,6].apply(parse_num) if df.shape[1]>6 else 0.0
    r["Comentarios"]=df.iloc[:,7].apply(parse_num) if df.shape[1]>7 else 0.0
    r=r.dropna(subset=["Data"])
    r=r[r["Investimento_aw"]>0]
    return r

def check_login():
    try: users=dict(st.secrets["users"])
    except: users={"brenno":"destr@vA!"}
    if "logged_in" not in st.session_state: st.session_state.logged_in=False
    if not st.session_state.logged_in:
        c1,c2,c3=st.columns([1,1.2,1])
        with c2:
            st.markdown("<br><br>",unsafe_allow_html=True)
            st.markdown("""<div style='text-align:center;padding:24px;background:linear-gradient(135deg,#1a1210,#221a16);border-radius:16px;border:1px solid #3a2c28;'>
            <div style='font-size:48px;'>🔓</div><h2 style='color:#f6e8d8;'>DESTRAVA</h2>
            <p style='color:#bd6d34;'>por Carol Matos · Analytics</p></div>""",unsafe_allow_html=True)
            with st.form("login_form"):
                u=st.text_input("Utilizador"); p=st.text_input("Password",type="password")
                if st.form_submit_button("Entrar",use_container_width=True):
                    if u in users and users[u]==p:
                        st.session_state.logged_in=True; st.session_state.usuario=u; st.rerun()
                    else: st.error("Credenciais incorrectas.")
        return False
    return True

def main():
    if not check_login(): return

    with st.sidebar:
        st.markdown('<div style="color:#c5936d;font-size:11px;font-weight:600;margin-bottom:8px;">ATALHOS</div>',unsafe_allow_html=True)
        st.markdown("""
        <a href="#evolucao" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">📈 Evolucao</a>
        <a href="#canais" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">📊 Canais</a>
        <a href="#campeoes" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">🏆 Campeoes</a>
        <a href="#awareness" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">📡 Awareness</a>
        <a href="#funil" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">🔽 Funil</a>
        <a href="#metricas-pago" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">📉 Metricas Pago</a>
        <a href="#ipa" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">🎯 IPA</a>
        <a href="#insights-ia" style="display:block;color:#bd6d34;font-size:12px;text-decoration:none;background:#2a1f1a;padding:6px 12px;border-radius:8px;border:1px solid #bd6d34;text-align:center;">🤖 Insights IA</a>
        """,unsafe_allow_html=True)
        st.markdown("---")
        st.markdown('<div style="color:#c5936d;font-size:11px;">👤 {}</div>'.format(st.session_state.get("usuario","")),unsafe_allow_html=True)
        if st.button("🔄 Actualizar dados",use_container_width=True): st.cache_data.clear(); st.rerun()
        if st.button("🚪 Sair",use_container_width=True): st.session_state.logged_in=False; st.rerun()

    st.markdown("""<div style="margin-bottom:8px;"><h1 style="color:#f6e8d8;margin:0;font-size:28px;">📊 Dashboard de Performance</h1>
    <p style="color:#c5936d;margin:0;font-size:13px;">Destrava · por Carol Matos</p></div>""",unsafe_allow_html=True)
    st.markdown("""<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:16px;padding:8px 16px;background:#1a1210;border-radius:8px;border:1px solid #3a2c28;">
    <span style="color:#c5936d;font-size:11px;font-weight:600;">IR PARA:</span>
    <a href="#evolucao" style="color:#c5936d;font-size:11px;text-decoration:none;background:#1a1210;padding:3px 10px;border-radius:20px;border:1px solid #3a2c28;">📈 Evolucao</a>
    <a href="#canais" style="color:#c5936d;font-size:11px;text-decoration:none;background:#1a1210;padding:3px 10px;border-radius:20px;border:1px solid #3a2c28;">📊 Canais</a>
    <a href="#campeoes" style="color:#c5936d;font-size:11px;text-decoration:none;background:#1a1210;padding:3px 10px;border-radius:20px;border:1px solid #3a2c28;">🏆 Campeoes</a>
    <a href="#awareness" style="color:#c5936d;font-size:11px;text-decoration:none;background:#1a1210;padding:3px 10px;border-radius:20px;border:1px solid #3a2c28;">📡 Awareness</a>
    <a href="#funil" style="color:#c5936d;font-size:11px;text-decoration:none;background:#1a1210;padding:3px 10px;border-radius:20px;border:1px solid #3a2c28;">🔽 Funil</a>
    <a href="#metricas-pago" style="color:#c5936d;font-size:11px;text-decoration:none;background:#1a1210;padding:3px 10px;border-radius:20px;border:1px solid #3a2c28;">📉 Metricas Pago</a>
    <a href="#ipa" style="color:#c5936d;font-size:11px;text-decoration:none;background:#1a1210;padding:3px 10px;border-radius:20px;border:1px solid #3a2c28;">🎯 IPA</a>
    <a href="#insights-ia" style="color:#bd6d34;font-size:11px;text-decoration:none;background:#2a1f1a;padding:3px 10px;border-radius:20px;border:1px solid #bd6d34;">🤖 Insights IA</a>
    </div>""",unsafe_allow_html=True)

    with st.spinner("A carregar dados..."):
        df_raw=ler_dados(); df_pago_raw=ler_pago(); df_aw_raw=ler_awareness()

    if df_raw.empty:
        st.error("Sem dados na planilha Resultados Shopee."); return

    # FILTROS
    data_min=df_raw["Data"].min().date(); data_max=df_raw["Data"].max().date()
    if "preset" not in st.session_state: st.session_state.preset="all"
    preset=st.session_state.get("preset","all")
    if   preset=="7d":  d_ini_def=max(data_max-timedelta(days=6),data_min)
    elif preset=="14d": d_ini_def=max(data_max-timedelta(days=13),data_min)
    elif preset=="28d": d_ini_def=max(data_max-timedelta(days=27),data_min)
    elif preset=="30d": d_ini_def=max(data_max-timedelta(days=29),data_min)
    else:               d_ini_def=data_min
    d_fim_def=data_max

    sid2_opts=sorted([x for x in df_raw["Sub_id2"].unique() if x.strip()])
    sid1_opts=sorted([x for x in df_raw["Sub_id1"].unique() if x.strip()])
    sid3_opts=sorted([x for x in df_raw["Sub_id3"].unique() if x.strip()])

    with st.expander("🎛️ Filtros",expanded=False):
        st.markdown('<div style="color:#bd6d34;font-size:12px;font-weight:700;margin-bottom:6px;">📅 Periodo</div>',unsafe_allow_html=True)
        b1,b2,b3,b4,b5=st.columns(5)
        with b1:
            if st.button("7 dias",use_container_width=True,key="b7"): st.session_state.preset="7d"; st.rerun()
        with b2:
            if st.button("14 dias",use_container_width=True,key="b14"): st.session_state.preset="14d"; st.rerun()
        with b3:
            if st.button("28 dias",use_container_width=True,key="b28"): st.session_state.preset="28d"; st.rerun()
        with b4:
            if st.button("30 dias",use_container_width=True,key="b30"): st.session_state.preset="30d"; st.rerun()
        with b5:
            if st.button("Tudo",use_container_width=True,key="ba"): st.session_state.preset="all"; st.rerun()
        datas=st.date_input("",value=(d_ini_def,d_fim_def),min_value=data_min,max_value=data_max,label_visibility="collapsed")
        d_ini,d_fim=(datas if isinstance(datas,tuple) and len(datas)==2 else (d_ini_def,d_fim_def))
        st.markdown("<hr style='border-color:#3a2c28;margin:10px 0;'>",unsafe_allow_html=True)
        st.markdown('<div style="color:#bd6d34;font-size:12px;font-weight:700;margin-bottom:4px;">Canal (Sub_id2)</div>',unsafe_allow_html=True)
        sid2_sel=st.multiselect("",sid2_opts,default=[],placeholder="Todos",label_visibility="collapsed",key="ms2")
        st.markdown("<hr style='border-color:#3a2c28;margin:10px 0;'>",unsafe_allow_html=True)
        st.markdown('<div style="color:#bd6d34;font-size:12px;font-weight:700;margin-bottom:4px;">Sub_id1</div>',unsafe_allow_html=True)
        sid1_sel=st.multiselect("",sid1_opts,default=[],placeholder="Todos",label_visibility="collapsed",key="ms1")
        st.markdown("<hr style='border-color:#3a2c28;margin:10px 0;'>",unsafe_allow_html=True)
        st.markdown('<div style="color:#bd6d34;font-size:12px;font-weight:700;margin-bottom:4px;">Sub_id3</div>',unsafe_allow_html=True)
        sid3_sel=st.multiselect("",sid3_opts,default=[],placeholder="Todos",label_visibility="collapsed",key="ms3")

    if not sid2_sel: sid2_sel=sid2_opts
    if not sid1_sel: sid1_sel=sid1_opts
    if not sid3_sel: sid3_sel=sid3_opts

    # FILTRAR df_raw (so vendas/cliques/comissao - sem investimento)
    mask=((df_raw["Data"].dt.date>=d_ini)&(df_raw["Data"].dt.date<=d_fim))
    if sid2_sel!=sid2_opts: mask=mask&df_raw["Sub_id2"].isin(sid2_sel)
    if sid1_sel!=sid1_opts: mask=mask&df_raw["Sub_id1"].isin(sid1_sel)
    if sid3_sel!=sid3_opts: mask=mask&df_raw["Sub_id3"].isin(sid3_sel)
    df=df_raw[mask].copy()

    # FILTRAR df_pago_raw pelo mesmo periodo
    mask_p=(df_pago_raw["Data"].dt.date>=d_ini)&(df_pago_raw["Data"].dt.date<=d_fim) if not df_pago_raw.empty else pd.Series(dtype=bool)
    if not df_pago_raw.empty:
        if sid1_sel!=sid1_opts: mask_p=mask_p&df_pago_raw["Sub_id1"].isin(sid1_sel)
    df_pago_periodo=df_pago_raw[mask_p].copy() if not df_pago_raw.empty else pd.DataFrame()

    # FILTRAR awareness
    df_aw=df_aw_raw[(df_aw_raw["Data"].dt.date>=d_ini)&(df_aw_raw["Data"].dt.date<=d_fim)].copy() if not df_aw_raw.empty else pd.DataFrame()

    if df.empty:
        st.markdown('<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:10px;padding:24px;text-align:center;"><div style="font-size:32px;">📭</div><div style="color:#f6e8d8;font-size:16px;">Sem dados para o periodo seleccionado</div><div style="color:#c5936d;font-size:13px;">Dados disponiveis ate {}.</div></div>'.format(data_max),unsafe_allow_html=True)
        st.stop()

    # CALCULAR METRICAS
    # Investimento vem SEMPRE do df_pago_raw (nunca do df merged)
    invest_pago=df_pago_periodo["Investimento"].sum() if not df_pago_periodo.empty else 0.0
    # Awareness: usar SEMPRE o total acumulado (df_aw_raw), nao apenas o periodo filtrado
    invest_aw=df_aw_raw["Investimento_aw"].sum() if not df_aw_raw.empty else 0.0
    invest_total=invest_pago+invest_aw

    # Metricas de vendas/comissao do df (Resultados Shopee)
    m=calcular(df)
    # Substituir investimento pelo valor real do df_pago_raw
    m["invest"]=invest_pago
    m["invest_total"]=invest_total
    m["lucro_total"]=m["comissao"]-invest_total
    m["roi"]=(m["comissao"]-invest_total)/invest_total if invest_total>0 else 0

    # Metricas para o funil (Impressoes/Alcance/Cliques_Meta vem do df_pago_raw)
    if not df_pago_periodo.empty:
        m["impressoes"]=df_pago_periodo["Impressoes"].sum()
        m["alcance"]=df_pago_periodo["Alcance"].sum()
        m["cliques_meta"]=df_pago_periodo["Cliques_Meta"].sum()
        m["ctr_meta"]=(m["cliques_meta"]/m["alcance"]*100) if m["alcance"]>0 else 0
        m["ctr_cv"]=(m["vendas"]/m["cliques_meta"]*100) if m["cliques_meta"]>0 else 0
        m["freq"]=m["impressoes"]/m["alcance"] if m["alcance"]>0 else 0
        m["cpm_imp"]=(invest_pago/m["impressoes"]*1000) if m["impressoes"]>0 else 0
        m["cpm_alc"]=(invest_pago/m["alcance"]*1000) if m["alcance"]>0 else 0
        m["cpc"]=invest_pago/m["cliques_meta"] if m["cliques_meta"]>0 else 0
        m["cac"]=invest_pago/m["vendas"] if m["vendas"]>0 else 0

    df_ant=semana_anterior(df_raw,d_ini,d_fim)
    m_ant=calcular(df_ant) if not df_ant.empty else None
    m_ant_v=m_ant if m_ant else {}

    # Metricas por canal
    df_pago_v =df[df["Sub_id2"].str.lower()=="pago"]
    df_org    =df[df["Sub_id2"].str.lower()=="organico"]
    df_story  =df[df["Sub_id2"].str.lower()=="story"]
    m_pago    =calcular(df_pago_v) if len(df_pago_v)>0 else None
    m_org     =calcular(df_org)    if len(df_org)>0    else None
    m_story   =calcular(df_story)  if len(df_story)>0  else None

    if m_pago:
        m_pago["invest"]=invest_pago
        m_pago["lucro_total"]=m_pago["comissao"]-invest_pago
        m_pago["roi"]=(m_pago["comissao"]-invest_pago)/invest_pago if invest_pago>0 else 0
        if not df_pago_periodo.empty:
            m_pago["impressoes"]=df_pago_periodo["Impressoes"].sum()
            m_pago["alcance"]=df_pago_periodo["Alcance"].sum()
            m_pago["cliques_meta"]=df_pago_periodo["Cliques_Meta"].sum()
            m_pago["cpm_imp"]=(invest_pago/m_pago["impressoes"]*1000) if m_pago["impressoes"]>0 else 0
            m_pago["cpm_alc"]=(invest_pago/m_pago["alcance"]*1000) if m_pago["alcance"]>0 else 0
            m_pago["cpc"]=invest_pago/m_pago["cliques_meta"] if m_pago["cliques_meta"]>0 else 0
            m_pago["cac"]=invest_pago/m_pago["vendas"] if m_pago["vendas"]>0 else 0
            m_pago["ctr_meta"]=(m_pago["cliques_meta"]/m_pago["alcance"]*100) if m_pago["alcance"]>0 else 0
            m_pago["ctr_cv"]=(m_pago["vendas"]/m_pago["cliques_meta"]*100) if m_pago["cliques_meta"]>0 else 0
            m_pago["freq"]=m_pago["impressoes"]/m_pago["alcance"] if m_pago["alcance"]>0 else 0

    df_ant_pago =df_ant[df_ant["Sub_id2"].str.lower()=="pago"]  if not df_ant.empty else pd.DataFrame()
    df_ant_org  =df_ant[df_ant["Sub_id2"].str.lower()=="organico"] if not df_ant.empty else pd.DataFrame()
    df_ant_story=df_ant[df_ant["Sub_id2"].str.lower()=="story"]  if not df_ant.empty else pd.DataFrame()
    m_ant_pago  =calcular(df_ant_pago)  if not df_ant_pago.empty  else None
    m_ant_org   =calcular(df_ant_org)   if not df_ant_org.empty   else None
    m_ant_story =calcular(df_ant_story) if not df_ant_story.empty else None

    # df_daily para sparklines e graficos — investimento vem do df_pago_raw diario
    df_daily=df.groupby("Data").agg(Vendas=("Vendas","sum"),Comissao=("Comissao","sum"),Cliques=("Cliques","sum")).reset_index().sort_values("Data")
    df_daily["Ticket_Medio"]=df_daily.apply(lambda r:r["Comissao"]/r["Vendas"] if r["Vendas"]>0 else 0,axis=1)
    df_daily["CTR_calc"]=df_daily.apply(lambda r:r["Vendas"]/r["Cliques"]*100 if r["Cliques"]>0 else 0,axis=1)
    # Investimento diario do pago_raw
    if not df_pago_periodo.empty:
        inv_daily=df_pago_periodo.groupby("Data").agg(Invest_pago=("Investimento","sum")).reset_index()
        df_daily=df_daily.merge(inv_daily,on="Data",how="left")
        df_daily["Invest_pago"]=df_daily["Invest_pago"].fillna(0)
    else:
        df_daily["Invest_pago"]=0.0
    # Awareness diario (para sparkline e grafico de correlacao)
    if not df_aw.empty:
        inv_aw_daily=df_aw.groupby("Data").agg(Invest_aw=("Investimento_aw","sum")).reset_index()
        df_daily=df_daily.merge(inv_aw_daily,on="Data",how="left")
        df_daily["Invest_aw"]=df_daily["Invest_aw"].fillna(0)
    else:
        df_daily["Invest_aw"]=0.0
    df_daily["Investimento"]=df_daily["Invest_pago"]+df_daily["Invest_aw"]
    df_daily["ROI_calc"]=df_daily.apply(lambda r:(r["Comissao"]-r["Investimento"])/r["Investimento"] if r["Investimento"]>0 else 0,axis=1)

    # KPIs GERAIS
    st.markdown('<div class="section-title">💰 KPIs Gerais</div>',unsafe_allow_html=True)
    r1c1,r1c2,r1c3,r1c4=st.columns(4)
    invest_label="Investimento Total" if invest_aw>0 else "Investimento"
    with r1c1: card("Comissao Total",fmt_brl(m["comissao"]),"blue",delta_html(m["comissao"],m_ant_v.get("comissao",0)),sparkline(df_daily,"Comissao","#bd6d34"))
    with r1c2:
        cor="green" if m["lucro_total"]>=0 else "red"
        card("Lucro Total",fmt_brl(m["lucro_total"]),cor,delta_html(m["lucro_total"],m_ant_v.get("lucro_total",0)),sparkline(df_daily,"Comissao","#9c5834"))
    with r1c3: card(invest_label,fmt_brl(invest_total),"red",delta_html(invest_total,m_ant_v.get("invest",0)),sparkline(df_daily,"Investimento","#c0392b"))
    with r1c4:
        cor_roi="green" if m["roi"]>1 else ("yellow" if m["roi"]>=0 else "red")
        card("ROI","{:.2f}".format(m["roi"]),cor_roi,delta_html(m["roi"],m_ant_v.get("roi",0)),sparkline(df_daily,"ROI_calc","#d4a017"))
    r2c1,r2c2,r2c3,r2c4=st.columns(4)
    with r2c1: card("Cliques Shopee",fmt_num(m["cliques"]),"yellow",delta_html(m["cliques"],m_ant_v.get("cliques",0)),sparkline(df_daily,"Cliques","#d2b095"))
    with r2c2: card("Vendas",fmt_num(m["vendas"]),"purple",delta_html(m["vendas"],m_ant_v.get("vendas",0)),sparkline(df_daily,"Vendas","#9c5834"))
    with r2c3: card("CTR Shopee",fmt_pct(m["ctr_shopee"]),"blue",delta_html(m["ctr_shopee"],m_ant_v.get("ctr_shopee",0)),sparkline(df_daily,"CTR_calc","#bd6d34"))
    with r2c4: card("Ticket Medio",fmt_brl(m["ticket_medio"]),"orange",delta_html(m["ticket_medio"],m_ant_v.get("ticket_medio",0)),sparkline(df_daily,"Ticket_Medio","#bd6d34"))

    # CANAIS
    st.markdown('<div class="section-title">📂 Performance por Canal</div>',unsafe_allow_html=True)
    cc1,cc2,cc3=st.columns(3)
    def canal_card(col,mc,mc_ant,nome,emoji):
        with col:
            if mc:
                def trend(cur,a):
                    if not mc_ant or a==0: return ""
                    pct=(cur-a)/abs(a)*100; cor="#7a9e4e" if pct>0 else "#c0392b"; arr="▲" if pct>0 else "▼"
                    return '<span style="color:{};font-size:10px;">{} {:.1f}%</span>'.format(cor,arr,abs(pct))
                a=mc_ant if mc_ant else {}
                st.markdown("""<div class="canal-card"><div class="canal-title">{e} {n}</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                <div><div class="canal-metric">Vendas</div><div class="canal-value">{v}</div>{tv}</div>
                <div><div class="canal-metric">Comissao</div><div class="canal-value">{c}</div>{tc}</div>
                <div><div class="canal-metric">Cliques</div><div class="canal-value">{cl}</div></div>
                <div><div class="canal-metric">CTR</div><div class="canal-value">{ctr}</div></div>
                <div><div class="canal-metric">Ticket Medio</div><div class="canal-value">{tm}</div></div>
                </div></div>""".format(e=emoji,n=nome,v=fmt_num(mc["vendas"]),tv=trend(mc["vendas"],a.get("vendas",0)),
                c=fmt_brl(mc["comissao"]),tc=trend(mc["comissao"],a.get("comissao",0)),
                cl=fmt_num(mc["cliques"]),ctr=fmt_pct(mc["ctr_shopee"]),tm=fmt_brl(mc["ticket_medio"])),unsafe_allow_html=True)
            else:
                st.markdown('<div class="canal-card"><div class="canal-title">{} {}</div><div style="color:#8892a4;">Sem dados</div></div>'.format(emoji,nome),unsafe_allow_html=True)
    canal_card(cc1,m_pago,m_ant_pago,"Pago","📣")
    canal_card(cc2,m_org,m_ant_org,"Organico","🌱")
    canal_card(cc3,m_story,m_ant_story,"Story","📖")

    # KPIs CAMPANHA PAGO
    if m_pago:
        st.markdown('<div class="section-title">📣 KPIs Campanha (Pago)</div>',unsafe_allow_html=True)
        lucro_camp=m_pago["comissao"]-invest_pago
        roi_camp=(m_pago["comissao"]-invest_pago)/invest_pago if invest_pago>0 else 0
        cor_roi="green" if roi_camp>1 else ("yellow" if roi_camp>=0 else "red")
        mp=m_ant_pago if m_ant_pago else {}
        k1,k2,k3,k4,k5=st.columns(5)
        with k1: card("Vendas Pago",fmt_num(m_pago["vendas"]),"purple",delta_html(m_pago["vendas"],mp.get("vendas",0)))
        with k2: card("Comissao Pago",fmt_brl(m_pago["comissao"]),"blue",delta_html(m_pago["comissao"],mp.get("comissao",0)))
        with k3: card("Ticket Medio",fmt_brl(m_pago["ticket_medio"]),"orange",delta_html(m_pago["ticket_medio"],mp.get("ticket_medio",0)))
        with k4: card("Investimento",fmt_brl(invest_pago),"red",delta_html(invest_pago,mp.get("invest",0)))
        with k5: card("Lucro Campanha",fmt_brl(lucro_camp),cor_roi,delta_html(lucro_camp,mp.get("lucro_total",0)))
        k6,k7,k8,k9,k10=st.columns(5)
        with k6:  card("CPM Impressoes",fmt_brl(m_pago.get("cpm_imp",0)),"yellow",delta_html(m_pago.get("cpm_imp",0),mp.get("cpm_imp",0)))
        with k7:  card("CPM Alcance",fmt_brl(m_pago.get("cpm_alc",0)),"yellow",delta_html(m_pago.get("cpm_alc",0),mp.get("cpm_alc",0)))
        with k8:  card("CPC",fmt_brl(m_pago.get("cpc",0)),"blue",delta_html(m_pago.get("cpc",0),mp.get("cpc",0)))
        with k9:  card("CAC",fmt_brl(m_pago.get("cac",0)),"purple",delta_html(m_pago.get("cac",0),mp.get("cac",0)))
        with k10: card("Frequencia","{:.2f}x".format(m_pago.get("freq",0)),"orange",delta_html(m_pago.get("freq",0),mp.get("freq",0)))

    # AWARENESS
    st.markdown('<div id="awareness" class="section-title">📡 Campanha Awareness</div>',unsafe_allow_html=True)
    if not df_aw.empty:
        inv_aw=df_aw["Investimento_aw"].sum(); imp_aw=df_aw["Impressoes_aw"].sum()
        alc_aw=df_aw["Alcance_aw"].sum(); vis_aw=df_aw["Visitas_Perfil"].sum()
        seg_aw=df_aw["Seguidores"].sum()
        cpm_aw=(inv_aw/imp_aw*1000) if imp_aw>0 else 0
        cpa_aw=(inv_aw/vis_aw) if vis_aw>0 else 0
        cps_aw=(inv_aw/seg_aw) if seg_aw>0 else 0
        freq_aw=imp_aw/alc_aw if alc_aw>0 else 0
        com_aw=df_aw["Comentarios"].sum() if "Comentarios" in df_aw.columns else 0
        cpc_aw=(inv_aw/com_aw) if com_aw>0 else 0
        # Periodo anterior awareness
        df_aw_ant=semana_anterior(df_aw_raw,d_ini,d_fim) if not df_aw_raw.empty else pd.DataFrame()
        inv_aw_ant=df_aw_ant["Investimento_aw"].sum() if not df_aw_ant.empty else 0
        vis_aw_ant=df_aw_ant["Visitas_Perfil"].sum() if not df_aw_ant.empty else 0
        seg_aw_ant=df_aw_ant["Seguidores"].sum() if not df_aw_ant.empty else 0
        com_aw_ant=df_aw_ant["Comentarios"].sum() if not df_aw_ant.empty else 0

        aw1,aw2,aw3,aw4=st.columns(4)
        with aw1: card("Invest. Awareness",fmt_brl(inv_aw),"red",delta_html(inv_aw,inv_aw_ant))
        with aw2: card("Impressoes",fmt_num(int(imp_aw)),"yellow")
        with aw3: card("Visitas ao Perfil",fmt_num(int(vis_aw)),"purple",delta_html(vis_aw,vis_aw_ant))
        with aw4: card("Seguidores Ganhos",fmt_num(int(seg_aw)),"green",delta_html(seg_aw,seg_aw_ant))
        aw5,aw6,aw7,aw8=st.columns(4)
        with aw5: card("Comentarios",fmt_num(int(com_aw)),"blue",delta_html(com_aw,com_aw_ant))
        with aw6: card("CPM",fmt_brl(cpm_aw),"yellow")
        with aw7: card("Custo/Visita",fmt_brl(cpa_aw),"orange")
        with aw8: card("Custo/Seguidor",fmt_brl(cps_aw),"purple")
        df_aw_d=df_aw.groupby("Data").agg(
            Invest=("Investimento_aw","sum"),Impressoes=("Impressoes_aw","sum"),
            Visitas=("Visitas_Perfil","sum"),Seguidores=("Seguidores","sum"),
            Comentarios=("Comentarios","sum")).reset_index()
        df_aw_d["CPM"]=(df_aw_d["Invest"]/df_aw_d["Impressoes"]*1000).replace([np.inf,np.nan],0)
        df_aw_d["CPA"]=(df_aw_d["Invest"]/df_aw_d["Visitas"]).replace([np.inf,np.nan],0)
        df_aw_d["CPS"]=(df_aw_d["Invest"]/df_aw_d["Seguidores"]).replace([np.inf,np.nan],0)
        df_aw_d["CPC_aw"]=(df_aw_d["Invest"]/df_aw_d["Comentarios"]).replace([np.inf,np.nan],0)

        metricas_aw = {
            "Visitas ao Perfil": ("Invest","Visitas","CPA","Investimento (R$)","Visitas","Custo/Visita (R$)","#bd6d34"),
            "Impressoes": ("Invest","Impressoes","CPM","Investimento (R$)","Impressoes","CPM (R$)","#c5936d"),
            "Seguidores": ("Invest","Seguidores","CPS","Investimento (R$)","Seguidores","Custo/Seguidor (R$)","#9c5834"),
            "Comentarios": ("Invest","Comentarios","CPC_aw","Investimento (R$)","Comentarios","Custo/Comentario (R$)","#d2b095"),
        }
        met_aw=st.selectbox("Metrica Awareness",list(metricas_aw.keys()),key="sel_aw")
        col_bar,col_vol,col_custo,y1_title,y2_vol,y2_custo,cor=metricas_aw[met_aw]
        aw_theme=dict(plot_bgcolor="#0f0d0b",paper_bgcolor="#0f0d0b",font_color="#f6e8d8",
            legend=dict(font=dict(color="#f6e8d8",size=12),bgcolor="rgba(30,18,16,0.8)"))
        caw1,caw2=st.columns(2)
        with caw1:
            fig=go.Figure()
            fig.add_trace(go.Bar(x=df_aw_d["Data"],y=df_aw_d[col_bar],name="Investimento",marker_color="#c0392b",opacity=0.7))
            fig.add_trace(go.Scatter(x=df_aw_d["Data"],y=df_aw_d[col_vol],name=met_aw,mode="lines+markers",line=dict(color=cor,width=2),yaxis="y2"))
            fig.update_layout(title="Investimento vs {}".format(met_aw),
                yaxis=dict(title=y1_title,color="#c5936d",gridcolor="#2a1f1a"),
                yaxis2=dict(title=y2_vol,overlaying="y",side="right",color=cor),**aw_theme)
            st.plotly_chart(fig,use_container_width=True)
        with caw2:
            fig2=go.Figure()
            fig2.add_trace(go.Scatter(x=df_aw_d["Data"],y=df_aw_d[col_custo],name=y2_custo,mode="lines+markers",line=dict(color=cor,width=2),fill="tozeroy",fillcolor="rgba(189,109,52,0.15)"))
            fig2.update_layout(title="{} ao longo do tempo".format(y2_custo),
                yaxis=dict(title=y2_custo,color="#c5936d",gridcolor="#2a1f1a"),**aw_theme)
            st.plotly_chart(fig2,use_container_width=True)
        df_os=df[df["Sub_id2"].str.lower().isin(["organico","story"])].groupby("Data").agg(Vendas=("Vendas","sum")).reset_index()
        df_aw_s=df_aw_d[["Data","Invest"]].copy()
        df_aw_s["Data"]=df_aw_s["Data"]+pd.Timedelta(days=3)
        df_imp=df_os.merge(df_aw_s.rename(columns={"Invest":"Invest_lag"}),on="Data",how="left").fillna(0)
        if len(df_imp)>3 and df_imp["Invest_lag"].sum()>0:
            corr=df_imp["Invest_lag"].corr(df_imp["Vendas"])
            cor_txt="#7a9e4e" if corr>0.3 else ("#c0392b" if corr<-0.1 else "#c5936d")
            interp="correlacao positiva" if corr>0.3 else ("sem correlacao clara" if corr>=-0.1 else "correlacao negativa")
            st.markdown('<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:8px;padding:10px 14px;"><span style="color:#c5936d;font-size:11px;">Correlacao Awareness -> Vendas Org/Story (lag 3d): </span><span style="color:{};font-size:14px;font-weight:700;">{:.2f}</span> <span style="color:#c5936d;font-size:11px;">— {}</span></div>'.format(cor_txt,corr,interp),unsafe_allow_html=True)
    else:
        n_raw=len(df_aw_raw) if not df_aw_raw.empty else 0
        msg="Sem dados na aba Resultado Awareness." if n_raw==0 else "Sem dados de Awareness para este periodo ({} linhas totais).".format(n_raw)
        st.markdown('<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:8px;padding:16px;text-align:center;color:#c5936d;">{}</div>'.format(msg),unsafe_allow_html=True)


    st.markdown("---")

    # EVOLUCAO
    st.markdown('<div id="evolucao" class="section-title">📈 Evolucao Temporal</div>',unsafe_allow_html=True)
    metricas_disp={"Comissao":"Comissao","Vendas":"Vendas","Cliques":"Cliques","Investimento":"Investimento","Ticket Medio":"Ticket_Medio"}
    col_sel=st.multiselect("Metricas",list(metricas_disp.keys()),default=["Comissao","Vendas"])
    if col_sel:
        fig=go.Figure(); cores=["#bd6d34","#c5936d","#d2b095","#9c5834","#562d1d"]
        for i,nome in enumerate(col_sel):
            cr=metricas_disp[nome]; cor=cores[i%len(cores)]
            if cr in df_daily.columns:
                fig.add_trace(go.Scatter(x=df_daily["Data"],y=df_daily[cr],name=nome,mode="lines+markers",line=dict(color=cor,width=2),marker=dict(size=4)))
                mm7=df_daily[cr].rolling(7,min_periods=1).mean()
                fig.add_trace(go.Scatter(x=df_daily["Data"],y=mm7,name=nome+" MM7",mode="lines",line=dict(color=cor,width=1,dash="dash"),opacity=0.6))
        fig.update_layout(title="Evolucao + Media Movel 7 dias",hovermode="x unified",**PLOTLY_THEME)
        st.plotly_chart(fig,use_container_width=True)

    # CANAIS COMPARACAO
    st.markdown('<div id="canais" class="section-title">📊 Comparacao por Canal</div>',unsafe_allow_html=True)
    df_viz=df[df["Sub_id2"].str.strip()!=""].copy()
    df_canal=df_viz.groupby("Sub_id2").agg(Vendas=("Vendas","sum"),Comissao=("Comissao","sum"),Cliques=("Cliques","sum")).reset_index()
    col1,col2=st.columns(2)
    with col1:
        fig=px.bar(df_canal,x="Sub_id2",y="Comissao",title="Comissao por Canal",color="Sub_id2",text="Comissao",color_discrete_sequence=["#bd6d34","#9c5834","#c5936d"])
        fig.update_traces(texttemplate="R$ %{text:,.2f}",textposition="outside"); fig.update_layout(**PLOTLY_THEME); st.plotly_chart(fig,use_container_width=True)
    with col2:
        fig=px.pie(df_canal,names="Sub_id2",values="Vendas",title="Distribuicao Vendas",color_discrete_sequence=["#bd6d34","#9c5834","#c5936d"])
        fig.update_traces(textinfo="percent+label"); fig.update_layout(**PLOTLY_THEME); st.plotly_chart(fig,use_container_width=True)

    # CAMPEOES
    st.markdown('<div id="campeoes" class="section-title">🏆 Itens Campeoes</div>',unsafe_allow_html=True)
    df_s3=df[df["Sub_id3"]!=""].groupby("Sub_id3").agg(Comissao=("Comissao","sum"),Vendas=("Vendas","sum"),Cliques=("Cliques","sum")).reset_index()
    df_s3["CTR"]=(df_s3["Vendas"]/df_s3["Cliques"]*100).fillna(0)
    col1,col2=st.columns(2)
    with col1:
        t5=df_s3.nlargest(5,"Comissao").sort_values("Comissao",ascending=True)
        t5["lbl"]=t5.apply(lambda r:"R$ {:,.2f} | {:,.0f} vendas | CTR {:.1f}%".format(r["Comissao"],r["Vendas"],r["CTR"]),axis=1)
        fig=px.bar(t5,x="Comissao",y="Sub_id3",orientation="h",title="Top 5 por Comissao",text="lbl",color_discrete_sequence=["#9c5834"])
        fig.update_traces(textposition="outside"); fig.update_layout(**PLOTLY_THEME); st.plotly_chart(fig,use_container_width=True)
    with col2:
        t5v=df_s3.nlargest(5,"Vendas").sort_values("Vendas",ascending=True)
        fig=px.bar(t5v,x="Vendas",y="Sub_id3",orientation="h",title="Top 5 por Vendas",text="Vendas",color_discrete_sequence=["#c5936d"])
        fig.update_traces(texttemplate="%{text:.0f}",textposition="outside"); fig.update_layout(**PLOTLY_THEME); st.plotly_chart(fig,use_container_width=True)
    col3,col4=st.columns(2)
    with col3:
        t5c=df_s3.nlargest(5,"Cliques").sort_values("Cliques",ascending=True)
        fig=px.bar(t5c,x="Cliques",y="Sub_id3",orientation="h",title="Top 5 por Cliques",text="Cliques",color_discrete_sequence=["#d2b095"])
        fig.update_traces(texttemplate="%{text:.0f}",textposition="outside"); fig.update_layout(**PLOTLY_THEME); st.plotly_chart(fig,use_container_width=True)
    with col4:
        t5ctr=df_s3.nlargest(5,"CTR").sort_values("CTR",ascending=True)
        fig=px.bar(t5ctr,x="CTR",y="Sub_id3",orientation="h",title="Top 5 por CTR",text="CTR",color_discrete_sequence=["#bd6d34"])
        fig.update_traces(texttemplate="%{text:.2f}%",textposition="outside"); fig.update_layout(**PLOTLY_THEME); st.plotly_chart(fig,use_container_width=True)

    # SCATTER
    st.markdown('<div class="section-title">🔍 Analise Micro</div>',unsafe_allow_html=True)
    df_s1=df.groupby(["Sub_id1","Sub_id2"]).agg(Cliques=("Cliques","sum"),Vendas=("Vendas","sum"),Comissao=("Comissao","sum")).reset_index()
    df_s1["CTR_pct"]=(df_s1["Vendas"]/df_s1["Cliques"]*100).fillna(0).round(2)
    fig=px.scatter(df_s1,x="Cliques",y="Vendas",color="Sub_id2",size="Comissao",hover_name="Sub_id1",
        title="Cliques vs Vendas",color_discrete_sequence=["#bd6d34","#9c5834","#c5936d"],size_max=50)
    fig.update_layout(**PLOTLY_THEME); st.plotly_chart(fig,use_container_width=True)

    # GRAFICO CRUZAMENTO LIVRE
    st.markdown('<div class="section-title">🔀 Cruzamento de Metricas</div>',unsafe_allow_html=True)
    # Preparar dados diarios completos para cruzamento
    df_cross=df_daily.copy()
    if not df_aw.empty:
        df_aw_cross=df_aw.groupby("Data").agg(Invest_aw=("Investimento_aw","sum"),Visitas=("Visitas_Perfil","sum"),Seguidores=("Seguidores","sum"),Comentarios=("Comentarios","sum")).reset_index()
        df_cross=df_cross.merge(df_aw_cross,on="Data",how="left").fillna(0)
    else:
        for c in ["Invest_aw","Visitas","Seguidores","Comentarios"]: df_cross[c]=0.0

    opcoes_cross = {
        "Invest. Awareness vs Vendas Org/Story": ("Invest_aw","Vendas","#bd6d34"),
        "Invest. Total vs Vendas": ("Investimento","Vendas","#c5936d"),
        "Invest. Total vs Comissao": ("Investimento","Comissao","#9c5834"),
        "Invest. Pago vs Comissao": ("Invest_pago","Comissao","#bd6d34"),
        "Invest. Pago vs Vendas": ("Invest_pago","Vendas","#d2b095"),
        "Invest. Awareness vs Visitas Perfil": ("Invest_aw","Visitas","#c5936d"),
        "Invest. Awareness vs Seguidores": ("Invest_aw","Seguidores","#9c5834"),
        "Invest. Awareness vs Comentarios": ("Invest_aw","Comentarios","#bd6d34"),
        "Cliques Shopee vs Vendas": ("Cliques","Vendas","#c5936d"),
        "Cliques Shopee vs Comissao": ("Cliques","Comissao","#d2b095"),
        "Ticket Medio vs Vendas": ("Ticket_Medio","Vendas","#bd6d34"),
    }
    cross_sel=st.selectbox("Seleccionar cruzamento",list(opcoes_cross.keys()),key="sel_cross")
    col_x,col_y,cor_cross=opcoes_cross[cross_sel]
    if col_x in df_cross.columns and col_y in df_cross.columns:
        df_cross_f=df_cross[(df_cross[col_x]>0)|(df_cross[col_y]>0)]
        fig=go.Figure()
        fig.add_trace(go.Bar(x=df_cross_f["Data"],y=df_cross_f[col_x],name=col_x.replace("_"," "),marker_color="#c0392b",opacity=0.6))
        fig.add_trace(go.Scatter(x=df_cross_f["Data"],y=df_cross_f[col_y],name=col_y.replace("_"," "),mode="lines+markers",line=dict(color=cor_cross,width=2),yaxis="y2"))
        cross_theme=dict(plot_bgcolor="#0f0d0b",paper_bgcolor="#0f0d0b",font_color="#f6e8d8",
            legend=dict(font=dict(color="#f6e8d8",size=12),bgcolor="rgba(30,18,16,0.8)"))
        fig.update_layout(title=cross_sel,hovermode="x unified",
            yaxis=dict(title=col_x.replace("_"," "),color="#c5936d",gridcolor="#2a1f1a"),
            yaxis2=dict(title=col_y.replace("_"," "),overlaying="y",side="right",color=cor_cross),
            **cross_theme)
        st.plotly_chart(fig,use_container_width=True)


    # FUNIL
    if not df_pago_periodo.empty and df_pago_periodo["Impressoes"].sum()>0:
        st.markdown('<div id="funil" class="section-title">🔽 Funil de Conversao (Pago)</div>',unsafe_allow_html=True)
        imp_t=df_pago_periodo["Impressoes"].sum(); alc_t=df_pago_periodo["Alcance"].sum()
        clq_t=df_pago_periodo["Cliques_Meta"].sum(); vnd_t=df_pago_v["Vendas"].sum()
        if "modo_ctr" not in st.session_state: st.session_state.modo_ctr="anterior"
        modo_ctr=st.session_state.modo_ctr
        if modo_ctr=="anterior":
            cards_f=[("Impressoes -> Alcance","Frequencia de alcance. Ideal > 60%",alc_t,imp_t),
                     ("Alcance -> Cliques","CTR criativo. Ideal > 1%",clq_t,alc_t),
                     ("Cliques -> Vendas","Taxa de conversao final",vnd_t,clq_t)]
        else:
            cards_f=[("Impressoes -> Alcance","Alcance vs total impressoes",alc_t,imp_t),
                     ("Impressoes -> Cliques","Eficiencia global criativo",clq_t,imp_t),
                     ("Impressoes -> Vendas","O mais importante do funil",vnd_t,imp_t)]
        col_funil,col_steps=st.columns([1.2,1])
        with col_funil:
            fl=["Vendas","Cliques Meta","Alcance","Impressoes"]
            fv=[vnd_t,clq_t,alc_t,imp_t]
            fp=[vnd_t/imp_t*100 if imp_t>0 else 0, clq_t/imp_t*100 if imp_t>0 else 0,
                alc_t/imp_t*100 if imp_t>0 else 0, 100]
            cores_b={"Impressoes":"#bd6d34","Alcance":"#9c5834","Cliques Meta":"#c5936d","Vendas":"#d2b095"}
            cores_h={"Impressoes":"#f6a050","Alcance":"#c07840","Cliques Meta":"#e8b090","Vendas":"#f0d8b8"}
            fig_f=go.Figure()
            for l,v,p in zip(fl,fv,fp):
                fig_f.add_trace(go.Bar(x=[p],y=[l],orientation="h",marker_color=cores_h[l],
                    text="{:,.0f}  ({:.2f}%)".format(v,p),textposition="inside",name=l,showlegend=False))
            fig_f.update_layout(title="Funil - % do total de impressoes",barmode="overlay",**PLOTLY_THEME,height=240,margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig_f,use_container_width=True)
            st.markdown('<div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:-8px;">'+"".join(['<span style="font-size:10px;color:#c5936d;"><span style="color:{};font-size:14px;">■</span> {}</span>'.format(cores_b[k],k) for k in cores_b])+'</div>',unsafe_allow_html=True)
        with col_steps:
            st.markdown('<div style="color:#c5936d;font-size:11px;margin-bottom:8px;"><b style="color:#f6e8d8;">{}</b></div>'.format("CTR Anterior: step a step" if modo_ctr=="anterior" else "CTR Inicial: vs Impressoes"),unsafe_allow_html=True)
            for titulo,dica,num,den in cards_f:
                cur=num/den*100 if den>0 else 0
                st.markdown('<div class="metric-card" style="margin-bottom:6px;padding:10px 14px;" title="{}"><div class="metric-label" style="font-size:10px;">{}</div><div class="metric-value" style="font-size:18px;">{:.3f}%</div></div>'.format(dica,titulo,cur),unsafe_allow_html=True)
            if st.button("Ver CTR Inicial" if modo_ctr=="anterior" else "Ver CTR Anterior",key="toggle_ctr"):
                st.session_state.modo_ctr="inicial" if modo_ctr=="anterior" else "anterior"; st.rerun()

    # METRICAS PAGO
    if not df_pago_periodo.empty:
        st.markdown('<div id="metricas-pago" class="section-title">📉 Metricas Pago</div>',unsafe_allow_html=True)
        df_pd=df_pago_periodo.groupby("Data").agg(Investimento=("Investimento","sum"),Impressoes=("Impressoes","sum"),Alcance=("Alcance","sum"),Cliques_Meta=("Cliques_Meta","sum")).reset_index()
        df_pd_v=df_pago_v.groupby("Data").agg(Vendas=("Vendas","sum"),Comissao=("Comissao","sum")).reset_index()
        df_pd=df_pd.merge(df_pd_v,on="Data",how="left").fillna(0)
        df_pd["CPM"]=(df_pd["Investimento"]/df_pd["Impressoes"]*1000).replace([np.inf,np.nan],0)
        df_pd["CPC"]=(df_pd["Investimento"]/df_pd["Cliques_Meta"]).replace([np.inf,np.nan],0)
        df_pd["CAC"]=(df_pd["Investimento"]/df_pd["Vendas"]).replace([np.inf,np.nan],0)
        df_pd["CTR_Meta"]=(df_pd["Cliques_Meta"]/df_pd["Alcance"]*100).replace([np.inf,np.nan],0)

        metricas_pago_sel = {
            "Impressoes vs CPM": ("Investimento","Impressoes","CPM","Investimento (R$)","Impressoes","CPM (R$)","#c5936d"),
            "Cliques vs CPC": ("Investimento","Cliques_Meta","CPC","Investimento (R$)","Cliques","CPC (R$)","#bd6d34"),
            "Vendas vs CAC": ("Investimento","Vendas","CAC","Investimento (R$)","Vendas","CAC (R$)","#9c5834"),
            "Alcance vs CTR Meta": ("Investimento","Alcance","CTR_Meta","Investimento (R$)","Alcance","CTR Meta (%)","#d2b095"),
        }
        met_pago_sel=st.selectbox("Metrica Pago",list(metricas_pago_sel.keys()),key="sel_mp")
        col_bar_p,col_vol_p,col_custo_p,y1p,y2vp,y2cp,cor_p=metricas_pago_sel[met_pago_sel]
        pago_theme=dict(plot_bgcolor="#0f0d0b",paper_bgcolor="#0f0d0b",font_color="#f6e8d8",
            legend=dict(font=dict(color="#f6e8d8",size=12),bgcolor="rgba(30,18,16,0.8)"))
        cp1,cp2=st.columns(2)
        with cp1:
            fig=go.Figure()
            fig.add_trace(go.Bar(x=df_pd["Data"],y=df_pd[col_bar_p],name="Investimento",marker_color="#c0392b",opacity=0.7))
            fig.add_trace(go.Scatter(x=df_pd["Data"],y=df_pd[col_vol_p],name=col_vol_p,mode="lines+markers",line=dict(color=cor_p,width=2),yaxis="y2"))
            fig.update_layout(title="Investimento vs {}".format(col_vol_p),
                yaxis=dict(title=y1p,color="#c5936d",gridcolor="#2a1f1a"),
                yaxis2=dict(title=y2vp,overlaying="y",side="right",color=cor_p),**pago_theme)
            st.plotly_chart(fig,use_container_width=True)
        with cp2:
            fig2=go.Figure()
            fig2.add_trace(go.Scatter(x=df_pd["Data"],y=df_pd[col_custo_p],name=y2cp,mode="lines+markers",line=dict(color=cor_p,width=2),fill="tozeroy",fillcolor="rgba(189,109,52,0.15)"))
            fig2.update_layout(title="{} ao longo do tempo".format(y2cp),
                yaxis=dict(title=y2cp,color="#c5936d",gridcolor="#2a1f1a"),**pago_theme)
            st.plotly_chart(fig2,use_container_width=True)

    # METRICAS AWARENESS

    # IPA
    st.markdown('<div id="ipa" class="section-title">🎯 IPA — Indice de Potencial de Anuncio</div>',unsafe_allow_html=True)
    st.markdown('<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:8px;padding:12px 16px;margin-bottom:12px;color:#c5936d;font-size:12px;">O <b style="color:#f6e8d8;">IPA</b> identifica criativos do organico e story com maior potencial para anuncio directo. Score 0-100. <b style="color:#c0392b;">N/A</b> = menos de 3 vendas.</div>',unsafe_allow_html=True)
    df_ipa=df[df["Sub_id2"].str.lower().isin(["organico","story"])].groupby(["Sub_id3","Sub_id1"]).agg(Comissao=("Comissao","sum"),Vendas=("Vendas","sum"),Cliques=("Cliques","sum")).reset_index()
    df_ipa["CTR"]=(df_ipa["Vendas"]/df_ipa["Cliques"]*100).fillna(0)
    df_ipa["Ticket"]=(df_ipa["Comissao"]/df_ipa["Vendas"]).fillna(0)
    df_v=df_ipa[df_ipa["Vendas"]>=3].copy()
    if not df_v.empty:
        for col in ["Comissao","Vendas","Ticket","CTR"]:
            mn,mx=df_v[col].min(),df_v[col].max()
            df_v[col+"_n"]=((df_v[col]-mn)/(mx-mn)*100) if mx>mn else 50.0
        df_v["IPA"]=(df_v["Comissao_n"]*0.40+df_v["Vendas_n"]*0.25+df_v["Ticket_n"]*0.25+df_v["CTR_n"]*0.10).round(1)
    ja_pago=set(df[df["Sub_id2"].str.lower()=="pago"]["Sub_id3"].unique())
    df_ipa=df_ipa.merge(df_v[["Sub_id3","Sub_id1","IPA"]] if not df_v.empty else pd.DataFrame(columns=["Sub_id3","Sub_id1","IPA"]),on=["Sub_id3","Sub_id1"],how="left")
    df_ipa=df_ipa[~df_ipa["Sub_id3"].isin(ja_pago)]
    df_ipa["IPA_d"]=df_ipa["IPA"].apply(lambda x:"{:.1f}".format(x) if pd.notna(x) else "N/A")
    df_ipa["IPA_s"]=df_ipa["IPA"].fillna(-1)
    df_ipa=df_ipa.sort_values("IPA_s",ascending=False).reset_index(drop=True)
    df_ic=df_ipa[df_ipa["IPA_s"]>=0].head(15).sort_values("IPA_s",ascending=True)
    if not df_ic.empty:
        fig=px.bar(df_ic,x="IPA_s",y="Sub_id3",orientation="h",title="Top Criativos por IPA",text="IPA_d",color="IPA_s",color_continuous_scale=["#562d1d","#9c5834","#bd6d34","#f6e8d8"],hover_data={"Sub_id1":True,"Vendas":True,"Comissao":":.2f","CTR":":.2f","Ticket":":.2f","IPA_s":False},labels={"IPA_s":"IPA","Sub_id3":"Criativo"})
        fig.update_traces(textposition="outside"); fig.update_layout(**PLOTLY_THEME,height=max(300,len(df_ic)*40),coloraxis_showscale=False); st.plotly_chart(fig,use_container_width=True)
    df_it=df_ipa[["Sub_id3","Sub_id1","IPA_d","Vendas","Comissao","CTR","Ticket"]].copy()
    df_it.columns=["Sub_id3","Sub_id1","IPA","Vendas","Comissao (R$)","CTR (%)","Ticket (R$)"]
    df_it["Comissao (R$)"]=df_it["Comissao (R$)"].apply(lambda x:"{:.2f}".format(x))
    df_it["CTR (%)"]=df_it["CTR (%)"].apply(lambda x:"{:.2f}%".format(x))
    df_it["Ticket (R$)"]=df_it["Ticket (R$)"].apply(lambda x:"{:.2f}".format(x))
    st.dataframe(df_it,use_container_width=True,height=300)

    # TABELA
    st.markdown('<div class="section-title">📋 Dados Detalhados</div>',unsafe_allow_html=True)
    df_t=df[["Data","Sub_id2","Sub_id1","Sub_id3","Cliques","Vendas","Comissao"]].copy()
    df_t["Data"]=df_t["Data"].dt.strftime("%Y-%m-%d")
    df_t=df_t.sort_values("Comissao",ascending=False).reset_index(drop=True)
    busca=st.text_input("🔍 Pesquisar",placeholder="Ex: pago, 260302fronha...")
    if busca: df_t=df_t[df_t.apply(lambda r:busca.lower() in str(r).lower(),axis=1)]
    st.dataframe(df_t.style.format({"Comissao":"R$ {:.2f}"}),use_container_width=True,height=400)
    st.caption("{} linhas".format(len(df_t)))
    html_r="<html><body><h1>Relatorio Destrava</h1><p>Periodo: {} a {}</p><p>Comissao: {} | Lucro: {} | ROI: {:.2f} | Invest: {}</p>{}</body></html>".format(d_ini,d_fim,fmt_brl(m["comissao"]),fmt_brl(m["lucro_total"]),m["roi"],fmt_brl(invest_total),df_t.to_html(index=False))
    st.download_button("📥 Download HTML",data=html_r.encode("utf-8"),file_name="relatorio_{}_{}.html".format(d_ini,d_fim),mime="text/html")

    # INSIGHTS IA
    st.markdown('<div id="insights-ia" class="section-title">🤖 DESTRAVA AI</div>',unsafe_allow_html=True)
    st.markdown("""<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">
    <div style="background:#1a1210;border:1px solid #bd6d34;border-radius:10px;padding:16px;"><div style="color:#bd6d34;font-size:13px;font-weight:700;margin-bottom:6px;">Campanha Paga</div><div style="color:#c5936d;font-size:12px;">Analise tecnica de CPM, CPC, CAC, frequencia e funil.</div></div>
    <div style="background:#1a1210;border:1px solid #9c5834;border-radius:10px;padding:16px;"><div style="color:#9c5834;font-size:13px;font-weight:700;margin-bottom:6px;">Todos os Canais + Criativos</div><div style="color:#c5936d;font-size:12px;">Comparacao tecnica entre canais + sugestao de criativos baseada no IPA.</div></div>
    </div><div style="color:#c5936d;font-size:11px;margin-bottom:12px;">(*) Cada analise ~$0.01 de creditos Anthropic.</div>""",unsafe_allow_html=True)

    if "analise_camp" not in st.session_state: st.session_state.analise_camp=None
    if "analise_geral" not in st.session_state: st.session_state.analise_geral=None
    btn1,btn2,_=st.columns([1,1,2])
    with btn1: gerar_camp=st.button("Analisar Campanha Paga",use_container_width=True)
    with btn2: gerar_geral=st.button("Analisar Todos os Canais + Criativos",use_container_width=True)

    if gerar_camp and not df_pago_periodo.empty:
        with st.spinner("A analisar..."):
            try:
                api_key=st.secrets.get("anthropic",{}).get("api_key","")
                dados="Periodo:{} a {}\nInvest:{:.2f}|Vendas:{:.0f}|Comissao:{:.2f}|Lucro:{:.2f}|ROI:{:.2f}\nCPM_imp:{:.2f}|CPC:{:.2f}|CAC:{:.2f}|Freq:{:.2f}x\nCTR_Meta:{:.2f}%|CTR_Conv:{:.2f}%\nFunil:{:.0f}imp->{:.0f}alc->{:.0f}clq->{:.0f}vnd".format(
                    d_ini,d_fim,invest_pago,m_pago["vendas"] if m_pago else 0,m_pago["comissao"] if m_pago else 0,
                    (m_pago["comissao"] if m_pago else 0)-invest_pago,m_pago["roi"] if m_pago else 0,
                    m_pago.get("cpm_imp",0) if m_pago else 0,m_pago.get("cpc",0) if m_pago else 0,
                    m_pago.get("cac",0) if m_pago else 0,m_pago.get("freq",0) if m_pago else 0,
                    m_pago.get("ctr_meta",0) if m_pago else 0,m_pago.get("ctr_cv",0) if m_pago else 0,
                    m_pago.get("impressoes",0) if m_pago else 0,m_pago.get("alcance",0) if m_pago else 0,
                    m_pago.get("cliques_meta",0) if m_pago else 0,m_pago["vendas"] if m_pago else 0)
                prompt="Es especialista senior em Meta Ads e afiliados Shopee. Linguagem tecnica.\nFornece: 1.Diagnostico tecnico. 2.2-3 alertas criticos. 3.2-3 acoes concretas.\nDados:"+dados
                resp=requests.post("https://api.anthropic.com/v1/messages",headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},json={"model":"claude-sonnet-4-20250514","max_tokens":1000,"messages":[{"role":"user","content":prompt}]},timeout=30)
                rj=resp.json()
                if "error" in rj: raise Exception(rj["error"]["message"])
                st.session_state.analise_camp=(rj["content"][0]["text"],str(d_ini),str(d_fim))
            except Exception as e: st.error("Erro: {}".format(str(e)))

    if gerar_geral:
        with st.spinner("A analisar todos os canais..."):
            try:
                api_key=st.secrets.get("anthropic",{}).get("api_key","")
                top_ipa=df_v.nlargest(8,"IPA")[["Sub_id1","Sub_id3","IPA","Comissao","Vendas","CTR","Ticket"]].to_string(index=False) if not df_v.empty else "Sem dados"
                dados_g="Periodo:{} a {}\nComissao:{:.2f}|Lucro:{:.2f}|ROI:{:.2f}|Vendas:{:.0f}\nPago:{:.0f}vnd|R${:.2f}|ROI:{:.2f}|Ticket:{:.2f}\nOrganico:{:.0f}vnd|R${:.2f}|Ticket:{:.2f}\nStory:{:.0f}vnd|R${:.2f}|Ticket:{:.2f}\nInvest.Awareness:R${:.2f}\nTop IPA:\n{}".format(
                    d_ini,d_fim,m["comissao"],m["lucro_total"],m["roi"],m["vendas"],
                    m_pago["vendas"] if m_pago else 0,m_pago["comissao"] if m_pago else 0,m_pago["roi"] if m_pago else 0,m_pago["ticket_medio"] if m_pago else 0,
                    m_org["vendas"] if m_org else 0,m_org["comissao"] if m_org else 0,m_org["ticket_medio"] if m_org else 0,
                    m_story["vendas"] if m_story else 0,m_story["comissao"] if m_story else 0,m_story["ticket_medio"] if m_story else 0,
                    invest_aw,top_ipa)
                prompt_g="Es especialista senior Meta Ads e afiliados Shopee. Linguagem tecnica.\nCONTEXTO: PAGO=unico com investimento (Meta Ads directo Shopee). ORGANICO/STORY=custo zero. NUNCA migrar verba.\nFornece: 1.Diagnostico. 2.Avaliacao cada canal. 3.Acoes concretas. 4.CRIATIVOS PARA ANUNCIO (PECA CHAVE): baseado no IPA, indica candidatos com CAC alvo (ticket*0.3-0.5) e budget teste.\nDados:"+dados_g
                resp2=requests.post("https://api.anthropic.com/v1/messages",headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},json={"model":"claude-sonnet-4-20250514","max_tokens":1200,"messages":[{"role":"user","content":prompt_g}]},timeout=30)
                rj2=resp2.json()
                if "error" in rj2: raise Exception(rj2["error"]["message"])
                st.session_state.analise_geral=(rj2["content"][0]["text"],str(d_ini),str(d_fim))
            except Exception as e: st.error("Erro: {}".format(str(e)))

    if st.session_state.analise_camp:
        a,di,df_=st.session_state.analise_camp
        st.markdown('<div style="background:linear-gradient(135deg,#1a1210,#221a16);border-radius:12px;padding:20px;margin-top:12px;border-left:4px solid #bd6d34;border:1px solid #3a2c28;"><div style="color:#bd6d34;font-size:13px;font-weight:700;margin-bottom:12px;">Campanha Paga — {} a {}</div><div style="color:#f6e8d8;font-size:14px;line-height:1.8;">{}</div></div>'.format(di,df_,a.replace("\n","<br>")),unsafe_allow_html=True)
    if st.session_state.analise_geral:
        a2,di2,df2_=st.session_state.analise_geral
        st.markdown('<div style="background:linear-gradient(135deg,#1a1210,#221a16);border-radius:12px;padding:20px;margin-top:12px;border-left:4px solid #9c5834;border:1px solid #3a2c28;"><div style="color:#9c5834;font-size:13px;font-weight:700;margin-bottom:12px;">Todos os Canais + Criativos — {} a {}</div><div style="color:#f6e8d8;font-size:14px;line-height:1.8;">{}</div></div>'.format(di2,df2_,a2.replace("\n","<br>")),unsafe_allow_html=True)
    if st.session_state.analise_camp or st.session_state.analise_geral:
        if st.button("🗑️ Limpar analises",key="clear_ai"):
            st.session_state.analise_camp=None; st.session_state.analise_geral=None; st.rerun()

    st.markdown('<div class="footer">🔓 <strong style="color:#bd6d34;">DESTRAVA</strong> <span style="color:#c5936d;">por Carol Matos</span></div>',unsafe_allow_html=True)

if __name__=="__main__":
    main()
