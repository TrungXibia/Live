import easyocr
import numpy as np
from PIL import Image
import cv2

# Khởi tạo Reader 1 lần để dùng chung (cache vào Ram)
# Chỉ đọc số (allowlist) để tăng tốc và độ chính xác
reader = easyocr.Reader(['en'], gpu=False) 

def extract_numbers_from_image(image_file):
    """
    Đọc ảnh, trả về chuỗi 107 ký tự chuẩn XSMB.
    Input: File ảnh upload từ Streamlit.
    Output: (full_str_107, list_of_numbers_found)
    """
    try:
        # 1. Chuyển ảnh upload thành format OpenCV
        image = Image.open(image_file)
        image_np = np.array(image)
        
        # 2. Xử lý ảnh (Grayscale) để OCR tốt hơn
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        
        # 3. Đọc text (Chỉ chấp nhận số)
        # allowlist='0123456789' giúp loại bỏ chữ cái rác
        results = reader.readtext(gray, allowlist='0123456789', detail=0)
        
        # 4. Lọc rác: Chỉ lấy các số có độ dài hợp lệ (2 đến 5 chữ số)
        # XSMB có các giải: 5 số, 4 số, 3 số, 2 số.
        clean_nums = []
        for text in results:
            text = text.strip()
            # Loại bỏ các số quá ngắn (ví dụ số thứ tự 1, 2, 3...) hoặc quá dài
            if text.isdigit() and 2 <= len(text) <= 5:
                clean_nums.append(text)
        
        # 5. Sắp xếp và ghép vào cấu trúc XSMB
        # Tổng cộng XSMB có 27 giải.
        # Thứ tự đọc của EasyOCR thường là từ Trái qua Phải, Trên xuống Dưới.
        # Bảng KQXS thường xếp: GĐB -> G1 -> G2 ... -> G7
        
        # Nếu đọc thiếu hoặc thừa, ta trả về list để user sửa tay
        return clean_nums

    except Exception as e:
        return [f"Error: {str(e)}"]

def map_numbers_to_107_str(numbers_list):
    """
    Ghép danh sách số thô thành chuỗi 107 ký tự.
    Cần đúng 27 số theo thứ tự: 1 ĐB, 1 G1, 2 G2, 6 G3, 4 G4, 6 G5, 3 G6, 4 G7
    """
    # Cấu trúc số lượng giải
    structure = [1, 1, 2, 6, 4, 6, 3, 4] # Tổng 27 giải
    lengths   = [5, 5, 5, 5, 4, 4, 3, 2] # Độ dài từng giải
    
    full_str = ""
    current_idx = 0
    
    # Nếu không đủ 27 số, điền ? vào chỗ thiếu
    # Nếu thừa, cắt bớt
    
    for count, length in zip(structure, lengths):
        for _ in range(count):
            if current_idx < len(numbers_list):
                val = numbers_list[current_idx]
                # Kiểm tra độ dài, nếu sai thì fill ? (hoặc giữ nguyên nếu user chấp nhận rủi ro)
                if len(val) == length:
                    full_str += val
                else:
                    # Cố gắng fix: nếu dài hơn thì cắt, ngắn hơn thì pad ?
                    # Nhưng an toàn nhất là ghép vào, thuật toán soi cầu sẽ tự xử lý
                    if len(val) > length: full_str += val[-length:] # Lấy đuôi
                    else: full_str += val.rjust(length, '?') 
            else:
                full_str += "?" * length
            current_idx += 1
            
    return full_str
