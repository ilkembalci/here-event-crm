import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import os

st.set_page_config(page_title="Here Event OS", page_icon="🏢")

# --- HATA AYIKLAMA (DEBUG) MODU ---
def get_db():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        # Streamlit Secrets'tan anahtarı al
        if "gcp_json" in st.secrets:
            # Anahtarı yükle
            key_dict = json.loads(st.secrets["gcp_json"])
            
            # --- KRİTİK DÜZELTME: Private Key'deki \n sorunu ---
            # Bazen kopyalarken \n karakterleri bozulur, onları düzeltiyoruz.
            if "\\n" in key_dict["private_key"]:
                 key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        else:
            st.error("🚨 HATA: 'gcp_json' anahtarı Streamlit Secrets içinde bulunamadı!")
            return None

        client = gspread.authorize(creds)
        
        # Dosyayı açmayı dene
        return client.open("Here Event CRM")
        
    except Exception as e:
        # İŞTE BURASI HATAYI EKRANA BASACAK
        st.error(f"🔥 BAĞLANTI HATASI DETAYI: {e}")
        st.code(f"Hata Türü: {type(e).__name__}")
        return None

# --- GİRİŞ EKRANI ---
st.title("Sistem Kontrolü")

db = get_db()

if db:
    st.success("✅ Google Bağlantısı BAŞARILI!")
    try:
        users = db.worksheet("Kullanicilar").get_all_records()
        st.write("Kullanıcı Listesi Erişimi: OK")
        st.write(users) # Kullanıcıları ekrana basar (Test için)
    except Exception as e:
        st.error(f"Tablo Okuma Hatası: {e}")
        st.info("Lütfen Google Sheet'te 'Kullanicilar' adında bir sayfa olduğundan emin ol.")
else:
    st.warning("Yukarıdaki kırmızı hatayı oku ve Gemini'ye söyle.")
