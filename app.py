import streamlit as st
import json
import io
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload, MediaFileUpload
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- KONFIGURASI ---
FOLDER_ID = "1tpSWDgfMEac2ktTrUNMr7u7Y5V7tAZwa"

# Mengambil kredensial dari Secrets dengan penanganan format
def get_creds():
    creds_dict = st.secrets["gcp_service_account"]
    # Memastikan private_key diformat ulang dengan \n agar terbaca benar
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    return service_account.Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/drive'])

drive_service = build('drive', 'v3', credentials=get_creds())

# --- FUNGSI DRIVE ---
def get_drive_file_id(name, parent_id=FOLDER_ID):
    query = f"name = '{name}' and '{parent_id}' in parents"
    results = drive_service.files().list(q=query).execute()
    items = results.get('files', [])
    return items[0]['id'] if items else None

def save_to_json(new_data):
    file_id = get_drive_file_id("laporan_db.json")
    if file_id:
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        downloader.next_chunk()
        data = json.loads(fh.getvalue().decode('utf-8'))
    else:
        data = []
    data.append(new_data)
    
    with open("temp.json", "w") as f:
        json.dump(data, f)
    
    media = MediaFileUpload("temp.json", mimetype='application/json')
    if file_id:
        drive_service.files().update(fileId=file_id, media_body=media).execute()
    else:
        drive_service.files().create(body={'name': 'laporan_db.json', 'parents': [FOLDER_ID]}, media_body=media).execute()
    return data

def update_pdf(all_data):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.drawString(50, 800, "Laporan IT Triwulan - Isfan")
    y = 770
    for entry in all_data:
        text = f"{entry['Bulan']} | {entry['Unit']} | {entry['Kendala']}"
        c.drawString(50, y, text)
        y -= 20
    c.save()
    buffer.seek(0)
    
    file_id = get_drive_file_id("Laporan_IT_Isfan.pdf")
    media = MediaIoBaseUpload(buffer, mimetype='application/pdf')
    if file_id:
        drive_service.files().update(fileId=file_id, media_body=media).execute()
    else:
        drive_service.files().create(body={'name': 'Laporan_IT_Isfan.pdf', 'parents': [FOLDER_ID]}, media_body=media).execute()

# --- UI APP ---
st.title("IT Log Automation")
bulan = st.selectbox("Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
unit = st.text_input("Lokasi / Unit")
kendala = st.text_area("Jenis Kendala")
solusi = st.text_area("Tindakan / Solusi")
ss_file = st.file_uploader("Upload Screenshot WA", type=['png', 'jpg'])

if st.button("Konfirmasi & Update Laporan"):
    with st.spinner("Sedang memproses ke Drive..."):
        new_entry = {"Bulan": bulan, "Unit": unit, "Kendala": kendala, "Solusi": solusi}
        all_data = save_to_json(new_entry)
        update_pdf(all_data)
        
        folder_bulan_id = get_drive_file_id(bulan) or drive_service.files().create(body={'name': bulan, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [FOLDER_ID]}, fields='id').execute().get('id')
        
        if ss_file:
            file_metadata = {'name': f"SS_{unit}_{bulan}.png", 'parents': [folder_bulan_id]}
            media = MediaIoBaseUpload(io.BytesIO(ss_file.read()), mimetype='image/png')
            drive_service.files().create(body=file_metadata, media_body=media).execute()
            
    st.success("Berhasil! Data, PDF, dan SS sudah terupdate di Drive.")
