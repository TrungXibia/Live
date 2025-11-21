import streamlit as st
import requests
import pandas as pd
import json
import re

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH & CSS (ĐÃ CHỈNH SIÊU NHỎ GỌN)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Soi Cầu Pro: Compact View", page_icon="📊", layout="wide")

st.markdown("""
<style>
    .stDataFrame {font-size: 12px;}
    div.stButton > button {width: 100%; height: 3em; font-weight: bold;}
    thead tr th:first-child {display:none}
    tbody th {display:none}
    
    .step-header {
        background-color: #e3f2fd; padding: 10px; border-radius: 5px; 
        font-weight: bold; color: #0d47a1; margin-bottom: 10px; 
        border-left: 4px solid #1565c0; font-size: 16px;
    }
    
    /* CSS MỚI: SIÊU NHỎ GỌN */
    
    /* Box VIP (2+ ngày) - Màu Cam */
    .hot-box-vip {
        background-color: #fff3e0; border: 1px solid #ff9800; 
        border-radius: 4px; padding: 2px; text-align: center; margin-bottom: 4px;
        min-height: 50px;
    }
    .hot-title-vip {font-size: 9px; color: #e65100; line-height: 1.1; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;}
    .hot-val-vip {font-size: 18px; color: #d32f2f; font-weight: 900; line-height: 1.2;}

    /* Box 1 Ngày - Màu Xanh */
    .hot-box-1d {
        background-color: #f1f8e9; border: 1px solid #81c784; 
        border-radius: 4px; padding: 2px; text-align: center; margin-bottom: 4px;
        min-height: 50px;
    }
    .hot-title-1d {font-size: 9px; color: #2e7d32; line-height: 1.1; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;}
    .hot-val-1d {font-size: 18px; color: #1b5e20; font-weight: 900; line-height: 1.2;}
    
    .stTextArea textarea {font-size: 14px; font-family: monospace; color: #000;}
    
    /* Giảm khoảng cách giữa các cột */
    div[data-testid="column"] {
        padding: 0px 2px !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DỮ LIỆU & API
# -----------------------------------------------------------------------------
def get_api_url(limit=50):
    return f"https://www.kqxs88.live/api/front/open/lottery/history/list/game?limitNum={limit}&gameCode=miba"

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
def fetch_history(limit=50):
    try:
        url = get_api_url(limit)
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10).json()
        return r.get('t', {}).get('issueList', [])
    except Exception as e:
        st.error(f"Lỗi kết nối API: {e}")
        return []

def fetch_daiphat_live():
    try:
        from bs4 import BeautifulSoup
        url = "https://xosodaiphat.com/xsmb-truc-tiep.html"
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        mapping = {
            'ĐB': 'DB', 'G1': '1', 'G2': '2', 'G3': '3',
            'G4': '4', 'G5': '5', 'G6': '6', 'G7': '7'
        }
        
        results = []
        for label, code in mapping.items():
            nums = []
            idx = 0
            while True:
                # ID pattern: mb_prize_DB_item_0, mb_prize_1_item_0, ...
                element_id = f"mb_prize_{code}_item_{idx}"
                span = soup.find('span', id=element_id)
                if span:
                    text = span.get_text(strip=True)
                    if text and text.isdigit():
                        nums.append(text)
                    idx += 1
                else:
                    break
            
            if nums:
                results.append(f"{label}: {', '.join(nums)}")
                
        return "\n".join(results)
    except Exception as e:
        return ""

def fetch_live_data():
    # 1. Thử Minh Ngọc
    try:
        from bs4 import BeautifulSoup
        url = "https://www.minhngoc.net.vn/xo-so-truc-tiep/mien-bac.html"
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        mapping = {
            'ĐB': 'giaidb', 'G1': 'giai1', 'G2': 'giai2', 'G3': 'giai3',
            'G4': 'giai4', 'G5': 'giai5', 'G6': 'giai6', 'G7': 'giai7'
        }
        
        results = []
        box = soup.find('div', class_='box_kqxs')
        if box:
            for label, cls in mapping.items():
                row = box.find(class_=cls)
                if row:
                    nums = [span.get_text(strip=True) for span in row.find_all('div', recursive=True) if span.get_text(strip=True).isdigit()]
                    if not nums:
                         nums = [s.get_text(strip=True) for s in row.find_all(string=True) if s.get_text(strip=True).isdigit() and len(s.get_text(strip=True)) > 1]
                    if nums:
                        results.append(f"{label}: {', '.join(nums)}")
            
            if results: return "\n".join(results)
    except: pass

    # 2. Fallback sang Đại Phát
    return fetch_daiphat_live()

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
# 3. THUẬT TOÁN
# -----------------------------------------------------------------------------
def scan_positions_auto(data, mode, allow_rev, bridge_type="same_day", min_streak=2):
    if not data: return []
    results = []
    
    # Xác định phạm vi quét
    # same_day: Quét trên chính bản ghi đó (bỏ qua GĐB vì GĐB là kết quả) -> start_idx = 5 (GĐB có 5 ký tự)
    # cross_day: Quét trên bản ghi ngày hôm trước (lấy cả GĐB) -> start_idx = 0
    start_idx = 5 if bridge_type == "same_day" else 0
    
    # Lấy mẫu để tìm candidates
    # Nếu cross_day: Cần ít nhất 2 ngày dữ liệu (Hôm nay và Hôm qua) để check 1 nhịp
    if bridge_type == "cross_day" and len(data) < 2: return []
    
    day0 = data[0] # Ngày hiện tại (Kết quả cần soi)
    source_day = data[0] if bridge_type == "same_day" else data[1] # Nguồn dữ liệu để soi
    
    body = source_day['body']
    cand = []
    
    # 1. Tìm Candidate: Cặp vị trí (i, j) trên source_day tạo ra kết quả của day0
    for i in range(start_idx, len(body)):
        for j in range(start_idx, len(body)):
            if i == j: continue
            val = body[i] + body[j]
            match = False
            
            # So sánh với kết quả của day0
            if mode == "straight":
                if val == day0['de']: match = True
                elif allow_rev and val == day0['de_rev']: match = True
            else: # mode == "set"
                if get_set(val) == day0['de_set']: match = True
            
            if match: cand.append((i, j))
    
    # 2. Check Streak cho từng candidate
    for (i, j) in cand:
        streak = 0
        max_k = len(data) - 1 if bridge_type == "cross_day" else len(data)
        
        for k in range(max_k):
            current_res_day = data[k]
            current_src_day = data[k] if bridge_type == "same_day" else data[k+1]
            
            val = current_src_day['body'][i] + current_src_day['body'][j]
            match = False
            
            if mode == "straight":
                if val == current_res_day['de']: match = True
                elif allow_rev and val == current_res_day['de_rev']: match = True
            else:
                if get_set(val) == current_res_day['de_set']: match = True
            
            if match: streak += 1
            else: break 
            
        if streak >= 1: 
            results.append({"i": i, "j": j, "streak": streak})
            
    results.sort(key=lambda x: x['streak'], reverse=True)
    return results

def scan_prizes_auto(data, mode):
    pmap = get_prize_map_no_gdb(); res = []
    for p, (s, e) in pmap.items():
        streak = 0
        for d in data:
            digits = set(d['body'][s:e])
            match = False
            if mode == "straight": match = (d['de'][0] in digits and d['de'][1] in digits)
            else:
                for n in BO_DE_DICT.get(get_set(d['de']), []):
                    if n[0] in digits and n[1] in digits: match = True; break
            if match: streak += 1
            else: break
        if streak >= 1: res.append({"prize": p, "streak": streak, "val": data[0]['body'][s:e]})
    res.sort(key=lambda x: x['streak'], reverse=True)
    return res

# -----------------------------------------------------------------------------
# 4. SMART PARSER
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
    st.title("🎯 Siêu Gà Súp pờ soi")

    if 'saved_bridges' not in st.session_state: st.session_state['saved_bridges'] = []
    if 'saved_prizes' not in st.session_state: st.session_state['saved_prizes'] = []
    if 'pos_map' not in st.session_state: st.session_state['pos_map'] = get_pos_map()
    if 'live_text' not in st.session_state: st.session_state['live_text'] = ""
    if 'auto_refresh' not in st.session_state: st.session_state['auto_refresh'] = False

    # --- MENU ---
    c1, c2, c3 = st.columns([2, 1.5, 1.5])
    with c1: 
        method = st.selectbox("PHƯƠNG PHÁP", ["Cầu Vị Trí (Ghép 2 số)", "Cầu Giải (Nhị Hợp)"])
        
        bridge_type = "same_day"
        if "Vị Trí" in method:
            b_type_label = st.radio("Loại Cầu", ["Cầu Trong Ngày (Live)", "Cầu Ngày Trước (Cross-day)"])
            bridge_type = "same_day" if "Trong Ngày" in b_type_label else "cross_day"
            
    with c2: 
        is_set = st.checkbox("Soi Bộ Đào", False)
        mode = "set" if is_set else "straight"
        limit_days = st.slider("Số ngày", 10, 100, 50)
        
    with c3: 
        allow_rev = st.checkbox("Đảo AB", True) if not is_set and "Vị Trí" in method else True
        min_streak = st.number_input("Min Streak", 1, 20, 1)

    # --- LOAD DATA ---
    raw = fetch_history(limit_days)
    data = process_data(raw)
    if not data: st.error("Lỗi API"); return
    pos_map = get_pos_map()
    
    # --- AUTO SCAN ---
    final_bridges = []
    final_prizes = []

    if "Vị Trí" in method:
        res = scan_positions_auto(data, mode, allow_rev, bridge_type, min_streak)
        final_bridges = res
    elif "Cầu Giải" in method:
        res = scan_prizes_auto(data, mode)
        final_prizes = res

    vip_bridges = [b for b in final_bridges if b['streak'] >= 2]
    oneday_bridges = [b for b in final_bridges if b['streak'] == 1]
    
    vip_prizes = [p for p in final_prizes if p['streak'] >= 2]
    oneday_prizes = [p for p in final_prizes if p['streak'] == 1]

    # --- BƯỚC 1: KẾT QUẢ QUÉT (THU GỌN) ---
    st.markdown("<div class='step-header'>BƯỚC 1: KẾT QUẢ QUÉT LỊCH SỬ</div>", unsafe_allow_html=True)
    
    if "Vị Trí" in method:
        if vip_bridges:
            st.success(f"🔥 {len(vip_bridges)} Cầu VIP (Max {vip_bridges[0]['streak']}n)")
            # HIỂN THỊ LUÔN BẢNG (KHÔNG ẨN)
            df_vip = [{"#": i+1, "Vị trí": f"{pos_map[br['i']]} + {pos_map[br['j']]}", "Thông": f"{br['streak']}n"} for i,br in enumerate(vip_bridges[:20])]
            st.dataframe(pd.DataFrame(df_vip), use_container_width=True)
        
        if oneday_bridges:
            st.info(f"✅ {len(oneday_bridges)} Cầu 1 Ngày")

    elif "Cầu Giải" in method:
        if vip_prizes: 
            st.success(f"🔥 {len(vip_prizes)} Giải VIP")
            # HIỂN THỊ LUÔN BẢNG
            df_vip_prize = [{"Giải": p['prize'], "Thông": f"{p['streak']}n"} for p in vip_prizes]
            st.dataframe(pd.DataFrame(df_vip_prize), use_container_width=True)
            
        if oneday_prizes: 
            st.info(f"✅ {len(oneday_prizes)} Giải 1 Ngày")
            df_1d_prize = [{"Giải": p['prize'], "Thông": f"{p['streak']}n"} for p in oneday_prizes]
            st.dataframe(pd.DataFrame(df_1d_prize), use_container_width=True)

    # --- BƯỚC 2: DÁN LIVE ---
    st.markdown("<div class='step-header'>BƯỚC 2: DÁN KẾT QUẢ LIVE</div>", unsafe_allow_html=True)
    col_input, col_check = st.columns([2, 1])
    with col_input:
        raw_text = st.text_area("Dán nội dung (Minh Ngọc/Đại Phát):", value=st.session_state['live_text'], height=100, placeholder="Giải nhất 89650...")
        has_gdb = st.checkbox("Có GĐB?", value=True)
        
    with col_check:
        st.write("Tự động lấy KQ:")
        if st.button("🔄 Cập nhật Live (Auto)"):
            live_data = fetch_live_data()
            if live_data:
                st.session_state['live_text'] = live_data
                st.rerun()
            else:
                st.warning("Chưa lấy được dữ liệu hoặc lỗi.")
        
        auto = st.checkbox("Tự động (10s/lần)", value=st.session_state['auto_refresh'])
        if auto:
            st.session_state['auto_refresh'] = True
            import time
            time.sleep(10)
            st.rerun()
        else:
            st.session_state['auto_refresh'] = False
        
    # --- BƯỚC 3: ỐP CẦU ---
    if raw_text or bridge_type == "cross_day":
        st.markdown("<div class='step-header'>BƯỚC 3: KẾT QUẢ ỐP CẦU (REAL-TIME)</div>", unsafe_allow_html=True)
        
        live_str_107 = ""
        if raw_text:
            live_str_107, preview_info = parse_smart_text(raw_text, has_gdb)
            filled = 107 - live_str_107.count('?')
            st.progress(filled/107, f"Tiến độ: {filled}/107 số")
        elif bridge_type == "cross_day":
             # Nếu là cross_day và không có text, ta dùng data[0] làm nguồn soi
             # Nhưng thực ra logic cross_day là lấy data[0] để dự đoán ngày mai
             # Nên ta coi data[0]['body'] là nguồn
             live_str_107 = data[0]['body']
             st.info(f"🔮 Dự đoán cho ngày tiếp theo (Dựa trên KQ ngày {data[0]['issue']})")

        collected_predictions = set()
        oneday_predictions = set()

        if "Vị Trí" in method:
            # --- KHU VỰC VIP (MÀU CAM) ---
            if vip_bridges:
                st.write("**🔥 Cầu VIP (2+ ngày):**")
                cols = st.columns(8) 
                count = 0
                for idx, br in enumerate(vip_bridges):
                    i, j = br['i'], br['j']
                    
                    # Logic lấy số
                    vi, vj = '?', '?'
                    if i < len(live_str_107) and j < len(live_str_107):
                        vi, vj = live_str_107[i], live_str_107[j]
                    
                    if vi != '?' and vj != '?':
                        pred = vi + vj
                        collected_predictions.add(pred)
                        with cols[count%8]:
                            st.markdown(f"""<div class='hot-box-vip'><div class='hot-title-vip'>#{idx+1} ({br['streak']}n)</div><div class='hot-val-vip'>{pred}</div></div>""", unsafe_allow_html=True)
                        count += 1
                if count == 0: st.caption("Chưa có cầu VIP nổ (hoặc chưa quay đến).")

            # --- KHU VỰC 1 NGÀY (MÀU XANH) ---
            if oneday_bridges:
                st.write("**✅ Cầu 1 Ngày (Mới):**")
                cols1 = st.columns(10) 
                count1 = 0
                for idx, br in enumerate(oneday_bridges):
                    i, j = br['i'], br['j']
                    
                    vi, vj = '?', '?'
                    if i < len(live_str_107) and j < len(live_str_107):
                        vi, vj = live_str_107[i], live_str_107[j]
                        
                    if vi != '?' and vj != '?':
                        pred = vi + vj
                        oneday_predictions.add(pred)
                        with cols1[count1%10]:
                            st.markdown(f"""<div class='hot-box-1d'><div class='hot-title-1d'>1day</div><div class='hot-val-1d'>{pred}</div></div>""", unsafe_allow_html=True)
                        count1 += 1
                if count1 == 0: st.caption("Chưa có cầu 1 ngày nổ.")

        elif "Cầu Giải" in method:
            pmap = get_prize_map_no_gdb()
            # VIP
            found_vip = False
            st.write("🔥 Giải VIP:")
            for p in vip_prizes:
                pname = p['prize']; s, e = pmap.get(pname)
                if e <= len(live_str_107) and '?' not in live_str_107[s:e]:
                    st.success(f"{pname} ({p['streak']}n): {live_str_107[s:e]}")
                    found_vip = True
            if not found_vip: st.caption("...")
            
            # 1 DAY
            st.write("✅ Giải 1 Ngày:")
            for p in oneday_prizes:
                pname = p['prize']; s, e = pmap.get(pname)
                if e <= len(live_str_107) and '?' not in live_str_107[s:e]:
                    st.info(f"{pname}: {live_str_107[s:e]}")

        # --- BƯỚC 4: COPY TÁCH BIỆT ---
        if "Vị Trí" in method and (collected_predictions or oneday_predictions):
            st.markdown("<div class='step-header'>📋 COPY DÀN SỐ</div>", unsafe_allow_html=True)
            
            def make_text(pred_set, mode):
                if not pred_set: return ""
                if mode == "straight": return ", ".join(sorted(list(pred_set)))
                else:
                    sets = set(); nums = set()
                    for n in pred_set:
                        s = get_set(n); sets.add(f"Bộ {s}")
                        if s in BO_DE_DICT: nums.update(BO_DE_DICT[s])
                    return f"BỘ: {', '.join(sorted(list(sets)))}\n\nSỐ: {', '.join(sorted(list(nums)))}"

            c_vip, c_1d = st.columns(2)
            with c_vip:
                st.markdown("🔥 **VIP (2+ Ngày):**")
                st.text_area("Copy VIP:", value=make_text(collected_predictions, mode), height=100)
            with c_1d:
                st.markdown("✅ **1 Ngày:**")
                st.text_area("Copy 1 Day:", value=make_text(oneday_predictions, mode), height=100)

if __name__ == "__main__":
    main()
