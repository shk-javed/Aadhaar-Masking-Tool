# 🪪 Aadhaar Masking Tool  

![Python](https://img.shields.io/badge/Python-3.9-blue)
![Django](https://img.shields.io/badge/Django-Framework-green)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-orange)
![PaddleOCR](https://img.shields.io/badge/OCR-PaddleOCR-lightblue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow)

**Privacy-preserving OCR app** that automatically detects and masks Aadhaar numbers in images and PDFs using OCR + image processing.  
Built with **Python**, **Django**, **Tesseract OCR / PaddleOCR**, and **OpenCV**.  

---

## 📸 Demo (Before vs After Masking)
| Original Aadhaar | Masked Output |
|------------------|---------------|
| ![Original](assets/original_aadhaar.png) | ![Masked](assets/masked_aadhaar.png) |

> *Automatically masks first 8 digits from Aadhaar number while preserving visual quality.*

---

## ✨ Features
- 🔍 Automatic Aadhaar number detection using OCR (Tesseract / PaddleOCR)  
- 🧾 Supports multiple file types: JPG, PNG, PDF  
- 🔐 Masks the first 8 digits and keeps last 4 visible (configurable)  
- 🖼️ Handles tilted, low-quality, vernacular, and screenshot Aadhaar formats  
- 🌐 Simple Django web UI for uploading files and downloading masked output  
- 🛠️ Regex-based validation to reduce false positives  

---

## 🧰 Tech Stack
| Category | Technology |
|-----------|-------------|
| 💻 Language | Python 3 |
| 🌐 Framework | Django |
| 🔍 OCR Engine | Tesseract / PaddleOCR |
| 🎨 Image Processing | OpenCV |
| 🧮 Libraries | NumPy, Pillow, Regex, Matplotlib |
| ☁️ Deployment | Render / Hugging Face (optional) |

---

## 🚀 Quick Start (Local)
> Mac / Linux steps shown (Windows similar — adjust venv activation)

### 1️⃣ Clone the repository  
```bash
git clone https://github.com/shk-javed/Aadhaar-Masking-Tool.git
cd Aadhaar-Masking-Tool

### 2️⃣ Create & activate virtual environment  
```bash
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

python manage.py migrate
python manage.py runserver

👉 http://127.0.0.1:8000