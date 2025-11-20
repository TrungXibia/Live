import streamlit as st
import requests
import pandas as pd
import json

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH & CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Auto Scan: Max Streak", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div.stButton > button {width: 100%; height: 3em; font-weight: bold; background-color: #FF4B4B; color: white;}
    thead tr th:first-child {display:none}
    tbody th {display:none}
    .big-font {font-size:20px !important; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DATA & CONSTANTS
# -----------------------------------------------------------------------------
API_URL = "https://www.kqxs88.live/api/front/open/lottery/history/list/game?limitNum=50&gameCode=miba" 
# Tăng limit lên 50 để quét được cầu siêu dài

XSMB_STRUCTURE = [
    ("GĐB", 1, 5), ("G1", 1, 5), ("G2", 2, 5), ("G3", 6, 5),
    ("G4", 4, 4), ("G5", 6, 4), ("G6", 3, 3), ("G7", 4, 2)
]

BO_DE_DICT = {
    "00": ["00", "55", "05", "50"], "11": ["11", "66", "16", "61"],
    "22": ["22", "77", "27", "72"], "33": ["33", "88", "38", "83"],
    "44": ["44", "99", "49", "94"], "01": ["01", "10", "06", "60", "51", "15", "56", "65"],
    "02": ["02", "20", "07", "70", "52", "25", "57", "75"],
    "03": ["03", "30", "08", "80", "53", "35", "58", "85"],
    "04": ["04", "40", "09", "90", "54", "45", "59", "95"],
    "12": ["12", "21", "17", "71", "62", "26", "67", "76"],
    "13": ["13", "31", "18", 81, "63", "36", "68", "86"],
    "14": ["14", "41", "19", "91", "64", "46", "69", "96"],
    "23": ["23", "32", "28", "82", "73", "37", "78", "87"],
    "24": ["24", "42", "29", "92", "74", "47", "79", "97"],
    "34": ["34", "43", "39", "93", "84", "48", "89", "98"]
}
NUMBER_TO_SET_MAP = {str(n): s for s, nums in BO_DE_DICT.items() for n in nums}

# -----------------------------------------------------------------------------
# 3. HÀM XỬ LÝ DỮ LIỆU
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_data():
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
            "de": de,
            "de_rev": de[::-1],
            "de_set": get_set(de),
            "tam_cang": target_3c[0],
            "body": full
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
# 4. THUẬT TOÁN TỰ ĐỘNG (AUTO STREAK CALCULATION)
# -----------------------------------------------------------------------------

# --- A. SOI VỊ TRÍ ---
def auto_scan_positions(data, mode, allow_rev):
    if not data: return []
    day0 = data[0]
    body = day0['body']
    
    # Bước 1: Tìm những cặp ăn ngày hôm nay (Ngày 0)
    # Bắt đầu từ index 5 (BỎ GĐB)
    candidates = []
    start_idx = 5 
    
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
    
    # Bước 2: Với mỗi ứng viên, lùi về quá khứ đếm xem thông bao nhiêu ngày
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
            else: break # Gãy cầu -> Dừng đếm
        
        if streak >= 2: # Chỉ lấy cầu từ 2 ngày trở lên
            results.append({"i": i, "j": j, "streak": streak})
            
    # Bước 3: Sắp xếp từ cao xuống thấp
    results.sort(key=lambda x: x['streak'], reverse=True)
    return results

# --- B. SOI GIẢI (NHỊ HỢP) ---
def check_prize(p_str, de, mode):
    digits = set(p_str)
    if mode == "straight":
        return (de[0] in digits) and (de[1] in digits)
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
            p_str = day['body'][s:e]
            if check_prize(p_str, day['de'], mode): streak += 1
            else: break
            
        if streak >= 2:
            results.append({
                "prize": p_name,
                "streak": streak,
                "val": data[0]['body'][s:e]
            })
            
    results.sort(key=lambda x: x['streak'], reverse=True)
    return results

# --- C. SOI TÂM CÀNG ---
def auto_scan_tam_cang(data):
    res = []
    for k in range(5, len(data[0]['body'])):
        streak = 0
        for day in data:
            if day['body'][k] == day['tam_cang']: streak += 1
            else: break
        if streak >= 2:
            res.append({"idx": k, "streak": streak})
    res.sort(key=lambda x: x['streak'], reverse=True)
    return res

# -----------------------------------------------------------------------------
# 5. GIAO DIỆN CHÍNH
# -----------------------------------------------------------------------------
def main():
    st.title("⚡ Auto Soi Cầu: Tự Động Quét & Sắp Xếp")
    
    # --- MENU ĐƠN GIẢN ---
    c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 1.5])
    with c1:
        method = st.selectbox("🎯 Chọn Phương Pháp", ["1. Cầu Vị Trí (Cặp Số)", "2. Cầu Giải (Nhị Hợp)", "3. Cầu 3 Càng"])
    with c2:
        is_set = st.checkbox("Soi Bộ Đề", False)
        mode = "set" if is_set else "straight"
    with c3:
        allow_rev = True
        if not is_set and ("Vị Trí" in method or "3 Càng" in method):
            allow_rev = st.checkbox("Đảo AB", True)
    with c4:
        st.write("")
        btn = st.button("QUÉT TỰ ĐỘNG", type="primary")

    st.divider()
    
    raw = fetch_data()
    if not raw:
        st.error("Lỗi kết nối API.")
        return
        
    data = process_data(raw)
    pos_map = get_pos_map()
    
    # --- SHOW HISTORY ---
    st.subheader("📅 Lịch sử 5 ngày")
    if len(data) >= 5:
        h = [{"Ngày": d['issue'], "Đề": d['de'], "Bộ": d['de_set']} for d in data[:5]]
        st.dataframe(pd.DataFrame(h).T, use_container_width=True)
        
    # --- EXECUTE ---
    if btn:
        st.write("---")
        st.markdown("### 🏆 BẢNG XẾP HẠNG CẦU (DÀI NHẤT Ở TRÊN)")
        
        # 1. VỊ TRÍ
        if "Vị Trí" in method:
            with st.spinner("Đang tự động tính toán streak cho hàng ngàn vị trí..."):
                res = auto_scan_positions(data, mode, allow_rev)
            
            if res:
                rows = []
                for r in res[:100]: # Show top 100
                    val = data[0]['body'][r['i']] + data[0]['body'][r['j']]
                    rows.append({
                        "Hạng": f"#{len(rows)+1}",
                        "Vị trí 1": pos_map[r['i']],
                        "Vị trí 2": pos_map[r['j']],
                        "Độ Dài Cầu": f"{r['streak']} ngày 🔥",
                        "Báo số hôm nay": val
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else:
                st.warning("Không tìm thấy cầu nào chạy thông trên 2 ngày.")

        # 2. NHỊ HỢP
        elif "Cầu Giải" in method:
            with st.spinner("Đang quét G1-G7..."):
                res = auto_scan_prizes(data, mode)
            
            if res:
                rows = []
                for r in res:
                    rows.append({
                         "Hạng": f"#{len(rows)+1}",
                         "Tên Giải": r['prize'],
                         "Độ Dài Cầu": f"{r['streak']} ngày 🔥",
                         "Dữ liệu giải": r['val']
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True
