import streamlit as st
import requests
import pandas as pd
import json
import re

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH & CSS (FIX LỖI LOÁ MÀU)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Soi Cầu VIP: Giao Diện Mới", page_icon="🎯", layout="wide")

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div.stButton > button {width: 100%; height: 3em; font-weight: bold;}
    thead tr th:first-child {display:none}
    tbody th {display:none}
    
    /* Header từng bước - Màu chữ Đen đậm trên nền Xám xanh */
    .step-header {
        background-color: #e3f2fd; 
        padding: 15px; 
        border-radius: 8px; 
        font-weight: bold; 
        color: #0d47a1 !important; /* Chữ xanh đậm */
        margin-bottom: 15px; 
        border-left: 5px solid #1565c0;
        font-size: 18px;
    }
    
    /* Box kết quả ốp */
    .hot-box {
        background-color: #fff3e0; 
        border: 2px solid #ff9800; 
        border-radius: 8px; 
        padding: 10px; 
        text-align: center; 
        margin-bottom: 10px;
    }
    .hot-title {font-size: 12px; color: #e65100; font-weight: bold;}
    .hot-val {font-size: 28px; color: #d32f2f; font-weight: 900;}
    
    /* Input area to rõ */
    .stTextArea textarea {font-size: 16px; font-family: monospace; color: #000000;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DỮ LIỆU & API
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
        p.append({"issue": r.get('turnNum'), "de": de, "de_rev": de[::-1], "de_set": get_set(de), "body": f})
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
# 3. THUẬT TOÁN TÌM CẦU (CÓ THAM SỐ MIN STREAK)
# -----------------------------------------------------------------------------
def scan_positions_logic(data, mode, allow_rev, min_s):
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
        if strk >= min_s: res.append({"i": i, "j": j, "streak": strk})
    res.sort(key=lambda x: x['streak'], reverse=True)
    return res

def scan_prizes_logic(data, mode, min_s):
    pmap = get_prize_map_no_gdb(); res = []
    for p, (s, e) in pmap.items():
        strk = 0
        for d in data:
            digits = set(d['body'][s:e])
            match = False
            if mode == "straight": match = (d['de'][0] in digits and d['de'][1] in digits)
            else:
                for n in BO_DE_DICT.get(get_set(d['de']), []):
                    if n[0] in digits and n[1] in digits: match = True; break
            if match: strk += 1
            else: break
        if strk >= min_s: res.append({"prize": p, "streak": strk, "val": data[0]['body'][s:e]})
    res.sort(key=lambda x: x['streak'], reverse=True)
    return res

# -----------------------------------------------------------------------------
# 4. XỬ LÝ TEXT
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
                val = raw_str[start:end]; current_pos += length
            elif start < len(raw_str):
                partial = raw_str[start:]; val = partial.ljust(length, '?'); current_pos += len(partial)
            current_segment += val
            display_segment.append(val)
        full_str += current_segment
        status = "✅" if '?' not in current_segment else "⏳"
        label = "ĐB" if key == 'db' else key
        preview_list.append(f"G{label} ({status}): {', '.join(display_segment)}")
    return full_str, preview_list

# -----------------------------------------------------------------------------
# 5. GIAO DIỆN CHÍNH
# -----------------------------------------------------------------------------
def main():
    st.title("🎯 Soi Cầu VIP: Quy trình chuẩn")

    # --- MENU TRÊN CÙNG (DASHBOARD) ---
    with st.container():
        c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 1.5])
        with c1:
            method = st.selectbox("💎 PHƯƠNG PHÁP", ["Cầu Vị Trí (Ghép 2 số)", "Cầu Giải (Nhị Hợp)"])
        with c2:
            # User chọn min streak mong muốn
            pref_streak = st.number_input("Ngày thông (Min)", 2, 10, 3)
        with c3:
            is_set = st.checkbox("Soi Bộ Đề", False)
            mode = "set" if is_set else "straight"
        with c4:
            allow_rev = True
            if not is_set and "Vị Trí" in method:
                allow_rev = st.checkbox("Đảo AB", True)
            else: st.write("")

    # --- LOAD DATA ---
    raw = fetch_history()
    data = process_data(raw)
    if not data: st.error("Lỗi API"); return
    
    # --- AUTO RUN & FALLBACK LOGIC ---
    # Logic: Quét theo pref_streak. Nếu không có -> hạ xuống 2 -> hạ xuống 1.
    
    final_bridges = []
    final_prizes = []
    actual_min_streak = pref_streak

    if "Vị Trí" in method:
        res = scan_positions_logic(data, mode, allow_rev, pref_streak)
        if not res and pref_streak > 1:
            res = scan_positions_logic(data, mode, allow_rev, 1) # Fallback về 1
            actual_min_streak = 1
        final_bridges = res[:100]
    
    elif "Cầu Giải" in method:
        res = scan_prizes_logic(data, mode, pref_streak)
        if not res and pref_streak > 1:
            res = scan_prizes_logic(data, mode, 1)
            actual_min_streak = 1
        final_prizes = res

    # --- BƯỚC 1: HIỂN THỊ KẾT QUẢ QUÉT ---
    st.markdown("<div class='step-header'>BƯỚC 1: PHÂN TÍCH LỊCH SỬ (API)</div>", unsafe_allow_html=True)
    
    # Thông báo Fallback nếu có
    if actual_min_streak < pref_streak:
        st.warning(f"⚠️ Không tìm thấy cầu thông {pref_streak} ngày. Hệ thống tự động hiển thị cầu thông {actual_min_streak} ngày.")
    
    if final_bridges:
        st.success(f"✅ Đã tìm thấy {len(final_bridges)} Cầu Vị Trí đang chạy.")
    elif final_prizes:
        st.success(f"✅ Đã tìm thấy {len(final_prizes)} Giải đang ăn thông.")
    else:
        st.error("Không tìm thấy cầu nào (Kể cả 1 ngày).")

    # --- BƯỚC 2: DÁN DỮ LIỆU LIVE ---
    st.markdown("<div class='step-header'>BƯỚC 2: DÁN KẾT QUẢ LIVE (Minh Ngọc/Đại Phát)</div>", unsafe_allow_html=True)
    
    col_input, col_check = st.columns([2, 1])
    with col_input:
        raw_text = st.text_area("Dán nội dung vào đây:", height=150, placeholder="Giải nhất 89650...")
        has_gdb = st.checkbox("Văn bản CÓ chứa Giải Đặc Biệt?", value=True)
        
    # --- BƯỚC 3: KẾT QUẢ ỐP ---
    if raw_text:
        st.markdown("<div class='step-header'>BƯỚC 3: KẾT QUẢ ỐP CẦU (REAL-TIME)</div>", unsafe_allow_html=True)
        
        live_str_107, preview_info = parse_smart_text(raw_text, has_gdb)
        pos_map = get_pos_map()
        
        # Hiển thị tiến độ
        filled = 107 - live_str_107.count('?')
        st.progress(filled/107, f"Tiến độ quay: {filled}/107 số")

        # 1. VỊ TRÍ
        if "Vị Trí" in method and final_bridges:
            cols = st.columns(5); count = 0
            for idx, br in enumerate(final_bridges):
                i, j = br['i'], br['j']
                if i < len(live_str_107) and j < len(live_str_107):
                    vi, vj = live_str_107[i], live_str_107[j]
                    if vi != '?' and vj != '?':
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
            if count == 0: st.info("⏳ Các cầu đẹp chưa quay đến số tương ứng...")

        # 2. GIẢI
        elif "Cầu Giải" in method and final_prizes:
            pmap = get_prize_map_no_gdb()
            found = False
            for p in final_prizes:
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
