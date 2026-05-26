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
PDF_NAME  = "Laporan_IT_Triwulan_1_Isfan.pdf"
PDF_TITLE = "Laporan IT Triwulan I - Isfan"
JSON_NAME = "laporan_db.json"

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
        # Auto-create file JSON kosong di Drive
        empty = json.dumps([], ensure_ascii=False).encode("utf-8")
        media = MediaIoBaseUpload(io.BytesIO(empty), mimetype="application/json", resumable=False)
        f = service.files().create(
            body={"name": JSON_NAME, "parents": [FOLDER_ID]},
            media_body=media, fields="id"
        ).execute()
        return [], f["id"]
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
    b = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(b), mimetype="application/json", resumable=False)
    if not fid:
        # Auto-create kalau fid tidak diketahui
        service.files().create(
            body={"name": JSON_NAME, "parents": [FOLDER_ID]},
            media_body=media
        ).execute()
    else:
        service.files().update(fileId=fid, media_body=media).execute()

def upload_pdf(service, pdf_buffer):
    fid = get_file_id(service, PDF_NAME)
    media = MediaIoBaseUpload(pdf_buffer, mimetype="application/pdf", resumable=False)
    if not fid:
        # Auto-create PDF pertama kali
        service.files().create(
            body={"name": PDF_NAME, "parents": [FOLDER_ID]},
            media_body=media
        ).execute()
    else:
        service.files().update(fileId=fid, media_body=media).execute()

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

# ── Dekorasi halaman PDF ──────────────────────────────────────
def add_page_decorations(canvas, doc):
    canvas.saveState()
    W, H = A4
    canvas.setFillColor(C_HEADER)
    canvas.rect(0, H - 1.2*cm, W, 1.2*cm, fill=1, stroke=0)
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, H - 1.42*cm, W, 0.22*cm, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(1.5*cm, H - 0.82*cm, "LAPORAN IT TRIWULAN I")
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

# ── PDF Generator ─────────────────────────────────────────────
def generate_pdf(all_data):
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4,
                          rightMargin=1.5*cm, leftMargin=1.5*cm,
                          topMargin=3.0*cm, bottomMargin=1.8*cm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="main", frames=frame,
                                       onPage=add_page_decorations)])

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
                Paragraph("Laporan IT Triwulan I", s_judul),
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
st.title("🖥️ IT Log Automation")
st.caption("Input laporan kendala IT dan simpan otomatis ke Google Drive")

service = get_drive_service()

# ── Session state untuk edit ──────────────────────────────────
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

tab1, tab2 = st.tabs(["📝 Input Laporan", "🗂️ Lihat, Edit & Hapus Data"])

# ══════════════════════════════════════════════════════════════
# TAB 1 — CREATE
# ══════════════════════════════════════════════════════════════
with tab1:
    with st.form("form_laporan"):
        bulan   = st.selectbox("Bulan", [
            "Januari","Februari","Maret","April","Mei","Juni",
            "Juli","Agustus","September","Oktober","November","Desember"])
        unit    = st.text_input("Lokasi / Unit")
        kendala = st.text_area("Jenis Kendala / Pekerjaan")
        solusi  = st.text_area("Tindakan / Solusi")
        ss_file = st.file_uploader("Upload Screenshot WA (opsional)",
                                   type=["png","jpg","jpeg"])
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
            show_pdf_preview(generate_pdf(preview))

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
                    upload_pdf(service, generate_pdf(data))
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
            show_pdf_preview(generate_pdf(data))

        st.divider()

        BULAN_OPTIONS = [
            "Januari","Februari","Maret","April","Mei","Juni",
            "Juli","Agustus","September","Oktober","November","Desember"
        ]

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
                                    upload_pdf(service, generate_pdf(data))
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
                            upload_pdf(service, generate_pdf(new_data))
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
                    upload_pdf(service, generate_pdf(merged))
                    st.success(f"✅ Berhasil! Total sekarang {len(merged)} entri. Data lama tetap aman.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Gagal: {e}")
