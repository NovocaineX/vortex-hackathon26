import os
import firebase_admin
from firebase_admin import credentials, firestore, storage
from dotenv import load_dotenv

load_dotenv()

FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-adminsdk.json")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")

def init_firebase():
    if not firebase_admin._apps:
        try:
            if os.path.exists(FIREBASE_CREDENTIALS_PATH):
                cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
            else:
                print("[Firebase] Certificate file not found, defaulting...")
                cred = credentials.ApplicationDefault()
            
            opts = {}
            if FIREBASE_STORAGE_BUCKET:
                opts['storageBucket'] = FIREBASE_STORAGE_BUCKET
                
            firebase_admin.initialize_app(cred, opts)
            print("[Firebase] Admin SDK initialized.")
        except Exception as e:
            print(f"[Firebase ERROR] Failed to initialize: {e}")

init_firebase()

try:
    db = firestore.client()
    bucket = storage.bucket() if FIREBASE_STORAGE_BUCKET else storage.bucket("PLACEHOLDER")
except Exception as e:
    db = None
    bucket = None
    print(f"[Firebase ERROR] Missing db/bucket bind: {e}")
