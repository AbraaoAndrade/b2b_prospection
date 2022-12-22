#%%
f = open("geojs-24-mun.json", encoding="utf-8")
geojson = pd.DataFrame(json.load(f)["features"])
geojson_dict = {"id" : geojson.apply(lambda row: row["properties"]["id"], axis=1),
                "name" : geojson.apply(lambda row: row["properties"]["name"], axis=1),
                "coord" : geojson.apply(lambda row: row["geometry"], axis=1)}
geojson_df = pd.DataFrame(geojson_dict)
geojson_dict = dict(zip(geojson_df["name"], geojson_df["coord"].apply(lambda x: x["coordinates"][0])))
# with open('geojson.pkl', 'wb') as f:
#     pickle.dump(geojson_dict, f)

#%%
import pandas as pd
import numpy as np
import time 
import tqdm as tq
import pickle

import requests
import json
import folium
import haversine as hs
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from shapely.ops import cascaded_union, unary_union

import matplotlib.pyplot as plt
import seaborn as sns

from forex_python.converter import CurrencyRates
import datetime 

#%%

class b2b_report:
    def __init__(self):
        
        with open('geojson.pkl', 'rb') as f:
            self.geojson = pickle.load(f)

        cities_temp = list(self.geojson.keys())
        cities_temp.append("Grande Natal")
        self.cities = tuple(cities_temp)

        self.cities_polygon = [Polygon(city_polygon) for city_polygon in self.geojson.values()]
        self.total_polygon = unary_union(self.cities_polygon)

        self.types = pd.read_table("types.txt")["types"]

        c = CurrencyRates()
        dt = datetime.datetime.now()
        self.USD2BRL = c.get_rate('USD', 'BRL', dt)

        
        self.selected_cities = None
        self.selected_cities_polygon = None
        self.radius = None
        self.radius_km = None
        self.segment_coordinates = None
        self.API_KEY = None

        self.report = None


    def select_cities(self, selected_cities):
        grande_natal = ["Natal", "Parnamirim", "São Gonçalo do Amarante", "Macaíba", "Extremoz", "Arês", "Bom Jesus", 
                        "Ceará-Mirim", "Goianinha", "Ielmo Marinho", "Maxaranguape", "Monte Alegre", "Nísia Floresta", 
                        "São José de Mipibu", "Vera Cruz"]
        if "Grande Natal" in selected_cities:
            selected_cities.remove("Grande Natal")
            for city in grande_natal:
                selected_cities.append(city)

        self.selected_cities = selected_cities
        self.selected_cities_polygon = [Polygon(self.geojson[city]) for city in self.selected_cities]
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

    def budget(self, number=False): 
        if number:
            prev_gasto_number_usd = round(len(self.report)*0.017, 2)
            prev_gasto_number_brl = round(prev_gasto_number_usd*self.USD2BRL, 2)

            print(prev_gasto_number_usd, prev_gasto_number_brl)
                       
        else:
            prev_gasto_usd = round(len(self.segment_coordinates)*3*0.032, 2)
            prev_gasto_brl = round(prev_gasto_usd*self.USD2BRL, 2)   
            
            print(prev_gasto_usd, prev_gasto_brl)

    def get_b2b_clients_by_loc(self, loc, radius, type, api_key):
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
        API_KEY = api_key
        payload={}
        headers = {}

        
        # 2. First request
        url_nearbysearch_first = url.format(method="nearbysearch", 
                                            paramns=f"location={loc[0]}%2C{loc[1]}&radius={radius}&type={type}",
                                            key=API_KEY)
        response = requests.request("GET", url_nearbysearch_first, headers=headers, data=payload).json()
        if response["status"] == "OK":
            results_df = json2df_results(response["results"])

            # 3. Iterating until there is no next page
            while "next_page_token" in response.keys():
                time.sleep(2)
                
                url_nearbysearch = url.format(method="nearbysearch", 
                                            paramns=f"pagetoken={response['next_page_token']}",
                                            key=API_KEY)
                response = requests.request("GET", url_nearbysearch, headers=headers, data=payload).json()

                if response["status"] == "OK":
                    results_df_temp = json2df_results(response["results"])

                    results_df = pd.concat([results_df, results_df_temp])
            
            # 4. Adding phone number
            # placeid2phone_map = {}
            # for place_id in results_df["place_id"]:
            #     placeid2phone_map[place_id] = get_phone_number(place_id)

            results_df.index = range(len(results_df))
            # results_df["phone_number"] = results_df["place_id"].map(placeid2phone_map)

            return results_df
        
        else:
            return pd.DataFrame([])

    def get_phone_number(self, place_id):
        url = "https://maps.googleapis.com/maps/api/place/{method}/json?{paramns}&key={key}"
        with open('api_key.txt') as f:
            API_KEY = f.read()
        payload={}
        headers = {}
        # get details: phone number
        url_details = url.format(method="details", 
                                paramns=f"place_id={place_id}&fields=formatted_phone_number",
                                key=API_KEY)
        response_details = requests.request("GET", url_details, headers=headers, data=payload)
        result = response_details.json()["result"]
        if bool(result):
            phone_number = result["formatted_phone_number"]
        else: 
            phone_number = np.nan
        
        return phone_number

    def get_report(self, API_KEY, type):
        self.API_KEY = API_KEY
        report = pd.DataFrame([])
        results_per_loc = []
        for i, loc in enumerate(self.segment_coordinates):
            report_temp = self.get_b2b_clients_by_loc(loc, self.radius_km, type, self.API_KEY)
            results_per_loc.append(len(report_temp))
            report = pd.concat([report, report_temp])
        
        report["tipo"] = type

        self.report = report
    
    def add_number(self):
        self.report["phone_number"] = self.report.apply(lambda x: self.get_phone_number(x["place_id"]), axis=1)

    def final_report(self):
        self.report = self.report.sort_values("phone_number")

        columns = ['tipo', 'name', 'vicinity', 'phone_number', 'user_ratings_total', 'rating', "lat", "lng"]
        new_columns = ['Tipo', 'Nome', 'Endereço', 'Telefone', 'Número de avaliações', 'Avaliação', 'Latitude', 'Longitude']

        self.report = self.report[columns]
        self.report.columns = new_columns

# %%
test = b2b_report()
test.select_cities(["Natal"])
test.generate_segments(7)
test.budget()

#%%
test.get_report("AIzaSyDuSy2aD7Y47w54YOPcLiUlKp8C0Kd5Adc", "bar")

#%%
test.report

#%%
test.budget(number=True)

# %%
test.add_number()

# %%
test.final_report()
test.report
# %%
