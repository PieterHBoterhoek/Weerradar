from urllib.request import urlopen
import json
from flask import Flask, render_template, redirect, request, jsonify, send_from_directory
import html
import os
from datetime import datetime
import uuid

app = Flask(__name__)

url = "https://data.buienradar.nl/2.0/feed/json"
knmiFile = "etmgeg_260.txt"
outputDir = "resultaten"

# zorg dat de output directory bestaat
os.makedirs(outputDir, exist_ok=True)

response = urlopen(url)
months = ['Waarom moet het nou bij nul beginnen', 'Januari', 'Februari', 'Maart', 'April', 'Mei', 'Juni', "Juli", 'Augustus', "September", 'Oktober', 'November', "December"]

data = json.loads(response.read())
Stations = []

# pak alleen de nodige informatie uit de file
def parse_line(line):
    parts = line.strip().split(",")

    try:
        date = datetime.strptime(parts[1].strip(), "%Y%m%d")

        tg = int(parts[11].strip()) if parts[11].strip() else None
        tn = int(parts[12].strip()) if parts[12].strip() else None
        tx = int(parts[14].strip()) if parts[14].strip() else None
        rh = int(parts[22].strip()) if parts[22].strip() and parts[22].strip() != "-1" else None

        return {
            "date": date,
            "TG": tg,
            "TN": tn,
            "TX": tx,
            "RH": rh
        }

    except (ValueError, IndexError):
        return None

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

    sections = ["Vanochtend", "Vanmiddag", "Vanavond", "Vannacht", "Morgen", "Daarna"]

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

@app.route("/weerstatistieken", methods=['GET', 'POST'])
def WeerStatistieken():
    resultaat = None
    filename = None
    eersteDatum = None
    laatsteDatum = None

    # pak het eerste en laatste datum van de file
    with open(knmiFile, "r") as f:
        for line in f:
            if line.startswith("#") or line.strip() == "":
                continue

            parsed = parse_line(line)
            if not parsed:
                continue

            if eersteDatum is None:
                eersteDatum = parsed["date"].strftime("%Y-%m-%d")

            laatsteDatum = parsed["date"].strftime("%Y-%m-%d")

    if request.method == 'POST':
        start = request.form['start']
        eind = request.form["end"]

        if not start or not eind:
            return jsonify({"error": "Geef start en einddatum mee (YYYYMMDD)"}), 400

        start_date = datetime.strptime(start, "%Y%m%d")
        end_date = datetime.strptime(eind, "%Y%m%d")

        data = []

        with open(knmiFile, "r") as f:
            for line in f:
                if line.startswith("#") or line.strip() == "":
                    continue

                parsed = parse_line(line)
                if parsed and start_date <= parsed["date"] <= end_date:
                    data.append(parsed)

        if not data:
            return jsonify({"error": "Geen data gevonden in deze periode"}), 404
        
        # TG = Etmaalgemiddelde temperatuur (in 0.1 graden Celsius) / Daily mean temperature in (0.1 degrees Celsius)
        # TN = Minimum temperatuur (in 0.1 graden Celsius) / Minimum temperature (in 0.1 degrees Celsius)
        # TX = Maximum temperatuur (in 0.1 graden Celsius) / Maximum temperature (in 0.1 degrees Celsius)
        # RH = Etmaalsom van de neerslag (in 0.1 mm) (-1 voor <0.05 mm) / Daily precipitation amount (in 0.1 mm) (-1 for <0.05 mm)

        # bereken alle statistieken, deel door 10 anders kloppen de getallen niet
        maxTemp = max(d["TX"] for d in data if d["TX"] is not None) / 10
        minTemp = min(d["TN"] for d in data if d["TN"] is not None) / 10
        valid_tg = [d["TG"] for d in data if d["TG"] is not None] # neem niet de tgs mee die geen value hebben
        avgTemp = sum(valid_tg) / len(valid_tg) / 10
        totalRain = sum(d["RH"] for d in data if d["RH"] not in (None, -1)) / 10

        resultaat = {
            "periode": f"{start} - {eind}",
            "hoogste_temperatuur": maxTemp,
            "laagste_temperatuur": minTemp,
            "gemiddelde_temperatuur": round(avgTemp, 2),
            "totale_neerslag": totalRain
        }

        # bestand opslaan (uuid voor een unieke naam)
        filename = f"weerstatistieken-{start}-{eind}-{uuid.uuid4().hex}.txt"
        filepath = os.path.join(outputDir, filename)
        
        with open(filepath, "w") as f:
            f.write("Weerstatistieken\n")
            f.write(f"Periode: {start} - {eind}\n")
            f.write(f"Hoogste temperatuur: {maxTemp} \n")
            f.write(f"Laagste temperatuur: {minTemp} \n")
            f.write(f"Gemiddelde temperatuur: {round(avgTemp, 2)} \n")
            f.write(f"Totale neerslag: {totalRain} mm\n")

    return render_template("weerstatistieken.html", resultaat=resultaat, filename=filename, eerstedatum=eersteDatum, laatstedatum=laatsteDatum)

# download de nieuwste file die is aangemaakt
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory('resultaten', filename, as_attachment=True)

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