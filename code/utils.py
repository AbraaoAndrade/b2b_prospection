from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from shapely.ops import unary_union
import haversine as hs
from forex_python.converter import CurrencyRates

import datetime 
import pandas as pd
import numpy as np
import time 
from io import BytesIO
import xlsxwriter
import requests
import json

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

        self.types = pd.read_table("data/types.txt")["types"]
        self.sel_type = None

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
                for key, value in weekday_text_replace_dict.items():
                    weekday_text = weekday_text.replace(key, value)
            else:
                weekday_text = np.nan
        else:
            formatted_phone_number, weekday_text = np.nan, np.nan

        return formatted_phone_number, weekday_text


    def get_report(self, API_KEY, type):
        self.API_KEY = API_KEY
        self.sel_type = type
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

        self.formatted_report = self.report.sort_values(["phone_number", "opening_hours"])
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

def export_folium(m):
    data = BytesIO()
    m.save(data, close_file=False)
    return data.getvalue().decode()

def send_email(sender, password, receiver, smtp_server, smtp_port, email_message, subject, attachment=None):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.header import Header
    from email.mime.application import MIMEApplication

    message = MIMEMultipart()
    message['To'] = Header(receiver)
    message['From']  = Header(sender)
    message['Subject'] = Header(subject)
    message.attach(MIMEText(email_message,'plain', 'utf-8'))
    if attachment:
        att = MIMEApplication(attachment.read(), _subtype="txt")
        att.add_header('Content-Disposition', 'attachment', filename=attachment.name)
        message.attach(att)

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.ehlo()
    server.login(sender, password)
    text = message.as_string()
    server.sendmail(sender, receiver, text)
    server.quit()
