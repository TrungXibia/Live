import streamlit as st
import requests
import pandas as pd
import json
import re

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH & CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Soi Cầu VIP: API + Paste", page_icon="🎯", layout="wide")

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
    
    /* Phân chia khu vực */
    .section-header {
        background-color: #f0f2f6; padding: 10px; border-radius: 5px; 
        font-weight: bold; margin-top: 20px; margin-bottom: 10px; border-left: 5px solid #ff4b4b;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. LOGIC API & LỊCH SỬ (ĐỂ TÌM CẦU)
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

# --- THUẬT TOÁN TÌM CẦU TỪ LỊCH SỬ ---
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
# 3. LOGIC XỬ LÝ TEXT DÁN VÀO (REAL-TIME)
# -----------------------------------------------------------------------------
def parse_smart_text(text, has_gdb_checkbox):
    text = text.lower()
    buckets = {'db': '', '1': '', '2': '', '3': '', '4': '', '5': '', '6': '', '7': ''}
    current_bucket = None
    lines = text.split('\n')
    for line in lines:
        line_clean = line.strip()
        if not line_clean: continue
        if 'đặc biệt' in line_clean or 'đb' in line_clean or 'db' in line_clean: current_bucket = 'db'
        elif 'nhất' in line_clean or 'g.1' in line_clean or 'g1' in line_clean: current_bucket = '1'
        elif 'nhì' in line_clean or 'g.2' in line_clean or 'g2' in line_clean: current_bucket = '2'
        elif 'ba' in line_clean or 'g.3' in line_clean or 'g3' in line_clean: current_bucket = '3'
        elif 'tư' in line_clean or 'g.4' in line_clean or 'g4' in line_clean: current_bucket = '4'
        elif 'năm' in line_clean or 'g.5' in line_clean or 'g5' in line_clean: current_bucket = '5'
        elif 'sáu' in line_clean or 'g.6' in line_clean or 'g6' in line_clean: current_bucket = '6'
        elif 'bảy' in line_clean or 'g.7' in line_clean or 'g7' in line_clean: current_bucket = '7'
        
        if current_bucket:
            nums = re.findall(r'\d+', line_clean)
            buckets[current_bucket] += "".join(nums)

    RULES = [('db',1,5), ('1',1,5), ('2',2,5), ('3',6,5), ('4',4,4), ('5',6,4), ('6',3,3), ('7',4,2)]
    full_str = ""
    preview_list = []
    for key, count, length in RULES:
        raw_str = buckets[key]
        if key == 'db' and not has_gdb_checkbox:
            full_str += "?" * 5
            preview_list.append(f"GĐB: (Bỏ qua)")
            continue
        current_segment = ""
        display_segment = []
        current_pos = 0
        for i in range(count):
            start = current_pos; end = start + length
            val = "?" * length
            if end <= len(raw_str):
                val = raw_str[start:end]
                current_pos += length
            elif start < len(raw_str):
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
# 4. GIAO DIỆN CHÍNH
# -----------------------------------------------------------------------------
def main():
    st.title("🎯 Soi Cầu VIP: Quy trình chuẩn")

    # Khởi tạo Session
    if 'saved_bridges' not in st.session_state: st.session_state['saved_bridges'] = []
    if 'saved_prizes' not in st.session_state: st.session_state['saved_prizes'] = []
    if 'pos_map' not in st.session_state: st.session_state['pos_map'] = get_pos_map()

    # --- SIDEBAR: CẤU HÌNH ---
    with st.sidebar:
        st.header("⚙️ Cấu Hình")
        method = st.radio("Phương Pháp", ["Cầu Vị Trí (Ghép 2 số)", "Cầu Giải (Nhị Hợp)"])
        mode = "set" if st.checkbox("Soi Bộ Đề", False) else "straight"
        allow_rev = st.checkbox("Đảo AB", True)
        
        st.divider()
        st.info("1. Hệ thống tự quét cầu từ API.\n2. Bạn dán kết quả Live.\n3. Hệ thống tự ốp.")

    # --- PHẦN 1: DỮ LIỆU NỀN (API) ---
    st.markdown("<div class='section-header'>BƯỚC 1: PHÂN TÍCH LỊCH SỬ (Dữ liệu cũ)</div>", unsafe_allow_html=True)
    
    raw = fetch_history()
    data = process_data(raw)
    
    # Tự động quét nếu chưa có dữ liệu trong session
    if data and not st.session_state['saved_bridges'] and not st.session_state['saved_prizes']:
        with st.spinner("Đang tìm kiếm các cầu chạy thông..."):
            if "Vị Trí" in method:
                st.session_state['saved_bridges'] = auto_scan_positions(data, mode, allow_rev)[:50]
            if "Cầu Giải" in method:
                st.session_state['saved_prizes'] = auto_scan_prizes(data, mode)
    
    # Hiển thị trạng thái cầu
    n_bridges = len(st.session_state['saved_bridges'])
    n_prizes = len(st.session_state['saved_prizes'])
    
    c1, c2 = st.columns([3, 1])
    with c1:
        if "Vị Trí" in method:
            st.success(f"✅ Đã tìm thấy {n_bridges} Cầu Vị Trí đang chạy thông (Từ API).")
        else:
            st.success(f"✅ Đã tìm thấy {n_prizes} Giải đang ăn thông (Từ API).")
    with c2:
        if st.button("🔄 Quét lại API"):
            st.session_state['saved_bridges'] = []
            st.session_state['saved_prizes'] = []
            st.rerun()

    # --- PHẦN 2: DÁN KẾT QUẢ LIVE ---
    st.markdown("<div class='section-header'>BƯỚC 2: DÁN KẾT QUẢ LIVE (Minh Ngọc/Đại Phát)</div>", unsafe_allow_html=True)
    
    col_input, col_check = st.columns([2, 1])
    with col_input:
        raw_text = st.text_area("Dán nội dung vào đây:", height=150, placeholder="Giải nhất 89650\nGiải nhì 21573...")
        has_gdb = st.checkbox("Văn bản CÓ chứa Giải Đặc Biệt?", value=True)
    
    # --- PHẦN 3: KẾT QUẢ ỐP ---
    if raw_text:
        st.markdown("<div class='section-header'>BƯỚC 3: KẾT QUẢ ỐP CẦU (REAL-TIME)</div>", unsafe_allow_html=True)
        
        # 1. Phân tích text dán vào
        live_str_107, preview_info = parse_smart_text(raw_text, has_gdb)
        
        # Hiển thị tiến độ nhập liệu
        with col_check:
            filled = 107 - live_str_107.count('?')
            st.progress(filled/107, f"Đã có {filled}/107 số")
            with st.expander("Chi tiết phân tách"):
                for p in preview_info: st.caption(p)

        # 2. Ốp Cầu
        pos_map = st.session_state['pos_map']
        
        if "Vị Trí" in method:
            bridges = st.session_state['saved_bridges']
            if bridges:
                cols = st.columns(5); count = 0
                for idx, br in enumerate(bridges):
                    i, j = br['i'], br['j']
                    # Kiểm tra xem trong chuỗi Live đã có số ở vị trí này chưa
                    if i < len(live_str_107) and j < len(live_str_107):
                        vi, vj = live_str_107[i], live_str_107[j]
                        if vi != '?' and vj != '?':
                            # CẦU ĐÃ NỔ SỐ!
                            pred = vi + vj
                            with cols[count%5]:
                                st.markdown(f"""
                                <div class='hot-box'>
                                    <div class='hot-title'>Top {idx+1} (Thông {br['streak']}n)</div>
                                    <div style='font-size:10px; color:gray'>{pos_map[i]} + {pos_map[j]}</div>
                                    <div class='hot-val'>{pred}</div>
                                </div>
                                """, unsafe_allow_html=True)
                            count += 1
                if count == 0:
                    st.info("⏳ Các cầu đẹp chưa quay đến số tương ứng. Hãy dán tiếp khi có giải mới...")
            else:
                st.warning("Chưa có dữ liệu cầu từ Bước 1.")

        elif "Cầu Giải" in method:
            prizes = st.session_state['saved_prizes']
            pmap = get_prize_map_no_gdb()
            if prizes:
                found = False
                for p in prizes:
                    pname = p['prize']
                    s, e = pmap.get(pname)
                    if e <= len(live_str_107):
                        val = live_str_107[s:e]
                        if '?' not in val:
                            st.success(f"✅ Giải **{pname}** (Thông {p['streak']}n) về: **{val}**")
                            found = True
                if not found: st.info("⏳ Các giải trong cầu chưa quay xong...")

if __name__ == "__main__":
    main()
