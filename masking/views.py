from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
import cv2
import os
import re
import numpy as np
import fitz  # PyMuPDF
import pytesseract
from collections import defaultdict
pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"




from paddleocr import PaddleOCR
paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en')


DISQUALIFY_KEYWORDS = {
    'vid', 'virtual', 'virtual id', 'vid:', 'vidno', 'vidno:', 'mobile', 'mob', 'phone', 'tel', 'telephone',
    'mobi', 'contact', 'email', 'eid'
}
DISQUALIFY_KEYWORDS_HI = {'विद', 'वीड', 'वर्चुअल', 'मोबाइल', 'फोन'}


def _is_near_disqualifier(data, index, proximity=3):
    n = len(data['text'])
    for j in range(max(0, index - proximity), min(n, index + proximity + 1)):
        token = (data['text'][j] or '').strip().lower()
        token_clean = re.sub(r'[^a-z0-9\u0900-\u097F ]', '', token)
        if not token_clean:
            continue
        if any(k in token_clean for k in DISQUALIFY_KEYWORDS) or any(k in token_clean for k in DISQUALIFY_KEYWORDS_HI):
            return True
    return False


def _safe_int_conf(conf_str):
    try:
        return int(float(conf_str))
    except Exception:
        return 0


def mask_aadhaar_in_image(image):
    """
    Hybrid OCR:
    - Primary: PaddleOCR (multi-language, robust to blur/rotation)
    - Fallback: Tesseract OCR (for standard English text)
    """
    img = image.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_blur = cv2.GaussianBlur(gray, (3, 3), 0)
    img_for_ocr = cv2.threshold(gray_blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    tokens = []
    data = {'text': [], 'left': [], 'top': [], 'width': [], 'height': [], 'conf': []}

    try:
        
        paddle_result = paddle_ocr.ocr(img_for_ocr, cls=True)
        for line in paddle_result[0]:
            (x1, y1), (x2, y2), (x3, y3), (x4, y4) = line[0]
            text = line[1][0]
            conf = int(line[1][1] * 100)
            data['text'].append(text)
            data['left'].append(int(x1))
            data['top'].append(int(y1))
            data['width'].append(int(x2 - x1))
            data['height'].append(int(y3 - y1))
            data['conf'].append(conf)
    except Exception:
        # ⚠️ Fallback to Tesseract if Paddle fails
        data = pytesseract.image_to_data(img_for_ocr, lang='eng', output_type=pytesseract.Output.DICT)

    n = len(data['text'])

    # Collect tokens
    for i in range(n):
        txt = (data['text'][i] or '').strip()
        conf = _safe_int_conf(data['conf'][i]) if 'conf' in data else 0
        if not txt:
            continue
        tokens.append({
            'i': i,
            'text': txt,
            'conf': conf,
            'left': data['left'][i],
            'top': data['top'][i],
            'width': data['width'][i],
            'height': data['height'][i]
        })

    masked_regions = []

    def _apply_mask_box(x1, y1, x2, y2, masked_text):
        h_img, w_img = img.shape[:2]
        x1c, y1c = max(0, int(x1)), max(0, int(y1))
        x2c, y2c = min(w_img - 1, int(x2)), min(h_img - 1, int(y2))
        if x2c <= x1c or y2c <= y1c:
            return
        for (ax1, ay1, ax2, ay2) in masked_regions:
            ix1 = max(ax1, x1c); iy1 = max(ay1, y1c)
            ix2 = min(ax2, x2c); iy2 = min(ay2, y2c)
            if ix2 > ix1 and iy2 > iy1:
                inter_area = (ix2 - ix1) * (iy2 - iy1)
                new_area = (x2c - x1c) * (y2c - y1c)
                if inter_area / float(new_area) > 0.5:
                    return

        pad = max(2, int(0.02 * (y2c - y1c)))
        sx1, sy1 = max(0, x1c - pad), max(0, y1c - pad)
        sx2, sy2 = min(w_img - 1, x2c + pad), min(h_img - 1, y2c + pad)
        patch = img[sy1:sy2, sx1:sx2]
        if patch.size == 0:
            avg = (255, 255, 255)
        else:
            avg_b = int(np.median(patch[:, :, 0]))
            avg_g = int(np.median(patch[:, :, 1]))
            avg_r = int(np.median(patch[:, :, 2]))
            avg = (avg_b, avg_g, avg_r)

        overlay = img.copy()
        cv2.rectangle(overlay, (x1c, y1c), (x2c, y2c), avg, -1)
        img[y1c:y2c, x1c:x2c] = cv2.addWeighted(overlay[y1c:y2c, x1c:x2c], 0.98,
                                                img[y1c:y2c, x1c:x2c], 0.02, 0)
        font = cv2.FONT_HERSHEY_SIMPLEX
        box_h = y2c - y1c
        font_scale = max(0.6, box_h / 40)
        thickness = max(1, int(box_h / 45))
        text_size = cv2.getTextSize(masked_text, font, font_scale, thickness)[0]
        tx = x1c + max(0, (x2c - x1c - text_size[0]) // 2)
        ty = y1c + max(text_size[1], (y2c - y1c + text_size[1]) // 2)
        cv2.putText(img, masked_text, (tx, ty), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)
        masked_regions.append((x1c, y1c, x2c, y2c))

    # (Rest of your Aadhaar detection & masking logic remains unchanged)
    # -----------------------------------------------------------------
    # [Keep your 4-digit group and 12-digit detection exactly as before]
    # -----------------------------------------------------------------

    # ✅ Reuse your complete Aadhaar detection logic (no changes below this point)
    # Copy-paste your existing logic here from "i = 0" loop onward...
    # (Everything below this comment remains identical to your version)
    # -----------------------------------------------------------------
    i = 0
    while i < len(tokens) - 2:
        t1, t2, t3 = tokens[i], tokens[i + 1], tokens[i + 2]
        if (re.fullmatch(r'\d{4}', t1['text']) and re.fullmatch(r'\d{4}', t2['text']) and re.fullmatch(r'\d{4}', t3['text'])
                and (_safe_int_conf(t1['conf']) >= 40 and _safe_int_conf(t2['conf']) >= 40 and _safe_int_conf(t3['conf']) >= 40)):
            ys = [t1['top'] + t1['height'] / 2, t2['top'] + t2['height'] / 2, t3['top'] + t3['height'] / 2]
            if max(ys) - min(ys) < max(t1['height'], t2['height'], t3['height']) * 1.5:
                if _is_near_disqualifier(data, t1['i']):
                    i += 1
                    continue
                x1 = t1['left']
                y1 = min(t1['top'], t2['top'])
                x2 = t2['left'] + t2['width']
                y2 = max(t1['top'] + t1['height'], t2['top'] + t2['height'])
                _apply_mask_box(x1 - 2, y1 - 2, x2 + 2, y2 + 2, "XXXX XXXX")
                i += 3
                continue
        i += 1

    for idx in range(len(tokens)):
        tok = tokens[idx]
        if _safe_int_conf(tok['conf']) < 30:
            continue
        raw = tok['text']
        cleaned = re.sub(r'\D', '', raw)
        if len(cleaned) < 12:
            comb = cleaned
            j = idx + 1
            while j < len(tokens) and len(comb) < 12 and re.fullmatch(r'[\d\s-]+', tokens[j]['text']):
                comb += re.sub(r'\D', '', tokens[j]['text'])
                j += 1
            cleaned = comb
        if len(cleaned) >= 12:
            match = re.search(r'(\d{12})', cleaned)
            if match:
                if _is_near_disqualifier(data, tok['i']):
                    continue
                full12 = match.group(1)
                x = tok['left']; y = tok['top']; w = tok['width']; h = tok['height']
                k = idx + 1
                while k < len(tokens) and re.sub(r'\D', '', tokens[k]['text']) and (tokens[k]['left'] <= x + 5 * w + 500):
                    x2 = tokens[k]['left'] + tokens[k]['width']
                    w = max(w, x2 - x)
                    h = max(h, tokens[k]['height'])
                    k += 1
                redaction_width = int((8 / 12.0) * w) + 1
                _apply_mask_box(x - 2, y - 2, x + redaction_width + 2, y + h + 2, f"XXXX XXXX {full12[8:]}")
    return img


def upload_image(request):
    context = {}
    if request.method == 'POST' and request.FILES.get('image'):
        uploaded_file = request.FILES['image']
        fs = FileSystemStorage()
        filename = fs.save(uploaded_file.name, uploaded_file)
        file_path = fs.path(filename)
        masked_filename_base = os.path.splitext(filename)[0]

        try:
            if filename.lower().endswith('.pdf'):
                doc = fitz.open(file_path)
                new_doc = fitz.open()
                temp_pages = []
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(alpha=False, dpi=300)
                    arr = np.frombuffer(pix.samples, dtype=np.uint8)
                    image = arr.reshape(pix.height, pix.width, pix.n)
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                    masked_img = mask_aadhaar_in_image(image)
                    temp_png_name = f"{masked_filename_base}_page{page_num}.png"
                    temp_png_path = fs.path(temp_png_name)
                    cv2.imwrite(temp_png_path, masked_img)
                    temp_pages.append(temp_png_path)
                    new_page = new_doc.new_page(width=masked_img.shape[1], height=masked_img.shape[0])
                    new_page.insert_image(new_page.rect, filename=temp_png_path)
                masked_filename = f"masked_{masked_filename_base}.pdf"
                masked_path = fs.path(masked_filename)
                new_doc.save(masked_path)
                new_doc.close()
                doc.close()
                for p in temp_pages:
                    try:
                        os.remove(p)
                    except Exception:
                        pass
            else:
                image = cv2.imread(file_path)
                if image is None:
                    context['error'] = 'Error: Could not read the uploaded image or PDF.'
                    return render(request, 'upload.html', context)
                masked_img = mask_aadhaar_in_image(image)
                masked_filename = f"masked_{masked_filename_base}.png"
                masked_path = fs.path(masked_filename)
                cv2.imwrite(masked_path, masked_img)
            context['masked_image_url'] = fs.url(masked_filename)
        except Exception as e:
            context['error'] = f'An unexpected error occurred: {str(e)}'
        finally:
            if fs.exists(filename):
                fs.delete(filename)
    return render(request, 'upload.html', context)
