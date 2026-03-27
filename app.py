import streamlit as st
import urllib.request
import urllib.parse
import http.cookiejar
import re

# --- CONFIG & THEME ---
st.set_page_config(page_title="SLP - Så Lätt Parkering", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    
    /* Input styling */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #1A1C24 !important;
        color: white !important;
        border: 1px solid #30363D !important;
        border-radius: 10px !important;
    }

    /* Tibber-ish Purple/Electric Gradient Button */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.8em;
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        color: white;
        border: none;
        font-weight: 700;
        font-size: 1.1rem;
        box-shadow: 0 4px 15px rgba(168, 85, 247, 0.3);
        transition: 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(168, 85, 247, 0.5);
    }

    /* Footer */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #0E1117;
        color: #888;
        text-align: center;
        padding: 15px;
        font-size: 0.8rem;
        border-top: 1px solid #30363D;
        z-index: 100;
    }
    .footer a { color: #a855f7; text-decoration: none; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ SLP")
st.subheader("Så Lätt Parkering")

# --- BACKEND ---
query_params = st.query_params
reg_val = query_params.get("reg", "")
card_val = query_params.get("card", "")
stat_val = query_params.get("station", "")

if 'opener' not in st.session_state:
    cj = http.cookiejar.CookieJar()
    st.session_state.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    st.session_state.opener.addheaders = [('User-Agent', 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')]

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
names = sorted(list(stations_dict.keys()))
idx = names.index(stat_val) if stat_val in names else 0

# --- INTERFACE ---
with st.expander("⚙️ Inställningar", expanded=not reg_val):
    reg_in = st.text_input("Registreringsnummer", value=reg_val, placeholder="T.ex. ABC 123").upper()
    card_in = st.text_input("SL-kortsnummer", value=card_val, placeholder="9752 3124 xxxx xxxx xxx")
    stat_in = st.selectbox("Din parkering", options=names, index=idx)
    
    if st.button("Spara profil & länk"):
        st.query_params.update(reg=reg_in, card=card_in, station=stat_in)
        st.toast("Profil sparad!", icon="💾")

st.divider()

if reg_in:
    st.markdown(f"**Bil:** `{reg_in}`  \n**Plats:** `{stat_in}`")

if st.button("AKTIVERA PARKERING"):
    if not reg_in or not card_in:
        st.error("Gå till Inställningar först!")
    else:
        clean_c = card_in.replace(" ", "")
        with st.status("Kontaktar SL...", expanded=False) as status:
            try:
                # Step 1: Selecting Station
                d1 = urllib.parse.urlencode({"LocalDB": stations_dict[stat_in]}).encode()
                st.session_state.opener.open("https://sl.parkera.nu/?steg=1&ValjInfartsparkering=Ja", data=d1)
                
                # Step 2: Validating Card
                d2 = urllib.parse.urlencode({"SLKort": clean_c}).encode()
                res2 = st.session_state.opener.open("https://sl.parkera.nu/parkera-med-SL-kort/steg1_Kontrollera-kort0.asp", data=d2)
                h2 = res2.read().decode()

                if "inte vara aktiverat" in h2:
                    status.update(label="Kortet ej aktiverat!", state="error")
                elif "RegNo" in h2:
                    # Step 3: Finalizing
                    d3 = urllib.parse.urlencode({"BiljettID": "16", "RegNo": reg_in}).encode()
                    res3 = st.session_state.opener.open("https://sl.parkera.nu/?steg=starta-parkering", data=d3)
                    h3 = res3.read().decode()

                    if "Din parkering är startad" in h3 or "parkering är giltig" in h3:
                        status.update(label="Parkering Aktiverad!", state="complete")
                        st.balloons()
                    else:
                        status.update(label="Bekräftelse saknas.", state="error")
                else:
                    status.update(label="SL-kortet nekades.", state="error")
            except Exception as e:
                status.update(label=f"Fel: {e}", state="error")

st.write("\n" * 4) # Bottom padding

# --- FOOTER ---
st.markdown(f"""
    <div class="footer">
        SLP av <a href="mailto:infartparkering@magnerholt.com">Magnerholt</a><br>
        Elbil? <a href="https://invite.tibber.com/onc1s3yl" target="_blank">Skaffa Tibber!</a>
    </div>
    """, unsafe_allow_html=True)
