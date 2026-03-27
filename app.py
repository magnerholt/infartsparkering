import streamlit as st
import urllib.request
import urllib.parse
import http.cookiejar
import re

# --- MODERN DARK DESIGN ---
st.set_page_config(page_title="P-App", page_icon="🌙", layout="centered")

# Custom CSS för mörkt tema och snygga knappar
st.markdown("""
    <style>
    /* Bakgrund och text */
    .stApp {
        background-color: #0E1117;
        color: #FFFFFF;
    }
    
    /* Input-fält */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #1A1C24 !important;
        color: white !important;
        border: 1px solid #30363D !important;
        border-radius: 8px !important;
    }

    /* Den stora knappen */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%); /* Snygg gradient */
        color: white;
        border: none;
        font-weight: 700;
        font-size: 18px;
        letter-spacing: 1px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(168, 85, 247, 0.4);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(168, 85, 247, 0.6);
        color: white;
    }

    /* Expander */
    .stExpander {
        background-color: #1A1C24 !important;
        border: 1px solid #30363D !important;
        border-radius: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Snabbparkering")
st.caption("Enkel aktivering av infartsparkering")

# --- LOGIK & SETUP ---
query_params = st.query_params
default_reg = query_params.get("reg", "")
default_card = query_params.get("card", "")
default_station = query_params.get("station", "")

if 'opener' not in st.session_state:
    cj = http.cookiejar.CookieJar()
    st.session_state.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    st.session_state.opener.addheaders = [
        ('User-Agent', 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
    ]

@st.cache_data(ttl=3600)
def get_stations():
    try:
        response = st.session_state.opener.open("https://sl.parkera.nu/")
        html = response.read().decode('utf-8')
        matches = re.findall(r'<option value="(.*?)">(.*?)</option>', html)
        return {name.strip(): val for val, name in matches if val and "\\" in val}
    except:
        return {"Kunde inte hämta lista": ""}

stations_dict = get_stations()
station_names = sorted(list(stations_dict.keys()))
default_index = station_names.index(default_station) if default_station in station_names else 0

# --- GRÄNSSNITT ---
with st.expander("👤 Profil & Inställningar", expanded=not default_reg):
    reg_input = st.text_input("Registreringsnummer", value=default_reg).upper()
    card_input = st.text_input("SL-kortsnummer", value=default_card)
    selected_station_name = st.selectbox("Standardparkering", options=station_names, index=default_index)
    
    if st.button("Spara Profil"):
        st.query_params.update(reg=reg_input, card=card_input, station=selected_station_name)
        st.toast("Profil sparad i URLen!", icon="💾")

st.write("---")

if default_reg:
    st.markdown(f"**Fordon:** `{reg_input}`  \n**Plats:** `{selected_station_name}`")
else:
    st.info("Börja med att fylla i din profil ovan.")

# Huvudknappen
if st.button("AKTIVERA PARKERING"):
    if not reg_input or not card_input:
        st.error("Fyll i profilen först!")
    else:
        with st.status("Kopplar upp mot SL...", expanded=True) as status:
            try:
                # Steg 1
                station_id = stations_dict[selected_station_name]
                data_1 = urllib.parse.urlencode({"LocalDB": station_id}).encode('utf-8')
                st.session_state.opener.open("https://sl.parkera.nu/?steg=1&ValjInfartsparkering=Ja", data=data_1)
                
                # Steg 2
                data_2 = urllib.parse.urlencode({"SLKort": card_input}).encode('utf-8')
                res2 = st.session_state.opener.open("https://sl.parkera.nu/parkera-med-SL-kort/steg1_Kontrollera-kort0.asp", data=data_2)
                html_2 = res2.read().decode('utf-8')

                if "inte vara aktiverat" in html_2:
                    status.update(label="Kortet ej aktiverat!", state="error")
                elif "RegNo" in html_2 or "registreringsnummer" in html_2.lower():
                    # Steg 3
                    data_3 = urllib.parse.urlencode({"BiljettID": "16", "RegNo": reg_input}).encode('utf-8')
                    res3 = st.session_state.opener.open("https://sl.parkera.nu/?steg=starta-parkering", data=data_3)
                    final_html = res3.read().decode('utf-8')

                    if "Din parkering är startad" in final_html:
                        status.update(label="Parkering Aktiverad!", state="complete")
                        st.balloons()
                    else:
                        status.update(label="Kunde inte bekräfta.", state="error")
                else:
                    status.update(label="SL-kort nekades.", state="error")
            except Exception as e:
                status.update(label=f"Fel: {e}", state="error")
