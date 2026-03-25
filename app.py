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

st.set_page_config(page_title="Dashboard de Performance", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
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
.metric-card.orange{border-left-color:#bd6d34;}.metric-card.blue{border-left-color:#2980b9;}
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

PLOTLY_THEME = dict(plot_bgcolor="#0f0d0b",paper_bgcolor="#0f0d0b",font_color="#f6e8d8",
    legend=dict(font=dict(color="#f6e8d8",size=12),bgcolor="rgba(30,18,16,0.8)",bordercolor="#3a2c28",borderwidth=1),
    xaxis=dict(color="#c5936d",gridcolor="#2a1f1a"),yaxis=dict(color="#c5936d",gridcolor="#2a1f1a"))

def parse_num(s):
    s=str(s).strip().replace("R$","").replace("%","").strip()
    if not s or s in ["-","nan","None",""]: return 0.0
    if "," in s: s=s.replace(".","").replace(",",".")
    else: s=s.replace(",",".")
    try: return float(s)
    except: return 0.0

def fmt_brl(v): return "R$ {:,.2f}".format(v).replace(",","X").replace(".",",").replace("X",".")
def fmt_pct(v): return "{:.2f}%".format(v).replace(".",",")
def fmt_num(v): return "{:,}".format(int(v)).replace(",",".")

def card(label,value,color="blue",delta_html_str="",sparkline_fig=None):
    html='<div class="metric-card {}"><div class="metric-label">{}</div><div class="metric-value">{}</div>{}</div>'.format(color,label,str(value),delta_html_str or "")
    st.markdown(html,unsafe_allow_html=True)
    if sparkline_fig: st.plotly_chart(sparkline_fig,use_container_width=True,config={"displayModeBar":False})

def delta_html(val,ref):
    if not ref or ref==0: return '<span class="metric-delta-neu">sem ref. anterior</span>'
    pct=(val-ref)/abs(ref)*100
    if pct>0: return '<span class="metric-delta-pos">▲ {:.1f}% vs semana ant.</span>'.format(pct)
    elif pct<0: return '<span class="metric-delta-neg">▼ {:.1f}% vs semana ant.</span>'.format(abs(pct))
    return '<span class="metric-delta-neu">= igual semana ant.</span>'

def sparkline(df_d,col,color="#bd6d34"):
    if col not in df_d.columns or df_d[col].sum()==0: return None
    df14=df_d.tail(14)
    fig=go.Figure(go.Scatter(x=df14["Data"],y=df14[col],mode="lines",line=dict(color=color,width=1.5),fill="tozeroy",fillcolor="rgba(189,109,52,0.15)"))
    fig.update_layout(height=50,margin=dict(l=0,r=0,t=0,b=0),xaxis=dict(visible=False),yaxis=dict(visible=False),plot_bgcolor="#0f0d0b",paper_bgcolor="rgba(0,0,0,0)",showlegend=False)
    return fig

def dual_chart(df,x_col,bar_col,line_col,title,y1_label,y2_label,bar_color="#c0392b",line_color="#bd6d34"):
    theme=dict(plot_bgcolor="#0f0d0b",paper_bgcolor="#0f0d0b",font_color="#f6e8d8",legend=dict(font=dict(color="#f6e8d8",size=11),bgcolor="rgba(30,18,16,0.8)"))
    fig=go.Figure()
    fig.add_trace(go.Bar(x=df[x_col],y=df[bar_col],name=y1_label,marker_color=bar_color,opacity=0.7))
    fig.add_trace(go.Scatter(x=df[x_col],y=df[line_col],name=y2_label,mode="lines+markers",line=dict(color=line_color,width=2),yaxis="y2"))
    fig.update_layout(title=title,hovermode="x unified",
        yaxis=dict(title=y1_label,color="#c5936d",gridcolor="#2a1f1a"),
        yaxis2=dict(title=y2_label,overlaying="y",side="right",color=line_color),**theme)
    return fig

def calcular(df):
    cliques=df["Cliques"].sum() if "Cliques" in df.columns else 0
    vendas=df["Vendas"].sum(); comissao=df["Comissao"].sum()
    invest=df["Investimento"].sum() if "Investimento" in df.columns else 0
    impressoes=df["Impressoes"].sum() if "Impressoes" in df.columns else 0
    alcance=df["Alcance"].sum() if "Alcance" in df.columns else 0
    cliques_meta=df["Cliques_Meta"].sum() if "Cliques_Meta" in df.columns else 0
    lucro=comissao-invest; roi=(comissao-invest)/invest if invest>0 else 0
    ctr_shopee=(vendas/cliques*100) if cliques>0 else 0
    ctr_meta=(cliques_meta/alcance*100) if alcance>0 else 0
    ctr_cv=(vendas/cliques_meta*100) if cliques_meta>0 else 0
    freq=impressoes/alcance if alcance>0 else 0
    cpm_imp=(invest/impressoes*1000) if impressoes>0 else 0
    cpm_alc=(invest/alcance*1000) if alcance>0 else 0
    cpc=invest/cliques_meta if cliques_meta>0 else 0
    cac=invest/vendas if vendas>0 else 0
    ticket=comissao/vendas if vendas>0 else 0
    return dict(cliques=cliques,vendas=vendas,comissao=comissao,invest=invest,impressoes=impressoes,
                alcance=alcance,cliques_meta=cliques_meta,lucro=lucro,roi=roi,ctr_shopee=ctr_shopee,
                ctr_meta=ctr_meta,ctr_cv=ctr_cv,freq=freq,cpm_imp=cpm_imp,cpm_alc=cpm_alc,
                cpc=cpc,cac=cac,ticket=ticket)

def semana_anterior(df,d_ini,d_fim):
    delta=d_fim-d_ini; ant_fim=d_ini-timedelta(days=1); ant_ini=ant_fim-delta
    return df[(df["Data"].dt.date>=ant_ini)&(df["Data"].dt.date<=ant_fim)]

@st.cache_resource
def autenticar():
    try: creds=Credentials.from_service_account_info(st.secrets["gcp_service_account"],scopes=SCOPES)
    except: creds=Credentials.from_service_account_file("/Users/anacarol/automacao/automacao-planilhas-490816-ee73c7ff4bf2.json",scopes=SCOPES)
    return build("sheets","v4",credentials=creds)

@st.cache_data(ttl=300)
def ler_dados():
    svc=autenticar()
    res=svc.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID,range=f"{SHEET_NAME}!A1:H").execute()
    vals=res.get("values",[])
    if len(vals)<2: return pd.DataFrame()
    cab=vals[0]; linhas=vals[1:]; mc=len(cab)
    ln=[l+[""]*(mc-len(l)) for l in linhas]
    df=pd.DataFrame(ln,columns=cab)
    # Rename por posicao (cabecalho pode variar, ex: "Clique" vs "Cliques")
    nomes=["Data","Sub_id2","Sub_id1","Sub_id3","Cliques","Vendas","CTR","Comissao"]
    df=df.rename(columns={df.columns[i]:nomes[i] for i in range(min(len(df.columns),len(nomes)))})
    for col in ["Cliques","Vendas","Comissao"]: df[col]=df[col].apply(parse_num)
    df["Data"]=pd.to_datetime(df["Data"],errors="coerce")
    df=df.dropna(subset=["Data"])
    df["Sub_id2"]=df["Sub_id2"].fillna("").str.strip().str.lower()
    df["Sub_id1"]=df["Sub_id1"].fillna("").str.strip()
    df["Sub_id3"]=df["Sub_id3"].fillna("").str.strip()
    return df

@st.cache_data(ttl=300)
def ler_pago():
    # Resultados Pago: Data|Sub_id2|Sub_id1|Sub_id3|Investimento|Impressoes|Alcance|Cliques_Meta
    svc=autenticar()
    res=svc.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID,range=f"{SHEET_PAGO}!A1:L").execute()
    vals=res.get("values",[])
    if len(vals)<2: return pd.DataFrame()
    cab=vals[0]; linhas=vals[1:]
    mc=max(len(l) for l in [cab]+linhas)
    ln=[l+[""]*(mc-len(l)) for l in linhas]
    df=pd.DataFrame(ln,columns=(cab+["_"]*mc)[:mc])
    r=pd.DataFrame()
    r["Data"]=pd.to_datetime(df.iloc[:,0],errors="coerce")
    r["Sub_id2"]=df.iloc[:,1].astype(str).str.strip().str.lower()
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
    # Resultado Awareness: Data|Sub_id2|Investimento|Impressoes|Alcance|Visitas|Seguidores|Comentarios
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
        <a href="#kpis" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">💰 KPIs Gerais</a>
        <a href="#pago" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">📣 Campanha Pago</a>
        <a href="#awareness" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">📡 Awareness</a>
        <a href="#evolucao" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">📈 Evolucao</a>
        <a href="#campeoes" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">🏆 Campeoes</a>
        <a href="#ipa" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">🎯 IPA</a>
        <a href="#cruzamento" style="display:block;color:#c5936d;font-size:12px;text-decoration:none;background:#1a1210;padding:6px 12px;border-radius:8px;border:1px solid #3a2c28;margin-bottom:4px;text-align:center;">🔀 Cruzamento</a>
        <a href="#insights-ia" style="display:block;color:#bd6d34;font-size:12px;text-decoration:none;background:#2a1f1a;padding:6px 12px;border-radius:8px;border:1px solid #bd6d34;text-align:center;">🤖 Insights IA</a>
        """,unsafe_allow_html=True)
        st.markdown("---")
        st.markdown('<div style="color:#c5936d;font-size:11px;">👤 {}</div>'.format(st.session_state.get("usuario","")),unsafe_allow_html=True)
        if st.button("🔄 Actualizar dados",use_container_width=True): st.cache_data.clear(); st.rerun()
        if st.button("🚪 Sair",use_container_width=True): st.session_state.logged_in=False; st.rerun()

    st.markdown('<h1 style="color:#f6e8d8;margin:0;font-size:28px;">📊 Dashboard de Performance</h1><p style="color:#c5936d;margin:0 0 16px 0;font-size:13px;">Destrava · por Carol Matos</p>',unsafe_allow_html=True)

    with st.spinner("A carregar dados..."):
        df_raw=ler_dados(); df_pago_raw=ler_pago(); df_aw_raw=ler_awareness()

    if df_raw.empty:
        st.error("Sem dados na planilha Resultados Shopee."); return

    # ── FILTROS ──
    data_min=df_raw["Data"].min().date(); data_max=df_raw["Data"].max().date()
    if "preset" not in st.session_state: st.session_state.preset="all"
    p=st.session_state.get("preset","all")
    if   p=="7d":  d_ini_def=max(data_max-timedelta(days=6),data_min)
    elif p=="14d": d_ini_def=max(data_max-timedelta(days=13),data_min)
    elif p=="28d": d_ini_def=max(data_max-timedelta(days=27),data_min)
    elif p=="30d": d_ini_def=max(data_max-timedelta(days=29),data_min)
    else:          d_ini_def=data_min
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

    mask=((df_raw["Data"].dt.date>=d_ini)&(df_raw["Data"].dt.date<=d_fim))
    if sid2_sel!=sid2_opts: mask=mask&df_raw["Sub_id2"].isin(sid2_sel)
    if sid1_sel!=sid1_opts: mask=mask&df_raw["Sub_id1"].isin(sid1_sel)
    if sid3_sel!=sid3_opts: mask=mask&df_raw["Sub_id3"].isin(sid3_sel)
    df=df_raw[mask].copy()

    # Filtrar pago_raw por periodo
    if not df_pago_raw.empty:
        _di=pd.Timestamp(d_ini).date(); _df=pd.Timestamp(d_fim).date()
        mp=(df_pago_raw["Data"].dt.date>=_di)&(df_pago_raw["Data"].dt.date<=_df)
        if sid1_sel!=sid1_opts: mp=mp&df_pago_raw["Sub_id1"].isin(sid1_sel)
        df_pago_periodo=df_pago_raw[mp].copy()
    else:
        df_pago_periodo=pd.DataFrame()

    # Filtrar awareness por periodo
    if not df_aw_raw.empty:
        _di=pd.Timestamp(d_ini).date(); _df=pd.Timestamp(d_fim).date()
        ma=(df_aw_raw["Data"].dt.date>=_di)&(df_aw_raw["Data"].dt.date<=_df)
        df_aw=df_aw_raw[ma].copy()
    else:
        df_aw=pd.DataFrame()

    if df.empty:
        st.markdown('<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:10px;padding:24px;text-align:center;"><div style="font-size:32px;">📭</div><div style="color:#f6e8d8;font-size:16px;">Sem dados para o periodo seleccionado</div><div style="color:#c5936d;font-size:13px;">Dados disponiveis ate {}.</div></div>'.format(data_max),unsafe_allow_html=True)
        st.stop()

    # ── CALCULAR METRICAS ──
    # Investimento: sempre do df_pago_raw (nunca do df merged)
    invest_pago=df_pago_periodo["Investimento"].sum() if not df_pago_periodo.empty else 0.0
    invest_aw=df_aw["Investimento_aw"].sum() if not df_aw.empty else 0.0
    invest_total=invest_pago+invest_aw

    m=calcular(df)
    m["invest"]=invest_pago
    m["invest_total"]=invest_total
    m["lucro"]=m["comissao"]-invest_total
    m["roi"]=(m["comissao"]-invest_total)/invest_total if invest_total>0 else 0
    if not df_pago_periodo.empty:
        m["impressoes"]=df_pago_periodo["Impressoes"].sum()
        m["alcance"]=df_pago_periodo["Alcance"].sum()
        m["cliques_meta"]=df_pago_periodo["Cliques_Meta"].sum()

    df_ant=semana_anterior(df_raw,d_ini,d_fim)
    m_ant=calcular(df_ant) if not df_ant.empty else None
    mv=m_ant if m_ant else {}

    df_pago_v =df[df["Sub_id2"]=="pago"]
    df_org    =df[df["Sub_id2"]=="organico"]
    df_story  =df[df["Sub_id2"]=="story"]
    m_pago =calcular(df_pago_v)  if len(df_pago_v)>0  else None
    m_org  =calcular(df_org)     if len(df_org)>0     else None
    m_story=calcular(df_story)   if len(df_story)>0   else None

    if m_pago and not df_pago_periodo.empty:
        m_pago["invest"]=invest_pago
        m_pago["lucro"]=m_pago["comissao"]-invest_pago
        m_pago["roi"]=(m_pago["comissao"]-invest_pago)/invest_pago if invest_pago>0 else 0
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

    df_ant_pago =df_ant[df_ant["Sub_id2"]=="pago"]     if not df_ant.empty else pd.DataFrame()
    df_ant_org  =df_ant[df_ant["Sub_id2"]=="organico"] if not df_ant.empty else pd.DataFrame()
    df_ant_story=df_ant[df_ant["Sub_id2"]=="story"]    if not df_ant.empty else pd.DataFrame()
    m_ant_pago  =calcular(df_ant_pago)  if not df_ant_pago.empty  else None
    m_ant_org   =calcular(df_ant_org)   if not df_ant_org.empty   else None
    m_ant_story =calcular(df_ant_story) if not df_ant_story.empty else None

    # df_daily para sparklines
    df_daily=df.groupby("Data").agg(Vendas=("Vendas","sum"),Comissao=("Comissao","sum"),Cliques=("Cliques","sum")).reset_index().sort_values("Data")
    df_daily["Ticket_Medio"]=df_daily.apply(lambda r:r["Comissao"]/r["Vendas"] if r["Vendas"]>0 else 0,axis=1)
    df_daily["CTR_calc"]=df_daily.apply(lambda r:r["Vendas"]/r["Cliques"]*100 if r["Cliques"]>0 else 0,axis=1)
    if not df_pago_periodo.empty:
        inv_d=df_pago_periodo.groupby("Data").agg(Invest_pago=("Investimento","sum")).reset_index()
        df_daily=df_daily.merge(inv_d,on="Data",how="left")
        df_daily["Invest_pago"]=df_daily["Invest_pago"].fillna(0)
    else:
        df_daily["Invest_pago"]=0.0
    if not df_aw.empty:
        inv_aw_d=df_aw.groupby("Data").agg(Invest_aw=("Investimento_aw","sum")).reset_index()
        df_daily=df_daily.merge(inv_aw_d,on="Data",how="left")
        df_daily["Invest_aw"]=df_daily["Invest_aw"].fillna(0)
    else:
        df_daily["Invest_aw"]=0.0
    df_daily["Investimento"]=df_daily["Invest_pago"]+df_daily["Invest_aw"]
    df_daily["ROI_calc"]=df_daily.apply(lambda r:(r["Comissao"]-r["Investimento"])/r["Investimento"] if r["Investimento"]>0 else 0,axis=1)

    # ── KPIs GERAIS ──
    st.markdown('<div id="kpis" class="section-title">💰 KPIs Gerais</div>',unsafe_allow_html=True)
    r1,r2,r3,r4=st.columns(4)
    with r1: card("Comissao Total",fmt_brl(m["comissao"]),"blue",delta_html(m["comissao"],mv.get("comissao",0)),sparkline(df_daily,"Comissao","#bd6d34"))
    with r2: card("Lucro Total",fmt_brl(m["lucro"]),"green" if m["lucro"]>=0 else "red",delta_html(m["lucro"],mv.get("lucro",0)),sparkline(df_daily,"Comissao","#9c5834"))
    with r3: card("Investimento Total",fmt_brl(invest_total),"red",delta_html(invest_total,mv.get("invest",0)),sparkline(df_daily,"Investimento","#c0392b"))
    with r4:
        roi_g=m["roi"]
        cor_roi_g="green" if roi_g>1 else ("yellow" if roi_g>=0 else "red")
        card("ROI","{:.2f}".format(roi_g),cor_roi_g,delta_html(roi_g,mv.get("roi",0)),sparkline(df_daily,"ROI_calc","#d4a017"))
    r5,r6,r7,r8=st.columns(4)
    with r5: card("Cliques Shopee",fmt_num(m["cliques"]),"yellow",delta_html(m["cliques"],mv.get("cliques",0)),sparkline(df_daily,"Cliques","#d2b095"))
    with r6: card("Vendas",fmt_num(m["vendas"]),"purple",delta_html(m["vendas"],mv.get("vendas",0)),sparkline(df_daily,"Vendas","#9c5834"))
    with r7: card("CTR Shopee",fmt_pct(m["ctr_shopee"]),"blue",delta_html(m["ctr_shopee"],mv.get("ctr_shopee",0)),sparkline(df_daily,"CTR_calc","#bd6d34"))
    with r8: card("Ticket Medio",fmt_brl(m["ticket"]),"orange",delta_html(m["ticket"],mv.get("ticket",0)),sparkline(df_daily,"Ticket_Medio","#bd6d34"))

    # ── CANAIS ──
    st.markdown('<div class="section-title">📂 Performance por Canal</div>',unsafe_allow_html=True)
    cc1,cc2,cc3=st.columns(3)
    def canal_card(col,mc,ma,nome,emoji):
        with col:
            if mc:
                def tr(cur,a):
                    if not ma or a==0: return ""
                    pct=(cur-a)/abs(a)*100; c="#7a9e4e" if pct>0 else "#c0392b"; ar="▲" if pct>0 else "▼"
                    return '<span style="color:{};font-size:10px;">{} {:.1f}%</span>'.format(c,ar,abs(pct))
                a=ma if ma else {}
                st.markdown("""<div class="canal-card"><div class="canal-title">{e} {n}</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                <div><div class="canal-metric">Vendas</div><div class="canal-value">{v}</div>{tv}</div>
                <div><div class="canal-metric">Comissao</div><div class="canal-value">{c}</div>{tc}</div>
                <div><div class="canal-metric">Cliques</div><div class="canal-value">{cl}</div></div>
                <div><div class="canal-metric">CTR</div><div class="canal-value">{ctr}</div></div>
                <div><div class="canal-metric">Ticket Medio</div><div class="canal-value">{tm}</div></div>
                </div></div>""".format(e=emoji,n=nome,v=fmt_num(mc["vendas"]),tv=tr(mc["vendas"],a.get("vendas",0)),
                c=fmt_brl(mc["comissao"]),tc=tr(mc["comissao"],a.get("comissao",0)),
                cl=fmt_num(mc["cliques"]),ctr=fmt_pct(mc["ctr_shopee"]),tm=fmt_brl(mc["ticket"])),unsafe_allow_html=True)
            else:
                st.markdown('<div class="canal-card"><div class="canal-title">{} {}</div><div style="color:#8892a4;">Sem dados</div></div>'.format(emoji,nome),unsafe_allow_html=True)
    canal_card(cc1,m_pago,m_ant_pago,"Pago","📣")
    canal_card(cc2,m_org,m_ant_org,"Organico","🌱")
    canal_card(cc3,m_story,m_ant_story,"Story","📖")

    # ── CAMPANHA PAGO ──
    st.markdown('<div id="pago" class="section-title">📣 Campanha Pago</div>',unsafe_allow_html=True)
    if m_pago:
        lucro_camp=m_pago["comissao"]-invest_pago
        roi_camp=(m_pago["comissao"]-invest_pago)/invest_pago if invest_pago>0 else 0
        cor_roi="green" if roi_camp>1 else ("yellow" if roi_camp>=0 else "red")
        mp=m_ant_pago if m_ant_pago else {}
        n_dias_p=len(df_pago_periodo["Data"].unique()) or 1
        # Periodo anterior para metricas de campanha
        if not df_pago_raw.empty:
            _a_fim=pd.Timestamp(d_ini).date()-timedelta(days=1)
            _a_ini=_a_fim-timedelta(days=(d_fim-d_ini).days)
            _mp_ant=df_pago_raw[(df_pago_raw["Data"].dt.date>=_a_ini)&(df_pago_raw["Data"].dt.date<=_a_fim)]
            imp_p_ant=_mp_ant["Impressoes"].sum()
            alc_p_ant=_mp_ant["Alcance"].sum()
            clq_p_ant=_mp_ant["Cliques_Meta"].sum()
            inv_p_ant=_mp_ant["Investimento"].sum()
        else:
            imp_p_ant=alc_p_ant=clq_p_ant=inv_p_ant=0
        vnd_med=m_pago["vendas"]/n_dias_p
        com_med=m_pago["comissao"]/n_dias_p
        inv_med=invest_pago/n_dias_p
        roi_med=m_pago["roi"]  # mesmo valor, referencia

        def ppair(col,top_label,top_val,top_delta,bot_label,bot_val,bot_delta,color):
            with col:
                st.markdown(
                    '<div class="metric-card {c}" style="margin-bottom:2px;">'
                    '<div class="metric-label">{tl}</div><div class="metric-value">{tv}</div>{td}'
                    '</div>'
                    '<div class="metric-card {c}" style="opacity:0.75;">'
                    '<div class="metric-label">{bl}</div><div class="metric-value" style="font-size:16px;">{bv}</div>{bd}'
                    '</div>'.format(c=color,tl=top_label,tv=top_val,td=top_delta,bl=bot_label,bv=bot_val,bd=bot_delta),
                    unsafe_allow_html=True)

        # Linha 1: resultados financeiros
        st.markdown('<div style="color:#c5936d;font-size:11px;font-weight:600;margin:8px 0 4px 0;">RESULTADOS</div>',unsafe_allow_html=True)
        k1,k2,k3,k4,k5=st.columns(5)
        n_dias_p_ant=len(df_ant_pago["Data"].unique()) if not df_ant_pago.empty else 1
        vnd_med_a=(mp.get("vendas",0)/n_dias_p_ant) if n_dias_p_ant>0 else 0
        com_med_a=(mp.get("comissao",0)/n_dias_p_ant) if n_dias_p_ant>0 else 0
        inv_med_a=(mp.get("invest",0)/n_dias_p_ant) if n_dias_p_ant>0 else 0
        ppair(k1,"Vendas",fmt_num(m_pago["vendas"]),delta_html(m_pago["vendas"],mp.get("vendas",0)),"Media/dia",fmt_num(int(vnd_med)),delta_html(vnd_med,vnd_med_a),"purple")
        ppair(k2,"Comissao",fmt_brl(m_pago["comissao"]),delta_html(m_pago["comissao"],mp.get("comissao",0)),"Media/dia",fmt_brl(com_med),delta_html(com_med,com_med_a),"blue")
        lucro_med=lucro_camp/n_dias_p
        lucro_med_a=(mp.get("lucro",0)/(n_dias_p_ant or 1))
        ppair(k3,"Lucro",fmt_brl(lucro_camp),delta_html(lucro_camp,mp.get("lucro",0)),"Lucro/dia",fmt_brl(lucro_med),delta_html(lucro_med,lucro_med_a),cor_roi)
        ppair(k4,"Investimento",fmt_brl(invest_pago),delta_html(invest_pago,mp.get("invest",0)),"Invest./dia",fmt_brl(inv_med),delta_html(inv_med,inv_med_a),"red")
        # ROI com formatacao condicional
        roi_v=m_pago["roi"]
        roi_cor="red" if roi_v<0 else ("yellow" if roi_v<1 else "green")
        ppair(k5,"ROI","{:.2f}".format(roi_v),delta_html(roi_v,mp.get("roi",0)),"CAC",fmt_brl(m_pago.get("cac",0)),delta_html(m_pago.get("cac",0),mp.get("cac",0)),roi_cor)

        # Linha 2: metricas de campanha
        st.markdown('<div style="color:#c5936d;font-size:11px;font-weight:600;margin:12px 0 4px 0;">CAMPANHA</div>',unsafe_allow_html=True)
        k6,k7,k8,k9=st.columns(4)
        cpm_ant=(inv_p_ant/imp_p_ant*1000) if imp_p_ant>0 else 0
        cpm_alc_ant=(inv_p_ant/alc_p_ant*1000) if alc_p_ant>0 else 0
        cpc_ant=inv_p_ant/clq_p_ant if clq_p_ant>0 else 0
        ppair(k6,"Impressoes",fmt_num(int(m_pago.get("impressoes",0))),delta_html(m_pago.get("impressoes",0),imp_p_ant),"CPM",fmt_brl(m_pago.get("cpm_imp",0)),delta_html(m_pago.get("cpm_imp",0),cpm_ant),"yellow")
        ppair(k7,"Alcance",fmt_num(int(m_pago.get("alcance",0))),delta_html(m_pago.get("alcance",0),alc_p_ant),"CPM Alcance",fmt_brl(m_pago.get("cpm_alc",0)),delta_html(m_pago.get("cpm_alc",0),cpm_alc_ant),"yellow")
        ppair(k8,"Cliques Meta",fmt_num(int(m_pago.get("cliques_meta",0))),delta_html(m_pago.get("cliques_meta",0),clq_p_ant),"CPC",fmt_brl(m_pago.get("cpc",0)),delta_html(m_pago.get("cpc",0),cpc_ant),"orange")
        ppair(k9,"CTR Meta",fmt_pct(m_pago.get("ctr_meta",0)),delta_html(m_pago.get("ctr_meta",0),mp.get("ctr_meta",0)),"Frequencia","{:.2f}x".format(m_pago.get("freq",0)),delta_html(m_pago.get("freq",0),mp.get("freq",0)),"blue")

        # Graficos metricas pago
        if not df_pago_periodo.empty:
            st.markdown('<div style="color:#c5936d;font-size:12px;font-weight:600;margin:12px 0 6px 0;">📈 Evolucao Metricas Campanha</div>',unsafe_allow_html=True)
            df_pd=df_pago_periodo.groupby("Data").agg(Investimento=("Investimento","sum"),Impressoes=("Impressoes","sum"),Alcance=("Alcance","sum"),Cliques_Meta=("Cliques_Meta","sum")).reset_index()
            df_pd_v=df_pago_v.groupby("Data").agg(Vendas=("Vendas","sum"),Comissao=("Comissao","sum")).reset_index()
            df_pd=df_pd.merge(df_pd_v,on="Data",how="left").fillna(0)
            df_pd["CPM"]=(df_pd["Investimento"]/df_pd["Impressoes"]*1000).replace([np.inf,np.nan],0)
            df_pd["CPC"]=(df_pd["Investimento"]/df_pd["Cliques_Meta"]).replace([np.inf,np.nan],0)
            df_pd["CAC"]=(df_pd["Investimento"]/df_pd["Vendas"]).replace([np.inf,np.nan],0)
            df_pd["CTR_Meta"]=(df_pd["Cliques_Meta"]/df_pd["Alcance"]*100).replace([np.inf,np.nan],0)
            met_pd={"Investimento":"Investimento","Impressoes":"Impressoes","Alcance":"Alcance","Cliques Meta":"Cliques_Meta","Vendas":"Vendas","Comissao":"Comissao","CPM":"CPM","CPC":"CPC","CAC":"CAC","CTR Meta":"CTR_Meta"}
            dp={k:v for k,v in met_pd.items() if v in df_pd.columns}
            pc1,pc2=st.columns(2)
            with pc1: pm1=st.selectbox("Barra",list(dp.keys()),index=0,key="pm1")
            with pc2: pm2=st.selectbox("Linha",list(dp.keys()),index=2,key="pm2")
            df_pf=df_pd[(df_pd[dp[pm1]]>0)|(df_pd[dp[pm2]]>0)]
            st.plotly_chart(dual_chart(df_pf,"Data",dp[pm1],dp[pm2],"{} vs {}".format(pm1,pm2),pm1,pm2),use_container_width=True)
    else:
        st.markdown('<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:8px;padding:16px;text-align:center;color:#c5936d;">Sem dados de campanha paga para o periodo seleccionado.</div>',unsafe_allow_html=True)

    # ── AWARENESS ──
    st.markdown('<div id="awareness" class="section-title">📡 Campanha Awareness</div>',unsafe_allow_html=True)
    if not df_aw.empty:
        inv_aw_s=df_aw["Investimento_aw"].sum(); imp_aw=df_aw["Impressoes_aw"].sum()
        alc_aw=df_aw["Alcance_aw"].sum(); vis_aw=df_aw["Visitas_Perfil"].sum()
        seg_aw=df_aw["Seguidores"].sum(); com_aw=df_aw["Comentarios"].sum() if "Comentarios" in df_aw.columns else 0
        cpm_aw=(inv_aw_s/imp_aw*1000) if imp_aw>0 else 0
        cpa_aw=(inv_aw_s/vis_aw) if vis_aw>0 else 0
        cps_aw=(inv_aw_s/seg_aw) if seg_aw>0 else 0
        cpc_aw=(inv_aw_s/com_aw) if com_aw>0 else 0
        freq_aw=imp_aw/alc_aw if alc_aw>0 else 0
        df_aw_ant=semana_anterior(df_aw_raw,d_ini,d_fim) if not df_aw_raw.empty else pd.DataFrame()
        inv_a=df_aw_ant["Investimento_aw"].sum() if not df_aw_ant.empty else 0
        imp_a=df_aw_ant["Impressoes_aw"].sum() if not df_aw_ant.empty else 0
        vis_a=df_aw_ant["Visitas_Perfil"].sum() if not df_aw_ant.empty else 0
        seg_a=df_aw_ant["Seguidores"].sum() if not df_aw_ant.empty else 0
        com_a=df_aw_ant["Comentarios"].sum() if not df_aw_ant.empty else 0
        cpm_a=(inv_a/imp_a*1000) if imp_a>0 else 0
        cpa_a=(inv_a/vis_a) if vis_a>0 else 0
        cps_a=(inv_a/seg_a) if seg_a>0 else 0
        cpc_a=(inv_a/com_a) if com_a>0 else 0

        n_dias_aw=len(df_aw["Data"].unique()) or 1
        inv_aw_med=inv_aw_s/n_dias_aw
        inv_aw_med_a=(inv_a/len(df_aw_ant["Data"].unique())) if not df_aw_ant.empty and len(df_aw_ant["Data"].unique())>0 else 0

        def pair(col,top_label,top_val,top_delta,bot_label,bot_val,bot_delta,color):
            with col:
                st.markdown(
                    '<div class="metric-card {c}" style="margin-bottom:2px;">'
                    '<div class="metric-label">{tl}</div><div class="metric-value">{tv}</div>{td}'
                    '</div>'
                    '<div class="metric-card {c}" style="opacity:0.75;">'
                    '<div class="metric-label">{bl}</div><div class="metric-value" style="font-size:16px;">{bv}</div>{bd}'
                    '</div>'.format(c=color,tl=top_label,tv=top_val,td=top_delta,bl=bot_label,bv=bot_val,bd=bot_delta),
                    unsafe_allow_html=True)

        alc_a=df_aw_ant["Alcance_aw"].sum() if not df_aw_ant.empty else 0
        freq_a=(imp_a/alc_a) if alc_a>0 else 0
        aw1,aw2,aw3=st.columns(3)
        pair(aw1,"Investimento",fmt_brl(inv_aw_s),delta_html(inv_aw_s,inv_a),"Invest./dia",fmt_brl(inv_aw_med),delta_html(inv_aw_med,inv_aw_med_a),"red")
        pair(aw2,"Impressoes",fmt_num(int(imp_aw)),delta_html(imp_aw,imp_a),"CPM",fmt_brl(cpm_aw),delta_html(cpm_aw,cpm_a),"yellow")
        pair(aw3,"Alcance",fmt_num(int(alc_aw)),delta_html(alc_aw,alc_a),"Frequencia","{:.2f}x".format(freq_aw),delta_html(freq_aw,freq_a),"orange")
        aw4,aw5,aw6=st.columns(3)
        pair(aw4,"Visitas ao Perfil",fmt_num(int(vis_aw)),delta_html(vis_aw,vis_a),"Custo/Visita",fmt_brl(cpa_aw),delta_html(cpa_aw,cpa_a),"purple")
        pair(aw5,"Seguidores",fmt_num(int(seg_aw)),delta_html(seg_aw,seg_a),"Custo/Seguidor",fmt_brl(cps_aw),delta_html(cps_aw,cps_a),"green")
        pair(aw6,"Comentarios",fmt_num(int(com_aw)),delta_html(com_aw,com_a),"Custo/Comentario",fmt_brl(cpc_aw),delta_html(cpc_aw,cpc_a),"blue")

        # Grafico awareness
        df_aw_d=df_aw.groupby("Data").agg(Invest=("Investimento_aw","sum"),Impressoes=("Impressoes_aw","sum"),Visitas=("Visitas_Perfil","sum"),Seguidores=("Seguidores","sum"),Comentarios=("Comentarios","sum")).reset_index()
        df_aw_d["CPM"]=(df_aw_d["Invest"]/df_aw_d["Impressoes"]*1000).replace([np.inf,np.nan],0)
        df_aw_d["CPA"]=(df_aw_d["Invest"]/df_aw_d["Visitas"]).replace([np.inf,np.nan],0)
        df_aw_d["CPS"]=(df_aw_d["Invest"]/df_aw_d["Seguidores"]).replace([np.inf,np.nan],0)
        df_aw_d["CPC_aw"]=(df_aw_d["Invest"]/df_aw_d["Comentarios"]).replace([np.inf,np.nan],0)
        met_aw={"Investimento":"Invest","Impressoes":"Impressoes","Alcance":"Alcance","Visitas ao Perfil":"Visitas","Seguidores":"Seguidores","Comentarios":"Comentarios","CPM":"CPM","Custo/Visita":"CPA","Custo/Seguidor":"CPS","Custo/Comentario":"CPC_aw"}
        da={k:v for k,v in met_aw.items() if v in df_aw_d.columns}
        awc1,awc2=st.columns(2)
        with awc1: am1=st.selectbox("Barra",list(da.keys()),index=0,key="am1")
        with awc2: am2=st.selectbox("Linha",list(da.keys()),index=3,key="am2")
        df_awf=df_aw_d[(df_aw_d[da[am1]]>0)|(df_aw_d[da[am2]]>0)]
        st.plotly_chart(dual_chart(df_awf,"Data",da[am1],da[am2],"{} vs {}".format(am1,am2),am1,am2),use_container_width=True)

        # Correlacao awareness -> vendas
        df_os=df[df["Sub_id2"].isin(["organico","story"])].copy()
        df_os["Lucro_os"]=df_os["Comissao"]  # custo zero, lucro = comissao
        df_os_d=df_os.groupby("Data").agg(Vendas=("Vendas","sum"),Lucro_os=("Lucro_os","sum")).reset_index()
        df_aw_s2=df_aw_d[["Data","Invest"]].copy(); df_aw_s2["Data"]=df_aw_s2["Data"]+pd.Timedelta(days=3)
        df_imp=df_os_d.merge(df_aw_s2.rename(columns={"Invest":"Invest_lag"}),on="Data",how="left").fillna(0)
        if len(df_imp)>3 and df_imp["Invest_lag"].sum()>0:
            corr_v=df_imp["Invest_lag"].corr(df_imp["Vendas"])
            corr_l=df_imp["Invest_lag"].corr(df_imp["Lucro_os"])
            aw_t=dict(plot_bgcolor="#0f0d0b",paper_bgcolor="#0f0d0b",font_color="#f6e8d8",legend=dict(font=dict(color="#f6e8d8",size=11),bgcolor="rgba(30,18,16,0.8)"))
            def corr_badge(c):
                cor="#7a9e4e" if c>0.3 else ("#c0392b" if c<-0.1 else "#c5936d")
                txt="positiva" if c>0.3 else ("sem correlacao" if c>=-0.1 else "negativa")
                return cor,txt
            cv_cor,cv_txt=corr_badge(corr_v); cl_cor,cl_txt=corr_badge(corr_l)
            st.markdown(
                '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:8px 0;">'
                '<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:8px;padding:10px 14px;">'
                '<span style="color:#c5936d;font-size:11px;">Awareness -> Vendas Org/Story (lag 3d): </span>'
                '<span style="color:{};font-size:14px;font-weight:700;">{:.2f}</span>'
                ' <span style="color:#c5936d;font-size:10px;">— {}</span></div>'
                '<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:8px;padding:10px 14px;">'
                '<span style="color:#c5936d;font-size:11px;">Awareness -> Lucro Org/Story (lag 3d): </span>'
                '<span style="color:{};font-size:14px;font-weight:700;">{:.2f}</span>'
                ' <span style="color:#c5936d;font-size:10px;">— {}</span></div>'
                '</div>'.format(cv_cor,corr_v,cv_txt,cl_cor,corr_l,cl_txt),
                unsafe_allow_html=True)
            if len(df_imp)>=7:
                df_imp["corr_v_mm"]=df_imp["Invest_lag"].rolling(7,min_periods=3).corr(df_imp["Vendas"])
                df_imp["corr_l_mm"]=df_imp["Invest_lag"].rolling(7,min_periods=3).corr(df_imp["Lucro_os"])
                df_ic=df_imp.dropna(subset=["corr_v_mm"])
                if not df_ic.empty:
                    fig_ct=go.Figure()
                    fig_ct.add_trace(go.Scatter(x=df_ic["Data"],y=df_ic["corr_v_mm"],mode="lines+markers",line=dict(color="#bd6d34",width=2),name="Awareness -> Vendas"))
                    fig_ct.add_trace(go.Scatter(x=df_ic["Data"],y=df_ic["corr_l_mm"],mode="lines+markers",line=dict(color="#9c5834",width=2,dash="dash"),name="Awareness -> Lucro"))
                    fig_ct.add_hline(y=0.3,line_dash="dash",line_color="#7a9e4e",annotation_text="Positiva (0.3)")
                    fig_ct.add_hline(y=0,line_dash="dot",line_color="#c5936d")
                    fig_ct.update_layout(title="Tendencia de Correlacao Awareness (janela 7d)",yaxis=dict(title="Correlacao",color="#c5936d",gridcolor="#2a1f1a"),**aw_t)
                    st.plotly_chart(fig_ct,use_container_width=True)
    else:
        n=len(df_aw_raw) if not df_aw_raw.empty else 0
        st.markdown('<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:8px;padding:16px;text-align:center;color:#c5936d;">{}</div>'.format("Sem dados na aba Resultado Awareness." if n==0 else "Sem dados de Awareness para este periodo ({} linhas totais).".format(n)),unsafe_allow_html=True)

    st.markdown("---")

    # ── CRUZAMENTO DE METRICAS ──
    st.markdown('<div id="cruzamento" class="section-title">🔀 Cruzamento de Metricas</div>',unsafe_allow_html=True)
    df_cross=df_daily.copy()
    if not df_aw.empty:
        df_aw_cx=df_aw.groupby("Data").agg(Visitas=("Visitas_Perfil","sum"),Seguidores=("Seguidores","sum"),Comentarios=("Comentarios","sum")).reset_index()
        df_cross=df_cross.merge(df_aw_cx,on="Data",how="left").fillna(0)
    else:
        for c in ["Visitas","Seguidores","Comentarios"]: df_cross[c]=0.0

    met_disp={
        "Invest. Total (Pago+Awareness)":"Investimento",
        "Invest. Pago":"Invest_pago",
        "Invest. Awareness":"Invest_aw",
        "Vendas":"Vendas",
        "Comissao":"Comissao",
        "Cliques":"Cliques",
        "Ticket Medio":"Ticket_Medio",
        "Visitas Perfil":"Visitas",
        "Seguidores":"Seguidores",
        "Comentarios":"Comentarios",
    }
    disp={k:v for k,v in met_disp.items() if v in df_cross.columns}
    cx1,cx2=st.columns(2)
    with cx1: met1=st.selectbox("Metrica 1 (barras)",list(disp.keys()),index=0,key="cx1")
    with cx2: met2=st.selectbox("Metrica 2 (linha)",list(disp.keys()),index=3,key="cx2")
    col_x,col_y=disp[met1],disp[met2]
    if col_x in df_cross.columns and col_y in df_cross.columns:
        df_cf=df_cross[(df_cross[col_x]>0)|(df_cross[col_y]>0)]
        st.plotly_chart(dual_chart(df_cf,"Data",col_x,col_y,"{} vs {}".format(met1,met2),met1,met2),use_container_width=True)


    # ── EVOLUCAO ──
    st.markdown('<div id="evolucao" class="section-title">📈 Evolucao Temporal</div>',unsafe_allow_html=True)
    met_ev={"Comissao":"Comissao","Vendas":"Vendas","Cliques":"Cliques","Investimento":"Investimento","Ticket Medio":"Ticket_Medio"}
    ev_sel=st.multiselect("Metricas",list(met_ev.keys()),default=["Comissao","Vendas"],key="ev_sel")
    if ev_sel:
        fig=go.Figure(); cores=["#bd6d34","#c5936d","#d2b095","#9c5834","#562d1d"]
        for i,nome in enumerate(ev_sel):
            cr=met_ev[nome]; cor=cores[i%len(cores)]
            if cr in df_daily.columns:
                fig.add_trace(go.Scatter(x=df_daily["Data"],y=df_daily[cr],name=nome,mode="lines+markers",line=dict(color=cor,width=2),marker=dict(size=4)))
                mm7=df_daily[cr].rolling(7,min_periods=1).mean()
                fig.add_trace(go.Scatter(x=df_daily["Data"],y=mm7,name=nome+" MM7",mode="lines",line=dict(color=cor,width=1,dash="dash"),opacity=0.6))
        fig.update_layout(title="Evolucao + Media Movel 7 dias",hovermode="x unified",**PLOTLY_THEME)
        st.plotly_chart(fig,use_container_width=True)

    # ── COMPARACAO CANAIS ──
    st.markdown('<div class="section-title">📊 Comparacao por Canal</div>',unsafe_allow_html=True)
    df_viz=df[df["Sub_id2"].str.strip()!=""].copy()
    df_canal=df_viz.groupby("Sub_id2").agg(Vendas=("Vendas","sum"),Comissao=("Comissao","sum"),Cliques=("Cliques","sum")).reset_index()
    col1,col2=st.columns(2)
    with col1:
        fig=px.bar(df_canal,x="Sub_id2",y="Comissao",title="Comissao por Canal",color="Sub_id2",text="Comissao",color_discrete_sequence=["#bd6d34","#9c5834","#c5936d"])
        fig.update_traces(texttemplate="R$ %{text:,.2f}",textposition="outside"); fig.update_layout(**PLOTLY_THEME); st.plotly_chart(fig,use_container_width=True)
    with col2:
        fig=px.pie(df_canal,names="Sub_id2",values="Vendas",title="Distribuicao Vendas",color_discrete_sequence=["#bd6d34","#9c5834","#c5936d"])
        fig.update_traces(textinfo="percent+label"); fig.update_layout(**PLOTLY_THEME); st.plotly_chart(fig,use_container_width=True)

    # ── CAMPEOES ──
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

    # ── IPA ──
    st.markdown('<div id="ipa" class="section-title">🎯 IPA — Indice de Potencial de Anuncio</div>',unsafe_allow_html=True)
    st.markdown('<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:8px;padding:12px 16px;margin-bottom:12px;color:#c5936d;font-size:12px;">O <b style="color:#f6e8d8;">IPA</b> identifica criativos do organico e story com maior potencial para anuncio directo. Score 0-100. <b style="color:#c0392b;">N/A</b> = menos de 3 vendas.</div>',unsafe_allow_html=True)
    df_ipa=df[df["Sub_id2"].isin(["organico","story"])].groupby(["Sub_id3","Sub_id1"]).agg(Comissao=("Comissao","sum"),Vendas=("Vendas","sum"),Cliques=("Cliques","sum")).reset_index()
    df_ipa["CTR"]=(df_ipa["Vendas"]/df_ipa["Cliques"]*100).fillna(0)
    df_ipa["Ticket"]=(df_ipa["Comissao"]/df_ipa["Vendas"]).fillna(0)
    df_v=df_ipa[df_ipa["Vendas"]>=3].copy()
    if not df_v.empty:
        for col in ["Comissao","Vendas","Ticket","CTR"]:
            mn,mx=df_v[col].min(),df_v[col].max()
            df_v[col+"_n"]=((df_v[col]-mn)/(mx-mn)*100) if mx>mn else 50.0
        df_v["IPA"]=(df_v["Comissao_n"]*0.40+df_v["Vendas_n"]*0.25+df_v["Ticket_n"]*0.25+df_v["CTR_n"]*0.10).round(1)
    ja_pago=set(df[df["Sub_id2"]=="pago"]["Sub_id3"].unique())
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


    # ── TABELA ──
    st.markdown('<div class="section-title">📋 Dados Detalhados</div>',unsafe_allow_html=True)
    df_t=df[["Data","Sub_id2","Sub_id1","Sub_id3","Cliques","Vendas","Comissao"]].copy()
    df_t["Data"]=df_t["Data"].dt.strftime("%Y-%m-%d")
    df_t=df_t.sort_values("Comissao",ascending=False).reset_index(drop=True)
    busca=st.text_input("🔍 Pesquisar",placeholder="Ex: pago, 260302fronha...",key="busca")
    if busca: df_t=df_t[df_t.apply(lambda r:busca.lower() in str(r).lower(),axis=1)]
    st.dataframe(df_t.style.format({"Comissao":"R$ {:.2f}"}),use_container_width=True,height=400)
    st.caption("{} linhas".format(len(df_t)))
    html_r="<html><body><h1>Relatorio Destrava</h1><p>Periodo: {} a {}</p><p>Comissao: {} | Lucro: {} | ROI: {:.2f} | Invest: {}</p>{}</body></html>".format(d_ini,d_fim,fmt_brl(m["comissao"]),fmt_brl(m["lucro"]),m["roi"],fmt_brl(invest_total),df_t.to_html(index=False))
    st.download_button("📥 Download HTML",data=html_r.encode("utf-8"),file_name="relatorio_{}_{}.html".format(d_ini,d_fim),mime="text/html",key="dl_btn")

    # ── INSIGHTS IA ──
    st.markdown('<div id="insights-ia" class="section-title">🤖 DESTRAVA AI</div>',unsafe_allow_html=True)
    st.markdown("""<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">
    <div style="background:#1a1210;border:1px solid #bd6d34;border-radius:10px;padding:16px;"><div style="color:#bd6d34;font-size:13px;font-weight:700;margin-bottom:6px;">Campanha Paga</div><div style="color:#c5936d;font-size:12px;">Analise tecnica de CPM, CPC, CAC, frequencia e funil.</div></div>
    <div style="background:#1a1210;border:1px solid #9c5834;border-radius:10px;padding:16px;"><div style="color:#9c5834;font-size:13px;font-weight:700;margin-bottom:6px;">Todos os Canais + Criativos</div><div style="color:#c5936d;font-size:12px;">Comparacao entre canais + sugestao de criativos baseada no IPA.</div></div>
    </div><div style="color:#c5936d;font-size:11px;margin-bottom:12px;">(*) Cada analise ~$0.01 de creditos Anthropic.</div>""",unsafe_allow_html=True)

    if "analise_camp" not in st.session_state: st.session_state.analise_camp=None
    if "analise_geral" not in st.session_state: st.session_state.analise_geral=None
    btn1,btn2,_=st.columns([1,1,2])
    with btn1: gerar_camp=st.button("Analisar Campanha Paga",use_container_width=True,key="btn_camp")
    with btn2: gerar_geral=st.button("Analisar Todos + Criativos",use_container_width=True,key="btn_geral")

    if gerar_camp and m_pago and not df_pago_periodo.empty:
        with st.spinner("A analisar..."):
            try:
                api_key=st.secrets.get("anthropic",{}).get("api_key","")
                dados="Periodo:{} a {}\nInvest:{:.2f}|Vendas:{:.0f}|Comissao:{:.2f}|Lucro:{:.2f}|ROI:{:.2f}\nCPM:{:.2f}|CPC:{:.2f}|CAC:{:.2f}|Freq:{:.2f}x\nCTR_Meta:{:.2f}%|CTR_Conv:{:.2f}%\nFunil:{:.0f}imp->{:.0f}alc->{:.0f}clq->{:.0f}vnd".format(
                    d_ini,d_fim,invest_pago,m_pago["vendas"],m_pago["comissao"],m_pago["lucro"],m_pago["roi"],
                    m_pago.get("cpm_imp",0),m_pago.get("cpc",0),m_pago.get("cac",0),m_pago.get("freq",0),
                    m_pago.get("ctr_meta",0),m_pago.get("ctr_cv",0),
                    m_pago.get("impressoes",0),m_pago.get("alcance",0),m_pago.get("cliques_meta",0),m_pago["vendas"])
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
                    d_ini,d_fim,m["comissao"],m["lucro"],m["roi"],m["vendas"],
                    m_pago["vendas"] if m_pago else 0,m_pago["comissao"] if m_pago else 0,m_pago["roi"] if m_pago else 0,m_pago["ticket"] if m_pago else 0,
                    m_org["vendas"] if m_org else 0,m_org["comissao"] if m_org else 0,m_org["ticket"] if m_org else 0,
                    m_story["vendas"] if m_story else 0,m_story["comissao"] if m_story else 0,m_story["ticket"] if m_story else 0,
                    invest_aw,top_ipa)
                prompt_g="Es especialista senior Meta Ads e afiliados Shopee. Linguagem tecnica.\nCONTEXTO: PAGO=unico com investimento. ORGANICO/STORY=custo zero. NUNCA migrar verba.\nFornece: 1.Diagnostico. 2.Avaliacao cada canal. 3.Acoes concretas. 4.CRIATIVOS PARA ANUNCIO baseado no IPA com CAC alvo (ticket*0.3-0.5).\nDados:"+dados_g
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
