import streamlit as st
import folium
from streamlit_folium import folium_static
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from utils import *

def app():

    # 1. interface ------------------------------------------------------------------------------------------------
    cidades_selecionadas = st.multiselect("Cidades", (st.session_state.b2b_report_env.cities))
    st.text("""Obs: Grande Natal = Natal, Parnamirim, São Gonçalo do Amarante, Macaíba, Extremoz, Arês, Bom Jesus, Ceará-Mirim, Goianinha, Ielmo Marinho, Maxaranguape, Monte Alegre, Nísia Floresta, São José de Mipibu, Vera Cruz""")
    c1, c2 = st.columns(2)
    with c1:
        raio = st.number_input("Raio", min_value=1.0, max_value=8.0, step=0.1, value=1.5)
    with c2:
        type = st.selectbox("Tipo", st.session_state.b2b_report_env.types)

    c1, c2, _, _, _ = st.columns([1.4, 1, 1, 1, 1])
    with c1:
        checkbox_cidades = st.checkbox("cidades disponíveis")
    with c2:
        checkbox_segmentos = st.checkbox("segmentos")
    
    API_KEY = st.text_input("Chave API", type="password")
        
    st.session_state.b2b_report_env.progress_bar = st.progress(0)

    c1, c2, c3, c4, c5, _= st.columns([0.8, 1.3, 1.3, 1.5, 1, 1.1])
    with c1:
        button_gerar_relatorio = st.button("Gerar")
    with c3:
        if not st.session_state.b2b_report_env.report.empty:
            button_add_details = st.button("ADD detalhes")
    with c4:
        if not st.session_state.b2b_report_env.formatted_report.empty:
            st.download_button(label="Baixar Relatório",
                                data=st.session_state.b2b_report_env.to_excel(),
                                file_name="report.xlsx")
    with c5:
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

    st.text(st.session_state.b2b_report_env.radius_km)
        
    # 3. resultados --------------------------------------------------------------------------------------------
        # previsão de gastos
    if st.session_state['authentication_username'] in ["abraaoandrade"]:
        if not st.session_state.b2b_report_env.report.empty:
            prev_gasto_usd, prev_gasto_brl = st.session_state.b2b_report_env.budget()
            prev_gasto_details_usd, prev_gasto_details_brl = st.session_state.b2b_report_env.budget(details=True)
            st.warning(f"""Previsão de gasto: \n- Relatório    : {prev_gasto_usd} USD ~ {prev_gasto_brl} BRL (sem detalhes)
                        \n- ADD detalhes: {prev_gasto_details_usd} USD ~ {prev_gasto_details_brl} BRL""")
        else:
            prev_gasto_usd, prev_gasto_brl = st.session_state.b2b_report_env.budget()
            st.warning(f"Previsão de gasto: \n- Relatorio    : {prev_gasto_usd} USD ~ {prev_gasto_brl} BRL (sem detalhes)")
    
        # dataframe
    if not st.session_state.b2b_report_env.formatted_report.empty:
        # st.markdown("### Relatório")
        st.dataframe(st.session_state.b2b_report_env.formatted_report, height=200)

        # st.download_button(
        #     label="Press to Download",
        #     data=st.session_state.b2b_report_env.to_excel(),
        #     file_name="report.xlsx")

        # mapa
    red = {'fillColor': '#B1B1B1', 'color': '#FFFFFF'}
    green = {'fillColor': '#FF000000', 'color': '#00A60F'}
    m = folium.Map(tiles="openstreetmap")
    
    folium.TileLayer('stamentoner').add_to(m)
    folium.TileLayer('openstreetmap').add_to(m)

            # ajustando zoom
    m.fit_bounds(st.session_state.b2b_report_env.get_zoom_coordinates()) 
            # desenhando cidades
    if checkbox_cidades:
        group_all_cities = folium.FeatureGroup(name=f"<span style='color: black;'>Cidades disponíveis</span>")
        for row in st.session_state.b2b_report_env.geojson.query(f'name != {list(cidades_selecionadas)}').itertuples():
            folium.GeoJson(data=row.coord, style_function=lambda x:red).add_to(group_all_cities) 
        group_all_cities.add_to(m)
    group_sel_cities = folium.FeatureGroup(name=f"<span style='color: black;'>Cidades selecionadas</span>")
    for row in st.session_state.b2b_report_env.geojson.query(f'name == {list(cidades_selecionadas)}').itertuples():
        folium.GeoJson(data=row.coord, style_function=lambda x:green).add_to(group_sel_cities) 
    group_sel_cities.add_to(m)
            # desenhando segmentos
    if checkbox_segmentos and cidades_selecionadas:
        group_segments = folium.FeatureGroup(name=f"<span style='color: black;'>Segmentos</span>")
        for coord in st.session_state.b2b_report_env.segment_coordinates:
            folium.Circle(coord, st.session_state.b2b_report_env.radius_km, color="green").add_to(group_segments)
        group_segments.add_to(m)
            # estabelecimentos
    if not st.session_state.b2b_report_env.report.empty:
        group_results = folium.FeatureGroup(name=f"<span style='color: black;'>Estabelecimentos</span>") # st.session_state.b2b_report_env.sel_type
        for client in st.session_state.b2b_report_env.report.itertuples():
            latitude, longitude = client.lat, client.lng
            folium.Circle([latitude, longitude], 0.01, color="green", fill=False).add_to(group_results)
        group_results.add_to(m)
    # if not st.session_state.b2b_report_env.formatted_report.empty:
    #     group_phone = folium.FeatureGroup(name=f"<span style='color: black;'>Phone</span>")
    #     telefone, latitude, longitude =  st.session_state.b2b_report_env.formatted_report.loc[0, ["Telefone", "Latitude", "Longitude"]]
    #     folium.Marker(location=[latitude,longitude],popup = telefone,
    #               icon= folium.Icon(color="darkgreen",
    #               icon_color='white',icon = 'phone')).add_to(group_phone)
    #     group_phone.add_to(m)
    folium.map.LayerControl('topright', collapsed=False).add_to(m)
    folium_static(m)
    with c2:
        if not st.session_state.b2b_report_env.report.empty:
            st.download_button(label="Baixar Mapa",
                       data=export_folium(m),
                       file_name="mapa.html")
    
        # plot
    if not st.session_state.b2b_report_env.report.empty:
        # st.markdown("### Resultados por Região")
        fig, ax = plt.subplots(figsize=[12,4])
        ax.bar(range(1, len(st.session_state.b2b_report_env.results_per_loc)+1), st.session_state.b2b_report_env.results_per_loc, color="#31333F")
        ax.set_title("Resultados por Sub-regiões", loc="left", fontsize=22)
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
        
        