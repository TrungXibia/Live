import streamlit as st
import requests
import pandas as pd
import json

# -----------------------------------------------------------------------------
# CẤU HÌNH TRANG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Soi Cầu Pro: 3 Càng - Nhị Hợp - Đề",
    page_icon="🔥",
    layout="wide"
)

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div[data-testid="stExpander"] {border: 1px solid #e6e6e6; border-radius: 5px;}
    div.stButton > button {width: 100%; height: 3em; font-weight: bold;}
    .streak-badge {
        background-color: #28a745; color: white; padding: 2px 8px; 
        border-radius: 10px; font-weight: bold; font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH & DỮ LIỆU
# -----------------------------------------------------------------------------
API_URL = "https://www.kqxs88.live/api/front/open/lottery/history/list/game?limitNum=20&gameCode=miba" 
# Tăng limit lên 20 để tính streak dài hơn

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

def get_prize_groups():
    """Tạo map gom nhóm index theo từng giải (Ví dụ: G3.1 gồm các index [30,31,32,33,34])"""
    groups = {}
    current_idx = 0
    for p, c, l in XSMB_STRUCTURE:
        for i in range(1, c+1):
            prize_name = f"{p}.{i}" # VD: G1.1, G3.6
            indices = list(range(current_idx, current_idx + l))
            groups[prize_name] = indices
            current_idx += l
    return groups

def get_set_name(n): return NUMBER_TO_SET_MAP.get(str(n), "?")

def process_days_data(raw_list):
    processed_days = []
    
    for i in range(len(raw_list)):
        record = raw_list[i]
        full = parse_detail_to_107_chars(record.get('detail', ''))
        if len(full) != 107: continue
        
        target_3cang = full[2:5]
        de = target_3cang[1:]
        
        processed_days.append({
            "index": i,
            "issue": record.get('turnNum'),
            "tam_cang": target_3cang[0],
            "de": de,
            "de_rev": de[::-1],
            "de_set": get_set_name(de),
            "body": full[5:]
        })
    return processed_days

# -----------------------------------------------------------------------------
# 3. THUẬT TOÁN TÌM CẦU
# -----------------------------------------------------------------------------

def calculate_max_streak(days_data, idx1, idx2, mode, allow_rev):
    """Tính xem cặp (idx1, idx2) chạy thông bao nhiêu ngày từ ngày 0 về quá khứ"""
    streak = 0
    # Ngày 0 chắc chắn đúng rồi mới gọi hàm này, nên bắt đầu check từ ngày 1
    # Nhưng logic ở main loop đã check ngày 0. Ở đây ta đếm từ 0.
    
    for k in range(len(days_data)):
        day = days_data[k]
        val = day['body'][idx1] + day['body'][idx2]
        
        match = False
        if mode == "straight":
            if val == day['de']: match = True
            elif allow_rev and val == day['de_rev']: match = True
        else: # set
            if get_set_name(val) == day['de_set']: match = True
            
        if match:
            streak += 1
        else:
            break # Gãy cầu
            
    return streak

def find_nhi_hop_bridges(days_data, mode="straight", allow_rev=False):
    """
    Tìm cầu Nhị Hợp: Chỉ ghép các số trong CÙNG 1 GIẢI.
    Sắp xếp theo Streak giảm dần.
    """
    if not days_data: return []
    
    day0 = days_data[0]
    body0 = day0['body']
    prize_groups = get_prize_groups()
    
    results = []
    
    # Duyệt qua từng giải (G1.1, G2.1, ...)
    for prize_name, indices in prize_groups.items():
        # Duyệt các cặp index TRONG nội bộ giải đó
        for i in indices:
            for j in indices:
                if i == j: continue # Không ghép chính nó (nhưng có thể ghép 2 số giống nhau ở vị trí khác nhau)
                
                val = body0[i] + body0[j]
                
                # Check ngày 0
                match = False
                if mode == "straight":
                    if val == day0['de']: match = True
                    elif allow_rev and val == day0['de_rev']: match = True
                else:
                    if get_set_name(val) == day0['de_set']: match = True
                
                if match:
                    # Nếu ngày 0 đúng, tính tiếp Streak quá khứ
                    streak = calculate_max_streak(days_data, i, j, mode, allow_rev)
                    if streak >= 2: # Chỉ lấy cầu chạy từ 2 ngày trở lên
                        results.append({
                            "prize": prize_name,
                            "idx1": i,
                            "idx2": j,
                            "streak": streak,
                            "val_today": val
                        })
    
    # Sắp xếp kết quả: Streak cao nhất lên đầu
    results.sort(key=lambda x: x['streak'], reverse=True)
    return results

def find_de_pairs_global(days_data, mode="straight", allow_rev=False, min_days=3):
    """Tìm cầu Đề toàn cục (cũ)"""
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
        streak = calculate_max_streak(days_data, i, j, mode, allow_rev)
        if streak >= min_days:
            finals.append({"idx1": i, "idx2": j, "streak": streak})
            
    finals.sort(key=lambda x: x['streak'], reverse=True)
    return finals

def find_tam_cang(days_data):
    if not days_data: return []
    valid = []
    for k in range(len(days_data[0]['body'])):
        streak = 0
        for day in days_data:
            if day['body'][k] == day['tam_cang']: streak += 1
            else: break
        if streak >= 2:
            valid.append({"idx": k, "streak": streak})
    valid.sort(key=lambda x: x['streak'], reverse=True)
    return valid

# -----------------------------------------------------------------------------
# 4. GIAO DIỆN
# -----------------------------------------------------------------------------

def main():
    st.title("🔥 Soi Cầu Pro: Nhị Hợp & Dàn Đề")
    
    # --- MENU CẤU HÌNH ---
    with st.container():
        c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 1.5])
        with c1:
            scan_mode = st.selectbox("🎯 Chế độ Soi", [
                "Nhị Hợp (Nội bộ giải)", 
                "Cầu Đề (Ghép toàn bộ)", 
                "Tâm Càng (3 Càng)"
            ])
        with c2:
            min_streak = st.number_input("Min Streak (Ngày)", min_value=2, value=3, step=1)
        with c3:
            # Tùy chọn Đề
            allow_rev = True
            de_mode = "straight"
            if "Tâm Càng" not in scan_mode:
                is_set = st.checkbox("Soi theo Bộ", value=False)
                de_mode = "set" if is_set else "straight"
                if not is_set:
                    allow_rev = st.checkbox("Đảo (AB-BA)", value=True)
        with c4:
            st.write("")
            btn_scan = st.button("🚀 QUÉT", type="primary")

    st.divider()

    # --- DATA ---
    raw = fetch_lottery_data()
    if not raw: st.error("Lỗi API"); return
    
    # Xử lý toàn bộ dữ liệu (để tính streak)
    all_days = process_days_data(raw)
    pos_map = create_position_map()

    # Hiển thị KQ 5 ngày gần nhất
    st.subheader("📅 Kết quả gần đây")
    cols = st.columns(5)
    for i in range(min(5, len(all_days))):
        d = all_days[i]
        with cols[i]:
            st.info(f"{d['issue']}")
            st.markdown(f"Đề: **{d['de']}**")
            st.caption(f"Bộ: {d['de_set']}")

    # --- LOGIC QUÉT ---
    if btn_scan:
        st.write("---")
        
        # 1. CHẾ ĐỘ NHỊ HỢP
        if "Nhị Hợp" in scan_mode:
            with st.spinner("Đang quét từng giải..."):
                results = find_nhi_hop_bridges(all_days, mode=de_mode, allow_rev=allow_rev)
                
            # Lọc theo min streak user chọn
            filtered = [r for r in results if r['streak'] >= min_streak]
            
            st.subheader(f"🔍 KẾT QUẢ NHỊ HỢP ({len(filtered)} cầu)")
            st.markdown("Các cầu dưới đây lấy 2 số trong **cùng 1 giải** ghép lại thành Đề.")
            
            if filtered:
                df_data = []
                for item in filtered:
                    p_name = item['prize']
                    # Tính vị trí tương đối trong giải (VD: G3.1.1 và G3.1.5)
                    # map idx -> tên đầy đủ
                    pos1 = pos_map[item['idx1']] # G3.1.1
                    pos2 = pos_map[item['idx2']] # G3.1.5
                    
                    # Chỉ lấy phần đuôi index (1 và 5)
                    local_idx1 = pos1.split(".")[-1]
                    local_idx2 = pos2.split(".")[-1]
                    
                    row = {
                        "Giải": p_name,
                        "Vị trí ghép": f"Số thứ {local_idx1} & {local_idx2}",
                        "Streak (Ngày)": f"{item['streak']} 🔥",
                        "Giá trị hôm nay": item['val_today']
                    }
                    df_data.append(row)
                
                st.dataframe(pd.DataFrame(df_data), use_container_width=True)
            else:
                st.warning(f"Không tìm thấy cầu Nhị hợp nào chạy thông >= {min_streak} ngày.")

        # 2. CHẾ ĐỘ CẦU ĐỀ TOÀN CỤC
        elif "Cầu Đề" in scan_mode:
            with st.spinner("Đang quét toàn bộ 10.000 cặp..."):
                results = find_de_pairs_global(all_days, mode=de_mode, allow_rev=allow_rev, min_days=min_streak)
            
            st.subheader(f"🌐 CẦU ĐỀ TOÀN CỤC ({len(results)} cầu)")
            if results:
                df_data = []
                for item in results[:50]: # Show top 50 cầu đẹp nhất
                    val = all_days[0]['body'][item['idx1']] + all_days[0]['body'][item['idx2']]
                    df_data.append({
                        "Vị trí 1": pos_map[item['idx1']],
                        "Vị trí 2": pos_map[item['idx2']],
                        "Streak": f"{item['streak']} ngày",
                        "Báo số": val
                    })
                st.dataframe(pd.DataFrame(df_data), use_container_width=True)
                if len(results) > 50: st.caption("... và nhiều cầu khác (chỉ hiển thị Top 50)")
            else:
                st.warning("Không tìm thấy cầu nào.")

        # 3. CHẾ ĐỘ TÂM CÀNG
        elif "Tâm Càng" in scan_mode:
            results = find_tam_cang(all_days)
            filtered = [r for r in results if r['streak'] >= min_streak]
            
            st.subheader(f"🎯 CẦU TÂM CÀNG ({len(filtered)} vị trí)")
            if filtered:
                df_data = []
                for item in filtered:
                    df_data.append({
                        "Vị trí": pos_map[item['idx']],
                        "Streak": f"{item['streak']} ngày",
                        "Báo Càng": all_days[0]['body'][item['idx']]
                    })
                st.dataframe(pd.DataFrame(df_data), use_container_width=True)
            else:
                st.warning("Không tìm thấy cầu Càng nào.")

if __name__ == "__main__":
    main()
