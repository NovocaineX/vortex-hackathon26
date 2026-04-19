from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
from firebase_config import FIREBASE_API_KEY
from firebase_admin import auth

router = APIRouter(prefix="/auth")

class AuthRequest(BaseModel):
    email: str
    password: str

from utils.security import get_current_user
from fastapi import Depends
from firebase_config import db
from datetime import datetime, timezone

@router.post("/register")
def register_user(req: AuthRequest):
    if not FIREBASE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing FIREBASE_API_KEY in server configuration")
    
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {
        "email": req.email,
        "password": req.password,
        "returnSecureToken": True
    }
    
    r = requests.post(url, json=payload)
    data = r.json()
    if 'error' in data:
        raise HTTPException(status_code=400, detail=data['error']['message'])
    
    uid = data.get("localId")
    email = data.get("email")
    if db:
        db.collection("users").document(uid).set({
            "uid": uid,
            "email": email,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    return {
        "uid": uid,
        "email": email,
        "idToken": data.get("idToken"),
        "refreshToken": data.get("refreshToken"),
        "expiresIn": data.get("expiresIn")
    }

@router.post("/login")
def login_user(req: AuthRequest):
    if not FIREBASE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing FIREBASE_API_KEY in server configuration")
    
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": req.email,
        "password": req.password,
        "returnSecureToken": True
    }
    
    r = requests.post(url, json=payload)
    data = r.json()
    if 'error' in data:
        raise HTTPException(status_code=400, detail=data['error']['message'])
        
    return {
        "uid": data.get("localId"),
        "email": data.get("email"),
        "idToken": data.get("idToken"),
        "refreshToken": data.get("refreshToken"),
    }

@router.get("/me")
def get_user_me(user_info = Depends(get_current_user)):
    return {
        "uid": user_info.get("uid"),
        "email": user_info.get("email"),
        "created_at": user_info.get("auth_time")
    }
