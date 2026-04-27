import streamlit as st
import json
import io
import base64
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# --- KONFIGURASI ---
FOLDER_ID = "1tpSWDgfMEac2ktTrUNMr7u7Y5V7tAZwa"
PDF_NAME  = "Laporan_IT_Triwulan_I_Isfan.pdf"
PDF_TITLE = "Laporan IT Triwulan I - Isfan"
JSON_NAME = "laporan_db.json"

# ── Google Drive ────────────────────────────────────────────
@st.cache_resource
def get_drive_service():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        st.error(f"❌ Gagal konek ke Google Drive: {e}")
        st.stop()

def get_file_id(service, name, parent_id=FOLDER_ID):
    q = f"name='{name}' and '{parent_id}' in parents and trashed=false"
    res = service.files().list(q=q, fields="files(id)").execute()
    items = res.get("files", [])
    return items[0]["id"] if items else None

def load_json(service):
    fid = get_file_id(service, JSON_NAME)
    if not fid:
        return [], None
    req = service.files().get_media(fileId=fid)
    fh  = io.BytesIO()
    from googleapiclient.http import MediaIoBaseDownload
    dl = MediaIoBaseDownload(fh, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    return json.loads(fh.getvalue().decode("utf-8")), fid

def save_json(service, data, fid=None):
    b = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(b), mimetype="application/json", resumable=False)
    if fid:
        service.files().update(fileId=fid, media_body=media).execute()
    else:
        service.files().create(
            body={"name": JSON_NAME, "parents": [FOLDER_ID]}, media_body=media
        ).execute()

def upload_pdf(service, pdf_buffer):
    fid   = get_file_id(service, PDF_NAME)
    media = MediaIoBaseUpload(pdf_buffer, mimetype="application/pdf", resumable=False)
    if fid:
        service.files().update(fileId=fid, media_body=media).execute()
    else:
        service.files().create(
            body={"name": PDF_NAME, "parents": [FOLDER_ID]}, media_body=media
        ).execute()

def get_or_create_folder(service, name, parent_id=FOLDER_ID):
    fid = get_file_id(service, name, parent_id)
    if not fid:
        f   = service.files().create(
            body={"name": name, "mimeType": "application/vnd.google-apps.folder",
                  "parents": [parent_id]}, fields="id"
        ).execute()
        fid = f["id"]
    return fid

# ── PDF Generator ────────────────────────────────────────────
def generate_pdf(all_data):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("T", parent=styles["Heading1"],
                                 fontSize=13, alignment=TA_CENTER,
                                 spaceAfter=10, fontName="Helvetica-Bold")
    cell  = ParagraphStyle("C", parent=styles["Normal"], fontSize=9,
                           leading=12, fontName="Helvetica")
    ctr   = ParagraphStyle("CT", parent=cell, alignment=TA_CENTER)
    hdr   = ParagraphStyle("H", parent=cell, fontName="Helvetica-Bold",
                           alignment=TA_CENTER)

    elements = [Paragraph(PDF_TITLE, title_style), Spacer(1, 0.3*cm)]

    header = [Paragraph(t, hdr) for t in
              ["No", "Bulan", "Lokasi / Unit",
               "Jenis Kendala / Pekerjaan", "Tindakan / Solusi", "Status"]]

    rows = [header]
    for i, e in enumerate(all_data):
        rows.append([
            Paragraph(str(i+1), ctr),
            Paragraph(e.get("Bulan",  "-"), cell),
            Paragraph(e.get("Unit",   "-"), cell),
            Paragraph(e.get("Kendala","-"), cell),
            Paragraph(e.get("Solusi", "-"), cell),
            Paragraph("Selesai", ctr),
        ])

    col_widths = [1*cm, 2.5*cm, 3.2*cm, 5*cm, 5*cm, 2*cm]
    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  colors.HexColor("#2E75B6")),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("ALIGN",         (0,0), (-1,0),  "CENTER"),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("ALIGN",         (0,1), (0,-1),  "CENTER"),
        ("ALIGN",         (5,1), (5,-1),  "CENTER"),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("GRID",          (0,0), (-1,-1), 0.5, colors.HexColor("#AAAAAA")),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 5),
        *[("BACKGROUND",  (0,i), (-1,i),  colors.HexColor("#DEEAF1"))
          for i in range(2, len(rows), 2)],
    ]))

    elements.append(tbl)
    doc.build(elements)
    buf.seek(0)
    return buf

def show_pdf_preview(pdf_buffer):
    """Tampilkan PDF inline di Streamlit."""
    b64 = base64.b64encode(pdf_buffer.read()).decode("utf-8")
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" '
        f'width="100%" height="520px" style="border:1px solid #ddd; border-radius:8px;"></iframe>',
        unsafe_allow_html=True
    )

# ── UI ───────────────────────────────────────────────────────
st.title("🖥️ IT Log Automation")
st.caption("Input laporan kendala IT dan simpan otomatis ke Google Drive")

service = get_drive_service()

tab1, tab2 = st.tabs(["📝 Input Laporan", "🗂️ Lihat & Hapus Data"])

# ── TAB 1 : INPUT ────────────────────────────────────────────
with tab1:
    with st.form("form_laporan"):
        bulan   = st.selectbox("Bulan", [
            "Januari","Februari","Maret","April","Mei","Juni",
            "Juli","Agustus","September","Oktober","November","Desember"
        ])
        unit    = st.text_input("Lokasi / Unit")
        kendala = st.text_area("Jenis Kendala / Pekerjaan")
        solusi  = st.text_area("Tindakan / Solusi")
        ss_file = st.file_uploader("Upload Screenshot WA (opsional)",
                                   type=["png","jpg","jpeg"])

        col_prev, col_sub = st.columns([1, 1])
        with col_prev:
            preview_btn = st.form_submit_button("🔍 Preview PDF")
        with col_sub:
            submit_btn  = st.form_submit_button("✅ Konfirmasi & Update Laporan")

    # ── PREVIEW ──
    if preview_btn:
        if not unit or not kendala or not solusi:
            st.warning("⚠️ Isi semua field dulu untuk preview.")
        else:
            data, _ = load_json(service)
            preview_entry = {"Bulan": bulan, "Unit": unit,
                             "Kendala": kendala, "Solusi": solusi}
            preview_data  = data + [preview_entry]

            st.info(f"👁️ Preview PDF dengan {len(preview_data)} entri "
                    f"(data lama {len(data)} + entri baru ini). "
                    f"Belum tersimpan ke Drive.")
            pdf_buf = generate_pdf(preview_data)
            show_pdf_preview(pdf_buf)

    # ── SUBMIT ──
    if submit_btn:
        if not unit or not kendala or not solusi:
            st.warning("⚠️ Mohon isi semua field sebelum submit.")
        else:
            with st.spinner("Sedang memproses ke Drive..."):
                try:
                    data, fid = load_json(service)
                    data.append({"Bulan": bulan, "Unit": unit,
                                 "Kendala": kendala, "Solusi": solusi})
                    save_json(service, data, fid)
                    upload_pdf(service, generate_pdf(data))

                    if ss_file:
                        folder_id = get_or_create_folder(service, bulan)
                        ext = ss_file.name.rsplit(".", 1)[-1]
                        service.files().create(
                            body={"name": f"SS_{unit}_{bulan}.{ext}",
                                  "parents": [folder_id]},
                            media_body=MediaIoBaseUpload(
                                io.BytesIO(ss_file.read()),
                                mimetype=f"image/{ext}", resumable=False)
                        ).execute()

                    st.success(f"✅ Berhasil! **{PDF_NAME}** diperbarui di Drive.")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Terjadi kesalahan: {e}")

# ── TAB 2 : LIHAT & HAPUS ────────────────────────────────────
with tab2:
    st.subheader("📋 Data Laporan Tersimpan")
    data, fid = load_json(service)

    if not data:
        st.info("Belum ada data tersimpan.")
    else:
        st.write(f"Total entri: **{len(data)}**")

        # Tombol preview PDF yang tersimpan
        if st.button("🔍 Preview PDF Tersimpan"):
            pdf_buf = generate_pdf(data)
            show_pdf_preview(pdf_buf)

        st.divider()
        to_delete = []

        for i, entry in enumerate(data):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(
                    f"**{i+1}. {entry.get('Bulan','-')} | {entry.get('Unit','-')}**  \n"
                    f"🔧 {entry.get('Kendala','-')}  \n"
                    f"✅ {entry.get('Solusi','-')}"
                )
            with col2:
                if st.button("🗑️", key=f"del_{i}", help="Hapus entri ini"):
                    to_delete.append(i)

        if to_delete:
            with st.spinner("Menghapus dan update PDF..."):
                new_data = [e for idx, e in enumerate(data) if idx not in to_delete]
                save_json(service, new_data, fid)
                upload_pdf(service, generate_pdf(new_data))
                st.success("✅ Data dihapus dan PDF diperbarui di Drive!")
                st.rerun()
