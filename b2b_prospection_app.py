import streamlit as st
import folium
from streamlit_folium import folium_static
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from st_switcher import st_switcher
from streamlit_authenticator import Authenticate, Hasher
import yaml

from b2b_report import *
from send_email import *

def about():
    get_api_key_url = "https://developers.google.com/maps/documentation/places/web-service/get-api-key"
    st.warning("""
    Nesse projeto foi utilizada a API Places, um serviço da Google que retorna informações sobre lugares usando solicitações HTTP. \
    As interações com esse serviço se dão mediante uma chave de API, portanto, para experimentar o APP será necessário [criar uma chave](%s).
    """% get_api_key_url)

    with st.form("email_form", clear_on_submit=False):
        fullname = st.text_input(label="Nome Completo", placeholder="Porfavor digite seu nome completo")
        email = st.text_input(label="Email", placeholder="Porfavor digite seu email")
        text = st.text_area(label="Texto", placeholder="Porfavor digite sua mensagem aqui")

        submitted = st.form_submit_button("Enviar")
    
    if submitted:
        extra_info = """
        ---------------------------------------------------------------------------- \n
         Email Address of Sender: {} 
         Sender Full Name: {} \n
        ---------------------------------------------------------------------------- \n \n
        """.format(email, fullname)

        message = extra_info + text

        send_email(sender=st.secrets["EMAIL_USER"], password=st.secrets["EMAIL_KEY"],
                   receiver=st.secrets["EMAIL_USER"], smtp_server="smtp.gmail.com", smtp_port=587,
                   email_message=message, subject="B2B prospection APP")



def app():

    # 1. interface ------------------------------------------------------------------------------------------------
    cidades_selecionadas = st.multiselect("Cidades", (st.session_state.b2b_report_env.cities))
    st.text("""Obs: Grande Natal = Natal, Parnamirim, São Gonçalo do Amarante, Macaíba, Extremoz, Arês, Bom Jesus, Ceará-Mirim, Goianinha, Ielmo Marinho, Maxaranguape, Monte Alegre, Nísia Floresta, São José de Mipibu, Vera Cruz""")
    c1, c2 = st.columns(2)
    with c1:
        raio = st.number_input("Raio", min_value=1.0, max_value=8.0, step=0.1, value=1.5)
    with c2:
        type = st.selectbox("Tipo", st.session_state.b2b_report_env.types)

    c1, c2, _, _, _ = st.columns([1.1, 1, 1, 1, 1])
    with c1:
        checkbox_cidades = st.checkbox("todas cidades")
    with c2:
        checkbox_segmentos = st.checkbox("segmentos")
    
    API_KEY = st.text_input("Chave API", type="password")
        
    st.session_state.b2b_report_env.progress_bar = st.progress(0)

    c1, c2, c3, c4, _, _= st.columns([0.8, 1.3, 1.5, 1, 1.1, 1])
    with c1:
        button_gerar_relatorio = st.button("Gerar")
    with c2:
        if not st.session_state.b2b_report_env.report.empty:
            button_add_details = st.button("ADD detalhes")
    with c3:
        if not st.session_state.b2b_report_env.formatted_report.empty:
            st.download_button(label="Baixar Relatório",
                                data=st.session_state.b2b_report_env.to_excel(),
                                file_name="report.xlsx")
    with c4:
        if not st.session_state.b2b_report_env.formatted_report.empty:
            button_reset = st.button("Reset")


    # 2. processamento --------------------------------------------------------------------------------------------
    if cidades_selecionadas:
        st.session_state.b2b_report_env.select_cities(cidades_selecionadas)
        st.session_state.b2b_report_env.generate_segments(raio)

    if not st.session_state.b2b_report_env.formatted_report.empty:
        if button_reset:
            st.session_state.clear()
            st.experimental_rerun()

        # add details
    if not st.session_state.b2b_report_env.report.empty:
        if button_add_details:
            st.session_state.b2b_report_env.add_details()
            st.experimental_rerun()
            
        # gera relatorio
    if button_gerar_relatorio and st.session_state.authentication_status:
        st.session_state.b2b_report_env.get_report(API_KEY, type)
        st.experimental_rerun()
    elif button_gerar_relatorio and st.session_state.authentication_status != True:
        st.session_state.sidebar_state = 'expanded'
        st.experimental_rerun()
    else:
        st.session_state.sidebar_state = 'collapsed'

        
    # 3. resultados --------------------------------------------------------------------------------------------
        # previsão de gastos
    if not st.session_state.b2b_report_env.report.empty:
        prev_gasto_usd, prev_gasto_brl = st.session_state.b2b_report_env.budget()
        prev_gasto_details_usd, prev_gasto_details_brl = st.session_state.b2b_report_env.budget(details=True)
        st.warning(f"""Previsão de gasto: \n- Relatório    : {prev_gasto_usd} USD ~ {prev_gasto_brl} BRL (sem detalhes)
                     \n- ADD detalhes: {prev_gasto_details_usd} USD ~ {prev_gasto_details_brl} BRL""")
    else:
        prev_gasto_usd, prev_gasto_brl = st.session_state.b2b_report_env.budget()
        st.warning(f"Previsão de gasto: \n- Relatorio    : {prev_gasto_usd} USD ~ {prev_gasto_brl} BRL (sem detalhes)")
    

        # mapa
    red = {'fillColor': '#FC7979', 'color': '#FF0000'}
    green = {'fillColor': '#79FC7B', 'color': '#17A700'}
    m = folium.Map()
            # ajustando zoom
    m.fit_bounds(st.session_state.b2b_report_env.get_zoom_coordinates()) 
            # desenhando cidades
    if checkbox_cidades:
        for row in st.session_state.b2b_report_env.geojson.query(f'name != {list(cidades_selecionadas)}').itertuples():
            folium.GeoJson(data=row.coord, style_function=lambda x:red).add_to(m) 
    for row in st.session_state.b2b_report_env.geojson.query(f'name == {list(cidades_selecionadas)}').itertuples():
        folium.GeoJson(data=row.coord, style_function=lambda x:green).add_to(m) 
            # desenhando segmentos
    if checkbox_segmentos and cidades_selecionadas:
        for coord in st.session_state.b2b_report_env.segment_coordinates:
            folium.Circle(coord, st.session_state.b2b_report_env.radius_km, color="green").add_to(m)
    
    if not st.session_state.b2b_report_env.report.empty:
        for client in st.session_state.b2b_report_env.report.itertuples():
            latitude, longitude = client.lat, client.lng
            folium.Circle([latitude, longitude], 0.01, color="green", fill=False).add_to(m)
    
    folium_static(m)
    
        # plot
    if not st.session_state.b2b_report_env.report.empty:
        st.markdown("### Resultados por Região")
        fig, ax = plt.subplots(figsize=[12,6])
        ax.bar(range(1, len(st.session_state.b2b_report_env.results_per_loc)+1), st.session_state.b2b_report_env.results_per_loc, color="#31333F")
        ax.set_ylabel("Número de Resultados", fontsize=16)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.tick_params(axis='both', which='major', labelsize=16, colors="#31333F")
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_visible(True)
        ax.spines['bottom'].set_color('#31333F')
        fig.patch.set_alpha(0.0)
        ax.xaxis.label.set_color('#31333F')
        ax.yaxis.label.set_color('#31333F')
        ax.grid(axis='y')
        st.pyplot(fig)

        # dataframe
    if not st.session_state.b2b_report_env.formatted_report.empty:
        st.markdown("### Relatório")
        st.dataframe(st.session_state.b2b_report_env.formatted_report)
        
        st.download_button(
            label="Press to Download",
            data=st.session_state.b2b_report_env.to_excel(),
            file_name="report.xlsx")


if 'sidebar_state' not in st.session_state:
    st.session_state['sidebar_state'] = 'collapsed'
st.set_page_config(page_title="B2B prospection",
                    layout="centered",
                    page_icon=":handshake:",
                    initial_sidebar_state=st.session_state.sidebar_state)

# autentificação 
with open('data/config.yaml') as file:
    config = yaml.load(file, Loader=yaml.SafeLoader)

authenticator = Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None

with st.sidebar:
    name, st.session_state['authentication_status'], username = authenticator.login('Login', 'main')

    if st.session_state.authentication_status:
        authenticator.logout('Logout', 'main')
        st.success(f'Welcome *{name}*')
    elif st.session_state.authentication_status == False:
        st.error('Username/password is incorrect')
    elif st.session_state.authentication_status == None:
        st.warning('Please enter your username and password')


# pagina
page = st_switcher()
st.markdown("# Prospecção de clientes B2B")

if 'b2b_report_env' not in st.session_state:
    st.session_state['b2b_report_env'] = b2b_report()

if page == 'yang':
    about()
else:
    app()
    
