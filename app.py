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
SHEET_NAME      = "Página1"
SHEET_PAGO      = "Resultados Pago"
SHEET_AWARENESS = "Resultado Awareness"
SHEET_HORARIO   = "Insights_Horario"
SHEET_CATEGORIA = "Insights_Categoria"
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
.metric-card.green{border-left-color:#7a9e4e;border-left-width:6px;}
.metric-card.red{border-left-color:#c0392b;border-left-width:6px;}
.metric-card.yellow{border-left-color:#d4a017;border-left-width:6px;}
.metric-card.purple{border-left-color:#9c5834;}.metric-card.orange{border-left-color:#bd6d34;}
.metric-card.blue{border-left-color:#2980b9;}
.metric-card.roi-green{border-left-color:#7a9e4e;border-left-width:6px;background:linear-gradient(135deg,#1a2614,#1e2c18);}
.metric-card.roi-yellow{border-left-color:#d4a017;border-left-width:6px;background:linear-gradient(135deg,#241f0a,#2a2410);}
.metric-card.roi-red{border-left-color:#c0392b;border-left-width:6px;background:linear-gradient(135deg,#2a1010,#321515);}
.metric-label{color:#c5936d;font-size:11px;text-transform:uppercase;letter-spacing:1px;}
.metric-value{color:#f6e8d8;font-size:22px;font-weight:700;margin-top:4px;}
.metric-delta-pos{color:#7a9e4e;font-size:14px;margin-top:2px;font-weight:500;}
.metric-delta-neg{color:#c0392b;font-size:14px;margin-top:2px;font-weight:500;}
.metric-delta-neu{color:#c5936d;font-size:14px;margin-top:2px;}
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

def card(label,value,color="blue",delta_html_str="",sparkline_fig=None,avg_label="",avg_value="",_key=""):
    avg_html = (
        '<div style="margin-top:6px;padding-top:6px;border-top:1px solid #2a1f1a;display:flex;justify-content:space-between;align-items:center;">'
        '<span style="color:#8892a4;font-size:10px;text-transform:uppercase;letter-spacing:1px;">{}</span>'
        '<span style="color:#c5936d;font-size:13px;font-weight:500;">{}</span></div>'.format(avg_label,avg_value)
    ) if avg_label else ""
    html='<div class="metric-card {}"><div class="metric-label">{}</div><div class="metric-value">{}</div>{}{}</div>'.format(color,label,str(value),delta_html_str or "",avg_html)
    st.markdown(html,unsafe_allow_html=True)
    if sparkline_fig:
        _k = _key if _key else label.replace(" ","_").lower()
        st.plotly_chart(sparkline_fig,use_container_width=True,config={"displayModeBar":False},key=f"spark_{_k}")

def delta_html(val,ref,inverted=False):
    if ref is None or ref==0: return '<span class="metric-delta-neu">sem ref. anterior</span>'
    if ref<0 and val>=0:
        pct=(val-ref)/abs(ref)*100
        if not inverted: return '<span class="metric-delta-pos">▲ {:.1f}% vs período ant.</span>'.format(abs(pct))
        else: return '<span class="metric-delta-neg">▲ {:.1f}% vs período ant.</span>'.format(abs(pct))
    if ref>0 and val<0:
        pct=(val-ref)/abs(ref)*100
        if not inverted: return '<span class="metric-delta-neg">▼ {:.1f}% vs período ant.</span>'.format(abs(pct))
        else: return '<span class="metric-delta-pos">▼ {:.1f}% vs período ant.</span>'.format(abs(pct))
    pct=(val-ref)/abs(ref)*100
    if inverted:
        if pct<0: return '<span class="metric-delta-pos">▼ {:.1f}% vs período ant.</span>'.format(abs(pct))
        elif pct>0: return '<span class="metric-delta-neg">▲ {:.1f}% vs período ant.</span>'.format(pct)
    else:
        if pct>0: return '<span class="metric-delta-pos">▲ {:.1f}% vs período ant.</span>'.format(pct)
        elif pct<0: return '<span class="metric-delta-neg">▼ {:.1f}% vs período ant.</span>'.format(abs(pct))
    return '<span class="metric-delta-neu">= igual período ant.</span>'

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
    res=svc.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID,range=f"{SHEET_NAME}!A1:I").execute()
    vals=res.get("values",[])
    if len(vals)<2: return pd.DataFrame()
    cab=vals[0]; linhas=vals[1:]; mc=len(cab)
    ln=[l+[""]*(mc-len(l)) for l in linhas]
    df=pd.DataFrame(ln,columns=cab)
    nomes=["Data","Sub_id2","Sub_id1","Cliques","Vendas","CTR","Comissao","Sub_id3","Sub_id4"]
    df=df.rename(columns={df.columns[i]:nomes[i] for i in range(min(len(df.columns),len(nomes)))})
    for col in ["Cliques","Vendas","Comissao"]: df[col]=df[col].apply(parse_num)
    df["Data"]=pd.to_datetime(df["Data"],errors="coerce")
    df=df.dropna(subset=["Data"])
    df["Sub_id2"]=df["Sub_id2"].fillna("").str.strip().str.lower()
    df["Sub_id1"]=df["Sub_id1"].fillna("").str.strip()
    df["Sub_id3"]=df["Sub_id3"].fillna("").str.strip()
    if "Sub_id4" in df.columns: df["Sub_id4"]=df["Sub_id4"].astype(str).str.strip().apply(lambda x: "" if x.lower() in ["nan","none",""] else x)
    else: df["Sub_id4"]=""
    return df

@st.cache_data(ttl=300)
def ler_pago():
    svc=autenticar()
    res=svc.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID,range=f"{SHEET_PAGO}!A1:K").execute()
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
    r["Sub_id4"]=df.iloc[:,9].astype(str).str.strip().apply(lambda x: "" if x.lower() in ["nan","none",""] else x) if df.shape[1]>9 else ""
    r=r.dropna(subset=["Data"])
    r=r[r["Investimento"]>0]
    return r

@st.cache_data(ttl=300)
def ler_awareness():
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

@st.cache_data(ttl=300)
def ler_horario():
    svc=autenticar()
    res=svc.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID,range=f"{SHEET_HORARIO}!A1:K").execute()
    vals=res.get("values",[])
    if len(vals)<2: return pd.DataFrame()
    cab=vals[0]; linhas=vals[1:]; mc=len(cab)
    ln=[l+[""]*(mc-len(l)) for l in linhas]
    df=pd.DataFrame(ln,columns=cab)
    df.columns=[c.strip() for c in df.columns]
    rename={"ID do Pedido":"ID_Pedido","Status do Pedido":"Status","Sub_id1":"Sub_id1","Sub_id2":"Sub_id2",
            "Sub_id3":"Sub_id3","Sub_id4":"Sub_id4","Hora do Clique":"Hora_Clique","Hora do Pedido":"Hora_Pedido",
            "Dia da Semana":"DiaSemana","Hora do Dia":"HoraDia","Latência (h)":"Latencia_h"}
    df=df.rename(columns={k:v for k,v in rename.items() if k in df.columns})
    df["Hora_Pedido"]=pd.to_datetime(df["Hora_Pedido"],errors="coerce")
    df["Hora_Clique"]=pd.to_datetime(df["Hora_Clique"],errors="coerce")
    df["Latencia_h"]=df["Latencia_h"].astype(str).str.replace(",",".").pipe(pd.to_numeric,errors="coerce")
    df["HoraDia"]=df["HoraDia"].astype(str).str.replace("h","").pipe(pd.to_numeric,errors="coerce")
    for col in ["Sub_id1","Sub_id2","Sub_id3","Sub_id4","DiaSemana","Status"]:
        if col in df.columns: df[col]=df[col].fillna("").str.strip()
    if "Sub_id1" in df.columns:
        df["Sub_id1"]=df["Sub_id1"].replace("","story")
    if "Sub_id2" in df.columns:
        df["Sub_id2"]=df.apply(
            lambda r: "story" if r.get("Sub_id1","")=="story" and r.get("Sub_id2","")=="" else r.get("Sub_id2",""),
            axis=1)
    return df

@st.cache_data(ttl=300)
def ler_categoria():
    svc=autenticar()
    res=svc.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID,range=f"{SHEET_CATEGORIA}!A1:M").execute()
    vals=res.get("values",[])
    if len(vals)<2: return pd.DataFrame()
    cab=vals[0]; linhas=vals[1:]; mc=len(cab)
    ln=[l+[""]*(mc-len(l)) for l in linhas]
    df=pd.DataFrame(ln,columns=cab)
    df.columns=[c.strip() for c in df.columns]
    rename={"ID do Pedido":"ID_Pedido","Status do Pedido":"Status","Sub_id1":"Sub_id1","Sub_id2":"Sub_id2",
            "Sub_id3":"Sub_id3","Sub_id4":"Sub_id4","Categoria L1":"Cat_L1","Categoria L2":"Cat_L2",
            "Categoria L3":"Cat_L3","Nome do Item":"Produto","Preço (R$)":"Preco",
            "Qtd":"Qtd","Comissão do Item (R$)":"Comissao_item"}
    df=df.rename(columns={k:v for k,v in rename.items() if k in df.columns})
    for col in ["Preco","Comissao_item"]:
        if col in df.columns: df[col]=df[col].astype(str).str.replace(",",".").pipe(pd.to_numeric,errors="coerce").fillna(0)
    if "Qtd" in df.columns: df["Qtd"]=pd.to_numeric(df["Qtd"],errors="coerce").fillna(0)
    for col in ["Sub_id1","Sub_id2","Sub_id3","Sub_id4","Cat_L1","Cat_L2","Cat_L3","Produto","Status"]:
        if col in df.columns: df[col]=df[col].fillna("").str.strip()
    if "Sub_id1" in df.columns:
        df["Sub_id1"]=df["Sub_id1"].replace("","story")
    if "Sub_id2" in df.columns:
        df["Sub_id2"]=df.apply(
            lambda r: "story" if r.get("Sub_id1","")=="story" and r.get("Sub_id2","")=="" else r.get("Sub_id2",""),
            axis=1)
    return df

def check_login():
    try: users=dict(st.secrets["users"])
    except: users={"brenno":"destr@vA!"}
    if "logged_in" not in st.session_state: st.session_state.logged_in=False
    if not st.session_state.logged_in:
        c1,c2,c3=st.columns([1,1.2,1])
        with c2:
            st.markdown("<br><br>",unsafe_allow_html=True)
            st.markdown("""<div style='text-align:center;padding:24px;background:linear-gradient(135deg,#1a1210,#221a16);border-radius:16px;border:1px solid #3a2c28;'>
            <div style='font-size:48px;'>🔓</div><h2 style='color:#f6e8d8;'>MATIQ</h2>
            <p style='color:#bd6d34;'> Analytics</p></div>""",unsafe_allow_html=True)
            with st.form("login_form"):
                u=st.text_input("Utilizador"); p=st.text_input("Password",type="password")
                if st.form_submit_button("Entrar",use_container_width=True):
                    if u in users and users[u]==p:
                        st.session_state.logged_in=True; st.session_state.usuario=u; st.rerun()
                    else: st.error("Credenciais incorrectas.")
        return False
    return True

def render_publicos(df_raw, df_pago_raw):
    from datetime import date, timedelta
    st.markdown('<h1 style="color:#f6e8d8;margin:0;font-size:28px;">👥 Teste de Públicos</h1><p style="color:#c5936d;margin:0 0 16px 0;font-size:13px;">Matiq</p>',unsafe_allow_html=True)
    if "Sub_id4" not in df_raw.columns:
        df_p = pd.DataFrame()
    else:
        df_p = df_raw[(df_raw["Sub_id4"].astype(str).str.strip().replace("nan","") != "") & (df_raw["Sub_id2"].str.lower() == "pago")].copy()
    if df_p.empty:
        st.markdown('''<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:10px;padding:32px;text-align:center;margin-top:40px;"><div style="font-size:40px;margin-bottom:12px;">📭</div><div style="color:#f6e8d8;font-size:16px;font-weight:500;">Sem dados de públicos ainda</div><div style="color:#c5936d;font-size:13px;margin-top:8px;">Quando o script correr com campanhas segmentadas por público (Sub_id4 preenchido), os dados aparecerão aqui.</div></div>''', unsafe_allow_html=True)
        return
    data_min = df_p["Data"].min().date()
    hoje = date.today(); ontem = hoje - timedelta(days=1)
    if "pub_preset" not in st.session_state: st.session_state.pub_preset = "all"
    pp = st.session_state.get("pub_preset","all"); ref = ontem
    if   pp=="7d":  d_ini_def=max(ref-timedelta(days=6),data_min)
    elif pp=="14d": d_ini_def=max(ref-timedelta(days=13),data_min)
    elif pp=="30d": d_ini_def=max(ref-timedelta(days=29),data_min)
    else:           d_ini_def=data_min
    d_fim_def=ontem
    with st.expander("🎛️ Filtros",expanded=False):
        st.markdown('<div style="color:#bd6d34;font-size:12px;font-weight:700;margin-bottom:6px;">📅 Periodo</div>',unsafe_allow_html=True)
        pb1,pb2,pb3,pb4=st.columns(4)
        with pb1:
            if st.button("7 dias",use_container_width=True,key="pb7"): st.session_state.pub_preset="7d"; st.rerun()
        with pb2:
            if st.button("14 dias",use_container_width=True,key="pb14"): st.session_state.pub_preset="14d"; st.rerun()
        with pb3:
            if st.button("30 dias",use_container_width=True,key="pb30"): st.session_state.pub_preset="30d"; st.rerun()
        with pb4:
            if st.button("Tudo",use_container_width=True,key="pba"): st.session_state.pub_preset="all"; st.rerun()
        pdatas=st.date_input("",value=(d_ini_def,d_fim_def),min_value=data_min,max_value=ontem,label_visibility="collapsed",key="pub_datas")
        d_ini,d_fim=(pdatas if isinstance(pdatas,tuple) and len(pdatas)==2 else (d_ini_def,d_fim_def))
    mask = (df_p["Data"].dt.date >= d_ini) & (df_p["Data"].dt.date <= d_fim)
    df_p = df_p[mask].copy()
    if df_p.empty:
        st.warning("Sem dados de públicos no período seleccionado."); return
    publicos = sorted(df_p["Sub_id4"].unique())
    if not df_pago_raw.empty and "Sub_id4" in df_pago_raw.columns:
        df_pago_pub = df_pago_raw[(df_pago_raw["Sub_id4"].astype(str).str.strip().replace("nan","") != "") & (df_pago_raw["Data"].dt.date >= d_ini) & (df_pago_raw["Data"].dt.date <= d_fim)].copy()
        camp_por_pub = df_pago_pub.groupby("Sub_id4").agg(Investimento=("Investimento","sum"),Impressoes=("Impressoes","sum"),Alcance=("Alcance","sum"),Cliques_Meta=("Cliques_Meta","sum")).reset_index()
    else:
        camp_por_pub = pd.DataFrame(columns=["Sub_id4","Investimento","Impressoes","Alcance","Cliques_Meta"])
    rows = []
    for pub in publicos:
        df_pub = df_p[df_p["Sub_id4"] == pub]
        vendas=df_pub["Vendas"].sum(); comissao=df_pub["Comissao"].sum(); cliques=df_pub["Cliques"].sum()
        ctr=vendas/cliques if cliques>0 else 0; ticket=comissao/vendas if vendas>0 else 0
        row_camp = camp_por_pub[camp_por_pub["Sub_id4"] == pub]
        if not row_camp.empty:
            invest=row_camp["Investimento"].iloc[0]; impressoes=row_camp["Impressoes"].iloc[0]
            alcance=row_camp["Alcance"].iloc[0]; cliques_meta=row_camp["Cliques_Meta"].iloc[0]
        else:
            invest=impressoes=alcance=cliques_meta=0.0
        ctr_meta=cliques_meta/alcance*100 if alcance>0 else 0; cpm=invest/impressoes*1000 if impressoes>0 else 0
        cpc=invest/cliques_meta if cliques_meta>0 else 0; freq=impressoes/alcance if alcance>0 else 0
        lucro=comissao-invest; roi=(comissao-invest)/invest if invest>0 else None
        cac=invest/vendas if vendas>0 else None; rpc=comissao/cliques if cliques>0 else 0
        rows.append({"Público":pub,"Vendas":int(vendas),"Comissão":round(comissao,2),"Investimento":round(invest,2),
            "Lucro":round(lucro,2),"ROI":round(roi,2) if roi is not None else None,
            "CAC":round(cac,2) if cac is not None else None,"Cliques":int(cliques),"CTR":round(ctr*100,2),
            "Ticket":round(ticket,2),"RPC":round(rpc,2),"Impressões":int(impressoes),"Alcance":int(alcance),
            "Cliques Meta":int(cliques_meta),"CTR Meta":round(ctr_meta,2),"CPM":round(cpm,2),
            "CPC":round(cpc,2),"Frequência":round(freq,2)})
    df_m = pd.DataFrame(rows)
    n_publicos = len(df_m)
    if not df_m.empty and df_m["ROI"].notna().any():
        campeao_idx = df_m[df_m["ROI"].notna()]["ROI"].idxmax(); campeao = df_m.loc[campeao_idx, "Público"]
    else: campeao = None
    st.markdown(f'''<div style="margin-bottom:1.5rem;"><span style="color:#c5936d;font-size:12px;">Período: </span><span style="color:#f6e8d8;font-size:12px;font-weight:500;">{d_ini.strftime("%d/%m/%Y")} → {d_fim.strftime("%d/%m/%Y")}</span><span style="color:#c5936d;font-size:12px;margin-left:12px;">Públicos activos: </span><span style="color:#f6e8d8;font-size:12px;font-weight:500;">{n_publicos}</span></div>''', unsafe_allow_html=True)
    if campeao:
        row_c = df_m[df_m["Público"]==campeao].iloc[0]; roi_c = row_c["ROI"]
        cor_roi = "#7a9e4e" if roi_c>1 else ("#d4a017" if roi_c>=0 else "#c0392b")
        st.markdown(f'''<div style="background:linear-gradient(135deg,#1a1210,#221a16);border:1px solid #bd6d34;border-radius:12px;padding:16px 20px;margin-bottom:1.5rem;display:flex;align-items:center;gap:16px;"><div style="font-size:28px;">🏆</div><div><div style="color:#bd6d34;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;">Público campeão</div><div style="color:#f6e8d8;font-size:20px;font-weight:500;margin-top:2px;">{campeao}</div><div style="color:#c5936d;font-size:12px;margin-top:2px;">ROI <span style="color:{cor_roi};font-weight:500;">{roi_c:.2f}</span> &nbsp;·&nbsp; {row_c["Vendas"]} vendas &nbsp;·&nbsp; CAC R${row_c["CAC"]:.2f} &nbsp;·&nbsp; CTR {row_c["CTR"]:.2f}%</div></div></div>''', unsafe_allow_html=True)
    st.markdown('<div style="color:#f6e8d8;font-size:15px;font-weight:500;margin-bottom:1rem;padding-bottom:8px;border-bottom:1px solid #3a2c28;">Comparação por público</div>', unsafe_allow_html=True)
    cols = st.columns(n_publicos)
    CORES = ["#bd6d34","#c5936d","#9c5834","#d2b095","#562d1d","#f6e8d8"]
    for i, row in df_m.iterrows():
        pub = row["Público"]; eh_campeao = pub == campeao
        roi_val = row["ROI"]
        if roi_val is None: cor_roi_card = "#bd6d34"; roi_txt = "N/A"
        else:
            cor_roi_card = "#7a9e4e" if roi_val>1 else ("#d4a017" if roi_val>=0 else "#c0392b"); roi_txt = f"{roi_val:.2f}"
        border_col = "#bd6d34" if eh_campeao else "#3a2c28"; border_w = "2px" if eh_campeao else "1px"; trophy = " 🏆" if eh_campeao else ""
        with cols[i]:
            lucro_cor = "#7a9e4e" if row["Lucro"]>=0 else "#c0392b"; cac_txt = f'R${row["CAC"]:.2f}' if row["CAC"] else "N/A"
            st.markdown(f'''<div style="background:linear-gradient(135deg,#1e1410,#221a16);border-radius:12px;padding:14px 16px;border:{border_w} solid {border_col};height:100%;"><div style="color:#bd6d34;font-size:13px;font-weight:600;margin-bottom:10px;">{pub}{trophy}</div><div style="color:#c5936d;font-size:10px;font-weight:600;margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px;">Resultados</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:10px;"><div><div style="color:#c5936d;font-size:9px;text-transform:uppercase;">Vendas</div><div style="color:#f6e8d8;font-size:16px;font-weight:500;">{row["Vendas"]}</div></div><div><div style="color:#c5936d;font-size:9px;text-transform:uppercase;">Comissão</div><div style="color:#f6e8d8;font-size:16px;font-weight:500;">R${row["Comissão"]:.2f}</div></div><div><div style="color:#c5936d;font-size:9px;text-transform:uppercase;">Investimento</div><div style="color:#f6e8d8;font-size:16px;font-weight:500;">R${row["Investimento"]:.2f}</div></div><div><div style="color:#c5936d;font-size:9px;text-transform:uppercase;">Lucro</div><div style="color:{lucro_cor};font-size:16px;font-weight:500;">R${row["Lucro"]:.2f}</div></div><div><div style="color:#c5936d;font-size:9px;text-transform:uppercase;">ROI</div><div style="color:{cor_roi_card};font-size:16px;font-weight:500;">{roi_txt}</div></div><div><div style="color:#c5936d;font-size:9px;text-transform:uppercase;">CAC</div><div style="color:#f6e8d8;font-size:16px;font-weight:500;">{cac_txt}</div></div></div><div style="border-top:0.5px solid #3a2c28;padding-top:8px;margin-bottom:6px;"><div style="color:#c5936d;font-size:10px;font-weight:600;margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px;">Campanha</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;"><div><div style="color:#c5936d;font-size:9px;text-transform:uppercase;">Impressões</div><div style="color:#f6e8d8;font-size:16px;font-weight:500;">{row["Impressões"]:,}</div></div><div><div style="color:#c5936d;font-size:9px;text-transform:uppercase;">Alcance</div><div style="color:#f6e8d8;font-size:16px;font-weight:500;">{row["Alcance"]:,}</div></div><div><div style="color:#c5936d;font-size:9px;text-transform:uppercase;">CPM</div><div style="color:#f6e8d8;font-size:16px;font-weight:500;">R${row["CPM"]:.2f}</div></div><div><div style="color:#c5936d;font-size:9px;text-transform:uppercase;">Cliques</div><div style="color:#f6e8d8;font-size:16px;font-weight:500;">{row["Cliques Meta"]:,}</div></div><div><div style="color:#c5936d;font-size:9px;text-transform:uppercase;">CTR Meta</div><div style="color:#f6e8d8;font-size:16px;font-weight:500;">{row["CTR Meta"]:.2f}%</div></div><div><div style="color:#c5936d;font-size:9px;text-transform:uppercase;">CPC</div><div style="color:#f6e8d8;font-size:16px;font-weight:500;">R${row["CPC"]:.2f}</div></div><div style="grid-column:span 2;"><div style="color:#c5936d;font-size:9px;text-transform:uppercase;">Frequência</div><div style="color:#f6e8d8;font-size:16px;font-weight:500;">{row["Frequência"]:.2f}x</div></div></div></div></div>''', unsafe_allow_html=True)
    st.markdown('<div style="color:#f6e8d8;font-size:15px;font-weight:500;margin:1.5rem 0 1rem;padding-bottom:8px;border-bottom:1px solid #3a2c28;">Gráficos comparativos</div>', unsafe_allow_html=True)
    THEME = dict(plot_bgcolor="#0f0d0b",paper_bgcolor="#0f0d0b",font_color="#f6e8d8",xaxis=dict(color="#c5936d",gridcolor="#2a1f1a"),yaxis=dict(color="#c5936d",gridcolor="#2a1f1a"))
    metricas_graf = ["ROI","CAC","CTR","CTR Meta","CPM","CPC","Ticket","Vendas","Comissão","Impressões","Alcance"]
    sel_met = st.selectbox("Métrica para comparar",metricas_graf,key="pub_metrica")
    col_map = {"ROI":"ROI","CAC":"CAC","CTR":"CTR","CTR Meta":"CTR Meta","CPM":"CPM","CPC":"CPC","Ticket":"Ticket","Vendas":"Vendas","Comissão":"Comissão","Impressões":"Impressões","Alcance":"Alcance"}
    col_k = col_map[sel_met]
    df_graf = df_m[["Público",col_k]].dropna().copy()
    df_graf[col_k] = pd.to_numeric(df_graf[col_k], errors="coerce")
    cor_campeao = [("#bd6d34" if r["Público"]==campeao else "#9c5834") for _,r in df_graf.iterrows()]
    fig = go.Figure(go.Bar(x=df_graf["Público"],y=df_graf[col_k],marker_color=cor_campeao,text=df_graf[col_k].round(2),textposition="outside",width=0.5))
    fig.update_layout(title=f"{sel_met} por público",**THEME,height=300,showlegend=False,margin=dict(t=40,b=0,l=0,r=0))
    st.plotly_chart(fig,use_container_width=True)
    rad_cols = ["ROI","CTR Meta","CPM","CAC","Ticket"]
    df_rad = df_m[["Público"]+rad_cols].dropna()
    if len(df_rad) >= 2:
        inverted_metrics = {"CAC","CPM","CPC"}
        df_norm = df_rad.copy()
        for c in rad_cols:
            col_num = pd.to_numeric(df_rad[c], errors="coerce").fillna(0)
            mn,mx = col_num.min(), col_num.max()
            if mx > mn:
                norm = (col_num - mn) / (mx - mn) * 100
                df_norm[c] = (100 - norm).round(1) if c in inverted_metrics else norm.round(1)
            else: df_norm[c] = 50.0
        fig_r = go.Figure()
        for idx2, row2 in df_norm.iterrows():
            pub2 = row2["Público"]; vals2 = [row2[c] for c in rad_cols] + [row2[rad_cols[0]]]; cats2 = rad_cols + [rad_cols[0]]; cor2 = CORES[idx2 % len(CORES)]
            fig_r.add_trace(go.Scatterpolar(r=vals2,theta=cats2,fill="toself",name=pub2,line_color=cor2,opacity=0.7))
        fig_r.update_layout(polar=dict(bgcolor="#1a1210",radialaxis=dict(visible=True,range=[0,100],gridcolor="#3a2c28",color="#c5936d"),angularaxis=dict(color="#c5936d")),paper_bgcolor="#0f0d0b",font_color="#f6e8d8",legend=dict(bgcolor="#1a1210",bordercolor="#3a2c28",borderwidth=1),height=360,margin=dict(t=20,b=20,l=40,r=40))
        st.plotly_chart(fig_r,use_container_width=True)
    st.markdown('<div style="color:#f6e8d8;font-size:15px;font-weight:500;margin:1.5rem 0 1rem;padding-bottom:8px;border-bottom:1px solid #3a2c28;">Evolução diária por público</div>', unsafe_allow_html=True)
    met_evo = st.selectbox("Métrica diária",["Vendas","Comissao","Cliques"],key="pub_evo")
    df_daily_pub = df_p.groupby(["Data","Sub_id4"]).agg(Vendas=("Vendas","sum"),Comissao=("Comissao","sum"),Cliques=("Cliques","sum")).reset_index()
    fig_evo = go.Figure()
    for i2,pub2 in enumerate(publicos):
        df_sub = df_daily_pub[df_daily_pub["Sub_id4"]==pub2]
        fig_evo.add_trace(go.Scatter(x=df_sub["Data"],y=df_sub[met_evo],name=pub2,mode="lines+markers",line=dict(color=CORES[i2%len(CORES)],width=2),marker=dict(size=5)))
    fig_evo.update_layout(title=f"{met_evo} diário por público",hovermode="x unified",**THEME,height=280,margin=dict(t=40,b=0,l=0,r=0))
    st.plotly_chart(fig_evo,use_container_width=True)
    st.markdown('<div style="color:#f6e8d8;font-size:15px;font-weight:500;margin:1.5rem 0 1rem;padding-bottom:8px;border-bottom:1px solid #3a2c28;">Tabela completa</div>', unsafe_allow_html=True)
    df_tabela = df_m.copy()
    df_tabela["ROI"]=df_tabela["ROI"].apply(lambda x: f"{x:.2f}" if x is not None else "N/A")
    df_tabela["CAC"]=df_tabela["CAC"].apply(lambda x: f"R${x:.2f}" if x is not None else "N/A")
    df_tabela["CTR"]=df_tabela["CTR"].apply(lambda x: f"{x:.2f}%")
    df_tabela["Ticket"]=df_tabela["Ticket"].apply(lambda x: f"R${x:.2f}")
    df_tabela["Comissão"]=df_tabela["Comissão"].apply(lambda x: f"R${x:.2f}")
    df_tabela["Investimento"]=df_tabela["Investimento"].apply(lambda x: f"R${x:.2f}")
    df_tabela["Lucro"]=df_tabela["Lucro"].apply(lambda x: f"R${x:.2f}")
    df_tabela["RPC"]=df_tabela["RPC"].apply(lambda x: f"R${x:.2f}")
    st.dataframe(df_tabela,use_container_width=True,hide_index=True)
    st.markdown('<div style="margin-top:2rem;padding:10px 16px;background:#1a1210;border-radius:8px;border:1px solid #3a2c28;color:#c5936d;font-size:11px;">RPC = Receita Por Clique (Comissão / Cliques) — mede a eficiência monetária de cada clique do público.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
#  RADAR SHOPEE — v2
# ══════════════════════════════════════════════════════════════════════
def render_radar_shopee():
    ORDEM_DIAS = ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"]
    COR        = "#bd6d34"
    CORES      = ["#bd6d34","#c5936d","#9c5834","#d2b095","#7a9e4e","#2980b9","#562d1d"]
    COR_CANAL  = {"story":"#bd6d34","pago":"#9c5834","organico":"#c5936d"}
    THEME_BASE = dict(plot_bgcolor="#0f0d0b", paper_bgcolor="#0f0d0b", font_color="#f6e8d8")
    AXIS       = dict(color="#c5936d", gridcolor="#2a1f1a")
    THEME      = dict(**THEME_BASE, xaxis=AXIS, yaxis=AXIS)
    LEG        = dict(font=dict(color="#f6e8d8", size=11), bgcolor="rgba(30,18,16,0.8)")
    CANAIS_ORD = ["story", "pago", "organico"]

    def sec(titulo):
        st.markdown(f'<div style="color:#f6e8d8;font-size:16px;font-weight:600;margin:28px 0 12px;padding-bottom:8px;border-bottom:1px solid #3a2c28;">{titulo}</div>', unsafe_allow_html=True)

    def kpi(label, valor, sub="", cor_borda="#bd6d34"):
        sub_html = f'<div style="color:#c5936d;font-size:11px;margin-top:3px;">{sub}</div>' if sub else ""
        return (f'<div style="background:linear-gradient(135deg,#1e1410,#221a16);border-radius:12px;'
                f'padding:14px 18px;border-left:4px solid {cor_borda};">'
                f'<div style="color:#c5936d;font-size:10px;text-transform:uppercase;letter-spacing:1px;">{label}</div>'
                f'<div style="color:#f6e8d8;font-size:22px;font-weight:700;margin-top:4px;">{valor}</div>'
                f'{sub_html}</div>')

    def bar_h(pct, cor):
        return (f'<div style="height:8px;border-radius:4px;background:#2a1f1a;margin-top:4px;">'
                f'<div style="height:8px;border-radius:4px;background:{cor};width:{min(pct,100):.0f}%;"></div></div>')

    st.markdown('<h1 style="color:#f6e8d8;margin:0;font-size:28px;">📡 Radar Shopee</h1>'
                '<p style="color:#c5936d;margin:0 0 20px;font-size:13px;">Data Matiq · Análise profunda de comportamento</p>',
                unsafe_allow_html=True)

    with st.spinner("A carregar dados do Radar..."):
        dh = ler_horario()
        dc = ler_categoria()

    if dh.empty and dc.empty:
        st.markdown('<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:10px;padding:32px;text-align:center;">'
                    '<div style="font-size:40px;">📭</div>'
                    '<div style="color:#f6e8d8;font-size:16px;">Sem dados no Radar ainda</div>'
                    '<div style="color:#c5936d;font-size:13px;margin-top:8px;">Corre o script atualizar_planilha.py</div></div>',
                    unsafe_allow_html=True)
        return

    with st.expander("🎛️ Filtros", expanded=True):
        canais_disp   = sorted([x for x in dh["Sub_id2"].unique() if x]) if not dh.empty else []
        status_disp   = sorted([x for x in dh["Status"].unique()  if x]) if not dh.empty else []
        fc1, fc2 = st.columns(2)
        with fc1:
            st.markdown('<div style="color:#bd6d34;font-size:12px;font-weight:700;margin-bottom:4px;">Canal (Sub_id2)</div>', unsafe_allow_html=True)
            canais_sel = st.multiselect("", canais_disp, default=[], placeholder="Todos", label_visibility="collapsed", key="rs_canal")
        with fc2:
            st.markdown('<div style="color:#bd6d34;font-size:12px;font-weight:700;margin-bottom:4px;">Status do Pedido</div>', unsafe_allow_html=True)
            status_sel = st.multiselect("", status_disp, default=[], placeholder="Todos", label_visibility="collapsed", key="rs_status")

    dh = dh.copy(); dc = dc.copy()
    if canais_sel: dh = dh[dh["Sub_id2"].isin(canais_sel)]; dc = dc[dc["Sub_id2"].isin(canais_sel)]
    if status_sel: dh = dh[dh["Status"].isin(status_sel)];  dc = dc[dc["Status"].isin(status_sel)]

    if dh.empty and dc.empty:
        st.warning("Sem dados para os filtros seleccionados."); return

    sec("💰 Resumo do Período")
    total_pedidos  = dh["ID_Pedido"].nunique() if not dh.empty else 0
    total_comissao = dc["Comissao_item"].sum()  if not dc.empty else 0
    ticket_medio   = dc.groupby("ID_Pedido")["Comissao_item"].sum().mean() if not dc.empty else 0
    lat_media      = dh["Latencia_h"].mean()   if not dh.empty else 0
    pct_urgente    = (dh["Latencia_h"] < 1).sum() / max(len(dh[dh["Latencia_h"].notna()]), 1) * 100 if not dh.empty else 0
    top_canal      = (dh[dh["Sub_id2"] != ""]["Sub_id2"].value_counts().idxmax()
                      if not dh.empty and dh["Sub_id2"].any() else "—")

    k1,k2,k3,k4,k5,k6 = st.columns(6)
    k1.markdown(kpi("Pedidos",          f"{total_pedidos:,}"),              unsafe_allow_html=True)
    k2.markdown(kpi("Comissão Total",   fmt_brl(total_comissao)),           unsafe_allow_html=True)
    k3.markdown(kpi("Ticket Médio",     fmt_brl(ticket_medio)),             unsafe_allow_html=True)
    k4.markdown(kpi("Latência Média",   f"{lat_media:.1f}h"),               unsafe_allow_html=True)
    k5.markdown(kpi("Compras Urgentes", f"{pct_urgente:.0f}%", "em menos de 1h"), unsafe_allow_html=True)
    k6.markdown(kpi("Canal Top",        top_canal),                         unsafe_allow_html=True)

    sec("📅 Melhor Dia & Hora")

    if not dh.empty and "DiaSemana" in dh.columns:
        met_dh = st.radio("Métrica", ["🏅 Score IPA","Vendas","Comissão (R$)","Ticket Médio (R$)","Cliques"],
                          horizontal=True, key="rs_dh_met", label_visibility="collapsed")

        # toggle Total / Média por semana — só para métricas com volume acumulável
        if met_dh not in ["🏅 Score IPA", "Ticket Médio (R$)"]:
            _modo = st.radio("", ["📊 Total acumulado", "📈 Média por semana"],
                             horizontal=True, key="rs_dh_modo", label_visibility="collapsed", index=1)
            _usar_media = (_modo == "📈 Média por semana")
        else:
            _usar_media = True

        comissao_por_pedido = dc.groupby("ID_Pedido")["Comissao_item"].sum().reset_index(name="Comissao_ped")
        dh_com = dh.merge(comissao_por_pedido, on="ID_Pedido", how="left")
        dh_com["Comissao_ped"] = dh_com["Comissao_ped"].fillna(0)

        # coluna de semana para usar_media e IPA
        if "Hora_Pedido" in dh_com.columns:
            dh_com["_semana"] = dh_com["Hora_Pedido"].dt.isocalendar().week.astype(str) + "_" + \
                                dh_com["Hora_Pedido"].dt.year.astype(str)
        else:
            dh_com["_semana"] = "s1"

        def _pivot_media(df_src, col_val, grp=["DiaSemana","HoraDia"]):
            """Média por semana: agrega por semana×dia×hora, depois média das semanas."""
            tmp = df_src.copy()
            sem = tmp.groupby(["_semana"] + grp)[col_val].sum().reset_index(name="V")
            return sem.groupby(grp)["V"].mean().reset_index(name="Valor")

        if met_dh == "🏅 Score IPA":
            def norm_s(s):
                mn, mx = s.min(), s.max()
                if mx > mn: return (s - mn) / (mx - mn) * 100
                return pd.Series([50.0]*len(s), index=s.index)

            dia_grp = dh_com.groupby("DiaSemana", dropna=False)
            dia_vnd  = dia_grp["ID_Pedido"].nunique()
            dia_com  = dia_grp["Comissao_ped"].sum()
            dia_tkt  = dia_grp["Comissao_ped"].mean()
            dia_clk  = dia_grp["ID_Pedido"].count()
            dia_urg  = dh_com.assign(Urg=(dh_com["Latencia_h"]<1).astype(float)) \
                             .groupby("DiaSemana")["Urg"].mean() * 100
            dia_sem  = dh_com.groupby("DiaSemana")["_semana"].nunique()

            dia_df = pd.DataFrame({
                "Vendas":    dia_vnd, "Comissao": dia_com, "Ticket": dia_tkt,
                "Cliques":   dia_clk, "PctUrgente": dia_urg, "N_semanas": dia_sem,
            }).fillna(0)
            dia_df_f = dia_df[dia_df["N_semanas"] >= 2].copy()
            if dia_df_f.empty: dia_df_f = dia_df.copy()
            dia_df_f["Score"] = (
                norm_s(dia_df_f["Vendas"])     * 0.25 +
                norm_s(dia_df_f["Comissao"])   * 0.25 +
                norm_s(dia_df_f["Ticket"])     * 0.25 +
                norm_s(dia_df_f["Cliques"])    * 0.125 +
                norm_s(dia_df_f["PctUrgente"]) * 0.125
            ).round(1)

            hora_grp = dh_com.groupby("HoraDia", dropna=False)
            hora_vnd = hora_grp["ID_Pedido"].nunique()
            hora_com = hora_grp["Comissao_ped"].sum()
            hora_tkt = hora_grp["Comissao_ped"].mean()
            hora_clk = hora_grp["ID_Pedido"].count()
            hora_urg = dh_com.assign(Urg=(dh_com["Latencia_h"]<1).astype(float)) \
                             .groupby("HoraDia")["Urg"].mean() * 100
            hora_sem = dh_com.groupby("HoraDia")["_semana"].nunique()
            hora_df = pd.DataFrame({
                "Vendas":    hora_vnd, "Comissao": hora_com, "Ticket": hora_tkt,
                "Cliques":   hora_clk, "PctUrgente": hora_urg, "N_semanas": hora_sem,
            }).fillna(0)
            p10_vol = hora_df["Vendas"].quantile(0.10)
            hora_df_f = hora_df[hora_df["Vendas"] >= max(p10_vol, 1)].copy()
            hora_df_f2 = hora_df_f[hora_df_f["N_semanas"] >= 2].copy()
            if hora_df_f2.empty: hora_df_f2 = hora_df_f.copy()
            hora_df_f2["Score"] = (
                norm_s(hora_df_f2["Vendas"])     * 0.25 +
                norm_s(hora_df_f2["Comissao"])   * 0.25 +
                norm_s(hora_df_f2["Ticket"])     * 0.25 +
                norm_s(hora_df_f2["Cliques"])    * 0.125 +
                norm_s(hora_df_f2["PctUrgente"]) * 0.125
            ).round(1)

            grp = ["DiaSemana","HoraDia"]
            mom_df = dh_com.groupby(grp, dropna=False).agg(
                Vendas=("ID_Pedido","nunique"), Comissao=("Comissao_ped","sum"),
                Ticket=("Comissao_ped","mean"), N_semanas=("_semana","nunique"),
            ).reset_index().fillna(0)
            p10_mom = mom_df["Vendas"].quantile(0.10)
            mom_df_f = mom_df[(mom_df["N_semanas"] >= 2) & (mom_df["Vendas"] >= max(p10_mom,1))].copy()
            if mom_df_f.empty: mom_df_f = mom_df.copy()
            mom_df_f["Score"] = (
                norm_s(mom_df_f["Vendas"])   * 0.25 +
                norm_s(mom_df_f["Comissao"]) * 0.25 +
                norm_s(mom_df_f["Ticket"])   * 0.25 +
                norm_s(mom_df_f["Vendas"])   * 0.125 +
                pd.Series([50.0]*len(mom_df_f), index=mom_df_f.index) * 0.125
            ).round(1)

            pivot_data = mom_df_f[grp + ["Score"]].rename(columns={"Score":"Valor"})
            _score_dia  = dia_df_f["Score"]
            _score_hora = hora_df_f2["Score"]
            fmt_val    = lambda v: f"{v:.0f}"
            agg_func   = "mean"
            y_label    = "Score IPA*"
            nota_pesos = "Métrica exclusiva e de propriedade Matiq"

        elif met_dh == "Vendas":
            if _usar_media:
                pivot_data = _pivot_media(dh_com.assign(V=1).rename(columns={"V":"ID_Pedido_c"}),
                                          col_val="ID_Pedido_c")
                # sobrescrever com nunique por semana
                _tmp = dh_com.copy()
                _sem_grp = _tmp.groupby(["_semana","DiaSemana","HoraDia"])["ID_Pedido"].nunique().reset_index(name="V")
                pivot_data = _sem_grp.groupby(["DiaSemana","HoraDia"])["V"].mean().reset_index(name="Valor")
                agg_func = "mean"; _modo_lbl = "média/semana"
            else:
                pivot_data = dh_com.groupby(["DiaSemana","HoraDia"])["ID_Pedido"].nunique().reset_index(name="Valor")
                agg_func = "sum"; _modo_lbl = "total"
            fmt_val = lambda v: f"{v:.1f}" if _usar_media else f"{v:.0f}"
            y_label = f"Vendas ({_modo_lbl})"; nota_pesos = ""
            _score_dia = None; _score_hora = None

        elif met_dh == "Comissão (R$)":
            if _usar_media:
                _sem_grp2 = dh_com.groupby(["_semana","DiaSemana","HoraDia"])["Comissao_ped"].sum().reset_index(name="V")
                pivot_data = _sem_grp2.groupby(["DiaSemana","HoraDia"])["V"].mean().reset_index(name="Valor")
                agg_func = "mean"; _modo_lbl = "média/semana"
            else:
                pivot_data = dh_com.groupby(["DiaSemana","HoraDia"])["Comissao_ped"].sum().reset_index(name="Valor")
                agg_func = "sum"; _modo_lbl = "total"
            fmt_val = lambda v: fmt_brl(v)
            y_label = f"Comissão ({_modo_lbl})"; nota_pesos = ""
            _score_dia = None; _score_hora = None

        elif met_dh == "Ticket Médio (R$)":
            pivot_data = dh_com.groupby(["DiaSemana","HoraDia"])["Comissao_ped"].mean().reset_index(name="Valor")
            fmt_val = lambda v: fmt_brl(v); agg_func = "mean"
            y_label = "Ticket Médio (R$)"; nota_pesos = ""
            _score_dia = None; _score_hora = None

        else:  # Cliques
            if _usar_media:
                _sem_grp3 = dh_com.groupby(["_semana","DiaSemana","HoraDia"])["ID_Pedido"].count().reset_index(name="V")
                pivot_data = _sem_grp3.groupby(["DiaSemana","HoraDia"])["V"].mean().reset_index(name="Valor")
                agg_func = "mean"; _modo_lbl = "média/semana"
            else:
                pivot_data = dh.groupby(["DiaSemana","HoraDia"])["ID_Pedido"].count().reset_index(name="Valor")
                agg_func = "sum"; _modo_lbl = "total"
            fmt_val = lambda v: f"{v:.1f}" if _usar_media else f"{v:.0f}"
            y_label = f"Cliques ({_modo_lbl})"; nota_pesos = ""
            _score_dia = None; _score_hora = None

        pivot_data["DiaSemana"] = pd.Categorical(pivot_data["DiaSemana"], categories=ORDEM_DIAS, ordered=True)
        pivot_data = pivot_data.dropna(subset=["DiaSemana","HoraDia"]).sort_values(["DiaSemana","HoraDia"])

        if nota_pesos:
            st.markdown(f'<div style="color:#c5936d;font-size:11px;margin-bottom:12px;">ℹ️ {nota_pesos}</div>', unsafe_allow_html=True)

        if not pivot_data.empty and pivot_data["Valor"].sum() > 0:

            if met_dh == "🏅 Score IPA" and _score_dia is not None:
                best_dia_agg  = _score_dia.reindex(ORDEM_DIAS).dropna()
                best_hora_agg = _score_hora
                sub_label     = "score"
            else:
                best_dia_agg  = pivot_data.groupby("DiaSemana")["Valor"].agg(agg_func).reindex(ORDEM_DIAS).dropna()
                best_hora_agg = pivot_data.groupby("HoraDia")["Valor"].agg(agg_func)
                sub_label     = "média" if agg_func == "mean" else "total"

            top3_mom   = pivot_data.nlargest(3, "Valor").reset_index(drop=True)
            top3_dias  = best_dia_agg.nlargest(3)
            top3_horas = best_hora_agg.nlargest(3)

            TONS = [
                {"borda":"#f6e8d8","fundo":"linear-gradient(135deg,#2a2018,#2e2416)","valor":"#f6e8d8","label":"#bd6d34"},
                {"borda":"#bd6d34","fundo":"linear-gradient(135deg,#221a14,#261e18)","valor":"#bd6d34","label":"#c5936d"},
                {"borda":"#9c5834","fundo":"linear-gradient(135deg,#1e1410,#221a16)","valor":"#9c5834","label":"#c5936d"},
            ]
            medalhas = ["🥇","🥈","🥉"]

            col_mom, col_dias, col_horas = st.columns(3)

            with col_mom:
                st.markdown('<div style="color:#c5936d;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">🏆 Top 3 Momentos</div>', unsafe_allow_html=True)
                for i, row_m in top3_mom.iterrows():
                    t = TONS[i]
                    st.markdown(
                        f'<div style="background:{t["fundo"]};border-radius:10px;padding:12px 14px;'
                        f'border-left:3px solid {t["borda"]};margin-bottom:6px;">'
                        f'<div style="color:{t["label"]};font-size:10px;font-weight:700;text-transform:uppercase;">{medalhas[i]} #{i+1}</div>'
                        f'<div style="color:{t["valor"]};font-size:18px;font-weight:700;margin:3px 0;">'
                        f'{row_m["DiaSemana"]} {int(row_m["HoraDia"]):02d}h</div>'
                        f'<div style="color:#c5936d;font-size:10px;">{y_label}: {fmt_val(row_m["Valor"])}</div>'
                        f'</div>',
                        unsafe_allow_html=True)

            with col_dias:
                st.markdown('<div style="color:#c5936d;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">📅 Top 3 Dias</div>', unsafe_allow_html=True)
                for i, (dia, val_d) in enumerate(top3_dias.items()):
                    t = TONS[i]
                    st.markdown(
                        f'<div style="background:{t["fundo"]};border-radius:10px;padding:12px 14px;'
                        f'border-left:3px solid {t["borda"]};margin-bottom:6px;">'
                        f'<div style="color:{t["label"]};font-size:10px;font-weight:700;text-transform:uppercase;">{medalhas[i]} #{i+1}</div>'
                        f'<div style="color:{t["valor"]};font-size:18px;font-weight:700;margin:3px 0;">{dia}</div>'
                        f'<div style="color:#c5936d;font-size:10px;">{y_label} ({sub_label}): {fmt_val(val_d)}</div>'
                        f'</div>',
                        unsafe_allow_html=True)

            with col_horas:
                st.markdown('<div style="color:#c5936d;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">🕐 Top 3 Horas</div>', unsafe_allow_html=True)
                for i, (hora, val_h) in enumerate(top3_horas.items()):
                    t = TONS[i]
                    st.markdown(
                        f'<div style="background:{t["fundo"]};border-radius:10px;padding:12px 14px;'
                        f'border-left:3px solid {t["borda"]};margin-bottom:6px;">'
                        f'<div style="color:{t["label"]};font-size:10px;font-weight:700;text-transform:uppercase;">{medalhas[i]} #{i+1}</div>'
                        f'<div style="color:{t["valor"]};font-size:18px;font-weight:700;margin:3px 0;">{int(hora):02d}h</div>'
                        f'<div style="color:#c5936d;font-size:10px;">{y_label} ({sub_label}): {fmt_val(val_h)}</div>'
                        f'</div>',
                        unsafe_allow_html=True)

            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            h1, h2 = st.columns(2)

            with h1:
                dt = best_dia_agg.reset_index(); dt.columns = ["Dia","Valor"]
                campeao_dia = list(top3_dias.index)[0]
                cor_b = [COR if d == campeao_dia else "#3a2c28" for d in dt["Dia"]]
                fig_d = go.Figure(go.Bar(x=dt["Dia"], y=dt["Valor"], marker_color=cor_b,
                    text=dt["Valor"].apply(fmt_val),
                    textposition="outside", textfont=dict(size=10, color="#c5936d")))
                fig_d.update_layout(title=f"Por Dia da Semana ({y_label})", height=280,
                    margin=dict(t=36,b=0,l=0,r=0), showlegend=False,
                    **THEME_BASE, xaxis=AXIS,
                    yaxis=dict(**AXIS, range=[0, dt["Valor"].max()*1.25] if dt["Valor"].max() > 0 else [0,100]))
                st.plotly_chart(fig_d, use_container_width=True)

            with h2:
                ht = best_hora_agg.reset_index(); ht.columns = ["Hora","Valor"]; ht = ht.sort_values("Hora")
                campeao_hora = list(top3_horas.index)[0]
                cor_h = [COR if int(h) == campeao_hora else "#3a2c28" for h in ht["Hora"]]
                fig_h = go.Figure(go.Bar(
                    x=[f"{int(h):02d}h" for h in ht["Hora"]], y=ht["Valor"],
                    marker_color=cor_h, text=ht["Valor"].apply(fmt_val),
                    textposition="outside", textfont=dict(size=9, color="#c5936d")))
                fig_h.update_layout(title=f"Por Hora do Dia ({y_label})", height=280,
                    margin=dict(t=36,b=0,l=0,r=0), showlegend=False,
                    **THEME_BASE, xaxis=AXIS,
                    yaxis=dict(**AXIS, range=[0, ht["Valor"].max()*1.25] if ht["Valor"].max() > 0 else [0,100]))
                st.plotly_chart(fig_h, use_container_width=True)

    sec("📡 Canal (Sub_id2) em Profundidade")

    if not dh.empty:
        met_canal = st.radio("Métrica", ["Vendas","Comissão (R$)","Ticket Médio (R$)","Cliques"],
                             horizontal=True, key="rs_canal_met", label_visibility="collapsed")

        canais_todos = sorted([c for c in dh["Sub_id2"].unique() if c])
        if met_canal == "Vendas":
            cp = dh.groupby("Sub_id2")["ID_Pedido"].nunique().reset_index(name="Valor")
        elif met_canal == "Comissão (R$)":
            tmp = dh.merge(dc.groupby("ID_Pedido")["Comissao_item"].sum().reset_index(), on="ID_Pedido", how="left")
            cp  = tmp.groupby("Sub_id2")["Comissao_item"].sum().reset_index(name="Valor")
        elif met_canal == "Ticket Médio (R$)":
            tmp = dh.merge(dc.groupby("ID_Pedido")["Comissao_item"].sum().reset_index(), on="ID_Pedido", how="left")
            cp  = tmp.groupby("Sub_id2")["Comissao_item"].mean().reset_index(name="Valor")
        else:
            cp = dh.groupby("Sub_id2")["ID_Pedido"].count().reset_index(name="Valor")

        cp = cp[cp["Sub_id2"] != ""].sort_values("Valor", ascending=True)
        cor_cp = [COR_CANAL.get(c, COR) for c in cp["Sub_id2"]]
        fig_cp = go.Figure(go.Bar(
            x=cp["Valor"], y=cp["Sub_id2"], orientation="h", marker_color=cor_cp,
            text=cp["Valor"].apply(lambda v: f"{v:.0f}" if met_canal in ["Vendas","Cliques"] else fmt_brl(v)),
            textposition="outside", textfont=dict(color="#c5936d", size=11)))
        fig_cp.update_layout(title=f"{met_canal} por Canal", height=max(200, len(cp)*50),
            margin=dict(t=36,b=0,l=0,r=70), showlegend=False, **THEME_BASE, xaxis=AXIS, yaxis=AXIS)
        st.plotly_chart(fig_cp, use_container_width=True)

        st.markdown('<div style="color:#c5936d;font-size:13px;font-weight:600;margin:20px 0 10px;">⏱️ Latência clique → compra por Canal</div>', unsafe_allow_html=True)

        lat_df = dh[dh["Latencia_h"].notna() & (dh["Latencia_h"] >= 0)].copy()

        canais_disp_lat = [c for c in CANAIS_ORD if c in dh["Sub_id2"].unique()] + \
                          [c for c in dh["Sub_id2"].unique() if c not in CANAIS_ORD and c != ""]

        if not lat_df.empty:
            lat_grp = lat_df.groupby("Sub_id2")["Latencia_h"].agg(Media="mean", Mediana="median").reset_index()
            lat_grp = lat_grp[lat_grp["Sub_id2"] != ""]
            lat_grp["_ord"] = lat_grp["Sub_id2"].apply(lambda c: CANAIS_ORD.index(c) if c in CANAIS_ORD else 99)
            lat_grp = lat_grp.sort_values("_ord").drop(columns="_ord")

            cols_lat = st.columns(max(len(lat_grp), 1))
            for idx2, row in lat_grp.iterrows():
                canal_n = row["Sub_id2"]
                cor_c   = COR_CANAL.get(canal_n, COR)
                col_idx = list(lat_grp.index).index(idx2)
                with cols_lat[col_idx]:
                    st.markdown(
                        f'<div style="background:linear-gradient(135deg,#1e1410,#221a16);border-radius:12px;'
                        f'padding:14px 16px;border-left:4px solid {cor_c};margin-bottom:8px;">'
                        f'<div style="color:{cor_c};font-size:11px;font-weight:700;text-transform:uppercase;margin-bottom:8px;">{canal_n}</div>'
                        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">'
                        f'<div><div style="color:#c5936d;font-size:9px;text-transform:uppercase;">Média</div>'
                        f'<div style="color:#f6e8d8;font-size:22px;font-weight:700;">{row["Media"]:.1f}h</div></div>'
                        f'<div><div style="color:#c5936d;font-size:9px;text-transform:uppercase;">Mediana</div>'
                        f'<div style="color:#f6e8d8;font-size:22px;font-weight:700;">{row["Mediana"]:.1f}h</div></div>'
                        f'</div></div>',
                        unsafe_allow_html=True)

            st.markdown('<div style="color:#c5936d;font-size:12px;font-weight:600;margin:18px 0 10px;">🚦 Distribuição de Compras por Janela de Tempo</div>', unsafe_allow_html=True)

            COR_F1 = "#7a9e4e"; COR_F2 = "#d4a017"; COR_F3 = "#c0392b"

            rows_urg = []
            for canal_n in canais_disp_lat:
                sub = lat_df[lat_df["Sub_id2"] == canal_n]["Latencia_h"]
                if len(sub) == 0: continue
                f1 = (sub < 1).sum()  / len(sub) * 100
                f2 = ((sub >= 1) & (sub < 6)).sum() / len(sub) * 100
                f3 = (sub >= 6).sum() / len(sub) * 100
                rows_urg.append({"canal": canal_n, "f1": f1, "f2": f2, "f3": f3, "n": len(sub)})

            if rows_urg:
                cols_urg = st.columns(len(rows_urg))
                for i, r in enumerate(rows_urg):
                    cor_c = COR_CANAL.get(r["canal"], COR)
                    with cols_urg[i]:
                        st.markdown(
                            f'<div style="background:linear-gradient(135deg,#1e1410,#221a16);border-radius:12px;'
                            f'padding:14px 16px;border-left:4px solid {cor_c};">'
                            f'<div style="color:{cor_c};font-size:11px;font-weight:700;text-transform:uppercase;margin-bottom:12px;">{r["canal"]} (n={r["n"]})</div>'
                            f'<div style="margin-bottom:8px;">'
                            f'<div style="display:flex;justify-content:space-between;margin-bottom:2px;">'
                            f'<span style="color:#c5936d;font-size:11px;">&#60;1h (imediato)</span>'
                            f'<span style="color:{COR_F1};font-size:12px;font-weight:700;">{r["f1"]:.0f}%</span></div>'
                            f'{bar_h(r["f1"], COR_F1)}</div>'
                            f'<div style="margin-bottom:8px;">'
                            f'<div style="display:flex;justify-content:space-between;margin-bottom:2px;">'
                            f'<span style="color:#c5936d;font-size:11px;">1h–6h (rápido)</span>'
                            f'<span style="color:{COR_F2};font-size:12px;font-weight:700;">{r["f2"]:.0f}%</span></div>'
                            f'{bar_h(r["f2"], COR_F2)}</div>'
                            f'<div>'
                            f'<div style="display:flex;justify-content:space-between;margin-bottom:2px;">'
                            f'<span style="color:#c5936d;font-size:11px;">&gt;6h (longo prazo)</span>'
                            f'<span style="color:{COR_F3};font-size:12px;font-weight:700;">{r["f3"]:.0f}%</span></div>'
                            f'{bar_h(r["f3"], COR_F3)}</div>'
                            f'</div>',
                            unsafe_allow_html=True)

            st.markdown('<div style="color:#c5936d;font-size:12px;font-weight:600;margin:18px 0 8px;">Distribuição de Latência por Canal (histograma)</div>', unsafe_allow_html=True)
            canal_hist = st.selectbox("Canal", canais_disp_lat, key="rs_hist_canal")
            df_hist = lat_df[lat_df["Sub_id2"] == canal_hist]["Latencia_h"].clip(upper=72)
            cor_hist = COR_CANAL.get(canal_hist, COR)
            fig_hist = go.Figure(go.Histogram(x=df_hist, nbinsx=30, marker_color=cor_hist, opacity=0.85,
                hovertemplate="Latência: %{x:.1f}h<br>Pedidos: %{y}<extra></extra>"))
            fig_hist.add_vline(x=df_hist.mean(),   line_dash="dash", line_color="#f6e8d8",
                annotation_text=f"Média: {df_hist.mean():.1f}h",   annotation_font_color="#f6e8d8")
            fig_hist.add_vline(x=df_hist.median(), line_dash="dot",  line_color="#c5936d",
                annotation_text=f"Mediana: {df_hist.median():.1f}h", annotation_font_color="#c5936d")
            fig_hist.update_layout(title=f"Distribuição de Latência — {canal_hist} (cap. 72h)",
                height=280, margin=dict(t=36,b=0,l=0,r=0), **THEME_BASE, xaxis=AXIS, yaxis=AXIS,
                xaxis_title="Latência (h)", yaxis_title="Nº Pedidos")
            st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown('<div style="color:#c5936d;font-size:13px;font-weight:600;margin:20px 0 10px;">📈 Vendas por Canal × Dia da Semana</div>', unsafe_allow_html=True)
        cd = dh[dh["Sub_id2"] != ""].groupby(["Sub_id2","DiaSemana"])["ID_Pedido"].nunique().reset_index(name="Vendas")
        cd["DiaSemana"] = pd.Categorical(cd["DiaSemana"], categories=ORDEM_DIAS, ordered=True)
        cd = cd.dropna(subset=["DiaSemana"]).sort_values("DiaSemana")
        canais_graf = [c for c in CANAIS_ORD if c in cd["Sub_id2"].unique()] + \
                      [c for c in cd["Sub_id2"].unique() if c not in CANAIS_ORD and c != ""]
        COR_CANAL_LINHA = {"story":"#f6e8d8","pago":"#bd6d34","organico":"#7a9e4e"}
        fig_cd = go.Figure()
        for canal_n in canais_graf:
            sub = cd[cd["Sub_id2"] == canal_n]
            if sub.empty: continue
            fig_cd.add_trace(go.Scatter(x=sub["DiaSemana"], y=sub["Vendas"], mode="lines+markers",
                name=canal_n,
                line=dict(color=COR_CANAL_LINHA.get(canal_n, COR), width=3),
                marker=dict(size=8, symbol="circle")))
        fig_cd.update_layout(title="Vendas por Canal × Dia da Semana", height=300,
            margin=dict(t=36,b=0,l=0,r=0), **THEME_BASE, xaxis=AXIS, yaxis=AXIS, legend=LEG)
        st.plotly_chart(fig_cd, use_container_width=True)

    sec("🏷️ Categoria Aprofundada")

    if not dc.empty and "Cat_L1" in dc.columns:
        met_cat = st.radio("Métrica", ["Vendas","Comissão (R$)","Ticket Médio (R$)","Cliques","CTR (%)"],
                           horizontal=True, key="rs_cat_met", label_visibility="collapsed")

        nivel_cat = st.radio("Nível", ["L1","L1 + L2","L1 + L2 + L3"], horizontal=True, key="rs_cat_nivel")

        def agg_cat(df_in, cols_grp, met):
            if met == "Vendas":
                return df_in.groupby(cols_grp, dropna=False)["ID_Pedido"].nunique().reset_index(name="Valor")
            elif met == "Comissão (R$)":
                return df_in.groupby(cols_grp, dropna=False)["Comissao_item"].sum().reset_index(name="Valor")
            elif met == "Ticket Médio (R$)":
                return df_in.groupby(cols_grp, dropna=False).apply(
                    lambda x: x.groupby("ID_Pedido")["Comissao_item"].sum().mean()
                ).reset_index(name="Valor")
            elif met == "Cliques":
                return df_in.groupby(cols_grp, dropna=False)["ID_Pedido"].count().reset_index(name="Valor")
            else:
                tot = df_in.groupby(cols_grp, dropna=False)["ID_Pedido"].nunique()
                cli = df_in.groupby(cols_grp, dropna=False)["ID_Pedido"].count()
                return (tot / cli.replace(0, np.nan) * 100).reset_index(name="Valor")

        if nivel_cat == "L1":
            cat_perf = agg_cat(dc, "Cat_L1", met_cat)
            cat_perf["Label"] = cat_perf["Cat_L1"]
        elif nivel_cat == "L1 + L2":
            cat_perf = agg_cat(dc, ["Cat_L1","Cat_L2"], met_cat)
            cat_perf["Label"] = cat_perf["Cat_L1"] + " › " + cat_perf["Cat_L2"]
        else:
            cat_perf = agg_cat(dc, ["Cat_L1","Cat_L2","Cat_L3"], met_cat)
            cat_perf["Label"] = cat_perf["Cat_L1"] + " › " + cat_perf["Cat_L2"] + " › " + cat_perf["Cat_L3"]

        cat_perf = cat_perf[cat_perf["Label"].str.strip().replace("nan","").replace(" › "," › ") != ""].copy()
        cat_perf = cat_perf[~cat_perf["Label"].str.contains("nan", na=False)]
        cat_perf = cat_perf.sort_values("Valor", ascending=True).tail(20)

        cor_cat = [COR if i == len(cat_perf)-1 else "#2a1f1a" for i in range(len(cat_perf))]
        fig_cat = go.Figure(go.Bar(
            x=cat_perf["Valor"], y=cat_perf["Label"], orientation="h", marker_color=cor_cat,
            text=cat_perf["Valor"].apply(lambda v: f"{v:.0f}" if met_cat in ["Vendas","Cliques"] else fmt_brl(v) if "R$" in met_cat else f"{v:.1f}%"),
            textposition="outside", textfont=dict(color="#c5936d", size=10)))
        fig_cat.update_layout(title=f"{met_cat} por Categoria ({nivel_cat})",
            height=max(300, len(cat_perf)*36), margin=dict(t=36,b=0,l=0,r=90), showlegend=False,
            **THEME_BASE, xaxis=AXIS, yaxis=AXIS)
        st.plotly_chart(fig_cat, use_container_width=True)

        st.markdown('<div style="color:#c5936d;font-size:12px;font-weight:600;margin:20px 0 8px;">📅 Sazonalidade — Melhor Dia por Categoria</div>', unsafe_allow_html=True)
        if not dh.empty:
            dc_dia = dc.merge(dh[["ID_Pedido","DiaSemana"]].drop_duplicates(), on="ID_Pedido", how="left")
            dc_dia = dc_dia[dc_dia["DiaSemana"].notna() & (dc_dia["DiaSemana"] != "")]

            nivel_sazon = st.radio("Nível da sazonalidade", ["L1","L1 + L2","L1 + L2 + L3"],
                                   horizontal=True, key="rs_sazon_nivel")

            if nivel_sazon == "L1":
                sazon = dc_dia.groupby(["Cat_L1","DiaSemana"])["Comissao_item"].sum().reset_index()
                sazon["Label"] = sazon["Cat_L1"]
                cats_sazon = sorted([c for c in sazon["Label"].unique() if c and c != "nan"])
            elif nivel_sazon == "L1 + L2":
                sazon = dc_dia.groupby(["Cat_L1","Cat_L2","DiaSemana"])["Comissao_item"].sum().reset_index()
                sazon["Label"] = sazon["Cat_L1"] + " › " + sazon["Cat_L2"]
                cats_sazon = sorted([c for c in sazon["Label"].unique() if "nan" not in c and c != ""])
            else:
                sazon = dc_dia.groupby(["Cat_L1","Cat_L2","Cat_L3","DiaSemana"])["Comissao_item"].sum().reset_index()
                sazon["Label"] = sazon["Cat_L1"] + " › " + sazon["Cat_L2"] + " › " + sazon["Cat_L3"]
                cats_sazon = sorted([c for c in sazon["Label"].unique() if "nan" not in c and c != ""])

            sazon["DiaSemana"] = pd.Categorical(sazon["DiaSemana"], categories=ORDEM_DIAS, ordered=True)
            sazon = sazon.dropna(subset=["DiaSemana"]).sort_values("DiaSemana")

            if cats_sazon:
                cat_sel = st.selectbox("Categoria", cats_sazon, key="rs_sazon_cat")
                df_s = sazon[sazon["Label"] == cat_sel]
                if not df_s.empty:
                    melhor_d = df_s.loc[df_s["Comissao_item"].idxmax(), "DiaSemana"]
                    cor_s = [COR if d == melhor_d else "#2a1f1a" for d in df_s["DiaSemana"]]
                    fig_s = go.Figure(go.Bar(
                        x=df_s["DiaSemana"], y=df_s["Comissao_item"],
                        marker_color=cor_s,
                        text=df_s["Comissao_item"].apply(fmt_brl),
                        textposition="outside", textfont=dict(color="#c5936d", size=10)))
                    fig_s.update_layout(title=f"Comissão por Dia — {cat_sel}",
                        height=260, margin=dict(t=36,b=0,l=0,r=0), showlegend=False,
                        **THEME_BASE, xaxis=AXIS, yaxis=AXIS)
                    st.plotly_chart(fig_s, use_container_width=True)

    sec("🎯 Concentração — Produtos de Entrada (Sub_id3)")

    if not dc.empty and "Sub_id3" in dc.columns:
        total_dc_pedidos  = dc["ID_Pedido"].nunique()
        total_dc_comissao = dc["Comissao_item"].sum()

        pe_all = dc.copy()
        pe_com_sub3 = pe_all[pe_all["Sub_id3"].str.strip() != ""]
        cobertura_ped = pe_com_sub3["ID_Pedido"].nunique()
        cobertura_com = pe_com_sub3["Comissao_item"].sum()
        pct_ped = cobertura_ped / max(total_dc_pedidos,1) * 100
        pct_com = cobertura_com / max(total_dc_comissao,0.01) * 100

        cor_aviso = "#7a9e4e" if pct_com >= 70 else ("#d4a017" if pct_com >= 40 else "#c0392b")
        st.markdown(
            f'<div style="background:#1a1210;border:1px solid {cor_aviso};border-radius:8px;'
            f'padding:10px 16px;margin-bottom:12px;">'
            f'<span style="color:{cor_aviso};font-size:12px;font-weight:700;">📊 Cobertura do Sub_id3: </span>'
            f'<span style="color:#f6e8d8;font-size:12px;">'
            f'{cobertura_ped} de {total_dc_pedidos} pedidos ({pct_ped:.0f}%) · '
            f'{fmt_brl(cobertura_com)} de {fmt_brl(total_dc_comissao)} ({pct_com:.0f}% da comissão total)'
            f'</span>'
            f'{"" if pct_com >= 70 else "<br><span style=\'color:#c5936d;font-size:11px;\'>Pedidos sem Sub_id3 não aparecem no gráfico — provavelmente vendas antigas antes de implementar o rastreio.</span>"}'
            f'</div>',
            unsafe_allow_html=True)

        pe = pe_com_sub3.groupby("Sub_id3").agg(
            Pedidos      = ("ID_Pedido",    "nunique"),
            Comissao     = ("Comissao_item","sum"),
        ).reset_index().sort_values("Comissao", ascending=False).reset_index(drop=True)

        if not pe.empty:
            pe["Acum_pct"] = pe["Comissao"].cumsum() / pe["Comissao"].sum() * 100
            n_80      = int((pe["Acum_pct"] <= 80).sum()) + 1
            total_pe  = len(pe)
            val_80    = pe.head(n_80)["Comissao"].sum()

            c1, c2, c3 = st.columns(3)
            c1.markdown(kpi("Produtos de Entrada", f"{total_pe}", "com Sub_id3 preenchido"), unsafe_allow_html=True)
            c2.markdown(kpi("Fazem 80% da Comissão", f"{n_80}", f"de {total_pe} produtos"), unsafe_allow_html=True)
            c3.markdown(kpi(f"Comissão Top {n_80}", fmt_brl(val_80), f"{pct_com:.0f}% cobertura rastreada"), unsafe_allow_html=True)

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            pe_plot = pe.head(min(25, total_pe))
            cor_pe  = [COR if i < n_80 else "#2a1f1a" for i in range(len(pe_plot))]
            fig_pe  = go.Figure()
            fig_pe.add_trace(go.Bar(
                x=pe_plot["Sub_id3"], y=pe_plot["Comissao"],
                marker_color=cor_pe, name="Comissão",
                hovertemplate="%{x}<br>Comissão: R$ %{y:.2f}<extra></extra>"))
            fig_pe.add_trace(go.Scatter(
                x=pe_plot["Sub_id3"], y=pe_plot["Acum_pct"].head(len(pe_plot)),
                mode="lines", name="% Acumulado", yaxis="y2",
                line=dict(color="#f6e8d8", width=2),
                hovertemplate="%{y:.1f}%<extra></extra>"))
            fig_pe.add_hline(y=80, line_dash="dash", line_color="#d4a017",
                annotation_text="80%", annotation_font_color="#d4a017",
                annotation_position="right", yref="y2")
            fig_pe.update_layout(
                title=f"Pareto — os {n_80} produtos em laranja = 80% da comissão rastreada",
                height=320, margin=dict(t=44,b=60,l=0,r=0),
                yaxis2=dict(overlaying="y", side="right", color="#c5936d", ticksuffix="%", range=[0,105]),
                xaxis=dict(tickangle=-45, color="#c5936d", gridcolor="#2a1f1a"),
                yaxis=dict(color="#c5936d", gridcolor="#2a1f1a"),
                **THEME_BASE, legend=LEG, barmode="overlay")
            st.plotly_chart(fig_pe, use_container_width=True)

    sec("🔭 IPV — Índice de Potencial de Viralização")

    st.markdown(
        '<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:8px;padding:12px 16px;margin-bottom:16px;color:#c5936d;font-size:12px;">'
        'O <b style="color:#f6e8d8;">IPV</b> identifica os <b style="color:#f6e8d8;">produtos finais</b> (o que o cliente realmente comprou) '
        'com maior potencial de virar produto de entrada (Sub_id3) ou campanha paga. '
        'Score 0–100.'
        '</div>', unsafe_allow_html=True)

    if not dc.empty and "Produto" in dc.columns:
        df_ipv = dc[dc["Produto"].str.strip() != ""].copy()

        ipv_grp = df_ipv.groupby("Produto").agg(
            Pedidos       = ("ID_Pedido",     "nunique"),
            Qtd           = ("Qtd",           "sum"),
            Comissao      = ("Comissao_item", "sum"),
            Preco_medio   = ("Preco",         "mean"),
            N_canais      = ("Sub_id2",       "nunique"),
            N_sub3        = ("Sub_id3",       "nunique"),
        ).reset_index()

        ticket_por_ped = df_ipv.groupby(["Produto","ID_Pedido"])["Comissao_item"].sum().reset_index()
        ipv_ticket     = ticket_por_ped.groupby("Produto")["Comissao_item"].mean().reset_index(name="Ticket")
        ipv_grp        = ipv_grp.merge(ipv_ticket, on="Produto", how="left")

        df_ipv_v = ipv_grp[ipv_grp["Pedidos"] >= 2].copy()
        if not df_ipv_v.empty:
            def norm(s):
                mn, mx = s.min(), s.max()
                return ((s - mn) / (mx - mn) * 100) if mx > mn else pd.Series([50.0]*len(s), index=s.index)

            df_ipv_v["IPV"] = (
                norm(df_ipv_v["Ticket"])   * 0.35 +
                norm(df_ipv_v["Pedidos"])  * 0.25 +
                norm(df_ipv_v["N_canais"]) * 0.20 +
                norm(df_ipv_v["N_sub3"])   * 0.10 +
                norm(df_ipv_v["Qtd"])      * 0.10
            ).round(1)
            df_ipv_v = df_ipv_v.sort_values("IPV", ascending=False).reset_index(drop=True)

            top5 = df_ipv_v.head(5)
            cols_ipv = st.columns(5)
            for i, row in top5.iterrows():
                cor_ipv = "#7a9e4e" if row["IPV"] >= 70 else (COR if row["IPV"] >= 40 else "#9c5834")
                with cols_ipv[i]:
                    st.markdown(
                        f'<div style="background:linear-gradient(135deg,#1e1410,#221a16);border-radius:12px;'
                        f'padding:12px 14px;border-left:4px solid {cor_ipv};min-height:130px;">'
                        f'<div style="color:{cor_ipv};font-size:18px;font-weight:700;">IPV {row["IPV"]:.0f}</div>'
                        f'<div style="color:#f6e8d8;font-size:11px;font-weight:600;margin:6px 0;line-height:1.3;">{row["Produto"][:50]}</div>'
                        f'<div style="color:#c5936d;font-size:10px;">'
                        f'Ticket: {fmt_brl(row["Ticket"])} · {int(row["Pedidos"])} ped.<br>'
                        f'{int(row["N_canais"])} canal(is) · {int(row["N_sub3"])} entrada(s)'
                        f'</div></div>',
                        unsafe_allow_html=True)

            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

            top15 = df_ipv_v.head(15).sort_values("IPV", ascending=True)
            cor_ipv_bar = ["#7a9e4e" if v >= 70 else (COR if v >= 40 else "#9c5834") for v in top15["IPV"]]
            fig_ipv = go.Figure(go.Bar(
                x=top15["IPV"],
                y=top15["Produto"].str[:40],
                orientation="h",
                marker_color=cor_ipv_bar,
                text=top15["IPV"].apply(lambda v: f"{v:.0f}"),
                textposition="outside",
                textfont=dict(color="#c5936d", size=11),
                customdata=top15[["Ticket","Pedidos","N_canais","N_sub3"]].values,
                hovertemplate="<b>%{y}</b><br>IPV: %{x:.0f}<br>Ticket: R$ %{customdata[0]:.2f}<br>Pedidos: %{customdata[1]:.0f}<br>Canais: %{customdata[2]:.0f}<br>Entradas distintas: %{customdata[3]:.0f}<extra></extra>"))
            fig_ipv.update_layout(
                title="Top 15 Produtos por IPV",
                height=max(300, len(top15)*38),
                margin=dict(t=36,b=0,l=0,r=50),
                showlegend=False,
                **THEME_BASE,
                xaxis=dict(range=[0, 115], **AXIS),
                yaxis=AXIS)
            st.plotly_chart(fig_ipv, use_container_width=True)

    sec("🏆 Todos os Produtos Finais")

    if not dc.empty and "Produto" in dc.columns:
        tp = dc[dc["Produto"].str.strip() != ""].groupby(["Produto","Cat_L1","Cat_L2"]).agg(
            Pedidos       = ("ID_Pedido",     "nunique"),
            Qtd           = ("Qtd",           "sum"),
            Comissao      = ("Comissao_item", "sum"),
            Preco_medio   = ("Preco",         "mean"),
            N_canais      = ("Sub_id2",       "nunique"),
        ).reset_index()

        if not dc.empty and "Produto" in dc.columns:
            df_ipv_merge = dc[dc["Produto"].str.strip() != ""].groupby("Produto").agg(
                Pedidos_ipv = ("ID_Pedido","nunique"),
                N_canais_ipv= ("Sub_id2","nunique"),
                N_sub3_ipv  = ("Sub_id3","nunique"),
            ).reset_index()
            ticket_ipv = dc.groupby(["Produto","ID_Pedido"])["Comissao_item"].sum().reset_index()
            ticket_ipv = ticket_ipv.groupby("Produto")["Comissao_item"].mean().reset_index(name="Ticket_ipv")
            df_ipv_merge = df_ipv_merge.merge(ticket_ipv, on="Produto", how="left")
            if not df_ipv_merge.empty and len(df_ipv_merge[df_ipv_merge["Pedidos_ipv"] >= 2]) > 0:
                dv2 = df_ipv_merge[df_ipv_merge["Pedidos_ipv"] >= 2].copy()
                def norm2(s):
                    mn, mx = s.min(), s.max()
                    return ((s - mn) / (mx - mn) * 100) if mx > mn else pd.Series([50.0]*len(s), index=s.index)
                dv2["IPV"] = (
                    norm2(dv2["Ticket_ipv"])   * 0.35 +
                    norm2(dv2["Pedidos_ipv"])  * 0.25 +
                    norm2(dv2["N_canais_ipv"]) * 0.20 +
                    norm2(dv2["N_sub3_ipv"])   * 0.10 +
                    norm2(dv2["Pedidos_ipv"])  * 0.10
                ).round(1)
                tp = tp.merge(dv2[["Produto","IPV"]], on="Produto", how="left")
            else:
                tp["IPV"] = np.nan
        else:
            tp["IPV"] = np.nan

        tp = tp.sort_values("Comissao", ascending=False).reset_index(drop=True)
        tp.index = tp.index + 1

        tp_display = tp.copy()
        tp_display["Comissao"]   = tp_display["Comissao"].apply(fmt_brl)
        tp_display["Preco_medio"]= tp_display["Preco_medio"].apply(fmt_brl)
        tp_display["Qtd"]        = tp_display["Qtd"].apply(lambda v: f"{int(v):,}".replace(",","."))
        tp_display["IPV"]        = tp_display["IPV"].apply(lambda v: f"{v:.0f}" if pd.notna(v) else "—")
        tp_display = tp_display.rename(columns={
            "Produto":"Produto","Cat_L1":"Cat. L1","Cat_L2":"Cat. L2",
            "Pedidos":"Pedidos","Qtd":"Qtd","Comissao":"Comissão",
            "Preco_medio":"Preço Médio","N_canais":"Canais","IPV":"IPV"})
        tp_display = tp_display[["Produto","Cat. L1","Cat. L2","Pedidos","Qtd","Comissão","Preço Médio","Canais","IPV"]]

        busca_prod = st.text_input("🔍 Pesquisar produto", placeholder="Ex: fronha, cafeteira...", key="rs_busca_prod")
        if busca_prod:
            tp_display = tp_display[tp_display.apply(lambda r: busca_prod.lower() in str(r).lower(), axis=1)]

        st.dataframe(tp_display, use_container_width=True, height=500)
        st.caption(f"{len(tp_display)} produtos")

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    if st.button("🔄 Actualizar Radar", key="rs_refresh"):
        st.cache_data.clear(); st.rerun()

def main():
    if not check_login(): return

    with st.sidebar:
        if "pagina" not in st.session_state: st.session_state.pagina="dashboard"
        st.markdown('<div style="color:#c5936d;font-size:11px;font-weight:600;margin-bottom:8px;">NAVEGAÇÃO</div>',unsafe_allow_html=True)
        col_nav1,col_nav2=st.columns(2)
        with col_nav1:
            if st.button("📊 Dashboard",use_container_width=True,type="primary" if st.session_state.pagina=="dashboard" else "secondary"):
                st.session_state.pagina="dashboard"; st.rerun()
        with col_nav2:
            if st.button("👥 Públicos",use_container_width=True,type="primary" if st.session_state.pagina=="publicos" else "secondary"):
                st.session_state.pagina="publicos"; st.rerun()
        if st.button("📡 Radar Shopee",use_container_width=True,type="primary" if st.session_state.pagina=="radar" else "secondary"):
            st.session_state.pagina="radar"; st.rerun()
        st.markdown("---")
        if st.session_state.pagina=="dashboard":
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

    pagina_actual = st.session_state.get("pagina","dashboard")

    if pagina_actual == "radar":
        render_radar_shopee()
        return

    st.markdown('<h1 style="color:#f6e8d8;margin:0;font-size:28px;">📊 Dashboard de Performance</h1><p style="color:#c5936d;margin:0 0 16px 0;font-size:13px;">Data Matiq</p>',unsafe_allow_html=True)

    with st.spinner("A carregar dados..."):
        df_raw=ler_dados(); df_pago_raw=ler_pago(); df_aw_raw=ler_awareness()

    if df_raw.empty:
        st.error("Sem dados na planilha Resultados Shopee."); return

    if pagina_actual == "publicos":
        render_publicos(df_raw, df_pago_raw)
        return

    data_min=df_raw["Data"].min().date(); data_max=df_raw["Data"].max().date()
    hoje=date.today(); ontem=hoje-timedelta(days=1); ref=ontem
    if "preset" not in st.session_state: st.session_state.preset="7d"
    p=st.session_state.get("preset","all")
    if   p=="ontem": d_ini_def=ontem
    elif p=="7d":   d_ini_def=max(ref-timedelta(days=6),data_min)
    elif p=="14d":  d_ini_def=max(ref-timedelta(days=13),data_min)
    elif p=="28d":  d_ini_def=max(ref-timedelta(days=27),data_min)
    elif p=="30d":  d_ini_def=max(ref-timedelta(days=29),data_min)
    else:           d_ini_def=data_min
    d_fim_def=ontem
    sid2_opts = sorted([x for x in df_raw["Sub_id2"].unique() if str(x).strip()])
    sid1_opts = sorted([x for x in df_raw["Sub_id1"].unique() if str(x).strip()])
    sid3_opts = sorted([x for x in df_raw["Sub_id3"].unique() if str(x).strip()])

    # Inicializar estado dos filtros aplicados (separado dos widgets)
    if "filtros_aplicados" not in st.session_state:
        st.session_state.filtros_aplicados = {
            "d_ini": d_ini_def, "d_fim": d_fim_def,
            "sid2": [], "sid1": [], "sid3": []
        }
    if "filtros_reset_cnt" not in st.session_state:
        st.session_state.filtros_reset_cnt = 0
    _rc = st.session_state.filtros_reset_cnt  # sufixo dos keys

    # Expander: aberto por defeito, fecha após aplicar filtros
    _filtros_aberto = st.session_state.get("_filtros_expander_open", False)
    if "_filtros_expander_open" in st.session_state:
        del st.session_state["_filtros_expander_open"]
    with st.expander("🎛️ Filtros", expanded=_filtros_aberto):
        st.markdown('<div style="color:#bd6d34;font-size:12px;font-weight:700;margin-bottom:6px;">📅 Periodo</div>', unsafe_allow_html=True)
        b1,b2,b3,b4,b5,b6 = st.columns(6)
        with b1:
            if st.button("Ontem",   use_container_width=True, key="b0"):  st.session_state.preset="ontem"; st.rerun()
        with b2:
            if st.button("7 dias",  use_container_width=True, key="b7"):  st.session_state.preset="7d";    st.rerun()
        with b3:
            if st.button("14 dias", use_container_width=True, key="b14"): st.session_state.preset="14d";   st.rerun()
        with b4:
            if st.button("28 dias", use_container_width=True, key="b28"): st.session_state.preset="28d";   st.rerun()
        with b5:
            if st.button("30 dias", use_container_width=True, key="b30"): st.session_state.preset="30d";   st.rerun()
        with b6:
            if st.button("Tudo",    use_container_width=True, key="ba"):  st.session_state.preset="all";   st.rerun()
        datas = st.date_input("", value=(d_ini_def, d_fim_def), min_value=data_min, max_value=hoje, label_visibility="collapsed")
        d_ini_widget, d_fim_widget = (datas if isinstance(datas, tuple) and len(datas) == 2 else (d_ini_def, d_fim_def))

        st.markdown("<hr style='border-color:#3a2c28;margin:10px 0;'>", unsafe_allow_html=True)
        st.markdown('<div style="color:#bd6d34;font-size:12px;font-weight:700;margin-bottom:4px;">Canal (Sub_id2)</div>', unsafe_allow_html=True)
        sid2_widget = st.multiselect("", sid2_opts, default=[], placeholder="Todos", label_visibility="collapsed", key=f"ms2_{_rc}")
        st.markdown("<hr style='border-color:#3a2c28;margin:10px 0;'>", unsafe_allow_html=True)
        st.markdown('<div style="color:#bd6d34;font-size:12px;font-weight:700;margin-bottom:4px;">Sub_id1</div>', unsafe_allow_html=True)
        sid1_widget = st.multiselect("", sid1_opts, default=[], placeholder="Todos", label_visibility="collapsed", key=f"ms1_{_rc}")
        st.markdown("<hr style='border-color:#3a2c28;margin:10px 0;'>", unsafe_allow_html=True)
        st.markdown('<div style="color:#bd6d34;font-size:12px;font-weight:700;margin-bottom:4px;">Sub_id3</div>', unsafe_allow_html=True)
        sid3_widget = st.multiselect("", sid3_opts, default=[], placeholder="Todos", label_visibility="collapsed", key=f"ms3_{_rc}")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        _, bcol1, bcol2 = st.columns([4, 1, 1])
        with bcol1:
            if st.button("✕ Limpar", use_container_width=True, key="btn_limpar"):
                # Incrementar contador → widgets recriados com key novo = visualmente vazios
                st.session_state.filtros_reset_cnt += 1
                st.session_state.filtros_aplicados = {
                    "d_ini": d_ini_def, "d_fim": d_fim_def,
                    "sid2": [], "sid1": [], "sid3": []
                }
                st.session_state["_a_limpar"] = True
                st.session_state.preset = "7d"
                st.rerun()
        with bcol2:
            if st.button("🔍 Aplicar", use_container_width=True, type="primary", key="btn_aplicar"):
                st.session_state.filtros_aplicados = {
                    "d_ini": d_ini_widget, "d_fim": d_fim_widget,
                    "sid2": sid2_widget, "sid1": sid1_widget, "sid3": sid3_widget
                }
                st.rerun()

    # Fonte de verdade: filtros_aplicados
    # Se acabou de limpar, não actualizar com valores dos widgets (estão a ser apagados)
    _a_limpar = st.session_state.pop("_a_limpar", False)
    if not _a_limpar:
        _fa_actual = st.session_state.filtros_aplicados
        _widgets_mudaram = (
            d_ini_widget  != _fa_actual["d_ini"] or
            d_fim_widget  != _fa_actual["d_fim"] or
            sid2_widget   != _fa_actual["sid2"] or
            sid1_widget   != _fa_actual["sid1"] or
            sid3_widget   != _fa_actual["sid3"]
        )
        if _widgets_mudaram:
            st.session_state.filtros_aplicados = {
                "d_ini": d_ini_widget, "d_fim": d_fim_widget,
                "sid2": sid2_widget, "sid1": sid1_widget, "sid3": sid3_widget
            }
    fa = st.session_state.filtros_aplicados
    d_ini, d_fim = fa["d_ini"], fa["d_fim"]
    sid2_activo = set(fa["sid2"]) if fa["sid2"] else None
    sid1_activo = set(fa["sid1"]) if fa["sid1"] else None
    sid3_activo = set(fa["sid3"]) if fa["sid3"] else None

    # Mostrar resumo dos filtros activos
    filtros_activos = []
    if sid2_activo: filtros_activos.append("Canal: " + ", ".join(sorted(sid2_activo)))
    if sid1_activo: filtros_activos.append("Sub_id1: " + ", ".join(sorted(sid1_activo)))
    if sid3_activo: filtros_activos.append("Sub_id3: " + ", ".join(sorted(sid3_activo)))
    if filtros_activos:
        st.markdown(
            '<div style="background:#1a1210;border:1px solid #bd6d34;border-radius:8px;'
            'padding:8px 14px;margin-bottom:8px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">'
            '<span style="color:#bd6d34;font-size:11px;font-weight:700;">🎛️ Filtros activos:</span>'
            + "".join(f'<span style="background:#2a1f1a;color:#f6e8d8;font-size:11px;padding:2px 8px;border-radius:10px;">{f}</span>' for f in filtros_activos)
            + '</div>',
            unsafe_allow_html=True
        )

    # Aplicar filtros ao df_raw
    mask = (df_raw["Data"].dt.date >= d_ini) & (df_raw["Data"].dt.date <= d_fim)
    if sid2_activo: mask = mask & df_raw["Sub_id2"].isin(sid2_activo)
    if sid1_activo: mask = mask & df_raw["Sub_id1"].isin(sid1_activo)
    if sid3_activo: mask = mask & df_raw["Sub_id3"].isin(sid3_activo)
    df = df_raw[mask].copy()

    # Filtrar df_pago_periodo
    if not df_pago_raw.empty:
        mp = (df_pago_raw["Data"].dt.date >= d_ini) & (df_pago_raw["Data"].dt.date <= d_fim)
        if sid1_activo:
            mp = mp & df_pago_raw["Sub_id1"].isin(sid1_activo)
        if sid3_activo:
            sid1s_do_sid3 = set(
                df_raw[
                    (df_raw["Data"].dt.date >= d_ini) &
                    (df_raw["Data"].dt.date <= d_fim) &
                    df_raw["Sub_id3"].isin(sid3_activo)
                ]["Sub_id1"].unique()
            )
            mp = mp & df_pago_raw["Sub_id1"].isin(sid1s_do_sid3)
        df_pago_periodo = df_pago_raw[mp].copy()
    else:
        df_pago_periodo = pd.DataFrame()

    # Awareness: omitir quando qualquer filtro está activo (canal, sub_id1 ou sub_id3)
    aw_omitido = bool(sid2_activo or sid1_activo or sid3_activo)
    if not aw_omitido and not df_aw_raw.empty:
        ma = (df_aw_raw["Data"].dt.date >= d_ini) & (df_aw_raw["Data"].dt.date <= d_fim)
        df_aw = df_aw_raw[ma].copy()
    else:
        df_aw = pd.DataFrame()
    if df.empty:
        msg_filtros = " + ".join(filtros_activos) if filtros_activos else ""
        msg = (f'Sem dados para os filtros seleccionados ({msg_filtros}).' if filtros_activos
               else f'Sem dados para o período seleccionado. Dados disponíveis até {data_max}.')
        st.markdown(f'<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:10px;padding:24px;text-align:center;"><div style="font-size:32px;">📭</div><div style="color:#f6e8d8;font-size:16px;">{msg}</div></div>', unsafe_allow_html=True)
        st.stop()
    import datetime as _dt
    _todas_datas=set(df_raw[(df_raw["Data"].dt.date>=d_ini)&(df_raw["Data"].dt.date<=d_fim)]["Data"].dt.date.unique())
    _n_dias=(d_fim-d_ini).days+1
    _datas_esperadas={d_ini+_dt.timedelta(days=i) for i in range(_n_dias)}
    _gaps=sorted(_datas_esperadas-_todas_datas)
    _hoje=_dt.date.today()
    _gaps=[d for d in _gaps if d<_hoje and d<=ontem]
    if _gaps:
        _gaps_txt=_gaps[0].strftime("%d/%m") if len(_gaps)==1 else (", ".join(d.strftime("%d/%m") for d in _gaps) if len(_gaps)<=3 else ", ".join(d.strftime("%d/%m") for d in _gaps[:3])+f" (+{len(_gaps)-3})")
        st.markdown(f'''<div style="background:#1a1210;border:1px solid #d4a017;border-radius:8px;padding:10px 16px;margin-bottom:12px;display:flex;align-items:center;gap:10px;"><span style="font-size:14px;">⚠️</span><span style="color:#d4a017;font-size:12px;font-weight:600;">Sem dados em: <span style="font-weight:400;">{_gaps_txt}</span> — o script pode não ter corrido nesses dias.</span></div>''',unsafe_allow_html=True)
    # invest_pago = 0 se filtro de canal excluir "pago"
    _canal_tem_pago = (sid2_activo is None) or ("pago" in sid2_activo)
    invest_pago = (df_pago_periodo["Investimento"].sum() if (not df_pago_periodo.empty and _canal_tem_pago) else 0.0)
    # Awareness omitido quando há filtro de Sub_id1/Sub_id3 — não incluir no invest_total
    invest_aw=df_aw["Investimento_aw"].sum() if (not df_aw.empty and not aw_omitido) else 0.0
    invest_total=invest_pago+invest_aw
    _ant_fim=pd.Timestamp(d_ini).date()-timedelta(days=1); _ant_ini=_ant_fim-timedelta(days=(d_fim-d_ini).days)
    # Período anterior: respeitar os mesmos filtros de Sub_id1
    _pago_raw_ant=df_pago_raw[(df_pago_raw["Data"].dt.date>=_ant_ini)&(df_pago_raw["Data"].dt.date<=_ant_fim)] if not df_pago_raw.empty else pd.DataFrame()
    if sid1_activo and not _pago_raw_ant.empty: _pago_raw_ant=_pago_raw_ant[_pago_raw_ant["Sub_id1"].isin(sid1_activo)]
    invest_pago_ant=_pago_raw_ant["Investimento"].sum() if not _pago_raw_ant.empty else 0.0
    invest_aw_ant=(df_aw_raw[(df_aw_raw["Data"].dt.date>=_ant_ini)&(df_aw_raw["Data"].dt.date<=_ant_fim)]["Investimento_aw"].sum() if (not df_aw_raw.empty and not aw_omitido) else 0.0)
    invest_total_ant=invest_pago_ant+invest_aw_ant
    m=calcular(df); m["invest"]=invest_pago; m["invest_total"]=invest_total; m["lucro"]=m["comissao"]-invest_total; m["roi"]=(m["comissao"]-invest_total)/invest_total if invest_total>0 else 0
    if not df_pago_periodo.empty:
        m["impressoes"]=df_pago_periodo["Impressoes"].sum(); m["alcance"]=df_pago_periodo["Alcance"].sum(); m["cliques_meta"]=df_pago_periodo["Cliques_Meta"].sum()
    df_ant=semana_anterior(df_raw,d_ini,d_fim); m_ant=calcular(df_ant) if not df_ant.empty else None; mv=m_ant if m_ant else {}
    df_pago_v=df[df["Sub_id2"]=="pago"]; df_org=df[df["Sub_id2"]=="organico"]; df_story=df[df["Sub_id2"]=="story"]
    df_wpp=df[df["Sub_id2"]=="grupo1"]
    m_pago=calcular(df_pago_v) if len(df_pago_v)>0 else None; m_org=calcular(df_org) if len(df_org)>0 else None; m_story=calcular(df_story) if len(df_story)>0 else None
    m_wpp=calcular(df_wpp) if len(df_wpp)>0 else None
    if m_pago and not df_pago_periodo.empty:
        m_pago["invest"]=invest_pago; m_pago["lucro"]=m_pago["comissao"]-invest_pago; m_pago["roi"]=(m_pago["comissao"]-invest_pago)/invest_pago if invest_pago>0 else 0
        m_pago["impressoes"]=df_pago_periodo["Impressoes"].sum(); m_pago["alcance"]=df_pago_periodo["Alcance"].sum(); m_pago["cliques_meta"]=df_pago_periodo["Cliques_Meta"].sum()
        m_pago["cpm_imp"]=(invest_pago/m_pago["impressoes"]*1000) if m_pago["impressoes"]>0 else 0
        m_pago["cpm_alc"]=(invest_pago/m_pago["alcance"]*1000) if m_pago["alcance"]>0 else 0
        m_pago["cpc"]=invest_pago/m_pago["cliques_meta"] if m_pago["cliques_meta"]>0 else 0
        m_pago["cac"]=invest_pago/m_pago["vendas"] if m_pago["vendas"]>0 else 0
        m_pago["ctr_meta"]=(m_pago["cliques_meta"]/m_pago["alcance"]*100) if m_pago["alcance"]>0 else 0
        m_pago["ctr_cv"]=(m_pago["vendas"]/m_pago["cliques_meta"]*100) if m_pago["cliques_meta"]>0 else 0
        m_pago["freq"]=m_pago["impressoes"]/m_pago["alcance"] if m_pago["alcance"]>0 else 0
    df_ant_pago=df_ant[df_ant["Sub_id2"]=="pago"] if not df_ant.empty else pd.DataFrame()
    df_ant_org=df_ant[df_ant["Sub_id2"]=="organico"] if not df_ant.empty else pd.DataFrame()
    df_ant_story=df_ant[df_ant["Sub_id2"]=="story"] if not df_ant.empty else pd.DataFrame()
    df_ant_wpp=df_ant[df_ant["Sub_id2"]=="grupo1"] if not df_ant.empty else pd.DataFrame()
    m_ant_pago=calcular(df_ant_pago) if not df_ant_pago.empty else None
    m_ant_org=calcular(df_ant_org) if not df_ant_org.empty else None
    m_ant_story=calcular(df_ant_story) if not df_ant_story.empty else None
    m_ant_wpp=calcular(df_ant_wpp) if not df_ant_wpp.empty else None
    df_daily=df.groupby("Data").agg(Vendas=("Vendas","sum"),Comissao=("Comissao","sum"),Cliques=("Cliques","sum")).reset_index().sort_values("Data")
    df_daily["Ticket_Medio"]=df_daily.apply(lambda r:r["Comissao"]/r["Vendas"] if r["Vendas"]>0 else 0,axis=1)
    df_daily["CTR_calc"]=df_daily.apply(lambda r:r["Vendas"]/r["Cliques"]*100 if r["Cliques"]>0 else 0,axis=1)
    if not df_pago_periodo.empty:
        inv_d=df_pago_periodo.groupby("Data").agg(Invest_pago=("Investimento","sum")).reset_index()
        df_daily=df_daily.merge(inv_d,on="Data",how="left"); df_daily["Invest_pago"]=df_daily["Invest_pago"].fillna(0)
    else: df_daily["Invest_pago"]=0.0
    if not df_aw.empty:
        inv_aw_d=df_aw.groupby("Data").agg(Invest_aw=("Investimento_aw","sum")).reset_index()
        df_daily=df_daily.merge(inv_aw_d,on="Data",how="left"); df_daily["Invest_aw"]=df_daily["Invest_aw"].fillna(0)
    else: df_daily["Invest_aw"]=0.0
    df_daily["Investimento"]=df_daily["Invest_pago"]+df_daily["Invest_aw"]
    df_daily["ROI_calc"]=df_daily.apply(lambda r:(r["Comissao"]-r["Investimento"])/r["Investimento"] if r["Investimento"]>0 else 0,axis=1)
    df_daily["Lucro_calc"]=df_daily["Comissao"]-df_daily["Investimento"]
    n_dias_sel = max((d_fim - d_ini).days + 1, 1)  # dias do período seleccionado

    st.markdown('<div id="kpis" class="section-title">💰 KPIs Gerais</div>',unsafe_allow_html=True)
    r1,r2,r3,r4=st.columns(4)
    with r1: card("Comissao Total",fmt_brl(m["comissao"]),"blue",delta_html(m["comissao"],mv.get("comissao",0)),sparkline(df_daily,"Comissao","#bd6d34"),avg_label="média/dia",avg_value=fmt_brl(m["comissao"]/n_dias_sel),_key="comissao")
    comissao_total_ant=mv.get("comissao",0); lucro_ant=(comissao_total_ant-invest_total_ant) if invest_total_ant>0 else None
    with r2: card("Lucro Total",fmt_brl(m["lucro"]),"green" if m["lucro"]>=0 else "red",delta_html(m["lucro"],lucro_ant if lucro_ant is not None else 0),sparkline(df_daily,"Lucro_calc","#9c5834"),avg_label="média/dia",avg_value=fmt_brl(m["lucro"]/n_dias_sel),_key="lucro")
    with r3: card("Investimento Total",fmt_brl(invest_total),"red",delta_html(invest_total,invest_total_ant,inverted=True),sparkline(df_daily,"Investimento","#c0392b"),avg_label="média/dia",avg_value=fmt_brl(invest_total/n_dias_sel),_key="investimento")
    with r4:
        roi_g=m["roi"]; cor_roi_g="roi-green" if roi_g>1 else ("roi-yellow" if roi_g>=0 else "roi-red")
        comissao_ant=mv.get("comissao",0); roi_ant=(comissao_ant-invest_total_ant)/invest_total_ant if invest_pago_ant>0 and invest_total_ant>0 else None
        _roi_med = df_daily["ROI_calc"][df_daily["Investimento"]>0].mean() if (df_daily["Investimento"]>0).any() else 0
        card("ROI","{:.2f}".format(roi_g),cor_roi_g,delta_html(roi_g,roi_ant if roi_ant is not None else None),sparkline(df_daily,"ROI_calc","#d4a017"),avg_label="média/dia",avg_value="{:.2f}".format(_roi_med),_key="roi")
        st.markdown('<div style="font-size:12px;color:#c5936d;margin-top:-8px;"><span style="color:#7a9e4e;">■</span> &gt;1 bom &nbsp;<span style="color:#d4a017;">■</span> 0-1 atencao &nbsp;<span style="color:#c0392b;">■</span> &lt;0 prejuizo</div>',unsafe_allow_html=True)
    r5,r6,r7,r8=st.columns(4)
    with r5: card("Cliques Shopee",fmt_num(m["cliques"]),"yellow",delta_html(m["cliques"],mv.get("cliques",0)),sparkline(df_daily,"Cliques","#d2b095"),avg_label="média/dia",avg_value=fmt_num(int(m["cliques"]/n_dias_sel)),_key="cliques")
    with r6: card("Vendas",fmt_num(m["vendas"]),"purple",delta_html(m["vendas"],mv.get("vendas",0)),sparkline(df_daily,"Vendas","#9c5834"),avg_label="média/dia",avg_value=fmt_num(int(m["vendas"]/n_dias_sel)),_key="vendas")
    _ctr_med = df_daily["CTR_calc"][df_daily["CTR_calc"]>0].mean() if (df_daily["CTR_calc"]>0).any() else 0
    with r7: card("CTR Shopee",fmt_pct(m["ctr_shopee"]),"blue",delta_html(m["ctr_shopee"],mv.get("ctr_shopee",0)),sparkline(df_daily,"CTR_calc","#bd6d34"),avg_label="média/dia",avg_value=fmt_pct(_ctr_med),_key="ctr")
    _tk_med = df_daily["Ticket_Medio"][df_daily["Ticket_Medio"]>0].mean() if (df_daily["Ticket_Medio"]>0).any() else 0
    with r8: card("Ticket Medio",fmt_brl(m["ticket"]),"orange",delta_html(m["ticket"],mv.get("ticket",0)),sparkline(df_daily,"Ticket_Medio","#bd6d34"),avg_label="média/dia",avg_value=fmt_brl(_tk_med),_key="ticket")

    st.markdown('<div class="section-title">📂 Performance por Canal</div>',unsafe_allow_html=True)
    cc1,cc2,cc3,cc4=st.columns(4)
    def canal_card(col,mc,ma,nome,emoji):
        with col:
            if mc:
                def tr(cur,a,inv=False):
                    if not ma or a==0: return ""
                    pct=(cur-a)/abs(a)*100
                    if inv: c="#c0392b" if pct>0 else "#7a9e4e"; ar="▲" if pct>0 else "▼"
                    else: c="#7a9e4e" if pct>0 else "#c0392b"; ar="▲" if pct>0 else "▼"
                    return '<span style="color:{};font-size:10px;">{} {:.1f}%</span>'.format(c,ar,abs(pct))
                a=ma if ma else {}
                def _avg(val): return '<span style="color:#6a5a52;font-size:11px;font-weight:400;margin-left:6px;">{}/dia</span>'.format(val)
                st.markdown("""<div class="canal-card"><div class="canal-title">{e} {n}</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
<div><div class="canal-metric">Vendas</div><div class="canal-value">{v}{av}</div>{tv}</div>
<div><div class="canal-metric">Comissao</div><div class="canal-value">{c}{ac}</div>{tc}</div>
<div><div class="canal-metric">Cliques</div><div class="canal-value">{cl}{acl}</div>{tcl}</div>
<div><div class="canal-metric">CTR</div><div class="canal-value">{ctr}</div>{tctr}</div>
<div><div class="canal-metric">Ticket Medio</div><div class="canal-value">{tm}</div>{ttm}</div>
</div></div>""".format(
                    e=emoji,n=nome,
                    v=fmt_num(mc["vendas"]),av=_avg(fmt_num(int(mc["vendas"]/n_dias_sel))),tv=tr(mc["vendas"],a.get("vendas",0)),
                    c=fmt_brl(mc["comissao"]),ac=_avg(fmt_brl(mc["comissao"]/n_dias_sel)),tc=tr(mc["comissao"],a.get("comissao",0)),
                    cl=fmt_num(mc["cliques"]),acl=_avg(fmt_num(int(mc["cliques"]/n_dias_sel))),tcl=tr(mc["cliques"],a.get("cliques",0)),
                    ctr=fmt_pct(mc["ctr_shopee"]),tctr=tr(mc["ctr_shopee"],a.get("ctr_shopee",0)),
                    tm=fmt_brl(mc["ticket"]),ttm=tr(mc["ticket"],a.get("ticket",0))),unsafe_allow_html=True)
            else:
                st.markdown('<div class="canal-card"><div class="canal-title">{} {}</div><div style="color:#8892a4;">Sem dados</div></div>'.format(emoji,nome),unsafe_allow_html=True)
    canal_card(cc1,m_pago,m_ant_pago,"Pago","📣")
    canal_card(cc2,m_org,m_ant_org,"Organico","🌱")
    canal_card(cc3,m_story,m_ant_story,"Story","📖")
    canal_card(cc4,m_wpp,m_ant_wpp,"Whatsapp","💬")

    st.markdown('<div id="pago" class="section-title">📣 Campanha Pago</div>',unsafe_allow_html=True)
    if m_pago:
        lucro_camp=m_pago["comissao"]-invest_pago; roi_camp=(m_pago["comissao"]-invest_pago)/invest_pago if invest_pago>0 else 0
        cor_roi="green" if roi_camp>1 else ("yellow" if roi_camp>=0 else "red"); mp=m_ant_pago if m_ant_pago else {}
        n_dias_p=len(df_pago_periodo["Data"].unique()) or 1
        if not df_pago_raw.empty:
            _a_fim=pd.Timestamp(d_ini).date()-timedelta(days=1); _a_ini=_a_fim-timedelta(days=(d_fim-d_ini).days)
            _mp_ant=df_pago_raw[(df_pago_raw["Data"].dt.date>=_a_ini)&(df_pago_raw["Data"].dt.date<=_a_fim)]
            imp_p_ant=_mp_ant["Impressoes"].sum(); alc_p_ant=_mp_ant["Alcance"].sum(); clq_p_ant=_mp_ant["Cliques_Meta"].sum(); inv_p_ant=_mp_ant["Investimento"].sum()
        else: imp_p_ant=alc_p_ant=clq_p_ant=inv_p_ant=0
        vnd_med=m_pago["vendas"]/n_dias_p; com_med=m_pago["comissao"]/n_dias_p; inv_med=invest_pago/n_dias_p
        def ppair(col,top_label,top_val,top_delta,bot_label,bot_val,bot_delta,color,bot_is_cost=False):
            with col:
                card(top_label,top_val,color,top_delta,avg_label=bot_label,avg_value=bot_val+((" "+bot_delta) if bot_is_cost and bot_delta else ""))
        st.markdown('<div style="color:#c5936d;font-size:11px;font-weight:600;margin:8px 0 4px 0;">RESULTADOS</div>',unsafe_allow_html=True)
        k1,k2,k3,k4,k5=st.columns(5)
        n_dias_p_ant=max(len(df_ant_pago["Data"].unique()),1) if not df_ant_pago.empty else 1
        vnd_med_a=(mp.get("vendas",0)/n_dias_p_ant); com_med_a=(mp.get("comissao",0)/n_dias_p_ant); inv_med_a=invest_pago_ant/n_dias_p_ant
        ppair(k1,"Vendas",fmt_num(m_pago["vendas"]),delta_html(m_pago["vendas"],mp.get("vendas",0)),"Media/dia",fmt_num(int(vnd_med)),"","purple")
        ppair(k2,"Comissao",fmt_brl(m_pago["comissao"]),delta_html(m_pago["comissao"],mp.get("comissao",0)),"Media/dia",fmt_brl(com_med),"","blue")
        lucro_med=lucro_camp/n_dias_p; _pago_comissao_ant=df_ant[df_ant["Sub_id2"]=="pago"]["Comissao"].sum() if not df_ant.empty else 0
        lucro_camp_ant=(_pago_comissao_ant-invest_pago_ant) if invest_pago_ant>0 else None
        lucro_med_ant=(lucro_camp_ant/n_dias_p_ant) if lucro_camp_ant is not None else None
        ppair(k3,"Lucro",fmt_brl(lucro_camp),delta_html(lucro_camp,lucro_camp_ant),"Lucro/dia",fmt_brl(lucro_med),"",cor_roi)
        ppair(k4,"Investimento",fmt_brl(invest_pago),delta_html(invest_pago,invest_pago_ant),"Invest./dia",fmt_brl(inv_med),"","red")
        roi_v=m_pago["roi"]; roi_cor="roi-red" if roi_v<0 else ("roi-yellow" if roi_v<1 else "roi-green")
        roi_camp_ant=(_pago_comissao_ant-invest_pago_ant)/invest_pago_ant if invest_pago_ant>0 else None
        cac_ant=(invest_pago_ant/mp.get("vendas",1)) if mp.get("vendas",0)>0 else 0
        ppair(k5,"ROI","{:.2f}".format(roi_v),delta_html(roi_v,roi_camp_ant),"CAC",fmt_brl(m_pago.get("cac",0)),delta_html(m_pago.get("cac",0),cac_ant,inverted=True),roi_cor,bot_is_cost=True)
        with k5: st.markdown('<div style="font-size:12px;color:#c5936d;margin-top:-4px;"><span style="color:#7a9e4e;">■</span> &gt;1 bom &nbsp;<span style="color:#d4a017;">■</span> 0-1 atencao &nbsp;<span style="color:#c0392b;">■</span> &lt;0 prejuizo</div>',unsafe_allow_html=True)
        st.markdown('<div style="color:#c5936d;font-size:11px;font-weight:600;margin:12px 0 4px 0;">CAMPANHA</div>',unsafe_allow_html=True)
        k6,k7,k8,k9=st.columns(4)
        cpm_ant=(inv_p_ant/imp_p_ant*1000) if imp_p_ant>0 else 0; cpm_alc_ant=(inv_p_ant/alc_p_ant*1000) if alc_p_ant>0 else 0
        cpc_ant=inv_p_ant/clq_p_ant if clq_p_ant>0 else 0; ctr_meta_ant=(clq_p_ant/alc_p_ant*100) if alc_p_ant>0 else 0; freq_ant_p=(imp_p_ant/alc_p_ant) if alc_p_ant>0 else 0
        ppair(k6,"Impressoes",fmt_num(int(m_pago.get("impressoes",0))),delta_html(m_pago.get("impressoes",0),imp_p_ant),"CPM",fmt_brl(m_pago.get("cpm_imp",0)),delta_html(m_pago.get("cpm_imp",0),cpm_ant,inverted=True),"yellow",bot_is_cost=True)
        ppair(k7,"Alcance",fmt_num(int(m_pago.get("alcance",0))),delta_html(m_pago.get("alcance",0),alc_p_ant),"CPM Alcance",fmt_brl(m_pago.get("cpm_alc",0)),delta_html(m_pago.get("cpm_alc",0),cpm_alc_ant,inverted=True),"yellow",bot_is_cost=True)
        ppair(k8,"Cliques Meta",fmt_num(int(m_pago.get("cliques_meta",0))),delta_html(m_pago.get("cliques_meta",0),clq_p_ant),"CPC",fmt_brl(m_pago.get("cpc",0)),delta_html(m_pago.get("cpc",0),cpc_ant,inverted=True),"orange",bot_is_cost=True)
        ppair(k9,"CTR Meta",fmt_pct(m_pago.get("ctr_meta",0)),delta_html(m_pago.get("ctr_meta",0),ctr_meta_ant),"Frequencia","{:.2f}x".format(m_pago.get("freq",0)),delta_html(m_pago.get("freq",0),freq_ant_p),"blue",bot_is_cost=True)
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

        # ── PERFORMANCE POR CRIATIVO (Sub_id1 × Sub_id3) ──────────────
        st.markdown('<div style="color:#c5936d;font-size:12px;font-weight:600;margin:20px 0 8px 0;">🎯 PERFORMANCE POR CRIATIVO — ROI E FUNIL DE CONVERSÃO</div>', unsafe_allow_html=True)

        # Thresholds
        MIN_DIAS  = 3
        MIN_CLIQUES_PAUSAR = 100

        df_cri_clicks = df_pago_v.groupby(["Sub_id1","Sub_id3"]).agg(
            Cliques_Shopee=("Cliques","sum"),
            Vendas=("Vendas","sum"),
            Comissao=("Comissao","sum"),
        ).reset_index()

        dias_por_sid1 = df_pago_periodo.groupby("Sub_id1")["Data"].nunique().reset_index(name="N_dias")

        # Campanhas activas: tiveram investimento nos últimos 3 dias da planilha Pago (global)
        _ultimo_dia_pago = df_pago_raw["Data"].max().date() if not df_pago_raw.empty else None
        if _ultimo_dia_pago:
            _janela_activa = _ultimo_dia_pago - timedelta(days=2)  # últimos 3 dias
            _sid1_activos = set(
                df_pago_raw[
                    (df_pago_raw["Data"].dt.date >= _janela_activa) &
                    (df_pago_raw["Data"].dt.date <= _ultimo_dia_pago) &
                    (df_pago_raw["Investimento"] > 0)
                ]["Sub_id1"].unique()
            )
        else:
            _sid1_activos = set()

        inv_por_sid1 = df_pago_periodo.groupby("Sub_id1").agg(
            Investimento=("Investimento","sum"),
            Cliques_Meta=("Cliques_Meta","sum"),
        ).reset_index()

        df_cri = df_cri_clicks.merge(inv_por_sid1, on="Sub_id1", how="left")
        df_cri = df_cri.merge(dias_por_sid1, on="Sub_id1", how="left")
        df_cri["Investimento"] = df_cri["Investimento"].fillna(0)
        df_cri["Cliques_Meta"] = df_cri["Cliques_Meta"].fillna(0)
        df_cri["N_dias"]       = df_cri["N_dias"].fillna(0).astype(int)
        df_cri["Activa"]       = df_cri["Sub_id1"].isin(_sid1_activos)

        # Distribuir investimento proporcional e proteger contra índices desalinhados
        tot_clq = df_cri.groupby("Sub_id1")["Cliques_Shopee"].transform("sum")
        df_cri["Invest_card"] = (df_cri["Investimento"] * df_cri["Cliques_Shopee"].div(tot_clq.replace(0, np.nan))).fillna(0)

        # Excluir linhas sem investimento
        df_cri_sem_inv = pd.DataFrame()  # sempre definido para evitar NameError
        df_cri = df_cri[df_cri["Invest_card"] > 0].copy().reset_index(drop=True)

        if df_cri.empty:
            st.markdown(
                '<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:8px;'
                'padding:14px 16px;color:#c5936d;font-size:13px;">'
                'Sem criativos com investimento no período seleccionado.</div>',
                unsafe_allow_html=True
            )
        else:
            # Recalcular proporções com índices limpos
            tot_clq2 = df_cri.groupby("Sub_id1")["Cliques_Shopee"].transform("sum")
            df_cri["Cliques_Meta_card"] = (df_cri["Cliques_Meta"] * df_cri["Cliques_Shopee"].div(tot_clq2.replace(0, np.nan))).fillna(0)

            df_cri["ROI"]     = (df_cri["Comissao"] - df_cri["Invest_card"]) / df_cri["Invest_card"]
            df_cri["Receita"] = df_cri["Comissao"] - df_cri["Invest_card"]
            df_cri["CAC"]     = df_cri["Invest_card"].div(df_cri["Vendas"].replace(0, np.nan)).fillna(0)
            df_cri["RPC"]     = df_cri["Comissao"].div(df_cri["Cliques_Meta_card"].replace(0, np.nan)).fillna(0)
            df_cri["CPC"]     = df_cri["Invest_card"].div(df_cri["Cliques_Meta_card"].replace(0, np.nan)).fillna(0)
            df_cri["CTR"]     = (df_cri["Vendas"].div(df_cri["Cliques_Shopee"].replace(0, np.nan))).fillna(0) * 100

            def badge_decisao_cri(row):
                roi     = row["ROI"]
                cliques = row["Cliques_Shopee"]
                n_dias  = row["N_dias"]
                activa  = row.get("Activa", True)
                if not activa:
                    return ("\u26ab Desligada", "#6a5a52", "#1a1410")
                if n_dias < MIN_DIAS or pd.isna(roi):
                    return ("\u26aa Aguardar", "#8892a4", "#1e1e2e")
                if roi > 1:
                    return ("\U0001f7e2 Escalar", "#7a9e4e", "#0f1f0f")
                if roi >= 0:
                    return ("\U0001f7e1 Monitorar", "#d4a017", "#1f1a0a")
                if cliques >= MIN_CLIQUES_PAUSAR:
                    return ("\U0001f534 Pausar", "#c0392b", "#1f0808")
                return ("\u26aa Aguardar", "#8892a4", "#1e1e2e")

            df_cri["_badge"]    = df_cri.apply(badge_decisao_cri, axis=1)
            df_cri["_roi_sort"] = df_cri["ROI"].fillna(-999)
            df_cri = df_cri.sort_values(["Sub_id1","_roi_sort"], ascending=[True, False]).reset_index(drop=True)

            GRID = "1.4fr 1.3fr 0.8fr 0.9fr 0.7fr 0.85fr 0.85fr 0.75fr 0.8fr 0.8fr 0.65fr 0.85fr 1.15fr"

            header_html = (
                '<div style="display:grid;grid-template-columns:{g};gap:4px;'
                'padding:7px 12px;background:#221a16;border-radius:6px 6px 0 0;'
                'color:#c5936d;font-size:10px;font-weight:600;margin-top:8px;">'.format(g=GRID) +
                '<div>Campanha</div>'
                '<div>Card (Sub_id3)</div>'
                '<div style="text-align:right">Invest.*</div>'
                '<div style="text-align:right">Cliq. Meta</div>'
                '<div style="text-align:right">Vendas</div>'
                '<div style="text-align:right">Comiss\u00e3o</div>'
                '<div style="text-align:right">Receita</div>'
                '<div style="text-align:right">ROI</div>'
                '<div style="text-align:right">CAC</div>'
                '<div style="text-align:right">CPC</div>'
                '<div style="text-align:right">CTR</div>'
                '<div style="text-align:right">RPC\u25b2</div>'
                '<div style="text-align:center">Status</div>'
                '</div>'
            )

            rows_html = ""
            for _, row in df_cri.iterrows():
                badge_txt, badge_cor, badge_bg = row["_badge"]
                roi_raw  = row.get("ROI", np.nan)
                roi_val  = None if pd.isna(roi_raw) else roi_raw
                roi_str  = "{:.2f}\u00d7".format(roi_val) if roi_val is not None else "\u2014"
                roi_cor  = ("#7a9e4e" if roi_val is not None and roi_val > 1
                            else ("#d4a017" if roi_val is not None and roi_val >= 0
                            else ("#c0392b" if roi_val is not None else "#8892a4")))
                rec_raw  = row.get("Receita", np.nan)
                rec_str  = "R${:.0f}".format(rec_raw) if pd.notna(rec_raw) else "\u2014"
                rec_cor  = "#7a9e4e" if pd.notna(rec_raw) and rec_raw >= 0 else ("#c0392b" if pd.notna(rec_raw) else "#8892a4")
                cac_raw  = row.get("CAC", np.nan)
                cac_str  = "R${:.2f}".format(cac_raw) if pd.notna(cac_raw) and cac_raw > 0 else "\u2014"
                cpc_val  = row.get("CPC", np.nan)
                cpc_str  = "R${:.2f}".format(cpc_val) if pd.notna(cpc_val) and cpc_val > 0 else "\u2014"
                ctr_raw  = row.get("CTR", np.nan)
                ctr_str  = "{:.1f}%".format(ctr_raw) if pd.notna(ctr_raw) and ctr_raw > 0 else "\u2014"
                rpc_val  = row.get("RPC", np.nan)
                rpc_str  = "R${:.3f}".format(rpc_val) if pd.notna(rpc_val) and rpc_val > 0 else "\u2014"
                rpc_cor  = ("#7a9e4e" if (pd.notna(rpc_val) and pd.notna(cpc_val) and rpc_val > 0 and cpc_val > 0 and rpc_val > cpc_val)
                            else ("#c0392b" if (pd.notna(rpc_val) and pd.notna(cpc_val) and rpc_val > 0 and cpc_val > 0) else "#8892a4"))
                clq_str  = "{:,}".format(int(row["Cliques_Meta_card"])).replace(",",".")
                sid1     = row["Sub_id1"] or "\u2014"
                sid3     = row["Sub_id3"] or "\u2014"
                rows_html += (
                    '<div style="display:grid;grid-template-columns:{g};gap:4px;'
                    'padding:8px 12px;border-bottom:1px solid #2a1f1a;background:#1a1410;'
                    'color:#f6e8d8;font-size:11px;align-items:center;">'.format(g=GRID) +
                    '<div style="font-weight:600;color:#c5936d;">{}</div>'.format(sid1) +
                    '<div>{}</div>'.format(sid3) +
                    '<div style="text-align:right;color:#c5936d;">R${:.0f}</div>'.format(row["Invest_card"]) +
                    '<div style="text-align:right;">{}</div>'.format(clq_str) +
                    '<div style="text-align:right;">{}</div>'.format(int(row["Vendas"])) +
                    '<div style="text-align:right;">R${:.0f}</div>'.format(row["Comissao"]) +
                    '<div style="text-align:right;color:{c};font-weight:600;">{v}</div>'.format(c=rec_cor, v=rec_str) +
                    '<div style="text-align:right;color:{c};font-weight:700;">{v}</div>'.format(c=roi_cor, v=roi_str) +
                    '<div style="text-align:right;color:#c5936d;">{}</div>'.format(cac_str) +
                    '<div style="text-align:right;color:#c5936d;">{}</div>'.format(cpc_str) +
                    '<div style="text-align:right;color:#c5936d;">{}</div>'.format(ctr_str) +
                    '<div style="text-align:right;color:{c};font-weight:600;">{v}</div>'.format(c=rpc_cor, v=rpc_str) +
                    '<div style="text-align:center;">'
                    '<span style="background:{bg};color:{cor};border:1px solid {cor};'
                    'border-radius:12px;padding:2px 8px;font-size:10px;font-weight:600;white-space:nowrap;">'
                    '{txt}</span></div>'.format(bg=badge_bg, cor=badge_cor, txt=badge_txt) +
                    '</div>'
                )

            legenda_html = (
                '<div style="padding:8px 12px;background:#161210;border-radius:0 0 6px 6px;'
                'border-top:1px solid #2a1f1a;display:flex;gap:12px;flex-wrap:wrap;align-items:center;">'
                '<span style="color:#7a9e4e;font-size:10px;">\U0001f7e2 Escalar \u2192 ROI &gt; 1</span>'
                '<span style="color:#d4a017;font-size:10px;">\U0001f7e1 Monitorar \u2192 ROI 0\u20131</span>'
                '<span style="color:#c0392b;font-size:10px;">\U0001f534 Pausar \u2192 ROI &lt; 0 e cliques \u2265 100</span>'
                '<span style="color:#8892a4;font-size:10px;">\u26aa Aguardar \u2192 &lt; 3 dias</span>'
                '<span style="color:#6a5a52;font-size:10px;">\u26ab Desligada \u2192 sem invest. nos \u00faltimos 3 dias da planilha</span>'
                '<span style="color:#c5936d;font-size:10px;margin-left:auto;">'
                '* Invest. prop. por cliques &nbsp;|\u00a0 Receita = Comiss\u00e3o \u2212 Invest. &nbsp;|\u00a0'
                ' RPC\u25b2 = Comiss\u00e3o/Cliques &nbsp;'
                '<span style="color:#7a9e4e;">\u25cf</span> verde se RPC &gt; CPC &nbsp;'
                '<span style="color:#c0392b;">\u25cf</span> vermelho se RPC \u2264 CPC'
                '</span></div>'
            )

            st.markdown(
                '<div style="background:#0f0d0b;border:1px solid #3a2c28;border-radius:8px;overflow:hidden;">'
                + header_html + rows_html + legenda_html + '</div>',
                unsafe_allow_html=True
            )

    else:
        msg_pago = ('Sem dados de campanha paga para os filtros seleccionados.' if filtros_activos
                   else 'Sem dados de campanha paga para o período seleccionado.')
        st.markdown(f'<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:8px;padding:16px;text-align:center;color:#c5936d;">{msg_pago}</div>', unsafe_allow_html=True)

    st.markdown('<div id="awareness" class="section-title">📡 Campanha Awareness</div>',unsafe_allow_html=True)
    if not df_aw.empty:
        inv_aw_s=df_aw["Investimento_aw"].sum(); imp_aw=df_aw["Impressoes_aw"].sum(); alc_aw=df_aw["Alcance_aw"].sum()
        vis_aw=df_aw["Visitas_Perfil"].sum(); seg_aw=df_aw["Seguidores"].sum(); com_aw=df_aw["Comentarios"].sum() if "Comentarios" in df_aw.columns else 0
        cpm_aw=(inv_aw_s/imp_aw*1000) if imp_aw>0 else 0; cpa_aw=(inv_aw_s/vis_aw) if vis_aw>0 else 0; cps_aw=(inv_aw_s/seg_aw) if seg_aw>0 else 0; cpc_aw=(inv_aw_s/com_aw) if com_aw>0 else 0; freq_aw=imp_aw/alc_aw if alc_aw>0 else 0
        df_aw_ant=semana_anterior(df_aw_raw,d_ini,d_fim) if not df_aw_raw.empty else pd.DataFrame()
        inv_a=df_aw_ant["Investimento_aw"].sum() if not df_aw_ant.empty else 0; imp_a=df_aw_ant["Impressoes_aw"].sum() if not df_aw_ant.empty else 0
        vis_a=df_aw_ant["Visitas_Perfil"].sum() if not df_aw_ant.empty else 0; seg_a=df_aw_ant["Seguidores"].sum() if not df_aw_ant.empty else 0; com_a=df_aw_ant["Comentarios"].sum() if not df_aw_ant.empty else 0
        cpm_a=(inv_a/imp_a*1000) if imp_a>0 else 0; cpa_a=(inv_a/vis_a) if vis_a>0 else 0; cps_a=(inv_a/seg_a) if seg_a>0 else 0; cpc_a=(inv_a/com_a) if com_a>0 else 0
        alc_a=df_aw_ant["Alcance_aw"].sum() if not df_aw_ant.empty else 0; freq_a=(imp_a/alc_a) if alc_a>0 else 0
        n_dias_aw=len(df_aw["Data"].unique()) or 1; inv_aw_med=inv_aw_s/n_dias_aw; inv_aw_med_a=(inv_a/len(df_aw_ant["Data"].unique())) if not df_aw_ant.empty and len(df_aw_ant["Data"].unique())>0 else 0
        def pair(col,top_label,top_val,top_delta,bot_label,bot_val,bot_delta,color,bot_is_cost=False):
            with col:
                card(top_label,top_val,color,top_delta,avg_label=bot_label,avg_value=bot_val+((" "+bot_delta) if bot_is_cost and bot_delta else ""))
        aw1,aw2,aw3=st.columns(3)
        pair(aw1,"Investimento",fmt_brl(inv_aw_s),delta_html(inv_aw_s,inv_a),"Invest./dia",fmt_brl(inv_aw_med),"","red")
        pair(aw2,"Impressoes",fmt_num(int(imp_aw)),delta_html(imp_aw,imp_a),"CPM",fmt_brl(cpm_aw),delta_html(cpm_aw,cpm_a,inverted=True),"yellow",bot_is_cost=True)
        pair(aw3,"Alcance",fmt_num(int(alc_aw)),delta_html(alc_aw,alc_a),"Frequencia","{:.2f}x".format(freq_aw),delta_html(freq_aw,freq_a),"orange",bot_is_cost=True)
        aw4,aw5,aw6=st.columns(3)
        pair(aw4,"Visitas ao Perfil",fmt_num(int(vis_aw)),delta_html(vis_aw,vis_a),"Custo/Visita",fmt_brl(cpa_aw),delta_html(cpa_aw,cpa_a,inverted=True),"purple",bot_is_cost=True)
        pair(aw5,"Seguidores",fmt_num(int(seg_aw)),delta_html(seg_aw,seg_a),"Custo/Seguidor",fmt_brl(cps_aw),delta_html(cps_aw,cps_a,inverted=True),"green",bot_is_cost=True)
        pair(aw6,"Comentarios",fmt_num(int(com_aw)),delta_html(com_aw,com_a),"Custo/Comentario",fmt_brl(cpc_aw),delta_html(cpc_aw,cpc_a,inverted=True),"blue",bot_is_cost=True)
        df_aw_d=df_aw.groupby("Data").agg(Invest=("Investimento_aw","sum"),Impressoes=("Impressoes_aw","sum"),Visitas=("Visitas_Perfil","sum"),Seguidores=("Seguidores","sum"),Comentarios=("Comentarios","sum")).reset_index()
        df_aw_d["CPM"]=(df_aw_d["Invest"]/df_aw_d["Impressoes"]*1000).replace([np.inf,np.nan],0)
        df_aw_d["CPA"]=(df_aw_d["Invest"]/df_aw_d["Visitas"]).replace([np.inf,np.nan],0)
        df_aw_d["CPS"]=(df_aw_d["Invest"]/df_aw_d["Seguidores"]).replace([np.inf,np.nan],0)
        df_aw_d["CPC_aw"]=(df_aw_d["Invest"]/df_aw_d["Comentarios"]).replace([np.inf,np.nan],0)
        met_aw={"Investimento":"Invest","Impressoes":"Impressoes","Visitas ao Perfil":"Visitas","Seguidores":"Seguidores","Comentarios":"Comentarios","CPM":"CPM","Custo/Visita":"CPA","Custo/Seguidor":"CPS","Custo/Comentario":"CPC_aw"}
        da={k:v for k,v in met_aw.items() if v in df_aw_d.columns}
        awc1,awc2=st.columns(2)
        with awc1: am1=st.selectbox("Barra",list(da.keys()),index=0,key="am1")
        with awc2: am2=st.selectbox("Linha",list(da.keys()),index=3,key="am2")
        df_awf=df_aw_d[(df_aw_d[da[am1]]>0)|(df_aw_d[da[am2]]>0)]
        st.plotly_chart(dual_chart(df_awf,"Data",da[am1],da[am2],"{} vs {}".format(am1,am2),am1,am2),use_container_width=True)
        df_os=df[df["Sub_id2"].isin(["organico","story"])].copy(); df_os["Lucro_os"]=df_os["Comissao"]
        df_os_d=df_os.groupby("Data").agg(Vendas=("Vendas","sum"),Lucro_os=("Lucro_os","sum")).reset_index()
        df_aw_s2=df_aw_d[["Data","Invest"]].copy(); df_aw_s2["Data"]=df_aw_s2["Data"]+pd.Timedelta(days=3)
        df_imp=df_os_d.merge(df_aw_s2.rename(columns={"Invest":"Invest_lag"}),on="Data",how="left").fillna(0)
        if len(df_imp)>3 and df_imp["Invest_lag"].sum()>0:
            corr_v=df_imp["Invest_lag"].corr(df_imp["Vendas"]); corr_l=df_imp["Invest_lag"].corr(df_imp["Lucro_os"])
            aw_t=dict(plot_bgcolor="#0f0d0b",paper_bgcolor="#0f0d0b",font_color="#f6e8d8",legend=dict(font=dict(color="#f6e8d8",size=11),bgcolor="rgba(30,18,16,0.8)"))
            def corr_badge(c):
                cor="#7a9e4e" if c>0.3 else ("#c0392b" if c<-0.1 else "#c5936d"); txt="positiva" if c>0.3 else ("sem correlacao" if c>=-0.1 else "negativa"); return cor,txt
            cv_cor,cv_txt=corr_badge(corr_v); cl_cor,cl_txt=corr_badge(corr_l)
            st.markdown('<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:8px 0;"><div style="background:#1a1210;border:1px solid #3a2c28;border-radius:8px;padding:10px 14px;"><span style="color:#c5936d;font-size:11px;">Awareness -> Vendas Org/Story (lag 3d): </span><span style="color:{};font-size:14px;font-weight:700;">{:.2f}</span> <span style="color:#c5936d;font-size:10px;">— {}</span></div><div style="background:#1a1210;border:1px solid #3a2c28;border-radius:8px;padding:10px 14px;"><span style="color:#c5936d;font-size:11px;">Awareness -> Lucro Org/Story (lag 3d): </span><span style="color:{};font-size:14px;font-weight:700;">{:.2f}</span> <span style="color:#c5936d;font-size:10px;">— {}</span></div></div>'.format(cv_cor,corr_v,cv_txt,cl_cor,corr_l,cl_txt),unsafe_allow_html=True)
    else:
        if aw_omitido:
            st.markdown('<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:8px;padding:14px 16px;color:#c5936d;font-size:13px;">'
                '⚠️ Dados de Awareness omitidos — a campanha de Awareness não está associada a Sub_id1 ou Sub_id3 específicos, '
                'por isso não é possível filtrá-la por campanha. Remova os filtros de Sub_id1/Sub_id3 para ver o Awareness.'
                '</div>', unsafe_allow_html=True)
        else:
            n=len(df_aw_raw) if not df_aw_raw.empty else 0
            st.markdown('<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:8px;padding:16px;text-align:center;color:#c5936d;">{}</div>'.format("Sem dados na aba Resultado Awareness." if n==0 else "Sem dados de Awareness para este periodo ({} linhas totais).".format(n)),unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div id="cruzamento" class="section-title">🔀 Cruzamento de Metricas</div>',unsafe_allow_html=True)
    df_cross=df_daily.copy()
    if not df_aw.empty:
        df_aw_cx=df_aw.groupby("Data").agg(Visitas=("Visitas_Perfil","sum"),Seguidores=("Seguidores","sum"),Comentarios=("Comentarios","sum")).reset_index()
        df_cross=df_cross.merge(df_aw_cx,on="Data",how="left").fillna(0)
    else:
        for c in ["Visitas","Seguidores","Comentarios"]: df_cross[c]=0.0
    met_disp={"Invest. Total (Pago+Awareness)":"Investimento","Invest. Pago":"Invest_pago","Invest. Awareness":"Invest_aw","Vendas":"Vendas","Comissao":"Comissao","Cliques":"Cliques","Ticket Medio":"Ticket_Medio","Visitas Perfil":"Visitas","Seguidores":"Seguidores","Comentarios":"Comentarios"}
    disp={k:v for k,v in met_disp.items() if v in df_cross.columns}
    cx1,cx2=st.columns(2)
    with cx1: met1=st.selectbox("Metrica 1 (barras)",list(disp.keys()),index=0,key="cx1")
    with cx2: met2=st.selectbox("Metrica 2 (linha)",list(disp.keys()),index=3,key="cx2")
    col_x,col_y=disp[met1],disp[met2]
    if col_x in df_cross.columns and col_y in df_cross.columns:
        df_cf=df_cross[(df_cross[col_x]>0)|(df_cross[col_y]>0)]
        st.plotly_chart(dual_chart(df_cf,"Data",col_x,col_y,"{} vs {}".format(met1,met2),met1,met2),use_container_width=True)

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

    st.markdown('<div id="campeoes" class="section-title">🏆 Itens Campeoes</div>',unsafe_allow_html=True)
    ic_c1,ic_c2=st.columns([3,1])
    with ic_c1: st.markdown('<span style="color:#c5936d;font-size:12px;">Agrupamento para ranking de itens</span>',unsafe_allow_html=True)
    with ic_c2: ic_modo=st.radio("Agrupar por",["Sub_id3 (Criativo)","Sub_id1 (Grupo)"],key="ic_modo",horizontal=True,label_visibility="collapsed")
    ic_col="Sub_id1" if "Sub_id1" in ic_modo else "Sub_id3"
    df_ic_base=df[(df[ic_col]!="")&(df["Sub_id2"]!="story")].groupby(ic_col).agg(Comissao=("Comissao","sum"),Vendas=("Vendas","sum"),Cliques=("Cliques","sum")).reset_index()
    df_ic_base["Ticket"]=(df_ic_base["Comissao"]/df_ic_base["Vendas"]).fillna(0)
    col1,col2=st.columns(2)
    with col1:
        t5=df_ic_base.nlargest(5,"Comissao").sort_values("Comissao",ascending=True)
        t5["lbl"]=t5.apply(lambda r:"R$ {:,.2f} | {:,.0f} vendas".format(r["Comissao"],r["Vendas"]),axis=1)
        fig=px.bar(t5,x="Comissao",y=ic_col,orientation="h",title="Top 5 por Comissao",text="lbl",color_discrete_sequence=["#9c5834"])
        fig.update_traces(textposition="outside"); fig.update_layout(**PLOTLY_THEME); st.plotly_chart(fig,use_container_width=True)
    with col2:
        t5v=df_ic_base.nlargest(5,"Vendas").sort_values("Vendas",ascending=True)
        fig=px.bar(t5v,x="Vendas",y=ic_col,orientation="h",title="Top 5 por Vendas",text="Vendas",color_discrete_sequence=["#c5936d"])
        fig.update_traces(texttemplate="%{text:.0f}",textposition="outside"); fig.update_layout(**PLOTLY_THEME); st.plotly_chart(fig,use_container_width=True)
    col3,col4=st.columns(2)
    with col3:
        t5c=df_ic_base.nlargest(5,"Cliques").sort_values("Cliques",ascending=True)
        fig=px.bar(t5c,x="Cliques",y=ic_col,orientation="h",title="Top 5 por Cliques",text="Cliques",color_discrete_sequence=["#d2b095"])
        fig.update_traces(texttemplate="%{text:.0f}",textposition="outside"); fig.update_layout(**PLOTLY_THEME); st.plotly_chart(fig,use_container_width=True)
    with col4:
        # Ticket Medio: mais robusto que CTR (imune a volume baixo de cliques)
        t5tkt=df_ic_base[df_ic_base["Vendas"]>=2].nlargest(5,"Ticket").sort_values("Ticket",ascending=True)
        fig=px.bar(t5tkt,x="Ticket",y=ic_col,orientation="h",title="Top 5 por Ticket Medio",text="Ticket",color_discrete_sequence=["#bd6d34"])
        fig.update_traces(texttemplate="R$ %{text:.2f}",textposition="outside"); fig.update_layout(**PLOTLY_THEME); st.plotly_chart(fig,use_container_width=True)

    st.markdown('<div id="ipa" class="section-title">🎯 IPA — Indice de Potencial de Anuncio</div>',unsafe_allow_html=True)
    st.markdown('<div style="background:#1a1210;border:1px solid #3a2c28;border-radius:8px;padding:12px 16px;margin-bottom:12px;color:#c5936d;font-size:12px;">O <b style="color:#f6e8d8;">IPA</b> é uma fórmula exclusiva MATIQ que identifica criativos com maior potencial para anúncio. Utilize janelas temporais superiores a <b style="color:#f6e8d8;">7 dias</b> para resultados mais consistentes — períodos curtos podem resultar em <b style="color:#c0392b;">N/A</b>.</div>',unsafe_allow_html=True)
    ipa_c1,ipa_c2=st.columns([3,1])
    with ipa_c1: st.markdown('<span style="color:#c5936d;font-size:12px;">Agrupamento para o IPA</span>',unsafe_allow_html=True)
    with ipa_c2: ipa_modo=st.radio("IPA por",["Sub_id3 (Criativo)","Sub_id1 (Grupo)"],key="ipa_modo",horizontal=True,label_visibility="collapsed")
    ipa_col="Sub_id1" if "Sub_id1" in ipa_modo else "Sub_id3"
    ipa_other="Sub_id3" if ipa_col=="Sub_id1" else "Sub_id1"
    # Pedidos reais via Insights_Categoria cruzado com Insights_Horario (que tem a data)
    dc_raw=ler_categoria()
    dh_raw=ler_horario()
    if not dc_raw.empty and not dh_raw.empty and "Hora_Pedido" in dh_raw.columns:
        # IDs de pedidos no período seleccionado (via Insights_Horario que tem data)
        dh_raw["_data"]=pd.to_datetime(dh_raw["Hora_Pedido"],errors="coerce").dt.date
        ids_periodo=set(dh_raw[(dh_raw["_data"]>=d_ini)&(dh_raw["_data"]<=d_fim)]["ID_Pedido"].dropna().unique())
        dc_ipa=dc_raw[
            (dc_raw["Sub_id2"]=="organico") &
            (dc_raw["Sub_id1"]!="") & (dc_raw["Sub_id3"]!="") &
            (dc_raw["ID_Pedido"].isin(ids_periodo))
        ].copy()
        df_pedidos=dc_ipa.groupby([ipa_col,ipa_other]).agg(
            Pedidos=("ID_Pedido","nunique"),
        ).reset_index()
    else:
        df_pedidos=pd.DataFrame(columns=[ipa_col,ipa_other,"Pedidos"])
    df_org=df[df["Sub_id2"]=="organico"].copy()
    df_ipa_ped=df_org.groupby([ipa_col,ipa_other]).agg(
        Comissao=("Comissao","sum"),
        Vendas=("Vendas","sum"),
        Cliques=("Cliques","sum"),
    ).reset_index()
    # Pedidos reais: nunique de ID_Pedido via Insights_Categoria
    if not df_pedidos.empty:
        df_ipa_ped=df_ipa_ped.merge(df_pedidos[[ipa_col,ipa_other,"Pedidos"]],on=[ipa_col,ipa_other],how="left")
        df_ipa_ped["Pedidos"]=df_ipa_ped["Pedidos"].fillna(0).astype(int)
    else:
        df_ipa_ped["Pedidos"]=0
    df_ipa_ped["CTR"]=(df_ipa_ped["Vendas"]/df_ipa_ped["Cliques"]*100).fillna(0)
    df_ipa_ped["Ticket"]=(df_ipa_ped["Comissao"]/df_ipa_ped["Vendas"]).fillna(0)
    df_v=df_ipa_ped[df_ipa_ped["Vendas"]>=3].copy()
    if not df_v.empty:
        for col in ["Comissao","Vendas","Ticket","CTR"]:
            mn,mx=df_v[col].min(),df_v[col].max()
            df_v[col+"_n"]=((df_v[col]-mn)/(mx-mn)*100) if mx>mn else 50.0
        mn_c,mx_c=df_v["Cliques"].min(),df_v["Cliques"].max()
        df_v["Cliques_n"]=((df_v["Cliques"]-mn_c)/(mx_c-mn_c)*100) if mx_c>mn_c else 50.0
        # Diversidade de pedidos: ratio Pedidos/Vendas normalizado (1 pedido/venda = máxima diversidade)
        df_v["Div_pedidos"]=(df_v["Pedidos"]/df_v["Vendas"]).clip(0,1)
        mn_d,mx_d=df_v["Div_pedidos"].min(),df_v["Div_pedidos"].max()
        df_v["Div_n"]=((df_v["Div_pedidos"]-mn_d)/(mx_d-mn_d)*100) if mx_d>mn_d else 50.0
        # IPA: Comissao 30% | Vendas 20% | Ticket 18% | CTR 10% | Cliques 7% | Diversidade Pedidos 15%
        df_v["IPA"]=(df_v["Comissao_n"]*0.30+df_v["Vendas_n"]*0.20+df_v["Ticket_n"]*0.18+df_v["CTR_n"]*0.10+df_v["Cliques_n"]*0.07+df_v["Div_n"]*0.15).round(1)
    ja_pago=set(df[df["Sub_id2"]=="pago"][ipa_col].unique())
    merge_cols=[ipa_col,ipa_other,"IPA","Pedidos"] if not df_v.empty else [ipa_col,ipa_other]
    df_ipa=df_ipa_ped.merge(df_v[merge_cols] if not df_v.empty else pd.DataFrame(columns=[ipa_col,ipa_other,"IPA","Pedidos"]),on=[ipa_col,ipa_other],how="left",suffixes=("","_calc"))
    if "Pedidos_calc" in df_ipa.columns: df_ipa["Pedidos"]=df_ipa["Pedidos_calc"].fillna(df_ipa["Pedidos"]); df_ipa.drop(columns=["Pedidos_calc"],inplace=True)
    df_ipa=df_ipa[~df_ipa[ipa_col].isin(ja_pago)]
    df_ipa["IPA_d"]=df_ipa["IPA"].apply(lambda x:"{:.1f}".format(x) if pd.notna(x) else "N/A")
    df_ipa["IPA_s"]=df_ipa["IPA"].fillna(-1)
    df_ipa=df_ipa.sort_values("IPA_s",ascending=False).reset_index(drop=True)
    df_ic=df_ipa[df_ipa["IPA_s"]>=0].head(15).sort_values("IPA_s",ascending=True)
    if not df_ic.empty:
        hover_extra={ipa_other:True,"Vendas":True,"Pedidos":True,"Comissao":":.2f","CTR":":.2f","Ticket":":.2f","IPA_s":False}
        fig=px.bar(df_ic,x="IPA_s",y=ipa_col,orientation="h",title="Top por IPA",text="IPA_d",color="IPA_s",color_continuous_scale=["#562d1d","#9c5834","#bd6d34","#f6e8d8"],hover_data=hover_extra,labels={"IPA_s":"IPA",ipa_col:ipa_col})
        fig.update_traces(textposition="outside"); fig.update_layout(**PLOTLY_THEME,height=max(300,len(df_ic)*40),coloraxis_showscale=False); st.plotly_chart(fig,use_container_width=True)
    df_it=df_ipa[[ipa_col,ipa_other,"IPA_d","Vendas","Pedidos","Cliques","Comissao","CTR","Ticket"]].copy()
    df_it.columns=[ipa_col,ipa_other,"IPA","Vendas","Pedidos","Cliques","Comissao (R$)","CTR (%)","Ticket (R$)"]
    df_it["Comissao (R$)"]=df_it["Comissao (R$)"].apply(lambda x:"{:.2f}".format(x))
    df_it["CTR (%)"]=df_it["CTR (%)"].apply(lambda x:"{:.2f}%".format(x))
    df_it["Ticket (R$)"]=df_it["Ticket (R$)"].apply(lambda x:"{:.2f}".format(x))
    df_it["Cliques"]=df_it["Cliques"].apply(lambda x:"{:,.0f}".format(x).replace(",","."))
    df_it["Vendas"]=df_it["Vendas"].apply(lambda x:"{:,.0f}".format(x))
    df_it["Pedidos"]=df_it["Pedidos"].apply(lambda x:"{:,.0f}".format(x) if pd.notna(x) else "—")
    styled=df_it.style.set_properties(subset=[ipa_col,ipa_other],**{"text-align":"left"}).set_properties(subset=["IPA","Vendas","Pedidos","Cliques","Comissao (R$)","CTR (%)","Ticket (R$)"],**{"text-align":"center"}).set_table_styles([{"selector":"th","props":[("text-align","center")]}])
    st.dataframe(styled,use_container_width=True,height=300)

    st.markdown('<div class="section-title">📋 Dados Detalhados</div>',unsafe_allow_html=True)
    df_t=df[["Data","Sub_id2","Sub_id1","Sub_id3","Cliques","Vendas","Comissao"]].copy()
    df_t["CTR"]=df_t.apply(lambda r:(r["Vendas"]/r["Cliques"]*100) if r["Cliques"]>0 else 0.0,axis=1)
    df_t["Ticket"]=df_t.apply(lambda r:(r["Comissao"]/r["Vendas"]) if r["Vendas"]>0 else 0.0,axis=1)
    df_t["Data"]=df_t["Data"].dt.strftime("%Y-%m-%d")
    df_t=df_t.sort_values("Comissao",ascending=False).reset_index(drop=True)
    busca=st.text_input("🔍 Pesquisar",placeholder="Ex: pago, 260302fronha...",key="busca")
    if busca: df_t=df_t[df_t.apply(lambda r:busca.lower() in str(r).lower(),axis=1)]
    # Formatar colunas sem decimais desnecessários
    df_disp=df_t.copy()
    df_disp["Cliques"]=df_disp["Cliques"].apply(lambda x:int(x) if x==int(x) else x)
    df_disp["Vendas"]=df_disp["Vendas"].apply(lambda x:int(x) if x==int(x) else x)
    df_disp["Comissao"]=df_disp["Comissao"].apply(lambda x:"R$ {:.2f}".format(x))
    df_disp["CTR"]=df_disp["CTR"].apply(lambda x:"{:.1f}%".format(x))
    df_disp["Ticket"]=df_disp["Ticket"].apply(lambda x:"R$ {:.2f}".format(x))
    st.dataframe(df_disp,use_container_width=True,height=400)
    # Linha de resumo alinhada — mesma grelha de colunas da tabela
    # Colunas: idx(40) | Data | Sub_id2 | Sub_id1 | Sub_id3 | Cliques | Vendas | Comissao | CTR | Ticket
    # Usamos grid com proporções aproximadas ao st.dataframe
    r_cliques=int(df_t["Cliques"].sum()); r_vendas=int(df_t["Vendas"].sum()); r_comissao=df_t["Comissao"].sum()
    r_ctr=(r_vendas/r_cliques*100) if r_cliques>0 else 0.0; r_ticket=(r_comissao/r_vendas) if r_vendas>0 else 0.0
    st.markdown(
        '<div style="display:flex;justify-content:flex-end;gap:20px;background:#1a1410;border:1px solid #3a2c28;'
        'border-radius:0 0 6px 6px;padding:7px 16px;margin-top:-6px;flex-wrap:wrap;align-items:center;">'
        '<span style="color:#c5936d;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-right:auto;">∑ {} linhas</span>'
        '<span style="color:#c5936d;font-size:11px;">🖱 Cliques <b style="color:#f6e8d8;">{:,}</b></span>'
        '<span style="color:#c5936d;font-size:11px;">🛒 Vendas <b style="color:#f6e8d8;">{:,}</b></span>'
        '<span style="color:#c5936d;font-size:11px;">💰 Comissão <b style="color:#f6e8d8;">R$ {:.2f}</b></span>'
        '<span style="color:#c5936d;font-size:11px;">📊 CTR <b style="color:#f6e8d8;">{:.1f}%</b></span>'
        '<span style="color:#c5936d;font-size:11px;">🎫 Ticket <b style="color:#f6e8d8;">R$ {:.2f}</b></span>'
        '</div>'.format(len(df_t),r_cliques,r_vendas,r_comissao,r_ctr,r_ticket),
        unsafe_allow_html=True)
    html_r="<html><body><h1>Relatorio Matiq </h1><p>Periodo: {} a {}</p><p>Comissao: {} | Lucro: {} | ROI: {:.2f} | Invest: {}</p>{}</body></html>".format(d_ini,d_fim,fmt_brl(m["comissao"]),fmt_brl(m["lucro"]),m["roi"],fmt_brl(invest_total),df_t.to_html(index=False))
    st.download_button("📥 Download HTML",data=html_r.encode("utf-8"),file_name="relatorio_{}_{}.html".format(d_ini,d_fim),mime="text/html",key="dl_btn")

    st.markdown('<div id="insights-ia" class="section-title">🤖 MATIQ AI</div>',unsafe_allow_html=True)
    st.markdown("""<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;"><div style="background:#1a1210;border:1px solid #bd6d34;border-radius:10px;padding:16px;"><div style="color:#bd6d34;font-size:13px;font-weight:700;margin-bottom:6px;">Campanha Paga</div><div style="color:#c5936d;font-size:12px;">Analise tecnica de CPM, CPC, CAC, frequencia e funil.</div></div><div style="background:#1a1210;border:1px solid #9c5834;border-radius:10px;padding:16px;"><div style="color:#9c5834;font-size:13px;font-weight:700;margin-bottom:6px;">Todos os Canais + Criativos</div><div style="color:#c5936d;font-size:12px;">Comparacao entre canais + sugestao de criativos baseada no IPA.</div></div></div><div style="color:#c5936d;font-size:11px;margin-bottom:12px;">(*) Cada analise ~$0.01 de creditos Anthropic.</div>""",unsafe_allow_html=True)
    if "analise_camp" not in st.session_state: st.session_state.analise_camp=None
    if "analise_geral" not in st.session_state: st.session_state.analise_geral=None
    btn1,btn2,_=st.columns([1,1,2])
    with btn1: gerar_camp=st.button("Analisar Campanha Paga",use_container_width=True,key="btn_camp")
    with btn2: gerar_geral=st.button("Analisar Todos + Criativos",use_container_width=True,key="btn_geral")
    if gerar_camp and m_pago and not df_pago_periodo.empty:
        with st.spinner("A analisar..."):
            try:
                api_key=st.secrets.get("anthropic",{}).get("api_key","")
                dados="Periodo:{} a {}\nInvest:{:.2f}|Vendas:{:.0f}|Comissao:{:.2f}|Lucro:{:.2f}|ROI:{:.2f}\nCPM:{:.2f}|CPC:{:.2f}|CAC:{:.2f}|Freq:{:.2f}x\nCTR_Meta:{:.2f}%|CTR_Conv:{:.2f}%\nFunil:{:.0f}imp->{:.0f}alc->{:.0f}clq->{:.0f}vnd".format(d_ini,d_fim,invest_pago,m_pago["vendas"],m_pago["comissao"],m_pago["lucro"],m_pago["roi"],m_pago.get("cpm_imp",0),m_pago.get("cpc",0),m_pago.get("cac",0),m_pago.get("freq",0),m_pago.get("ctr_meta",0),m_pago.get("ctr_cv",0),m_pago.get("impressoes",0),m_pago.get("alcance",0),m_pago.get("cliques_meta",0),m_pago["vendas"])
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
                _ai_cols=[ipa_col,ipa_other,"IPA","Comissao","Vendas","CTR","Ticket","Pedidos"]; _ai_cols=[c for c in _ai_cols if c in df_v.columns]
                top_ipa=df_v.nlargest(8,"IPA")[_ai_cols].to_string(index=False) if not df_v.empty else "Sem dados"
                dados_g="Periodo:{} a {}\nComissao:{:.2f}|Lucro:{:.2f}|ROI:{:.2f}|Vendas:{:.0f}\nPago:{:.0f}vnd|R${:.2f}|ROI:{:.2f}|Ticket:{:.2f}\nOrganico:{:.0f}vnd|R${:.2f}|Ticket:{:.2f}\nStory:{:.0f}vnd|R${:.2f}|Ticket:{:.2f}\nInvest.Awareness:R${:.2f}\nTop IPA:\n{}".format(d_ini,d_fim,m["comissao"],m["lucro"],m["roi"],m["vendas"],m_pago["vendas"] if m_pago else 0,m_pago["comissao"] if m_pago else 0,m_pago["roi"] if m_pago else 0,m_pago["ticket"] if m_pago else 0,m_org["vendas"] if m_org else 0,m_org["comissao"] if m_org else 0,m_org["ticket"] if m_org else 0,m_story["vendas"] if m_story else 0,m_story["comissao"] if m_story else 0,m_story["ticket"] if m_story else 0,invest_aw,top_ipa)
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

    st.markdown('<div class="footer">🔓 <strong style="color:#bd6d34;">MATIQ</strong> <span style="color:#c5936d;">Analytics</span></div>',unsafe_allow_html=True)

if __name__=="__main__":
    main()
