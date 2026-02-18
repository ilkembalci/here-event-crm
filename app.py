import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import plotly.express as px
from fpdf import FPDF
import base64
import json

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Here Event OS", page_icon="🏢", layout="wide")

# Türkçe karakter haritası (PDF için)
TR_MAP = str.maketrans("ğĞıİşŞçÇöÖüÜ", "gGiIsScCoOuU")

st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; font-family: 'Segoe UI', sans-serif; }
    div[data-testid="stMetric"] {
        background-color: white; padding: 15px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; border-left: 5px solid #0071e3;
    }
    .stButton>button { border-radius: 8px; font-weight: 600; width: 100%; transition: 0.2s; }
</style>
""", unsafe_allow_html=True)

# --- EMAIL AYARLARI ---
# GÜVENLİK İÇİN: Gerçek şifrenizi buraya yazarken dikkatli olun
EMAIL_ADDRESS = "sirketmailin@gmail.com"  
EMAIL_PASSWORD = "xxxx xxxx xxxx xxxx" 

def send_email_notification(to_email, subject, body):
    try:
        if not EMAIL_ADDRESS or "sirketmailin" in EMAIL_ADDRESS: return False
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        server.quit()
        return True
    except: return False

# --- VERİTABANI BAĞLANTISI (BULUT & YEREL UYUMLU) ---
def get_db():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        # 1. YÖNTEM: Streamlit Cloud (Secrets)
        if "gcp_json" in st.secrets:
            key_dict = json.loads(st.secrets["gcp_json"])
            # Newline karakterlerini düzelt (En önemli kısım)
            if "\\n" in key_dict["private_key"]:
                key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
            
        # 2. YÖNTEM: Bilgisayarım (Localhost)
        elif os.path.exists("credentials.json"):
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
            
        else:
            st.error("🚨 Kimlik doğrulama anahtarı bulunamadı!")
            return None

        client = gspread.authorize(creds)
        return client.open("Here Event CRM")
        
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None

# --- PDF MOTORU ---
def create_advanced_pdf(firma, yetkili, kalemler_listesi):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 20)
            self.cell(0, 10, 'HERE EVENT', 0, 1, 'C')
            self.line(10, 25, 200, 25)
            self.ln(10)
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Karakter düzeltmesi
    if firma: firma = firma.translate(TR_MAP)
    if yetkili: yetkili = yetkili.translate(TR_MAP)
    
    pdf.cell(0, 10, f"Tarih: {datetime.now().strftime('%d-%m-%Y')}", 0, 1, 'R')
    pdf.cell(0, 10, f"Sayin {firma} Yetkilisi,", 0, 1)
    pdf.ln(5)
    
    toplam = 0
    pdf.cell(100, 10, "Hizmet", 1, 0)
    pdf.cell(30, 10, "Miktar", 1, 0)
    pdf.cell(50, 10, "Tutar", 1, 1)
    
    for k in kalemler_listesi:
        tutar = k['miktar'] * k['fiyat']
        toplam += tutar
        ad = k['ad'].translate(TR_MAP)
        pdf.cell(100, 10, ad[:40], 1, 0)
        pdf.cell(30, 10, str(k['miktar']), 1, 0)
        pdf.cell(50, 10, f"{tutar:,.0f} TL", 1, 1)
        
    pdf.ln(5)
    pdf.cell(0, 10, f"GENEL TOPLAM: {toplam:,.0f} TL", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- MODÜL: SATIŞ (ORTAK) ---
def module_sales_shared():
    st.subheader("💼 Satış & Teklif Robotu")
    db = get_db()
    if not db: return
    
    try:
        sheet = db.worksheet("Satis")
        df = pd.DataFrame(sheet.get_all_records())
    except:
        st.error("'Satis' sekmesi bulunamadı.")
        return

    t1, t2, t3 = st.tabs(["➕ Ekle", "📋 Liste", "🛒 Teklif Sepeti"])
    
    with t1:
        with st.form("satis"):
            c1,c2 = st.columns(2)
            f = c1.text_input("Firma"); y = c1.text_input("Yetkili"); tel = c1.text_input("Tel")
            h = c2.selectbox("Hizmet", ["Uçak", "Otel", "MICE", "Transfer"]); d = c2.selectbox("Durum", ["Fırsat", "Kazanıldı"])
            if st.form_submit_button("Kaydet"):
                sheet.append_row([str(datetime.now().date()), f, y, tel, h, d, ""])
                st.success("OK"); st.rerun()

    with t2:
        if not df.empty: st.dataframe(df, use_container_width=True)

    with t3:
        if 'sepet' not in st.session_state: st.session_state['sepet'] = []
        c_fir, _ = st.columns(2)
        sel_fir = c_fir.selectbox("Firma Seç", df["Firma Adı"].unique() if not df.empty else [])
        
        c1, c2, c3, c4 = st.columns([3,1,1,1])
        ad = c1.text_input("Ürün Adı")
        mik = c2.number_input("Adet", 1); fiy = c3.number_input("Birim Fiyat", 0)
        if c4.button("Ekle"): 
            st.session_state['sepet'].append({"ad": ad, "miktar": mik, "fiyat": fiy})
            st.rerun()
            
        if st.session_state['sepet']:
            sdf = pd.DataFrame(st.session_state['sepet'])
            st.dataframe(sdf)
            if st.button("PDF İNDİR"):
                pdf_bytes = create_advanced_pdf(sel_fir, "Yetkili", st.session_state['sepet'])
                b64 = base64.b64encode(pdf_bytes).decode()
                st.markdown(f'<a href="data:application/pdf;base64,{b64}" download="Teklif.pdf">📥 PDF İNDİR</a>', unsafe_allow_html=True)
            if st.button("Temizle"): st.session_state['sepet'] = []; st.rerun()

# --- YÖNETİCİ ONAY SİSTEMİ ---
def render_admin_approval(sheet_name, title, data_cols, status_col_idx, note_col_idx):
    st.markdown(f"##### {title}")
    db = get_db()
    if not db: return
    
    try:
        sheet = db.worksheet(sheet_name)
        df = pd.DataFrame(sheet.get_all_records())
        
        if not df.empty:
            bekleyen = df[df["Durum"] == "Bekliyor"]
            if bekleyen.empty: st.success("Bekleyen yok.")
            else:
                for i, row in bekleyen.iterrows():
                    with st.expander(f"📌 {row[data_cols[0]]} - {row[data_cols[1]]}", expanded=True):
                        st.write(f"**Detay:** {row}")
                        c_not, c1, c2 = st.columns([2,1,1])
                        red_not = c_not.text_input("Not", key=f"n_{sheet_name}_{i}")
                        if c1.button("✅", key=f"o_{sheet_name}_{i}"):
                            sheet.update_cell(i+2, status_col_idx, "Onaylandı")
                            st.rerun()
                        if c2.button("❌", key=f"r_{sheet_name}_{i}"):
                            sheet.update_cell(i+2, status_col_idx, "Reddedildi")
                            sheet.update_cell(i+2, note_col_idx, red_not)
                            st.rerun()
        else: st.info("Veri yok.")
    except: st.error(f"'{sheet_name}' sekmesi bulunamadı.")

def module_hr_admin():
    t1, t2 = st.tabs(["İzin", "Avans"])
    with t1: render_admin_approval("Izinler", "İzin Onayı", ["Personel", "Tur"], 7, 8)
    with t2: render_admin_approval("Avanslar", "Avans Onayı", ["Personel", "Tutar"], 5, 6)

def module_purchasing_admin():
    render_admin_approval("SatinAlma", "Gider Onayı", ["Talep Eden", "Urun/Hizmet"], 6, 7)

# --- PERSONEL İŞLEMLERİ ---
def module_hr_employee(user_info):
    t1, t2, t3 = st.tabs(["İzin", "Avans", "Satın Alma"])
    db = get_db()
    if not db: return
    
    with t1:
        with st.form("i"):
            tur = st.selectbox("Tür", ["Yıllık", "Mazeret"]); bas = st.date_input("Baş"); bit = st.date_input("Bit"); ac = st.text_input("Açık.")
            if st.form_submit_button("İste"):
                gun = (bit-bas).days+1
                db.worksheet("Izinler").append_row([str(datetime.now().date()), user_info['AdSoyad'], tur, str(bas), str(bit), gun, "Bekliyor", ac, ""])
                st.success("OK")
        try:
            df = pd.DataFrame(db.worksheet("Izinler").get_all_records())
            if not df.empty: st.dataframe(df[df["Personel"]==user_info['AdSoyad']][["Tur","Durum","YoneticiNotu"]], use_container_width=True)
        except: pass

    with t2:
        with st.form("a"):
            tut = st.number_input("Tutar"); seb = st.text_input("Sebep")
            if st.form_submit_button("İste"):
                db.worksheet("Avanslar").append_row([str(datetime.now().date()), user_info['AdSoyad'], tut, seb, "Bekliyor", ""])
                st.success("OK")
        try:
            df = pd.DataFrame(db.worksheet("Avanslar").get_all_records())
            if not df.empty: st.dataframe(df[df["Personel"]==user_info['AdSoyad']][["Tutar","Durum","YoneticiNotu"]], use_container_width=True)
        except: pass

    with t3:
        with st.form("s"):
            u = st.text_input("Ürün"); t = st.number_input("Tutar")
            if st.form_submit_button("İste"):
                db.worksheet("SatinAlma").append_row([str(datetime.now().date()), user_info['AdSoyad'], u, "", t, "Bekliyor", ""])
                st.success("OK")
        try:
            df = pd.DataFrame(db.worksheet("SatinAlma").get_all_records())
            if not df.empty: st.dataframe(df[df["Talep Eden"]==user_info['AdSoyad']][["Urun/Hizmet","Durum"]], use_container_width=True)
        except: pass

# --- MAIN ---
def main():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.title("Here Event OS")
            with st.form("login"):
                u = st.text_input("Kullanıcı"); p = st.text_input("Şifre", type="password")
                if st.form_submit_button("Giriş"):
                    db = get_db()
                    if db:
                        try:
                            users = db.worksheet("Kullanicilar").get_all_records()
                            found = False
                            for user in users:
                                if str(user['KullaniciAdi']).strip() == u and str(user['Sifre']).strip() == p:
                                    st.session_state['logged_in'] = True; st.session_state['user_info'] = user; found=True; st.rerun()
                            if not found: st.error("Hatalı Giriş")
                        except Exception as e: st.error(f"Kullanıcı listesi okunamadı: {e}")
    else:
        user = st.session_state['user_info']
        if str(user['KullaniciAdi']).strip() == "admin": role = "Yonetici"
        else: role = str(user.get('Rol', 'Personel')).strip()

        with st.sidebar:
            st.title(f"👤 {user['AdSoyad']}")
            st.caption(f"Yetki: {role}")
            if role == "Yonetici":
                menu = st.radio("Menü", ["📊 Dashboard", "💼 Satış & Teklif", "👥 İK (ONAY)", "🛒 Satın Alma (ONAY)", "Çıkış"])
            else:
                menu = st.radio("Menü", ["💼 Satış & Teklif", "👋 Personel İşlemlerim", "Çıkış"])

        if menu == "Çıkış": st.session_state['logged_in'] = False; st.rerun()
        elif menu == "💼 Satış & Teklif": module_sales_shared()
        elif menu == "👥 İK (ONAY)": module_hr_admin()
        elif menu == "🛒 Satın Alma (ONAY)": module_purchasing_admin()
        elif menu == "👋 Personel İşlemlerim": module_hr_employee(user)
        elif menu == "📊 Dashboard": st.title("Yönetim Paneli"); st.metric("Sistem", "Online")

if __name__ == "__main__":
    main()
