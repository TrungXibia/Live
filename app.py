import streamlit as st
import requests
import pandas as pd
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH & CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Chiến Trường XSMB: Live Minh Ngọc", page_icon="⚔️", layout="wide")

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div.stButton > button {width: 100%; height: 3em; font-weight: bold;}
    thead tr th:first-child {display:none}
    tbody th {display:none}
    
    .hot-box {
        background-color: #ffebee; border: 2px solid #ef5350; 
        border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 10px;
    }
    .hot-val {font-size: 24px; color: #d32f2f; font-weight: 900;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. CONSTANTS
# -----------------------------------------------------------------------------
# API Lịch sử (Chỉ dùng để tìm cầu từ quá khứ)
HISTORY_API_URL = "https://www.kqxs88.live/api/front/open/lottery/history/list/game?limitNum=50&gameCode=miba"

# Link Live chuẩn Minh Ngọc
LIVE_URL = "https://www.minhngoc.net.vn/xo-so-truc-tiep/mien-bac.html"

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
# 3. HÀM LẤY DỮ LIỆU LỊCH SỬ (API)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_history_data():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(HISTORY_API_URL, headers=headers, timeout=10).json()
        return res.get('t', {}).get('issueList', [])
    except: return []

def parse_detail(d_str):
    try:
        return "".join([g.replace(",", "").strip() for g in json.loads(d_str)])
    except: return ""

def process_history(raw):
    processed = []
    for rec in raw:
        full = parse_detail(rec.get('detail', ''))
        if len(full) != 107: continue
        de = full[2:5][1:]
        processed.append({
            "de": de, "de_rev": de[::-1], "de_set": NUMBER_TO_SET_MAP.get(de, "?"),
            "body": full
        })
    return processed

def get_pos_map():
    m = []
    for p, c, l in XSMB_STRUCTURE:
        for i in range(1, c+1):
            for j in range(1, l+1): m.append(f"{p}.{i}.{j}")
    return m

# -----------------------------------------------------------------------------
# 4. HÀM CÀO LIVE MINH NGỌC (ĐÃ KIỂM TRA HTML CHUẨN)
# -----------------------------------------------------------------------------
def fetch_live_minhngoc():
    """
    Cào trang trực tiếp Minh Ngọc, đảm bảo đúng class name hiện tại.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        # Thêm random time để tránh cache trình duyệt
        resp = requests.get(f"{LIVE_URL}?t={int(time.time())}", headers=headers, timeout=5)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Lấy bảng kết quả mới nhất
        # Minh Ngọc thường dùng class="content" hoặc "box_kqxs"
        # Cách chắc ăn nhất là tìm bảng có class "bkqt" nằm trong div "box_kqxs"
        box = soup.find('div', class_='box_kqxs')
        if not box: return None, "Không tìm thấy box kết quả"
        
        # --- KIỂM TRA NGÀY ---
        # Minh Ngọc hiện ngày ở 1 div class="ngay" hoặc tiêu đề
        # Ta sẽ thử lấy, nếu không khớp ngày hôm nay -> Cảnh báo
        # (Logic này tùy chọn, vì đôi khi server giờ lệch, nhưng tốt nhất nên có warning)
        
        # --- BÓC TÁCH DỮ LIỆU ---
        prizes_data = {}
        
        # Class name chuẩn của Minh Ngọc (Case Sensitive)
        # GĐB là 'giaiDb' (chữ D viết hoa, b viết thường)
        # Các giải khác: giai1, giai2...
        mapping_class = {
            "GĐB": "giaiDb",
            "G1": "giai1", "G2": "giai2", "G3": "giai3",
            "G4": "giai4", "G5": "giai5", "G6": "giai6", "G7": "giai7"
        }
        
        for my_name, mn_class in mapping_class.items():
            cell = box.find('td', class_=mn_class)
            nums = []
            if cell:
                # Trường hợp 1: Số nằm trong thẻ div (thường là giải có nhiều số: G3, G4...)
                divs = cell.find_all('div')
                if divs:
                    nums = [d.text.strip() for d in divs]
                else:
                    # Trường hợp 2: Số nằm trực tiếp trong td (thường là GĐB, G1)
                    txt = cell.text.strip()
                    if txt: nums = [txt]
            
            # Lọc bỏ ký tự rác nếu có (đôi khi có ký tự xuống dòng)
            clean_nums = [n for n in nums if n.isdigit()]
            prizes_data[my_name] = clean_nums

        # --- GHÉP CHUỖI 107 KÝ TỰ ---
        full_str = ""
        # Thứ tự XSMB_STRUCTURE: GĐB -> G1 -> ... -> G7
        # Nhưng Minh Ngọc GĐB lại quay CUỐI CÙNG. 
        # -> Kệ thứ tự quay, ta cứ ghép đúng vị trí. Cái nào chưa quay điền '?'
        
        for p_name, count, length in XSMB_STRUCTURE:
            current_nums = prizes_data.get(p_name, [])
            
            for i in range(count):
                if i < len(current_nums):
                    val = current_nums[i]
                    # Nếu độ dài chưa đủ (đang quay dở số đó), điền ?
                    if len(val) == length:
                        full_str += val
                    else:
                        full_str += val.ljust(length, '?')
                else:
                    # Chưa quay đến giải này
                    full_str += "?" * length
        
        filled = 107 - full_str.count('?')
        return full_str, filled

    except Exception as e:
        return None, str(e)

# -----------------------------------------------------------------------------
# 5. TÌM CẦU TỪ LỊCH SỬ (BẮT ĐẦU TỪ INDEX 5)
# -----------------------------------------------------------------------------
def find_best_bridges(history, limit=50):
    if not history: return []
    day0 = history[0]
    body = day0['body']
    # Bắt đầu từ 5 để bỏ GĐB
    start_idx = 5 
    candidates = []
    
    for i in range(start_idx, len(body)):
        for j in range(start_idx, len(body)):
            if i == j: continue
            val = body[i] + body[j]
            # Chấp nhận mọi loại cầu (Thẳng, Đảo, Bộ) để bắt dính
            match = False
            if val == day0['de'] or val == day0['de_rev'] or NUMBER_TO_SET_MAP.get(val) == day0['de_set']:
                match = True
            if match: candidates.append((i, j))
            
    results = []
    for (i, j) in candidates:
        streak = 0
        for day in history:
            val = day['body'][i] + day['body'][j]
            match = False
            if val == day['de'] or val == day['de_rev'] or NUMBER_TO_SET_MAP.get(val) == day['de_set']:
                streak += 1
            else: break
        
        if streak >= 3:
            results.append({"i": i, "j": j, "streak": streak})
            
    results.sort(key=lambda x: x['streak'], reverse=True)
    return results[:limit]

# -----------------------------------------------------------------------------
# 6. GIAO DIỆN
# -----------------------------------------------------------------------------
def main():
    st.title("⚔️ Chiến Trường XSMB: LIVE MINH NGỌC")
    
    if 'bridges' not in st.session_state: st.session_state['bridges'] = []
    if 'pos_map' not in st.session_state: st.session_state['pos_map'] = get_pos_map()

    # --- BƯỚC 1: QUÉT LỊCH SỬ ---
    with st.expander("⚙️ BƯỚC 1: CHUẨN BỊ (Quét từ API Lịch sử)", expanded=not bool(st.session_state['bridges'])):
        if st.button("🔍 QUÉT CẦU NGAY"):
            with st.spinner("Đang tải..."):
                hist = process_history(fetch_history_data())
                if hist:
                    # Bỏ ngày đầu tiên nếu nó trùng với ngày hiện tại (tránh lấy cầu của chính hôm nay để soi hôm nay)
                    # Tuy nhiên để đơn giản, ta cứ lấy data mới nhất đã hoàn thành.
                    bridges = find_best_bridges(hist, limit=100)
                    st.session_state['bridges'] = bridges
                    st.success(f"Đã tìm được {len(bridges)} cầu ngon (G1-G7)!")
                else: st.error("API Lịch sử lỗi.")

    st.divider()

    # --- BƯỚC 2: LIVE ---
    st.header("🔴 LIVE MONITOR (18:15 - 18:30)")
    
    c1, c2 = st.columns([1, 3])
    with c1:
        refresh = st.button("🔄 F5 CẬP NHẬT", type="primary")
    
    # Cào Minh Ngọc
    live_str, filled_len = fetch_live_minhngoc()
    
    with c2:
        if live_str:
            pct = int((filled_len/107)*100)
            st.progress(pct, f"Tiến độ quay: {filled_len}/107 ({pct}%)")
            
            # Show bảng số thô để user kiểm tra
            with st.expander("Xem dữ liệu thô (Minh Ngọc)"):
                st.text(live_str)
                st.caption("Dữ liệu được map vào chuỗi 107 ký tự. '?' là chưa quay.")
        else:
            st.error(f"Lỗi cào Minh Ngọc: {filled_len}")
            return

    # --- BƯỚC 3: ỐP CẦU ---
    st.subheader("⚡ CẦU ĐANG NỔ (Real-time)")
    
    if not st.session_state['bridges']:
        st.warning("Vui lòng làm Bước 1 trước.")
    else:
        pos_map = st.session_state['pos_map']
        bridges = st.session_state['bridges']
        
        cols = st.columns(5)
        count = 0
        
        for idx, br in enumerate(bridges):
            i, j = br['i'], br['j']
            # Kiểm tra xem vị trí i, j trong live_str đã có số chưa
            val_i = live_str[i]
            val_j = live_str[j]
            
            if val_i != '?' and val_j != '?':
                # CẦU ĐÃ NỔ
                pred = val_i + val_j
                with cols[count % 5]:
                    st.markdown(f"""
                    <div class="hot-box">
                        <div style="font-size:10px; color:gray">Cầu #{idx+1} (Thông {br['streak']}n)</div>
                        <div style="font-size:11px; font-weight:bold">{pos_map[i]} + {pos_map[j]}</div>
                        <div class="hot-val">{pred}</div>
                    </div>
                    """, unsafe_allow_html=True)
                count += 1
        
        if count == 0:
            st.info("⏳ Các vị trí cầu chưa quay đến. Vui lòng chờ...")

if __name__ == "__main__":
    main()
