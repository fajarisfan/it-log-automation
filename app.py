import streamlit as st
import json
import io
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload, MediaFileUpload
from reportlab.pdfgen import canvas

# Konfigurasi ID Folder Drive
FOLDER_ID = "1tpSWDgfMEac2ktTrUNMr7u7Y5V7tAZwa"

# Setup Google Drive
creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=['https://www.googleapis.com/auth/drive'])
drive_service = build('drive', 'v3', credentials=creds)

def get_drive_file_id(name):
    query = f"name = '{name}' and '{FOLDER_ID}' in parents"
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

# UI Streamlit
st.title("IT Log Automation")
bulan = st.selectbox("Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
unit = st.text_input("Lokasi / Unit")
kendala = st.text_area("Jenis Kendala")
solusi = st.text_area("Tindakan / Solusi")
ss_file = st.file_uploader("Upload Screenshot WA", type=['png', 'jpg'])

if st.button("Konfirmasi & Update Laporan"):
    # 1. Simpan ke database JSON
    new_entry = {"Bulan": bulan, "Unit": unit, "Kendala": kendala, "Solusi": solusi}
    all_data = save_to_json(new_entry)
    
    # 2. Upload Screenshot ke folder bulanan
    folder_bulan_id = get_drive_file_id(bulan) or drive_service.files().create(body={'name': bulan, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [FOLDER_ID]}, fields='id').execute().get('id')
    
    if ss_file:
        file_metadata = {'name': f"SS_{unit}_{bulan}.png", 'parents': [folder_bulan_id]}
        media = MediaIoBaseUpload(io.BytesIO(ss_file.read()), mimetype='image/png')
        drive_service.files().create(body=file_metadata, media_body=media).execute()

    st.success("Data berhasil ditambah & Laporan terupdate!")
