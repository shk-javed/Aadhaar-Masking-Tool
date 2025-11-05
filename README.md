# 🪪 Aadhaar Masking Tool

**Privacy-preserving OCR app** that automatically detects and masks Aadhaar numbers in images and PDFs using OCR + image processing.  
Built with **Python**, **Django**, **Tesseract OCR / PaddleOCR** (optional), and **OpenCV**.

---

## 🔥 Demo
> Add a short GIF or screenshot here (recommended). Example markdown:

(Place `assets/demo.gif` in repo or link to an external image)

---

## ✨ Features
- 🔎 Automatic Aadhaar number detection using OCR (Tesseract / PaddleOCR)  
- 🧾 Supports multiple file types: JPG, PNG, PDF  
- 🔐 Masks the first 8 digits and keeps last 4 visible (configurable)  
- 🖼️ Handles tilted, low-quality, vernacular, and screenshot Aadhaar formats (improved by PaddleOCR)  
- 🌐 Simple Django web UI for uploading files and downloading masked output  
- 🛠️ Regex-based validation to reduce false positives

---

## 🧰 Tech Stack
- Language: **Python 3**
- Web: **Django**
- OCR: **Tesseract OCR** (or **PaddleOCR** for better multi-language/screenshot support)
- Image processing: **OpenCV**
- Others: `numpy`, `pytesseract` (or `paddleocr`), `Pillow`, etc.

---

## 🚀 Quick Start (local)
> Mac / Linux steps (Windows similar — adapt venv activation)

1. Clone repository
```bash
git clone https://github.com/shk-javed/Aadhaar-Masking-Tool.git
cd Aadhaar-Masking-Tool
