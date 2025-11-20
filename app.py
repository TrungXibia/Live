import streamlit as st
import requests
import pandas as pd
import json
import scraper  # <--- IMPORT FILE VỪA TẠO

# -----------------------------------------------------------------------------
# CẤU HÌNH
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Soi Cầu Pro: Live Minh Ngọc", page_icon="⚔️", layout="wide")

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div.stButton > button {width: 100%; height: 3em; font-weight: bold;}
    thead tr th:first-child {display:none}
    tbody th {display:none}
    .hot-box {background-color:#ffebee; border:2px solid #ef5350; border-radius:8px; padding:10px; text-align:center; margin-bottom:10px;}
    .hot-val {font-size:26px; color:#d32f2f; font-weight:900;}
    .live-progress {font-weight:bold; color:#2e7d32;}
</style>
""", unsafe_allow_html=True)

API_URL = "https://www.kqxs88.live/api/front/open/lottery/history/list/game?limitNum=50&gameCode=miba"

XSMB_STRUCTURE = [
    ("GĐB", 1, 5), ("G1", 1, 5), ("G2", 2, 5), ("G3", 6, 5),
    ("G4", 4, 4), ("G5", 6, 4), ("G6", 3, 3), ("G7", 4, 2)
]

BO_DE_DICT = {
    "00": ["00","55","05","50"], "11": ["11","66","16","61"], "22": ["22","77","27","72"], "33": ["33","88","38","83"],
    "44": ["44","99","49","94"], "01": ["01","10","06","60","51","15","56","65"], "02": ["02","20","07","70","52","25","57","75"],
    "03": ["03","30","08","80","53","35","58","85"], "04": ["04","40","09","90","54","45","59","95"],
    "12": ["12","21","17","71","62","26","67","76"], "13": ["13","31","18","81","63","36","68","86"],
    "14": ["14","41","19","91","64","46","69","96"], "23": ["23","32","28","82","73","37","78","87"],
    "24": ["24","42","29","92","74","47","79","97"], "34": ["34","43","39","93","84","48","89", "98"]
}
NUMBER_TO_SET_MAP = {str(n): s for s, nums in BO_DE_DICT.items() for n in nums}

# -----------------------------------------------------------------------------
# HÀM XỬ LÝ (LOGIC CŨ)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_history_data():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(API_URL, headers=headers, timeout=10)
        return resp.json().get('t', {}).get('issueList', [])
    except: return []

def parse_detail(d_str):
    try:
        return "".join([g.replace(",", "").strip() for g in json.loads(d_str)])
    except: return ""

def get_set(n): return NUMBER_TO_SET_MAP.get(str(n), "?")

def process_data(raw):
    processed = []
    for i, rec in enumerate(raw):
        full = parse_detail(rec.get('detail', ''))
        if len(full) != 107: continue
        target_3c = full[2:5]
        de = target_3c[1:]
        processed.append({
            "issue": rec.get('turnNum'),
            "de": de, "de_rev": de[::-1], "de_set": get_set(de), "tam_cang": target_3c[0], "body": full
        })
    return processed

def get_pos_map():
    m = []
    for p, c, l in XSMB_STRUCTURE:
        for i in range(1, c+1):
            for j in range(1, l+1): m.append(f"{p}.{i}.{j}")
    return m

def get_prize_map_no_gdb():
    m = {}
    curr = 0
    for p, c, l in XSMB_STRUCTURE:
        for i in range(1, c+1):
            s, e = curr, curr + l
            if p != "GĐB":
                key = f"{p}" if c == 1 else f"{p}.{i}"
                m[key] = (s, e)
            curr += l
    return m

# -----------------------------------------------------------------------------
# ALGORITHMS
# -----------------------------------------------------------------------------
def auto_scan_positions(data, mode, allow_rev):
    if not data: return []
    day0 = data[0]; body = day0['body']; candidates = []; start_idx = 5 
    for i in range(start_idx, len(body)):
        for j in range(start_idx, len(body)):
            if i == j: continue
            val = body[i] + body[j]
            match = False
            if mode == "straight":
                if val == day0['de']: match = True
                elif allow_rev and val == day0['de_rev']: match = True
            else:
                if get_set(val) == day0['de_set']: match = True
            if match: candidates.append((i, j))
    
    results = []
    for (i, j) in candidates:
        streak = 0
        for day in data:
            val = day['body'][i] + day['body'][j]
            match = False
            if mode == "straight":
                if val == day['de']: match = True
                elif allow_rev and val == day['de_rev']: match = True
            else:
                if get_set(val) == day['de_set']: match = True
            if match: streak += 1
            else: break 
        if streak >= 2: results.append({"i": i, "j": j, "streak": streak})
    results.sort(key=lambda x: x['streak'], reverse=True)
    return results

def check_prize(p_str, de, mode):
    digits = set(p_str)
    if mode == "straight": return (de[0] in digits) and (de[1] in digits)
    else:
        nums = BO_DE_DICT.get(get_set(de), [])
        for n in nums:
            if (n[0] in digits) and (n[1] in digits): return True
        return False

def auto_scan_prizes(data, mode):
    prize_map = get_prize_map_no_gdb()
    results = []
    for p_name, (s, e) in prize_map.items():
        streak = 0
        for day in data:
            if check_prize(day['body'][s:e], day['de'], mode): streak += 1
            else: break
        if streak >= 2: results.append({"prize": p_name, "streak": streak, "val": data[0]['body'][s:e]})
    results.sort(key=lambda x: x['streak'], reverse=True)
    return results

def auto_scan_tam_cang(data):
    res = []
    for k in range(5, len(data[0]['body'])):
        streak = 0
        for day in data:
            if day['body'][k] == day['tam_cang']: streak += 1
            else: break
        if streak >= 2: res.append({"idx": k, "streak": streak})
    res.sort(key=lambda x: x['streak'], reverse=True)
    return res

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
def main():
    st.title("🔥 Chiến Trường XSMB (Scraper Tách Biệt)")

    if 'saved_bridges' not in st.session_state: st.session_state['saved_bridges'] = []
    if 'saved_prizes' not in st.session_state: st.session_state['saved_prizes'] = []
    if 'saved_cang' not in st.session_state: st.session_state['saved_cang'] = []
    if 'pos_map' not in st.session_state: st.session_state['pos_map'] = get_pos_map()

    c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 1.5])
    with c1: method = st.selectbox("Phương Pháp", ["1. Cầu Vị Trí", "2. Cầu Giải", "3. Cầu 3 Càng"])
    with c2: is_set = st.checkbox("Soi Bộ", False); mode = "set" if is_set else "straight"
    with c3: allow_rev = st.checkbox("Đảo AB", True) if not is_set and "Vị Trí" in method or "3 Càng" in method else True
    with c4: st.write(""); btn = st.button("QUÉT AUTO", type="primary")

    st.divider()
    raw = fetch_history_data()
    if not raw: st.error("Lỗi API"); return
    data = process_data(raw)
    pos_map = get_pos_map()

    st.subheader("📅 Lịch sử 5 ngày")
    if len(data)>=5: st.dataframe(pd.DataFrame([{"Ngày": d['issue'], "Đề": d['de'], "Bộ": d['de_set']} for d in data[:5]]).T, use_container_width=True)

    if btn:
        st.session_state['saved_bridges'] = []
        st.session_state['saved_prizes'] = []
        st.session_state['saved_cang'] = []
        st.write("---")
        
        if "Vị Trí" in method:
            with st.spinner("Scanning..."): res = auto_scan_positions(data, mode, allow_rev)
            if res:
                st.session_state['saved_bridges'] = res[:30]
                rows = [{"Hạng":f"#{i+1}", "V1": pos_map[r['i']], "V2": pos_map[r['j']], "Thông": f"{r['streak']}n", "Báo": data[0]['body'][r['i']]+data[0]['body'][r['j']]} for i,r in enumerate(res[:50])]
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else: st.warning("Không tìm thấy cầu.")
            
        elif "Cầu Giải" in method:
            res = auto_scan_prizes(data, mode)
            st.session_state['saved_prizes'] = res
            if res:
                rows = [{"Giải": r['prize'], "Thông": f"{r['streak']}n", "Dữ liệu": r['val']} for r in res]
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else: st.warning("Không tìm thấy cầu.")

        elif "3 Càng" in method:
            tc = auto_scan_tam_cang(data)
            de = auto_scan_positions(data, mode, allow_rev)
            st.session_state['saved_cang'] = tc[:10]
            st.session_state['saved_bridges'] = de[:20]
            st.success("Đã lưu cầu Càng & Đề.")

    st.write("---")
    st.header("🔴 LIVE MONITOR (Minh Ngọc)")
    
    col_l, col_s = st.columns([1, 3])
    with col_l: 
        refresh = st.button("🔄 CẬP NHẬT LIVE", type="primary")
    
    # GỌI HÀM TỪ FILE SCRAPER.PY
    live_str, filled_len = scraper.get_live_xsmb_minhngoc()
    
    with col_s:
        if live_str:
            pct = int((filled_len/107)*100)
            st.markdown(f"<div class='live-progress'>{filled_len}/107 ({pct}%)</div>", unsafe_allow_html=True)
            st.progress(pct)
        else:
            st.error(f"Lỗi cào: {filled_len}")
            return

    # ỐP CẦU
    if not st.session_state.get('saved_bridges') and not st.session_state.get('saved_prizes'):
        st.info("Bấm QUÉT AUTO trước.")
    else:
        st.subheader("⚡ CẦU ĐANG NỔ")
        
        # 1. VỊ TRÍ / 3 CÀNG
        saved_b = st.session_state.get('saved_bridges', [])
        if saved_b:
            cols = st.columns(5)
            c = 0
            for idx, br in enumerate(saved_b):
                i, j = br['i'], br['j']
                val_i, val_j = live_str[i], live_str[j]
                if val_i != '?' and val_j != '?':
                    pred = val_i + val_j
                    with cols[c % 5]:
                        st.markdown(f"<div class='hot-box'><div style='font-size:10px'>Cầu #{idx+1} ({br['streak']}n)</div><div style='font-size:11px'>{pos_map[i]}+{pos_map[j]}</div><div class='hot-val'>{pred}</div></div>", unsafe_allow_html=True)
                    c += 1
            if c == 0: st.info("Cầu vị trí chưa nổ số.")

        # 2. GIẢI
        saved_p = st.session_state.get('saved_prizes', [])
        if saved_p:
            st.write("Trạng thái Cầu Giải:")
            prize_map = get_prize_map_no_gdb()
            found = False
            for p in saved_p:
                p_name = p['prize']
                s, e = prize_map.get(p_name)
                live_p = live_str[s:e]
                if '?' not in live_p:
                    st.success(f"✅ **{p_name}** ({p['streak']}n): {live_p}")
                    found = True
            if not found: st.info("Các giải chưa quay xong.")

if __name__ == "__main__":
    main()
