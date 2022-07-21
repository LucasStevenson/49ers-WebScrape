import requests, sqlite3, ssl, certifi
from collections import defaultdict
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from geopy.geocoders import Nominatim
import geopy.geocoders

class Main:
    def __init__(self, dbFile):
        self.college_to_players = defaultdict(list) # dictionary that maps data like so: {(collegeName, latitude, longitude): [all players that went to collegeName]}
        self.conn = sqlite3.connect(dbFile) # making connection to database file
        self.cursor = self.conn.cursor() # initialize cursor that allows us to execute commands
        self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS college_locations (
                    college_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    college_name TEXT,
                    latitude TEXT,
                    longitude TEXT
                )
        """)

    def _getRosterData(self):
        # scrapes the roster webpage and returns the table rows that have each player's information
        url = "https://www.49ers.com/team/players-roster/"
        response = requests.get(url)
        nfl = BeautifulSoup(response.content, 'html.parser')
        nfl_main = nfl.find(id="main-content")
        nfl_roster = nfl_main.find(summary="Roster")
        nfl_roster_body = nfl_roster.find('tbody')
        rows = nfl_roster_body.find_all('tr')
        return rows

    def _store_data(self):
        # iterates over all the rows returned by _getRosterData() method
        # for each row, check which college the player went to
        # if latitude and longitude of college is already in the database, save data to college_to_players dictionary and continue onto next row
        # else if latitude and longitude of college NOT in database, get the coords by calling _get_coords() method and save latitude and longitude to both the database and college_to_players dictionary
        rows = self._getRosterData()
        for row in rows:
            name = row.find_all('td')[0].text.strip()
            college = row.find_all('td')[7].text.strip()
            dbQuery = self.cursor.execute("SELECT latitude, longitude FROM college_locations WHERE college_name = ?", (college,)).fetchall()
            print(college, dbQuery)
            # if coordinates of college already exists in db
            if dbQuery:
                lat, lon = dbQuery[0]
                self.college_to_players[(college, lat, lon)].append(name)
                continue

            # this part of the for loop only executes if latitude and longitude of college not in db
            try:
                location = self._get_coords(college) # get coords
                lat, lon = str(location.latitude), str(location.longitude)
                self.cursor.execute("INSERT INTO college_locations(college_name, latitude, longitude) VALUES(?,?,?)", (college, lat, lon)) # save coords to db
                self.college_to_players[(college, lat, lon)].append(name) # save (collegeName, lat, long) as dict key and append playerName to dict value
            except Exception as e:
                print(e)

        self.conn.commit()

    def _get_coords(self, uni):
        # gets the latitude and longitude of specified university 
        ctx = ssl.create_default_context(cafile=certifi.where())
        geopy.geocoders.options.default_ssl_context = ctx
        geolocator = Nominatim(user_agent='my_map')
        location1 = geolocator.geocode(f"{uni} University")
        if location1 != None:
            return location1
        return geolocator.geocode(f"University of {uni}")

    def _plot_data(self):
        # parses data in college_to_players dictionary and plots information on an interactive map of the US
        lat, lon, text = [],[],[]
        for k,v in self.college_to_players.items():
            print(f"{k}: {v}")
            lat.append(k[1])
            lon.append(k[2])
            text.append(f"{k[0]}: {v}")

        fig = go.Figure(data=go.Scattergeo(
            lon=lon,
            lat=lat,
            text=text,
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
        self._store_data()
        self._plot_data()
        self.conn.close()

if __name__ == '__main__':
    fourtyNinersMain = Main("locations.db")
    fourtyNinersMain.run()
