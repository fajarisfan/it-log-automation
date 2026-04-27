import streamlit as st
import json
import io
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload, MediaFileUpload
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Konfigurasi
FOLDER_ID = "1tpSWDgfMEac2ktTrUNMr7u7Y5V7tAZwa"
creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=['https://www.googleapis.com/auth/drive'])
drive_service = build('drive', 'v3', credentials=creds)

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
    # Buat PDF di Memory
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.drawString(100, 800, "Laporan IT Tahunan")
    y = 750
    for entry in all_data:
        text = f"{entry['Bulan']} | {entry['Unit']} | {entry['Kendala']}"
        c.drawString(50, y, text)
        y -= 20
    c.save()
    buffer.seek(0)
    
    # Upload/Overwrite PDF
    file_id = get_drive_file_id("Laporan_IT_Isfan.pdf")
    media = MediaIoBaseUpload(buffer, mimetype='application/pdf')
    if file_id:
        drive_service.files().update(fileId=file_id, media_body=media).execute()
    else:
        drive_service.files().create(body={'name': 'Laporan_IT_Isfan.pdf', 'parents': [FOLDER_ID]}, media_body=media).execute()

# --- UI ---
st.title("IT Log Automation")
bulan = st.selectbox("Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
unit = st.text_input("Lokasi / Unit")
kendala = st.text_area("Jenis Kendala")
solusi = st.text_area("Tindakan / Solusi")
ss_file = st.file_uploader("Upload Screenshot WA", type=['png', 'jpg'])

if st.button("Konfirmasi & Update Laporan"):
    # 1. Update Database
    new_entry = {"Bulan": bulan, "Unit": unit, "Kendala": kendala, "Solusi": solusi}
    all_data = save_to_json(new_entry)
    
    # 2. Update PDF Otomatis
    update_pdf(all_data)
    
    # 3. Upload SS
    folder_bulan_id = get_drive_file_id(bulan) or drive_service.files().create(body={'name': bulan, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [FOLDER_ID]}, fields='id').execute().get('id')
    if ss_file:
        file_metadata = {'name': f"SS_{unit}_{bulan}.png", 'parents': [folder_bulan_id]}
        media = MediaIoBaseUpload(io.BytesIO(ss_file.read()), mimetype='image/png')
        drive_service.files().create(body=file_metadata, media_body=media).execute()

    st.success("PDF & Data berhasil terupdate!")
