# Forensica AI

### Explainable AI Platform for Document Forgery Detection

Forensica AI is an AI-assisted forensic document analysis platform designed to detect forged, manipulated, or suspicious documents using explainable analysis techniques.
The system analyzes uploaded files and highlights anomalies such as font inconsistencies, pixel cloning, layout irregularities, and compression artifacts while generating a structured forensic report.

This project was built for **ThinkRoot x Vortex ’26 Hackathon – Track C**.

---

## Problem Statement

Digital documents such as certificates, IDs, transcripts, invoices, and official records are frequently forged or manipulated using image editing tools.
Manual forensic verification is time-consuming and requires expert knowledge.

There is a need for an **automated system that can assist investigators and institutions in verifying document authenticity quickly and transparently.**

---

## Solution

Forensica AI provides an automated pipeline that:

1. Accepts uploaded documents (PDF, JPG, PNG).
2. Extracts text and visual patterns from the document.
3. Runs multiple forensic analysis modules.
4. Detects suspicious anomalies.
5. Highlights manipulated regions visually.
6. Generates a structured forensic report with explanations.

The platform focuses on **explainability**, allowing investigators to understand **why a document was flagged as suspicious** rather than just receiving a score.

---

## Key Features

* AI-assisted document authenticity verification
* OCR-based text extraction
* Pixel anomaly detection
* Font inconsistency detection
* Layout integrity analysis
* Compression artifact detection
* Explainable anomaly visualization
* Structured forensic report generation
* Secure per-user document history

---

## Detection Pipeline

The system performs analysis using a modular forensic pipeline:

1. **Document Upload**
   User uploads a document for analysis.

2. **Pre-processing**
   Image normalization and preparation.

3. **OCR Extraction**
   Text extracted using Tesseract OCR.

4. **Forensic Analysis Modules**

   * Pixel anomaly detection
   * Font inconsistency detection
   * Layout irregularity detection
   * Compression artifact analysis

5. **Explainability Engine**
   Highlights suspicious regions and provides reasoning.

6. **Report Generation**
   Produces a downloadable verification report.

---

## System Architecture

Frontend
HTML, CSS, JavaScript dashboard interface.

Backend
Python FastAPI backend handling analysis pipeline.

Detection Engine
OpenCV image analysis + OCR processing.

Database & Authentication
Firebase Authentication and Firestore for secure per-user document storage.

Storage
Firebase Storage for encrypted user document storage.

Deployment
Application can run locally for development.
Cloud deployment can be configured using Docker and Netlify integration.

---

## Tech Stack

Frontend

* HTML
* CSS
* JavaScript

Backend

* Python
* FastAPI

AI / Image Processing

* OpenCV
* Tesseract OCR
* NumPy

Infrastructure

* Firebase Authentication
* Firebase Firestore
* Firebase Storage
* Docker
* Netlify

---

## Repository Structure

```
backend/
    models/
    services/
    routes/
    utils/

frontend/
    css/
    js/


```

---

## Running Locally

Clone the repository:

```
git clone https://github.com/NovocaineX/vortex-hackathon26.git
```

Install dependencies:

```
pip install -r requirements.txt
```

Run the backend server:

```
python backend/main.py
```

Open the frontend in a browser and upload a document to start analysis.

---

## Security & Privacy

* Documents are stored securely per user.
* Uploaded files are isolated and encrypted.
* User authentication prevents cross-user access to analysis history.

---

## Future Improvements

* Deep learning based forgery detection models
* Blockchain-based document authenticity verification
* Institutional verification integrations
* Large-scale batch document analysis
* Multilingual OCR support

---

## Demo

Demo video and screenshots are available in the `demo/` directory.

---

## Authors

Developed by **Aadarsh (NovocaineX)** for the ThinkRoot x Vortex ’26 Hackathon.
