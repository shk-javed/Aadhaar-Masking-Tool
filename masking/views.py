from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.clickjacking import xframe_options_exempt
from django.urls import reverse

import os
import cv2
import numpy as np
import fitz  # PyMuPDF

from .utils.ocr_utils import mask_aadhaar_image

# Ensure media root exists
os.makedirs(settings.MEDIA_ROOT, exist_ok=True)


def _pixmap_to_bgr(pix):
    """Convert PyMuPDF pixmap to BGR numpy image"""
    arr = np.frombuffer(pix.samples, dtype=np.uint8)
    if pix.n == 4:
        img = arr.reshape(pix.height, pix.width, 4)
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
    elif pix.n == 3:
        img = arr.reshape(pix.height, pix.width, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    elif pix.n == 1:
        img = arr.reshape(pix.height, pix.width)
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    else:
        img = arr.reshape(pix.height, pix.width, pix.n)[:, :, :3]
        if img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    return img


def upload_image(request):
    context = {}
    if request.method == 'POST' and request.FILES.get('image'):
        uploaded_file = request.FILES['image']
        fs = FileSystemStorage(location=settings.MEDIA_ROOT)
        filename = fs.save(uploaded_file.name, uploaded_file)
        file_path = fs.path(filename)
        masked_filename = None

        try:
            # ---------- PDF FLOW ----------
            if filename.lower().endswith('.pdf'):
                doc = fitz.open(file_path)
                temp_paths = []

                # 1) Har page ko image bana kar mask karo
                for pnum in range(len(doc)):
                    page = doc.load_page(pnum)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    img = _pixmap_to_bgr(pix)

                    masked = mask_aadhaar_image(img)

                    tmp_name = f"tmp_masked_{os.path.splitext(filename)[0]}_p{pnum}.png"
                    tmp_path = os.path.join(settings.MEDIA_ROOT, tmp_name)
                    cv2.imwrite(tmp_path, masked)
                    temp_paths.append(tmp_path)

                # 2) Masked PNGs se naya PDF banao
                new_doc = fitz.open()
                for mp in temp_paths:
                    page_img = fitz.Pixmap(mp)
                    page = new_doc.new_page(width=page_img.width, height=page_img.height)
                    page.insert_image(page.rect, filename=mp)

                masked_filename = f"masked_{os.path.splitext(filename)[0]}.pdf"
                masked_path = fs.path(masked_filename)
                new_doc.save(masked_path)
                new_doc.close()
                doc.close()

                # 3) Preview ke liye IMAGE create karo (sirf first page)
                if temp_paths:
                    first_png = temp_paths[0]
                    preview_name = f"preview_{os.path.splitext(filename)[0]}.png"
                    preview_path = os.path.join(settings.MEDIA_ROOT, preview_name)

                    img_preview = cv2.imread(first_png)
                    if img_preview is not None:
                        cv2.imwrite(preview_path, img_preview)
                        context['masked_pdf_image_preview'] = fs.url(preview_name)

                # 4) Temp PNGs cleanup
                for p in temp_paths:
                    try:
                        os.remove(p)
                    except Exception:
                        pass

                # 5) Download link
                context['masked_pdf_url'] = fs.url(masked_filename)

            # ---------- IMAGE FLOW ----------
            else:
                image = cv2.imdecode(
                    np.fromfile(file_path, dtype=np.uint8),
                    cv2.IMREAD_COLOR
                )
                if image is None:
                    image = cv2.imread(file_path)

                if image is None:
                    context['error'] = 'Could not read uploaded file as image.'
                    if fs.exists(filename):
                        fs.delete(filename)
                    return render(request, 'upload.html', context)

                masked_img = mask_aadhaar_image(image)
                masked_filename = f"masked_{os.path.splitext(filename)[0]}.png"
                masked_path = fs.path(masked_filename)
                cv2.imwrite(masked_path, masked_img)

                context['masked_image_url'] = fs.url(masked_filename)

            return render(request, 'upload.html', context)

        except Exception as e:
            context['error'] = f"An unexpected error occurred: {str(e)}"
            return render(request, 'upload.html', context)

        finally:
            try:
                if fs.exists(filename):
                    fs.delete(filename)
            except Exception:
                pass

    return render(request, 'upload.html', context)


# Optional: agar kisi jagah future me PDF ko direct <embed> se dikhana ho
@xframe_options_exempt
def preview_pdf(request, filename):
    pdf_path = os.path.join(settings.MEDIA_ROOT, filename)
    if not os.path.exists(pdf_path):
        raise Http404("PDF not found")

    return FileResponse(
        open(pdf_path, 'rb'),
        content_type='application/pdf',
        headers={
            "X-Content-Type-Options": "nosniff",
            "Access-Control-Allow-Origin": "*",
        }
    )
