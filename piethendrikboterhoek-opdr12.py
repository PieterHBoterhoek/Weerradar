from urllib.request import urlopen
import json
from flask import Flask, render_template, redirect

app = Flask(__name__)

url = "https://data.buienradar.nl/2.0/feed/json"

response = urlopen(url)

data = json.loads(response.read())
data2 = json.dumps(data)
data3 = json.loads(data2)

introTxt = """
/-------------
Welkom Jongeman!
Maak een keuze ?
    1. Weerstatistieken in een bepaalde periode
    2: Het actuele weer van een plaats
    3: Het weerbericht
Of sluit af via 'q'
-------------/"""

def ReadJson():
    print(data)

def CheckInput(userInput):
    if userInput == "q":
        quit()
    elif userInput == "1":
        print("1")
    elif userInput == "2":
        print("2")
    elif userInput == "3":
        print(data3["forecast"]["weatherreport"]["text"])

def Main():
    print(introTxt)
    while True:
        userInput = input(">")
        CheckInput(userInput)

@app.route("/")
def hello_world():
    Main()
    return render_template('index.html')

@app.errorhandler(404)
def redirect_to_root(e):
    return redirect("/")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)