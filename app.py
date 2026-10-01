import math
from datetime import datetime
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from streamlit_geolocation import streamlit_geolocation
from urllib3.util.retry import Retry

st.set_page_config(page_title="香港交通實時到站", page_icon="🇭🇰", layout="wide")
KMB_MIRROR="https://winstonma.github.io/MMM-HK-Transport-ETA-Data"
TIMEOUT=15
MTR_DATA={'AEL': {'name': '機場快綫', 'stations': {'HOK': '香港', 'KOW': '九龍', 'TSY': '青衣', 'AIR': '機場', 'AWE': '博覽館'}}, 'TCL': {'name': '東涌綫', 'stations': {'HOK': '香港', 'KOW': '九龍', 'OLY': '奧運', 'NAC': '南昌', 'LAK': '荔景', 'TSY': '青衣', 'SUN': '欣澳', 'TUC': '東涌'}}, 'TML': {'name': '屯馬綫', 'stations': {'WKS': '烏溪沙', 'MOS': '馬鞍山', 'HEO': '恆安', 'TSH': '大水坑', 'SHM': '石門', 'CIO': '第一城', 'STW': '沙田圍', 'CKT': '車公廟', 'TAW': '大圍', 'HIK': '顯徑', 'DIH': '鑽石山', 'KAT': '啟德', 'SUW': '宋皇臺', 'TKW': '土瓜灣', 'HOM': '何文田', 'HUH': '紅磡', 'ETS': '尖東', 'AUS': '柯士甸', 'NAC': '南昌', 'MEF': '美孚', 'TWW': '荃灣西', 'KSR': '錦上路', 'YUL': '元朗', 'LOP': '朗屏', 'TIS': '天水圍', 'SIH': '兆康', 'TUM': '屯門'}}, 'TKL': {'name': '將軍澳綫', 'stations': {'NOP': '北角', 'QUB': '鰂魚涌', 'YAT': '油塘', 'TIK': '調景嶺', 'TKO': '將軍澳', 'LHP': '康城', 'HAO': '坑口', 'POA': '寶琳'}}, 'EAL': {'name': '東鐵綫', 'stations': {'ADM': '金鐘', 'EXH': '會展', 'HUH': '紅磡', 'MKK': '旺角東', 'KOT': '九龍塘', 'TAW': '大圍', 'SHT': '沙田', 'FOT': '火炭', 'RAC': '馬場', 'UNI': '大學', 'TAP': '大埔墟', 'TWO': '太和', 'FAN': '粉嶺', 'SHS': '上水', 'LOW': '羅湖', 'LMC': '落馬洲'}}, 'SIL': {'name': '南港島綫', 'stations': {'ADM': '金鐘', 'OCP': '海洋公園', 'WCH': '黃竹坑', 'LET': '利東', 'SOH': '海怡半島'}}, 'TWL': {'name': '荃灣綫', 'stations': {'CEN': '中環', 'ADM': '金鐘', 'TST': '尖沙咀', 'JOR': '佐敦', 'YMT': '油麻地', 'MOK': '旺角', 'PRE': '太子', 'SSP': '深水埗', 'CSW': '長沙灣', 'LCK': '荔枝角', 'MEF': '美孚', 'LAK': '荔景', 'KWF': '葵芳', 'KWH': '葵興', 'TWH': '大窩口', 'TSW': '荃灣'}}, 'ISL': {'name': '港島綫', 'stations': {'KET': '堅尼地城', 'HKU': '香港大學', 'SYP': '西營盤', 'SHW': '上環', 'CEN': '中環', 'ADM': '金鐘', 'WAC': '灣仔', 'CAB': '銅鑼灣', 'TIH': '天后', 'FOH': '炮台山', 'NOP': '北角', 'QUB': '鰂魚涌', 'TAK': '太古', 'SWH': '西灣河', 'SKW': '筲箕灣', 'HFC': '杏花邨', 'CHW': '柴灣'}}, 'KTL': {'name': '觀塘綫', 'stations': {'WHA': '黃埔', 'HOM': '何文田', 'YMT': '油麻地', 'MOK': '旺角', 'PRE': '太子', 'SKM': '石硤尾', 'KOT': '九龍塘', 'LOF': '樂富', 'WTS': '黃大仙', 'DIH': '鑽石山', 'CHH': '彩虹', 'KOB': '九龍灣', 'NTK': '牛頭角', 'KWT': '觀塘', 'LAT': '藍田', 'YAT': '油塘', 'TIK': '調景嶺'}}, 'DRL': {'name': '迪士尼綫', 'stations': {'SUN': '欣澳', 'DIS': '迪士尼'}}}
ALL_STATIONS={}
for x in MTR_DATA.values(): ALL_STATIONS.update(x["stations"])

@st.cache_resource
def http():
    retry=Retry(total=3,backoff_factor=.5,status_forcelist=(429,500,502,503,504),allowed_methods=frozenset(["GET"]),raise_on_status=False)
    s=requests.Session(); a=HTTPAdapter(max_retries=retry,pool_connections=20,pool_maxsize=20)
    s.mount("https://",a); s.mount("http://",a); return s

def get_json(url):
    r=http().get(url,timeout=TIMEOUT); r.raise_for_status(); return r.json()

def rows(value):
    if isinstance(value,list): return value
    if not isinstance(value,dict): return []
    data=value.get("data",value)
    if isinstance(data,list): return data
    if isinstance(data,dict):
        out=[]
        for k,v in data.items():
            if isinstance(v,dict):
                item=dict(v); item.setdefault("id",k); out.append(item)
        return out
    return []

def dist(lat1,lon1,lat2,lon2):
    r=6371000; p1,p2=math.radians(lat1),math.radians(lat2)
    dp=math.radians(lat2-lat1); dl=math.radians(lon2-lon1)
    a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return r*2*math.atan2(math.sqrt(a),math.sqrt(1-a))

def sort_key(v):
    v=str(v); n=''.join(c for c in v if c.isdigit()); return (int(n) if n else 999999,v)

@st.cache_data(ttl=86400,show_spinner="正在下載九巴／龍運車站資料...")
def kmb_stops():
    result={}
    for item in rows(get_json(f"{KMB_MIRROR}/kmb/stops/allstops.json")):
        sid=str(item.get("stop") or item.get("stop_id") or item.get("id") or "")
        if not sid: continue
        rv=item.get("routes") or []
        if isinstance(rv,str): rv=[x.strip() for x in rv.split(',') if x.strip()]
        try: lat=float(item.get("lat") or item.get("latitude") or 0); lon=float(item.get("long") or item.get("lon") or item.get("longitude") or 0)
        except (TypeError,ValueError): lat=lon=0
        result[sid]={"name":item.get("name_tc") or item.get("name_zh") or item.get("name") or f"車站 {sid}","lat":lat,"lon":lon,"routes":sorted({str(x) for x in rv},key=sort_key)}
    if not result: raise ValueError("九巴車站資料為空")
    return result

@st.cache_data(ttl=86400,show_spinner="正在下載九巴／龍運路線資料...")
def kmb_routes():
    try:
        r=rows(get_json(f"{KMB_MIRROR}/kmb/routes/allroutes.json"))
        if r:return r
    except Exception: pass
    return get_json("https://data.etabus.gov.hk/v1/transport/kmb/route").get("data",[])

def rnum(x): return str(x.get("route") or x.get("route_id") or x.get("route_no") or x.get("id") or "")
def rbound(x):
    v=str(x.get("bound") or x.get("dir") or x.get("direction") or "O").lower()
    return "I" if v in ("i","inbound","in") else "O"
def rst(x): return str(x.get("service_type") or x.get("serviceType") or "1")
def rdest(x,b):
    return (x.get("dest_tc") or x.get("destination_tc") or x.get("dest") or "去程") if b=="O" else (x.get("orig_tc") or x.get("origin_tc") or x.get("orig") or x.get("dest_tc") or "回程")

def parse_eta(v): return datetime.fromisoformat(v) if v else None
def eta_label(t):
    now=datetime.now(t.tzinfo) if t.tzinfo else datetime.now(); m=math.floor((t-now).total_seconds()/60)
    return "即將抵達" if m<=0 else f"{m} 分鐘"

def show_kmb_eta(stop,route,bound=None,service_type="1"):
    try: data=get_json(f"https://data.etabus.gov.hk/v1/transport/kmb/eta/{stop}/{route}/{service_type}").get("data",[])
    except Exception as e: st.error(f"未能下載九巴／龍運到站資料：{e}"); return
    data=[x for x in data if (not bound or x.get("dir")==bound) and (x.get("eta") or x.get("rmk_tc"))]
    if not data: st.info("此方向目前沒有即將到達的班次。")
    for x in data:
        t=parse_eta(x.get("eta")); dest=x.get("dest_tc") or "未知終點"; remark=x.get("rmk_tc") or ""
        if t: st.success(f"🚌 **{route} 往 {dest}**｜**{eta_label(t)}**（{t.strftime('%H:%M')}） {remark}")
        else: st.warning(f"🚌 **{route} 往 {dest}**｜{remark or '未有實時資料'}")

def show_mtr(line,station):
    try: data=get_json(f"https://rt.data.gov.hk/v1/transport/mtr/getSchedule.php?line={line}&sta={station}&lang=tc").get("data",{}).get(f"{line}-{station}",{})
    except Exception as e: st.error(f"未能下載港鐵資料：{e}"); return
    if not data: st.info("此站目前沒有列車資料。"); return
    c1,c2=st.columns(2)
    for c,k,title in ((c1,"UP","⬆️ 上行"),(c2,"DOWN","⬇️ 下行")):
        with c:
            st.markdown(f"**{title}**")
            for x in data.get(k,[]): st.success(f"**{x.get('plat','-')} 號月台 ➜ {ALL_STATIONS.get(x.get('dest'),x.get('dest') or '未知終點')}**｜{x.get('ttnt','-')} 分鐘")

@st.cache_data(ttl=86400)
def ctb_routes(): return get_json("https://rt.data.gov.hk/v1/transport/citybus-nwfb/route/ctb").get("data",[])
@st.cache_data(ttl=3600)
def ctb_stops(route,direction):
    b="https://rt.data.gov.hk/v1/transport/citybus-nwfb"; rs=get_json(f"{b}/route-stop/ctb/{route}/{direction}").get("data",[]); d={}
    for x in rs:
        sid=x.get("stop")
        if sid:d[sid]=get_json(f"{b}/stop/{sid}").get("data",{})
    return rs,d
def show_ctb(stop,route,direction):
    try:data=[x for x in get_json(f"https://rt.data.gov.hk/v1/transport/citybus-nwfb/eta/ctb/{stop}/{route}").get("data",[]) if x.get("dir")==direction]
    except Exception as e:st.error(f"未能下載城巴資料：{e}");return
    if not data:st.info("目前沒有即將到達的班次。")
    for x in data:
        t=parse_eta(x.get("eta")); st.success(f"🟡 **往 {x.get('dest_tc','未知終點')}**｜**{eta_label(t)}**（{t.strftime('%H:%M')}）") if t else st.warning(x.get("rmk_tc") or "未有實時資料")

st.title("🇭🇰 香港交通實時到站")
near,mtr,kmb,ctb=st.tabs(["📍 附近路線","🚇 港鐵","🚌 九巴及龍運","🟡 城巴"])
with near:
    st.subheader("📍 尋找附近巴士站"); radius=st.slider("搜尋範圍（米）",200,2000,500,100)
    st.markdown("#### 按下方 **Get Location** 按鈕取得 GPS 位置")
    location=streamlit_geolocation()
    with st.expander("若看不到 GPS 按鈕，可手動輸入位置"):
        manual=st.checkbox("使用手動位置"); c1,c2=st.columns(2); ml=c1.number_input("緯度",value=22.3692,format="%.6f"); mn=c2.number_input("經度",value=114.1201,format="%.6f")
    lat=lon=None
    if isinstance(location,dict) and location.get("latitude") is not None: lat=float(location["latitude"]);lon=float(location["longitude"]);st.success(f"✅ GPS 位置：{lat:.5f}, {lon:.5f}")
    elif manual:lat,lon=ml,mn;st.success(f"✅ 手動位置：{lat:.5f}, {lon:.5f}")
    else:st.warning("請按 Get Location 並允許瀏覽器取得位置，或展開手動位置。")
    if lat is not None:
        try:
            sd=kmb_stops(); rd=kmb_routes(); nearby=[]
            for sid,info in sd.items():
                if info["lat"] and info["lon"]:
                    d=dist(lat,lon,info["lat"],info["lon"])
                    if d<=radius:nearby.append((sid,info,d))
            nearby.sort(key=lambda x:x[2])
            available=sorted({r for _,i,_ in nearby for r in i["routes"]},key=sort_key)
            if not available:st.warning("範圍內找不到九巴／龍運車站，請增大搜尋範圍。")
            else:
                route=st.selectbox("1. 選擇路線",available,key="near_route")
                meta=[x for x in rd if rnum(x)==route]; dirs={}
                for x in meta:
                    b=rbound(x);sv=rst(x);dirs[f"{b}_{sv}"]=f"往 {rdest(x,b)}（班次類型 {sv}）"
                if not dirs:dirs={"O_1":"去程","I_1":"回程"}
                direction=st.selectbox("2. 選擇方向",list(dirs),format_func=lambda x:dirs[x],key="near_dir");bound,stype=direction.split("_",1)
                filtered=[x for x in nearby if route in x[1]["routes"]]
                opts={sid:f"{i['name']}（{int(d)} 米）" for sid,i,d in filtered}
                if not opts:st.info("所選路線在目前搜尋範圍內沒有車站。")
                else:
                    stop=st.selectbox("3. 選擇附近車站",list(opts),format_func=lambda x:opts[x],key="near_stop");st.divider();show_kmb_eta(stop,route,bound,stype)
        except Exception as e:st.error(f"未能下載附近巴士資料：{e}")
with mtr:
    st.subheader("🚇 港鐵下班車");line=st.selectbox("選擇港鐵路綫",list(MTR_DATA),format_func=lambda x:MTR_DATA[x]["name"]);station=st.selectbox("選擇車站",list(MTR_DATA[line]["stations"]),format_func=lambda x:MTR_DATA[line]["stations"][x]);st.divider();show_mtr(line,station)
with kmb:
    st.subheader("🚌 九巴及龍運下班車")
    try:
        sd=kmb_stops();rd=kmb_routes();routes=sorted({r for i in sd.values() for r in i["routes"]},key=sort_key);route=st.selectbox("1. 選擇路線",routes,key="k_route")
        meta=[x for x in rd if rnum(x)==route];dirs={}
        for x in meta:
            b=rbound(x);sv=rst(x);dirs[f"{b}_{sv}"]=f"往 {rdest(x,b)}（班次類型 {sv}）"
        if not dirs:dirs={"O_1":"去程","I_1":"回程"}
        direction=st.selectbox("2. 選擇方向",list(dirs),format_func=lambda x:dirs[x],key="k_dir");bound,stype=direction.split("_",1)
        opts={sid:i["name"] for sid,i in sd.items() if route in i["routes"]};stop=st.selectbox("3. 選擇車站",list(opts),format_func=lambda x:opts[x],key="k_stop");st.divider();show_kmb_eta(stop,route,bound,stype)
    except Exception as e:st.error(f"未能下載九巴／龍運資料：{e}")
with ctb:
    st.subheader("🟡 城巴下班車")
    try:
        data=ctb_routes();routes=sorted({x["route"] for x in data},key=sort_key);route=st.selectbox("1. 選擇路線",routes,key="c_route");meta=next(x for x in data if x["route"]==route);ds={"outbound":f"往 {meta.get('dest_tc','終點站')}","inbound":f"往 {meta.get('orig_tc','起點站')}"};di=st.selectbox("2. 選擇方向",list(ds),format_func=lambda x:ds[x]);rs,details=ctb_stops(route,di);opts={x["stop"]:f"{x.get('seq','-')}. {details.get(x['stop'],{}).get('name_tc','未知車站')}" for x in rs};stop=st.selectbox("3. 選擇車站",list(opts),format_func=lambda x:opts[x]);st.divider();show_ctb(stop,route,"O" if di=="outbound" else "I")
    except Exception as e:st.error(f"未能下載城巴資料：{e}")
