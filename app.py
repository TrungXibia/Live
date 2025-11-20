import streamlit as st
import requests
import pandas as pd
import json

# -----------------------------------------------------------------------------
# CẤU HÌNH TRANG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Soi Cầu VIP: Tâm Càng & Đề",
    page_icon="🎯",
    layout="wide"
)

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div[data-testid="stExpander"] {border: 1px solid #e6e6e6; border-radius: 5px;}
    /* Tùy chỉnh nút bấm to đẹp hơn */
    div.stButton > button {
        width: 100%;
        height: 3em;
        font-weight: bold;
        font-size: 16px;
    }
    /* Canh chỉnh tiêu đề cột */
    .css-1q8dd3e {padding-top: 2rem;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH & DỮ LIỆU (GIỮ NGUYÊN)
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
        
        target_3cang = full[2:5] 
        
        processed_days.append({
            "index": i,
            "issue": record.get('turnNum'),
            "tam_cang": target_3cang[0],
            "de": target_3cang[1:],
            "de_rev": target_3cang[1:][::-1],
            "de_set": get_set_name(target_3cang[1:]),
            "body": full[5:]
        })
    return processed_days, pos_map

# -----------------------------------------------------------------------------
# 3. THUẬT TOÁN TÌM CẦU
# -----------------------------------------------------------------------------
def find_tam_cang_positions(days_data):
    if not days_data: return []
    valid_indices = []
    body_len = len(days_data[0]['body'])
    for k in range(body_len):
        streak = True
        for day in days_data:
            if day['body'][k] != day['tam_cang']:
                streak = False; break
        if streak: valid_indices.append(k)
    return valid_indices

def find_de_pairs(days_data, mode="straight", allow_rev=False):
    if not days_data: return []
    day0 = days_data[0]
    body = day0['body']
    candidates = []
    
    for i in range(len(body)):
        for j in range(len(body)):
            if i == j: continue
            val = body[i] + body[j]
            match = False
            if mode == "straight":
                if val == day0['de']: match = True
                elif allow_rev and val == day0['de_rev']: match = True
            else:
                if get_set_name(val) == day0['de_set']: match = True
            if match: candidates.append((i, j))
            
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
# 4. GIAO DIỆN (ĐÃ CHUYỂN MENU LÊN TRÊN)
# -----------------------------------------------------------------------------

def main():
    st.title("🎯 Soi Cầu VIP: Tâm Càng & Đề")
    
    # --- MENU CẤU HÌNH TRÊN CÙNG (4 CỘT) ---
    with st.container():
        c1, c2, c3, c4 = st.columns([1.5, 2, 1.5, 1.5])
        
        with c1:
            days = st.slider("Ngày thông", 2, 5, 3, help="Số ngày cầu chạy liên tiếp")
            
        with c2:
            # Dùng radio horizontal hoặc selectbox cho gọn
            mode = st.selectbox("Chế độ soi Đề", ["Thẳng (Bạch thủ)", "Bộ Đề (Hệ Bóng)"])
            
        with c3:
            allow_rev = False
            # Chỉ hiện checkbox đảo nếu chọn soi Thẳng
            if "Thẳng" in mode:
                st.write("") # Spacer cho thẳng hàng
                allow_rev = st.checkbox("Đảo (AB-BA)", value=True)
            else:
                st.write("")
                st.caption("Soi bộ tự động đảo")
                
        with c4:
            st.write("") # Spacer để nút bấm căn giữa với input
            # Nút bấm chính
            btn_scan = st.button("🚀 QUÉT NGAY", type="primary")

    st.divider()

    # --- XỬ LÝ DỮ LIỆU ---
    raw = fetch_lottery_data()
    if not raw: 
        st.error("Không lấy được dữ liệu từ Server."); return
    
    data, pmap = process_days_data(raw, days)
    if len(data) < days: 
        st.warning("Dữ liệu chưa đủ số ngày yêu cầu."); return

    # --- HIỂN THỊ LỊCH SỬ KẾT QUẢ ---
    st.subheader(f"📅 Dữ liệu đầu vào ({days} ngày)")
    cols = st.columns(days)
    for i, d in enumerate(data):
        with cols[i]:
            st.info(f"**{d['issue']}**")
            st.markdown(f"3 Càng: **{d['tam_cang']}{d['de']}**")
            st.caption(f"Càng: {d['tam_cang']} | Đề: {d['de']}")

    # --- LOGIC QUÉT (KHI BẤM NÚT) ---
    if btn_scan:
        st.write("---")
        
        # 1. QUÉT TÂM CÀNG
        tc_indices = find_tam_cang_positions(data)
        
        # 2. QUÉT CẦU ĐỀ
        mode_key = "straight" if "Thẳng" in mode else "set"
        de_pairs = find_de_pairs(data, mode=mode_key, allow_rev=allow_rev)
        
        # --- HIỂN THỊ KẾT QUẢ ---
        
        col_kq1, col_kq2 = st.columns(2)
        
        with col_kq1:
            st.success(f"🅰️ CẦU TÂM CÀNG ({len(tc_indices)} vị trí)")
            if tc_indices:
                tc_data = []
                for idx in tc_indices:
                    row = {"Vị trí": f"{pmap[idx]}", "Index": idx}
                    # Chỉ hiện giá trị ngày mới nhất cho gọn
                    row[f"Giá trị hôm nay ({data[0]['issue']})"] = data[0]['body'][idx]
                    tc_data.append(row)
                st.dataframe(pd.DataFrame(tc_data), use_container_width=True, hide_index=True)
            else:
                st.warning("Không có cầu Càng nào thông.")

        with col_kq2:
            st.success(f"🅱️ CẦU ĐỀ ({len(de_pairs)} cặp)")
            if de_pairs:
                de_data = []
                for (i, j) in de_pairs:
                    val_hom_nay = data[0]['body'][i] + data[0]['body'][j]
                    display = val_hom_nay
                    if "Thẳng" in mode:
                        if val_hom_nay == data[0]['de']: display += " (Thẳng)"
                        elif val_hom_nay == data[0]['de_rev']: display += " (Đảo)"
                    else:
                        display += f" (Bộ {data[0]['de_set']})"
                        
                    de_data.append({
                        "Vị trí 1": pmap[i],
                        "Vị trí 2": pmap[j],
                        f"Giá trị hôm nay": display
                    })
                st.dataframe(pd.DataFrame(de_data), use_container_width=True, hide_index=True)
            else:
                st.warning("Không có cầu Đề nào thông.")

        # --- PHẦN GHÉP 3 CÀNG (NẰM DƯỚI CÙNG) ---
        if tc_indices and de_pairs:
            st.divider()
            st.header("💎 GỢI Ý GHÉP 3 CÀNG (MỚI NHẤT)")
            
            # Lấy tối đa 5 vị trí càng đầu tiên và 5 cặp đề đầu tiên để demo
            demo_cang = tc_indices[:5]
            demo_de = de_pairs[:10]
            
            st.markdown("Dưới đây là các tổ hợp **3 Càng** được tạo ra từ các cầu trên cho ngày tiếp theo (dựa trên dữ liệu hôm nay):")
            
            # Tạo ma trận ghép
            matrix_data = []
            
            # Lấy body ngày mới nhất để dự đoán tương lai (thực tế là soi cầu cho ngày mai dựa trên vị trí cũ)
            # Tuy nhiên ở đây ta hiển thị kết quả của Kỳ Mới Nhất để chứng minh cầu đúng.
            d_new = data[0] 
            
            for idx_cang in demo_cang:
                val_cang = d_new['body'][idx_cang]
                row_str = []
                for (i, j) in demo_de:
                    val_de = d_new['body'][i] + d_new['body'][j]
                    # Nếu đảo
                    res_3c = f"{val_cang}{val_de}"
                    row_str.append(res_3c)
                
                matrix_data.append({
                    "Càng": f"{pmap[idx_cang]} ({val_cang})",
                    "Ghép với các cặp Đề bên trên ->": " | ".join(row_str)
                })
            
            st.table(pd.DataFrame(matrix_data))

if __name__ == "__main__":
    main()
