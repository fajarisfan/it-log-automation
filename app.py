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
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                Paragraph, Spacer, HRFlowable,
                                BaseDocTemplate, PageTemplate, Frame)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# --- KONFIGURASI ---
FOLDER_ID = "1tpSWDgfMEac2ktTrUNMr7u7Y5V7tAZwa"
PDF_NAME  = "Laporan_IT_Triwulan_I_Isfan.pdf"
PDF_TITLE = "Laporan IT Triwulan I - Isfan"
JSON_NAME = "laporan_db.json"

# Palet warna
C_HEADER   = colors.HexColor("#1A5276")
C_SUBHEAD  = colors.HexColor("#2E86C1")
C_ROW_ODD  = colors.HexColor("#EBF5FB")
C_ROW_EVEN = colors.white
C_ACCENT   = colors.HexColor("#F39C12")
C_TEXT     = colors.HexColor("#1C2833")
C_WHITE    = colors.white
C_GREEN    = colors.HexColor("#1E8449")

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
        f = service.files().create(
            body={"name": name, "mimeType": "application/vnd.google-apps.folder",
                  "parents": [parent_id]}, fields="id"
        ).execute()
        fid = f["id"]
    return fid

# ── Dekorasi Header & Footer setiap halaman ──────────────────
def add_page_decorations(canvas, doc):
    canvas.saveState()
    W, H = A4

    # Strip biru atas
    canvas.setFillColor(C_HEADER)
    canvas.rect(0, H - 1.2*cm, W, 1.2*cm, fill=1, stroke=0)

    # Garis aksen oranye di bawah strip atas
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, H - 1.42*cm, W, 0.22*cm, fill=1, stroke=0)

    # Teks header
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(1.5*cm, H - 0.82*cm, "LAPORAN IT TRIWULAN I")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(W - 1.5*cm, H - 0.82*cm, "Teknisi: Isfan")

    # Strip biru bawah (footer)
    canvas.setFillColor(C_HEADER)
    canvas.rect(0, 0, W, 0.85*cm, fill=1, stroke=0)

    # Garis aksen oranye di atas footer
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, 0.85*cm, W, 0.18*cm, fill=1, stroke=0)

    # Teks footer
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(1.5*cm, 0.3*cm, "Divisi IT - Laporan Teknis Internal")
    canvas.drawRightString(W - 1.5*cm, 0.3*cm, f"Halaman {doc.page}")

    canvas.restoreState()

# ── PDF Generator ────────────────────────────────────────────
def generate_pdf(all_data):
    buf = io.BytesIO()

    doc = BaseDocTemplate(
        buf, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=3.0*cm, bottomMargin=1.8*cm,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="main", frames=frame,
                                       onPage=add_page_decorations)])

    # ── Paragraph styles ──
    s_judul = ParagraphStyle("judul", fontName="Helvetica-Bold", fontSize=15,
                             textColor=C_HEADER, alignment=TA_CENTER, spaceAfter=3)
    s_sub   = ParagraphStyle("sub",   fontName="Helvetica",      fontSize=9,
                             textColor=C_SUBHEAD, alignment=TA_CENTER, spaceAfter=8)
    s_hdr   = ParagraphStyle("hdr",   fontName="Helvetica-Bold", fontSize=9,
                             textColor=C_WHITE, alignment=TA_CENTER, leading=13)
    s_cell  = ParagraphStyle("cell",  fontName="Helvetica",      fontSize=8.5,
                             textColor=C_TEXT, leading=12)
    s_ctr   = ParagraphStyle("ctr",   fontName="Helvetica",      fontSize=8.5,
                             textColor=C_TEXT, alignment=TA_CENTER, leading=12)
    s_done  = ParagraphStyle("done",  fontName="Helvetica-Bold", fontSize=8,
                             textColor=C_GREEN, alignment=TA_CENTER, leading=12)
    s_info  = ParagraphStyle("info",  fontName="Helvetica",      fontSize=8,
                             textColor=C_TEXT, leading=13)

    elements = []
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph("Laporan IT Triwulan I", s_judul))
    elements.append(Paragraph("Teknisi: Isfan &nbsp;|&nbsp; Divisi Teknologi Informasi", s_sub))
    elements.append(HRFlowable(width="100%", thickness=2, color=C_ACCENT, spaceAfter=10))

    # ── Buat baris tabel ──
    header = [
        Paragraph("No",                        s_hdr),
        Paragraph("Bulan",                     s_hdr),
        Paragraph("Lokasi / Unit",             s_hdr),
        Paragraph("Jenis Kendala / Pekerjaan", s_hdr),
        Paragraph("Tindakan / Solusi",         s_hdr),
        Paragraph("Status",                    s_hdr),
    ]
    rows = [header]
    last_bulan = None

    for i, e in enumerate(all_data):
        bulan_ini = e.get("Bulan", "-")
        tampil_bulan = "" if bulan_ini == last_bulan else bulan_ini
        if bulan_ini != last_bulan:
            last_bulan = bulan_ini

        rows.append([
            Paragraph(str(i + 1), s_ctr),
            Paragraph(tampil_bulan, s_cell),
            Paragraph(e.get("Unit",    "-"), s_cell),
            Paragraph(e.get("Kendala", "-"), s_cell),
            Paragraph(e.get("Solusi",  "-"), s_cell),
            Paragraph("Selesai", s_done),
        ])

    # Zebra striping
    row_bg = []
    for i in range(1, len(rows)):
        bg = C_ROW_ODD if i % 2 == 1 else C_ROW_EVEN
        row_bg.append(("BACKGROUND", (0, i), (-1, i), bg))

    col_widths = [0.85*cm, 2.3*cm, 3.1*cm, 5.0*cm, 4.8*cm, 2.15*cm]
    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",    (0, 0), (-1, 0),  C_HEADER),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  9),
        ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, 0),  8),
        ("BOTTOMPADDING", (0, 0), (-1, 0),  8),
        ("LINEBELOW",     (0, 0), (-1, 0),  2, C_ACCENT),

        # Body
        ("VALIGN",        (0, 1), (-1, -1), "TOP"),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8.5),
        ("TOPPADDING",    (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),

        # Kolom center
        ("ALIGN",         (0, 1), (0, -1),  "CENTER"),
        ("ALIGN",         (1, 1), (1, -1),  "CENTER"),
        ("ALIGN",         (5, 1), (5, -1),  "CENTER"),

        # Grid
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#BDC3C7")),
        ("BOX",           (0, 0), (-1, -1), 1.2, C_SUBHEAD),

        *row_bg,
    ]))

    elements.append(tbl)
    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=C_SUBHEAD, spaceAfter=6))

    # Ringkasan
    bulan_list = list(dict.fromkeys(e.get("Bulan", "") for e in all_data))
    elements.append(Paragraph(
        f"Total entri: <b>{len(all_data)}</b> &nbsp;|&nbsp; "
        f"Bulan tercatat: <b>{', '.join(bulan_list)}</b>",
        s_info
    ))

    doc.build(elements)
    buf.seek(0)
    return buf


def show_pdf_preview(pdf_buffer):
    b64 = base64.b64encode(pdf_buffer.read()).decode("utf-8")
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" '
        f'width="100%" height="560px" '
        f'style="border:2px solid #2E86C1; border-radius:10px;"></iframe>',
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

    # ── INISIALISASI DATA AWAL ────────────────────────────────
    st.divider()
    with st.expander("⚙️ Inisialisasi Data Awal (Januari–April) — klik sekali saja"):
        st.warning("⚠️ Tombol ini akan **menimpa** semua data yang ada di Drive dengan data "
                   "Januari–April. Gunakan HANYA jika JSON di Drive masih kosong!")
        if st.button("📥 Isi Data Januari–April ke Drive"):
            data_awal = [
                {
                    "Bulan": "Januari",
                    "Unit": "Kasir",
                    "Kendala": "PC lambat dan sering hang",
                    "Solusi": "Cleaning sistem, optimasi startup, dan pengecekan RAM"
                },
                {
                    "Bulan": "Januari",
                    "Unit": "Apotek rawat jalan",
                    "Kendala": "Printer tidak terdeteksi",
                    "Solusi": "Re-install driver dan pengecekan kabel data USB"
                },
                {
                    "Bulan": "Februari",
                    "Unit": "Alamanda",
                    "Kendala": "Koneksi LAN terputus",
                    "Solusi": "Crimping ulang konektor RJ45 dan pengecekan port switch"
                },
                {
                    "Bulan": "Februari",
                    "Unit": "Gas Medis",
                    "Kendala": "Aplikasi sistem rumah sakit error",
                    "Solusi": "Troubleshooting pada software dan koordinasi tim sistem"
                },
                {
                    "Bulan": "Maret",
                    "Unit": "IGD",
                    "Kendala": "Monitor tidak tampil (No Signal)",
                    "Solusi": "Pengecekan kabel VGA/HDMI dan pembersihan slot GPU"
                },
                {
                    "Bulan": "Maret",
                    "Unit": "Farmasi",
                    "Kendala": "Instalasi perangkat komputer baru",
                    "Solusi": "Setting awal OS, jaringan, dan aplikasi standar RS"
                },
                {
                    "Bulan": "April",
                    "Unit": "Ruang SIMRS",
                    "Kendala": "Pengolahan data laporan jaspel (PDF ke CSV)",
                    "Solusi": "Konversi dan validasi data digital menggunakan aplikasi utilitas buatan sendiri"
                },
            ]
            with st.spinner("Menyimpan data awal ke Drive..."):
                try:
                    _, fid_existing = load_json(service)
                    save_json(service, data_awal, fid_existing)
                    upload_pdf(service, generate_pdf(data_awal))
                    st.success("✅ Data Januari–April berhasil disimpan! Sekarang bisa tambah Mei dan seterusnya.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Gagal: {e}")
