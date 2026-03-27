import streamlit as st
import urllib.request
import urllib.parse
import http.cookiejar
import re

# --- SETUP ---
st.set_page_config(page_title="SL Parkering", page_icon="🚗")
st.title("🚗 Smart Parkering")

# Skapa en session (CookieJar) som lever under hela körningen
if 'opener' not in st.session_state:
    cj = http.cookiejar.CookieJar()
    st.session_state.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    st.session_state.opener.addheaders = [
        ('User-Agent', 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'),
        ('Origin', 'https://sl.parkera.nu'),
        ('Referer', 'https://sl.parkera.nu/')
    ]

def get_stations():
    """Hämtar alla tillgängliga parkeringar från rullistan på hemsidan."""
    try:
        response = st.session_state.opener.open("https://sl.parkera.nu/")
        html = response.read().decode('utf-8')
        # Sök efter alla <option value="...">Namn</option>
        matches = re.findall(r'<option value="(.*?)">(.*?)</option>', html)
        # Filtrera bort tomma eller ogiltiga val
        stations = {name.strip(): val for val, name in matches if val and "\\" in val}
        return stations
    except Exception as e:
        st.error(f"Kunde inte hämta parkeringslista: {e}")
        return {"Tumba (Default)": r"Infartsparkeringar\Botkyrka-kommun\Tumba"}

# --- UI / INPUTS ---
stations_dict = get_stations()
station_names = sorted(list(stations_dict.keys()))

# Kom ihåg valda värden i session_state
selected_station_name = st.selectbox("Välj parkering", options=station_names)
reg_number = st.text_input("Registreringsnummer", value=st.session_state.get('reg', 'FTX466')).upper()
nu_number = st.text_input("SL-kortsnummer (NU-nummer)", value=st.session_state.get('card', '9752312497411665613'))

# Spara till session_state
st.session_state['reg'] = reg_number
st.session_state['card'] = nu_number

if st.button("🚀 Starta Parkering", use_container_width=True):
    station_id = stations_dict[selected_station_name]
    
    with st.spinner(f'Aktiverar parkering i {selected_station_name}...'):
        try:
            # Steg 1: Välj Station
            data_1 = urllib.parse.urlencode({"LocalDB": station_id}).encode('utf-8')
            st.session_state.opener.open("https://sl.parkera.nu/?steg=1&ValjInfartsparkering=Ja", data=data_1)

            # Steg 2: Skicka Kort
            data_2 = urllib.parse.urlencode({"SLKort": nu_number}).encode('utf-8')
            res2 = st.session_state.opener.open("https://sl.parkera.nu/parkera-med-SL-kort/steg1_Kontrollera-kort0.asp", data=data_2)
            html_2 = res2.read().decode('utf-8')

            if "inte vara aktiverat" in html_2:
                st.error("❌ Kortet är inte aktiverat (ingen resa hittades på kortet).")
            elif "RegNo" in html_2 or "registreringsnummer" in html_2.lower():
                # Steg 3: Slutför
                data_3 = urllib.parse.urlencode({"BiljettID": "16", "RegNo": reg_number}).encode('utf-8')
                res3 = st.session_state.opener.open("https://sl.parkera.nu/?steg=starta-parkering", data=data_3)
                final_html = res3.read().decode('utf-8')

                if "Din parkering är startad" in final_html or "parkering är giltig" in final_html:
                    st.success(f"✅ Klart! Parkering startad för {reg_number} i {selected_station_name}.")
                    st.balloons()
                else:
                    st.warning("⚠️ Hittade inte bekräftelsemeddelandet. Logga in på sl.parkera.nu och kolla.")
            else:
                st.error("❌ Okänt fel vid kortkontroll.")
        
        except Exception as e:
            st.error(f"Tekniskt fel: {e}")

st.divider()
st.caption("Denna app laddar inte ner något till din telefon. Den körs helt i webbläsaren.")
