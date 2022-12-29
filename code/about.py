import streamlit as st
import pandas as pd
from streamlit_authenticator import Hasher
from utils import *

def about():
    st.markdown("""---""")
    col1, col2, col3 = st.columns([15,1,1])
    with col1:
        st.markdown("Abraão Andrade — 28 Dez 2022 — 1 min leitura")
    with col2:
        st.markdown("[![Title](https://img.icons8.com/ios-glyphs/30/null/github.png)](https://github.com/AbraaoAndrade/b2b_prospection)")
    with col3:
        st.markdown("[![Title](https://img.icons8.com/ios-glyphs/30/null/linkedin-circled--v1.png)](linkedin.com/in/abraão-andrade-3632031b0)")
    
    st.markdown("## Contextualização")

    st.markdown("""
    A prospecção comercial é o primeiro passo para a venda. Esse tipo de atividade é fundamental para \
    construção de um bom volume de negócios, portanto, mapear a praça em que sua empresa está inserida \
    é um passo fundamental para um bom planejamento estratégico de vendas.
    """)

    st.markdown("## Projeto")
    st.markdown("""
    O projeto se propõe a gerar um relatório de potenciais clientes, com informações de localização e \
    telefone a partir de ferramentas disponíveis de Ciência de Dados.
    """)
    st.markdown("""
    Para isso foi utilizada a API Places, um serviço da Google que retorna informações sobre lugares usando \
    solicitações HTTP. Essa API permite pesquisar estabelecimentos dentro de um raio a partir de uma coordenada \
    de referência, restrito a um tipo, por exemplo: farmácia, bar, padaria…
    """)
    st.markdown("""
    Acontece que há um limite de 60 resultados por request, por isso, a ideia é fragmentar sua região de\
    interesse em sub-regiões para otimizar o número de estabelecimentos gerado.
    """)
    
    st.image("images/processo.png")
    st.image("images/plot.png")
    st.dataframe(pd.read_excel("data/report_pharmacy.xlsx"), height=200)

    get_api_key_url = "https://developers.google.com/maps/documentation/places/web-service/get-api-key"
    st.warning("""
    Nesse projeto foi utilizada a API Places, um serviço da Google em que as interações se dão mediante \
    uma chave de API, portanto, para experimentar o App será necessário [criar uma chave](%s).
    """% get_api_key_url)

    
    
    st.markdown("""---""")

    st.markdown("## Contato")
    checkbox_access = st.checkbox("Solicitar acesso")
    with st.form("email_form", clear_on_submit=False):
        if checkbox_access:
            col1, col2 = st.columns(2)
            with col1:
                username = st.text_input(label="Nome de Usuário")
            with col2:
                password = [st.text_input(label="Senha", type="password")]
        fullname = st.text_input(label="Nome Completo", placeholder="Digite seu nome completo")
        email = st.text_input(label="Email", placeholder="Digite seu email")
        text = st.text_area(label="Texto", placeholder="Digite sua mensagem aqui")

        submitted = st.form_submit_button("Enviar")

    if submitted:
        extra_info = """
        ---------------------------------------------------------------------------- \n
         Email Address of Sender: {} 
         Sender Full Name: {} \n
        ---------------------------------------------------------------------------- \n \n
        """.format(email, fullname)

        if checkbox_access:
            access_info = """
            Username: {}
            Password: {}
            \n
            """.format(username, Hasher(password).generate())
            extra_info = extra_info + access_info

        message = extra_info + text

        send_email(sender=st.secrets["EMAIL_USER"], password=st.secrets["EMAIL_KEY"],
                   receiver=st.secrets["EMAIL_USER"], smtp_server="smtp.gmail.com", smtp_port=587,
                   email_message=message, subject="B2B prospection APP")
