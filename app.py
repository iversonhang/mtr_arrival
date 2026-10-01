import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import extra_streamlit_components as stx
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from streamlit_geolocation import streamlit_geolocation
from urllib3.util.retry import Retry


# ==========================================
# 0. App configuration and shared helpers
# ==========================================
st.set_page_config(
    page_title="香港交通實時到站",
    page_icon="🇭🇰",
    layout="wide",
)

HK_TZ = ZoneInfo("Asia/Hong_Kong")
REQUEST_TIMEOUT = 12


def hk_now():
    return datetime.now(HK_TZ)


@st.cache_resource
def get_http_session():
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session = requests.Session()
    session.headers.update({"User-Agent": "HK-Transport-ETA-Streamlit/1.0"})
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get_json(url, timeout=REQUEST_TIMEOUT):
    response = get_http_session().get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS coordinates in metres."""
    radius_m = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_m * c


def parse_eta(eta_value):
    """Parse an ISO ETA and return a timezone-aware datetime."""
    if not eta_value:
        return None
    eta_dt = datetime.fromisoformat(eta_value)
    if eta_dt.tzinfo is None:
        eta_dt = eta_dt.replace(tzinfo=HK_TZ)
    return eta_dt.astimezone(HK_TZ)


def eta_message(eta_dt):
    seconds = (eta_dt - hk_now()).total_seconds()
    minutes = math.floor(seconds / 60)
    return "即將抵達" if minutes <= 0 else f"{minutes} 分鐘"


def natural_route_key(route):
    """Sort routes naturally, for example 2 before 10 and 10 before 10A."""
    route = str(route)
    prefix = "".join(ch for ch in route if not ch.isdigit())
    digits = "".join(ch for ch in route if ch.isdigit())
    suffix_start = len(prefix) + len(digits)
    suffix = route[suffix_start:]
    return (prefix, int(digits) if digits else 999999, suffix, route)


# ==========================================
# 1. MTR data
# ==========================================
MTR_DATA = {
    "AEL": {
        "name": "機場快綫",
        "stations": {
            "HOK": "香港",
            "KOW": "九龍",
            "TSY": "青衣",
            "AIR": "機場",
            "AWE": "博覽館",
        },
    },
    "TCL": {
        "name": "東涌綫",
        "stations": {
            "HOK": "香港",
            "KOW": "九龍",
            "OLY": "奧運",
            "NAC": "南昌",
            "LAK": "荔景",
            "TSY": "青衣",
            "SUN": "欣澳",
            "TUC": "東涌",
        },
    },
    "TML": {
        "name": "屯馬綫",
        "stations": {
            "WKS": "烏溪沙",
            "MOS": "馬鞍山",
            "HEO": "恆安",
            "TSH": "大水坑",
            "SHM": "石門",
            "CIO": "第一城",
            "STW": "沙田圍",
            "CKT": "車公廟",
            "TAW": "大圍",
            "HIK": "顯徑",
            "DIH": "鑽石山",
            "KAT": "啟德",
            "SUW": "宋皇臺",
            "TKW": "土瓜灣",
            "HOM": "何文田",
            "HUH": "紅磡",
            "ETS": "尖東",
            "AUS": "柯士甸",
            "NAC": "南昌",
            "MEF": "美孚",
            "TWW": "荃灣西",
            "KSR": "錦上路",
            "YUL": "元朗",
            "LOP": "朗屏",
            "TIS": "天水圍",
            "SIH": "兆康",
            "TUM": "屯門",
        },
    },
    "TKL": {
        "name": "將軍澳綫",
        "stations": {
            "NOP": "北角",
            "QUB": "鰂魚涌",
            "YAT": "油塘",
            "TIK": "調景嶺",
            "TKO": "將軍澳",
            "LHP": "康城",
            "HAO": "坑口",
            "POA": "寶琳",
        },
    },
    "EAL": {
        "name": "東鐵綫",
        "stations": {
            "ADM": "金鐘",
            "EXH": "會展",
            "HUH": "紅磡",
            "MKK": "旺角東",
            "KOT": "九龍塘",
            "TAW": "大圍",
            "SHT": "沙田",
            "FOT": "火炭",
            "RAC": "馬場",
            "UNI": "大學",
            "TAP": "大埔墟",
            "TWO": "太和",
            "FAN": "粉嶺",
            "SHS": "上水",
            "LOW": "羅湖",
            "LMC": "落馬洲",
        },
    },
    "SIL": {
        "name": "南港島綫",
        "stations": {
            "ADM": "金鐘",
            "OCP": "海洋公園",
            "WCH": "黃竹坑",
            "LET": "利東",
            "SOH": "海怡半島",
        },
    },
    "TWL": {
        "name": "荃灣綫",
        "stations": {
            "CEN": "中環",
            "ADM": "金鐘",
            "TST": "尖沙咀",
            "JOR": "佐敦",
            "YMT": "油麻地",
            "MOK": "旺角",
            "PRE": "太子",
            "SSP": "深水埗",
            "CSW": "長沙灣",
            "LCK": "荔枝角",
            "MEF": "美孚",
            "LAK": "荔景",
            "KWF": "葵芳",
            "KWH": "葵興",
            "TWH": "大窩口",
            "TSW": "荃灣",
        },
    },
    "ISL": {
        "name": "港島綫",
        "stations": {
            "KET": "堅尼地城",
            "HKU": "香港大學",
            "SYP": "西營盤",
            "SHW": "上環",
            "CEN": "中環",
            "ADM": "金鐘",
            "WAC": "灣仔",
            "CAB": "銅鑼灣",
            "TIH": "天后",
            "FOH": "炮台山",
            "NOP": "北角",
            "QUB": "鰂魚涌",
            "TAK": "太古",
            "SWH": "西灣河",
            "SKW": "筲箕灣",
            "HFC": "杏花邨",
            "CHW": "柴灣",
        },
    },
    "KTL": {
        "name": "觀塘綫",
        "stations": {
            "WHA": "黃埔",
            "HOM": "何文田",
            "YMT": "油麻地",
            "MOK": "旺角",
            "PRE": "太子",
            "SKM": "石硤尾",
            "KOT": "九龍塘",
            "LOF": "樂富",
            "WTS": "黃大仙",
            "DIH": "鑽石山",
            "CHH": "彩虹",
            "KOB": "九龍灣",
            "NTK": "牛頭角",
            "KWT": "觀塘",
            "LAT": "藍田",
            "YAT": "油塘",
            "TIK": "調景嶺",
        },
    },
    "DRL": {
        "name": "迪士尼綫",
        "stations": {"SUN": "欣澳", "DIS": "迪士尼"},
    },
}

ALL_STATIONS = {}
for line_info in MTR_DATA.values():
    ALL_STATIONS.update(line_info["stations"])


# ==========================================
# 2. Cached transport metadata
# ==========================================
@st.cache_data(ttl=86_400, show_spinner="正在下載九巴及龍運路線資料...")
def load_bus_metadata():
    base_url = "https://data.etabus.gov.hk/v1/transport/kmb"
    routes = get_json(f"{base_url}/route").get("data", [])
    stops_raw = get_json(f"{base_url}/stop").get("data", [])
    route_stops = get_json(f"{base_url}/route-stop").get("data", [])

    stops_dict = {
        s["stop"]: {
            "name_en": s.get("name_en", ""),
            "name_tc": s.get("name_tc", ""),
            "lat": float(s.get("lat") or 0),
            "lon": float(s.get("long") or 0),
        }
        for s in stops_raw
        if s.get("stop")
    }
    return routes, stops_dict, route_stops


@st.cache_data(ttl=86_400, show_spinner="正在下載城巴路線資料...")
def load_ctb_routes():
    url = "https://rt.data.gov.hk/v1/transport/citybus-nwfb/route/ctb"
    return get_json(url).get("data", [])


@st.cache_data(ttl=86_400, show_spinner=False)
def get_ctb_stop(stop_id):
    url = f"https://rt.data.gov.hk/v1/transport/citybus-nwfb/stop/{stop_id}"
    return get_json(url).get("data", {})


@st.cache_data(ttl=3_600, show_spinner="正在下載城巴站點資料...")
def get_ctb_route_stops(route, direction):
    url = (
        "https://rt.data.gov.hk/v1/transport/citybus-nwfb/"
        f"route-stop/ctb/{route}/{direction}"
    )
    route_stops = get_json(url).get("data", [])
    stop_details = {
        rs["stop"]: get_ctb_stop(rs["stop"])
        for rs in route_stops
        if rs.get("stop")
    }
    return route_stops, stop_details


# ==========================================
# 3. ETA fragments, refreshed every 60 seconds
# ==========================================
@st.fragment(run_every=60)
def render_mtr_eta(selected_line, selected_sta):
    url = (
        "https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php"
        f"?line={selected_line}&sta={selected_sta}&lang=tc"
    )
    try:
        data = get_json(url)
        if data.get("status") == 0 or "data" not in data:
            st.warning("目前沒有實時數據，服務可能已暫停。")
            return

        schedule_data = data["data"].get(f"{selected_line}-{selected_sta}", {})
        if not schedule_data:
            st.info("此車站目前沒有即將到達的列車。")
            return

        col1, col2 = st.columns(2)

        def draw_trains(direction_key, title):
            trains = schedule_data.get(direction_key, [])
            st.markdown(f"**{title}**")
            if not trains:
                st.write("沒有列車數據。")
                return

            for train in trains:
                dest_code = train.get("dest", "")
                dest_name = ALL_STATIONS.get(dest_code, dest_code or "未知終點")
                minutes = train.get("ttnt", "-")
                platform = train.get("plat", "-")
                train_time = train.get("time", "")
                arrival_time = train_time[-8:-3] if len(train_time) >= 8 else "--:--"
                st.success(
                    f"**{platform} 號月台** ➔ **{dest_name}**\n\n"
                    f"即將到達： **{minutes} 分鐘** ({arrival_time})"
                )

        with col1:
            draw_trains("UP", "⬆️ 上行列車")
        with col2:
            draw_trains("DOWN", "⬇️ 下行列車")

        st.caption(f"🔄 最後更新時間：{hk_now().strftime('%H:%M:%S')}")
    except requests.RequestException as exc:
        st.error(f"未能連接港鐵實時到站服務：{exc}")
    except (ValueError, TypeError, KeyError) as exc:
        st.error(f"港鐵到站資料格式異常：{exc}")


@st.fragment(run_every=60)
def render_kmb_eta(stop, route, service_type, bound):
    eta_url = (
        "https://data.etabus.gov.hk/v1/transport/kmb/eta/"
        f"{stop}/{route}/{service_type}"
    )
    try:
        eta_data = get_json(eta_url).get("data", [])
        eta_data = [eta for eta in eta_data if eta.get("dir") == bound]

        if not eta_data:
            st.info("目前沒有即將到達的巴士，或服務已暫停。")
        else:
            for eta in eta_data:
                eta_dt = parse_eta(eta.get("eta"))
                remark = eta.get("rmk_tc", "")
                company = eta.get("co", "KMB/LWB")
                destination = eta.get("dest_tc", "未知終點")

                if eta_dt is None:
                    st.warning(
                        f"🚍 **路線 {route}** ({company}) | "
                        f"狀態：{remark or '原定班次，未有實時數據'}"
                    )
                    continue

                suffix = f" - {remark}" if remark else ""
                st.success(
                    f"🚍 **路線 {route}** ({company}) ➔ **往 {destination}**\n\n"
                    f"即將到達： **{eta_message(eta_dt)}** "
                    f"({eta_dt.strftime('%H:%M')}){suffix}"
                )

        st.caption(f"🔄 最後更新時間：{hk_now().strftime('%H:%M:%S')}")
    except requests.RequestException as exc:
        st.error(f"未能連接九巴／龍運實時到站服務：{exc}")
    except (ValueError, TypeError, KeyError) as exc:
        st.error(f"九巴／龍運到站資料格式異常：{exc}")


@st.fragment(run_every=60)
def render_ctb_eta(stop, route, direction_code):
    eta_url = (
        "https://rt.data.gov.hk/v1/transport/citybus-nwfb/eta/"
        f"ctb/{stop}/{route}"
    )
    try:
        eta_data = get_json(eta_url).get("data", [])
        eta_data = [eta for eta in eta_data if eta.get("dir") == direction_code]

        if not eta_data:
            st.info("目前沒有即將到達的巴士。")
        else:
            for eta in eta_data:
                eta_dt = parse_eta(eta.get("eta"))
                remark = eta.get("rmk_tc", "")
                destination = eta.get("dest_tc", "未知終點")

                if eta_dt is None:
                    st.warning(f"🟡 **狀態：** {remark or '原定班次，未有實時數據'}")
                    continue

                suffix = f" - {remark}" if remark else ""
                st.success(
                    f"🟡 **往 {destination}**\n\n"
                    f"即將到達： **{eta_message(eta_dt)}** "
                    f"({eta_dt.strftime('%H:%M')}){suffix}"
                )

        st.caption(f"🔄 最後更新時間：{hk_now().strftime('%H:%M:%S')}")
    except requests.RequestException as exc:
        st.error(f"未能連接城巴實時到站服務：{exc}")
    except (ValueError, TypeError, KeyError) as exc:
        st.error(f"城巴到站資料格式異常：{exc}")


# ==========================================
# 4. Main interface
# ==========================================
cookie_manager = stx.CookieManager(key="cookie_manager_init")
expire_date = datetime.now() + timedelta(days=365)

st.title("🇭🇰 香港交通實時到站")
st.caption("實時資料每 60 秒自動更新")

tab_nearby, tab_mtr, tab_bus, tab_ctb = st.tabs(
    ["📍 附近路線", "🚇 港鐵", "🚌 九巴及龍運", "🟡 城巴"]
)


# Nearby KMB/LWB routes
with tab_nearby:
    st.subheader("📍 尋找附近巴士路線")
    st.info("點擊下方定位按鈕並允許瀏覽器取得位置。目前附近搜尋支援九巴及龍運。")

    search_radius = st.slider(
        "選擇搜尋範圍（米）",
        min_value=200,
        max_value=2000,
        value=500,
        step=100,
        key="nearby_radius",
    )
    location = streamlit_geolocation()

    try:
        routes, stops_dict, route_stops = load_bus_metadata()
    except requests.RequestException as exc:
        routes, stops_dict, route_stops = [], {}, []
        st.error(f"未能下載九巴／龍運路線資料：{exc}")
    except (ValueError, TypeError, KeyError) as exc:
        routes, stops_dict, route_stops = [], {}, []
        st.error(f"九巴／龍運路線資料格式異常：{exc}")

    has_location = (
        bool(location)
        and location.get("latitude") is not None
        and location.get("longitude") is not None
    )

    if has_location and stops_dict:
        user_lat = float(location["latitude"])
        user_lon = float(location["longitude"])
        st.success(
            f"✅ 成功取得位置！緯度：{user_lat:.4f}，經度：{user_lon:.4f}"
        )

        nearby_stops_info = {}
        for stop_id, info in stops_dict.items():
            if info["lat"] > 0 and info["lon"] > 0:
                distance = calculate_distance(
                    user_lat, user_lon, info["lat"], info["lon"]
                )
                if distance <= search_radius:
                    nearby_stops_info[stop_id] = {
                        "name": info["name_tc"],
                        "dist": distance,
                    }

        if nearby_stops_info:
            nearby_ids = set(nearby_stops_info)
            nearby_route_stops = [
                rs for rs in route_stops if rs.get("stop") in nearby_ids
            ]

            if nearby_route_stops:
                available_routes = sorted(
                    {rs["route"] for rs in nearby_route_stops},
                    key=natural_route_key,
                )
                selected_route = st.selectbox(
                    "1. 選擇附近的巴士路線：",
                    available_routes,
                    key="nb_route",
                )

                selected_route_stops = [
                    rs
                    for rs in nearby_route_stops
                    if rs.get("route") == selected_route
                ]
                route_meta = [r for r in routes if r.get("route") == selected_route]

                direction_options = {}
                for rs in selected_route_stops:
                    direction_key = f"{rs['bound']}_{rs['service_type']}"
                    if direction_key not in direction_options:
                        destination = "未知終點"
                        for meta in route_meta:
                            if (
                                meta.get("bound") == rs.get("bound")
                                and meta.get("service_type") == rs.get("service_type")
                            ):
                                destination = meta.get("dest_tc", destination)
                                break
                        direction_options[direction_key] = (
                            f"往 {destination}（班次類型 {rs['service_type']}）"
                        )

                selected_direction = st.selectbox(
                    "2. 選擇方向：",
                    list(direction_options),
                    format_func=lambda value: direction_options[value],
                    key="nb_dir",
                )
                bound, service_type = selected_direction.split("_", 1)

                final_stops = [
                    rs
                    for rs in selected_route_stops
                    if rs.get("bound") == bound
                    and rs.get("service_type") == service_type
                ]
                final_stops.sort(
                    key=lambda item: nearby_stops_info[item["stop"]]["dist"]
                )

                if final_stops:
                    stop_options = {
                        rs["stop"]: (
                            f"{nearby_stops_info[rs['stop']]['name']} "
                            f"（距離 {int(nearby_stops_info[rs['stop']]['dist'])} 米）"
                        )
                        for rs in final_stops
                    }
                    selected_stop = st.selectbox(
                        "3. 選擇附近的車站：",
                        list(stop_options),
                        format_func=lambda value: stop_options[value],
                        key="nb_stop",
                    )
                    st.divider()
                    st.markdown(f"**📍 {stop_options[selected_stop]}**")
                    render_kmb_eta(
                        selected_stop, selected_route, service_type, bound
                    )
                else:
                    st.warning("所選方向在附近沒有車站。")
            else:
                st.warning("範圍內未能找到任何巴士路線。")
        else:
            st.warning("範圍內未能找到九巴／龍運巴士站，請嘗試增大搜尋範圍。")
    elif not has_location:
        st.warning("⏳ 請點擊上方定位按鈕並允許取得位置。")


# MTR
with tab_mtr:
    st.subheader("🚇 港鐵下班車")

    saved_mtr_line = cookie_manager.get("saved_mtr_line")
    line_keys = list(MTR_DATA)
    line_index = line_keys.index(saved_mtr_line) if saved_mtr_line in line_keys else 0

    selected_line = st.selectbox(
        "選擇港鐵路綫：",
        line_keys,
        index=line_index,
        format_func=lambda value: MTR_DATA[value]["name"],
        key="mtr_line",
    )
    if selected_line != saved_mtr_line:
        cookie_manager.set(
            "saved_mtr_line",
            selected_line,
            expires_at=expire_date,
            key="set_cookie_mtr_line",
        )

    station_keys = list(MTR_DATA[selected_line]["stations"])
    saved_mtr_station = cookie_manager.get("saved_mtr_sta")
    station_index = (
        station_keys.index(saved_mtr_station)
        if saved_mtr_station in station_keys
        else 0
    )

    selected_station = st.selectbox(
        "選擇車站：",
        station_keys,
        index=station_index,
        format_func=lambda value: MTR_DATA[selected_line]["stations"][value],
        key="mtr_sta",
    )
    if selected_station != saved_mtr_station:
        cookie_manager.set(
            "saved_mtr_sta",
            selected_station,
            expires_at=expire_date,
            key="set_cookie_mtr_sta",
        )

    st.divider()
    render_mtr_eta(selected_line, selected_station)


# KMB/LWB
with tab_bus:
    st.subheader("🚌 九巴及龍運下班車")

    try:
        routes, stops_dict, route_stops = load_bus_metadata()
    except requests.RequestException as exc:
        routes, stops_dict, route_stops = [], {}, []
        st.error(f"未能下載九巴／龍運路線資料：{exc}")
    except (ValueError, TypeError, KeyError) as exc:
        routes, stops_dict, route_stops = [], {}, []
        st.error(f"九巴／龍運路線資料格式異常：{exc}")

    if routes:
        unique_routes = sorted(
            {route["route"] for route in routes if route.get("route")},
            key=natural_route_key,
        )
        saved_route = cookie_manager.get("saved_kmb_route")
        route_index = unique_routes.index(saved_route) if saved_route in unique_routes else 0

        selected_route = st.selectbox(
            "1. 選擇巴士路綫：",
            unique_routes,
            index=route_index,
            key="kmb_route",
        )
        if selected_route != saved_route:
            cookie_manager.set(
                "saved_kmb_route",
                selected_route,
                expires_at=expire_date,
                key="set_cookie_kmb_route",
            )

        route_directions = [r for r in routes if r.get("route") == selected_route]
        direction_options = {
            f"{r['bound']}_{r['service_type']}": (
                f"往 {r.get('dest_tc', '未知終點')}"
                f"（班次類型 {r['service_type']}）"
            )
            for r in route_directions
        }

        if direction_options:
            selected_direction = st.selectbox(
                "2. 選擇方向：",
                list(direction_options),
                format_func=lambda value: direction_options[value],
                key="kmb_dir",
            )
            bound, service_type = selected_direction.split("_", 1)

            stops_for_route = sorted(
                [
                    rs
                    for rs in route_stops
                    if rs.get("route") == selected_route
                    and rs.get("bound") == bound
                    and rs.get("service_type") == service_type
                ],
                key=lambda item: int(item.get("seq", 0)),
            )
            stop_options = {
                rs["stop"]: (
                    f"{rs.get('seq', '-')}. "
                    f"{stops_dict.get(rs['stop'], {}).get('name_tc', '未知車站')}"
                )
                for rs in stops_for_route
                if rs.get("stop")
            }

            if stop_options:
                selected_stop = st.selectbox(
                    "3. 選擇車站：",
                    list(stop_options),
                    format_func=lambda value: stop_options[value],
                    key="kmb_stop",
                )
                st.divider()
                render_kmb_eta(
                    selected_stop, selected_route, service_type, bound
                )
            else:
                st.warning("此路線方向沒有車站資料。")
        else:
            st.warning("此路線沒有方向資料。")


# Citybus
with tab_ctb:
    st.subheader("🟡 城巴下班車")

    try:
        ctb_routes = load_ctb_routes()
    except requests.RequestException as exc:
        ctb_routes = []
        st.error(f"未能下載城巴路線資料：{exc}")
    except (ValueError, TypeError, KeyError) as exc:
        ctb_routes = []
        st.error(f"城巴路線資料格式異常：{exc}")

    if ctb_routes:
        route_list = sorted(
            {route["route"] for route in ctb_routes if route.get("route")},
            key=natural_route_key,
        )
        saved_ctb_route = cookie_manager.get("saved_ctb_route")
        ctb_route_index = (
            route_list.index(saved_ctb_route) if saved_ctb_route in route_list else 0
        )

        selected_ctb_route = st.selectbox(
            "1. 選擇城巴路綫：",
            route_list,
            index=ctb_route_index,
            key="ctb_route_sel",
        )
        if selected_ctb_route != saved_ctb_route:
            cookie_manager.set(
                "saved_ctb_route",
                selected_ctb_route,
                expires_at=expire_date,
                key="set_cookie_ctb_route",
            )

        route_meta = next(
            route
            for route in ctb_routes
            if route.get("route") == selected_ctb_route
        )
        direction_options = {
            "outbound": f"往 {route_meta.get('dest_tc', '終點站')}",
            "inbound": f"往 {route_meta.get('orig_tc', '起點站')}",
        }
        selected_ctb_direction = st.selectbox(
            "2. 選擇方向：",
            list(direction_options),
            format_func=lambda value: direction_options[value],
            key="ctb_dir",
        )

        try:
            ctb_route_stops, ctb_stop_details = get_ctb_route_stops(
                selected_ctb_route, selected_ctb_direction
            )
        except requests.RequestException as exc:
            ctb_route_stops, ctb_stop_details = [], {}
            st.error(f"未能下載城巴站點資料：{exc}")
        except (ValueError, TypeError, KeyError) as exc:
            ctb_route_stops, ctb_stop_details = [], {}
            st.error(f"城巴站點資料格式異常：{exc}")

        if ctb_route_stops:
            ctb_stop_options = {
                rs["stop"]: (
                    f"{rs.get('seq', '-')}. "
                    f"{ctb_stop_details.get(rs['stop'], {}).get('name_tc', '未知車站')}"
                )
                for rs in ctb_route_stops
                if rs.get("stop")
            }

            if ctb_stop_options:
                selected_ctb_stop = st.selectbox(
                    "3. 選擇車站：",
                    list(ctb_stop_options),
                    format_func=lambda value: ctb_stop_options[value],
                    key="ctb_stop",
                )
                st.divider()
                direction_code = "O" if selected_ctb_direction == "outbound" else "I"
                render_ctb_eta(
                    selected_ctb_stop, selected_ctb_route, direction_code
                )
            else:
                st.warning("此方向沒有有效的車站資料。")
        else:
            st.warning("此方向沒有車站資料。")
