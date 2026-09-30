import streamlit as st
import requests

# 1. MTR Line and Station Mappings
# The API requires specific 3-letter codes for lines and stations.
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

# Create a master dictionary for looking up destination full names dynamically
ALL_STATIONS = {}
for line_info in MTR_DATA.values():
    ALL_STATIONS.update(line_info["stations"])

st.set_page_config(page_title="MTR Real-Time Arrivals", page_icon="🚇")
st.title("🚇 MTR Real-Time Arrivals")

# 2. UI for Line and Station Selection
line_options = {code: info["name"] for code, info in MTR_DATA.items()}
selected_line = st.selectbox("Select MTR Line:", options=list(line_options.keys()), format_func=lambda x: f"{line_options[x]} ({x})")

station_options = MTR_DATA[selected_line]["stations"]
selected_sta = st.selectbox("Select Station:", options=list(station_options.keys()), format_func=lambda x: f"{station_options[x]} ({x})")

# 3. Fetch Data
if st.button("Get Arrival Times", type="primary"):
    # The API endpoint for MTR Next Train
    url = f"https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={selected_line}&sta={selected_sta}&lang=en"
    
    with st.spinner("Fetching real-time data..."):
        try:
            response = requests.get(url)
            data = response.json()
            
            # The API returns status 0 if there's no data or train service is suspended
            if data.get("status") == 0 or "data" not in data:
                st.warning("No real-time data available right now (Service might be suspended or closed).")
            else:
                schedule_key = f"{selected_line}-{selected_sta}"
                schedule_data = data["data"].get(schedule_key, {})
                
                if not schedule_data:
                    st.info("No upcoming trains found for this station.")
                
                col1, col2 = st.columns(2)
                
                def render_trains(direction_key, title):
                    if direction_key in schedule_data and schedule_data[direction_key]:
                        st.subheader(title)
                        for train in schedule_data[direction_key]:
                            dest_code = train.get("dest", "")
                            dest_name = ALL_STATIONS.get(dest_code, dest_code)
                            ttnt = train.get("ttnt", "0")
                            plat = train.get("plat", "-")
                            arrival_time = train.get("time", "")[-8:-3] # Extract HH:mm
                            
                            st.success(f"**Platform {plat}** ➔ **{dest_name}**\n\nArriving in: **{ttnt} min** ({arrival_time})")
                    else:
                        st.write(f"No {direction_key.lower()}bound data.")

                with col1:
                    render_trains("UP", "⬆️ Upbound (UP)")
                with col2:
                    render_trains("DOWN", "⬇️ Downbound (DOWN)")
                    
        except Exception as e:
            st.error(f"Error fetching data: {e}")
