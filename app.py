import streamlit as st
import urllib.request
import urllib.parse
import http.cookiejar
import re

# --- KONFIGURATION & DESIGN ---
st.set_page_config(page_title="SLP - Så Lätt Parkering", page_icon="⚡", layout="centered")

# Custom CSS för Modern Dark Mode och Tibber-inspirerad estetik
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    
    /* Styling för input-fält och rullistor */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #1A1C24 !important;
        color: white !important;
        border: 1px solid #30363D !important;
        border-radius: 10px !important;
    }

    /* Den stora aktiveringsknappen med gradient */
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
        margin-top: 10px;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(168, 85, 247, 0.5);
        color: white;
    }

    /* Footer-styling */
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
    
    /* Expander-styling */
    .stExpander {
        background-color: #1A1C24 !important;
        border: 1px solid #30363D !important;
        border-radius: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ SLP")
st.subheader("Så Lätt Parkering")

# --- BACKEND LOGIK (Session & Scraper) ---
query_params = st.query_params
reg_val = query_params.get("reg", "")
card_val = query_params.get("card", "")
stat_val = query_params.get("station", "")

if 'opener' not in st.session_state:
    cj = http.cookiejar.CookieJar()
    st.session_state.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    # Browser-liknande headers för att undvika blockering
    st.session_state.opener.addheaders = [('User-Agent', 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')]

@st.cache_data(ttl=3600)
def get_stations():
    """Hämtar tillgängliga parkeringar direkt från källan."""
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

# --- ANVÄNDARGRÄNSSNITT ---
with st.expander("⚙️ Inställningar", expanded=not reg_val):
    reg_in = st.text_input("Registreringsnummer", value=reg_val, placeholder="T.ex. ABC 123").upper()
    
    # Placeholder som visar det fasta formatet för SL-kort
    card_in = st.text_input(
        "SL-kortsnummer (19 siffror)", 
        value=card_val, 
        placeholder="(9752 3124) xxx xxxx xxxx"
    )
    
    stat_in = st.selectbox("Din standardparkering", options=names, index=idx)
    
    if st.button("Spara profil & skapa personlig länk"):
        # Uppdatera URL-parametrarna för att baka in datan i länken
        st.query_params.update(reg=reg_in, card=card_in, station=stat_in)
        st.success("✅ Profilen är nu inbäddad i länken!")
        st.info("👉 **VIKTIGT:** För att slippa fylla i detta igen, spara denna sida som ett bokmärke eller välj 'Lägg till på hemskärmen' i din mobil nu.")
        st.balloons()

st.divider()

# Visa aktuell konfiguration om den finns
if reg_in:
    st.markdown(f"**Fordon:** `{reg_in}`  \n**Zon:** `{stat_in}`")

# --- EXEKVERING ---
if st.button("AKTIVERA PARKERING"):
    if not reg_in or not card_in:
        st.error("Gå in under Inställningar och fyll i dina uppgifter först!")
    else:
        # Tvätta kortsnumret från mellanslag innan anrop
        clean_card = card_in.replace(" ", "")
        
        with st.status("Kontaktar SL:s servrar...", expanded=False) as status:
            try:
                # Steg 1: Välj Parkeringsplats
                station_id = stations_dict[stat_in]
                d1 = urllib.parse.urlencode({"LocalDB": station_id}).encode('utf-8')
                st.session_state.opener.open("https://sl.parkera.nu/?steg=1&ValjInfartsparkering=Ja", data=d1)
                
                # Steg 2: Validera SL-kort (NU-nummer)
                d2 = urllib.parse.urlencode({"SLKort": clean_card}).encode('utf-8')
                res2 = st.session_state.opener.open("https://sl.parkera.nu/parkera-med-SL-kort/steg1_Kontrollera-kort0.asp", data=d2)
                h2 = res2.read().decode('utf-8')

                if "inte vara aktiverat" in h2:
                    status.update(label="Kortet ej aktiverat! (Ingen giltig resa hittades)", state="error")
                elif "RegNo" in h2 or "registreringsnummer" in h2.lower():
                    # Steg 3: Slutför parkeringen (24h gratisbiljett ID 16)
                    d3 = urllib.parse.urlencode({"BiljettID": "16", "RegNo": reg_in}).encode('utf-8')
                    res3 = st.session_state.opener.open("https://sl.parkera.nu/?steg=starta-parkering", data=d3)
                    h3 = res3.read().decode('utf-8')

                    if "Din parkering är startad" in h3 or "parkering är giltig" in h3:
                        status.update(label="Parkering Aktiverad! ✅", state="complete")
                        st.toast("Trevlig resa!", icon="🚀")
                    else:
                        status.update(label="Kunde inte bekräfta aktivering.", state="error")
                        st.warning("Logga in på sl.parkera.nu för att kontrollera status.")
                else:
                    status.update(label="SL-kortet nekades av systemet.", state="error")
            except Exception as e:
                status.update(label=f"Ett tekniskt fel uppstod: {e}", state="error")

# Padding för att innehållet inte ska döljas av footern
st.write("\n" * 5)

# --- FOOTER ---
st.markdown(f"""
    <div class="footer">
        SLP av <a href="mailto:infartsparkering@magnerholt.com">Magnerholt</a><br>
        Elbil? <a href="https://invite.tibber.com/onc1s3yl" target="_blank">Skaffa Tibber!</a>
    </div>
    """, unsafe_allow_html=True)
