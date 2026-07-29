import streamlit as st
import requests

# ══════════════════════════════════════════════════════════════
# KONFIGURASI API BACKEND (FastAPI - Replit)
# ══════════════════════════════════════════════════════════════
# Base URL diambil dari link yang kamu berikan (tanpa "/docs" di belakang,
# karena "/docs" itu halaman Swagger UI, bukan endpoint API).
API_BASE_URL = "https://f1676d66-2903-4e7d-adb1-7a2c0c0c53fb-00-2b4ce73ugrqn0.sisko.replit.dev"
API_ENDPOINT = f"{API_BASE_URL}/generate-report"

TRIWULAN_OPTIONS = {
    "Triwulan 1 (Jan–Mar)": "tw1",
    "Triwulan 2 (Apr–Jun)": "tw2",
    "Triwulan Final / Tahunan": "final",
}

# ══════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════
st.set_page_config(page_title="Laporan IT - Bukti EKIN", page_icon="🖥️", layout="centered")

st.title("🖥️ Buat Laporan Pendukung Bukti EKIN")
st.caption("Upload data Excel & screenshot WA — laporan PDF akan dibuat otomatis oleh server "
           "dan disimpan ke Google Drive.")

st.divider()

# ── Pilih Triwulan ───────────────────────────────────────────
selected_triwulan_label = st.selectbox(
    "📅 Pilih Periode Triwulan",
    options=list(TRIWULAN_OPTIONS.keys()),
    help="Pilih periode yang sesuai dengan eKinerja — Triwulan 1, Triwulan 2, atau Final/Tahunan",
)
triwulan_value = TRIWULAN_OPTIONS[selected_triwulan_label]

st.divider()

# ── Upload File ───────────────────────────────────────────────
st.subheader("📂 Upload Data")

excel_file = st.file_uploader(
    "Upload File Excel (.xlsx)",
    type=["xlsx"],
    accept_multiple_files=False,
    help="File Excel berisi data laporan kendala IT.",
)

screenshots = st.file_uploader(
    "Upload Screenshot WA (opsional, boleh lebih dari satu)",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
    help="Screenshot bukti percakapan WhatsApp, bersifat opsional.",
)

if excel_file:
    st.caption(f"✅ Excel terpilih: `{excel_file.name}`")
if screenshots:
    st.caption(f"✅ {len(screenshots)} screenshot terpilih: " +
               ", ".join(f"`{f.name}`" for f in screenshots))

st.divider()

# ── Tombol Proses ────────────────────────────────────────────
proses_btn = st.button("🚀 Proses & Generate Laporan", type="primary", use_container_width=True)

if proses_btn:
    if not excel_file:
        st.warning("⚠️ Mohon upload file Excel (.xlsx) terlebih dahulu.")
    else:
        with st.spinner("⏳ Mengirim data ke server dan membuat laporan..."):
            try:
                # multipart/form-data: excel_file (single) + screenshots (multiple, optional)
                files = [
                    ("excel_file", (
                        excel_file.name,
                        excel_file.getvalue(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )),
                ]
                if screenshots:
                    for ss in screenshots:
                        files.append(("screenshots", (ss.name, ss.getvalue(), ss.type or "image/jpeg")))

                data = {"triwulan": triwulan_value}

                response = requests.post(API_ENDPOINT, files=files, data=data, timeout=120)

                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ Laporan berhasil dibuat!")
                    st.balloons()

                    web_view_link = result.get("webViewLink")
                    if web_view_link:
                        st.markdown("### 📄 Laporan PDF siap dibuka:")
                        st.link_button("📂 Buka PDF di Google Drive", web_view_link, use_container_width=True)
                    else:
                        st.info("Laporan berhasil diproses, tetapi field `webViewLink` tidak "
                                "ditemukan pada respons server. Berikut respons lengkapnya:")
                        st.json(result)
                else:
                    try:
                        error_detail = response.json().get("detail", response.text)
                    except ValueError:
                        error_detail = response.text
                    st.error(f"❌ Gagal memproses laporan (Status {response.status_code}): {error_detail}")

            except requests.exceptions.ConnectionError:
                st.error(
                    "❌ Gagal terhubung ke server backend. Pastikan server Replit sedang aktif "
                    "(tidak dalam mode sleep) dan URL API sudah benar."
                )
            except requests.exceptions.Timeout:
                st.error("❌ Permintaan ke server melebihi batas waktu (timeout). Coba lagi beberapa saat.")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Terjadi kesalahan saat menghubungi server: {e}")
            except Exception as e:
                st.error(f"❌ Terjadi kesalahan tak terduga: {e}")
