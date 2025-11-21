import streamlit as st
import requests
import pandas as pd
import json
import re

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH & CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Soi Cầu VIP: Auto + 1 Day", page_icon="🎯", layout="wide")

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div.stButton > button {width: 100%; height: 3em; font-weight: bold;}
    thead tr th:first-child {display:none}
    tbody th {display:none}
    
    .step-header {
        background-color: #e3f2fd; padding: 15px; border-radius: 8px; 
        font-weight: bold; color: #0d47a1; margin-bottom: 15px; 
        border-left: 5px solid #1565c0; font-size: 18px;
    }
    
    .hot-box {
        background-color: #fff3e0; border: 2px solid #ff9800; 
        border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 10px;
    }
    .hot-title {font-size: 11px; color: #e65100; font-weight: bold;}
    .hot-val {font-size: 24px; color: #d32f2f; font-weight: 900;}
    
    /* Box cho cầu 1 ngày (Màu nhạt hơn) */
    .hot-box-1day {
        background-color: #f5f5f5; border: 2px solid #9e9e9e; 
        border-radius: 8px; padding: 5px; text-align: center; margin-bottom: 5px;
    }
    .hot-title-1day {font-size: 10px; color: #616161;}
    .hot-val-1day {font-size: 20px; color: #424242; font-weight: bold;}

    .stTextArea textarea {font-size: 16px; font-family: monospace; color: #000;}
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
# 3. THUẬT TOÁN (ĐÃ SỬA ĐỂ LẤY CẢ CẦU 1 NGÀY)
# -----------------------------------------------------------------------------
def scan_positions_auto(data, mode, allow_rev):
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
    
    results = []
    for (i, j) in cand:
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
        
        # UPDATE: Lấy cả cầu 1 ngày
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
        # UPDATE: Lấy cả cầu 1 ngày
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
    st.title("🎯 Soi Cầu VIP: Full Option")

    # --- MENU ---
    with st.container():
        c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 1.5])
        with c1:
            method = st.selectbox("💎 PHƯƠNG PHÁP", ["Cầu Vị Trí (Ghép 2 số)", "Cầu Giải (Nhị Hợp)"])
        with c2:
            st.info("⚡ Auto: VIP + Cầu 1 ngày")
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
    pos_map = get_pos_map()
    
    # --- AUTO SCAN ---
    final_bridges = []
    final_prizes = []

    if "Vị Trí" in method:
        res = scan_positions_auto(data, mode, allow_rev)
        final_bridges = res
    elif "Cầu Giải" in method:
        res = scan_prizes_auto(data, mode)
        final_prizes = res

    # Tách cầu VIP và cầu 1 ngày
    vip_bridges = [b for b in final_bridges if b['streak'] >= 2]
    oneday_bridges = [b for b in final_bridges if b['streak'] == 1]
    
    vip_prizes = [p for p in final_prizes if p['streak'] >= 2]
    oneday_prizes = [p for p in final_prizes if p['streak'] == 1]

    # --- BƯỚC 1: KẾT QUẢ QUÉT ---
    st.markdown("<div class='step-header'>BƯỚC 1: KẾT QUẢ QUÉT LỊCH SỬ</div>", unsafe_allow_html=True)
    
    if "Vị Trí" in method:
        # VIP TABLE
        if vip_bridges:
            st.success(f"✅ Tìm thấy {len(vip_bridges)} Cầu VIP (2+ ngày). Dài nhất: {vip_bridges[0]['streak']} ngày.")
            list_data = []
            for idx, br in enumerate(vip_bridges[:20]): 
                 val_old = data[0]['body'][br['i']] + data[0]['body'][br['j']]
                 list_data.append({"Hạng": f"#{idx+1}", "Vị trí": f"{pos_map[br['i']]} + {pos_map[br['j']]}", "Thông": f"{br['streak']}n", "Qua về": val_old})
            st.dataframe(pd.DataFrame(list_data), use_container_width=True)
        else:
            st.warning("Không có cầu VIP (>=2 ngày).")
            
        # 1-DAY TABLE (ẨN/HIỆN)
        with st.expander(f"👁️ Xem thêm: {len(oneday_bridges)} Cầu chạy 1 ngày"):
            if oneday_bridges:
                list_1d = []
                for idx, br in enumerate(oneday_bridges[:50]):
                    val_old = data[0]['body'][br['i']] + data[0]['body'][br['j']]
                    list_1d.append({"#": idx+1, "Vị trí": f"{pos_map[br['i']]} + {pos_map[br['j']]}", "Qua về": val_old})
                st.dataframe(pd.DataFrame(list_1d), use_container_width=True)
            else:
                st.write("Không có cầu 1 ngày.")

    elif "Cầu Giải" in method:
        # VIP TABLE
        if vip_prizes:
            st.success(f"✅ Tìm thấy {len(vip_prizes)} Giải VIP.")
            list_data = [{"Hạng": f"#{i+1}", "Giải": p['prize'], "Thông": f"{p['streak']}n"} for i, p in enumerate(vip_prizes)]
            st.dataframe(pd.DataFrame(list_data), use_container_width=True)
        else:
            st.warning("Không có giải VIP.")
            
        # 1-DAY TABLE
        with st.expander(f"👁️ Xem thêm: {len(oneday_prizes)} Giải chạy 1 ngày"):
            if oneday_prizes:
                list_1d = [{"Giải": p['prize'], "Thông": "1 ngày"} for p in oneday_prizes]
                st.dataframe(pd.DataFrame(list_1d), use_container_width=True)

    # --- BƯỚC 2: DÁN LIVE ---
    st.markdown("<div class='step-header'>BƯỚC 2: DÁN KẾT QUẢ LIVE</div>", unsafe_allow_html=True)
    col_input, col_check = st.columns([2, 1])
    with col_input:
        raw_text = st.text_area("Dán nội dung (Minh Ngọc/Đại Phát):", height=150, placeholder="Giải nhất 89650...")
        has_gdb = st.checkbox("Văn bản CÓ chứa Giải Đặc Biệt?", value=True)
        
    # --- BƯỚC 3: ỐP CẦU ---
    if raw_text:
        st.markdown("<div class='step-header'>BƯỚC 3: KẾT QUẢ ỐP CẦU (REAL-TIME)</div>", unsafe_allow_html=True)
        
        live_str_107, preview_info = parse_smart_text(raw_text, has_gdb)
        filled = 107 - live_str_107.count('?')
        st.progress(filled/107, f"Tiến độ: {filled}/107 số")

        collected_predictions = set()

        # 1. VỊ TRÍ
        if "Vị Trí" in method:
            # --- KHU VỰC CẦU VIP ---
            if vip_bridges:
                st.subheader("🔥 Cầu VIP (2+ ngày)")
                cols = st.columns(5); count = 0
                for idx, br in enumerate(vip_bridges):
                    i, j = br['i'], br['j']
                    if i < len(live_str_107) and j < len(live_str_107):
                        vi, vj = live_str_107[i], live_str_107[j]
                        if vi != '?' and vj != '?':
                            pred = vi + vj
                            collected_predictions.add(pred)
                            with cols[count%5]:
                                st.markdown(f"""<div class='hot-box'><div class='hot-title'>#{idx+1} (Thông {br['streak']}n)</div><div style='font-size:10px;color:gray'>{pos_map[i]}+{pos_map[j]}</div><div class='hot-val'>{pred}</div></div>""", unsafe_allow_html=True)
                            count += 1
                if count == 0: st.info("⏳ Cầu VIP chưa nổ số...")
            
            # --- KHU VỰC CẦU 1 NGÀY (ẨN) ---
            if oneday_bridges:
                with st.expander("⚡ Xem Cầu 1 ngày đang nổ (Rủi ro cao)"):
                    cols1 = st.columns(6); count1 = 0
                    for idx, br in enumerate(oneday_bridges):
                        i, j = br['i'], br['j']
                        if i < len(live_str_107) and j < len(live_str_107):
                            vi, vj = live_str_107[i], live_str_107[j]
                            if vi != '?' and vj != '?':
                                pred = vi + vj
                                # Không add vào collected_predictions chính, để riêng
                                with cols1[count1%6]:
                                    st.markdown(f"""<div class='hot-box-1day'><div class='hot-title-1day'>1 ngày</div><div class='hot-val-1day'>{pred}</div></div>""", unsafe_allow_html=True)
                                count1 += 1
                    if count1 == 0: st.info("Chưa có cầu 1 ngày nào nổ.")

        # 2. GIẢI
        elif "Cầu Giải" in method:
            # VIP
            if vip_prizes:
                st.subheader("🔥 Giải VIP (2+ ngày)")
                pmap = get_prize_map_no_gdb()
                for p in vip_prizes:
                    pname = p['prize']; s, e = pmap.get(pname)
                    if e <= len(live_str_107):
                        val = live_str_107[s:e]
                        if '?' not in val: st.success(f"✅ Giải **{pname}** (Thông {p['streak']}n) về: **{val}**")
            
            # 1 DAY
            if oneday_prizes:
                with st.expander("⚡ Giải 1 ngày"):
                    pmap = get_prize_map_no_gdb()
                    for p in oneday_prizes:
                        pname = p['prize']; s, e = pmap.get(pname)
                        if e <= len(live_str_107):
                            val = live_str_107[s:e]
                            if '?' not in val: st.info(f"🔹 Giải **{pname}** (1 ngày) về: **{val}**")

        # --- BƯỚC 4: COPY DÀN SỐ (CHỈ LẤY TỪ CẦU VIP) ---
        if "Vị Trí" in method and collected_predictions:
            st.markdown("<div class='step-header'>📋 DÀN SỐ VIP ĐỂ COPY</div>", unsafe_allow_html=True)
            if mode == "straight":
                final_list = sorted(list(collected_predictions))
                st.text_area("Copy:", value=", ".join(final_list), height=70)
            else: 
                detected_sets = set()
                full_expansion = set()
                for num in collected_predictions:
                    s = get_set(num)
                    detected_sets.add(f"Bộ {s}")
                    if s in BO_DE_DICT: full_expansion.update(BO_DE_DICT[s])
                c_set, c_num = st.columns(2)
                with c_set: st.text_area("Bộ:", value=", ".join(sorted(list(detected_sets))), height=70)
                with c_num: st.text_area("Số:", value=", ".join(sorted(list(full_expansion))), height=70)

if __name__ == "__main__":
    main()
