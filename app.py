import streamlit as st
import requests
import pandas as pd
import json
import re

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH & CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Soi Cầu: Copy Paste Pro", page_icon="📋", layout="wide")

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div.stButton > button {width: 100%; height: 3em; font-weight: bold;}
    thead tr th:first-child {display:none}
    tbody th {display:none}
    
    .hot-box {
        background-color: #e3f2fd; border: 2px solid #1565c0; 
        border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 10px;
    }
    .hot-title {font-size: 11px; color: #0d47a1; font-weight: bold;}
    .hot-val {font-size: 26px; color: #d32f2f; font-weight: 900;}
    
    /* Input area font */
    .stTextArea textarea {font-size: 16px; font-family: monospace;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. CẤU TRÚC DỮ LIỆU
# -----------------------------------------------------------------------------
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
        de = f[2:5][1:]
        p.append({"issue": r.get('turnNum'), "de": de, "de_rev": de[::-1], "de_set": get_set(de), "tam_cang": f[2], "body": f})
    return p

def get_pos_map():
    m = []
    for p, c, l in XSMB_STRUCTURE:
        for i in range(1, c+1):
            for j in range(1, l+1): m.append(f"{p}.{i}.{j}")
    return m

def get_prize_map_no_gdb():
    m = {}; curr = 0
    for p, c, l in XSMB_STRUCTURE:
        for i in range(1, c+1):
            s, e = curr, curr + l
            if p != "GĐB": m[f"{p}" if c==1 else f"{p}.{i}"] = (s, e)
            curr += l
    return m

# -----------------------------------------------------------------------------
# 4. HÀM PHÂN TÍCH THÔNG MINH (SMART PARSER)
# -----------------------------------------------------------------------------
def parse_smart_text(text, has_gdb_checkbox):
    """
    Phân tích text copy từ Minh Ngọc/Đại Phát.
    Tự động nhận diện tên giải và gom số.
    """
    text = text.lower()
    
    # Thùng chứa số liệu từng giải
    buckets = {'db': '', '1': '', '2': '', '3': '', '4': '', '5': '', '6': '', '7': ''}
    current_bucket = None
    
    # Tách dòng để xử lý
    lines = text.split('\n')
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean: continue
        
        # Nhận diện tiêu đề giải
        # Ưu tiên từ khóa dài trước
        if 'đặc biệt' in line_clean or 'đb' in line_clean or 'db' in line_clean: current_bucket = 'db'
        elif 'nhất' in line_clean or 'g.1' in line_clean or 'g1' in line_clean: current_bucket = '1'
        elif 'nhì' in line_clean or 'g.2' in line_clean or 'g2' in line_clean: current_bucket = '2'
        elif 'ba' in line_clean or 'g.3' in line_clean or 'g3' in line_clean: current_bucket = '3'
        elif 'tư' in line_clean or 'g.4' in line_clean or 'g4' in line_clean: current_bucket = '4'
        elif 'năm' in line_clean or 'g.5' in line_clean or 'g5' in line_clean: current_bucket = '5'
        elif 'sáu' in line_clean or 'g.6' in line_clean or 'g6' in line_clean: current_bucket = '6'
        elif 'bảy' in line_clean or 'g.7' in line_clean or 'g7' in line_clean: current_bucket = '7'
        
        # Lấy số trong dòng này (bất kể có tên giải hay không)
        if current_bucket:
            nums = re.findall(r'\d+', line_clean)
            buckets[current_bucket] += "".join(nums)

    # Ghép thành chuỗi 107 ký tự
    RULES = [
        ('db', 1, 5), ('1', 1, 5), ('2', 2, 5), ('3', 6, 5),
        ('4', 4, 4), ('5', 6, 4), ('6', 3, 3), ('7', 4, 2)
    ]
    
    full_str = ""
    preview_list = []
    
    for key, count, length in RULES:
        raw_str = buckets[key]
        
        # Nếu người dùng bảo KHÔNG có GĐB thì điền ? vào GĐB
        if key == 'db' and not has_gdb_checkbox:
            full_str += "?" * 5
            preview_list.append(f"GĐB: (Bỏ qua)")
            continue
            
        # Tự động cắt chuỗi dính liền
        current_segment = ""
        display_segment = []
        current_pos = 0
        
        for i in range(count):
            start = current_pos
            end = start + length
            
            val = "?" * length
            
            if end <= len(raw_str):
                val = raw_str[start:end]
                current_pos += length
            elif start < len(raw_str):
                # Có số nhưng thiếu (đang quay)
                partial = raw_str[start:]
                val = partial.ljust(length, '?')
                current_pos += len(partial)
            
            current_segment += val
            display_segment.append(val)
            
        full_str += current_segment
        status = "✅" if '?' not in current_segment else "⏳"
        label = "ĐB" if key == 'db' else key
        preview_list.append(f"G{label} ({status}): {', '.join(display_segment)}")
        
    return full_str, preview_list

# -----------------------------------------------------------------------------
# 5. THUẬT TOÁN SOI CẦU
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
            d_set = set(d['body'][s:e])
            match = False
            if mode == "straight": match = (d['de'][0] in d_set and d['de'][1] in d_set)
            else:
                for n in BO_DE_DICT.get(get_set(d['de']), []):
                    if n[0] in d_set and n[1] in d_set: match = True; break
            if match: strk += 1
            else: break
        if strk >= 2: res.append({"prize": p, "streak": strk, "val": data[0]['body'][s:e]})
    res.sort(key=lambda x: x['streak'], reverse=True)
    return res

# -----------------------------------------------------------------------------
# 6. GIAO DIỆN CHÍNH
# -----------------------------------------------------------------------------
def main():
    st.title("📋 Soi Cầu: Copy & Paste (Smart)")
    
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
    
    if not st.session_state['saved_bridges'] and not st.session_state['saved_prizes']:
        with st.spinner("Đang học cầu từ quá khứ..."):
            if "Vị Trí" in method: st.session_state['saved_bridges'] = auto_scan_positions(data, mode, allow_rev)[:50]
            if "Cầu Giải" in method: st.session_state['saved_prizes'] = auto_scan_prizes(data, mode)
        st.toast("Đã quét xong lịch sử!")

    st.divider()

    # --- BƯỚC 2: DÁN DỮ LIỆU ---
    st.subheader("📝 Dán kết quả (Minh Ngọc / Đại Phát)")
    
    col_opt, col_area = st.columns([1, 3])
    with col_opt:
        has_gdb = st.checkbox("Văn bản CÓ chứa GĐB?", value=True, help="Bỏ tích nếu bạn chỉ copy từ Giải Nhất")
        if st.button("🧹 Xóa & Dán lại"): st.rerun()
            
    with col_area:
        # SỬA LỖI CÚ PHÁP TẠI ĐÂY: ĐƯA VỀ 1 DÒNG
        raw_text = st.text_area("Dán nội dung vào đây:", height=200, placeholder="Giải nhất 89650\nGiải nhì 2157312383...")

    # --- BƯỚC 3: XỬ LÝ & ỐP ---
    if raw_text:
        # GỌI HÀM PHÂN TÍCH THÔNG MINH
        live_str_107, preview_info = parse_smart_text(raw_text, has_gdb)
        
        # Hiển thị bảng phân tách để user kiểm tra
        st.info("🔍 Kết quả phân tách dữ liệu:")
        
        # Chia cột hiển thị preview cho gọn
        p_col1, p_col2 = st.columns(2)
        half = len(preview_info) // 2
        with p_col1:
            for line in preview_info[:half]: st.text(line)
        with p_col2:
            for line in preview_info[half:]: st.text(line)
            
        # Đếm tiến độ
        filled_len = 107 - live_str_107.count('?')
        st.progress(filled_len/107, f"Đã nhận diện: {filled_len}/107 vị trí")
        
        st.write("---")
        st.subheader("⚡ KẾT QUẢ ỐP CẦU")
        
        pos_map = st.session_state['pos_map']
        
        # 1. VỊ TRÍ
        if "Vị Trí" in method:
            bridges = st.session_state['saved_bridges']
            cols = st.columns(5); count = 0
            for idx, br in enumerate(bridges):
                i, j = br['i'], br['j']
                if i < len(live_str_107) and j < len(live_str_107):
                    vi, vj = live_str_107[i], live_str_107[j]
                    if vi != '?' and vj != '?':
                        pred = vi + vj
                        with cols[count%5]:
                            st.markdown(f"<div class='hot-box'><div class='hot-title'>Cầu #{idx+1} ({br['streak']}n)</div><div style='font-size:11px'>{pos_map[i]}+{pos_map[j]}</div><div class='hot-val'>{pred}</div></div>", unsafe_allow_html=True)
                        count += 1
            if count == 0: st.warning("Chưa có cầu nào nổ số.")

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
