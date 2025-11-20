import easyocr
import numpy as np
from PIL import Image
import cv2

# Khởi tạo OCR (Chỉ chạy 1 lần)
reader = easyocr.Reader(['en'], gpu=False) 

def extract_numbers_from_image(image_file):
    """
    Xử lý ảnh chụp màn hình xổ số.
    Trả về danh sách các con số tìm thấy có khả năng là giải.
    """
    try:
        # 1. Load ảnh
        image = Image.open(image_file)
        img = np.array(image)
        
        # 2. Tiền xử lý ảnh (Tăng tương phản để đọc số đỏ/đen rõ hơn)
        # Chuyển xám
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        # Ngưỡng hóa (Threshold) để làm nổi bật chữ đen trên nền trắng
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 3. OCR (Chỉ đọc số)
        # detail=0 chỉ lấy text, paragraph=False để đọc từng cụm số riêng lẻ
        results = reader.readtext(gray, allowlist='0123456789', detail=0, paragraph=False)
        
        candidates = []
        
        # 4. Lọc rác thông minh
        for text in results:
            # Xóa khoảng trắng thừa
            clean_text = text.replace(" ", "").strip()
            
            # Chỉ lấy số
            if not clean_text.isdigit():
                continue
                
            length = len(clean_text)
            
            # QUY TẮC XSMB:
            # Giải ĐB, 1, 2, 3: 5 chữ số
            # Giải 4, 5: 4 chữ số
            # Giải 6: 3 chữ số
            # Giải 7: 2 chữ số
            # -> Chỉ chấp nhận số có độ dài 2, 3, 4, 5
            
            # Loại bỏ số năm (2025) nếu nó xuất hiện ở đầu/cuối (thường OCR đọc theo thứ tự)
            # Tuy nhiên khó phân biệt 2025 với giải 4. Nên cứ lấy hết, user sửa sau.
            
            if length in [2, 3, 4, 5]:
                candidates.append(clean_text)
                
        return candidates

    except Exception as e:
        return [f"Error: {str(e)}"]

def map_numbers_to_107_str(numbers_list):
    """
    Cố gắng nhét danh sách số vào đúng 27 giải của XSMB.
    Tổng cộng 27 số. 
    Thứ tự ưu tiên: Lấy 27 số ĐẦU TIÊN tìm thấy (vì ảnh thường chụp từ trên xuống).
    """
    # Cấu trúc số lượng giải XSMB
    # GĐB(1), G1(1), G2(2), G3(6), G4(4), G5(6), G6(3), G7(4) -> Tổng 27
    PRIZE_COUNTS = [1, 1, 2, 6, 4, 6, 3, 4]
    PRIZE_LENGTHS = [5, 5, 5, 5, 4, 4, 3, 2]
    
    full_str = ""
    current_idx = 0
    
    # Nếu danh sách đưa vào > 27 số (do dính ngày tháng, mã đb...), ta ưu tiên lấy những số đúng định dạng giải
    # Nhưng đơn giản nhất là lấy 27 số đầu tiên hợp lệ.
    
    for count, length in zip(PRIZE_COUNTS, PRIZE_LENGTHS):
        for _ in range(count):
            if current_idx < len(numbers_list):
                val = numbers_list[current_idx]
                
                # Kiểm tra độ dài có khớp giải không? 
                # (Ví dụ GĐB bắt buộc 5 số, G7 bắt buộc 2 số)
                # Nếu khớp -> Ghép. Nếu không khớp -> Vẫn ghép nhưng cảnh báo (hoặc user tự sửa)
                # Ở đây ta ghép luôn, thừa thiếu tính sau.
                
                if len(val) == length:
                    full_str += val
                elif len(val) > length: 
                    full_str += val[-length:] # Cắt đuôi
                else:
                    full_str += val.rjust(length, '?') # Điền ?
                    
            else:
                full_str += "?" * length
            current_idx += 1
            
    return full_str
