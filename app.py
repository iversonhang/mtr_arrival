import math
from datetime import datetime

import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from streamlit_geolocation import streamlit_geolocation
from urllib3.util.retry import Retry

st.set_page_config(page_title="香港交通實時到站", page_icon="🇭🇰", layout="wide")

KMB_MIRROR = "https://winstonma.github.io/MMM-HK-Transport-ETA-Data"
TIMEOUT = 15
MTR_DATA = {'AEL': {'name': '機場快綫', 'stations': {'HOK': '香港', 'KOW': '九龍', 'TSY': '青衣', 'AIR': '機場', 'AWE': '博覽館'}}, 'TCL': {'name': '東涌綫', 'stations': {'HOK': '香港', 'KOW': '九龍', 'OLY': '奧運', 'NAC': '南昌', 'LAK': '荔景', 'TSY': '青衣', 'SUN': '欣澳', 'TUC': '東涌'}}, 'TML': {'name': '屯馬綫', 'stations': {'WKS': '烏溪沙', 'MOS': '馬鞍山', 'HEO': '恆安', 'TSH': '大水坑', 'SHM': '石門', 'CIO': '第一城', 'STW': '沙田圍', 'CKT': '車公廟', 'TAW': '大圍', 'HIK': '顯徑', 'DIH': '鑽石山', 'KAT': '啟德', 'SUW': '宋皇臺', 'TKW': '土瓜灣', 'HOM': '何文田', 'HUH': '紅磡', 'ETS': '尖東', 'AUS': '柯士甸', 'NAC': '南昌', 'MEF': '美孚', 'TWW': '荃灣西', 'KSR': '錦上路', 'YUL': '元朗', 'LOP': '朗屏', 'TIS': '天水圍', 'SIH': '兆康', 'TUM': '屯門'}}, 'TKL': {'name': '將軍澳綫', 'stations': {'NOP': '北角', 'QUB': '鰂魚涌', 'YAT': '油塘', 'TIK': '調景嶺', 'TKO': '將軍澳', 'LHP': '康城', 'HAO': 'Hang Hau', 'POA': '寶琳'}}, 'EAL': {'name': '東鐵綫', 'stations': {'ADM': '金鐘', 'EXH': '會展', 'HUH': '紅磡', 'MKK': '旺角東', 'KOT': '九龍塘', 'TAW': '大圍', 'SHT': '沙田', 'FOT': '火炭', 'RAC': '馬場', 'UNI': '大學', 'TAP': '大埔墟', 'TWO': '太和', 'FAN': '粉嶺', 'SHS': '上水', 'LOW': '羅湖', 'LMC': '落馬洲'}}, 'SIL': {'name': '南港島綫', 'stations': {'ADM': '金鐘', 'OCP': '海洋公園', 'WCH': '黃竹坑', 'LET': '利東', 'SOH': '海怡半島'}}, 'TWL': {'name': '荃灣綫', 'stations': {'CEN': '中環', 'ADM': '金鐘', 'TST': '尖沙咀', 'JOR': '佐敦', 'YMT': '油麻地', 'MOK': '旺角', 'PRE': '太子', 'SSP': '深水埗', 'CSW': '長沙灣', 'LCK': '荔枝角', 'MEF': '美孚', 'LAK': '荔景', 'KWF': '葵芳', 'KWH': '葵興', 'TWH': '大窩口', 'TSW': '荃灣'}}, 'ISL': {'name': '港島綫', 'stations': {'KET': '堅尼地城', 'HKU': '香港大學', 'SYP': '西營盤', 'SHW': '上環', 'CEN': '中環', 'ADM': '金鐘', 'WAC': '灣仔', 'CAB': '銅鑼灣', 'TIH': '天后', 'FOH': '炮台山', 'NOP': '北角', 'QUB': '鰂魚涌', 'TAK': '太古', 'SWH': '西灣河', 'SKW': '筲箕灣', 'HFC': '杏花邨', 'CHW': '柴灣'}}, 'KTL': {'name': '觀塘綫', 'stations': {'WHA': '黃埔', 'HOM': '何文田', 'YMT': '油麻地', 'MOK': '旺角', 'PRE': '太子', 'SKM': '石硤尾', 'KOT': '九龍塘', 'LOF': '樂富', 'WTS': '黃大仙', 'DIH': '鑽石山', 'CHH': '彩虹', 'KOB': '九龍灣', 'NTK': '牛頭角', 'KWT': '觀塘', 'LAT': '藍田', 'YAT': '油塘', 'TIK': '調景嶺'}}, 'DRL': {'name': '迪士尼綫', 'stations': {'SUN': '欣澳', 'DIS': '迪士尼'}}}
ALL_STATIONS = {}
for info in MTR_DATA.values():
    ALL_STATIONS.update(info["stations"])


@st.cache_resource
def http():
    retry = Retry(total=3, connect=3, read=3, status=3, backoff_factor=0.5,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset(["GET"]), raise_on_status=False)
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get_json(url):
    r = http().get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def rows(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    data = payload.get("data", payload)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        output = []
        for key, value in data.items():
            if isinstance(value, dict):
                item = dict(value)
                item.setdefault("id", key)
                output.append(item)
        return output
    return []


def distance_m(lat1, lon1, lat2, lon2):
    radius = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def natural_key(value):
    value = str(value)
    number = "".join(c for c in value if c.isdigit())
    return (int(number) if number else 999999, value)


@st.cache_data(ttl=86400, show_spinner="正在下載九巴／龍運車站資料...")
def load_kmb_stops():
    payload = get_json(f"{KMB_MIRROR}/kmb/stops/allstops.json")
    result = {}
    for item in rows(payload):
        stop_id = item.get("stop") or item.get("stop_id") or item.get("id")
        if not stop_id:
            continue
        try:
            latitude = float(item.get("lat") or item.get("latitude") or 0)
            longitude = float(item.get("long") or item.get("lon") or item.get("longitude") or 0)
        except (TypeError, ValueError):
            latitude, longitude = 0.0, 0.0
        routes_value = item.get("routes") or []
        if isinstance(routes_value, str):
            routes_value = [r.strip() for r in routes_value.split(",") if r.strip()]
        result[str(stop_id)] = {
            "name": item.get("name_tc") or item.get("name_zh") or item.get("name") or f"車站 {stop_id}",
            "lat": latitude,
            "lon": longitude,
            "routes": sorted({str(r) for r in routes_value}, key=natural_key),
        }
    if not result:
        raise ValueError("車站資料格式不正確或沒有資料")
    return result


@st.cache_data(ttl=86400, show_spinner="正在下載城巴路線資料...")
def load_ctb_routes():
    return get_json("https://rt.data.gov.hk/v1/transport/citybus-nwfb/route/ctb").get("data", [])


@st.cache_data(ttl=3600, show_spinner=False)
def load_ctb_route_stops(route, direction):
    base = "https://rt.data.gov.hk/v1/transport/citybus-nwfb"
    route_stops = get_json(f"{base}/route-stop/ctb/{route}/{direction}").get("data", [])
    details = {}
    for item in route_stops:
        stop_id = item.get("stop")
        if stop_id:
            details[stop_id] = get_json(f"{base}/stop/{stop_id}").get("data", {})
    return route_stops, details


def parse_eta(text):
    if not text:
        return None
    return datetime.fromisoformat(text)


def eta_text(eta_dt):
    now = datetime.now(eta_dt.tzinfo) if eta_dt.tzinfo else datetime.now()
    mins = math.floor((eta_dt - now).total_seconds() / 60)
    return "即將抵達" if mins <= 0 else f"{mins} 分鐘"


def show_kmb_eta(stop_id, route):
    url = f"https://data.etabus.gov.hk/v1/transport/kmb/eta/{stop_id}/{route}/1"
    try:
        eta_rows = get_json(url).get("data", [])
    except Exception as exc:
        st.error(f"未能下載九巴／龍運到站資料：{exc}")
        return
    eta_rows = [r for r in eta_rows if r.get("eta") or r.get("rmk_tc")]
    if not eta_rows:
        st.info("目前沒有即將到達的班次。")
        return
    for item in eta_rows:
        eta_dt = parse_eta(item.get("eta"))
        destination = item.get("dest_tc") or "未知終點"
        remark = item.get("rmk_tc") or ""
        direction = "去程" if item.get("dir") == "O" else "回程" if item.get("dir") == "I" else ""
        if eta_dt:
            st.success(f"🚌 **{route} {direction} 往 {destination}**  |  **{eta_text(eta_dt)}**（{eta_dt.strftime('%H:%M')}） {remark}")
        else:
            st.warning(f"🚌 **{route} {direction} 往 {destination}**  |  {remark or '未有實時資料'}")
    st.caption(f"最後更新：{datetime.now().strftime('%H:%M:%S')}")


def show_mtr_eta(line, station):
    url = f"https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={line}&sta={station}&lang=tc"
    try:
        payload = get_json(url)
        schedule = payload.get("data", {}).get(f"{line}-{station}", {})
    except Exception as exc:
        st.error(f"未能下載港鐵到站資料：{exc}")
        return
    if not schedule:
        st.info("此站目前沒有列車資料。")
        return
    c1, c2 = st.columns(2)
    for container, key, title in ((c1, "UP", "⬆️ 上行"), (c2, "DOWN", "⬇️ 下行")):
        with container:
            st.markdown(f"**{title}**")
            trains = schedule.get(key, [])
            if not trains:
                st.write("沒有列車資料。")
            for train in trains:
                dest = ALL_STATIONS.get(train.get("dest"), train.get("dest") or "未知終點")
                st.success(f"**{train.get('plat', '-')} 號月台 ➜ {dest}**  |  {train.get('ttnt', '-')} 分鐘")


def show_ctb_eta(stop_id, route, direction_code):
    url = f"https://rt.data.gov.hk/v1/transport/citybus-nwfb/eta/ctb/{stop_id}/{route}"
    try:
        eta_rows = [r for r in get_json(url).get("data", []) if r.get("dir") == direction_code]
    except Exception as exc:
        st.error(f"未能下載城巴到站資料：{exc}")
        return
    if not eta_rows:
        st.info("目前沒有即將到達的班次。")
    for item in eta_rows:
        eta_dt = parse_eta(item.get("eta"))
        if eta_dt:
            st.success(f"🟡 **往 {item.get('dest_tc', '未知終點')}**  |  **{eta_text(eta_dt)}**（{eta_dt.strftime('%H:%M')}） {item.get('rmk_tc', '')}")
        else:
            st.warning(item.get("rmk_tc") or "未有實時資料")


st.title("🇭🇰 香港交通實時到站")
tab_nearby, tab_mtr, tab_kmb, tab_ctb = st.tabs(["📍 附近路線", "🚇 港鐵", "🚌 九巴及龍運", "🟡 城巴"])

with tab_nearby:
    st.subheader("📍 尋找附近巴士站")
    radius = st.slider("搜尋範圍（米）", 200, 2000, 500, 100)
    st.markdown("#### 按下方 **Get Location** 按鈕取得 GPS 位置")
    location = streamlit_geolocation()

    with st.expander("若看不到 GPS 按鈕，可手動輸入位置"):
        manual = st.checkbox("使用手動位置")
        col1, col2 = st.columns(2)
        manual_lat = col1.number_input("緯度", value=22.3692, format="%.6f")
        manual_lon = col2.number_input("經度", value=114.1201, format="%.6f")

    latitude = longitude = None
    if isinstance(location, dict) and location.get("latitude") is not None:
        latitude = float(location["latitude"])
        longitude = float(location["longitude"])
        st.success(f"✅ GPS 位置：{latitude:.5f}, {longitude:.5f}")
    elif manual:
        latitude, longitude = manual_lat, manual_lon
        st.success(f"✅ 手動位置：{latitude:.5f}, {longitude:.5f}")
    else:
        st.warning("請按 Get Location 並允許瀏覽器取得位置，或展開手動位置。")

    if latitude is not None:
        try:
            stop_data = load_kmb_stops()
            nearby = []
            for stop_id, info in stop_data.items():
                if info["lat"] and info["lon"]:
                    dist = distance_m(latitude, longitude, info["lat"], info["lon"])
                    if dist <= radius:
                        nearby.append((stop_id, info, dist))
            nearby.sort(key=lambda x: x[2])
            if not nearby:
                st.warning("範圍內找不到九巴／龍運車站，請增大搜尋範圍。")
            else:
                stop_options = {sid: f"{info['name']}（{int(dist)} 米）" for sid, info, dist in nearby}
                selected_stop = st.selectbox("1. 選擇附近車站", list(stop_options), format_func=lambda x: stop_options[x])
                routes = stop_data[selected_stop]["routes"]
                if routes:
                    selected_route = st.selectbox("2. 選擇路線", routes)
                    st.divider()
                    show_kmb_eta(selected_stop, selected_route)
                else:
                    st.info("這個車站的路線清單暫時沒有資料。")
        except Exception as exc:
            st.error(f"未能下載巴士站資料：{exc}")

with tab_mtr:
    st.subheader("🚇 港鐵下班車")
    line = st.selectbox("選擇港鐵路綫", list(MTR_DATA), format_func=lambda x: MTR_DATA[x]["name"])
    station = st.selectbox("選擇車站", list(MTR_DATA[line]["stations"]), format_func=lambda x: MTR_DATA[line]["stations"][x])
    st.divider()
    show_mtr_eta(line, station)

with tab_kmb:
    st.subheader("🚌 九巴及龍運下班車")
    try:
        stop_data = load_kmb_stops()
        all_routes = sorted({route for info in stop_data.values() for route in info["routes"]}, key=natural_key)
        selected_route = st.selectbox("1. 選擇路線", all_routes, key="kmb_route")
        serving_stops = [(sid, info) for sid, info in stop_data.items() if selected_route in info["routes"]]
        serving_stops.sort(key=lambda x: x[1]["name"])
        options = {sid: info["name"] for sid, info in serving_stops}
        if options:
            selected_stop = st.selectbox("2. 選擇車站", list(options), format_func=lambda x: options[x], key="kmb_stop")
            st.divider()
            show_kmb_eta(selected_stop, selected_route)
        else:
            st.info("此路線沒有車站資料。")
    except Exception as exc:
        st.error(f"未能下載九巴／龍運資料：{exc}")

with tab_ctb:
    st.subheader("🟡 城巴下班車")
    try:
        ctb_routes = load_ctb_routes()
        route_numbers = sorted({r["route"] for r in ctb_routes}, key=natural_key)
        route = st.selectbox("1. 選擇路線", route_numbers, key="ctb_route")
        meta = next(r for r in ctb_routes if r["route"] == route)
        direction_options = {"outbound": f"往 {meta.get('dest_tc', '終點站')}", "inbound": f"往 {meta.get('orig_tc', '起點站')}"}
        direction = st.selectbox("2. 選擇方向", list(direction_options), format_func=lambda x: direction_options[x])
        route_stops, details = load_ctb_route_stops(route, direction)
        options = {r["stop"]: f"{r.get('seq', '-')}. {details.get(r['stop'], {}).get('name_tc', '未知車站')}" for r in route_stops}
        if options:
            stop_id = st.selectbox("3. 選擇車站", list(options), format_func=lambda x: options[x])
            st.divider()
            show_ctb_eta(stop_id, route, "O" if direction == "outbound" else "I")
        else:
            st.info("此方向沒有車站資料。")
    except Exception as exc:
        st.error(f"未能下載城巴資料：{exc}")
