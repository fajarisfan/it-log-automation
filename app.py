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
from reportlab.platypus import (Table, TableStyle, Paragraph, Spacer,
                                HRFlowable, BaseDocTemplate, PageTemplate, Frame)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# --- KONFIGURASI ---
FOLDER_ID = "1tpSWDgfMEac2ktTrUNMr7u7Y5V7tAZwa"
JSON_NAME = "laporan_db.json"

TRIWULAN_CONFIG = {
    "Triwulan 1 (Jan–Mar)": {
        "pdf_name":  "Laporan_IT_Triwulan_1_Isfan.pdf",
        "pdf_title": "Laporan IT Triwulan I",
        "header":    "LAPORAN IT TRIWULAN I",
        "bulan":     ["Januari", "Februari", "Maret"],
    },
    "Triwulan 2 (Apr–Jun)": {
        "pdf_name":  "Laporan_IT_Triwulan_2_Isfan.pdf",
        "pdf_title": "Laporan IT Triwulan II",
        "header":    "LAPORAN IT TRIWULAN II",
        "bulan":     ["April", "Mei", "Juni"],
    },
    "Triwulan Final / Tahunan": {
        "pdf_name":  "Laporan_IT_Triwulan_Final_Isfan.pdf",
        "pdf_title": "Laporan IT Tahunan (Final)",
        "header":    "LAPORAN IT TAHUNAN (FINAL)",
        "bulan":     ["Januari","Februari","Maret","April","Mei","Juni",
                      "Juli","Agustus","September","Oktober","November","Desember"],
    },
}

C_HEADER  = colors.HexColor("#1A5276")
C_SUBHEAD = colors.HexColor("#2E86C1")
C_ROW_ODD = colors.HexColor("#EBF5FB")
C_ROW_EVEN= colors.white
C_ACCENT  = colors.HexColor("#F39C12")
C_TEXT    = colors.HexColor("#1C2833")
C_WHITE   = colors.white
C_GREEN   = colors.HexColor("#1E8449")

# ── Google Drive ─────────────────────────────────────────────
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
        st.error("❌ File `laporan_db.json` tidak ditemukan. Pastikan file sudah ada di folder Drive dan folder sudah di-share ke service account sebagai Editor.")
        st.stop()
    req = service.files().get_media(fileId=fid)
    fh  = io.BytesIO()
    dl  = MediaIoBaseDownload(fh, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    raw = fh.getvalue().decode("utf-8").strip()
    if not raw:
        return [], fid
    return json.loads(raw), fid

def save_json(service, data, fid=None):
    if not fid:
        st.error("❌ File `laporan_db.json` tidak ditemukan. Cek folder Drive.")
        st.stop()
    b = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(b), mimetype="application/json", resumable=False)
    service.files().update(fileId=fid, media_body=media).execute()

def create_placeholder_pdf(pdf_title, header_text):
    """Buat PDF placeholder 1 halaman untuk file yang belum ada di Drive."""
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4,
                          rightMargin=1.5*cm, leftMargin=1.5*cm,
                          topMargin=3.0*cm, bottomMargin=1.8*cm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="main", frames=frame,
                                       onPage=make_page_decorator(header_text))])
    s_judul = ParagraphStyle("judul", fontName="Helvetica-Bold", fontSize=15,
                             textColor=C_HEADER, alignment=TA_CENTER, spaceAfter=12)
    s_info  = ParagraphStyle("info",  fontName="Helvetica", fontSize=10,
                             textColor=C_TEXT, alignment=TA_CENTER, leading=16)
    elements = [
        Spacer(1, 2*cm),
        Paragraph(pdf_title, s_judul),
        Spacer(1, 0.5*cm),
        HRFlowable(width="60%", thickness=2, color=C_ACCENT, spaceAfter=20),
        Spacer(1, 0.5*cm),
        Paragraph("File ini akan diperbarui otomatis", s_info),
        Paragraph("melalui aplikasi EKIN IT Support.", s_info),
        Spacer(1, 0.3*cm),
        Paragraph("Teknisi: Isfan | Divisi Teknologi Informasi", s_info),
        Paragraph("RSUD Kota Cilegon", s_info),
    ]
    doc.build(elements)
    buf.seek(0)
    return buf

def upload_pdf(service, pdf_buffer, pdf_name=None):
    target = pdf_name or "Laporan_IT_Triwulan_1_Isfan.pdf"
    fid = get_file_id(service, target)
    if not fid:
        # Auto create kalau belum ada
        pdf_buffer.seek(0)
        media = MediaIoBaseUpload(pdf_buffer, mimetype="application/pdf", resumable=False)
        service.files().create(
            body={"name": target, "parents": [FOLDER_ID]},
            media_body=media, fields="id"
        ).execute()
    else:
        media = MediaIoBaseUpload(pdf_buffer, mimetype="application/pdf", resumable=False)
        service.files().update(fileId=fid, media_body=media).execute()

def ensure_all_pdfs_exist(service):
    """Cek semua file PDF triwulan — auto create placeholder kalau belum ada."""
    missing = []
    for nama_triwulan, cfg in TRIWULAN_CONFIG.items():
        fid = get_file_id(service, cfg["pdf_name"])
        if not fid:
            missing.append((nama_triwulan, cfg))
    if missing:
        for nama_triwulan, cfg in missing:
            placeholder = create_placeholder_pdf(cfg["pdf_title"], cfg["header"])
            upload_pdf(service, placeholder, cfg["pdf_name"])
    return missing

def upload_screenshot(service, ss_file, bulan, unit):
    try:
        fid = get_file_id(service, bulan)
        if not fid:
            try:
                f = service.files().create(
                    body={"name": bulan,
                          "mimeType": "application/vnd.google-apps.folder",
                          "parents": [FOLDER_ID]},
                    fields="id"
                ).execute()
                fid = f["id"]
            except Exception:
                fid = FOLDER_ID
        ext = ss_file.name.rsplit(".", 1)[-1]
        service.files().create(
            body={"name": f"SS_{unit}_{bulan}.{ext}", "parents": [fid]},
            media_body=MediaIoBaseUpload(
                io.BytesIO(ss_file.read()),
                mimetype=f"image/{ext}", resumable=False)
        ).execute()
    except Exception as e:
        st.warning(f"⚠️ Screenshot tidak tersimpan: {e}")

# ── Helper: Deteksi folder bulan yang sudah ada di Drive ─────
BULAN_URUT = [
    "Januari","Februari","Maret","April","Mei","Juni",
    "Juli","Agustus","September","Oktober","November","Desember"
]

def get_existing_month_folders(service):
    """Return dict {nama_bulan: folder_id} untuk folder bulan yang sudah ada di Drive."""
    q = f"'{FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    res = service.files().list(q=q, fields="files(id,name)").execute()
    items = res.get("files", [])
    return {item["name"]: item["id"] for item in items if item["name"] in BULAN_URUT}

def get_next_months(existing_folders):
    """Return list bulan yang belum ada foldernya."""
    return [b for b in BULAN_URUT if b not in existing_folders]

def get_or_create_folder(service, bulan_name):
    """Get folder id bulan, buat baru kalau belum ada."""
    fid = get_file_id(service, bulan_name)
    if not fid:
        f = service.files().create(
            body={"name": bulan_name,
                  "mimeType": "application/vnd.google-apps.folder",
                  "parents": [FOLDER_ID]},
            fields="id"
        ).execute()
        fid = f["id"]
    return fid

def upload_ss_to_folder(service, ss_file, folder_id, filename):
    """Upload file SS ke folder tertentu."""
    ext = ss_file.name.rsplit(".", 1)[-1].lower()
    mime = f"image/{ext}" if ext in ["jpg","jpeg","png","webp"] else "application/octet-stream"
    service.files().create(
        body={"name": filename, "parents": [folder_id]},
        media_body=MediaIoBaseUpload(
            io.BytesIO(ss_file.read()),
            mimetype=mime, resumable=False)
    ).execute()

# ── Dekorasi halaman PDF ──────────────────────────────────────
def make_page_decorator(header_text):
    def add_page_decorations(canvas, doc):
        canvas.saveState()
        W, H = A4
        canvas.setFillColor(C_HEADER)
        canvas.rect(0, H - 1.2*cm, W, 1.2*cm, fill=1, stroke=0)
        canvas.setFillColor(C_ACCENT)
        canvas.rect(0, H - 1.42*cm, W, 0.22*cm, fill=1, stroke=0)
        canvas.setFillColor(C_WHITE)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(1.5*cm, H - 0.82*cm, header_text)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(W - 1.5*cm, H - 0.82*cm, "Teknisi: Isfan")
        canvas.setFillColor(C_HEADER)
        canvas.rect(0, 0, W, 0.85*cm, fill=1, stroke=0)
        canvas.setFillColor(C_ACCENT)
        canvas.rect(0, 0.85*cm, W, 0.18*cm, fill=1, stroke=0)
        canvas.setFillColor(C_WHITE)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(1.5*cm, 0.3*cm, "Divisi IT - Laporan Teknis Internal")
        canvas.drawRightString(W - 1.5*cm, 0.3*cm, f"Halaman {doc.page}")
        canvas.restoreState()
    return add_page_decorations

# ── PDF Generator ─────────────────────────────────────────────
def generate_pdf(all_data, pdf_title="Laporan IT Triwulan I", header_text="LAPORAN IT TRIWULAN I"):
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4,
                          rightMargin=1.5*cm, leftMargin=1.5*cm,
                          topMargin=3.0*cm, bottomMargin=1.8*cm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="main", frames=frame,
                                       onPage=make_page_decorator(header_text))])

    s_judul = ParagraphStyle("judul", fontName="Helvetica-Bold", fontSize=15,
                             textColor=C_HEADER, alignment=TA_CENTER, spaceAfter=3)
    s_sub   = ParagraphStyle("sub",   fontName="Helvetica", fontSize=9,
                             textColor=C_SUBHEAD, alignment=TA_CENTER, spaceAfter=8)
    s_hdr   = ParagraphStyle("hdr",   fontName="Helvetica-Bold", fontSize=9,
                             textColor=C_WHITE, alignment=TA_CENTER, leading=13)
    s_cell  = ParagraphStyle("cell",  fontName="Helvetica", fontSize=8.5,
                             textColor=C_TEXT, leading=12)
    s_ctr   = ParagraphStyle("ctr",   fontName="Helvetica", fontSize=8.5,
                             textColor=C_TEXT, alignment=TA_CENTER, leading=12)
    s_done  = ParagraphStyle("done",  fontName="Helvetica-Bold", fontSize=8,
                             textColor=C_GREEN, alignment=TA_CENTER, leading=12)
    s_info  = ParagraphStyle("info",  fontName="Helvetica", fontSize=8,
                             textColor=C_TEXT, leading=13)

    elements = [Spacer(1, 0.2*cm),
                Paragraph(pdf_title, s_judul),
                Paragraph("Teknisi: Isfan &nbsp;|&nbsp; Divisi Teknologi Informasi", s_sub),
                HRFlowable(width="100%", thickness=2, color=C_ACCENT, spaceAfter=10)]

    header = [Paragraph(t, s_hdr) for t in
              ["No","Bulan","Lokasi / Unit",
               "Jenis Kendala / Pekerjaan","Tindakan / Solusi","Status"]]
    rows = [header]
    last_bulan = None
    for i, e in enumerate(all_data):
        bulan_ini = e.get("Bulan", "-")
        tampil    = "" if bulan_ini == last_bulan else bulan_ini
        if bulan_ini != last_bulan:
            last_bulan = bulan_ini
        rows.append([
            Paragraph(str(i+1), s_ctr),
            Paragraph(tampil, s_cell),
            Paragraph(e.get("Unit",    "-"), s_cell),
            Paragraph(e.get("Kendala", "-"), s_cell),
            Paragraph(e.get("Solusi",  "-"), s_cell),
            Paragraph("Selesai", s_done),
        ])

    row_bg = [("BACKGROUND", (0,i), (-1,i), C_ROW_ODD if i%2==1 else C_ROW_EVEN)
              for i in range(1, len(rows))]

    tbl = Table(rows, colWidths=[0.85*cm,2.3*cm,3.1*cm,5.0*cm,4.8*cm,2.15*cm],
                repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), C_HEADER),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 9),
        ("ALIGN",         (0,0),(-1,0), "CENTER"),
        ("TOPPADDING",    (0,0),(-1,0), 8),
        ("BOTTOMPADDING", (0,0),(-1,0), 8),
        ("LINEBELOW",     (0,0),(-1,0), 2, C_ACCENT),
        ("VALIGN",        (0,1),(-1,-1),"TOP"),
        ("FONTNAME",      (0,1),(-1,-1),"Helvetica"),
        ("FONTSIZE",      (0,1),(-1,-1), 8.5),
        ("TOPPADDING",    (0,1),(-1,-1), 6),
        ("BOTTOMPADDING", (0,1),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ("ALIGN",         (0,1),(0,-1), "CENTER"),
        ("ALIGN",         (1,1),(1,-1), "CENTER"),
        ("ALIGN",         (5,1),(5,-1), "CENTER"),
        ("GRID",          (0,0),(-1,-1), 0.4, colors.HexColor("#BDC3C7")),
        ("BOX",           (0,0),(-1,-1), 1.2, C_SUBHEAD),
        *row_bg,
    ]))

    bulan_list = list(dict.fromkeys(e.get("Bulan","") for e in all_data))
    elements += [tbl, Spacer(1, 0.5*cm),
                 HRFlowable(width="100%", thickness=1, color=C_SUBHEAD, spaceAfter=6),
                 Paragraph(f"Total entri: <b>{len(all_data)}</b> &nbsp;|&nbsp; "
                            f"Bulan tercatat: <b>{', '.join(bulan_list)}</b>", s_info)]
    doc.build(elements)
    buf.seek(0)
    return buf

def show_pdf_preview(pdf_buffer):
    b64 = base64.b64encode(pdf_buffer.read()).decode("utf-8")
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" '
        f'width="100%" height="560px" '
        f'style="border:2px solid #2E86C1; border-radius:10px;"></iframe>',
        unsafe_allow_html=True)

# ── UI ────────────────────────────────────────────────────────
st.title("🖥️ Buat push dukung bukti EKIN")
st.caption("Input laporan kendala IT dan simpan otomatis ke Google Drive")

service = get_drive_service()

# ── Auto-create PDF placeholder kalau belum ada di Drive ─────
if "pdf_init_done" not in st.session_state:
    with st.spinner("🔍 Mengecek file PDF di Drive..."):
        missing = ensure_all_pdfs_exist(service)
        if missing:
            nama_missing = [cfg["pdf_name"] for _, cfg in missing]
            st.success(f"✅ Auto-created {len(missing)} file PDF baru di Drive: {', '.join(nama_missing)}")
    st.session_state.pdf_init_done = True

# ── Pilih Triwulan ────────────────────────────────────────────
st.divider()
selected_triwulan = st.selectbox(
    "📅 Pilih Periode Triwulan",
    options=list(TRIWULAN_CONFIG.keys()),
    help="Pilih periode yang sesuai dengan eKinerja — Triwulan 1, Triwulan 2, atau Final/Tahunan"
)
cfg       = TRIWULAN_CONFIG[selected_triwulan]
PDF_NAME  = cfg["pdf_name"]
PDF_TITLE = cfg["pdf_title"]
HDR_TEXT  = cfg["header"]
BULAN_TRIWULAN = cfg["bulan"]

st.info(f"📄 PDF target: `{PDF_NAME}`")
st.divider()

# ── Session state untuk edit ──────────────────────────────────
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

tab1, tab2, tab3 = st.tabs(["📝 Input Laporan", "🗂️ Lihat, Edit & Hapus Data", "📸 Upload SS WA"])

# ══════════════════════════════════════════════════════════════
# TAB 1 — CREATE
# ══════════════════════════════════════════════════════════════
with tab1:
    with st.form("form_laporan"):
        bulan   = st.selectbox("Bulan", BULAN_TRIWULAN)
        unit    = st.text_input("Lokasi / Unit")
        kendala = st.text_area("Jenis Kendala / Pekerjaan")
        solusi  = st.text_area("Tindakan / Solusi")
        with st.expander("📎 Upload Screenshot WA (opsional, lebih lengkap di Tab 3)"):
            st.caption("💡 Untuk upload SS WA lebih mudah, pakai tab **📸 Upload SS WA** di atas.")
            ss_file = st.file_uploader("Screenshot WA", type=["png","jpg","jpeg"])
        col1, col2 = st.columns(2)
        with col1: preview_btn = st.form_submit_button("🔍 Preview PDF")
        with col2: submit_btn  = st.form_submit_button("✅ Konfirmasi & Update Laporan")

    if preview_btn:
        if not unit or not kendala or not solusi:
            st.warning("⚠️ Isi semua field dulu untuk preview.")
        else:
            data, _ = load_json(service)
            preview  = data + [{"Bulan":bulan,"Unit":unit,"Kendala":kendala,"Solusi":solusi}]
            st.info(f"👁️ Preview {len(preview)} entri (belum tersimpan ke Drive)")
            show_pdf_preview(generate_pdf(preview, PDF_TITLE, HDR_TEXT))

    if submit_btn:
        if not unit or not kendala or not solusi:
            st.warning("⚠️ Mohon isi semua field sebelum submit.")
        else:
            with st.spinner("Menyimpan ke Drive..."):
                try:
                    data, fid = load_json(service)
                    data.append({"Bulan":bulan,"Unit":unit,
                                 "Kendala":kendala,"Solusi":solusi})
                    save_json(service, data, fid)
                    upload_pdf(service, generate_pdf(data, PDF_TITLE, HDR_TEXT), PDF_NAME)
                    if ss_file:
                        upload_screenshot(service, ss_file, bulan, unit)
                    st.success(f"✅ Berhasil! **{PDF_NAME}** diperbarui di Drive.")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Terjadi kesalahan: {e}")

# ══════════════════════════════════════════════════════════════
# TAB 2 — READ / UPDATE / DELETE
# ══════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📋 Data Laporan Tersimpan")
    data, fid = load_json(service)

    if not data:
        st.info("Belum ada data tersimpan.")
    else:
        st.write(f"Total entri: **{len(data)}**")
        if st.button("🔍 Preview PDF Tersimpan"):
            show_pdf_preview(generate_pdf(data, PDF_TITLE, HDR_TEXT))

        st.divider()

        BULAN_OPTIONS = BULAN_TRIWULAN

        for i, entry in enumerate(data):
            # ── Mode EDIT aktif untuk baris ini ──────────────
            if st.session_state.edit_index == i:
                with st.container(border=True):
                    st.markdown(f"#### ✏️ Edit Entri #{i+1}")
                    with st.form(key=f"form_edit_{i}"):
                        e_bulan = st.selectbox(
                            "Bulan",
                            BULAN_OPTIONS,
                            index=BULAN_OPTIONS.index(entry.get("Bulan","Januari"))
                                  if entry.get("Bulan") in BULAN_OPTIONS else 0
                        )
                        e_unit    = st.text_input("Lokasi / Unit",
                                                  value=entry.get("Unit",""))
                        e_kendala = st.text_area("Jenis Kendala / Pekerjaan",
                                                 value=entry.get("Kendala",""))
                        e_solusi  = st.text_area("Tindakan / Solusi",
                                                 value=entry.get("Solusi",""))
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            save_edit = st.form_submit_button("💾 Simpan Perubahan",
                                                              type="primary")
                        with col_cancel:
                            cancel_edit = st.form_submit_button("✖ Batal")

                    if save_edit:
                        if not e_unit or not e_kendala or not e_solusi:
                            st.warning("⚠️ Semua field harus diisi.")
                        else:
                            with st.spinner("Menyimpan perubahan ke Drive..."):
                                try:
                                    data[i] = {
                                        "Bulan":   e_bulan,
                                        "Unit":    e_unit,
                                        "Kendala": e_kendala,
                                        "Solusi":  e_solusi,
                                    }
                                    save_json(service, data, fid)
                                    upload_pdf(service, generate_pdf(data, PDF_TITLE, HDR_TEXT), PDF_NAME)
                                    st.success("✅ Entri berhasil diperbarui!")
                                    st.session_state.edit_index = None
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Gagal menyimpan: {e}")

                    if cancel_edit:
                        st.session_state.edit_index = None
                        st.rerun()

            # ── Mode NORMAL (tampil biasa + tombol Edit/Hapus) ─
            else:
                c1, c2, c3 = st.columns([5, 1, 1])
                with c1:
                    st.markdown(
                        f"**{i+1}. {entry.get('Bulan','-')} | {entry.get('Unit','-')}**  \n"
                        f"🔧 {entry.get('Kendala','-')}  \n"
                        f"✅ {entry.get('Solusi','-')}"
                    )
                with c2:
                    if st.button("✏️", key=f"edit_{i}", help="Edit entri ini"):
                        st.session_state.edit_index = i
                        st.rerun()
                with c3:
                    if st.button("🗑️", key=f"del_{i}", help="Hapus entri ini"):
                        with st.spinner("Menghapus..."):
                            new_data = [e for j, e in enumerate(data) if j != i]
                            save_json(service, new_data, fid)
                            upload_pdf(service, generate_pdf(new_data, PDF_TITLE, HDR_TEXT), PDF_NAME)
                            st.success("✅ Dihapus!")
                            st.rerun()

    # ── Gabungkan Data Januari–April ──────────────────────────
    st.divider()
    with st.expander("⚙️ Tambah Data Awal Januari–April"):
        st.info("✅ Data Januari–April akan ditambahkan **di depan** data yang sudah ada. "
                "Data lama seperti Mei **tidak akan hilang**.")
        if st.button("📥 Gabungkan Data Januari–April ke Drive"):
            data_awal = [
                {"Bulan":"Januari",  "Unit":"Kasir",
                 "Kendala":"PC lambat dan sering hang",
                 "Solusi":"Cleaning sistem, optimasi startup, dan pengecekan RAM"},
                {"Bulan":"Januari",  "Unit":"Apotek rawat jalan",
                 "Kendala":"Printer tidak terdeteksi",
                 "Solusi":"Re-install driver dan pengecekan kabel data USB"},
                {"Bulan":"Februari", "Unit":"Alamanda",
                 "Kendala":"Koneksi LAN terputus",
                 "Solusi":"Crimping ulang konektor RJ45 dan pengecekan port switch"},
                {"Bulan":"Februari", "Unit":"Gas Medis",
                 "Kendala":"Aplikasi sistem rumah sakit error",
                 "Solusi":"Troubleshooting pada software dan koordinasi tim sistem"},
                {"Bulan":"Maret",    "Unit":"IGD",
                 "Kendala":"Monitor tidak tampil (No Signal)",
                 "Solusi":"Pengecekan kabel VGA/HDMI dan pembersihan slot GPU"},
                {"Bulan":"Maret",    "Unit":"Farmasi",
                 "Kendala":"Instalasi perangkat komputer baru",
                 "Solusi":"Setting awal OS, jaringan, dan aplikasi standar RS"},
                {"Bulan":"April",    "Unit":"Ruang SIMRS",
                 "Kendala":"Pengolahan data laporan jaspel (PDF ke CSV)",
                 "Solusi":"Konversi dan validasi data digital menggunakan aplikasi utilitas buatan sendiri"},
            ]
            with st.spinner("Menggabungkan data..."):
                try:
                    existing, fid_ex = load_json(service)
                    merged = data_awal + existing
                    save_json(service, merged, fid_ex)
                    upload_pdf(service, generate_pdf(merged, PDF_TITLE, HDR_TEXT), PDF_NAME)
                    st.success(f"✅ Berhasil! Total sekarang {len(merged)} entri. Data lama tetap aman.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Gagal: {e}")

# ══════════════════════════════════════════════════════════════
# TAB 3 — UPLOAD SCREENSHOT WA
# ══════════════════════════════════════════════════════════════
with tab3:
    st.subheader("📸 Upload Screenshot WhatsApp")
    st.caption("SS WA masuk ke folder bulan yang belum ada — folder lama (Januari–April) dilewati otomatis.")

    # Refresh state untuk folder
    if "ss_folders_refreshed" not in st.session_state:
        st.session_state.ss_folders_refreshed = False

    # Tombol refresh manual
    col_refresh, _ = st.columns([1, 3])
    with col_refresh:
        if st.button("🔄 Cek Folder Drive"):
            st.session_state.ss_folders_refreshed = True
            st.rerun()

    # Load info folder dari Drive
    with st.spinner("Mengecek folder bulan di Drive..."):
        try:
            existing_folders = get_existing_month_folders(service)
        except Exception as e:
            st.error(f"❌ Gagal baca folder Drive: {e}")
            existing_folders = {}

    next_months = get_next_months(existing_folders)

    # Info status folder
    with st.expander("📁 Status Folder Bulan di Drive", expanded=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**✅ Sudah Ada:**")
            if existing_folders:
                for b in BULAN_URUT:
                    if b in existing_folders:
                        st.markdown(f"- {b}")
            else:
                st.caption("(belum ada folder bulan)")
        with col_b:
            st.markdown("**📂 Belum Ada (bisa upload):**")
            if next_months:
                for b in next_months:
                    st.markdown(f"- {b}")
            else:
                st.success("Semua bulan sudah ada foldernya!")

    st.divider()

    if not next_months:
        st.info("✅ Semua bulan sudah punya folder. Tidak ada folder baru yang perlu dibuat.")
    else:
        # Form upload SS
        with st.form("form_upload_ss"):
            st.markdown("#### Upload SS ke Bulan Baru")

            # Hanya tampilkan bulan yang belum ada foldernya
            bulan_ss = st.selectbox(
                "Pilih Bulan Tujuan",
                next_months,
                help="Hanya bulan yang belum punya folder ditampilkan"
            )
            unit_ss = st.text_input(
                "Unit / Lokasi",
                placeholder="Contoh: IGD, Farmasi, Kasir..."
            )
            keterangan_ss = st.text_input(
                "Keterangan (opsional)",
                placeholder="Contoh: koordinasi BPJS, laporan breakout..."
            )
            files_ss = st.file_uploader(
                "Upload Screenshot WA",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
                help="Bisa upload lebih dari 1 file sekaligus"
            )

            submit_ss = st.form_submit_button("📤 Upload ke Drive", type="primary")

        if submit_ss:
            if not unit_ss:
                st.warning("⚠️ Isi Unit / Lokasi dulu.")
            elif not files_ss:
                st.warning("⚠️ Pilih minimal 1 file screenshot.")
            else:
                with st.spinner(f"Membuat/mengecek folder '{bulan_ss}' dan upload..."):
                    try:
                        folder_id = get_or_create_folder(service, bulan_ss)
                        berhasil = 0
                        for idx, ss in enumerate(files_ss, start=1):
                            ext = ss.name.rsplit(".", 1)[-1].lower()
                            ket_part = f"_{keterangan_ss.replace(' ','_')}" if keterangan_ss else ""
                            nama_file = f"SS_{unit_ss.replace(' ','_')}_{bulan_ss}{ket_part}_{idx}.{ext}"
                            upload_ss_to_folder(service, ss, folder_id, nama_file)
                            berhasil += 1
                        st.success(
                            f"✅ {berhasil} file berhasil diupload ke folder **{bulan_ss}** di Drive!\n\n"
                            f"📁 Nama folder: `{bulan_ss}` | 🗂️ Unit: `{unit_ss}`"
                        )
                        st.balloons()
                        # Reset state refresh supaya folder baru ke-detect
                        st.session_state.ss_folders_refreshed = False
                    except Exception as e:
                        st.error(f"❌ Gagal upload: {e}")

    # ── Upload SS ke folder yang sudah ada ───────────────────
    st.divider()
    with st.expander("➕ Upload SS ke Folder yang Sudah Ada"):
        st.caption("Kalau mau nambahin SS ke folder bulan yang sudah ada.")
        with st.form("form_upload_ss_existing"):
            bulan_exist = st.selectbox(
                "Pilih Bulan",
                list(existing_folders.keys()) if existing_folders else ["(tidak ada)"],
                help="Folder bulan yang sudah ada di Drive"
            )
            unit_ex = st.text_input("Unit / Lokasi", key="unit_exist")
            ket_ex  = st.text_input("Keterangan (opsional)", key="ket_exist")
            files_ex = st.file_uploader(
                "Upload Screenshot WA",
                type=["png","jpg","jpeg","webp"],
                accept_multiple_files=True,
                key="files_exist"
            )
            submit_ex = st.form_submit_button("📤 Upload ke Folder Ini")

        if submit_ex:
            if not existing_folders:
                st.warning("⚠️ Tidak ada folder yang bisa dipilih.")
            elif not unit_ex:
                st.warning("⚠️ Isi Unit / Lokasi dulu.")
            elif not files_ex:
                st.warning("⚠️ Pilih minimal 1 file screenshot.")
            else:
                with st.spinner(f"Upload ke folder '{bulan_exist}'..."):
                    try:
                        folder_id = existing_folders[bulan_exist]
                        berhasil = 0
                        for idx, ss in enumerate(files_ex, start=1):
                            ext = ss.name.rsplit(".", 1)[-1].lower()
                            ket_part = f"_{ket_ex.replace(' ','_')}" if ket_ex else ""
                            nama_file = f"SS_{unit_ex.replace(' ','_')}_{bulan_exist}{ket_part}_{idx}.{ext}"
                            upload_ss_to_folder(service, ss, folder_id, nama_file)
                            berhasil += 1
                        st.success(f"✅ {berhasil} file diupload ke folder **{bulan_exist}**!")
                    except Exception as e:
                        st.error(f"❌ Gagal upload: {e}")
