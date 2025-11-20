import streamlit as st
import requests
import pandas as pd
import json
import scraper # Import file scraper.py

# -----------------------------------------------------------------------------
# CẤU HÌNH
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Soi Cầu Ảnh", page_icon="📸", layout="wide")

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div.stButton > button {width: 100%; height: 3em; font-weight: bold;}
    .hot-box {background-color:#ffebee; border:2px solid #ef5350; border-radius:8px; padding:10px; text-align:center;}
    .hot-val {font-size:26px; color:#d32f2f; font-weight:900;}
    textarea {font-family: monospace; font-size: 16px !important; letter-spacing: 2px;}
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
# HÀM XỬ LÝ
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_history():
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(API_URL, headers=h, timeout=10).json()
        return r.get('t', {}).get('issueList', [])
    except: return []

def parse_detail(d_str):
    try: return "".join([g.replace(",", "").strip() for g in json.loads(d_str)])
    except: return ""

def get_set(n): return NUMBER_TO_SET_MAP.get(str(n), "?")

def process_data(raw):
    p = []
    for r in raw:
        f = parse_detail(r.get('detail', ''))
        if len(f) != 107: continue
        de = f[2:5][1:]
        p.append({"issue": r.get('turnNum'), "de": de, "de_rev": de[::-1], "de_set": get_set(de), "body": f})
    return p

def get_pos_map():
    m = []
    for p, c, l in XSMB_STRUCTURE:
        for i in range(1, c+1): m.append(f"{p}.{i}.{j}" for j in range(1, l+1))
    # Flatten logic
    flat = []
    for p, c, l in XSMB_STRUCTURE:
        for i in range(1, c+1):
            for j in range(1, l+1): flat.append(f"{p}.{i}.{j}")
    return flat

def get_prize_map_no_gdb():
    m = {}; curr = 0
    for p, c, l in XSMB_STRUCTURE:
        for i in range(1, c+1):
            s, e = curr, curr + l
            if p != "GĐB": m[f"{p}" if c==1 else f"{p}.{i}"] = (s, e)
            curr += l
    return m

# -----------------------------------------------------------------------------
# ALGORITHMS
# -----------------------------------------------------------------------------
def auto_scan_positions(data, mode, allow_rev):
    if not data: return []
    day0 = data[0]; body = day0['body']; cand = []
    # Start index 5 to skip GĐB
    for i in range(5, len(body)):
        for j in range(5, len(body)):
            if i == j: continue
            v = body[i] + body[j]
            match = False
            if mode == "straight":
                if v == day0['de']: match = True
                elif allow_rev and v == day0['de_rev']: match = True
            else:
                if get_set(v) == day0['de_set']: match = True
            if match: cand.append((i, j))
    
    res = []
    for (i, j) in cand:
        strk = 0
        for day in data:
            v = day['body'][i] + day['body'][j]
            match = False
            if mode == "straight":
                if v == day['de']: match = True
                elif allow_rev and v == day['de_rev']: match = True
            else:
                if get_set(v) == day['de_set']: match = True
            if match: strk += 1
            else: break
        if strk >= 2: res.append({"i": i, "j": j, "streak": strk})
    res.sort(key=lambda x: x['streak'], reverse=True)
    return res

def check_prize(p_str, de, mode):
    d = set(p_str)
    if mode == "straight": return (de[0] in d) and (de[1] in d)
    else:
        for n in BO_DE_DICT.get(get_set(de), []):
            if (n[0] in d) and (n[1] in d): return True
        return False

def auto_scan_prizes(data, mode):
    pmap = get_prize_map_no_gdb(); res = []
    for p, (s, e) in pmap.items():
        strk = 0
        for d in data:
            if check_prize(d['body'][s:e], d['de'], mode): strk += 1
            else: break
        if strk >= 2: res.append({"prize": p, "streak": strk, "val": data[0]['body'][s:e]})
    res.sort(key=lambda x: x['streak'], reverse=True)
    return res

def auto_scan_tam_cang(data):
    res = []
    for k in range(5, len(data[0]['body'])):
        strk = 0
        for d in data:
            if d['body'][k] == d['tam_cang']: strk += 1
            else: break
        if strk >= 2: res.append({"idx": k, "streak": strk})
    res.sort(key=lambda x: x['streak'], reverse=True)
    return res

# -----------------------------------------------------------------------------
# MAIN UI
# -----------------------------------------------------------------------------
def main():
    st.title("📸 Soi Cầu Ảnh (OCR)")
    
    if 'saved_bridges' not in st.session_state: st.session_state['saved_bridges'] = []
    if 'saved_prizes' not in st.session_state: st.session_state['saved_prizes'] = []
    if 'saved_cang' not in st.session_state: st.session_state['saved_cang'] = []
    if 'ocr_result_list' not in st.session_state: st.session_state['ocr_result_list'] = []

    # --- BƯỚC 1: CHỌN PHƯƠNG PHÁP & QUÉT LỊCH SỬ ---
    c1, c2, c3 = st.columns(3)
    with c1: method = st.selectbox("Phương Pháp", ["1. Cầu Vị Trí", "2. Cầu Giải", "3. Cầu 3 Càng"])
    with c2: is_set = st.checkbox("Soi Bộ", False); mode = "set" if is_set else "straight"
    with c3: allow_rev = st.checkbox("Đảo AB", True) if not is_set and "Vị Trí" in method else True
    
    raw = fetch_history()
    if not raw: st.error("Lỗi API"); return
    data = process_data(raw)
    pos_map = get_pos_map()

    # Tự động quét ngầm khi load trang để sẵn sàng ốp
    if not st.session_state['saved_bridges'] and not st.session_state['saved_prizes']:
        with st.spinner("Đang quét lịch sử..."):
            if "Vị Trí" in method or "3 Càng" in method:
                st.session_state['saved_bridges'] = auto_scan_positions(data, mode, allow_rev)[:30]
                st.session_state['saved_cang'] = auto_scan_tam_cang(data)[:10]
            if "Cầu Giải" in method:
                st.session_state['saved_prizes'] = auto_scan_prizes(data, mode)
        st.toast("Đã quét xong lịch sử!", icon="✅")

    # --- BƯỚC 2: UPLOAD ẢNH ---
    st.divider()
    st.subheader("📸 Upload Ảnh Bảng Kết Quả (Minh Ngọc/Rồng Bạch Kim...)")
    
    uploaded_file = st.file_uploader("Chọn ảnh chụp màn hình", type=['png', 'jpg', 'jpeg'])
    
    if uploaded_file is not None:
        # Xử lý OCR
        with st.spinner("Đang đọc số từ ảnh..."):
            raw_nums = scraper.extract_numbers_from_image(uploaded_file)
            
        st.info(f"Tìm thấy {len(raw_nums)} số. Hệ thống cần 27 số (GĐB -> G7).")
        
        # Cho phép sửa tay trước khi ốp
        nums_text = " ".join(raw_nums)
        edited_text = st.text_area("Kiểm tra & Sửa danh sách số (Cách nhau khoảng trắng)", nums_text, height=100)
        
        if st.button("🚀 XÁC NHẬN & ỐP CẦU", type="primary"):
            # Parse lại từ text area
            final_nums = edited_text.split()
            full_str_live = scraper.map_numbers_to_107_str(final_nums)
            
            # Hiển thị kết quả ốp
            st.write("---")
            st.subheader("⚡ KẾT QUẢ ỐP CẦU")
            
            # LOGIC HIỂN THỊ GIỐNG HỆT BÀI TRƯỚC, CHỈ THAY DATA ĐẦU VÀO
            # A. VỊ TRÍ
            if "Vị Trí" in method or "3 Càng" in method:
                bridges = st.session_state['saved_bridges']
                if not bridges: st.warning("Chưa có cầu lịch sử.")
                else:
                    cols = st.columns(5); count = 0
                    for idx, br in enumerate(bridges):
                        i, j = br['i'], br['j']
                        if i < len(full_str_live) and j < len(full_str_live):
                            vi, vj = full_str_live[i], full_str_live[j]
                            if vi != '?' and vj != '?':
                                with cols[count%5]:
                                    st.markdown(f"<div class='hot-box'><div style='font-size:10px'>Cầu #{idx+1} ({br['streak']}n)</div><div style='font-size:11px'>{pos_map[i]}+{pos_map[j]}</div><div class='hot-val'>{vi}{vj}</div></div>", unsafe_allow_html=True)
                                count += 1
                    if count == 0: st.warning("Không khớp được cầu nào (hoặc dữ liệu ảnh thiếu).")

            # B. GIẢI
            if "Cầu Giải" in method:
                prizes = st.session_state['saved_prizes']
                pmap = get_prize_map_no_gdb()
                found = False
                for p in prizes:
                    pname = p['prize']
                    s, e = pmap.get(pname)
                    if s < len(full_str_live) and e <= len(full_str_live):
                        val = full_str_live[s:e]
                        if '?' not in val:
                            st.success(f"✅ **{pname}** (Thông {p['streak']}n): {val}")
                            found = True
                if not found: st.warning("Chưa có giải nào khớp.")

if __name__ == "__main__":
    main()
