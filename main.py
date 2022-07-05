import os, sys, ssl, certifi
from collections import defaultdict
from requests import get
from bs4 import BeautifulSoup
import sqlite3
import plotly.graph_objects as go
from geopy.geocoders import Nominatim
import geopy.geocoders

class Main():
    def __init__(self, dbFile):
        self.conn = sqlite3.connect(dbFile)
        self.cursor = self.conn.cursor()
        self.cursor.executescript("""
                CREATE TABLE IF NOT EXISTS college_locations (
                    college_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    college_name TEXT,
                    latitude TEXT,
                    longitude TEXT
                );
                CREATE TABLE IF NOT EXISTS players (
                    player_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT,
                    college_id INTEGER,
                    FOREIGN KEY (college_id) REFERENCES college_locations(college_id)
                );
        """)

    def _getRosterData(self):
        # scrapes the roster webpage and returns the table rows that have each player's information
        url = "https://www.49ers.com/team/players-roster/"
        response = get(url)
        nfl = BeautifulSoup(response.content, 'html.parser')
        nfl_main = nfl.find(id="main-content")
        nfl_roster = nfl_main.find(summary="Roster")
        nfl_roster_body = nfl_roster.find('tbody')
        rows = nfl_roster_body.find_all('tr')
        return rows

    def _map_college_to_players(self):
        # maps college names to all the players that went to that college
        rows = self._getRosterData()
        college_to_player = defaultdict(list)
        for row in rows:
            name = row.find_all('td')[0].text.strip()
            college = row.find_all('td')[7].text.strip()
            college_to_player[college].append(name)
        return college_to_player

    def _get_coords(self, uni):
        # gets the latitude and longitude of university 
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

    def _update_locations_db(self):
        # checks if there's any colleges not in the db and adds them if need be
        college_to_player = self._map_college_to_players()
        colleges_not_in_db = []
        for college, players in college_to_player.items():
            query = self.cursor.execute("SELECT * FROM college_locations WHERE college_name = ?", (college,)).fetchall()
            if bool(query) == False: # college NOT in db
                try:
                    location = self._get_coords(college)
                    colleges_not_in_db.append((college, location.latitude, location.longitude))
                except Exception as e:
                    print(e)
                    #continue

        # save new colleges to db
        self.cursor.executemany("INSERT INTO college_locations(college_name, latitude, longitude) VALUES (?,?,?)", colleges_not_in_db)
        self.conn.commit()

    def _plot_data(self):
        self._update_locations_db()
        # this makes it so that select doesn't return tuple and instead the individual values
        self.cursor.row_factory = lambda cursor, row: row[0]

        fig = go.Figure(data=go.Scattergeo(
            lon=self.cursor.execute("SELECT longitude FROM college_locations").fetchall(),
            lat=self.cursor.execute("SELECT latitude FROM college_locations").fetchall(),
            text=self.cursor.execute("SELECT college_name FROM college_locations").fetchall(),
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
        self._plot_data()
        self.conn.close()


if __name__ == '__main__':
    fourtyNinersMain = Main("locations.db")
    fourtyNinersMain.run()
