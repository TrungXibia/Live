import streamlit as st
import requests
import pandas as pd
import json
import scraper

# ... (Giữ nguyên phần cấu hình & hàm xử lý lịch sử cũ) ...
# CHỈ CẦN COPY ĐÈ PHẦN MAIN BÊN DƯỚI NẾU BẠN ĐÃ CÓ FILE APP.PY TRƯỚC ĐÓ
# HOẶC COPY TOÀN BỘ NẾU MUỐN CHẮC CHẮN

# -----------------------------------------------------------------------------
# CẤU HÌNH (Full code để tránh lỗi)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Soi Cầu Ảnh Thông Minh", page_icon="📸", layout="wide")
st.markdown("""<style>.stDataFrame{font-size:14px}div.stButton>button{width:100%;height:3em;font-weight:bold}.hot-box{background-color:#ffebee;border:2px solid #ef5350;border-radius:8px;padding:10px;text-align:center}.hot-val{font-size:26px;color:#d32f2f;font-weight:900}textarea{font-size:18px!important;font-family:monospace}</style>""", unsafe_allow_html=True)

API_URL = "https://www.kqxs88.live/api/front/open/lottery/history/list/game?limitNum=50&gameCode=miba"
XSMB_STRUCTURE = [("GĐB", 1, 5), ("G1", 1, 5), ("G2", 2, 5), ("G3", 6, 5),("G4", 4, 4), ("G5", 6, 4), ("G6", 3, 3), ("G7", 4, 2)]
BO_DE_DICT = {"00": ["00","55","05","50"], "11": ["11","66","16","61"], "22": ["22","77","27","72"], "33": ["33","88","38","83"],"44": ["44","99","49","94"], "01": ["01","10","06","60","51","15","56","65"], "02": ["02","20","07","70","52","25","57","75"],"03": ["03","30","08","80","53","35","58","85"], "04": ["04","40","09","90","54","45","59","95"],"12": ["12","21","17","71","62","26","67","76"], "13": ["13","31","18","81","63","36","68","86"],"14": ["14","41","19","91","64","46","69","96"], "23": ["23","32","28","82","73","37","78","87"],"24": ["24","42","29","92","74","47","79","97"], "34": ["34","43","39","93","84","48","89", "98"]}
NUMBER_TO_SET_MAP = {str(n): s for s, nums in BO_DE_DICT.items() for n in nums}

@st.cache_data(ttl=60)
def fetch_history():
    try:
        r = requests.get(API_URL, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10).json()
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

def auto_scan_positions(data, mode, allow_rev):
    if not data: return []
    day0 = data[0]; body = day0['body']; cand = []
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

def auto_scan_prizes(data, mode):
    pmap = get_prize_map_no_gdb(); res = []
    for p, (s, e) in pmap.items():
        strk = 0
        for d in data:
            val = d['body'][s:e]
            d_set = set(val)
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
# MAIN
# -----------------------------------------------------------------------------
def main():
    st.title("📸 Soi Cầu Ảnh: Fix 'Mã ĐB'")
    
    if 'saved_bridges' not in st.session_state: st.session_state['saved_bridges'] = []
    if 'saved_prizes' not in st.session_state: st.session_state['saved_prizes'] = []
    if 'saved_cang' not in st.session_state: st.session_state['saved_cang'] = []
    if 'pos_map' not in st.session_state: st.session_state['pos_map'] = get_pos_map()

    c1, c2, c3 = st.columns(3)
    with c1: method = st.selectbox("Phương Pháp", ["1. Cầu Vị Trí", "2. Cầu Giải", "3. Cầu 3 Càng"])
    with c2: is_set = st.checkbox("Soi Bộ", False); mode = "set" if is_set else "straight"
    with c3: allow_rev = st.checkbox("Đảo AB", True) if not is_set and "Vị Trí" in method else True
    
    raw = fetch_history()
    data = process_data(raw)
    
    # Auto scan
    if not st.session_state['saved_bridges'] and not st.session_state['saved_prizes']:
        with st.spinner("Đang chuẩn bị dữ liệu cầu..."):
            if "Vị Trí" in method or "3 Càng" in method:
                st.session_state['saved_bridges'] = auto_scan_positions(data, mode, allow_rev)[:30]
                st.session_state['saved_cang'] = auto_scan_tam_cang(data)[:10]
            if "Cầu Giải" in method:
                st.session_state['saved_prizes'] = auto_scan_prizes(data, mode)
        st.success("Đã sẵn sàng!")

    st.divider()
    st.subheader("📸 Bước 2: Upload ảnh KQXS (Minh Ngọc/Đại Phát)")
    uploaded_file = st.file_uploader("Chọn ảnh", type=['png', 'jpg', 'jpeg'])
    
    if uploaded_file is not None:
        with st.spinner("Đang đọc ảnh & Lọc rác..."):
            # Gọi hàm mới, nhận thêm biến found_anchor
            raw_nums, found_anchor = scraper.extract_numbers_from_image(uploaded_file)
            
        if found_anchor:
            st.success("✅ Đã tìm thấy mốc 'G.ĐB' hoặc 'Giải ĐB'. Đã lọc bỏ phần đầu.")
        else:
            st.warning("⚠️ Không tìm thấy chữ 'G.ĐB'. Hệ thống lấy toàn bộ số tìm thấy (Có thể lẫn Ngày tháng/Mã ĐB). Vui lòng kiểm tra kỹ.")
            
        st.info(f"Tìm thấy {len(raw_nums)} số giải.")
        
        # Hiển thị ô sửa
        nums_text = " ".join(raw_nums)
        user_nums_str = st.text_area("Kiểm tra list số:", value=nums_text, height=100)
        
        if st.button("🚀 ỐP CẦU NGAY", type="primary"):
            final_nums = user_nums_str.split()
            if len(final_nums) < 27:
                st.error(f"Thiếu số! Mới có {len(final_nums)}/27 giải. Hãy kiểm tra lại ảnh.")
            else:
                full_str_live = scraper.map_numbers_to_107_str(final_nums)
                st.write("---")
                
                # LOGIC HIỂN THỊ KẾT QUẢ
                pos_map = st.session_state['pos_map']
                
                if "Vị Trí" in method or "3 Càng" in method:
                    bridges = st.session_state['saved_bridges']
                    cols = st.columns(5); count = 0
                    for idx, br in enumerate(bridges):
                        i, j = br['i'], br['j']
                        if i < len(full_str_live) and j < len(full_str_live):
                            vi, vj = full_str_live[i], full_str_live[j]
                            if vi != '?' and vj != '?':
                                with cols[count%5]:
                                    st.markdown(f"<div class='hot-box'><div style='font-size:10px'>Cầu #{idx+1} ({br['streak']}n)</div><div style='font-size:11px'>{pos_map[i]}+{pos_map[j]}</div><div class='hot-val'>{vi}{vj}</div></div>", unsafe_allow_html=True)
                                count += 1
                    if count == 0: st.warning("Không có cầu nào khớp.")

                if "Cầu Giải" in method:
                    prizes = st.session_state['saved_prizes']
                    pmap = get_prize_map_no_gdb()
                    found = False
                    for p in prizes:
                        pname = p['prize']
                        s, e = pmap.get(pname)
                        val = full_str_live[s:e]
                        if '?' not in val:
                            st.success(f"✅ **{pname}** (Thông {p['streak']}n): {val}")
                            found = True
                    if not found: st.warning("Không có giải nào khớp.")

if __name__ == "__main__":
    main()
