import streamlit as st
import requests
import pandas as pd
import json
import re

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH & CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Soi Cầu: Copy & Paste", page_icon="📋", layout="wide")

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div.stButton > button {width: 100%; height: 3em; font-weight: bold;}
    thead tr th:first-child {display:none}
    tbody th {display:none}
    
    /* Box kết quả */
    .hot-box {
        background-color: #e3f2fd; border: 2px solid #1565c0; 
        border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 10px;
    }
    .hot-title {font-size: 11px; color: #0d47a1; font-weight: bold;}
    .hot-val {font-size: 26px; color: #d32f2f; font-weight: 900;}
    
    /* Input area */
    .stTextArea textarea {font-size: 16px; font-family: monospace;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. CẤU TRÚC DỮ LIỆU
# -----------------------------------------------------------------------------
API_URL = "https://www.kqxs88.live/api/front/open/lottery/history/list/game?limitNum=50&gameCode=miba"

# Thứ tự chuẩn 27 giải của XSMB
# [GĐB(1), G1(1), G2(2), G3(6), G4(4), G5(6), G6(3), G7(4)]
PRIZE_ORDER = [
    ('GĐB', 5), 
    ('G1', 5), 
    ('G2', 5), ('G2', 5),
    ('G3', 5), ('G3', 5), ('G3', 5), ('G3', 5), ('G3', 5), ('G3', 5),
    ('G4', 4), ('G4', 4), ('G4', 4), ('G4', 4),
    ('G5', 4), ('G5', 4), ('G5', 4), ('G5', 4), ('G5', 4), ('G5', 4),
    ('G6', 3), ('G6', 3), ('G6', 3),
    ('G7', 2), ('G7', 2), ('G7', 2), ('G7', 2)
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
# 3. HÀM XỬ LÝ LỊCH SỬ (API)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_history():
    try:
        r = requests.get(API_URL, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10).json()
        return r.get('t', {}).get('issueList', [])
    except: return []

def parse_detail_json(d_str):
    try: return "".join([g.replace(",", "").strip() for g in json.loads(d_str)])
    except: return ""

def get_set(n): return NUMBER_TO_SET_MAP.get(str(n), "?")

def process_data(raw):
    p = []
    for r in raw:
        f = parse_detail_json(r.get('detail', ''))
        if len(f) != 107: continue
        de = f[2:5][1:] # Lấy 2 số cuối GĐB
        p.append({"issue": r.get('turnNum'), "de": de, "de_rev": de[::-1], "de_set": get_set(de), "tam_cang": f[2], "body": f})
    return p

def get_pos_map():
    # Tạo tên vị trí G1.1.1 v.v...
    m = []
    # Cấu trúc gộp để hiển thị
    struct = [("GĐB",1,5),("G1",1,5),("G2",2,5),("G3",6,5),("G4",4,4),("G5",6,4),("G6",3,3),("G7",4,2)]
    for p, c, l in struct:
        for i in range(1, c+1):
            for j in range(1, l+1): m.append(f"{p}.{i}.{j}")
    return m

def get_prize_map_no_gdb():
    # Map vị trí giải (bỏ GĐB)
    m = {}; curr = 0
    struct = [("GĐB",1,5),("G1",1,5),("G2",2,5),("G3",6,5),("G4",4,4),("G5",6,4),("G6",3,3),("G7",4,2)]
    for p, c, l in struct:
        for i in range(1, c+1):
            s, e = curr, curr + l
            if p != "GĐB": m[f"{p}" if c==1 else f"{p}.{i}"] = (s, e)
            curr += l
    return m

# -----------------------------------------------------------------------------
# 4. HÀM XỬ LÝ TEXT DÁN VÀO (QUAN TRỌNG)
# -----------------------------------------------------------------------------
def parse_pasted_text(text, has_gdb):
    """
    Phân tích văn bản dán vào, tách số và ghép thành chuỗi 107 ký tự.
    has_gdb: True nếu văn bản có chứa GĐB, False nếu bắt đầu từ G1.
    """
    # 1. Tìm tất cả các cụm số trong văn bản
    # Regex tìm số có từ 2 đến 5 chữ số
    raw_nums = re.findall(r'\b\d{2,5}\b', text)
    
    # 2. Lọc lại: Đôi khi dính ngày tháng (2025) hoặc đầu mã (1RS)
    # Ta ưu tiên ghép vào giải.
    
    full_str = ""
    
    # Danh sách giải chuẩn
    # Nếu không có GĐB, ta bỏ phần tử đầu tiên (GĐB) trong PRIZE_ORDER đi để fill sau
    target_prizes = PRIZE_ORDER
    if not has_gdb:
        # Thêm placeholder cho GĐB (5 dấu ?) vào đầu chuỗi kết quả
        full_str += "?????"
        target_prizes = PRIZE_ORDER[1:] # Bắt đầu từ G1
        
    current_num_idx = 0
    
    for p_name, length in target_prizes:
        if current_num_idx < len(raw_nums):
            val = raw_nums[current_num_idx]
            
            # Kiểm tra độ dài. 
            # Nếu số tìm được dài hơn giải (VD tìm thấy 2157312383 mà giải chỉ cần 5 số)
            # Trường hợp dính chùm (Minh Ngọc hay bị): 2157312383 -> Tách đôi
            
            if len(val) > length and len(val) % length == 0:
                # Case đặc biệt: Dính chùm. Cắt ra.
                # Nhưng regex \b\d{2,5}\b có thể đã tách rồi nếu có dấu cách.
                # Nếu user paste dính liền (2157312383), regex trên sẽ ko bắt được (vì > 5).
                # Nên ta dùng regex \d+ rồi xử lý sau thì tốt hơn.
                pass 
                
            # Logic đơn giản: Lấy số tìm được, nhét vào.
            # Nếu độ dài sai lệch -> Pad ?
            if len(val) == length:
                full_str += val
            elif len(val) > length:
                full_str += val[-length:] # Lấy đuôi
            else:
                full_str += val.rjust(length, '?')
            
            current_num_idx += 1
        else:
            # Hết số để điền -> Điền ?
            full_str += "?" * length
            
    # Nếu chưa đủ 107 ký tự, điền nốt ?
    if len(full_str) < 107:
        full_str += "?" * (107 - len(full_str))
        
    # Cắt đúng 107 (nếu thừa)
    return full_str[:107]

def parse_pasted_text_v2(text, has_gdb):
    """
    Phiên bản 2: Xử lý dính chùm tốt hơn (như ví dụ Minh Ngọc G3 dính lẹo)
    """
    # Lấy tất cả các chữ số liền nhau
    all_digits = "".join(re.findall(r'\d+', text))
    
    # Loại bỏ các số rác thường gặp ở đầu (Năm 2025, Ngày 20, 11...)
    # Cái này khó tự động hoàn toàn. Tốt nhất cứ lấy từ trên xuống.
    # Nếu user paste cả ngày tháng thì chịu, user phải xóa tay.
    
    full_str = ""
    current_pos = 0
    
    # Xử lý GĐB
    if not has_gdb:
        full_str += "?????" # Placeholder cho GĐB
        prizes_to_fill = PRIZE_ORDER[1:] # G1 -> G7
    else:
        prizes_to_fill = PRIZE_ORDER # GĐB -> G7
        
    for p_name, length in prizes_to_fill:
        # Cắt chuỗi digits
        if current_pos + length <= len(all_digits):
            val = all_digits[current_pos : current_pos + length]
            full_str += val
            current_pos += length
        else:
            # Không đủ số
            full_str += "?" * length
            
    return full_str[:107]

# -----------------------------------------------------------------------------
# 5. THUẬT TOÁN SOI CẦU (TÁI SỬ DỤNG)
# -----------------------------------------------------------------------------
def auto_scan_positions(data, mode, allow_rev):
    if not data: return []
    day0 = data[0]; body = day0['body']; cand = []; start_idx = 5 
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
            if match: cand.append((i, j))
    res = []
    for (i, j) in cand:
        strk = 0
        for day in data:
            val = day['body'][i] + day['body'][j]
            match = False
            if mode == "straight":
                if val == day['de']: match = True
                elif allow_rev and val == day['de_rev']: match = True
            else:
                if get_set(val) == day['de_set']: match = True
            if match: strk += 1
            else: break
        if strk >= 2: res.append({"i": i, "j": j, "streak": strk})
    res.sort(key=lambda x: x['streak'], reverse=True)
    return res

def auto_scan_prizes(data, mode):
    pmap = get_prize_map_no_gdb(); res = []
    for p, (s, e) in pmap.items():
        strk = 0
        for d in data:
            # Check containment
            digits = set(d['body'][s:e])
            match = False
            if mode == "straight": match = (d['de'][0] in digits and d['de'][1] in digits)
            else:
                for n in BO_DE_DICT.get(get_set(d['de']), []):
                    if n[0] in digits and n[1] in digits: match = True; break
            if match: strk += 1
            else: break
        if strk >= 2: res.append({"prize": p, "streak": strk, "val": data[0]['body'][s:e]})
    res.sort(key=lambda x: x['streak'], reverse=True)
    return res

# -----------------------------------------------------------------------------
# 6. GIAO DIỆN CHÍNH
# -----------------------------------------------------------------------------
def main():
    st.title("📋 Soi Cầu: Copy & Paste (Real-time)")
    
    # Init Session
    if 'saved_bridges' not in st.session_state: st.session_state['saved_bridges'] = []
    if 'saved_prizes' not in st.session_state: st.session_state['saved_prizes'] = []
    if 'pos_map' not in st.session_state: st.session_state['pos_map'] = get_pos_map()

    # --- BƯỚC 1: QUÉT LỊCH SỬ ---
    c1, c2, c3 = st.columns(3)
    with c1: method = st.selectbox("Phương Pháp", ["1. Cầu Vị Trí", "2. Cầu Giải"])
    with c2: is_set = st.checkbox("Soi Bộ", False); mode = "set" if is_set else "straight"
    with c3: allow_rev = st.checkbox("Đảo AB", True) if not is_set and "Vị Trí" in method else True
    
    raw = fetch_history()
    data = process_data(raw)
    
    # Auto run history scan
    if not st.session_state['saved_bridges'] and not st.session_state['saved_prizes']:
        with st.spinner("Đang học cầu từ quá khứ..."):
            if "Vị Trí" in method:
                st.session_state['saved_bridges'] = auto_scan_positions(data, mode, allow_rev)[:50]
            if "Cầu Giải" in method:
                st.session_state['saved_prizes'] = auto_scan_prizes(data, mode)
        st.toast("Đã quét xong lịch sử!")

    st.divider()

    # --- BƯỚC 2: DÁN DỮ LIỆU ---
    st.subheader("📝 Dán kết quả vào đây (Minh Ngọc / Đại Phát)")
    
    col_opt, col_area = st.columns([1, 3])
    with col_opt:
        has_gdb = st.checkbox("Đã có GĐB?", value=True, help="Tích nếu trong đoạn văn bản dán vào CÓ chứa giải Đặc Biệt (5 số). Bỏ tích nếu chỉ copy từ Giải 1.")
        if st.button("🧹 Xóa & Dán lại"):
            st.rerun()
            
    with col_area:
        raw_text = st.text_area("Paste (Dán) nội dung vào đây:", height=150, placeholder="Ví dụ:\nGiải nhất 89650\nGiải nhì 21573 12383...")

    # --- BƯỚC 3: XỬ LÝ & ỐP ---
    if raw_text:
        # Sử dụng hàm v2 (xử lý dính chùm) để mạnh hơn
        live_str_107 = parse_pasted_text_v2(raw_text, has_gdb)
        
        # Đếm số ký tự đã có
        filled_len = 107 - live_str_107.count('?')
        
        st.info(f"Đã nhận diện: {filled_len}/107 con số. (Chuỗi: {live_str_107[:20]}...)")
        
        st.write("---")
        st.subheader("⚡ KẾT QUẢ ỐP CẦU")
        
        pos_map = st.session_state['pos_map']
        
        # 1. VỊ TRÍ
        if "Vị Trí" in method:
            bridges = st.session_state['saved_bridges']
            if not bridges: 
                st.warning("Vui lòng reload để quét lại lịch sử.")
            else:
                cols = st.columns(5); count = 0
                for idx, br in enumerate(bridges):
                    i, j = br['i'], br['j']
                    # Check range
                    if i < len(live_str_107) and j < len(live_str_107):
                        vi, vj = live_str_107[i], live_str_107[j]
                        if vi != '?' and vj != '?':
                            pred = vi + vj
                            with cols[count%5]:
                                st.markdown(f"<div class='hot-box'><div class='hot-title'>Cầu #{idx+1} ({br['streak']}n)</div><div style='font-size:11px'>{pos_map[i]} + {pos_map[j]}</div><div class='hot-val'>{pred}</div></div>", unsafe_allow_html=True)
                            count += 1
                if count == 0: st.warning("Chưa có cầu nào khớp (hoặc thiếu số liệu).")

        # 2. GIẢI
        if "Cầu Giải" in method:
            prizes = st.session_state['saved_prizes']
            pmap = get_prize_map_no_gdb()
            found = False
            for p in prizes:
                pname = p['prize']
                s, e = pmap.get(pname)
                if e <= len(live_str_107):
                    val = live_str_107[s:e]
                    if '?' not in val:
                        st.success(f"✅ **{pname}** (Thông {p['streak']}n): {val}")
                        found = True
            if not found: st.warning("Chưa có giải nào khớp.")

if __name__ == "__main__":
    main()
