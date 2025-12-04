import os
import re
import cv2
import numpy as np
from paddleocr import PaddleOCR
import pytesseract
from collections import defaultdict
from math import atan2, degrees
from django.conf import settings

# Configure tesseract from settings if available
pytesseract.pytesseract.tesseract_cmd = getattr(settings, "TESSERACT_CMD", "/usr/bin/tesseract")

# Lazy PaddleOCR singleton
_paddle = None


def get_paddle():
    global _paddle
    if _paddle is None:
        lang = getattr(settings, "PADDLE_OCR_LANG", "en")
        _paddle = PaddleOCR(use_angle_cls=True, lang=lang)
    return _paddle


# Regex patterns
AADHAAR_PATTERNS = [
    re.compile(r'\b\d{4}\s\d{4}\s\d{4}\b'),  # 4 4 4 with spaces
    re.compile(r'\b\d{12}\b'),               # 12 digits together
    re.compile(r'\b\d{4}-\d{4}-\d{4}\b'),    # 4-4-4
]
VID_PATTERN = re.compile(r'\b(?:\d{4}\s\d{4}\s\d{4}\s\d{4}|\d{16})\b')
EID_PATTERN = re.compile(r'\b\d{1,4}/\d{1,5}/\d{1,5}\b')
PARTIAL4 = re.compile(r'\b\d{4}\b')

# Keywords that suggest the number is NOT Aadhaar (phone/email etc.)
DISQUALIFY_KEYWORDS = {
    'virtual', 'mobile', 'phone', 'tel', 'telephone', 'email',
    'contact', 'mob', 'eid', 'vid', 'virtual id'
}
DISQUALIFY_KEYWORDS_HI = {'मोबाइल', 'फोन', 'ईमेल', 'వర్చुअల'}


def normalize_text(s: str) -> str:
    if s is None:
        return ""
    return s.replace('\u200b', '').replace('\xa0', ' ').strip()


def digits_only(s: str) -> str:
    return ''.join(ch for ch in (s or "") if ch.isdigit())


def is_near_disqualifier(all_texts, idx, proximity=3):
    n = len(all_texts)
    for j in range(max(0, idx - proximity), min(n, idx + proximity + 1)):
        token = normalize_text(all_texts[j]).lower()
        token_clean = re.sub(r'[^a-z0-9\u0900-\u097F ]', '', token)
        if not token_clean:
            continue
        if any(k in token_clean for k in DISQUALIFY_KEYWORDS) or any(k in token_clean for k in DISQUALIFY_KEYWORDS_HI):
            return True
    return False


# ---------- Image Preprocessing ----------
def enhance_for_ocr(img):
    """Convert to RGB, apply CLAHE & slight denoise. Returns color image for OCR & gray for fallback."""
    # ensure BGR input
    if img is None:
        return None, None
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    img_rgb_clahe = cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)
    gray = cv2.cvtColor(img_rgb_clahe, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    return img_rgb_clahe, gray


def get_largest_quad_contour(edges):
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    conts = sorted(contours, key=cv2.contourArea, reverse=True)
    for cnt in conts:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and cv2.contourArea(approx) > 1000:
            return approx.reshape(4, 2)
    return None


def order_points(pts):
    # Order: tl, tr, br, bl
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def four_point_transform(image, pts):
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = max(int(widthA), int(widthB))
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = max(int(heightA), int(heightB))
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]
    ], dtype='float32')
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    return warped


def deskew_and_warp(img):
    """Attempt to detect doc and warp to frontal view. Return warped or original if detection fails."""
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)
        quad = get_largest_quad_contour(edges)
        if quad is not None:
            warped = four_point_transform(img, quad)
            return warped
    except Exception:
        pass
    return img


# ---------- OCR Helpers ----------
def paddle_ocr_read(img_rgb):
    """Call paddle and return normalized list of (box, text, conf)"""
    paddle = get_paddle()
    # PaddleOCR accepts numpy RGB, convert if needed
    result = paddle.ocr(img_rgb, cls=True)
    lines = []
    # result can be like [ [ [box], (text, conf) ], ... ] or [ [ [box], [ (text, conf) ... ] ] ] depending on version
    # Try to flatten robustly
    try:
        # If returned as list of lines
        for item in (result[0] if isinstance(result, list) and len(result) and isinstance(result[0], list) and len(result[0]) and isinstance(result[0][0], list) else result):
            # item expected shape: [box, (text, conf)] or [[box], [(text, conf)]]
            if not item:
                continue
            if isinstance(item[0][0], (list, tuple)):
                box = item[0][0]
                text = item[1][0] if isinstance(item[1], (list, tuple)) else item[1]
                conf = float(item[1][1]) if isinstance(item[1], (list, tuple)) else 1.0
            else:
                # fallback structure
                box = item[0]
                text = item[1][0] if isinstance(item[1], (list, tuple)) else str(item[1])
                conf = float(item[1][1]) if isinstance(item[1], (list, tuple)) else 1.0
            lines.append((box, normalize_text(text), int(conf * 100)))
    except Exception:
        # As a last resort, try to parse common structure
        try:
            for line in result:
                box = line[0]
                text = line[1][0]
                conf = float(line[1][1])
                lines.append((box, normalize_text(text), int(conf * 100)))
        except Exception:
            pass
    return lines


def pytesseract_read(gray_img):
    d = pytesseract.image_to_data(gray_img, lang='eng', output_type=pytesseract.Output.DICT)
    out = []
    n = len(d['text'])
    for i in range(n):
        txt = normalize_text(d['text'][i])
        if not txt:
            continue
        x = int(d['left'][i])
        y = int(d['top'][i])
        w = int(d['width'][i])
        h = int(d['height'][i])
        conf = int(float(d['conf'][i])) if d['conf'][i] != '-1' else 0
        box = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        out.append((box, txt, conf))
    return out


# ---------- Masking ----------
def expand_box(box, pad, img_shape):
    xs = [int(pt[0]) for pt in box]
    ys = [int(pt[1]) for pt in box]
    x1, x2 = max(0, min(xs) - pad), min(img_shape[1], max(xs) + pad)
    y1, y2 = max(0, min(ys) - pad), min(img_shape[0], max(ys) + pad)
    return x1, y1, x2, y2


def apply_mask(img, mask_rects, style='solid'):
    out = img.copy()
    mask_canvas = np.zeros(img.shape[:2], dtype=np.uint8)
    for (x1, y1, x2, y2) in mask_rects:
        cv2.rectangle(mask_canvas, (x1, y1), (x2, y2), 255, -1)

    # # Dilate to cover scribbles
    # h, w = img.shape[:2]
    # kernel_size = max(15, int(min(h, w) * 0.01))
    # kernel = np.ones((kernel_size, kernel_size), np.uint8)
    # mask_canvas = cv2.dilate(mask_canvas, kernel, iterations=1)

    if style == 'solid':
        # Fill with median color in each region (to blend)
        contours, _ = cv2.findContours(mask_canvas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            x, y, ww, hh = cv2.boundingRect(c)
            patch = img[y:y + hh, x:x + ww]
            if patch.size == 0:
                color = (255, 255, 255)
            else:
                m_b = int(np.median(patch[:, :, 0]))
                m_g = int(np.median(patch[:, :, 1]))
                m_r = int(np.median(patch[:, :, 2]))
                color = (m_b, m_g, m_r)
            out[y:y + hh, x:x + ww] = color
    elif style == 'blur':
        blurred = cv2.GaussianBlur(out, (51, 51), 0)
        out[mask_canvas == 255] = blurred[mask_canvas == 255]
    elif style == 'pixelate':
        contours, _ = cv2.findContours(mask_canvas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            x, y, ww, hh = cv2.boundingRect(c)
            roi = out[y:y + hh, x:x + ww]
            if roi.size == 0:
                continue
            # pixelate by resizing small then resizing back
            small = cv2.resize(roi, (max(1, ww // 10), max(1, hh // 10)), interpolation=cv2.INTER_LINEAR)
            pixel = cv2.resize(small, (ww, hh), interpolation=cv2.INTER_NEAREST)
            out[y:y + hh, x:x + ww] = pixel
    else:
        # default to solid
        return apply_mask(img, mask_rects, style='solid')

    return out


def last4_from_digits(digits: str) -> str:
    digits = digits or ""
    return digits[-4:] if len(digits) >= 4 else "XXXX"

def draw_mask_label(img, rect, last4: str):
    """
    Rect ke center me 'XXXX XXXX' likhega (white text).
    Last 4 digits original image se hi dikhengi.
    """
    x1, y1, x2, y2 = rect

    text = "XXXX XXXX"   # Aadhaar-style masking (8 digits only)

    font = cv2.FONT_HERSHEY_SIMPLEX
    box_h = max(y2 - y1, 1)

    font_scale = max(box_h / 40.0, 0.6)
    thickness = max(int(box_h / 60), 1)

    (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)

    text_x = x1 + (x2 - x1 - text_w) // 2
    text_y = y1 + (y2 - y1 + text_h) // 2

    cv2.putText(
        img,
        text,
        (text_x, text_y),
        font,
        font_scale,
        (0, 0, 0),
        thickness,
        cv2.LINE_AA,
    )


def mask_aadhaar_image(image):
    """
    Full pipeline:
    - deskew/warp
    - enhance
    - paddleocr -> tokens
    - fallback to pytesseract if paddle empty
    - pattern matching + duplicate masking
    - apply mask according to settings
    - overlay 'XXXX XXXX 1234' on masked region
    """
    # 1) Deskew / warp
    # warped = deskew_and_warp(image)
    # ⚠️ SKIP WARPING: It causes "white dot" / tiny crop issues if contours are wrong.
    # We want the FULL original image with masks.
    warped = image.copy()

    # 2) Enhance
    img_for_paddle, gray = enhance_for_ocr(warped)

    # 3) OCR read
    lines = []
    try:
        lines = paddle_ocr_read(img_for_paddle)
    except Exception:
        lines = []

    if not lines:
        # fallback
        try:
            lines = pytesseract_read(gray)
        except Exception:
            lines = []

    # Build tokens
    tokens = []
    all_texts = []
    for (box, text, conf) in lines:
        norm = normalize_text(text)
        all_texts.append(norm)
    for idx, (box, text, conf) in enumerate(lines):
        norm = normalize_text(text)
        digits = digits_only(norm)
        xs = [int(pt[0]) for pt in box]
        ys = [int(pt[1]) for pt in box]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        tokens.append({
            'i': idx,
            'text': norm,
            'digits': digits,
            'conf': int(conf) if conf is not None else 0,
            'box': (x1, y1, x2, y2)
        })

    # 4) Robust masking logic + labels
    mask_regions = []  # each: {'rect': (x1,y1,x2,y2), 'last4': '1234'}

    # ---- Pass 1: 12-digit tokens (single token Aadhaar) ----
    for t in tokens:
        d = t['digits']

        # Agar ye number 'VID', 'mobile', 'phone', etc ke aas-paas hai to skip
        if is_near_disqualifier(all_texts, t['i']):
            continue

        if len(d) == 12:
            x1, y1, x2, y2 = t['box']
            width = x2 - x1
            mask_width = int(width * (8 / 12.0))  # first 8 digits

            mx1 = x1
            mx2 = x1 + mask_width
            pad = 2

            rect = expand_box([(mx1, y1), (mx2, y1), (mx2, y2), (mx1, y2)], pad, image.shape)
            mask_regions.append({
                'rect': rect,
                'last4': last4_from_digits(d)
            })

    # ---- Pass 2: 4-4-4 grouped tokens ----
    four_digit_tokens = [t for t in tokens if len(t['digits']) == 4]
    four_digit_tokens.sort(key=lambda x: (x['box'][1], x['box'][0]))

    used_indices = set()

    for i in range(len(four_digit_tokens)):
        if i in used_indices:
            continue

        t1 = four_digit_tokens[i]

        # Agar first 4-digit block 'VID' / mobile / phone ke aas-paas hai to
        # ye group Aadhaar nahi hai → skip
        if is_near_disqualifier(all_texts, t1['i']):
            continue

        t1_x1, t1_y1, t1_x2, t1_y2 = t1['box']
        t1_y_center = (t1_y1 + t1_y2) / 2
        t1_height = t1_y2 - t1_y1

        best_t2 = None
        best_t2_idx = -1

        # find middle block
        for j in range(i + 1, len(four_digit_tokens)):
            if j in used_indices:
                continue

            t2 = four_digit_tokens[j]
            t2_x1, t2_y1, t2_x2, t2_y2 = t2['box']
            t2_y_center = (t2_y1 + t2_y2) / 2
            t2_height = t2_y2 - t2_y1

            if abs(t1_y_center - t2_y_center) > max(t1_height, t2_height) * 0.5:
                continue

            gap = t2_x1 - t1_x2
            if 0 < gap < max(t1_height, t2_height) * 3.0:
                best_t2 = t2
                best_t2_idx = j
                break

        if best_t2:
            best_t3 = None
            best_t3_idx = -1

            for k in range(best_t2_idx + 1, len(four_digit_tokens)):
                if k in used_indices:
                    continue

                t3 = four_digit_tokens[k]
                t3_x1, t3_y1, t3_x2, t3_y2 = t3['box']
                t3_y_center = (t3_y1 + t3_y2) / 2
                t3_height = t3_y2 - t3_y1

                if abs(t1_y_center - t3_y_center) > max(t1_height, t3_height) * 0.5:
                    continue

                gap = t3_x1 - best_t2['box'][2]
                if 0 < gap < max(t1_height, t3_height) * 3.0:
                    best_t3 = t3
                    best_t3_idx = k
                    break

            if best_t3:
                # Combined 12 digits
                digits12 = (t1['digits'] or "") + (best_t2['digits'] or "") + (best_t3['digits'] or "")
                last4 = last4_from_digits(digits12)

                # Rect that covers first 8 digits = union of t1 + t2
                t2_x1, t2_y1, t2_x2, t2_y2 = best_t2['box']
                x1 = min(t1_x1, t2_x1)
                y1 = min(t1_y1, t2_y1)
                x2 = max(t1_x2, t2_x2)
                y2 = max(t1_y2, t2_y2)

                pad = 2
                rect = expand_box([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], pad, image.shape)

                mask_regions.append({
                    'rect': rect,
                    'last4': last4
                })

                used_indices.add(i)
                used_indices.add(best_t2_idx)
                used_indices.add(best_t3_idx)

    # ---- Fallback: agar abhi tak koi Aadhaar mask region nahi mila ----
    # Kuch cards me 12 digits ek hi token me aa jate hain but pattern logic miss kar deta hai.
    # Yaha hum un tokens ko pakadte hain jinke digits 11–13 ke beech hain
    # (12 approximate), aur jinke aas-paas mobile / phone / VID jaisa text nahi hai.
    if not mask_regions:
        best_candidate = None
        for t in tokens:
            d = t['digits'] or ""
            # Aadhaar 12-digit hota hai; 11–13 ko tolerate karte hain (OCR mistakes ke liye)
            if 11 <= len(d) <= 13:
                # nearby words me 'mobile', 'phone', 'email', 'VID' etc na ho
                if is_near_disqualifier(all_texts, t['i']):
                    continue
                best_candidate = t
                break

        if best_candidate is not None:
            d = best_candidate['digits'] or ""
            x1, y1, x2, y2 = best_candidate['box']
            width = x2 - x1

            # Sirf first 8 digits ka fraction – approx 8 / len(d)
            frac = 8.0 / max(len(d), 8)   # min 8 to avoid >1
            mask_width = int(width * frac)

            mx1 = x1
            mx2 = x1 + mask_width
            pad = 2

            rect = expand_box(
                [(mx1, y1), (mx2, y1), (mx2, y2), (mx1, y2)],
                pad,
                image.shape
            )
            mask_regions.append({
                'rect': rect,
                'last4': last4_from_digits(d)
            })

    # Rectangles sirf Aadhaar ke liye
    rects = [m['rect'] for m in mask_regions]

    # Pehle visual mask (blank region) – sirf first 8 digits area cover hoga
    mask_style = getattr(settings, "MASK_STYLE", "solid")
    out_img = apply_mask(warped, rects, style=mask_style)

    # Ab masked region ke upar 'XXXX XXXX' likho
    for m in mask_regions:
        draw_mask_label(out_img, m['rect'], m['last4'])

    return out_img
