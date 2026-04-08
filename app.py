from urllib.request import urlopen
import json
from flask import Flask, render_template, redirect, request
import html

app = Flask(__name__)

url = "https://data.buienradar.nl/2.0/feed/json"

response = urlopen(url)
months = ['Waarom moet het nou bij nul beginnen', 'Januari', 'Februari', 'Maart', 'April', 'Mei', 'Juni', "Juli", 'Augustus', "September", 'Oktober', 'November', "December"]

data = json.loads(response.read())
Stations = []

def GetStations():
    for station in data["actual"]["stationmeasurements"]:
        s=station["regio"]
        Stations.append(s)
    print(Stations)
    return Stations

@app.route("/actueel", methods=['GET'])
def ActueelWeer():
    if not Stations:
        GetStations()

    station_data = []

    for s in data["actual"]["stationmeasurements"]:
        station_data.append({
            "name": s.get("regio"),
            "weertype": s.get("weatherdescription", "niet gemeten"),
            "temperatuur": s.get("temperature", "niet gemeten"),
            "bodemtemperatuur": s.get("groundtemperature", "niet gemeten"),
            "windkracht": s.get("windspeedBft", "niet gemeten"),
            "windrichting": s.get("winddirection", "niet gemeten"),
            "luchtvochtigheid": s.get("humidity"),
            "luchtdruk": s.get("airpressure"),
            "neerslag": s.get("rainFallLast24Hour", "niet gemeten"),
        })

    return render_template("actueelweer.html", stations=station_data)

def ConvertDate(date):
    sec1 = ''
    sec2 = ''
    sec3 = ''
    currentSec = 1
    for i in date:
        if i == "-":
            currentSec += 1
            continue
        else:
            if currentSec == 1:
                sec1 += i
            elif currentSec == 2:
                sec2 += i
            else:
                sec3 += i
    ''.join(sec1)
    ''.join(sec2)
    sec2 = months[int(sec2)]
    ''.join(sec3)
    date = f"Geplaats op {sec3} {sec2} {sec1}"
    return date

def WeerberichtFormatter(weerbericht, summary):
    weerbericht = html.unescape(weerbericht).strip()
    summary = html.unescape(summary).strip()

    sections = ["Vanmiddag", "Vanavond", "Vannacht", "Morgen", "Daarna"]

    if weerbericht.startswith(summary):
        bericht = weerbericht[len(summary):].strip()
    else:
        bericht = weerbericht
    
    samenvatting = f"<b>{summary}</b>"

    for i in sections:
        bericht = bericht.replace(i, f"\n\n<b>{i}</b>")

    if weerbericht.startswith(summary):
        return samenvatting + "\n" + bericht
    else:
        return bericht

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/weerstatistieken")
def WeerStatistieken():
    return render_template("weerstatistieken.html")

@app.route("/Weerbericht")
def Weerbericht():
    datumFull = data["forecast"]["weatherreport"]["published"]
    date = ''
    time = ''
    section = 1
    for i in datumFull:
        if section == 1:
            if i == "T":
                ''.join(date)
                section = 2
                continue
            else:
                date += i
        else:
            time += i
    ''.join(time)
    titel = data["forecast"]["weatherreport"]["title"]
    weerbericht = data["forecast"]["weatherreport"]["text"]
    samenvatting = data["forecast"]["weatherreport"]["summary"]
    author = data["forecast"]["weatherreport"]["author"]
    return render_template("weerbericht.html", date=ConvertDate(date=date), time=time, titel=titel, weerbericht=WeerberichtFormatter(weerbericht=weerbericht, summary=samenvatting), author=author)

@app.errorhandler(404)
def redirect_to_root(e):
    return redirect("/")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)