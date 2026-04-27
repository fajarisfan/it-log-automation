import streamlit as st
import json
import io
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- KONFIGURASI ---
FOLDER_ID = "1tpSWDgfMEac2ktTrUNMr7u7Y5V7tAZwa"

@st.cache_resource
def get_drive_service():
    """Inisialisasi Drive service sekali, di-cache agar tidak reconnect terus."""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        # Fix newline di private key (umum terjadi di Streamlit Cloud)
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"❌ Gagal konek ke Google Drive: {e}")
        st.stop()

# --- FUNGSI DRIVE ---
def get_drive_file_id(service, name, parent_id=FOLDER_ID):
    query = f"name = '{name}' and '{parent_id}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    return items[0]['id'] if items else None

def save_to_json(service, new_data):
    """Download JSON yang ada, tambah entry baru, lalu upload balik — tanpa file temp."""
    file_id = get_drive_file_id(service, "laporan_db.json")
    
    if file_id:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        data = json.loads(fh.getvalue().decode('utf-8'))
    else:
        data = []
    
    data.append(new_data)
    
    # Upload pakai BytesIO, tanpa nulis file ke disk
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
    media = MediaIoBaseUpload(io.BytesIO(json_bytes), mimetype='application/json', resumable=False)
    
    if file_id:
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        service.files().create(
            body={'name': 'laporan_db.json', 'parents': [FOLDER_ID]},
            media_body=media
        ).execute()
    
    return data

def update_pdf(service, all_data):
    """Buat PDF dari semua data, dengan penanganan overflow halaman."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, "Laporan IT Triwulan - Isfan")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Total entri: {len(all_data)}")
    
    y = height - 100
    margin_bottom = 50

    for i, entry in enumerate(all_data):
        # Pindah halaman baru kalau sudah hampir habis
        if y < margin_bottom + 60:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - 50

        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, f"{i+1}. {entry.get('Bulan', '-')} | {entry.get('Unit', '-')}")
        y -= 15
        
        c.setFont("Helvetica", 9)
        c.drawString(60, y, f"Kendala : {entry.get('Kendala', '-')}")
        y -= 13
        c.drawString(60, y, f"Solusi  : {entry.get('Solusi', '-')}")
        y -= 20  # Spasi antar entri

    c.save()
    buffer.seek(0)
    
    file_id = get_drive_file_id(service, "Laporan_IT_Isfan.pdf")
    media = MediaIoBaseUpload(buffer, mimetype='application/pdf', resumable=False)
    
    if file_id:
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        service.files().create(
            body={'name': 'Laporan_IT_Isfan.pdf', 'parents': [FOLDER_ID]},
            media_body=media
        ).execute()

def get_or_create_folder(service, name, parent_id=FOLDER_ID):
    """Cari folder by name, buat baru kalau belum ada."""
    folder_id = get_drive_file_id(service, name, parent_id)
    if not folder_id:
        folder = service.files().create(
            body={
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            },
            fields='id'
        ).execute()
        folder_id = folder.get('id')
    return folder_id

# --- UI APP ---
st.title("🖥️ IT Log Automation")
st.caption("Input laporan kendala IT dan simpan otomatis ke Google Drive")

with st.form("form_laporan"):
    bulan = st.selectbox("Bulan", [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ])
    unit = st.text_input("Lokasi / Unit")
    kendala = st.text_area("Jenis Kendala")
    solusi = st.text_area("Tindakan / Solusi")
    ss_file = st.file_uploader("Upload Screenshot WA (opsional)", type=['png', 'jpg', 'jpeg'])
    submitted = st.form_submit_button("✅ Konfirmasi & Update Laporan")

if submitted:
    if not unit or not kendala or not solusi:
        st.warning("⚠️ Mohon isi semua field sebelum submit.")
    else:
        with st.spinner("Sedang memproses ke Drive..."):
            try:
                service = get_drive_service()
                
                new_entry = {
                    "Bulan": bulan,
                    "Unit": unit,
                    "Kendala": kendala,
                    "Solusi": solusi
                }
                
                # 1. Simpan ke JSON
                all_data = save_to_json(service, new_entry)
                
                # 2. Update PDF
                update_pdf(service, all_data)
                
                # 3. Upload screenshot kalau ada
                if ss_file:
                    folder_bulan_id = get_or_create_folder(service, bulan)
                    ext = ss_file.name.split('.')[-1]
                    file_metadata = {
                        'name': f"SS_{unit}_{bulan}.{ext}",
                        'parents': [folder_bulan_id]
                    }
                    media = MediaIoBaseUpload(
                        io.BytesIO(ss_file.read()),
                        mimetype=f'image/{ext}',
                        resumable=False
                    )
                    service.files().create(body=file_metadata, media_body=media).execute()
                
                st.success("✅ Berhasil! Data, PDF, dan screenshot sudah tersimpan di Drive.")
                st.balloons()
                
            except Exception as e:
                st.error(f"❌ Terjadi kesalahan: {e}")
