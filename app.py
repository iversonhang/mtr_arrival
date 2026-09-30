import streamlit as st
import requests
from datetime import datetime

# ==========================================
# 1. 港鐵 (MTR) 數據設定
# ==========================================
MTR_DATA = {
    "AEL": {"name": "機場快綫", "stations": {"HOK": "香港", "KOW": "九龍", "TSY": "青衣", "AIR": "機場", "AWE": "博覽館"}},
    "TCL": {"name": "東涌綫", "stations": {"HOK": "香港", "KOW": "九龍", "OLY": "奧運", "NAC": "南昌", "LAK": "荔景", "TSY": "青衣", "SUN": "欣澳", "TUC": "東涌"}},
    "TML": {"name": "屯馬綫", "stations": {"WKS": "烏溪沙", "MOS": "馬鞍山", "HEO": "恆安", "TSH": "大水坑", "SHM": "石門", "CIO": "第一城", "STW": "沙田圍", "CKT": "車公廟", "TAW": "大圍", "HIK": "顯徑", "DIH": "鑽石山", "KAT": "啟德", "SUW": "宋皇臺", "TKW": "土瓜灣", "HOM": "何文田", "HUH": "紅磡", "ETS": "尖東", "AUS": "柯士甸", "NAC": "南昌", "MEF": "美孚", "TWW": "荃灣西", "KSR": "錦上路", "YUL": "元朗", "LOP": "朗屏", "TIS": "天水圍", "SIH": "兆康", "TUM": "屯門"}},
    "TKL": {"name": "將軍澳綫", "stations": {"NOP": "北角", "QUB": "鰂魚涌", "YAT": "油塘", "TIK": "調景嶺", "TKO": "將軍澳", "LHP": "康城", "HAO": "坑口", "POA": "寶琳"}},
    "EAL": {"name": "東鐵綫", "stations": {"ADM": "金鐘", "EXH": "會展", "HUH": "紅磡", "MKK": "旺角東", "KOT": "九龍塘", "TAW": "大圍", "SHT": "沙田", "FOT": "火炭", "RAC": "馬場", "UNI": "大學", "TAP": "大埔墟", "TWO": "太和", "FAN": "粉嶺", "SHS": "上水", "LOW": "羅湖", "LMC": "落馬洲"}},
    "SIL": {"name": "南港島綫", "stations": {"ADM": "金鐘", "OCP": "海洋公園", "WCH": "黃竹坑", "LET": "利東", "SOH": "海怡半島"}},
    "TWL": {"name": "荃灣綫", "stations": {"CEN": "中環", "ADM": "金鐘", "TST": "尖沙咀", "JOR": "佐敦", "YMT": "油麻地", "MOK": "旺角", "PRE": "太子", "SSP": "深水埗", "CSW": "長沙灣", "LCK": "荔枝角", "MEF": "美孚", "LAK": "荔景", "KWF": "葵芳", "KWH": "葵興", "TWH": "大窩口", "TSW": "荃灣"}},
    "ISL": {"name": "港島綫", "stations": {"KET": "堅尼地城", "HKU": "香港大學", "SYP": "西營盤", "SHW": "上環", "CEN": "中環", "ADM": "金鐘", "WAC": "灣仔", "CAB": "銅鑼灣", "TIH": "天后", "FOH": "炮台山", "NOP": "北角", "QUB": "鰂魚涌", "TAK": "太古", "SWH": "西灣河", "SKW": "筲箕灣", "HFC": "杏花邨", "CHW": "柴灣"}},
    "KTL": {"name": "觀塘綫", "stations": {"WHA": "黃埔", "HOM": "何文田", "YMT": "油麻地", "MOK": "旺角", "PRE": "太子", "SKM": "石硤尾", "KOT": "九龍塘", "LOF": "樂富", "WTS": "黃大仙", "DIH": "鑽石山", "CHH": "彩虹", "KOB": "九龍灣", "NTK": "牛頭角", "KWT": "觀塘", "LAT": "藍田", "YAT": "油塘", "TIK": "調景嶺"}},
    "DRL": {"name": "迪士尼綫", "stations": {"SUN": "欣澳", "DIS": "迪士尼"}}
}

ALL_STATIONS = {}
for line_info in MTR_DATA.values():
    ALL_STATIONS.update(line_info["stations"])

# ==========================================
# 2. API 數據快取函數
# ==========================================
@st.cache_data
def load_bus_metadata():
    base_url = "https://data.etabus.gov.hk/v1/transport/kmb"
    routes = requests.get(f"{base_url}/route").json().get("data", [])
    stops_raw = requests.get(f"{base_url}/stop").json().get("data", [])
    route_stops = requests.get(f"{base_url}/route-stop").json().get("data", [])
    stops_dict = {s["stop"]: {"name_en": s.get("name_en", ""), "name_tc": s.get("name_tc", "")} for s in stops_raw}
    return routes, stops_dict, route_stops

@st.cache_data
def load_ctb_routes():
    url = "https://rt.data.gov.hk/v1/transport/citybus-nwfb/route/ctb"
    return requests.get(url).json().get("data", [])

@st.cache_data
def get_ctb_route_stops(route, direction):
    url = f"https://rt.data.gov.hk/v1/transport/citybus-nwfb/route-stop/ctb/{route}/{direction}"
    route_stops = requests.get(url).json().get("data", [])
    stop_details = {}
    for rs in route_stops:
        stop_id = rs["stop"]
        stop_url = f"https://rt.data.gov.hk/v1/transport/citybus-nwfb/stop/{stop_id}"
        stop_details[stop_id] = requests.get(stop_url).json().get("data", {})
    return route_stops, stop_details

# ==========================================
# 3. 自動刷新模塊 (每 60 秒更新一次)
# ==========================================
@st.fragment(run_every=60)
def render_mtr_eta(selected_line, selected_sta):
    url = f"https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={selected_line}&sta={selected_sta}&lang=tc"
    try:
        data = requests.get(url).json()
        if data.get("status") == 0 or "data" not in data:
            st.warning("目前沒有實時數據（服務可能已暫停）。")
            return

        schedule_data = data["data"].get(f"{selected_line}-{selected_sta}", {})
        if not schedule_data:
            st.info("此車站目前沒有即將到達的列車。")
            return

        col1, col2 = st.columns(2)
        def draw_trains(dir_key, title):
            if dir_key in schedule_data and schedule_data[dir_key]:
                st.markdown(f"**{title}**")
                for train in schedule_data[dir_key]:
                    dest_name = ALL_STATIONS.get(train.get("dest", ""), train.get("dest", ""))
                    ttnt = train.get("ttnt", "0")
                    plat = train.get("plat", "-")
                    arrival_time = train.get("time", "")[-8:-3]
                    st.success(f"**{plat} 號月台** ➔ **{dest_name}**\n\n即將到達： **{ttnt} 分鐘** ({arrival_time})")
            else:
                st.write("沒有列車數據。")

        with col1: draw_trains("UP", "⬆️ 上行列車")
        with col2: draw_trains("DOWN", "⬇️ 下行列車")
        st.caption(f"🔄 最後更新時間：{datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        st.error(f"獲取數據時發生錯誤: {e}")

@st.fragment(run_every=60)
def render_kmb_eta(stop, route, service_type, bound):
    eta_url = f"https://data.etabus.gov.hk/v1/transport/kmb/eta/{stop}/{route}/{service_type}"
    try:
        eta_data = requests.get(eta_url).json().get("data", [])
        eta_data = [eta for eta in eta_data if eta["dir"] == bound]
        
        if not eta_data:
            st.info("目前沒有即將到達的巴士，或服務已暫停。")
        else:
            for eta in eta_data:
                eta_time_str = eta.get("eta")
                rmk = eta.get("rmk_tc", "")
                company = eta.get("co", "KMB/LWB")
                dest = eta.get("dest_tc", "")
                
                if not eta_time_str:
                    st.warning(f"🚍 **公司:** {company} | 狀態: {rmk or '原定班次 (未有實時數據)'}")
                    continue
                
                eta_dt = datetime.fromisoformat(eta_time_str)
                diff_minutes = int((eta_dt - datetime.now(eta_dt.tzinfo)).total_seconds() / 60)
                time_msg = "即將抵達" if diff_minutes <= 0 else f"{diff_minutes} 分鐘"
                
                st.success(f"🚍 **公司:** {company} ➔ **往 {dest}**\n\n即將到達： **{time_msg}** ({eta_dt.strftime('%H:%M')}) {f'- {rmk}' if rmk else ''}")
        st.caption(f"🔄 最後更新時間：{datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        st.error(f"獲取數據時發生錯誤: {e}")

@st.fragment(run_every=60)
def render_ctb_eta(stop, route, dir_code):
    eta_url = f"https://rt.data.gov.hk/v1/transport/citybus-nwfb/eta/ctb/{stop}/{route}"
    try:
        eta_data = requests.get(eta_url).json().get("data", [])
        eta_data = [eta for eta in eta_data if eta.get("dir") == dir_code]
        
        if not eta_data:
            st.info("目前沒有即將到達的巴士。")
        else:
            for eta in eta_data:
                eta_time = eta.get("eta")
                rmk = eta.get("rmk_tc", "")
                dest = eta.get("dest_tc", "")
                
                if not eta_time:
                    st.warning(f"🟡 **狀態:** {rmk or '原定班次 (未有實時數據)'}")
                    continue
                
                eta_dt = datetime.fromisoformat(eta_time)
                diff_mins = int((eta_dt - datetime.now(eta_dt.tzinfo)).total_seconds() / 60)
                time_msg = "即將抵達" if diff_mins <= 0 else f"{diff_mins} 分鐘"
                
                st.success(f"🟡 **往 {dest}**\n\n即將到達： **{time_msg}** ({eta_dt.strftime('%H:%M')}) {f'- {rmk}' if rmk else ''}")
        st.caption(f"🔄 最後更新時間：{datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        st.error(f"獲取數據時發生錯誤: {e}")

# ==========================================
# 4. 主介面佈局
# ==========================================
st.set_page_config(page_title="香港交通實時到站", page_icon="🇭🇰")
st.title("🇭🇰 香港交通實時到站")

tab_mtr, tab_bus, tab_ctb = st.tabs(["🚇 港鐵", "🚌 九巴及龍運", "🟡 城巴"])

# --- 港鐵分頁 ---
with tab_mtr:
    st.subheader("🚇 港鐵下班車")
    line_options = {code: info["name"] for code, info in MTR_DATA.items()}
    sel_line = st.selectbox("選擇港鐵路綫：", options=list(line_options.keys()), format_func=lambda x: f"{line_options[x]}", key="mtr_line")
    
    sta_options = MTR_DATA[sel_line]["stations"]
    sel_sta = st.selectbox("選擇車站：", options=list(sta_options.keys()), format_func=lambda x: f"{sta_options[x]}", key="mtr_sta")
    
    st.divider()
    render_mtr_eta(sel_line, sel_sta)


# --- 九巴/龍運分頁 ---
with tab_bus:
    st.subheader("🚌 九巴及龍運下班車")
    routes, stops_dict, route_stops = load_bus_metadata()

    if routes:
        unique_routes = sorted(list(set([r["route"] for r in routes])))
        sel_route = st.selectbox("1. 選擇巴士路綫：", unique_routes, key="kmb_route")
        
        route_dirs = [r for r in routes if r["route"] == sel_route]
        dir_options = {f"{r['bound']}_{r['service_type']}": f"往 {r['dest_tc']} (常規/特別班次 {r['service_type']})" for r in route_dirs}
        sel_dir = st.selectbox("2. 選擇方向：", options=list(dir_options.keys()), format_func=lambda x: dir_options[x], key="kmb_dir")
        bound, srv_type = sel_dir.split("_")
        
        stops_for_route = sorted([rs for rs in route_stops if rs["route"] == sel_route and rs["bound"] == bound and rs["service_type"] == srv_type], key=lambda x: int(x["seq"]))
        stop_opts = {rs["stop"]: f"{rs['seq']}. {stops_dict.get(rs['stop'], {}).get('name_tc', '未知車站')}" for rs in stops_for_route}
        sel_stop = st.selectbox("3. 選擇車站：", options=list(stop_opts.keys()), format_func=lambda x: stop_opts[x], key="kmb_stop")
        
        st.divider()
        render_kmb_eta(sel_stop, sel_route, srv_type, bound)


# --- 城巴分頁 ---
with tab_ctb:
    st.subheader("🟡 城巴下班車")
    ctb_routes = load_ctb_routes()
    
    if ctb_routes:
        sel_ctb_route = st.selectbox("1. 選擇城巴路綫：", [r["route"] for r in ctb_routes], key="ctb_route_sel")
        
        route_meta = next(r for r in ctb_routes if r["route"] == sel_ctb_route)
        dir_opts = {"outbound": f"往 {route_meta.get('dest_tc', '終點站')}", "inbound": f"往 {route_meta.get('orig_tc', '起點站')}"}
        sel_ctb_dir = st.selectbox("2. 選擇方向：", options=list(dir_opts.keys()), format_func=lambda x: dir_opts[x], key="ctb_dir")
        
        route_stops, stop_details = get_ctb_route_stops(sel_ctb_route, sel_ctb_dir)
        
        if route_stops:
            stop_opts = {rs["stop"]: f"{rs['seq']}. {stop_details.get(rs['stop'], {}).get('name_tc', '未知車站')}" for rs in route_stops}
            sel_ctb_stop = st.selectbox("3. 選擇車站：", options=list(stop_opts.keys()), format_func=lambda x: stop_opts[x], key="ctb_stop")
            
            st.divider()
            dir_code = "O" if sel_ctb_dir == "outbound" else "I"
            render_ctb_eta(sel_ctb_stop, sel_ctb_route, dir_code)
        else:
            st.warning("此方向沒有車站數據。")
