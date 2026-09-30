import streamlit as st
import requests
from datetime import datetime

# ==========================================
# 1. MTR Data Configuration
# ==========================================
MTR_DATA = {
    "AEL": {"name": "Airport Express", "stations": {"HOK": "Hong Kong", "KOW": "Kowloon", "TSY": "Tsing Yi", "AIR": "Airport", "AWE": "AsiaWorld-Expo"}},
    "TCL": {"name": "Tung Chung Line", "stations": {"HOK": "Hong Kong", "KOW": "Kowloon", "OLY": "Olympic", "NAC": "Nam Cheong", "LAK": "Lai King", "TSY": "Tsing Yi", "SUN": "Sunny Bay", "TUC": "Tung Chung"}},
    "TML": {"name": "Tuen Ma Line", "stations": {"WKS": "Wu Kai Sha", "MOS": "Ma On Shan", "HEO": "Heng On", "TSH": "Tai Shui Hang", "SHM": "Shek Mun", "CIO": "City One", "STW": "Sha Tin Wai", "CKT": "Che Kung Temple", "TAW": "Tai Wai", "HIK": "Hin Keng", "DIH": "Diamond Hill", "KAT": "Kai Tak", "SUW": "Sung Wong Toi", "TKW": "To Kwa Wan", "HOM": "Ho Man Tin", "HUH": "Hung Hom", "ETS": "East Tsim Sha Tsui", "AUS": "Austin", "NAC": "Nam Cheong", "MEF": "Mei Foo", "TWW": "Tsuen Wan West", "KSR": "Kam Sheung Road", "YUL": "Yuen Long", "LOP": "Long Ping", "TIS": "Tin Shui Wai", "SIH": "Siu Hong", "TUM": "Tuen Mun"}},
    "TKL": {"name": "Tseung Kwan O Line", "stations": {"NOP": "North Point", "QUB": "Quarry Bay", "YAT": "Yau Tong", "TIK": "Tiu Keng Leng", "TKO": "Tseung Kwan O", "LHP": "LOHAS Park", "HAO": "Hang Hau", "POA": "Po Lam"}},
    "EAL": {"name": "East Rail Line", "stations": {"ADM": "Admiralty", "EXH": "Exhibition Centre", "HUH": "Hung Hom", "MKK": "Mong Kok East", "KOT": "Kowloon Tong", "TAW": "Tai Wai", "SHT": "Sha Tin", "FOT": "Fo Tan", "RAC": "Racecourse", "UNI": "University", "TAP": "Tai Po Market", "TWO": "Tai Wo", "FAN": "Fanling", "SHS": "Sheung Shui", "LOW": "Lo Wu", "LMC": "Lok Ma Chau"}},
    "SIL": {"name": "South Island Line", "stations": {"ADM": "Admiralty", "OCP": "Ocean Park", "WCH": "Wong Chuk Hang", "LET": "Lei Tung", "SOH": "South Horizons"}},
    "TWL": {"name": "Tsuen Wan Line", "stations": {"CEN": "Central", "ADM": "Admiralty", "TST": "Tsim Sha Tsui", "JOR": "Jordan", "YMT": "Yau Ma Tei", "MOK": "Mong Kok", "PRE": "Prince Edward", "SSP": "Sham Shui Po", "CSW": "Cheung Sha Wan", "LCK": "Lai Chi Kok", "MEF": "Mei Foo", "LAK": "Lai King", "KWF": "Kwai Fong", "KWH": "Kwai Hing", "TWH": "Tai Wo Hau", "TSW": "Tsuen Wan"}},
    "ISL": {"name": "Island Line", "stations": {"KET": "Kennedy Town", "HKU": "HKU", "SYP": "Sai Ying Pun", "SHW": "Sheung Wan", "CEN": "Central", "ADM": "Admiralty", "WAC": "Wan Chai", "CAB": "Causeway Bay", "TIH": "Tin Hau", "FOH": "Fortress Hill", "NOP": "North Point", "QUB": "Quarry Bay", "TAK": "Tai Koo", "SWH": "Sai Wan Ho", "SKW": "Shau Kei Wan", "HFC": "Heng Fa Chuen", "CHW": "Chai Wan"}},
    "KTL": {"name": "Kwun Tong Line", "stations": {"WHA": "Whampoa", "HOM": "Ho Man Tin", "YMT": "Yau Ma Tei", "MOK": "Mong Kok", "PRE": "Prince Edward", "SKM": "Shek Kip Mei", "KOT": "Kowloon Tong", "LOF": "Lok Fu", "WTS": "Wong Tai Sin", "DIH": "Diamond Hill", "CHH": "Choi Hung", "KOB": "Kowloon Bay", "NTK": "Ngau Tau Kok", "KWT": "Kwun Tong", "LAT": "Lam Tin", "YAT": "Yau Tong", "TIK": "Tiu Keng Leng"}},
    "DRL": {"name": "Disneyland Resort Line", "stations": {"SUN": "Sunny Bay", "DIS": "Disneyland Resort"}}
}

ALL_STATIONS = {}
for line_info in MTR_DATA.values():
    ALL_STATIONS.update(line_info["stations"])


# ==========================================
# 2. Bus Data Caching Logic (KMB & LWB)
# ==========================================
@st.cache_data
def load_bus_metadata():
    """
    Downloads the master lists of routes, stops, and mappings.
    @st.cache_data ensures this only runs once per server start to speed up the app.
    """
    base_url = "https://data.etabus.gov.hk/v1/transport/kmb"
    routes = requests.get(f"{base_url}/route").json().get("data", [])
    stops_raw = requests.get(f"{base_url}/stop").json().get("data", [])
    route_stops = requests.get(f"{base_url}/route-stop").json().get("data", [])
    
    # Map stop IDs to their English and Chinese names
    stops_dict = {
        s["stop"]: {"name_en": s.get("name_en", ""), "name_tc": s.get("name_tc", "")} 
        for s in stops_raw
    }
    return routes, stops_dict, route_stops

# ==========================================
# 3. Main Application Layout
# ==========================================
st.set_page_config(page_title="HK Transit Arrivals", page_icon="🇭🇰")
st.title("🇭🇰 HK Transit Real-Time Arrivals")

# Create the Tabs
tab_mtr, tab_bus = st.tabs(["🚇 MTR", "🚌 KMB & LWB Bus"])

# --- MTR TAB ---
with tab_mtr:
    st.subheader("MTR Next Train")
    line_options = {code: info["name"] for code, info in MTR_DATA.items()}
    selected_line = st.selectbox("Select MTR Line:", options=list(line_options.keys()), format_func=lambda x: f"{line_options[x]} ({x})")

    station_options = MTR_DATA[selected_line]["stations"]
    selected_sta = st.selectbox("Select Station:", options=list(station_options.keys()), format_func=lambda x: f"{station_options[x]} ({x})")

    if st.button("Get Train Arrivals", type="primary", key="mtr_btn"):
        url = f"https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={selected_line}&sta={selected_sta}&lang=en"
        
        with st.spinner("Fetching MTR data..."):
            try:
                response = requests.get(url)
                data = response.json()
                if data.get("status") == 0 or "data" not in data:
                    st.warning("No real-time data available right now.")
                else:
                    schedule_key = f"{selected_line}-{selected_sta}"
                    schedule_data = data["data"].get(schedule_key, {})
                    
                    if not schedule_data:
                        st.info("No upcoming trains found for this station.")
                    
                    col1, col2 = st.columns(2)
                    def render_trains(direction_key, title):
                        if direction_key in schedule_data and schedule_data[direction_key]:
                            st.markdown(f"**{title}**")
                            for train in schedule_data[direction_key]:
                                dest_code = train.get("dest", "")
                                dest_name = ALL_STATIONS.get(dest_code, dest_code)
                                ttnt = train.get("ttnt", "0")
                                plat = train.get("plat", "-")
                                arrival_time = train.get("time", "")[-8:-3]
                                st.success(f"**Platform {plat}** ➔ **{dest_name}**\n\nArriving in: **{ttnt} min** ({arrival_time})")
                        else:
                            st.write(f"No {direction_key.lower()}bound data.")

                    with col1: render_trains("UP", "⬆️ Upbound (UP)")
                    with col2: render_trains("DOWN", "⬇️ Downbound (DOWN)")
            except Exception as e:
                st.error(f"Error fetching data: {e}")


# --- BUS TAB ---
with tab_bus:
    st.subheader("KMB & LWB Next Bus")
    
    with st.spinner("Loading bus routes and stops (this takes a few seconds on first load)..."):
        routes, stops_dict, route_stops = load_bus_metadata()

    if not routes:
        st.error("Failed to load bus metadata from the API.")
    else:
        # Step 1: Select Bus Route (KMB + LWB)
        unique_routes = sorted(list(set([r["route"] for r in routes])))
        selected_bus_route = st.selectbox("1. Select Bus Route:", unique_routes)
        
        # Step 2: Select Direction
        route_directions = [r for r in routes if r["route"] == selected_bus_route]
        dir_options = {
            f"{r['bound']}_{r['service_type']}": f"To {r['dest_en']} (Service Type {r['service_type']})" 
            for r in route_directions
        }
        selected_bus_dir = st.selectbox("2. Select Direction:", options=list(dir_options.keys()), format_func=lambda x: dir_options[x])
        bound, service_type = selected_bus_dir.split("_")
        
        # Step 3: Select Stop
        stops_for_route = [rs for rs in route_stops if rs["route"] == selected_bus_route and rs["bound"] == bound and rs["service_type"] == service_type]
        stops_for_route = sorted(stops_for_route, key=lambda x: int(x["seq"]))
        
        stop_options = {
            rs["stop"]: f"{rs['seq']}. {stops_dict.get(rs['stop'], {}).get('name_en', 'Unknown')} - {stops_dict.get(rs['stop'], {}).get('name_tc', '')}" 
            for rs in stops_for_route
        }
        selected_bus_stop = st.selectbox("3. Select Stop:", options=list(stop_options.keys()), format_func=lambda x: stop_options[x])
        
        # Step 4: Fetch ETA
        if st.button("Get Bus ETA", type="primary", key="bus_btn"):
            eta_url = f"https://data.etabus.gov.hk/v1/transport/kmb/eta/{selected_bus_stop}/{selected_bus_route}/{service_type}"
            
            with st.spinner("Fetching live bus ETA..."):
                try:
                    eta_resp = requests.get(eta_url).json()
                    eta_data = eta_resp.get("data", [])
                    # Filter data strictly for the selected direction
                    eta_data = [eta for eta in eta_data if eta["dir"] == bound]
                    
                    if not eta_data:
                        st.info("No upcoming buses found or service is currently suspended.")
                    else:
                        for eta in eta_data:
                            eta_time_str = eta.get("eta")
                            rmk = eta.get("rmk_en", "")
                            company = eta.get("co", "KMB/LWB")
                            
                            # Handle scheduled buses that don't have a GPS connection yet
                            if not eta_time_str:
                                st.warning(f"🚍 **Company:** {company} | Status: {rmk or 'Scheduled (No real-time info yet)'}")
                                continue
                            
                            # Calculate time difference
                            eta_dt = datetime.fromisoformat(eta_time_str)
                            now = datetime.now(eta_dt.tzinfo)
                            diff_minutes = int((eta_dt - now).total_seconds() / 60)
                            
                            if diff_minutes <= 0:
                                time_msg = "Arriving now"
                            else:
                                time_msg = f"In {diff_minutes} min"
                                
                            arrival_time_formatted = eta_dt.strftime('%H:%M')
                            
                            st.success(f"🚍 **Company:** {company} ➔ **To {eta.get('dest_en')}**\n\nArriving: **{time_msg}** ({arrival_time_formatted}) {f'- {rmk}' if rmk else ''}")
                except Exception as e:
                    st.error(f"Error fetching ETA: {e}")
