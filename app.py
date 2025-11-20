import streamlit as st
import requests
import pandas as pd
import json
import time
from bs4 import BeautifulSoup

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH & CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Chiến Trường XSMB: Auto & Live", page_icon="⚔️", layout="wide")

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div.stButton > button {width: 100%; height: 3em; font-weight: bold;}
    thead tr th:first-child {display:none}
    tbody th {display:none}
    
    /* Style cho Live Box */
    .hot-box {
        background-color: #ffebee; border: 2px solid #ef5350; 
        border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 10px;
    }
    .hot-title {font-size: 11px; color: #c62828; font-weight: bold;}
    .hot-val {font-size: 26px; color: #d32f2f; font-weight: 900;}
    .live-progress {font-weight: bold; color: #2e7d32;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DATA & CONSTANTS
# -----------------------------------------------------------------------------
# API Lịch sử (Quét cầu)
API_URL = "https://www.kqxs88.live/api/front/open/lottery/history/list/game?limitNum=50&gameCode=miba"
# Link Live (Ốp cầu)
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
# 3. HÀM XỬ LÝ DỮ LIỆU LỊCH SỬ
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
# 4. THUẬT TOÁN TỰ ĐỘNG (AUTO SCAN)
# -----------------------------------------------------------------------------

# --- A. SOI VỊ TRÍ ---
def auto_scan_positions(data, mode, allow_rev):
    if not data: return []
    day0 = data[0]
    body = day0['body']
    
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
        
        if streak >= 2: # Min streak 2
            results.append({"i": i, "j": j, "streak": streak})
            
    results.sort(key=lambda x: x['streak'], reverse=True)
    return results

# --- B. SOI GIẢI ---
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
            results.append({"prize": p_name, "streak": streak, "val": data[0]['body'][s:e]})
            
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
# 5. MODULE LIVE MINH NGỌC (REAL-TIME)
# -----------------------------------------------------------------------------
def fetch_live_minhngoc():
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        resp = requests.get(f"{LIVE_URL}?t={int(time.time())}", headers=headers, timeout=5)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        box = soup.find('div', class_='box_kqxs')
        if not box: return None, 0

        prizes_data = {}
        mapping_class = {
            "GĐB": "giaiDb", "G1": "giai1", "G2": "giai2", "G3": "giai3",
            "G4": "giai4", "G5": "giai5", "G6": "giai6", "G7": "giai7"
        }
        
        for my_name, mn_class in mapping_class.items():
            cell = box.find('td', class_=mn_class)
            nums = []
            if cell:
                divs = cell.find_all('div')
                if divs: nums = [d.text.strip() for d in divs]
                else: nums = [cell.text.strip()]
            
            clean_nums = [n for n in nums if n.isdigit()]
            prizes_data[my_name] = clean_nums

        full_str = ""
        for p_name, count, length in XSMB_STRUCTURE:
            current_nums = prizes_data.get(p_name, [])
            for i in range(count):
                if i < len(current_nums):
                    val = current_nums[i]
                    if len(val) == length: full_str += val
                    else: full_str += val.ljust(length, '?')
                else:
                    full_str += "?" * length
        
        filled = 107 - full_str.count('?')
        return full_str, filled
    except: return None, 0

# -----------------------------------------------------------------------------
# 6. GIAO DIỆN CHÍNH
# -----------------------------------------------------------------------------
def main():
    st.title("🔥 Chiến Trường XSMB: Auto Scan + Live Ốp Cầu")
    
    # Session để lưu cầu tìm được
    if 'saved_bridges' not in st.session_state: st.session_state['saved_bridges'] = []
    if 'saved_prizes' not in st.session_state: st.session_state['saved_prizes'] = []
    if 'saved_cang' not in st.session_state: st.session_state['saved_cang'] = []
    if 'pos_map' not in st.session_state: st.session_state['pos_map'] = get_pos_map()

    # --- PHẦN 1: MENU ---
    c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 1.5])
    with c1:
        method = st.selectbox("🎯 Phương Pháp", ["1. Cầu Vị Trí (Cặp Số)", "2. Cầu Giải (Nhị Hợp)", "3. Cầu 3 Càng"])
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
    
    raw = fetch_history_data()
    if not raw: st.error("Lỗi API Lịch sử."); return
    data = process_data(raw)
    pos_map = get_pos_map()
    
    st.subheader("📅 Lịch sử 5 ngày gần nhất")
    if len(data) >= 5:
        h = [{"Ngày": d['issue'], "Đề": d['de'], "Bộ": d['de_set']} for d in data[:5]]
        st.dataframe(pd.DataFrame(h).T, use_container_width=True)

    # --- PHẦN 2: KẾT QUẢ QUÉT (AUTO SCAN) ---
    if btn:
        # Reset saved
        st.session_state['saved_bridges'] = []
        st.session_state['saved_prizes'] = []
        st.session_state['saved_cang'] = []

        st.write("---")
        st.markdown("### 🏆 BẢNG XẾP HẠNG CẦU (Dữ liệu Lịch sử)")
        
        # 1. VỊ TRÍ
        if "Vị Trí" in method:
            with st.spinner("Đang quét vị trí..."):
                res = auto_scan_positions(data, mode, allow_rev)
            
            if res:
                # Lưu Top 30 cầu vào Session để dùng cho Live
                st.session_state['saved_bridges'] = res[:30]
                
                rows = []
                for r in res[:50]:
                    val = data[0]['body'][r['i']] + data[0]['body'][r['j']]
                    rows.append({
                        "Hạng": f"#{len(rows)+1}",
                        "Vị trí 1": pos_map[r['i']],
                        "Vị trí 2": pos_map[r['j']],
                        "Thông": f"{r['streak']} ngày 🔥",
                        "Báo số": val
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
                st.success(f"Đã lưu Top 30 cầu vị trí. Kéo xuống dưới để xem Live!")
            else:
                st.warning("Không tìm thấy cầu vị trí nào.")

        # 2. NHỊ HỢP
        elif "Cầu Giải" in method:
            res = auto_scan_prizes(data, mode)
            st.session_state['saved_prizes'] = res # Lưu hết
            if res:
                rows = [{"Hạng": f"#{i+1}", "Giải": r['prize'], "Thông": f"{r['streak']} ngày 🔥", "Dữ liệu": r['val']} for i, r in enumerate(res)]
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
                st.success("Đã lưu danh sách cầu giải.")

        # 3. 3 CÀNG
        elif "3 Càng" in method:
            c_col, d_col = st.columns(2)
            tc = auto_scan_tam_cang(data)
            de = auto_scan_positions(data, mode, allow_rev)
            
            st.session_state['saved_cang'] = tc[:10]
            st.session_state['saved_bridges'] = de[:20] # Lưu đề để ghép

            with c_col:
                st.info(f"Tâm Càng")
                if tc: st.dataframe(pd.DataFrame([{"Vị trí": pos_map[r['idx']], "Thông": f"{r['streak']} ngày"} for r in tc]), use_container_width=True)
            with d_col:
                st.success(f"Cầu Đề")
                if de:
                    rows = [{"V1": pos_map[r['i']], "V2": pos_map[r['j']], "Thông": f"{r['streak']} ngày"} for r in de[:20]]
                    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    # --- PHẦN 3: LIVE MINH NGỌC (ỐP CẦU) ---
    st.write("---")
    st.header("🔴 LIVE MONITOR: ỐP CẦU TRỰC TIẾP (Minh Ngọc)")
    
    # Nút cập nhật Live
    col_live_btn, col_live_status = st.columns([1, 3])
    with col_live_btn:
        refresh_live = st.button("🔄 CẬP NHẬT LIVE", type="primary")
    
    # Lấy dữ liệu Live
    live_str, filled_len = fetch_live_minhngoc()
    
    with col_live_status:
        if live_str:
            pct = int((filled_len/107)*100)
            st.markdown(f"<div class='live-progress'>Tiến độ quay: {filled_len}/107 ({pct}%)</div>", unsafe_allow_html=True)
            st.progress(pct)
        else:
            st.error("Chưa lấy được dữ liệu Minh Ngọc. Kiểm tra mạng.")
            return

    # HIỂN THỊ BOX DỰ BÁO
    if not st.session_state.get('saved_bridges') and not st.session_state.get('saved_prizes'):
        st.info("💡 Hãy bấm nút 'QUÉT TỰ ĐỘNG' ở trên để tìm cầu trước. Sau đó kết quả sẽ hiện ở đây.")
    else:
        st.subheader("⚡ CẦU ĐANG NỔ SỐ")
        
        # A. NẾU ĐANG SOI VỊ TRÍ HOẶC 3 CÀNG
        saved_b = st.session_state.get('saved_bridges', [])
        if saved_b:
            cols = st.columns(5)
            count = 0
            for idx, br in enumerate(saved_b):
                i, j = br['i'], br['j']
                val_i, val_j = live_str[i], live_str[j]
                
                if val_i != '?' and val_j != '?': # Đã có số
                    pred = val_i + val_j
                    with cols[count % 5]:
                        st.markdown(f"""
                        <div class="hot-box">
                            <div class="hot-title">🔥 Cầu #{idx+1} (Thông {br['streak']}n)</div>
                            <div style="font-size:10px">{pos_map[i]} + {pos_map[j]}</div>
                            <div class="hot-val">{pred}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    count += 1
            if count == 0: st.info("Các cầu vị trí đang chờ quay...")

        # B. NẾU ĐANG SOI GIẢI
        saved_p = st.session_state.get('saved_prizes', [])
        if saved_p:
            st.write("Trạng thái Cầu Giải:")
            # Với cầu giải, ta cần map lại vị trí index
            prize_map = get_prize_map_no_gdb()
            active_prizes = []
            
            for p in saved_p:
                p_name = p['prize']
                s, e = prize_map.get(p_name)
                p_str_live = live_str[s:e]
                
                if '?' not in p_str_live: # Giải này đã quay xong
                    active_prizes.append(f"✅ **{p_name}** (Thông {p['streak']}n): {p_str_live}")
            
            if active_prizes:
                for line in active_prizes: st.write(line)
            else:
                st.info("Các giải trong danh sách cầu chưa quay xong.")

if __name__ == "__main__":
    main()
