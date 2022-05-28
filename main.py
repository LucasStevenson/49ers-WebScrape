import csv
import os
from collections import defaultdict
import sys
from requests import get
from bs4 import BeautifulSoup
import pandas as pd
import plotly.graph_objects as go
from geopy.geocoders import Nominatim
import geopy.geocoders
import ssl
import certifi

class Main():
    def __init__(self, csvFile):
        self.csvFile = csvFile

    def _getPlayersAndColleges(self):
        url = "https://www.49ers.com/team/players-roster/"
        response = get(url)
        nfl = BeautifulSoup(response.content, 'html.parser')
        nfl_main = nfl.find(id="main-content")
        nfl_roster = nfl_main.find(summary="Roster")
        nfl_roster_body = nfl_roster.find('tbody')
        rows = nfl_roster_body.find_all('tr')
        playersToCollege = {}
        for row in rows:
            playerName = row.find_all('td')[0].text
            playerCollege = row.find_all('td')[7].text
            playersToCollege[playerName.strip()] = playerCollege.strip()
        return playersToCollege

    def _get_coords(self, uni):
        ctx = ssl.create_default_context(cafile=certifi.where())
        geopy.geocoders.options.default_ssl_context = ctx
        geolocator = Nominatim(user_agent='my_map')
        location1 = geolocator.geocode(uni)
        if location1 != None:
            return location1
        location2 = geolocator.geocode(f"{uni} University")
        if location2 != None:
            return location2
        return geolocator.geocode(f"University of {uni}")

    def _map_location_to_player(self):
        lat_long_dict = defaultdict(list)
        players_uni_dict = self._getPlayersAndColleges()
        for player, university in players_uni_dict.items():
            try:
                location = self._get_coords(university)
                lat_long_dict[(location.latitude, location.longitude, university)].append(player)
            except Exception as e:
                print(e)
                continue
        return lat_long_dict

    def _write_data_to_csvFile(self):
        lat_long_dict = self._map_location_to_player()
        with open(self.csvFile, 'w') as player_file:
            player_writer = csv.writer(player_file, delimiter=',')
            player_writer.writerow(['Players', "Latitude", "Longitude", "Location"])
            for location, players in lat_long_dict.items():
                latitude, longitude, college = location
                player_writer.writerow(
                    [players, latitude, longitude, college])

    def _plot_data(self):
        df = pd.read_csv(self.csvFile)
        print(df)
        fig = go.Figure(data=go.Scattergeo(
            lon=df['Longitude'],
            lat=df['Latitude'],
            text=df["Players"] + ": " + df["Location"],
            mode='markers',
            marker_color="rgb(210, 0, 0)"
        ))

        fig.update_layout(
            title='SF 49ers Colleges<br>(Hover for [player name: college])',
            geo=dict(
                scope='usa',
                showland=True,
                landcolor="rgb(207,181,59)",
            ),
        )
        fig.show()

    def run(self):
        if os.path.exists(self.csvFile):
            print(f"'{self.csvFile}' already exists")
            userInput = input("Do you want to use the information from there? (keep in mind it might be outdated) [Y/N]: ")
            if userInput.lower() == "y":
                self._plot_data()
                return
        print("Fetching latest player information...")
        self._write_data_to_csvFile()
        self._plot_data()


if __name__ == '__main__':
    fourtyNinersMain = Main("player_file.csv")
    fourtyNinersMain.run()
