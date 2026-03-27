import streamlit as st
import urllib.request
import urllib.parse
import http.cookiejar
import re

# --- KONFIGURATION & SESSION ---
st.set_page_config(page_title="SL Parkering", page_icon="🚗")
st.title("🚗 Min Infartsparkering")

# Hämta värden från URL-parametrar (om de finns)
# Exempel: app.py?reg=ABC123&card=9752...
query_params = st.query_params
default_reg = query_params.get("reg", "")
default_card = query_params.get("card", "")

if 'opener' not in st.session_state:
    cj = http.cookiejar.CookieJar()
    st.session_state.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    st.session_state.opener.addheaders = [
        ('User-Agent', 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'),
        ('Origin', 'https://sl.parkera.nu'),
        ('Referer', 'https://sl.parkera.nu/')
    ]

@st.cache_data(ttl=3600) # Cachear listan i en timme för snabbare laddning
def get_stations():
    try:
        response = st.session_state.opener.open("https://sl.parkera.nu/")
        html = response.read().decode('utf-8')
        matches = re.findall(r'<option value="(.*?)">(.*?)</option>', html)
        return {name.strip(): val for val, name in matches if val and "\\" in val}
    except:
        return {"Anslutningsfel - ladda om sidan": ""}

# --- ANVÄNDARGRÄNSSNITT ---
stations_dict = get_stations()
station_names = sorted(list(stations_dict.keys()))

with st.expander("⚙️ Inställningar (Sparas i din länk)", expanded=not default_reg):
    reg_input = st.text_input("Registreringsnummer", value=default_reg, placeholder="t.ex. ABC123").upper()
    card_input = st.text_input("SL-kortsnummer (NU-nummer)", value=default_card, placeholder="9752...")
    
    if st.button("Spara mina uppgifter"):
        # Uppdaterar URL:en så användaren kan bokmärka den
        st.query_params.update(reg=reg_input, card=card_input)
        st.success("Uppgifter sparade i adressfältet! Bokmärk denna sida för att slippa fylla i dem igen.")

selected_station_name = st.selectbox("Välj parkering", options=station_names)

# --- KÖRNING ---
if st.button("🚀 Starta Parkering", use_container_width=True):
    if not reg_input or not card_input:
        st.error("Du måste fylla i både registreringsnummer och kortsnummer.")
    else:
        station_id = stations_dict[selected_station_name]
        
        with st.spinner(f'Aktiverar...'):
            try:
                # Steg 1: Välj Station
                data_1 = urllib.parse.urlencode({"LocalDB": station_id}).encode('utf-8')
                st.session_state.opener.open("https://sl.parkera.nu/?steg=1&ValjInfartsparkering=Ja", data=data_1)

                # Steg 2: Skicka Kort
                data_2 = urllib.parse.urlencode({"SLKort": card_input}).encode('utf-8')
                res2 = st.session_state.opener.open("https://sl.parkera.nu/parkera-med-SL-kort/steg1_Kontrollera-kort0.asp", data=data_2)
                html_2 = res2.read().decode('utf-8')

                if "inte vara aktiverat" in html_2:
                    st.error("❌ Kortet är inte aktiverat (ingen giltig resa hittades).")
                elif "RegNo" in html_2 or "registreringsnummer" in html_2.lower():
                    # Steg 3: Slutför
                    data_3 = urllib.parse.urlencode({"BiljettID": "16", "RegNo": reg_input}).encode('utf-8')
                    res3 = st.session_state.opener.open("https://sl.parkera.nu/?steg=starta-parkering", data=data_3)
                    final_html = res3.read().decode('utf-8')

                    if "Din parkering är startad" in final_html:
                        st.success(f"✅ Parkering startad för {reg_input}!")
                        st.balloons()
                    else:
                        st.warning("⚠️ Kunde inte bekräfta parkering. Kontrollera sl.parkera.nu.")
                else:
                    st.error("❌ Fel vid kontroll av SL-kort.")
            except Exception as e:
                st.error(f"Ett tekniskt fel uppstod: {e}")

st.caption("Tips: Öppna sidan i Safari på iPhone och välj 'Lägg till på hemskärmen'.")
