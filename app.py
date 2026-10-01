import streamlit as st
import requests
from datetime import datetime, timedelta
import math
from streamlit_geolocation import streamlit_geolocation
import extra_streamlit_components as stx
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

MIRROR_BASE = "https://winstonma.github.io/MMM-HK-Transport-ETA-Data"
REQUEST_TIMEOUT = 15

@st.cache_resource
def get_session():
    retry = Retry(total=3, connect=3, read=3, status=3, backoff_factor=0.5,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset(["GET"]), raise_on_status=False)
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter); session.mount("http://", adapter)
    return session

def get_json(url):
    response = get_session().get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status(); return response.json()

def as_list(payload):
    if isinstance(payload, list): return payload
    if isinstance(payload, dict):
        data = payload.get("data", payload)
        if isinstance(data, list): return data
        if isinstance(data, dict): return [v for v in data.values() if isinstance(v, dict)]
    return []

# ==========================================
# 0. 輔助函數：計算 GPS 距離 (Haversine formula)
# ==========================================
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000 # 地球半徑 (米)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c # 回傳距離 (米)

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
@st.cache_data(ttl=86400, show_spinner="正在下載九巴及龍運資料...")
def load_bus_metadata():
    stops_raw = as_list(get_json(f"{MIRROR_BASE}/kmb/stops/allstops.json"))
    stops_dict = {}
    for item in stops_raw:
        stop_id = item.get("stop") or item.get("stop_id") or item.get("id")
        if stop_id:
            stops_dict[str(stop_id)] = {**item,
                "name_tc": item.get("name_tc") or item.get("name_zh") or item.get("name") or "未知車站",
                "lat": float(item.get("lat") or item.get("latitude") or 0),
                "lon": float(item.get("long") or item.get("lon") or item.get("longitude") or 0),
                "routes": item.get("routes") or []}
    try:
        routes = get_json("https://data.etabus.gov.hk/v1/transport/kmb/route").get("data", [])
    except (requests.RequestException, ValueError):
        numbers = sorted({str(r) for stop in stops_dict.values() for r in stop.get("routes", [])})
        routes = [{"route": r, "bound": b, "service_type": "1", "dest_tc": "請選擇方向"} for r in numbers for b in ("O","I")]
    return routes, stops_dict

@st.cache_data(ttl=3600, show_spinner=False)
def get_kmb_route_stops(route, bound, service_type):
    direction = "outbound" if bound == "O" else "inbound"
    for url in (f"https://data.etabus.gov.hk/v1/transport/kmb/route-stop/{route}/{direction}/{service_type}",
                f"https://data.etabus.gov.hk/v1/transport/kmb/route-stop/{route}/{bound}/{service_type}"):
        try:
            rows = get_json(url).get("data", [])
            if rows: return rows
        except (requests.RequestException, ValueError): pass
    return []

@st.cache_data(ttl=86400, show_spinner=False)
def get_kmb_stop(stop_id):
    stop = load_bus_metadata()[1].get(stop_id)
    if stop: return stop
    try: return get_json(f"{MIRROR_BASE}/kmb/stops/{stop_id}.json")
    except (requests.RequestException, ValueError): return {}

@st.cache_data(ttl=86400)
def load_ctb_routes():
    return get_json("https://rt.data.gov.hk/v1/transport/citybus-nwfb/route/ctb").get("data", [])

@st.cache_data(ttl=86400, show_spinner=False)
def get_ctb_stop(stop_id):
    return get_json(f"https://rt.data.gov.hk/v1/transport/citybus-nwfb/stop/{stop_id}").get("data", {})

@st.cache_data(ttl=3600)
def get_ctb_route_stops(route, direction):
    rows = get_json(f"https://rt.data.gov.hk/v1/transport/citybus-nwfb/route-stop/ctb/{route}/{direction}").get("data", [])
    return rows, {r["stop"]: get_ctb_stop(r["stop"]) for r in rows if r.get("stop")}


# ==========================================
# 3. 自動刷新模塊 (每 60 秒更新一次)
# ==========================================
@st.fragment(run_every=60)
def render_mtr_eta(selected_line, selected_sta):
    url = f"https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={selected_line}&sta={selected_sta}&lang=tc"
    try:
        data = get_json(url)
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
        eta_data = get_json(eta_url).get("data", [])
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
                    st.warning(f"🚍 **路線:** {route} ({company}) | 狀態: {rmk or '原定班次 (未有實時數據)'}")
                    continue
                
                eta_dt = datetime.fromisoformat(eta_time_str)
                diff_minutes = int((eta_dt - datetime.now(eta_dt.tzinfo)).total_seconds() / 60)
                time_msg = "即將抵達" if diff_minutes <= 0 else f"{diff_minutes} 分鐘"
                
                st.success(f"🚍 **路線 {route}** ({company}) ➔ **往 {dest}**\n\n即將到達： **{time_msg}** ({eta_dt.strftime('%H:%M')}) {f'- {rmk}' if rmk else ''}")
        st.caption(f"🔄 最後更新時間：{datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        st.error(f"獲取數據時發生錯誤: {e}")

@st.fragment(run_every=60)
def render_ctb_eta(stop, route, dir_code):
    eta_url = f"https://rt.data.gov.hk/v1/transport/citybus-nwfb/eta/ctb/{stop}/{route}"
    try:
        eta_data = get_json(eta_url).get("data", [])
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
st.set_page_config(page_title="香港交通實時到站", page_icon="🇭🇰", layout="wide")

cookie_manager = stx.CookieManager(key="cookie_manager_init")
expire_date = datetime.now() + timedelta(days=365)

st.title("🇭🇰 香港交通實時到站")

tab_nearby, tab_mtr, tab_bus, tab_ctb = st.tabs(["📍 附近路線", "🚇 港鐵", "🚌 九巴及龍運", "🟡 城巴"])

# --- 附近路線分頁 ---
with tab_nearby:
    st.subheader("📍 尋找附近巴士路線")
    st.info("提示：點擊下方按鈕取得 GPS 定位。目前支援九巴及龍運路線。")
    search_radius = st.slider("選擇搜尋範圍（米）", 200, 2000, 500, 100, key="nearby_radius")
    st.markdown("### 📍 按下方按鈕取得我的位置")
    location = streamlit_geolocation()
    try: routes, stops_dict = load_bus_metadata()
    except Exception as exc:
        routes, stops_dict = [], {}; st.error(f"未能下載附近搜尋資料：{exc}")
    if location and location.get("latitude") is not None and location.get("longitude") is not None:
        user_lat, user_lon = float(location["latitude"]), float(location["longitude"])
        st.success(f"✅ 成功取得位置！（緯度：{user_lat:.4f}，經度：{user_lon:.4f}）")
        nearby = {}
        for sid, info in stops_dict.items():
            if info["lat"] and info["lon"]:
                dist = calculate_distance(user_lat,user_lon,info["lat"],info["lon"])
                if dist <= search_radius: nearby[sid]={"name":info["name_tc"],"dist":dist,"routes":info.get("routes",[])}
        available = sorted({str(r) for item in nearby.values() for r in item["routes"]})
        if not available: st.warning("範圍內未能找到九巴／龍運巴士站，請嘗試增大搜尋範圍。")
        else:
            sel_route=st.selectbox("1. 選擇附近巴士路線：",available,key="nb_route")
            matched={sid:d for sid,d in nearby.items() if sel_route in [str(r) for r in d["routes"]]}
            meta=[r for r in routes if str(r.get("route"))==sel_route]
            dirs={f"{r.get('bound','O')}_{r.get('service_type','1')}":f"往 {r.get('dest_tc','請選擇方向')}（班次類型 {r.get('service_type','1')}）" for r in meta}
            if not dirs: dirs={"O_1":"去程","I_1":"回程"}
            selected=st.selectbox("2. 選擇方向：",list(dirs),format_func=lambda x:dirs[x],key="nb_dir")
            bound,service_type=selected.split("_",1)
            sequence=get_kmb_route_stops(sel_route,bound,service_type)
            final=[r for r in sequence if r.get("stop") in matched]
            final.sort(key=lambda r:matched[r["stop"]]["dist"])
            if not final: st.warning("所選方向在搜尋範圍內沒有車站，請嘗試另一方向或增大範圍。")
            else:
                opts={r["stop"]:f"{matched[r['stop']]['name']}（距離 {int(matched[r['stop']]['dist'])} 米）" for r in final}
                sel_stop=st.selectbox("3. 選擇附近車站：",list(opts),format_func=lambda x:opts[x],key="nb_stop")
                st.divider(); st.markdown(f"**📍 {opts[sel_stop]}**")
                render_kmb_eta(sel_stop,sel_route,service_type,bound)
    else: st.warning("⏳ 請按上方定位按鈕，並允許瀏覽器取得位置。")


# --- 港鐵分頁 ---
with tab_mtr:
    st.subheader("🚇 港鐵下班車")
    
    saved_mtr_line = cookie_manager.get("saved_mtr_line")
    line_keys = list(MTR_DATA.keys())
    line_idx = line_keys.index(saved_mtr_line) if saved_mtr_line in line_keys else 0
    
    sel_line = st.selectbox("選擇港鐵路綫：", options=line_keys, index=line_idx, format_func=lambda x: f"{MTR_DATA[x]['name']}", key="mtr_line")
    if sel_line != saved_mtr_line:
        cookie_manager.set("saved_mtr_line", sel_line, expires_at=expire_date, key="set_cookie_mtr_line")
    
    sta_keys = list(MTR_DATA[sel_line]["stations"].keys())
    saved_mtr_sta = cookie_manager.get("saved_mtr_sta")
    sta_idx = sta_keys.index(saved_mtr_sta) if saved_mtr_sta in sta_keys else 0
    
    sel_sta = st.selectbox("選擇車站：", options=sta_keys, index=sta_idx, format_func=lambda x: f"{MTR_DATA[sel_line]['stations'][x]}", key="mtr_sta")
    if sel_sta != saved_mtr_sta:
        cookie_manager.set("saved_mtr_sta", sel_sta, expires_at=expire_date, key="set_cookie_mtr_sta")
    
    st.divider()
    render_mtr_eta(sel_line, sel_sta)


# --- 九巴/龍運分頁 ---
with tab_bus:
    st.subheader("🚌 九巴及龍運下班車")
    routes, stops_dict = load_bus_metadata()

    if routes:
        unique_routes = sorted(list(set([r["route"] for r in routes])))
        
        saved_kmb_route = cookie_manager.get("saved_kmb_route")
        kmb_idx = unique_routes.index(saved_kmb_route) if saved_kmb_route in unique_routes else 0
        
        sel_route = st.selectbox("1. 選擇巴士路綫：", unique_routes, index=kmb_idx, key="kmb_route")
        if sel_route != saved_kmb_route:
            cookie_manager.set("saved_kmb_route", sel_route, expires_at=expire_date, key="set_cookie_kmb_route")
        
        route_dirs = [r for r in routes if r["route"] == sel_route]
        dir_options = {f"{r['bound']}_{r['service_type']}": f"往 {r['dest_tc']} (常規/特別班次 {r['service_type']})" for r in route_dirs}
        sel_dir = st.selectbox("2. 選擇方向：", options=list(dir_options.keys()), format_func=lambda x: dir_options[x], key="kmb_dir")
        bound, srv_type = sel_dir.split("_")
        
        stops_for_route = sorted(get_kmb_route_stops(sel_route, bound, srv_type), key=lambda x: int(x.get("seq", 0)))
        stop_opts = {rs["stop"]: f"{rs['seq']}. {(stops_dict.get(rs['stop']) or get_kmb_stop(rs['stop'])).get('name_tc', '未知車站')}" for rs in stops_for_route}
        sel_stop = st.selectbox("3. 選擇車站：", options=list(stop_opts.keys()), format_func=lambda x: stop_opts[x], key="kmb_stop")
        
        st.divider()
        render_kmb_eta(sel_stop, sel_route, srv_type, bound)


# --- 城巴分頁 ---
with tab_ctb:
    st.subheader("🟡 城巴下班車")
    ctb_routes = load_ctb_routes()
    
    if ctb_routes:
        route_list = sorted(set(r["route"] for r in ctb_routes))
        
        saved_ctb_route = cookie_manager.get("saved_ctb_route")
        ctb_idx = route_list.index(saved_ctb_route) if saved_ctb_route in route_list else 0
        
        sel_ctb_route = st.selectbox("1. 選擇城巴路綫：", route_list, index=ctb_idx, key="ctb_route_sel")
        if sel_ctb_route != saved_ctb_route:
            cookie_manager.set("saved_ctb_route", sel_ctb_route, expires_at=expire_date, key="set_cookie_ctb_route")
        
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
