from flask import Flask, render_template, url_for, request, redirect, session, jsonify
import sqlite3
import os
import time
import base64
import numpy as np
import pandas as pd
import requests
import config
import pickle
import io
from PIL import Image
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
import telepot
import joblib   # <<< NEW: for loading Season Grow models

# --- NEW IMPORTS FOR GEMINI CHATBOT ---
from google import genai
from google.genai import types
# --------------------------------------

# --- ML Model Loading ---
forest = pickle.load(open('models/yield_rf.pkl', 'rb'))  # yield
model = pickle.load(open('models/classifier.pkl','rb'))
ferti = pickle.load(open('models/fertilizer.pkl','rb'))
cr = pickle.load(open('models/RandomForest.pkl', 'rb'))

# --- NEW: SEASON GROW MODELS & DATA ---
try:
    season_df = pd.read_csv("season_grow_dataset.csv")
    season_model = joblib.load("season_model.pkl")
    days_model = joblib.load("days_model.pkl")
    print("Season Grow models and dataset loaded successfully.")
except Exception as e:
    print(f"WARNING: Could not load Season Grow models/dataset: {e}")
    season_df = None
    season_model = None
    days_model = None
# --------------------------------------

# --- NEW: Initialize the Gemini Client using the API key ---
client = None
try:
    if hasattr(config, 'GEMINI_API_KEY'):
        client = genai.Client(api_key=config.GEMINI_API_KEY)
    else:
        print("WARNING: GEMINI_API_KEY not found in config.py. Chatbot will be disabled.")
except Exception as e:
    print(f"ERROR initializing Gemini client: {e}")
# -----------------------------------------------------------

# --- START: INTELLIGENT CHATBOT LOGIC (Dual Language Update) ---
def get_chatbot_response(user_message, language):
    """
    Uses the Gemini API to generate an intelligent, context-aware agricultural response
    in the requested language (English or Kannada).
    """
    if not client:
        # Fallback message based on language
        if language == 'Kannada':
            return "ಕ್ಷಮಿಸಿ, AI ಚಾಟ್‌ಬಾಟ್ ಸೇವೆಯನ್ನು ಸರಿಯಾಗಿ ಕಾನ್ಫಿಗರ್ ಮಾಡಲಾಗಿಲ್ಲ (API ಕೀ ಕಾಣೆಯಾಗಿದೆ)."
        return "Sorry, the AI chatbot service is not configured correctly (API Key missing or invalid)."

    # Define a core system instruction
    system_instruction_core = (
        "You are the AgroNet Chatbot, an expert assistant for farmers and agricultural enthusiasts in India. "
        "Your responses must be helpful, concise, and focused on relevant topics like crops (Rice, Wheat, Cotton, Maize, Tomato, Onion), soil science, fertilizer use, market prices, and weather impacts. "
        "If a user asks for a specific prediction (like 'best crop' or 'fertilizer recommendation'), direct them to the dedicated pages: CROP, FERTILIZER, or MARKET, as your role is guidance, not calculation. "
        "Maintain a supportive and professional tone. Keep your responses brief."
    )
    
    # Add language-specific instruction
    if language == 'Kannada':
        language_instruction = "Crucially, you MUST translate your entire final response into **Kannada** (ಕನ್ನಡ). The user will be typing in Kannada or English, but the response must be in Kannada. Do not include any English text other than the names of the web pages (CROP, MARKET, FERTILIZER, etc.)."
        error_msg = "ನಿಮ್ಮ ವಿನಂತಿಯನ್ನು ಪ್ರಕ್ರಿಯೆಗೊಳಿಸುವಾಗ ದೋಷ ಎದುರಾಗಿದೆ. AI ಸೇವೆಯು ತಾತ್ಕಾಲಿಕವಾಗಿ ಲಭ್ಯವಿಲ್ಲದಿರಬಹುದು."
    else: # Default to English
        language_instruction = "Your response must be entirely in **English**."
        error_msg = "I encountered an error while processing your request. The AI service may be temporarily unavailable."

    # Combine instructions
    final_system_instruction = f"{system_instruction_core} {language_instruction}"

    try:
        # Configuration for the API call
        config_params = types.GenerateContentConfig(
            system_instruction=final_system_instruction
        )

        # Call the Gemini API
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_message,
            config=config_params,
        )

        return response.text.strip() if response.text else error_msg

    except Exception as e:
        print(f"Gemini API Error: {e}")
        return error_msg

# --- END: INTELLIGENT CHATBOT LOGIC ---


def weather_fetch(city_name):
    """
    Fetch and returns the temperature and humidity of a city
    :params: city_name
    :return: temperature, humidity
    """
    api_key = config.weather_api_key
    base_url = "http://api.openweathermap.org/data/2.5/weather?"

    complete_url = base_url + "appid=" + api_key + "&q=" + city_name
    response = requests.get(complete_url)
    x = response.json()
    print('vgj,hDS|m n')
    print(response)

    if x["cod"] != "404":
        y = x["main"]

        temperature = round((y["temp"] - 273.15), 2)
        humidity = y["humidity"]
        return temperature, humidity
    else:
        return None

# --- Database Connection and Table Setup ---
connection = sqlite3.connect('user_data.db')
cursor = connection.cursor()

command = """CREATE TABLE IF NOT EXISTS user(name TEXT, password TEXT, mobile TEXT, email TEXT, image TEXT)"""
cursor.execute(command)

command = """CREATE TABLE IF NOT EXISTS farmer(name TEXT, password TEXT, mobile TEXT, email TEXT, image TEXT)"""
cursor.execute(command)

command = """CREATE TABLE IF NOT EXISTS seller(Id INTEGER PRIMARY KEY AUTOINCREMENT, crop TEXT, cost TEXT, district TEXT, image BLOB, quantity TEXT)"""
cursor.execute(command)

command = """CREATE TABLE IF NOT EXISTS tools(Id INTEGER PRIMARY KEY AUTOINCREMENT, crop TEXT, cost TEXT, district TEXT, image BLOB, quantity TEXT)"""
cursor.execute(command)

command = """CREATE TABLE IF NOT EXISTS buyer(Id INTEGER PRIMARY KEY AUTOINCREMENT, crop TEXT, cost TEXT, district TEXT, image BLOB)"""
cursor.execute(command)

command = """CREATE TABLE IF NOT EXISTS community_query(Id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, image BLOB, query TEXT)"""
cursor.execute(command)

command = """CREATE TABLE IF NOT EXISTS community_answer(query_id TEXT, username TEXT, answer TEXT)"""
cursor.execute(command)

app = Flask(__name__)
app.secret_key = os.urandom(24)
# ---------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')

def getprofile():
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM user WHERE name = '"+session['username']+"'")
    result = cursor.fetchone()
    if result:
        return result[-1]
    else:
        cursor.execute("SELECT * FROM farmer WHERE name = '"+session['username']+"'")
        result = cursor.fetchone()
        return result[-1]

# --- START: NEW CHATBOT ROUTES ---

@app.route('/agrichat')
def agrichat():
    # This route renders the new chatbot.html template
    if 'username' not in session:
         return redirect(url_for('index'))
         
    return render_template('chatbot.html', dp=getprofile(), name=session['username'])

@app.route('/api/agrichat', methods=['POST'])
def agrichat_api():
    # This API endpoint handles POST requests from the frontend JavaScript
    if not request.is_json or 'user_message' not in request.json or 'language' not in request.json:
        return jsonify({"error": "Missing 'user_message' or 'language' in request body"}), 400

    user_message = request.json['user_message']
    language = request.json['language'] # Get the language preference
    
    # Process the message using the Gemini API
    bot_reply = get_chatbot_response(user_message, language) # Pass language to the function

    response_data = {
        "bot_reply": bot_reply,
    }
    
    return jsonify(response_data)

# --- END: NEW CHATBOT ROUTES ---


@app.route('/userlog', methods=['GET', 'POST'])
def userlog():
    if request.method == 'POST':

        connection = sqlite3.connect('user_data.db')
        cursor = connection.cursor()

        name = request.form['name']
        password = request.form['password']

        query = "SELECT * FROM user WHERE name = '"+name+"' AND password= '"+password+"'"
        cursor.execute(query)

        result = cursor.fetchone()

        if result:
            session['username'] = result[0]
            return redirect(url_for('market'))
        else:
            return render_template('index.html', msg='Sorry, Incorrect Credentials Provided,  Try Again')

    return render_template('index.html')


@app.route('/userreg', methods=['GET', 'POST'])
def userreg():
    if request.method == 'POST':

        connection = sqlite3.connect('user_data.db')
        cursor = connection.cursor()

        name = request.form['name']
        password = request.form['password']
        mobile = request.form['phone']
        email = request.form['email']
        file = request.files['file']
        filename = file.filename
        file_content = file.read()
        File = base64.b64encode(file_content).decode('utf-8')
        
        print(name, mobile, email, password, File)

        cursor.execute("INSERT INTO user VALUES (?,?,?,?,?)",[name, password, mobile, email, File])
        connection.commit()

        return render_template('index.html', msg='Successfully Registered')
    
    return render_template('index.html')

@app.route('/farmerlog', methods=['GET', 'POST'])
def farmerlog():
    if request.method == 'POST':

        connection = sqlite3.connect('user_data.db')
        cursor = connection.cursor()

        name = request.form['name']
        password = request.form['password']
        print(name, password)
        query = "SELECT * FROM farmer WHERE name = '"+name+"' AND password= '"+password+"'"
        cursor.execute(query)

        result = cursor.fetchone()
        print(result)
        if result:
            session['username'] = result[0]
            return redirect(url_for('amarket'))
        else:
            return render_template('index.html', msg='Sorry, Incorrect Credentials Provided,  Try Again')

    return render_template('index.html')


@app.route('/farmerreg', methods=['GET', 'POST'])
def farmerreg():
    if request.method == 'POST':

        connection = sqlite3.connect('user_data.db')
        cursor = connection.cursor()

        name = request.form['name']
        password = request.form['password']
        mobile = request.form['phone']
        email = request.form['email']
        file = request.files['file']
        filename = file.filename
        print(filename)
        file_content = file.read()
        File = base64.b64encode(file_content).decode('utf-8')
        
        print(name, mobile, email, password, File)

        cursor.execute("INSERT INTO farmer VALUES (?,?,?,?,?)",[name, password, mobile, email, File])
        connection.commit()

        return render_template('index.html', msg='Successfully Registered')
    
    return render_template('index.html')


@app.route('/fertilizer', methods=['GET', 'POST'])
def fertilizer():
    import requests
    data=requests.get("https://api.thingspeak.com/channels/2780187/feeds.json?results=2")
    moi=data.json()['feeds'][-1]['field1']
    temp=data.json()['feeds'][-1]['field2']
    hum=data.json()['feeds'][-1]['field3']
    n=data.json()['feeds'][-1]['field4']
    p=data.json()['feeds'][-1]['field5']
    k=data.json()['feeds'][-1]['field6']
    if request.method == 'POST':

        temp = request.form.get('temp')
        humi = request.form.get('humid')
        mois = request.form.get('mois')
        soil = request.form.get('soil')
        crop = request.form.get('crop')
        nitro = request.form.get('nitro')
        pota = request.form.get('pota')
        phosp = request.form.get('phos')
        input = [int(float(temp)),int(float(humi)),int(float(mois)),int(float(soil)),int(float(crop)),int(float(nitro)),int(float(pota)),int(float(phosp))]

        res = ferti.classes_[model.predict([input])]
        print(f"RES   {res}")

        return render_template('fertilizer.html', prediction=res[0], dp = getprofile(), name=session['username'])
    
    
    return render_template('fertilizer.html',moi=moi,temp=temp,hum=hum,n=n,p=p,k=k, dp = getprofile(), name=session['username'])

##    return render_template('fertilizer.html')

@app.route('/Yield', methods=['GET', 'POST'])
def Yield():
    import requests
    data=requests.get("https://api.thingspeak.com/channels/2780187/feeds.json?results=2")
    moi=data.json()['feeds'][-1]['field1']
    temp=data.json()['feeds'][-1]['field2']
    hum=data.json()['feeds'][-1]['field3']
    n=data.json()['feeds'][-1]['field4']
    p=data.json()['feeds'][-1]['field5']
    k=data.json()['feeds'][-1]['field6']
    if request.method == 'POST':
        File = request.form['season']
        from check import check_stat
        check_stat(File)

        return render_template('yield.html')

    return render_template('yield.html',moi=moi,temp=temp,hum=hum,n=n,p=p,k=k, dp = getprofile(), name=session['username'])

@app.route('/crop', methods=['GET', 'POST'])
def crop():
    import requests
    data=requests.get("https://api.thingspeak.com/channels/2780187/feeds.json?results=2")
    moi=data.json()['feeds'][-1]['field1']
    temp=data.json()['feeds'][-1]['field2']
    hum=data.json()['feeds'][-1]['field3']
    n=data.json()['feeds'][-1]['field4']
    p=data.json()['feeds'][-1]['field5']
    k=data.json()['feeds'][-1]['field6']
    if request.method == 'POST':
        N = request.form['nitrogen']
        P = request.form['phosphorous']
        K = request.form['pottasium']
        ph = request.form['ph']
        rainfall = request.form['rainfall']
        temp = request.form['temperature']
        hum = request.form['humidity']
        data = np.array([[N, P, K, temp, hum, ph, rainfall]])
        my_prediction = cr.predict(data)
        final_prediction = my_prediction[0]
        print(f"{final_prediction}")
        imageDisplay=f"http://127.0.0.1:5000/static/display/{final_prediction}.jpg"

        return render_template('crop.html', p_result=final_prediction,imageDisplay=imageDisplay, dp = getprofile(), name=session['username'])
##        else:
##            return render_template('crop.html', msg="Some thing went wrong, try again")
    
    return render_template('crop.html',moi=moi,temp=temp,hum=hum,n=n,p=p,k=k, dp = getprofile(), name=session['username'])

# --- NEW: SEASON GROW ROUTE (Crop season & harvest advisor) ---
@app.route('/season-grow', methods=['GET', 'POST'])
def season_grow():

    # Safety check: dataset or models missing
    if season_df is None or season_model is None or days_model is None:
        return render_template(
            'seasongrow.html',
            crops=[],
            prediction=None,
            error_msg="Season Grow models or dataset not loaded.",
            crop_defaults=[],            # <-- always send safe empty list
            dp=getprofile(),
            name=session.get('username', '')
        )

    crops = sorted(season_df['crop'].unique())
    prediction = None
    error_msg = None

    if request.method == 'POST':
        crop = request.form.get('crop')

        if not crop:
            error_msg = "Please select a crop."

        else:
            try:
                default_row = season_df[season_df['crop'] == crop].iloc[0]

                temp_val = request.form.get('temp')
                rain_val = request.form.get('rain')
                ph_val = request.form.get('ph')

                temp = float(temp_val) if temp_val else float(default_row['temp_mean'])
                rain = float(rain_val) if rain_val else float(default_row['rain_mean'])
                ph = float(ph_val) if ph_val else float(default_row['ph_mean'])

                X_input = pd.DataFrame(
                    [[crop, temp, rain, ph]],
                    columns=["crop", "temp_mean", "rain_mean", "ph_mean"],
                )

                season_pred = season_model.predict(X_input)[0]
                days_pred = int(round(days_model.predict(X_input)[0]))

                prediction = {
                    "crop": crop,
                    "season_pred": season_pred,
                    "days_pred": days_pred,
                    "sowing_start": default_row["sowing_start"],
                    "sowing_end": default_row["sowing_end"],
                    "harvest_start": default_row["harvest_start"],
                    "harvest_end": default_row["harvest_end"],
                    "soil_type": default_row["soil_type"],
                    "temp_mean": temp,
                    "rain_mean": rain,
                    "ph_mean": ph,
                }

            except Exception as e:
                print("ERROR:", e)
                error_msg = "Prediction failed due to invalid data."

    return render_template(
        'seasongrow.html',
        crops=crops,
        prediction=prediction,
        error_msg=error_msg,
        crop_defaults=season_df.to_dict(orient='records'),   # <-- always valid
        dp=getprofile(),
        name=session.get('username', '')
    )
# ---------------------------------------------------------------

@app.route('/tools')
def tools():
        connection = sqlite3.connect('user_data.db')
        cursor = connection.cursor()

        cursor.execute("select * from tools")
        result = cursor.fetchall()

        if result:
            profile = []
            for row in result:
                profile.append(row[-2])

            return render_template('tools.html', result=result, profile=profile, dp = getprofile(), name=session['username'])
        else:
            return render_template('tools.html', dp = getprofile(), name=session['username'])
        
@app.route('/buyer')
def buyer():
        connection = sqlite3.connect('user_data.db')
        cursor = connection.cursor()

        cursor.execute("select * from seller")
        result = cursor.fetchall()

        if result:
            profile = []
            for row in result:
                profile.append(row[-2])

            return render_template('buyer.html', result=result, profile=profile, dp = getprofile(), name=session['username'])
        else:
            return render_template('buyer.html', dp = getprofile(), name=session['username'])

@app.route('/sell_tool', methods=['POST', 'GET'])
def sell_tool():
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()
    if request.method == 'POST':
        crop = request.form['crop']
        cost = request.form['cost']
        dist = request.form['dist']
        qnt = request.form['qnt']
        file = request.files['file']
        filename = file.filename
        print(filename)
        file_content = file.read()
        File = base64.b64encode(file_content).decode('utf-8')

        connection = sqlite3.connect('user_data.db')
        cursor = connection.cursor()

        cursor.execute("INSERT INTO tools (crop, cost, district, image, quantity) VALUES (?,?,?,?,?)",[crop, cost, dist, File, qnt])
        connection.commit()

        cursor.execute("select * from tools")
        result = cursor.fetchall()

        return render_template('tool.html', msg="data uploaded successfully",result=result, dp = getprofile(), name=session['username'])

    cursor.execute("select * from tools")
    result = cursor.fetchall()
    return render_template('tool.html',result=result, dp = getprofile(), name=session['username'])

@app.route('/sell_crop', methods=['POST', 'GET'])
def sell_crop():
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()
    if request.method == ['POST']:
        crop = request.form['crop']
        cost = request.form['cost']
        dist = request.form['dist']
        qnt = request.form['qnt']
        file = request.files['file']
        filename = file.filename
        print(filename)
        file_content = file.read()
        File = base64.b64encode(file_content).decode('utf-8')

        connection = sqlite3.connect('user_data.db')
        cursor = connection.cursor()

        cursor.execute("INSERT INTO seller (crop, cost, district, image, quantity) VALUES (?,?,?,?,?)",[crop, cost, dist, File, qnt])
        connection.commit()

        cursor.execute("select * from seller")
        result = cursor.fetchall()
        return render_template('seller.html', msg="data uploaded successfully", dp = getprofile(), name=session['username'], result=result)
    cursor.execute("select * from seller")
    result = cursor.fetchall()
    return render_template('seller.html', dp = getprofile(), name=session['username'], result=result)

@app.route('/aweather', methods=['GET', 'POST'])
def aweather():
    if request.method == 'POST':
        try:
            # 1. Capture both District (city) and State (stt)
            district_name = request.form['city']
            state_name = request.form['stt']
            
            # 2. Construct a precise query string for the API (e.g., "Pune, Maharashtra")
            city_query = f"{district_name}, {state_name}"
            
            api_key = config.weather_api_key
            
            # --- API SETUP (WeatherAPI.com) ---
            base_url = "http://api.weatherapi.com/v1/current.json"
            complete_url = f"{base_url}?key={api_key}&q={city_query}"

            response = requests.get(complete_url)
            x = response.json()

            # WeatherAPI.com returns an 'error' object if it fails.
            if "error" not in x:
                # Extract data on success
                city_display = x["location"]["name"] # The API might return a standardized name
                temperature = x["current"]["temp_c"]
                temp_display = f"{temperature}°C"
                sky = x["current"]["condition"]["text"]
                Time = x["location"]["localtime"].split(' ')[1] # Extracts time part only

                return render_template('aweather.html', city=city_display, temp=temp_display, time=Time, sky=sky, dp=getprofile(), name=session['username'])
            else:
                # Handle API error (Invalid Key, City Not Found)
                error_msg = x["error"]["message"]
                return render_template('aweather.html', msg=f"Weather data not found! Error: {error_msg}", dp=getprofile(), name=session['username'])
        
        except requests.exceptions.RequestException:
            return render_template('aweather.html', msg="A network error occurred.", dp=getprofile(), name=session['username'])
        except Exception as e:
            # Catch all other errors
            print(f"An unexpected error occurred in /aweather: {e}")
            return render_template('aweather.html', msg="An unexpected error occurred. Check server logs.", dp=getprofile(), name=session['username'])
    
    return render_template('aweather.html', dp=getprofile(), name=session['username'])


@app.route('/weather', methods=['GET', 'POST'])
def weather():
    if request.method == 'POST':
        try:
            # 1. Capture both District (city) and State (stt)
            district_name = request.form['city']
            state_name = request.form['stt']
            
            # 2. Construct a precise query string for the API (e.g., "Pune, Maharashtra")
            city_query = f"{district_name}, {state_name}"
            
            api_key = config.weather_api_key
            
            # --- API SETUP (WeatherAPI.com) ---
            base_url = "http://api.weatherapi.com/v1/current.json"
            complete_url = f"{base_url}?key={api_key}&q={city_query}"

            response = requests.get(complete_url)
            x = response.json()

            # WeatherAPI.com returns an 'error' object if it fails.
            if "error" not in x:
                # Extract data on success
                city_display = x["location"]["name"] # The API might return a standardized name
                temperature = x["current"]["temp_c"]
                temp_display = f"{temperature}°C"
                sky = x["current"]["condition"]["text"]
                Time = x["location"]["localtime"].split(' ')[1] # Extracts time part only

                return render_template('weather.html', city=city_display, temp=temp_display, time=Time, sky=sky, dp=getprofile(), name=session['username'])
            else:
                # Handle API error (Invalid Key, City Not Found)
                error_msg = x["error"]["message"]
                return render_template('weather.html', msg=f"Weather data not found! Error: {error_msg}", dp=getprofile(), name=session['username'])
        
        except requests.exceptions.RequestException:
            return render_template('weather.html', msg="A network error occurred.", dp=getprofile(), name=session['username'])
        except Exception as e:
            # Catch all other errors
            print(f"An unexpected error occurred in /weather: {e}")
            return render_template('weather.html', msg="An unexpected error occurred. Check server logs.", dp=getprofile(), name=session['username'])
    
    return render_template('weather.html', dp=getprofile(), name=session['username'])

# ... (The rest of app.py including if __name__ == "__main__":)

@app.route('/amarket')
def amarket():
    url = "https://www.napanta.com/market-price/karnataka/bangalore/bangalore/15-dec-2025"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    # Find the table with class "table table-bordered table-striped"
    table = soup.find("table")
    if table:
        result = [['Commodity', 'City', 'Variety', 'Maximum Price', 'Average Price', 'Minimum Price', 'Last Updated On']]
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if cells:
                d = [cell.get_text(strip=True) for cell in cells]
                result.append(d[:-1])
    return render_template('amarket.html', result=result, dp = getprofile(), name=session['username'])

@app.route('/market')
def market():
    url = "https://www.napanta.com/market-price/karnataka/bangalore/bangalore/15-dec-2025"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    # Find the table with class "table table-bordered table-striped"
    table = soup.find("table")
    if table:
        result = [['Commodity', 'City','Variety', 'Maximum Price',  'Average Price', 'Minimum Price', 'Last Updated On']]
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if cells:
                d = [cell.get_text(strip=True) for cell in cells]
                result.append(d[:-1])
    return render_template('market.html', result=result, dp = getprofile(), name=session['username'])

@app.route('/FAQ')
def FAQ():
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()
    cursor.execute("select * from community_query")
    result = cursor.fetchall()
    if result:
        rows = []
        for row in result:
            cursor.execute("select * from community_answer where query_id = '"+str(row[0])+"'")
            result1 = cursor.fetchall()
            if result1:
                    rows.append([row[0], row[1], row[3], "data:image/jpeg;base64,"+row[2], result1])
            else:
                rows.append([row[0], row[1], row[3], "data:image/jpeg;base64,"+row[2], []])
        return render_template('community.html', rows = rows, dp = getprofile(), name=session['username'])
    return render_template('community.html', msg="FAQ not found", dp = getprofile(), name=session['username'])

@app.route('/FAQ1')
def FAQ1():
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()
    cursor.execute("select * from community_query")
    result = cursor.fetchall()
    if result:
        rows = []
        for row in result:
            cursor.execute("select * from community_answer where query_id = '"+str(row[0])+"'")
            result1 = cursor.fetchall()
            if result1:
                    rows.append([row[0], row[1], row[3], "data:image/jpeg;base64,"+row[2], result1])
            else:
                rows.append([row[0], row[1], row[3], "data:image/jpeg;base64,"+row[2], []])
        return render_template('acommunity.html', rows = rows, dp = getprofile(), name=session['username'])
    return render_template('acommunity.html', msg="FAQ not found", dp = getprofile(), name=session['username'])

@app.route('/acommunity', methods=['GET', 'POST'])
def acommunity():
    if request.method == 'POST':
        try:
            file = request.files['file']
            filename = file.filename
            print(filename)
            file_content = file.read()
            File = base64.b64encode(file_content).decode('utf-8')
        except:
            with open('demo.png', 'rb') as file:
                image_data = file.read()
                File = base64.b64encode(image_data).decode('utf-8')
        
        query = request.form['qn']
        connection = sqlite3.connect('user_data.db')
        cursor = connection.cursor()

        cursor.execute("INSERT INTO community_query (username, image, query) VALUES (?,?,?)",[session['username'], File, query])
        connection.commit()

        return redirect(url_for('FAQ1'))
    return redirect(url_for('FAQ1'))

@app.route('/community', methods=['GET', 'POST'])
def community():
    if request.method == 'POST':
        try:
            file = request.files['file']
            filename = file.filename
            print(filename)
            file_content = file.read()
            File = base64.b64encode(file_content).decode('utf-8')
        except:
            with open('demo.png', 'rb') as file:
                image_data = file.read()
                File = base64.b64encode(image_data).decode('utf-8')
        
        query = request.form['qn']
        connection = sqlite3.connect('user_data.db')
        cursor = connection.cursor()

        cursor.execute("INSERT INTO community_query (username, image, query) VALUES (?,?,?)",[session['username'], File, query])
        connection.commit()

        return redirect(url_for('FAQ'))
    return redirect(url_for('FAQ'))

@app.route('/answers', methods=['GET', 'POST'])
def answers():
    if request.method == 'POST':
        ID = request.form['ID']
        ansr = request.form['ansr']

        connection = sqlite3.connect('user_data.db')
        cursor = connection.cursor()
        
        cursor.execute("INSERT INTO community_answer (query_id, username, answer) VALUES (?,?,?)",[ID, session['username'], ansr])
        connection.commit()

        return redirect(url_for('FAQ'))
    return redirect(url_for('FAQ'))

@app.route('/logout')
def logout():
    return render_template('index.html')

@app.route('/Delete/<Id>')
def Delete(Id):
    print(Id)
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()

    cursor.execute("delete from tools where Id = '"+str(Id)+"'")
    connection.commit()

    return redirect(url_for('sell_tool'))

@app.route('/Edit/<Id>')
def Edit(Id):
    print(Id)
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()

    cursor.execute("select * from tools where Id = '"+str(Id)+"'")
    result = cursor.fetchone()
    return render_template('edittool.html', result=result, dp = getprofile(), name=session['username'])

@app.route('/edit_tool', methods=['POST', 'GET'])
def edit_tool():
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()
    if request.method == 'POST':
        Id = request.form['Id']
        crop = request.form['crop']
        cost = request.form['cost']
        dist = request.form['dist']
        qnt = request.form['qnt']
        file = request.files['file']
        filename = file.filename
        print(filename)
        file_content = file.read()
        File = base64.b64encode(file_content).decode('utf-8')

        connection = sqlite3.connect('user_data.db')
        cursor = connection.cursor()

        cursor.execute("update tools set crop = ?, cost = ?, district = ?, image= ?, quantity =? where Id = ?",[crop, cost, dist, File, qnt, Id])
        connection.commit()

        cursor.execute("select * from tools")
        result = cursor.fetchall()

        return render_template('tool.html', msg="data uploaded successfully",result=result, dp = getprofile(), name=session['username'])

    cursor.execute("select * from tools")
    result = cursor.fetchall()
    return render_template('tool.html',result=result, dp = getprofile(), name=session['username'])

@app.route('/Deletecrop/<Id>')
def Deletecrop(Id):
    print(Id)
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()

    cursor.execute("delete from seller where Id = '"+str(Id)+"'")
    connection.commit()

    return redirect(url_for('sell_crop'))

@app.route('/Editcrop/<Id>')
def Editcrop(Id):
    print(Id)
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()

    cursor.execute("select * from seller where Id = '"+str(Id)+"'")
    result = cursor.fetchone()
    return render_template('editcrop.html', result=result, dp = getprofile(), name=session['username'])


@app.route('/edit_crop', methods=['POST', 'GET'])
def edit_crop():
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()
    if request.method == 'POST':
        Id = request.form['Id']
        crop = request.form['crop']
        cost = request.form['cost']
        dist = request.form['dist']
        qnt = request.form['qnt']
        file = request.files['file']
        filename = file.filename
        print(filename)
        file_content = file.read()
        File = base64.b64encode(file_content).decode('utf-8')

        connection = sqlite3.connect('user_data.db')
        cursor = connection.cursor()

        cursor.execute("update seller set crop = ?, cost = ?, district = ?, image= ?, quantity =? where Id = ?",[crop, cost, dist, File, qnt, Id])
        connection.commit()

        cursor.execute("select * from seller")
        result = cursor.fetchall()

        return render_template('seller.html', msg="data uploaded successfully",result=result, dp = getprofile(), name=session['username'])

    cursor.execute("select * from seller")
    result = cursor.fetchall()
    return render_template('seller.html',result=result, dp = getprofile(), name=session['username'])

@app.route('/Buycrop/<Id>')
def Buycrop(Id):
    print(Id)
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()

    cursor.execute("select crop, cost, district, quantity from seller where Id = '"+str(Id)+"'")
    result = cursor.fetchone()

    msg = f" Name: {session['username']}\n Crop : {result[0]}\n cost : {result[1]}\n district: {result[2]}\n quantity: {result[3]}"
    bot = telepot.Bot('8044801915:AAEG-EbSh-1f1m5fFwq4xxX_lZSbUjGhsmQ')
    bot.sendMessage('757000976', str(msg))
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()

    cursor.execute("select * from seller")
    result = cursor.fetchall()

    if result:
        profile = []
        for row in result:
            profile.append(row[-2])

        return render_template('buyer.html',msg=msg, result=result, profile=profile, dp = getprofile(), name=session['username'])
    else:
        return render_template('buyer.html', dp = getprofile(), name=session['username'])

@app.route('/Buytool/<Id>')
def Buytool(Id):
    print(Id)
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()

    cursor.execute("select crop, cost, district, quantity from tools where Id = '"+str(Id)+"'")
    result = cursor.fetchone()
    
    msg = f" Name: {session['username']}\n Tool : {result[0]}\n cost : {result[1]}\n district: {result[2]}\n quantity: {result[3]}"
    # bot = telepot.Bot('8044801915:AAEG-EbSh-1f1m5fFwq4xxX_lZSbUjGhsmQ')
    # bot.sendMessage('757000976', str(msg))
    
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()

    cursor.execute("select * from tools")
    result = cursor.fetchall()

    if result:
        profile = []
        for row in result:
            profile.append(row[-2])

        return render_template('tools.html', result=result, profile=profile, dp = getprofile(), name=session['username'], msg=msg)
    else:
        return render_template('tools.html', dp = getprofile(), name=session['username'])

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
