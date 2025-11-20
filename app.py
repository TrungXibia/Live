import streamlit as st
import requests
import pandas as pd
import json

# -----------------------------------------------------------------------------
# CẤU HÌNH TRANG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Soi Cầu: Tâm Càng & Đề",
    page_icon="🎯",
    layout="wide"
)

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div[data-testid="stExpander"] {border: 1px solid #e6e6e6; border-radius: 5px;}
    h3 {color: #0f54c9;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH & DỮ LIỆU
# -----------------------------------------------------------------------------
API_URL = "https://www.kqxs88.live/api/front/open/lottery/history/list/game?limitNum=10&gameCode=miba"

XSMB_STRUCTURE = [
    ("G1", 1, 5), ("G2", 2, 5), ("G3", 6, 5),
    ("G4", 4, 4), ("G5", 6, 4), ("G6", 3, 3), ("G7", 4, 2)
]

BO_DE_DICT = {
    "00": ["00", "55", "05", "50"], "11": ["11", "66", "16", "61"],
    "22": ["22", "77", "27", "72"], "33": ["33", "88", "38", "83"],
    "44": ["44", "99", "49", "94"], "01": ["01", "10", "06", "60", "51", "15", "56", "65"],
    "02": ["02", "20", "07", "70", "52", "25", "57", "75"],
    "03": ["03", "30", "08", "80", "53", "35", "58", "85"],
    "04": ["04", "40", "09", "90", "54", "45", "59", "95"],
    "12": ["12", "21", "17", "71", "62", "26", "67", "76"],
    "13": ["13", "31", "18", 81, "63", "36", "68", "86"],
    "14": ["14", "41", "19", "91", "64", "46", "69", "96"],
    "23": ["23", "32", "28", "82", "73", "37", "78", "87"],
    "24": ["24", "42", "29", "92", "74", "47", "79", "97"],
    "34": ["34", "43", "39", "93", "84", "48", "89", "98"]
}
NUMBER_TO_SET_MAP = {str(n): s for s, nums in BO_DE_DICT.items() for n in nums}

# -----------------------------------------------------------------------------
# 2. HÀM XỬ LÝ DỮ LIỆU
# -----------------------------------------------------------------------------

@st.cache_data(ttl=60)
def fetch_lottery_data():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(API_URL, headers=headers, timeout=10).json()
        return res.get('t', {}).get('issueList', [])
    except: return None

def parse_detail_to_107_chars(detail_str):
    try:
        return "".join([g.replace(",", "").strip() for g in json.loads(detail_str)]) if detail_str else ""
    except: return ""

def create_position_map():
    mapping = []
    for p, c, l in XSMB_STRUCTURE:
        for i in range(1, c+1):
            for j in range(1, l+1): mapping.append(f"{p}.{i}.{j}")
    return mapping

def get_set_name(n): return NUMBER_TO_SET_MAP.get(str(n), "?")

def process_days_data(raw_list, num_days):
    processed_days = []
    pos_map = create_position_map()
    
    for i in range(min(num_days, len(raw_list))):
        record = raw_list[i]
        full = parse_detail_to_107_chars(record.get('detail', ''))
        if len(full) != 107: continue
        
        target_3cang = full[2:5] # Ví dụ 589 (Tâm càng=5, Đề=89)
        
        processed_days.append({
            "index": i,
            "issue": record.get('turnNum'),
            "tam_cang": target_3cang[0],     # Chữ số hàng trăm
            "de": target_3cang[1:],          # 2 số cuối
            "de_rev": target_3cang[1:][::-1],
            "de_set": get_set_name(target_3cang[1:]),
            "body": full[5:]
        })
    return processed_days, pos_map

# -----------------------------------------------------------------------------
# 3. THUẬT TOÁN TÌM CẦU (TÁCH BIỆT)
# -----------------------------------------------------------------------------

def find_tam_cang_positions(days_data):
    """Tìm 1 vị trí duy nhất chạy thông giải Tâm Càng (Hàng trăm)"""
    if not days_data: return []
    
    valid_indices = []
    body_len = len(days_data[0]['body'])
    
    for k in range(body_len):
        streak = True
        for day in days_data:
            # So sánh ký tự tại vị trí k với Tâm càng của ngày đó
            if day['body'][k] != day['tam_cang']:
                streak = False
                break
        if streak:
            valid_indices.append(k)
            
    return valid_indices

def find_de_pairs(days_data, mode="straight", allow_rev=False):
    """Tìm cặp vị trí chạy thông giải Đề"""
    if not days_data: return []
    
    day0 = days_data[0]
    body = day0['body']
    candidates = []
    
    # 1. Lọc ứng viên ngày đầu
    for i in range(len(body)):
        for j in range(len(body)):
            if i == j: continue
            val = body[i] + body[j]
            match = False
            
            if mode == "straight":
                if val == day0['de']: match = True
                elif allow_rev and val == day0['de_rev']: match = True
            else: # set
                if get_set_name(val) == day0['de_set']: match = True
            
            if match: candidates.append((i, j))
            
    # 2. Check streak
    finals = []
    for (i, j) in candidates:
        streak = True
        for k in range(1, len(days_data)):
            day = days_data[k]
            val = day['body'][i] + day['body'][j]
            
            if mode == "straight":
                if allow_rev:
                    if val != day['de'] and val != day['de_rev']: streak = False; break
                else:
                    if val != day['de']: streak = False; break
            else:
                if get_set_name(val) != day['de_set']: streak = False; break
        
        if streak: finals.append((i, j))
        
    return finals

# -----------------------------------------------------------------------------
# 4. GIAO DIỆN
# -----------------------------------------------------------------------------

def main():
    st.title("🎯 Soi Cầu: Tâm Càng + Cầu Đề = 3 Càng")
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Cấu Hình")
        days = st.slider("Số ngày chạy thông", 2, 5, 3)
        
        mode = st.radio("Chế độ soi Đề", ["Thẳng (Bạch thủ)", "Bộ Đề (Hệ)"])
        allow_rev = False
        if "Thẳng" in mode:
            allow_rev = st.checkbox("Chấp nhận Đề Đảo (AB-BA)", value=True)
            
        if st.button("🚀 QUÉT NGAY", type="primary"):
            st.session_state['scan'] = True

    # --- DATA ---
    raw = fetch_lottery_data()
    if not raw: st.error("Lỗi API"); return
    
    data, pmap = process_days_data(raw, days)
    if len(data) < days: st.warning("Thiếu dữ liệu"); return

    # --- HIỂN THỊ KQ ---
    st.subheader(f"📅 Kết quả {days} ngày qua")
    cols = st.columns(days)
    for i, d in enumerate(data):
        with cols[i]:
            st.markdown(f"**{d['issue']}**")
            st.code(f"3C: {d['tam_cang']}{d['de']}", language="text")
            st.caption(f"Càng: {d['tam_cang']} | Đề: {d['de']}")

    # --- QUÉT ---
    if st.session_state.get('scan'):
        st.divider()
        
        # 1. QUÉT TÂM CÀNG (HÀNG TRĂM)
        with st.spinner("Đang quét Tâm Càng..."):
            tc_indices = find_tam_cang_positions(data)
        
        # 2. QUÉT CẦU ĐỀ
        with st.spinner("Đang quét Cầu Đề..."):
            mode_key = "straight" if "Thẳng" in mode else "set"
            de_pairs = find_de_pairs(data, mode=mode_key, allow_rev=allow_rev)
        
        # --- HIỂN THỊ KẾT QUẢ TÁCH BIỆT ---
        
        # BẢNG 1: CẦU TÂM CÀNG
        st.subheader(f"🅰️ CẦU TÂM CÀNG ({len(tc_indices)} vị trí)")
        st.markdown("*Là các vị trí chạy thông đúng số hàng trăm của GĐB.*")
        
        if tc_indices:
            tc_data = []
            for idx in tc_indices:
                row = {"Vị trí": f"{pmap[idx]} (Idx {idx})"}
                for d in data: row[f"Ngày {d['issue']}"] = d['body'][idx]
                tc_data.append(row)
            st.dataframe(pd.DataFrame(tc_data), use_container_width=True)
        else:
            st.warning("Không tìm thấy cầu Tâm Càng nào chạy thông.")

        st.divider()

        # BẢNG 2: CẦU ĐỀ
        st.subheader(f"🅱️ CẦU ĐỀ ({len(de_pairs)} cặp)")
        st.markdown(f"*Là các cặp vị trí chạy thông giải Đề (Chế độ: {mode}).*")
        
        if de_pairs:
            de_data = []
            for (i, j) in de_pairs:
                row = {"Vị trí 1": pmap[i], "Vị trí 2": pmap[j]}
                for d in data:
                    val = d['body'][i] + d['body'][j]
                    # Format hiển thị
                    display = val
                    if "Thẳng" in mode:
                        if val == d['de']: display += " (Thẳng)"
                        elif val == d['de_rev']: display += " (Đảo)"
                    else:
                        display += f" (Bộ {d['de_set']})"
                    row[f"Ngày {d['issue']}"] = display
                de_data.append(row)
            st.dataframe(pd.DataFrame(de_data), use_container_width=True)
        else:
            st.warning("Không tìm thấy cầu Đề nào chạy thông.")
            
        # TỔNG HỢP
        if tc_indices and de_pairs:
            st.success(f"💡 MẸO: Hãy ghép bất kỳ vị trí ở Bảng A với cặp ở Bảng B để tạo thành dàn 3 Càng siêu chuẩn!")
            
            with st.expander("Xem ví dụ ghép 3 Càng"):
                # Lấy ví dụ 1 cái càng + 1 cầu đề đầu tiên
                k = tc_indices[0]
                i, j = de_pairs[0]
                st.markdown(f"**Ví dụ ghép:**")
                st.markdown(f"- Càng: `{pmap[k]}`")
                st.markdown(f"- Đề: `{pmap[i]}` + `{pmap[j]}`")
                st.markdown("---")
                for d in data:
                    cang = d['body'][k]
                    de = d['body'][i] + d['body'][j]
                    st.text(f"Ngày {d['issue']}: {cang} (Càng) + {de} (Đề) -> 3 Càng về {d['tam_cang']}{d['de']}")

if __name__ == "__main__":
    main()
