import json
import pandas as pd
import streamlit as st
import plotly.express as px


st.set_page_config(
    page_title="A3 Monitoramento",
    layout="wide"
)

st.title("A3 Monitoramento")

with open(
    "historico/historico.json",
    "r",
    encoding="utf-8"
) as arquivo:

    dados = json.load(arquivo)

df = pd.DataFrame(dados)

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "CPU",
    f"{df.iloc[-1]['cpu']}%"
)

col2.metric(
    "RAM",
    f"{df.iloc[-1]['ram_percent']}%"
)

col3.metric(
    "GPU",
    f"{df.iloc[-1]['gpu_percent']}%"
)

col4.metric(
    "PING",
    f"{df.iloc[-1]['ping']} ms"
)

st.subheader("Últimos Registros")

st.dataframe(
    df.tail(20),
    use_container_width=True
)
st.subheader("Últimos Registros")

st.dataframe(
    df.tail(20),
    use_container_width=True
)

fig_cpu = px.line(
    df,
    x="timestamp",
    y="cpu",
    title="Uso de CPU (%)"
)

st.plotly_chart(
    fig_cpu,
    use_container_width=True
)