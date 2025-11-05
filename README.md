# 🪪 Aadhaar Masking Tool  
> A privacy-preserving AI tool that automatically detects and masks Aadhaar numbers from documents using **TesseractOCR**, **OpenCV**, and **Django**.

---

## ✨ Overview
This project aims to protect user privacy by automatically **detecting and masking Aadhaar numbers** from uploaded images or PDFs.  
It uses Optical Character Recognition (OCR) to locate Aadhaar numbers and then applies intelligent masking to hide the first 8 digits — ensuring that sensitive data remains secure.

---

## 🎯 Features
- 🔍 **Automatic Aadhaar Detection** using OCR (TesseractOCR)
- 🧠 **Regex-based filtering** to detect valid Aadhaar patterns
- 🖼️ **Masking of digits** using OpenCV rectangle overlays
- 📄 **Supports multiple file types** (JPG, PNG, PDF)
- 🌐 **Web Interface** built with Django for easy uploads
- 🏗️ Handles **tilted, low-quality, and multilingual Aadhaar cards**

---

## 🧠 Tech Stack
| Category | Technologies Used |
|-----------|------------------|
| 💻 Programming Language | Python |
| 🧩 Framework | Django |
| 🔍 OCR Engine | TesseractOCR |
| 🎨 Image Processing | OpenCV |
| 🧮 Libraries | NumPy, re, Matplotlib |
| ☁️ Deployment | Render / Hugging Face (optional) |

---

## ⚙️ Installation and Setup
Follow these steps to run the project locally 👇  

### 1️⃣ Clone the repository
```bash
git clone https://github.com/shk-javed/Aadhaar-Masking-Tool.git
cd Aadhaar-Masking-Tool
