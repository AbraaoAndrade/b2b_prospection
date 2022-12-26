import streamlit as st
import streamlit.components.v1 as components
import folium
from streamlit_folium import folium_static
from st_switcher import st_switcher

import pandas as pd
import numpy as np
import time 
import tqdm as tq
import pickle
import os
from io import BytesIO
import xlsxwriter

import requests
import json
import folium
import haversine as hs
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from shapely.ops import cascaded_union, unary_union

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import seaborn as sns

from forex_python.converter import CurrencyRates
import datetime 

class b2b_report:
    def __init__(self):

        geojson_raws = ["https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-24-mun.json",
                        "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-25-mun.json"]
        geojson = pd.DataFrame([])
        for geojson_raw in geojson_raws:
            resp = requests.get(geojson_raw)

            geojson_temp = pd.DataFrame(json.loads(resp.text)["features"])
            geojson = pd.concat([geojson, geojson_temp])
        geojson_dict = {"id" : geojson.apply(lambda row: row["properties"]["id"], axis=1),
                        "name" : geojson.apply(lambda row: row["properties"]["name"], axis=1),
                        "coord" : geojson.apply(lambda row: row["geometry"], axis=1)}
        self.geojson = pd.DataFrame(geojson_dict)
        
        cities_temp = list(self.geojson["name"])
        cities_temp.append("Grande Natal")
        self.cities = tuple(cities_temp)

        self.cities_polygon = [Polygon(city["coordinates"][0]) for city in self.geojson["coord"]]
                                
        self.total_polygon = unary_union(self.cities_polygon)

        self.types = pd.read_table("types.txt")["types"]

        c = CurrencyRates()
        dt = datetime.datetime.now()
        try:
            self.USD2BRL = c.get_rate('USD', 'BRL', dt)
        except:
            self.USD2BRL = 5.30

        self.selected_cities = []
        self.selected_cities_polygon = None
        self.radius = None
        self.radius_km = None
        self.segment_coordinates = []
        self.API_KEY = None

        self.report = pd.DataFrame([])
        self.results_per_loc = []
        self.formatted_report = pd.DataFrame([])

        self.progress_bar = None



    def select_cities(self, selected_cities):
        grande_natal = ["Natal", "Parnamirim", "São Gonçalo do Amarante", "Macaíba", "Extremoz", "Arês", "Bom Jesus", 
                        "Ceará-Mirim", "Goianinha", "Ielmo Marinho", "Maxaranguape", "Monte Alegre", "Nísia Floresta", 
                        "São José de Mipibu", "Vera Cruz"]
        if "Grande Natal" in selected_cities:
            selected_cities.remove("Grande Natal")
            for city in grande_natal:
                selected_cities.append(city)

        self.selected_cities = selected_cities
        self.selected_cities_polygon = [Polygon(city["coordinates"][0]) for city in self.geojson.query(f'name == {list(self.selected_cities)}')["coord"]]
        self.total_polygon = unary_union(self.selected_cities_polygon)

    def get_zoom_coordinates(self):
        minx, miny, maxx, maxy = self.total_polygon.bounds
        sw = [maxy, maxx]
        ne = [miny, minx]

        return [sw, ne]

    def generate_segments(self, radius):
        self.radius = radius
        dist_dg = 0.01 * radius
        minx, miny, maxx, maxy = self.total_polygon.bounds
        delta_x = maxx-minx
        delta_y = maxy-miny
        num_x = int(np.ceil(delta_x/(dist_dg)))
        num_y = int(np.ceil(delta_y/(dist_dg)))
        coord_list = []
        self.segment_coordinates = []
        for i in range(num_y):
            for j in range(num_x):
                coord = [miny+(i*dist_dg)+(j%2*dist_dg/2), minx+(j*dist_dg)]
                coord_list.append(coord)

                point = Point(coord[1], coord[0])
                if self.total_polygon.contains(point):
                    self.segment_coordinates.append(coord)
        dist_km = hs.haversine(coord_list[0],coord_list[1])*1000
        self.radius_km = dist_km/2

    def budget(self, details=False): 
        if details:
            prev_gasto_details_usd = round(len(self.report)*0.017, 2)
            prev_gasto_details_brl = round(prev_gasto_details_usd*self.USD2BRL, 2)

            return prev_gasto_details_usd, prev_gasto_details_brl
                       
        else:
            prev_gasto_usd = round(len(self.segment_coordinates)*3*0.032, 2)
            prev_gasto_brl = round(prev_gasto_usd*self.USD2BRL, 2)   
            
            return prev_gasto_usd, prev_gasto_brl

    def get_b2b_clients_by_loc(self, loc, radius, type):
        # 1. Setup
        def json2df_results(results_json):
            # get json results and transform in DF
            results_df = pd.DataFrame(results_json)
            results_df["lat"] = results_df["geometry"].apply(lambda row: row["location"]["lat"])
            results_df["lng"] = results_df["geometry"].apply(lambda row: row["location"]["lng"])

            # filling missing columns
            columns = ['business_status', 'name', 'user_ratings_total', 'rating', 'vicinity', 'lat', 'lng', "types", 'place_id', 'phone_number']
            diff = list(set(columns) - set(results_df.columns))
            for missing_column in  diff:
                results_df[missing_column] = np.nan

            results_df = results_df[columns]
            return results_df
            
        

        url = "https://maps.googleapis.com/maps/api/place/{method}/json?{paramns}&key={key}"
        payload={}
        headers = {}

        
        # 2. First request
        url_nearbysearch_first = url.format(method="nearbysearch", 
                                            paramns=f"location={loc[0]}%2C{loc[1]}&radius={radius}&type={type}",
                                            key=self.API_KEY)
        response = requests.request("GET", url_nearbysearch_first, headers=headers, data=payload).json()
        if response["status"] == "OK":
            results_df = json2df_results(response["results"])

            # 3. Iterating until there is no next page
            while "next_page_token" in response.keys():
                time.sleep(2)
                
                url_nearbysearch = url.format(method="nearbysearch", 
                                            paramns=f"pagetoken={response['next_page_token']}",
                                            key=self.API_KEY)
                response = requests.request("GET", url_nearbysearch, headers=headers, data=payload).json()

                if response["status"] == "OK":
                    results_df_temp = json2df_results(response["results"])

                    results_df = pd.concat([results_df, results_df_temp])
           

            results_df.index = range(len(results_df))

            return results_df
        
        else:
            return pd.DataFrame([])

    def get_details(self, place_id):
        url = "https://maps.googleapis.com/maps/api/place/{method}/json?{paramns}&key={key}"
        payload={}
        headers = {}
        # get details: phone number, current_opening_hours
        url_details = url.format(method="details", 
                                paramns=f"place_id={place_id}&fields=formatted_phone_number%2Ccurrent_opening_hours",
                                key=self.API_KEY)
        response_details = requests.request("GET", url_details, headers=headers, data=payload)
        result = response_details.json()["result"]
        
        weekday_text_replace_dict = {"\u2009–\u2009":"-", "\u202f":" ", "Monday":"seg", "Tuesday":"ter", "Wednesday":"qua", "Thursday":"qui", "Friday":"sex", "Saturday":"sab", "Sunday":"dom"}
        if bool(result):
            if "formatted_phone_number" in list(result.keys()):
                formatted_phone_number = result["formatted_phone_number"]
            else:
                formatted_phone_number = np.nan
            if "current_opening_hours" in list(result.keys()):
                weekday_text = " > ".join(result["current_opening_hours"]["weekday_text"])
                for key, value in replace_dict.items():
                    weekday_text = weekday_text.replace(key, value)
            else:
                weekday_text = np.nan
        else:
            formatted_phone_number, weekday_text = np.nan, np.nan

        return formatted_phone_number, weekday_text

    def get_report(self, API_KEY, type):
        self.API_KEY = API_KEY
        report = pd.DataFrame([])
        results_per_loc = []
        for i, loc in enumerate(self.segment_coordinates):
            report_temp = self.get_b2b_clients_by_loc(loc, self.radius_km, type)
            results_per_loc.append(len(report_temp))
            report = pd.concat([report, report_temp])

            self.progress_bar.progress((i+1)/len(self.segment_coordinates))
        
        report["tipo"] = type

        self.results_per_loc = results_per_loc
        self.report = report
    
    def add_details(self):

        numbers_list = []
        opening_hours_list = []
        for i, place_id in enumerate(self.report["place_id"]):
            number, opening_hours = self.get_details(place_id)
            numbers_list.append(number)
            opening_hours_list.append(opening_hours)
            self.progress_bar.progress((i+1)/len(self.report))
        self.report["phone_number"] = numbers_list
        self.report["opening_hours"] = opening_hours_list

        self.formatted_report = self.report.sort_values("phone_number")
        self.formatted_report = self.formatted_report.reset_index(drop=True)
        columns = ['tipo', 'name', 'vicinity', 'phone_number', 'opening_hours', 'user_ratings_total', 'rating', "lat", "lng"]
        new_columns = ['Tipo', 'Nome', 'Endereço', 'Telefone', 'Horário de Funcionamento', 'Número de avaliações', 'Avaliação', 'Latitude', 'Longitude']
        self.formatted_report = self.formatted_report[columns]
        self.formatted_report.columns = new_columns

    def to_excel(self):
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        self.formatted_report.to_excel(writer, index=False, sheet_name='Sheet1')
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        format1 = workbook.add_format({'num_format': '0.00'}) 
        worksheet.set_column('A:A', None, format1)  
        writer.save()
        processed_data = output.getvalue()
        return processed_data

def about():
    st.text("about")

def app():
    

    red = {'fillColor': '#FC7979', 'color': '#FF0000'}
    green = {'fillColor': '#79FC7B', 'color': '#17A700'}

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
    if button_gerar_relatorio:
        st.session_state.b2b_report_env.get_report(API_KEY, type)
        st.experimental_rerun()

        
    

    
    # 3. resultados --------------------------------------------------------------------------------------------
        # previsão de gastos
    if not st.session_state.b2b_report_env.report.empty:
        prev_gasto_usd, prev_gasto_brl = st.session_state.b2b_report_env.budget()
        prev_gasto_details_usd, prev_gasto_details_brl = st.session_state.b2b_report_env.budget(details=True)
        st.warning(f"""Previsão de gasto: \n- Relatorio    : {prev_gasto_usd} USD ~ {prev_gasto_brl} BRL (sem detalhes)
                     \n- ADD telefones: {prev_gasto_details_usd} USD ~ {prev_gasto_details_brl} BRL""")
    else:
        prev_gasto_usd, prev_gasto_brl = st.session_state.b2b_report_env.budget()
        st.warning(f"Previsão de gasto: \n- Relatorio    : {prev_gasto_usd} USD ~ {prev_gasto_brl} BRL (sem detalhes)")
    

        # mapa
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
        ax.bar(range(1, len(st.session_state.b2b_report_env.results_per_loc)+1), st.session_state.b2b_report_env.results_per_loc, color="#FF4B4B")
        # ax.set_title("Resultados por Região", fontsize=20, loc="left")
        ax.set_ylabel("Número de Resultados", fontsize=16)
        # ax.set_xlabel("Segmentos", fontsize=16)
        # ax.set_xticks(range(len(st.session_state.b2b_report_env.results_per_loc)))
        # ax.set_xticklabels(range(1, len(st.session_state.b2b_report_env.results_per_loc)+1))
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.tick_params(axis='both', which='major', labelsize=16)
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_visible(True)
        ax.grid(axis='y')
        st.pyplot(fig)

    if not st.session_state.b2b_report_env.formatted_report.empty:
        # relatorio_number = pd.read_csv("data/relatorio_number.xlsx")

        st.markdown("### Relatório")
        st.dataframe(st.session_state.b2b_report_env.formatted_report)
        
        st.download_button(
            label="Press to Download",
            data=st.session_state.b2b_report_env.to_excel(),
            file_name="report.xlsx")

st.set_page_config(page_title="B2B prospection",
                    layout="centered",
                    initial_sidebar_state="auto")

page = st_switcher()
st.markdown("# Prospecção de clientes B2B")

if 'b2b_report_env' not in st.session_state:
    st.session_state['b2b_report_env'] = b2b_report()

if page == 'yang':
    about()
else:
    app()
    
