# Forensica AI

Explainable AI Platform for Detecting Forged or Manipulated Documents

Forensica AI is a cybersecurity-focused forensic analysis platform that detects potential document tampering using a modular AI-assisted pipeline. The system analyzes uploaded documents through multiple forensic stages including OCR extraction, anomaly detection, layout analysis, font verification, and metadata inspection to determine authenticity.

This project was developed for ThinkRoot x Vortex ’26 Hackathon — Track C.

------------------------------------------------------------

PROBLEM

Digital documents such as certificates, transcripts, invoices, and identity records are frequently manipulated using image editing software. Traditional verification methods rely on manual inspection which is slow, error-prone, and requires specialized expertise.

There is a need for a scalable automated system that assists investigators, institutions, and organizations in detecting document forgery quickly while providing explainable evidence.

------------------------------------------------------------

SOLUTION

Forensica AI provides a modular forensic analysis pipeline capable of automatically analyzing documents and highlighting suspicious regions.

The system:

• Extracts text using OCR  
• Detects visual manipulation artifacts  
• Identifies font inconsistencies  
• Evaluates layout structure  
• Analyzes metadata  
• Aggregates risk signals into an interpretable forensic score  
• Generates a structured verification report  

The goal is not just detection but explainable forensic insights, allowing investigators to understand why a document is considered suspicious.

------------------------------------------------------------

KEY FEATURES

• Automated document forgery detection  
• Explainable anomaly detection  
• OCR-based text extraction  
• Pixel anomaly and cloning detection  
• Font inconsistency detection  
• Layout integrity analysis  
• Metadata forensics  
• Risk scoring engine  
• Secure per-user document history  
• Batch document analysis  

------------------------------------------------------------

SYSTEM ARCHITECTURE

Frontend Dashboard  
        ↓  
FastAPI Backend API  
        ↓  
Forensic Analysis Pipeline  
    • File Preprocessor  
    • OCR Extraction  
    • Pixel & Anomaly Detection  
    • Layout Consistency Check  
    • Font Detection  
    • Metadata Forensics  
    • Risk Scoring Engine  
        ↓  
Result Aggregation + Forensic Report

------------------------------------------------------------

FORENSIC ANALYSIS PIPELINE

1. File Preprocessing  
Image normalization, noise filtering, and format standardization.

2. OCR Extraction  
Text is extracted using Tesseract OCR and analyzed for structural inconsistencies.

3. Pixel Anomaly Detection  
Detects cloned regions, editing artifacts, and unnatural pixel patterns.

4. Layout Integrity Check  
Analyzes alignment, spacing, and structural layout inconsistencies.

5. Font Detection  
Detects mismatched fonts and typographic anomalies often introduced by edits.

6. Metadata Forensics  
Extracts embedded metadata and identifies suspicious editing timestamps.

7. Risk Scoring Engine  
All signals are aggregated to produce a forgery probability score.

------------------------------------------------------------

TECHNOLOGY STACK

Backend
• Python
• FastAPI
• OpenCV
• Tesseract OCR
• NumPy

Frontend
• HTML
• CSS
• JavaScript

Infrastructure
• Firebase Authentication
• Firebase Firestore
• Firebase Storage
• Docker
• Netlify

------------------------------------------------------------

STORAGE STRATEGY

Cloud Mode

Firebase is used for:

• User authentication  
• Secure document storage  
• Analysis result persistence  

Local Mode

For development and resource efficiency, the system can run locally with temporary storage and offline analysis.

------------------------------------------------------------

REPOSITORY STRUCTURE

backend/
    models/
    routes/
    services/
    utils/

frontend/
    css/
    js/


------------------------------------------------------------

RUNNING THE PROJECT LOCALLY

Clone the repository

git clone https://github.com/NovocaineX/vortex-hackathon26.git

Install dependencies

pip install -r requirements.txt

Run the backend server

python backend/main.py

Open the frontend in your browser and upload a document to start analysis.

------------------------------------------------------------

SECURITY AND PRIVACY

• Each user's uploads are isolated  
• Documents are encrypted in storage  
• Access control enforced through Firebase authentication  
• Analysis history is restricted per user  

------------------------------------------------------------

FUTURE IMPROVEMENTS

• Deep learning based forgery detection models  
• Blockchain-backed document verification  
• Institutional verification APIs  
• Multilingual OCR support  
• Large scale batch verification  

------------------------------------------------------------

DEMO

Demo video and screenshots are available in the demo directory.

------------------------------------------------------------

AUTHOR

Developed by Aadarsh (NovocaineX) for ThinkRoot x Vortex ’26 Hackathon.
