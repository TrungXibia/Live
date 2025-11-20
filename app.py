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
        de = f[2:5][1:] # Lấy 2 số cuối GĐB
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
# 4. HÀM PHÂN TÍCH VĂN BẢN THÔNG MINH (SMART PARSER)
# -----------------------------------------------------------------------------
def parse_smart_text(text, has_gdb_checkbox):
    """
    Phân tích text dán vào dựa trên tên giải.
    Tự động tách chuỗi dính liền (VD: 2157312383 -> 21573, 12383)
    """
    text = text.lower() # Chuẩn hóa về chữ thường
    
    # 1. Tạo các thùng chứa (Buckets) cho từng giải
    buckets = {
        'db': '', '1': '', '2': '', '3': '', '4': '', '5': '', '6': '', '7': ''
    }
    
    current_bucket = None
    
    lines = text.split('\n')
    for line in lines:
        line_clean = line.strip()
        
        # --- NHẬN DIỆN TÊN GIẢI ---
        if 'đặc biệt' in line_clean or 'đb' in line_clean or 'db' in line_clean:
            current_bucket = 'db'
        elif 'nhất' in line_clean or 'g.1' in line_clean or 'g1' in line_clean:
            current_bucket = '1'
        elif 'nhì' in line_clean or 'g.2' in line_clean or 'g2' in line_clean:
            current_bucket = '2'
        elif 'ba' in line_clean or 'g.3' in line_clean or 'g3' in line_clean:
            current_bucket = '3'
        elif 'tư' in line_clean or 'g.4' in line_clean or 'g4' in line_clean:
            current_bucket = '4'
        elif 'năm' in line_clean or 'g.5' in line_clean or 'g5' in line_clean:
            current_bucket = '5'
        elif 'sáu' in line_clean or 'g.6' in line_clean or 'g6' in line_clean:
            current_bucket = '6'
        elif 'bảy' in line_clean or 'g.7' in line_clean or 'g7' in line_clean:
            current_bucket = '7'
            
        # --- LẤY SỐ VÀO THÙNG ---
        if current_bucket:
            # Tìm tất cả các con số trong dòng này
            nums = re.findall(r'\d+', line_clean)
            # Nối vào thùng hiện tại
            buckets[current_bucket] += "".join(nums)

    # 2. Xử lý và ghép chuỗi 107 ký tự
    # Cấu trúc: (Key_Bucket, Số lượng giải, Độ dài 1 giải)
    RULES = [
        ('db', 1, 5),
        ('1', 1, 5),
        ('2', 2, 5),
        ('3', 6, 5),
        ('4', 4, 4),
        ('5', 6, 4),
        ('6', 3, 3),
        ('7', 4, 2)
    ]
    
    full_str = ""
    preview_list = [] # Để hiển thị cho user xem
    
    for key, count, length in RULES:
        raw_str = buckets[key]
        
        # Nếu người dùng bỏ tích "Đã có GĐB" và key là db -> Bỏ qua (điền ?)
        if key == 'db' and not has_gdb_checkbox:
            full_str += "?" * 5
            preview_list.append(f"GĐB: (Bỏ qua)")
            continue
            
        # Lấy đoạn chuỗi tương ứng
        current_segment = ""
        display_segment = []
        current_pos = 0
        
        for i in range(count):
            # Cắt chuỗi dính liền
            start = current_pos
            end = start + length
            
            val = "?" * length
            
            if end <= len(raw_str):
                val = raw_str[start:end]
                current_pos += length
            elif start < len(raw_str):
                # Có số nhưng thiếu
                partial = raw_str[start:]
                val = partial.ljust(length, '?')
                current_pos += len(partial)
            
            current_segment += val
            display_segment.append(val)
            
        full_str += current_segment
        
        status = "✅" if '?' not in current_segment else "⏳"
        preview_list.append(f"G{key if key != 'db' else 'ĐB'} ({status}): {', '.join(display_segment)}")
        
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
    st.title("📋 Soi Cầu: Copy & Paste (Th
