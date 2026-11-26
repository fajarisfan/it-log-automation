import streamlit as st
import json
import io
import base64
import re
import hmac
import hashlib
import zipfile
import secrets as _secrets
from urllib.parse import quote
from xml.sax.saxutils import escape as _xml_escape
from datetime import datetime, timedelta, timezone, date

def bersih_pdf(t):
    """Buang emoji/simbol yang tidak ada di font PDF (Helvetica), supaya tidak jadi kotak hitam."""
    return str(t).encode("cp1252", "ignore").decode("cp1252")

def xml_escape(t):
    return _xml_escape(bersih_pdf(t))
from collections import Counter
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (Table, TableStyle, Paragraph, Spacer,
                                HRFlowable, BaseDocTemplate, PageTemplate, Frame, KeepTogether, PageBreak, Flowable,
                                Image as RLImage)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

st.set_page_config(page_title="Laporan IT SIRS", page_icon="🖥️", layout="centered")
st.markdown("""<style>
.block-container{max-width:920px;padding-top:1.4rem;padding-bottom:5rem;}
@media (max-width:640px){.block-container{padding-left:.9rem;padding-right:.9rem;}}
footer{visibility:hidden;}
hr{margin:1rem 0!important;}
h1{font-size:1.7rem!important;}
h4,h5{margin-top:.6rem!important;}
div[data-testid="stVerticalBlockBorderWrapper"]{border-radius:14px;}
div[data-testid="stExpander"]{border-radius:12px;}
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button{border-radius:10px;font-weight:600;}
div[data-baseweb="input"],div[data-baseweb="select"]>div,div[data-baseweb="textarea"]{border-radius:10px!important;}
div[data-baseweb="tab-list"]{gap:.25rem;}
button[data-baseweb="tab"]{padding:.65rem .9rem;font-weight:600;}
.hero{background:linear-gradient(135deg,#1B5276,#2E86C1);border-bottom:4px solid #F39C12;
      border-radius:14px;padding:1.1rem 1.25rem;margin:0 0 1rem 0;}
.hero-t{color:#fff;font-size:1.3rem;font-weight:700;line-height:1.3;}
.hero-s{color:#D6EAF8;font-size:.9rem;margin-top:.25rem;}
</style>""", unsafe_allow_html=True)

LOGO_KOTA_CILEGON_B64 = "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6afzyiuvMGHCBPx+P+PHj2fhwoVcd911vP3228yePZszzzyTyspKzj77bIqKinjqqae4/vrrmTRpEieeeCIulvHUuQ4WksnJBCszaXK9lN9R4SwOC2eT1Jp1roMPuCyvkK5+PzGtSGrN+TkF9A+EWO64xLTivJwC+gSCzE8nWZBJ09znY1Q4m0PD2cTVFiy9X2ST0pqrSjezqH0CXb1z7uN6M1b7P4+V2O49hL39+r6aK668grnz5zL2X49TW1vLMceMYvKk9wB4/oUXKC4u5q233+bNN9/kqaeeIjc3l5dffplbb72VF154gaOOOqr+fvPmzeORRx7hxhtvpHv37mQyGR577DGuuuqqenD+UHNdl1AoRLdu3cjPz2fAgAFcdNFFDBgwgGeeeYaLLrqImpoannjiCTKZTL1tGwqFsG2bNWvW8Nlnn3HggQcyZswYevbsyZNPPsk+++zDypUreeedd9Ba06dPHyZOnMjhhx9O7969efjhh7Esi/fee4/PPvuMUChES08l/im2jQ28S/fF0dQ9V2vNZRdfwqjDR5FIJHjuuec4/fTTWblyJZlMBtuyWLJkCcOHD2fkyJGMHz+e888/H8uy8Pl8FBcXM3DgQO677z4eeughTjvtNFatWoXrurRv357bb7+d66+/nlgsxuDBgxk7dixjx44lHo/z/PPPc8stt1BVVUXv3r158MEHueWWW3Bdl/bt2zNkyBCuvPJKKioqCAaDrFu3jtdeew2tNT6fj0AgwOrVqznuuOMYMWIEI0eOpLy8HJ/PR8+ePZk9ezbfffcdffr0wefz7dR7+70Qzwf/+Q26+yD+8eBD9O3bt/7fPp+PFStWkJeXRzgcxufzoZTivvvuY8aMGaxcuZLc3FyOP/54Xn75ZW644Qb69evHmWeeyapVq+jQoQM33ngjbdu2ZfDgwaxatQrbtjn88MN59dVXCYVCPProowwYMIAWLVowbtw4xowZgxACj830k9n5n1z5X7s4jks4HGbMmDEsWLCAeDzOhRdeSHFxMVJKXnrpJf70pz8RiUQYOnQoX3zxBX379q2//r777mPo0KEcddRR9e/w3nvvkZWVxTHHHPMj3k6RSqW45ZZbGD16NMcee2z9z999911Gjx5NcXEx2dnZTJgwgY8//pjbbruNSZMm4bouL7zwArNmzSKS5cfq1RQx+gAEoF75HnV9O9w7PkX7JMIu5NTTT+fTTz+lqKiIli1bEggEaNmyJS1atEBKic/nIx6PY9s2hm12AA0NDSil8Pv9KKXo0qULtm0DZrM744wzePrpp3Fdl8rKSiZMmMBnn33Gddddx+GHH84rr7zC2WefjRAC13XJz883Q7gT45fWmoyj+eyzz3jppZe49dZbeeCBB7Asi8ceewyA+fPnc84552DbNv369ePCCy+koKCA3r1789///pcaM4xN4zZ/j+x08v8B/f15+qmn2XfAvqxfv5799tuPJk2acOONNxIIBLj99tu56aab8Pl8KKVQSuG6LkopzjnnHE488UQmT57MoYceypw5czj99NOpqqrC7/fzxRdfkEgkePvttzn88MM5/PDDufnmmzn11FMpKSkhGAxy6aWXctttt1FeXo5lWbiuizT5sTuV9b97192w5n9/pO457e0bVmUyLYqLh4cF0T8W5P/n2muu4fTTT6/X8K666ipWrlxJcXExlmUxYcIEbrvtNmzbJhKJkJ2dTSgUorKykpYtW1JSUkLv3r2xbZvttrO5+eab6datW3255J+j+f1+Nm7cyM0338wXX3zByy+/zJAhQ+o90FprNmzYQFZWFt27d2fhwoWcfPLJKKV46623uPfee2nWrBn//Oc/KSkp4bnnn6eiogI3mSD3wD6o4b3Q2SGz6I/oiL77I+TXqxD5Yc59+BFKSkvo3r07kUiE5557jokTJ3LQQQeRSqWwLIv8/Hzuu+8++vfvTyAQIBaL0b17dz744APuuOMOhBAMHjy4/jXmzJljvK2e2n7HHXdQVVXF1VdfjRACn8+Hz+err1/2Y8wB4fH/g8EgAwYM4PPPP6dt27acccYZ5OXlMX36dN5++22+/PJLzjrrLDp27Mj8+fMJh8Ok02meeOIJ9t57b9avX0/R9O+QvQ8gEAgwZ+pXTF++kC5dunDdddfRtWtX+vTpw/z58/niiy8YOXIkV199NU8++SQ5OTkAnHrqqdxxxx307NmT7OxszjzzTNasWcPUqVPZf//9eeGFF9Bao5RiwYIFKKW48MIL2XfffTn55JNp06YN1dXVvP7660gpdwrWzX/o92R0b0e73Y+KxtT7NLV/z559N6x/56N58xf92F/V1tZy00038d5777F48WLGjh3LaaedRnl5Obm5udxyyy18++23nHnmmfz5z39m+fLlBAIBhg0bxqWXXsq6devo1asXl112GXfddRcvvPACl1xyCa+//vovCtZgMEh2djbjxo2jubn5h3+7rksoFKJ58+Zcc801nHnmmQghuPTSS7nggguwLIt4PM5///tfjjjiCKqrq2nevDk3/PVvtHrmE1zXxT6iM+qw3qgX50I0jTj5ANy7vsS9fQquv7BeY3jyyScRQpCXl0e3bt146623+PjjjxkxYgTz58/nmWeeYfTo0axZswatNU2bNqW8vJxzzz2XaDTKbbfdRjKZ5JVXXuH000/npZde4rLLLqt3bD388MPce++9rF+/nsWLF+O6LmlvI854wN4Z77vWmj59+hAKhbj99tuprq5m2bJlzJ07lzFjxrDHHntwzTXXMHz4cO69914+/PBDRo8eTSQSoUuXLoRCIa644gpS369Ej90J36x1+Hw+TjzxRLTWDB8+nMWLF9OuXTsOPvhgxo8fT3Z2Nn6/n6ysLGKxmDmlTwjOOussXnrpJd544w1OOukkfvOb35BIJNh7771p2rQpsViMfv36MWvWLNavX8/nn39OXl4er7zyCvvssw9XX301e++9NzU1NT8q462R/f/fH8/r/391a+7Xzz8f4NdfL3xN9ey978j+/Y9Z98UX836M19KyLMrLy+nUqRPDhg0jlUoxatQonn/+eW666SYCgQCffPIJb7/9NrZt07dvXyZNmsTRRx9Nnz596NmzJ5s2bSKRSPD2228zaNAgsrKyWLp0KbZtb+Fl/blbNptlzJgxWJbF0qVLaWpqukU2XCAQ4IQTTmD16tV8++239O7dG9u2adq0KdOmTSOZTPL5559z0003ceONNzJy5EieefoZ8p54D/v8Aag2uYjHPsWdXIwI+nG/WA5X7w+rKnEXlyE/W44a3omjzz2b41auZPLkybRo0YL777+fjRs3cvTRR9OpUyduvfVWLr30Ul588UU6duxIPB4nnU6TSCR46aWX0FqTl5dHZWUl+fn5DBs2DK01nTp1Yvjw4eTn51NYWEhlZSWdOnXi5JNP5rzzzqOsrIzWrVszb948bNumvLx8q4yvnXls2+att97iwAMPJJPJ0KtXLy655BJSqRSzZ89GKYVh95q/m2oJ2cD8jbhvrkU8+DUi5k9w4tln8eqrr3LwwQeTlZVFNBrdQmqHw2EuvvhihBCUlpYSCoWQUmLbNm3b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"

# --- KONFIGURASI ---
FOLDER_ID = "1tpSWDgfMEac2ktTrUNMr7u7Y5V7tAZwa"
TRIWULAN_CONFIG = {
    "Triwulan 1 (Jan–Mar)": {
        "pdf_name":  "Laporan_IT_Triwulan_1_Isfan.pdf",
        "pdf_title": "Laporan IT Triwulan I",
        "header":    "LAPORAN IT TRIWULAN I",
        "json_name": "laporan_db.json",
        "bulan":     ["Januari", "Februari", "Maret"],
        "romawi":    "I",
    },
    "Triwulan 2 (Apr–Jun)": {
        "pdf_name":  "Laporan_IT_Triwulan_2_Isfan.pdf",
        "pdf_title": "Laporan IT Triwulan II",
        "header":    "LAPORAN IT TRIWULAN II",
        "json_name": "laporan_db_tw2.json",
        "bulan":     ["April", "Mei", "Juni"],
        "romawi":    "II",
    },
    "Triwulan 3 (Jul–Sep)": {
        "pdf_name":  "Laporan_IT_Triwulan_3_Isfan.pdf",
        "pdf_title": "Laporan IT Triwulan III",
        "header":    "LAPORAN IT TRIWULAN III",
        "json_name": "laporan_db_tw3.json",
        "bulan":     ["Juli", "Agustus", "September"],
        "romawi":    "III",
    },
    "Triwulan 4 (Okt–Des)": {
        "pdf_name":  "Laporan_IT_Triwulan_4_Isfan.pdf",
        "pdf_title": "Laporan IT Triwulan IV",
        "header":    "LAPORAN IT TRIWULAN IV",
        "json_name": "laporan_db_tw4.json",
        "bulan":     ["Oktober", "November", "Desember"],
        "romawi":    "IV",
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

def load_json(service, json_name="laporan_db.json"):
    fid = get_file_id(service, json_name)
    if not fid:
        st.error(f"❌ File `{json_name}` tidak ditemukan. Pastikan file sudah ada di folder Drive dan folder sudah di-share ke service account sebagai Editor.")
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
    data = json.loads(raw)
    if isinstance(data, list):                      # jam lama "09.22" -> "09:22"
        for e_ in data:
            if isinstance(e_, dict):
                for k_ in ("Mulai_Jam", "Selesai_Jam"):
                    if e_.get(k_):
                        e_[k_] = _norm_jam(e_[k_])
                if e_.get("TTD_Waktu"):
                    e_["TTD_Waktu"] = _norm_waktu(e_["TTD_Waktu"])
    return data, fid

def save_json(service, data, fid=None):
    if not fid:
        st.error("❌ File `laporan_db.json` tidak ditemukan. Cek folder Drive.")
        st.stop()
    b = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(b), mimetype="application/json", resumable=False)
    service.files().update(fileId=fid, media_body=media).execute()

def upload_pdf(service, pdf_buffer, pdf_name=None):
    target = pdf_name or "Laporan_IT_Triwulan_1_Isfan.pdf"
    fid = get_file_id(service, target)
    if not fid:
        st.error(
            f"❌ File `{target}` belum ada di folder Drive.\n\n"
            f"Upload dulu file PDF kosong dengan nama tersebut ke folder Drive, "
            f"lalu refresh app ini."
        )
        st.stop()
    media = MediaIoBaseUpload(pdf_buffer, mimetype="application/pdf", resumable=False)
    service.files().update(fileId=fid, media_body=media).execute()

def get_or_create_folder(service, folder_name, parent_id=FOLDER_ID):
    """Cari folder di Drive; kalau belum ada, buat otomatis."""
    safe_name = re.sub(r"[\\/:*?\"<>|']", "_", str(folder_name or "Lainnya")).strip() or "Lainnya"
    fid = get_file_id(service, safe_name, parent_id)
    if fid:
        return fid
    meta = {
        "name": safe_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    res = service.files().create(body=meta, fields="id").execute()
    return res["id"]

def simpan_bukti_ttd_png(service, entry, png_bytes):
    """Simpan gambar TTD (.png) ke folder bulan (Oktober/November/Desember, dst.)."""
    bln = bulan_entri(entry)
    if not bln or bln == "-":
        bln = "Lainnya"
    folder_id = get_or_create_folder(service, bln, FOLDER_ID)
    tgl = re.sub(r"[\\/:*?\"<>|']", "-", str(entry.get("Tanggal") or "tanpa_tgl")).strip()
    unit = re.sub(r"[\\/:*?\"<>|']", "_", str(entry.get("Unit") or "Unit")).strip()
    nama = re.sub(r"[\\/:*?\"<>|']", "_", str(entry.get("Pelapor") or "User")).strip()
    fname = f"TTD_{tgl}_{unit}_{nama}.png"
    fid = get_file_id(service, fname, folder_id)
    media = MediaIoBaseUpload(io.BytesIO(png_bytes), mimetype="image/png", resumable=False)
    if fid:
        service.files().update(fileId=fid, media_body=media).execute()
    else:
        meta = {"name": fname, "parents": [folder_id]}
        service.files().create(body=meta, media_body=media, fields="id").execute()

TTD_JSON = "ttd_config.json"

def load_ttd(service):
    """Baca ttd_config.json (ttd IT + Kanit permanen). Return (dict, file_id|None)."""
    fid = get_file_id(service, TTD_JSON)
    if not fid:
        return {}, None
    req = service.files().get_media(fileId=fid)
    fh  = io.BytesIO()
    dl  = MediaIoBaseDownload(fh, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    raw = fh.getvalue().decode("utf-8").strip()
    return (json.loads(raw) if raw else {}), fid

def _fit_sig(im, max_w, max_side=None):
    """Kecilkan gambar ttd: lebar <= max_w dan sisi terpanjang <= max_side (tampil di form cuma ±1,5 cm)."""
    from PIL import Image as PILImage
    sc = 1.0
    if im.width > max_w:
        sc = min(sc, max_w / im.width)
    if max_side and max(im.size) > max_side:
        sc = min(sc, max_side / max(im.size))
    if sc < 1.0:
        im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), PILImage.LANCZOS)
    return im

def clean_signature(im, max_w, max_side=None):
    """Foto/scan ttd -> hanya tinta (latar transparan), dicrop rapat ke GUGUSAN TINTA UTAMA.
    Bintik, noda kertas, dan benda di tepi foto (meja/keranjang) dibuang."""
    from PIL import Image as PILImage, ImageFilter, ImageOps
    im = ImageOps.exif_transpose(im).convert("RGBA")
    if im.getchannel("A").getextrema()[0] < 255:          # sudah transparan (PNG) -> biarkan
        return _fit_sig(im, max_w, max_side)
    try:
        import numpy as np
    except ImportError:
        return _fit_sig(im, max_w, max_side)

    foto_besar = im.width >= 700          # foto/scan besar; gambar kecil (kanvas jari) diproses lebih lembut
    # kerja di resolusi menengah supaya detail ttd kecil tidak hilang
    work_w = 1000
    if im.width > work_w:
        im = im.resize((work_w, max(1, int(im.height * work_w / im.width))))
    rgb  = im.convert("RGB")
    gray = rgb.convert("L")
    # perkiraan terang kertas per area (dihitung di versi kecil biar cepat)
    sw, sh = max(1, gray.width // 4), max(1, gray.height // 4)
    small = gray.resize((sw, sh))
    k = max(3, (sw // 18) | 1)
    bg_s = small.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.GaussianBlur(max(1, sw // 30)))
    bg = bg_s.resize(gray.size, PILImage.BILINEAR)
    g = np.asarray(gray, dtype=np.float32)
    b = np.maximum(np.asarray(bg, dtype=np.float32), 1.0)
    ratio = g / b
    alpha = np.clip((0.78 - ratio) / (0.78 - 0.48), 0.0, 1.0)   # hanya yang jelas gelap = tinta
    # buka-morfologi 3x3: titik-titik tunggal (pola layar monitor, bintik kertas) hilang, goresan tetap
    if foto_besar:
        a8 = PILImage.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
        alpha = np.asarray(a8, dtype=np.float32) / 255.0

    # --- pilih gugusan tinta utama (grid kasar + flood fill) ---
    cell = 10
    H, W = alpha.shape
    gh, gw = H // cell, W // cell
    if gh < 3 or gw < 3:
        keep = np.ones_like(alpha, dtype=bool)
    else:
        ink = (alpha[:gh*cell, :gw*cell] > 0.5).reshape(gh, cell, gw, cell).sum(axis=(1, 3))
        occ = ink >= 3
        dil = occ.copy()
        for _ in range(2):                                   # jembatani celah antar goresan
            d2 = dil.copy()
            d2[1:, :] |= dil[:-1, :]; d2[:-1, :] |= dil[1:, :]
            d2[:, 1:] |= dil[:, :-1]; d2[:, :-1] |= dil[:, 1:]
            d2[1:, 1:] |= dil[:-1, :-1]; d2[:-1, :-1] |= dil[1:, 1:]
            d2[1:, :-1] |= dil[:-1, 1:]; d2[:-1, 1:] |= dil[1:, :-1]
            dil = d2
        lab = np.zeros((gh, gw), dtype=np.int32)
        comps, nid = [], 0
        for sy in range(gh):
            for sx in range(gw):
                if dil[sy, sx] and lab[sy, sx] == 0:
                    nid += 1
                    stack = [(sy, sx)]; lab[sy, sx] = nid; cells = []
                    while stack:
                        y, x = stack.pop(); cells.append((y, x))
                        for dy in (-1, 0, 1):
                            for dx in (-1, 0, 1):
                                ny, nx = y + dy, x + dx
                                if 0 <= ny < gh and 0 <= nx < gw and dil[ny, nx] and lab[ny, nx] == 0:
                                    lab[ny, nx] = nid; stack.append((ny, nx))
                    comps.append(cells)
        best, best_border = None, None
        for cells in comps:
            score = sum(int(ink[y, x]) for y, x in cells)
            touches = any(y in (0, gh-1) or x in (0, gw-1) for y, x in cells)
            if not touches and (best is None or score > best[0]):
                best = (score, cells)
            if best_border is None or score > best_border[0]:
                best_border = (score, cells)
        chosen = (best or best_border)
        keep = np.zeros_like(alpha, dtype=bool)
        if chosen:
            for y, x in chosen[1]:
                keep[y*cell:(y+1)*cell, x*cell:(x+1)*cell] = True
        else:
            keep[:] = True
    alpha = alpha * keep
    alpha[alpha < (0.35 if foto_besar else 0.1)] = 0.0   # buang sisa samar

    arr = np.asarray(rgb, dtype=np.float32) * (1.0 - 0.25 * alpha[..., None])
    arr[alpha == 0] = 0.0
    out = PILImage.fromarray(np.dstack([arr, alpha * 255.0]).astype(np.uint8), "RGBA")
    box = out.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox()
    if box:
        pad = 6
        out = out.crop((max(0, box[0]-pad), max(0, box[1]-pad),
                        min(out.width, box[2]+pad), min(out.height, box[3]+pad)))
    return _fit_sig(out, max_w, max_side)

def img_to_b64(uploaded, max_w=700, max_side=480):
    """TTD permanen: bersihkan latar, simpan sebagai PNG transparan (base64)."""
    from PIL import Image as PILImage
    im = clean_signature(PILImage.open(io.BytesIO(uploaded.getvalue())), max_w, max_side)
    out = io.BytesIO()
    im.save(out, "PNG", optimize=True)
    return base64.b64encode(out.getvalue()).decode("utf-8")

def _isi_digest(e):
    """Sidik isi laporan (tanggal, unit, kendala, tindakan, nama penerima). Dipakai untuk mendeteksi
    perubahan isi setelah tanda tangan masuk."""
    bagian = [str(e.get(k, "") or "").strip() for k in ("Tanggal", "Unit", "Kendala", "Solusi", "Pelapor")]
    return hashlib.sha256("|".join(bagian).encode("utf-8")).hexdigest()[:16]

def check_missing_files(service):
    """Return list file (PDF/JSON) yang belum ada di Drive."""
    missing = []
    for nama_triwulan, cfg in TRIWULAN_CONFIG.items():
        if not get_file_id(service, cfg["pdf_name"]):
            missing.append(f"PDF: `{cfg['pdf_name']}` ({nama_triwulan})")
        if not get_file_id(service, cfg["json_name"]):
            missing.append(f"JSON: `{cfg['json_name']}` ({nama_triwulan})")
    return missing




# ── Tanggal otomatis (WIB) ───────────────────────────────────
WIB = timezone(timedelta(hours=7))
BULAN_ID = ["Januari","Februari","Maret","April","Mei","Juni","Juli",
            "Agustus","September","Oktober","November","Desember"]

def tanggal_hari_ini():
    n = datetime.now(WIB)
    return f"{n.day} {BULAN_ID[n.month-1]} {n.year}"


def tanggal_fmt(d):
    return f"{d.day} {BULAN_ID[d.month-1]} {d.year}"

def hari_ini_wib():
    return datetime.now(WIB).date()

def jam_sekarang():
    return datetime.now(WIB).strftime("%H:%M")

def parse_tanggal_id(txt):
    """'10 November 2026' / '10/11/2026' / '2026-11-10' -> date, atau None."""
    if not txt:
        return None
    t = str(txt).strip()
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", t)
    if m:
        for i, b in enumerate(BULAN_ID):
            if b.lower() == m.group(2).lower():
                try: return date(int(m.group(3)), i + 1, int(m.group(1)))
                except ValueError: return None
    m = re.search(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})", t)
    if m:
        y = int(m.group(3)); y = y + 2000 if y < 100 else y
        try: return date(y, int(m.group(2)), int(m.group(1)))
        except ValueError: return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        try: return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError: return None
    return None

def _jam_ke_menit(j):
    m = re.match(r"^\s*(\d{1,2})[.:](\d{2})\s*$", j or "")
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None

def _menit_ke_jam(mnt):
    mnt %= 1440
    return f"{mnt // 60:02d}:{mnt % 60:02d}"

def _norm_jam(j):
    """'9.05' / '09.05' -> '09:05'. Teks lain dibiarkan."""
    m = re.match(r"^\s*(\d{1,2})[.:](\d{2})\s*$", str(j or ""))
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else j

def _norm_waktu(w):
    """'19 November 2026 19.42' -> '19 November 2026 19:42'."""
    if not w:
        return w
    return re.sub(r"(\d{1,2})\.(\d{2})\s*$", lambda m: f"{int(m.group(1)):02d}:{m.group(2)}", str(w))

def bulan_entri(e):
    """Bulan sebuah entri: dari tanggalnya kalau ada, kalau tidak dari kolom Bulan."""
    d = parse_tanggal_id(e.get("Tanggal"))
    return BULAN_ID[d.month - 1] if d else (e.get("Bulan") or "-")

def _urut_key(e):
    d = parse_tanggal_id(e.get("Tanggal"))
    if d:
        return (d.year, d.month, d.day, _jam_ke_menit(e.get("Mulai_Jam")) or 0)
    b = e.get("Bulan")
    bln = BULAN_ID.index(b) + 1 if b in BULAN_ID else 13
    return (datetime.now(WIB).year, bln, 0, 0)           # tanpa tanggal: di awal bulannya

def urutkan(data):
    """Urutkan entri kronologis (tanggal + jam mulai). Stabil: urutan sama tetap seperti semula."""
    return sorted(data, key=_urut_key)

# ── Tebak peralatan & jenis pekerjaan dari teks kendala/solusi ──
_ALAT_RULES = [
    (r"\bprinter\b|cetak", "Printer"),
    (r"\bscanner\b", "Scanner"),
    (r"\bups\b", "UPS"),
    (r"\bcctv\b", "CCTV"),
    (r"switch|\bhub\b|jaringan|network|\blan\b|internet|router|mikrotik|\butp\b", "Perangkat Jaringan"),
    (r"access point|\bap\b|wifi|wi-fi|hotspot", "Access Point / WiFi"),
    (r"\bserver\b", "Server"),
    (r"laptop|notebook", "Laptop"),
    (r"\bpc\b|komputer|computer|\bcpu\b|monitor|keyboard|mouse|\bram\b|hardisk|harddisk|\bssd\b|\bpsu\b", "PC / Komputer"),
    (r"telepon|\bphone\b|pabx", "Telepon / PABX"),
    (r"proyektor|projector|\btv\b", "Proyektor / TV"),
]
_JENIS_RULES = [
    ("a", r"bersih|cleaning|\bclean\b|debu|kotor|blower"),
    ("b", r"install|instal|pasang|kabel|crimp|konektor|\bscan|ganti|colok|konfigurasi|setting|setup|driver|reset"),
    ("c", r"database|\bdb\b|mysql|\bsql\b|rdbms|backup|restore|query|oracle|postgres"),
    ("d", r"aplikasi|bridging|vclaim|modul|fitur|custom"),
    ("e", r"windows|\bos\b|booting|\bboot\b|bsod|blue screen|format|restart|\bhang\b|lemot|lambat|aktivasi|lisensi"),
]

def tebak_detail(kendala, solusi):
    k, sl = (kendala or "").lower(), (solusi or "").lower()
    alat = ""
    for teks in (k, sl):
        for pat, nama in _ALAT_RULES:
            if re.search(pat, teks):
                alat = nama
                break
        if alat:
            break
    gabung = k + " " + sl
    jenis = [huruf for huruf, pat in _JENIS_RULES if re.search(pat, gabung)]
    return {"Peralatan": alat, "Jenis": jenis}

# ── Parser teks laporan dari WhatsApp ────────────────────────
_WA_LABELS = [
    ("bulan",   r"bulan"),
    ("tanggal", r"tanggal|tgl"),
    ("pelapor", r"nama\s+pelapor|pelapor|user|penerima"),
    ("unit",    r"lokasi\s*/\s*unit|lokasi|unit|ruangan|ruang|tempat"),
    ("kendala", r"jenis\s+kendala(?:\s*/\s*pekerjaan)?|kendala|masalah|keluhan|pekerjaan|problem|laporan"),
    ("solusi",  r"tindakan\s*/\s*solusi|solusi|tindakan|penanganan|perbaikan|action"),
]
_WA_LABEL_RE = [(k, re.compile(r"^\s*(?:[-•\d.)]+\s*)?(?:%s)\s*[:=]\s*(.*)$" % pat, re.I))
                for k, pat in _WA_LABELS]
# ── Format pesan WhatsApp yang dikenali ──────────────────────
_T = r"(?P<h>\d{1,2})[.:](?P<mi>\d{2})(?:[.:]\d{2})?(?:\s?(?P<ap>[AaPp])\.?[Mm]\.?)?"
_D = r"(?P<d>\d{1,2})[/.\-](?P<mo>\d{1,2})[/.\-](?P<y>\d{2,4})"
_LRM = "\u200e\u200f\u202f"
_WA_MSG_RES = [
    # Android (salin pesan):  [09.10, 11/11/2026] Nama: pesan
    re.compile(rf"^[{_LRM}]*\[\s*{_T}\s*,\s*{_D}\s*\]\s*(?P<s>[^:]{{1,60}}?):\s*(?P<t>.*)$"),
    # iOS / varian:           [11/11/26 09.10.05] Nama: pesan
    re.compile(rf"^[{_LRM}]*\[\s*{_D}\s*,?\s*{_T}\s*\]\s*(?P<s>[^:]{{1,60}}?):\s*(?P<t>.*)$"),
    # Ekspor chat:            11/11/26 09.10 - Nama: pesan
    re.compile(rf"^[{_LRM}]*{_D}\s*,?\s*{_T}\s*[-–]\s*(?P<s>[^:]{{1,60}}?):\s*(?P<t>.*)$"),
]
_WA_NOISE = re.compile(
    r"^<?(media omitted|attached:.*|image omitted|video omitted|sticker omitted|gif omitted|"
    r"document omitted|audio omitted|this message was deleted|pesan ini dihapus|"
    r"you deleted this message)>?\s*$", re.I)

def _wa_msg_start(line):
    """Baris awal pesan WA -> {date, jam, sender, text}; None kalau bukan awal pesan."""
    line = line.strip()
    for rx in _WA_MSG_RES:
        m = rx.match(line)
        if not m:
            continue
        y = int(m.group("y")); y = y + 2000 if y < 100 else y
        h = int(m.group("h")); ap = (m.group("ap") or "").lower()
        if ap == "p" and h < 12: h += 12
        if ap == "a" and h == 12: h = 0
        try:
            d = date(y, int(m.group("mo")), int(m.group("d")))
        except ValueError:
            return None
        return {"date": d, "jam": f"{h:02d}:{m.group('mi')}",
                "sender": m.group("s").strip(), "text": m.group("t")}
    return None

def _wa_clean(t):
    t = re.sub(r"[*~`]", "", t)
    t = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", t)
    return " ".join(t.split())

def parse_wa_messages(text):
    """Pecah teks WA menjadi daftar pesan (baris lanjutan digabung ke pesan sebelumnya)."""
    msgs, cur = [], None
    for raw in text.replace("\r", "").split("\n"):
        st_ = _wa_msg_start(raw)
        if st_:
            cur = st_; msgs.append(cur)
        elif cur is not None and raw.strip():
            cur["text"] += " " + raw.strip()
    for m in msgs:
        m["text"] = _wa_clean(m["text"])
    return [m for m in msgs if m["text"] and not _WA_NOISE.match(m["text"])]

# ── Deteksi nama ruangan/unit dari teks bebas ────────────────
_UNIT_BUILTIN = [
    "IGD", "ICU", "ICU 1", "ICU 2", "NICU", "PICU", "HCU", "IBS", "VK", "Perina", "Nusa Indah",
    "MCU", "PPI", "BDRS", "CSSD", "K3", "Kepegawaian", "Penunjang", "Farmasi", "Gudang Farmasi",
    "Kasir", "Rekam Medis", "Laboratorium", "Radiologi", "Gizi", "Laundry", "Pendaftaran",
    "Keuangan", "IPSRS", "Hemodialisa", "Rehab Medik", "Kamar Operasi", "Poli Anak", "Poli Gigi",
    "Poli Bedah", "Poli Mata", "Poli THT", "Poli Jantung", "Poli Saraf", "Poli Penyakit Dalam",
    "Poli Kandungan",
]
_UNIT_STOP = set("""tidak tak ga gak nggak bisa tdk nya mohon minta tolong komputer pc printer internet
jaringan wifi simrs sim rs error mati lemot hang yang dan untuk sudah sdh belum kok kenapa ya dong bantu
bantuannya cek dari di ke ini itu ada sedang lagi pas saat udah koneksi konek lan jam menit pakai
gunakan periksa ganti perbaiki lihat install instal nyalakan hidupkan print ngeprint scan buka kabel
admin tim mas mbak pak bu dok dr""".split())

def _norm_unit_tok(w):
    if any(c.isdigit() for c in w) or w.isupper():
        return w.upper()
    return w.capitalize()

def detect_unit(text, known=None, heuristik=True):
    """Cari nama ruangan: daftar unit yang pernah dipakai + daftar bawaan, lalu tebakan 'di/dari <ruang>'."""
    t = text or ""
    cands, seen = [], set()
    for c in list(known or []) + _UNIT_BUILTIN:
        c = (c or "").strip()
        if len(c) >= 2 and c.lower() not in seen:
            seen.add(c.lower()); cands.append(c)
    best = None
    for name in cands:
        pat = r"(?<![A-Za-z0-9])" + r"\s*".join(re.escape(x) for x in name.split()) + r"(?![A-Za-z0-9])"
        if re.search(pat, t, re.I) and (best is None or len(name) > len(best)):
            best = name
    if best:
        return best
    if not heuristik:
        return ""
    nama_re = r"([A-Za-z0-9][\w\-/.]*(?:\s+[A-Za-z0-9][\w\-/.]*){0,2})"
    # 1) kata penanda yang jelas: unit / ruang / poli / bagian / instalasi / bangsal
    m = re.search(r"\b(unit|ruang|ruangan|poli|bagian|instalasi|bangsal)\s+" + nama_re, t, re.I)
    pre = m.group(1).lower() if m else ""
    grup = m.group(2) if m else ""
    # 2) "di <Ruang>" / "dari <Ruang>": hanya dipercaya kalau diawali huruf kapital
    if not m:
        for m2 in re.finditer(r"\b(?:di|dari)\s+" + nama_re, t, re.I):
            if m2.group(1)[0].isupper():
                grup = m2.group(1)
                break
    if grup:
        toks = []
        for w in grup.split():
            if w.lower().strip(".,") in _UNIT_STOP:
                break
            toks.append(w.strip(".,"))
        if toks:
            nama = " ".join(_norm_unit_tok(x) for x in toks)
            if pre in ("ruangan",):
                pre = "ruang"
            return (pre.capitalize() + " " + nama) if pre in ("poli", "bangsal", "instalasi", "ruang") else nama
    return ""

_ACK_RE = re.compile(r"^(siap|ok|oke|baik|sip|noted|otw|ya|iya|mohon ditunggu|ditunggu|segera|izin|ijin|"
                     r"terima kasih|makasih|trims|thanks|baik pak|baik bu)\b", re.I)
def _is_ack(t):
    return len(t.strip()) <= 40 and _ACK_RE.match(t.strip()) is not None

def _bulan_from_text(txt):
    if not txt:
        return None
    for b in BULAN_ID:
        if re.search(r"\b%s\b" % b, txt, re.I):
            return b
    m = re.search(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})\b", txt)
    if m and 1 <= int(m.group(2)) <= 12:
        return BULAN_ID[int(m.group(2)) - 1]
    return None

def _has_labels(text):
    for raw in text.replace("\r", "").split("\n"):
        st_ = _wa_msg_start(raw)
        line = st_["text"] if st_ else raw
        line = re.sub(r"[*~`]", "", line)
        if any(rx.match(line) for _, rx in _WA_LABEL_RE):
            return True
    return False

def _parse_wa_conversation(msgs, default_bulan, known_units, it_names, reply_all=True, pelapor_units=None):
    """Percakapan WA: pesan user = kendala (+ jam mulai), balasan IT = solusi (+ jam selesai)."""
    it_names = [n.strip().lower() for n in (it_names or []) if n.strip()]
    def is_it(sender):
        return any(n in sender.lower() for n in it_names)
    tickets, cur = [], None
    for m in msgs:
        if is_it(m["sender"]):
            if cur is None or _is_ack(m["text"]):
                continue
            terbuka = [tk for tk in tickets if not tk["solusi"]]
            for tk in (terbuka if (reply_all and terbuka) else [cur]):
                tk["solusi"].append(m["text"]); tk["selesai"] = (m["date"], m["jam"])
        else:
            if _is_ack(m["text"]):
                continue
            if cur is not None and not cur["solusi"] and cur["sender"] == m["sender"]:
                cur["kendala"].append(m["text"])           # pesan lanjutan pelapor yang sama
            else:
                cur = {"sender": m["sender"], "date": m["date"], "jam": m["jam"],
                       "kendala": [m["text"]], "solusi": [], "selesai": None}
                tickets.append(cur)
    out = []
    for tk in tickets:
        kendala, solusi = " ".join(tk["kendala"]), " ".join(tk["solusi"])
        pelapor = "" if re.match(r"^[+\d][\d\s\-+()]{6,}$", tk["sender"]) else tk["sender"]
        e = {"Bulan": BULAN_ID[tk["date"].month - 1], "Unit": detect_unit(kendala, known_units) or
             detect_unit(solusi, known_units, heuristik=False) or
             (pelapor_units or {}).get(pelapor.strip().lower(), ""), "Kendala": kendala, "Solusi": solusi,
             "Pelapor": pelapor, "Tanggal": tanggal_fmt(tk["date"]), "Mulai_Jam": tk["jam"],
             "Selesai_Jam": tk["selesai"][1] if tk["selesai"] else ""}
        if tk["selesai"] and tk["selesai"][0] != tk["date"]:
            e["Selesai_Tgl"] = tanggal_fmt(tk["selesai"][0])
        out.append(e)
    return out

def parse_wa_report(text, default_bulan, known_units=None, it_names=None, reply_all=True, pelapor_units=None):
    """Ubah teks WA jadi list entri. Tiga mode:
    1) berlabel (Unit:/Kendala:/Solusi:)  2) percakapan WA (timestamp + pengirim)  3) teks bebas."""
    text = text.replace("\r", "")
    if not _has_labels(text):
        msgs = parse_wa_messages(text)
        if msgs:
            return _parse_wa_conversation(msgs, default_bulan, known_units, it_names, reply_all, pelapor_units)
        flat = _wa_clean(text)
        if not flat:
            return []
        return [{"Bulan": default_bulan, "Unit": detect_unit(flat, known_units), "Kendala": flat,
                 "Solusi": "", "Pelapor": "", "Tanggal": "", "Mulai_Jam": "", "Selesai_Jam": ""}]

    text = re.sub(r"[*~`]", "", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)
    entries, cur, field = [], {}, None

    def push():
        nonlocal cur
        if cur:
            d_wa = parse_tanggal_id(cur.get("tanggal")) or cur.get("_tgl")
            bulan = (BULAN_ID[d_wa.month - 1] if d_wa else None) \
                    or _bulan_from_text(cur.get("bulan")) or _bulan_from_text(cur.get("tanggal")) \
                    or default_bulan
            unit = cur.get("unit", "").strip() or detect_unit(cur.get("kendala", ""), known_units) \
                   or detect_unit(cur.get("solusi", ""), known_units, heuristik=False)
            entries.append({"Bulan": bulan, "Unit": unit,
                            "Kendala": cur.get("kendala", "").strip(),
                            "Solusi": cur.get("solusi", "").strip(),
                            "Pelapor": cur.get("pelapor", "").strip(),
                            "Tanggal": tanggal_fmt(d_wa) if d_wa else "",
                            "Mulai_Jam": cur.get("_jam", ""), "Selesai_Jam": ""})
        cur = {}

    last_ts = None
    for raw in text.split("\n"):
        st_ = _wa_msg_start(raw)
        if st_:
            last_ts = (st_["date"], st_["jam"])
            line = st_["text"].rstrip()
        else:
            line = raw.rstrip()
        if not line.strip():
            field = None
            continue
        hit = None
        for key, rx in _WA_LABEL_RE:
            m = rx.match(line)
            if m:
                hit = (key, m.group(1).strip())
                break
        if hit:
            key, val = hit
            if key in cur:          # label yang sama muncul lagi = laporan baru
                push()
            if last_ts and "_tgl" not in cur:
                cur["_tgl"], cur["_jam"] = last_ts
            cur[key] = val
            field = key
        elif field:
            cur[field] = (cur.get(field, "") + " " + line.strip()).strip()

    push()
    return [e for e in entries if e["Unit"] or e["Kendala"] or e["Solusi"]]

# ── Dekorasi halaman PDF ──────────────────────────────────────
def make_page_decorator(header_text):
    def add_page_decorations(canvas, doc):
        canvas.saveState()
        W, H = A4
        HEADER_H = 1.55*cm
        canvas.setFillColor(C_HEADER)
        canvas.rect(0, H - HEADER_H, W, HEADER_H, fill=1, stroke=0)
        canvas.setFillColor(C_ACCENT)
        canvas.rect(0, H - HEADER_H - 0.22*cm, W, 0.22*cm, fill=1, stroke=0)

        logo_reader = ImageReader(io.BytesIO(base64.b64decode(LOGO_KOTA_CILEGON_B64)))
        logo_h = 1.15*cm
        logo_w = logo_h * (logo_reader.getSize()[0] / logo_reader.getSize()[1])
        canvas.drawImage(logo_reader, 1.5*cm, H - HEADER_H + (HEADER_H - logo_h)/2,
                         width=logo_w, height=logo_h, mask="auto", preserveAspectRatio=True)

        canvas.setFillColor(C_WHITE)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(1.5*cm + logo_w + 0.3*cm, H - 0.68*cm, header_text)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(W - 1.5*cm, H - 0.68*cm, "Teknisi: Isfan Fajar Anugrah")
        canvas.drawRightString(W - 1.5*cm, H - 1.15*cm, "NIP: 199709302025211069")
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


# ── Gambar ttd → flowable reportlab ──────────────────────────
def rl_sig(raw, max_w, max_h):
    if not raw:
        return None
    try:
        iw, ih = ImageReader(io.BytesIO(raw)).getSize()
        ratio = min(max_w/iw, max_h/ih)
        return RLImage(io.BytesIO(raw), width=iw*ratio, height=ih*ratio, mask="auto")
    except Exception:
        return None

def rl_sig_norm(raw, diag, max_w, max_h):
    """Ttd dengan ukuran VISUAL seragam: diagonal kotak tinta dibuat sama (diag), lalu dibatasi max_w x max_h.
    Ttd yang melebar dan ttd yang tinggi-sempit jadi terlihat sama besar."""
    if not raw:
        return None
    try:
        iw, ih = ImageReader(io.BytesIO(raw)).getSize()
        sc = diag / ((iw ** 2 + ih ** 2) ** 0.5)
        w, h = iw * sc, ih * sc
        if w > max_w or h > max_h:
            k = min(max_w / w, max_h / h)
            w, h = w * k, h * k
        return RLImage(io.BytesIO(raw), width=w, height=h, mask="auto")
    except Exception:
        return None

MODE_UKURAN_TTD = {
    "tinggi":   "Samakan tinggi (lebar menyesuaikan bentuk ttd)",
    "luas":     "Samakan luas (ttd lebar dan ttd tinggi terasa seimbang)",
    "diagonal": "Samakan diagonal (kompromi tinggi & luas)",
    "kotak":    "Muat di satu kotak (ukuran asli ttd, cara paling sederhana)",
}

def rl_sig_mode(raw, mode="diagonal"):
    """Ttd dengan proporsi asli (tidak digepengkan), ukuran diseragamkan menurut mode."""
    if not raw:
        return None
    try:
        iw, ih = ImageReader(io.BytesIO(raw)).getSize()
        max_w, max_h = 3.8 * cm, 2.0 * cm
        if mode == "tinggi":
            h = 1.7 * cm; w = iw * h / ih
        elif mode == "luas":
            sc = ((1.9 * cm) ** 2 / (iw * ih)) ** 0.5; w, h = iw * sc, ih * sc
        elif mode == "kotak":
            sc = min(3.6 * cm / iw, 1.5 * cm / ih); w, h = iw * sc, ih * sc
        else:
            sc = 2.7 * cm / ((iw ** 2 + ih ** 2) ** 0.5); w, h = iw * sc, ih * sc
        if w > max_w or h > max_h:
            k = min(max_w / w, max_h / h); w, h = w * k, h * k
        return RLImage(io.BytesIO(raw), width=w, height=h, mask="auto")
    except Exception:
        return None

def ttd_user_to_b64(uploaded, max_w=500, max_side=400):
    """TTD user per tiket: bersihkan latar kertas → PNG transparan (base64)."""
    from PIL import Image as PILImage
    im = clean_signature(PILImage.open(io.BytesIO(uploaded.getvalue())), max_w, max_side)
    out = io.BytesIO()
    im.save(out, "PNG", optimize=True)
    return base64.b64encode(out.getvalue()).decode("utf-8")

def _isi_digest(e):
    """Sidik isi laporan (tanggal, unit, kendala, tindakan, nama penerima). Dipakai untuk mendeteksi
    perubahan isi setelah tanda tangan masuk."""
    bagian = [str(e.get(k, "") or "").strip() for k in ("Tanggal", "Unit", "Kendala", "Solusi", "Pelapor")]
    return hashlib.sha256("|".join(bagian).encode("utf-8")).hexdigest()[:16]

# ── FORM per tiket (meniru form kertas "Pemeliharaan Rutin/Berkala Komputer") ──
JENIS_PEKERJAAN = [("a","Cleaning"), ("b","Service (Scaning/Install/Pengkabelan)"),
                   ("c","Maintenance RDBMS"), ("d","Customisasi Aplikasi"),
                   ("e","Maintenance OS")]

def split_items(text):
    """Pecah teks jadi butir 1..n (per baris, atau penomoran '1. ... 2. ...')."""
    t = (text or "").strip()
    if not t:
        return []
    parts = [x for x in re.split(r"\n+", t) if x.strip()]
    if len(parts) == 1:
        parts = re.split(r"\s+(?=\d+[.)]\s)", parts[0])
    return [re.sub(r"^\s*\d+[.)]\s*", "", x).strip() for x in parts if x.strip()]

class PilihanKerja(Flowable):
    """Daftar a–f; yang dipilih dilingkari seperti di form kertas."""
    def __init__(self, dipilih, lainnya="", width=17.6*cm):
        super().__init__()
        self.dipilih, self.lainnya, self.w, self.h = set(dipilih), lainnya, width, 1.55*cm
    def wrap(self, aw, ah):
        return self.w, self.h
    def draw(self):
        c, fs = self.canv, 8.5
        c.setFont("Helvetica", fs); c.setFillColor(C_TEXT)
        def item(x, y, key, label):
            txt = f"{key}. {label}"
            wd = stringWidth(txt, "Helvetica", fs)
            c.drawString(x, y, txt)
            if key in self.dipilih:
                c.saveState(); c.setStrokeColor(C_HEADER); c.setLineWidth(1)
                c.ellipse(x-4, y-3.5, x+wd+4, y+fs+1.5, stroke=1, fill=0); c.restoreState()
            return x + wd + 0.9*cm
        y = self.h - 0.45*cm
        x = item(0.5*cm, y, *JENIS_PEKERJAAN[0]); item(x, y, *JENIS_PEKERJAAN[1])
        y -= 0.5*cm
        x = item(0.5*cm, y, *JENIS_PEKERJAAN[2]); x = item(x, y, *JENIS_PEKERJAAN[3]); item(x, y, *JENIS_PEKERJAAN[4])
        y -= 0.5*cm
        x = item(0.5*cm, y, "f", "Lainnya")
        if "f" in self.dipilih or self.lainnya:
            self.dipilih.add("f")
        c.setDash(1, 2); c.setStrokeColor(colors.grey); c.line(x-0.7*cm, y-2, self.w, y-2); c.setDash()
        if self.lainnya:
            c.setFont("Helvetica", fs); c.drawString(x-0.6*cm, y, self.lainnya[:90])

def build_form_flowables(e, nomor, total, tanpa_ttd_staf=False, tampil_nomor=True):
    ss = st.session_state
    cfg_ttd = ss.get("ttd_cfg", {}) or {}
    def b64_bytes(key):
        v = cfg_ttd.get(key)
        return base64.b64decode(v) if (v and not tanpa_ttd_staf) else None

    f   = ParagraphStyle("f",  fontName="Helvetica", fontSize=8.5, textColor=C_TEXT, leading=11)
    fb  = ParagraphStyle("fb", parent=f, fontName="Helvetica-Bold")
    ftt = ParagraphStyle("ftt", fontName="Helvetica-Bold", fontSize=10.5, textColor=C_TEXT,
                         alignment=TA_CENTER, leading=13)
    fsub= ParagraphStyle("fsub", fontName="Helvetica-Bold", fontSize=9, textColor=C_TEXT,
                         alignment=TA_CENTER, leading=12, spaceBefore=4, spaceAfter=6)
    fc  = ParagraphStyle("fc", parent=f, alignment=TA_CENTER)
    fcb = ParagraphStyle("fcb", parent=fc, fontName="Helvetica-Bold")
    fn  = ParagraphStyle("fn", parent=fc, fontSize=7.5, leading=10)
    DOT = (1, 2)
    def P(txt, st_=f): return Paragraph(xml_escape(str(txt)) if txt else "", st_)
    def line_tbl(data, widths, dotted_cols, min_h=0.5*cm):
        t = Table(data, colWidths=widths)
        style = [("VALIGN",(0,0),(-1,-1),"BOTTOM"),("TOPPADDING",(0,0),(-1,-1),1),
                 ("BOTTOMPADDING",(0,0),(-1,-1),1),("LEFTPADDING",(0,0),(-1,-1),2),
                 ("RIGHTPADDING",(0,0),(-1,-1),2)]
        for c in dotted_cols:
            style.append(("LINEBELOW",(c,0),(c,-1),0.5,colors.grey,1,DOT))
        t.setStyle(TableStyle(style)); return t

    year = datetime.now(WIB).year
    tgl = e.get("Tanggal") or f"{e.get('Bulan','')} {year}"
    out = [Paragraph("PEMELIHARAAN RUTIN/BERKALA KOMPUTER", ftt),
           Paragraph("RSUD KOTA CILEGON", ftt),
           Paragraph("<u>RINCIAN PEMERIKSAAN DAN TINDAKAN SERVIS</u>", fsub)]

    out.append(line_tbl([[P("TGL/BLN/THN :"), P(tgl), P("No.Reg :"), P(e.get("NoReg",""))]],
                        [2.6*cm, 6.2*cm, 1.8*cm, 7.0*cm], [1, 3]))
    out.append(line_tbl([[P("I", fb), P("LOKASI/UNIT/RUANGAN :", fb), P(e.get("Unit",""))]],
                        [1.0*cm, 4.6*cm, 12.0*cm], [2]))
    out.append(line_tbl([[P("II", fb), P("NAMA PERALATAN/INVENTARIS (Nama/Merk/Type) :", fb), P(e.get("Peralatan",""))]],
                        [1.0*cm, 8.2*cm, 8.4*cm], [2]))

    def numbered(items, n=4):
        items = list(items)
        if len(items) > n:
            items = items[:n-1] + ["; ".join(items[n-1:])]
        items += [""] * (n - len(items))
        return line_tbl([[P(i+1), P(t)] for i, t in enumerate(items)], [0.9*cm, 16.7*cm], [1])

    out.append(Table([[P("III", fb), P("URAIAN PERMASALAHAN :", fb)]], colWidths=[1.0*cm, 16.6*cm],
                     style=[("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    out.append(numbered(split_items(e.get("Kendala",""))))

    out.append(Table([[P("IV", fb), P("JANGKA WAKTU PELAKSANAAN :", fb)]], colWidths=[1.0*cm, 16.6*cm],
                     style=[("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    tgl_dasar = e.get("Tanggal") or ""
    out.append(line_tbl([[P("Mulai Tgl :"), P(e.get("Mulai_Tgl") or tgl_dasar), P("Jam :"), P(e.get("Mulai_Jam","")),
                          P("Selesai Tgl :"), P(e.get("Selesai_Tgl") or tgl_dasar), P("Jam :"), P(e.get("Selesai_Jam",""))]],
                        [1.8*cm, 3.2*cm, 1.0*cm, 2.0*cm, 2.2*cm, 3.2*cm, 1.0*cm, 2.2*cm], [1, 3, 5, 7]))

    out.append(Table([[P("V", fb), P("SOLUSI DAN TINDAKAN/PEKERJAAN (lingkari sesuai pekerjaan) :", fb)]],
                     colWidths=[1.0*cm, 16.6*cm],
                     style=[("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    out.append(PilihanKerja(e.get("Jenis", []), e.get("Lainnya", "")))

    out.append(Table([[P("VI", fb), P("PENGGANTIAN SUKU CADANG :", fb)]], colWidths=[1.0*cm, 16.6*cm],
                     style=[("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]))
    sc = list(e.get("SukuCadang", []))
    rows = [[P("NAMA", fcb), P("VOLUME", fcb), P("SATUAN", fcb)]]
    for r in sc[:6]:
        rows.append([P(r.get("nama","")), P(r.get("volume",""), fc), P(r.get("satuan",""), fc)])
    while len(rows) < 5:
        rows.append(["", "", ""])
    tsc = Table(rows, colWidths=[11.6*cm, 3.0*cm, 3.0*cm], rowHeights=[0.5*cm] + [0.48*cm]*(len(rows)-1))
    tsc.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.8,colors.black),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                             ("TOPPADDING",(0,0),(-1,-1),1),("BOTTOMPADDING",(0,0),(-1,-1),1)]))
    out.append(tsc)

    out.append(Table([[P("VII", fb), P("KETERANGAN HASIL", fb)]], colWidths=[1.0*cm, 16.6*cm],
                     style=[("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    out.append(numbered(split_items(e.get("Solusi",""))))

    # ── tanda tangan: Pengawas (Kanit) | Teknisi (IT) ; di bawahnya User penerima ──
    def dots(v, n=34): return v.strip() if v and v.strip() else "." * n
    mode_ttd = ss.get("ttd_mode_ukuran") or cfg_ttd.get("mode_ukuran") or "luas"
    def sig(raw): return rl_sig_mode(raw, mode_ttd) or ""
    def nama_cell(nama, extra=""):
        t = f"( {xml_escape(nama)} )"
        if extra: t += f"<br/><font size=7>{xml_escape(extra)}</font>"
        return Paragraph(t, fc)
    tanggal_ttd = e.get("Tanggal") or ""      # jangan pakai tanggal hari ini kalau entri tak punya tanggal
    atas = Table(
        [[Paragraph("PENGAWAS PEKERJAAN", fcb), Paragraph("PETUGAS SERVICE/", fcb)],
         [Paragraph("Petugas Unit SIMRS", fc), Paragraph("Teknisi", fc)],
         [sig(b64_bytes("kanit_img_b64")), sig(b64_bytes("it_img_b64"))],
         [nama_cell(dots(ss.get("ttd_pengawas_nama", ""))),
          nama_cell("Isfan Fajar Anugrah")]],
        colWidths=[8.8*cm, 8.8*cm], rowHeights=[0.42*cm, 0.42*cm, 2.15*cm, None])
    bawah = Table(
        [[Paragraph(f"Cilegon, {xml_escape(dots(tanggal_ttd, 24))}", fc)],
         [Paragraph("Petugas Yang Menerima", fcb)],
         [Paragraph("Hasil Service / User", fc)],
         [sig(base64.b64decode(e["TTD_User"]) if e.get("TTD_User") else None)],
         [nama_cell(dots(e.get("Pelapor","")))]],
        colWidths=[17.6*cm], rowHeights=[0.5*cm, 0.42*cm, 0.42*cm, 2.15*cm, None])
    for t_ in (atas, bawah):
        t_.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"),   # gambar ttd di tengah kolom, sejajar nama
                                ("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),0),
                                ("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    atas.setStyle(TableStyle([("VALIGN", (0,2), (-1,2), "MIDDLE")]))     # ttd di tengah ruangnya
    bawah.setStyle(TableStyle([("VALIGN", (0,3), (-1,3), "MIDDLE")]))
    out += [Spacer(1, 0.35*cm), atas, Spacer(1, 0.1*cm), bawah]
    if e.get("TTD_Kode"):
        _utuh = e.get("TTD_Isi") == _isi_digest(e)
        out.append(Paragraph(
            "<font size=6.5 color='#7F8C8D'>Kode verifikasi tanda tangan: %s%s</font>"
            % (xml_escape(str(e["TTD_Kode"])), "" if _utuh else " (isi laporan diubah setelah ditandatangani)"),
            ParagraphStyle("kodev", parent=f, alignment=1)))
    if tampil_nomor:
        out.append(Paragraph(f"<font size=7 color='#7F8C8D'>Lampiran {nomor} dari {total}</font>",
                             ParagraphStyle("lamp", parent=f, alignment=2)))
    return out

# ── PDF Generator ─────────────────────────────────────────────
class _Penanda(Flowable):
    """Flowable tanpa ukuran: mencatat nomor halaman tempat ia tergambar."""
    def __init__(self, simpan, nama):
        super().__init__()
        self.simpan, self.nama = simpan, nama
        self.width = self.height = 0
    def wrap(self, aw, ah):
        return (0, 0)
    def draw(self):
        self.simpan[self.nama] = self.canv.getPageNumber()

def generate_pdf(all_data, pdf_title="Laporan IT Triwulan I", header_text="LAPORAN IT TRIWULAN I", romawi="I",
                 hanya_form=False, cetak=False, tanpa_ttd_staf=False, kompak=False):
    all_data = urutkan(all_data)
    _pad = 4 if kompak else 6                    # kompak: dipakai otomatis kalau ringkasan terlempar sendirian ke halaman baru
    buf = io.BytesIO()
    nomor_dokumen = f"No: LAP-IT/TW-{romawi}/{datetime.now().year}/RSUD-CLG"
    top_m = 1.4*cm if cetak else 3.0*cm
    bot_m = 1.4*cm if cetak else 1.8*cm
    doc = BaseDocTemplate(buf, pagesize=A4,
                          rightMargin=1.5*cm, leftMargin=1.5*cm,
                          topMargin=top_m, bottomMargin=bot_m)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    if cetak:
        doc.addPageTemplates([PageTemplate(id="main", frames=frame)])
    else:
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
    s_nomor = ParagraphStyle("nomor", fontName="Helvetica-Oblique", fontSize=8,
                             textColor=C_TEXT, alignment=TA_CENTER, spaceAfter=4)
    s_pel   = ParagraphStyle("pel", fontName="Helvetica", fontSize=7.5,
                             textColor=C_TEXT, alignment=TA_CENTER, leading=10)
    s_ringkasan_title = ParagraphStyle("ringkasan_title", fontName="Helvetica-Bold",
                             fontSize=10, textColor=C_HEADER, spaceBefore=(4 if kompak else 10), spaceAfter=4)
    s_ringkasan = ParagraphStyle("ringkasan", fontName="Helvetica", fontSize=9,
                             textColor=C_TEXT, leading=(12 if kompak else 14), alignment=TA_LEFT)

    elements = [Spacer(1, 0.2*cm),
                Paragraph(pdf_title, s_judul),
                Paragraph("Teknisi: Isfan Fajar Anugrah &nbsp;|&nbsp; NIP: 199709302025211069 &nbsp;|&nbsp; Divisi Teknologi Informasi", s_sub),
                Paragraph(nomor_dokumen, s_nomor),
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
            Paragraph(xml_escape(tampil), s_cell),
            Paragraph(xml_escape(e.get("Unit", "-")), s_cell),
            Paragraph(xml_escape(e.get("Kendala", "-")), s_cell),
            Paragraph(xml_escape(e.get("Solusi", "-")), s_cell),
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
        ("TOPPADDING",    (0,1),(-1,-1), _pad),
        ("BOTTOMPADDING", (0,1),(-1,-1), _pad),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ("ALIGN",         (0,1),(0,-1), "CENTER"),
        ("ALIGN",         (1,1),(1,-1), "CENTER"),
        ("ALIGN",         (5,1),(5,-1), "CENTER"),
        ("GRID",          (0,0),(-1,-1), 0.4, colors.HexColor("#BDC3C7")),
        ("BOX",           (0,0),(-1,-1), 1.2, C_SUBHEAD),
        *row_bg,
    ]))

    bulan_list = list(dict.fromkeys(bulan_entri(e) for e in all_data))
    blok_ringkasan = [Spacer(1, (0.15 if kompak else 0.5)*cm),
                      HRFlowable(width="100%", thickness=1, color=C_SUBHEAD, spaceAfter=(3 if kompak else 6)),
                      Paragraph(f"Total entri: <b>{len(all_data)}</b> &nbsp;|&nbsp; "
                                f"Bulan tercatat: <b>{', '.join(bulan_list)}</b>", s_info)]

    if all_data:
        unit_counts = Counter(e.get("Unit", "-") for e in all_data)
        unit_teratas, jumlah_teratas = unit_counts.most_common(1)[0]
        urut_unit = unit_counts.most_common()
        if all(c == 1 for _, c in urut_unit):
            rincian = f"{len(urut_unit)} unit/lokasi berbeda, masing-masing 1 kali"
        else:
            tampil = "; ".join(f"{xml_escape(u)} ({c})" for u, c in urut_unit[:5])
            sisa = len(urut_unit) - 5
            rincian = tampil + (f"; dan {sisa} unit lainnya" if sisa > 0 else "")
        ringkasan_text = (
            f"Selama periode ini tercatat <b>{len(all_data)} kendala/pekerjaan</b> yang ditangani. "
            + ("" if all(c == 1 for _, c in urut_unit) else
               f"Unit/lokasi dengan jumlah penanganan terbanyak adalah <b>{xml_escape(unit_teratas)}</b> "
               f"sebanyak {jumlah_teratas} kali. ")
            + f"Rincian per unit: {rincian}. "
            f"Seluruh kendala pada periode ini telah ditindaklanjuti hingga selesai."
        )
        blok_ringkasan += [
            Paragraph("Ringkasan Periode", s_ringkasan_title),
            Paragraph(ringkasan_text, s_ringkasan),
        ]
    # tabel dulu, lalu ringkasan satu blok utuh (tidak pernah kepotong ke halaman berikutnya)
    _hal = {}
    elements += [tbl, _Penanda(_hal, "tbl"), KeepTogether([_Penanda(_hal, "sum")] + blok_ringkasan)]

    if hanya_form:                       # rekap form saja (tanpa tabel ringkasan)
        elements = []
        for n, e in enumerate(all_data, 1):
            if n > 1:
                elements.append(PageBreak())
            elements += build_form_flowables(e, n, len(all_data), tanpa_ttd_staf=tanpa_ttd_staf,
                                             tampil_nomor=not cetak)
    elif st.session_state.get("lampiran", True):
        for n, e in enumerate(all_data, 1):
            elements.append(PageBreak())
            elements += build_form_flowables(e, n, len(all_data))
    doc.build(elements)
    # ringkasan terlempar sendirian ke halaman baru (halaman hampir kosong)? bangun ulang dengan tata letak lebih rapat
    if (not kompak and not hanya_form and _hal.get("sum") and _hal.get("tbl")
            and _hal["sum"] > _hal["tbl"]):
        return generate_pdf(all_data, pdf_title, header_text, romawi,
                            hanya_form=hanya_form, cetak=cetak, tanpa_ttd_staf=tanpa_ttd_staf, kompak=True)
    buf.seek(0)
    return buf

def show_pdf_preview(pdf_buffer):
    b64 = base64.b64encode(pdf_buffer.read()).decode("utf-8")
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" '
        f'width="100%" height="560px" '
        f'style="border:2px solid #2E86C1; border-radius:10px;"></iframe>',
        unsafe_allow_html=True)

# ── Input detail form servis (dipakai form baru & edit) ──────
def _stamp_jam(key):
    st.session_state[key] = jam_sekarang()

def _auto_detail():
    """Dipanggil saat teks kendala/solusi berubah: centang jenis kerja & isi peralatan otomatis.
    Hanya menimpa kalau user belum mengubahnya sendiri."""
    ss = st.session_state
    g = tebak_detail(ss.get("in_kendala", ""), ss.get("in_solusi", ""))
    prev = ss.get("_auto_prev", {"Peralatan": "", "Jenis": []})
    cur_alat = (ss.get("in_alat", "") or "").strip()
    if not cur_alat or cur_alat == prev["Peralatan"]:
        ss["in_alat"] = g["Peralatan"]
    cur_j = sorted(k for k, _ in JENIS_PEKERJAAN if ss.get(f"in_jn_{k}"))
    if not cur_j or cur_j == sorted(prev["Jenis"]):
        for k, _ in JENIS_PEKERJAAN:
            ss[f"in_jn_{k}"] = k in g["Jenis"]
    ss["_auto_prev"] = g

def detail_inputs(prefix, e=None):
    """Mode baru (e=None): nilai disimpan di session_state (bisa diisi otomatis).
    Mode edit (e=entri): nilai awal dari entri."""
    new = e is None
    e = e or {}
    ss = st.session_state
    if new:
        ss.setdefault("in_tgl", hari_ini_wib())
        for k_, v_ in (("in_alat", ""), ("in_mjam", ""), ("in_sjam", ""), ("in_lain", ""),
                       ("in_sc", ""), ("in_durasi", 30)):
            ss.setdefault(k_, v_)
        for k, _ in JENIS_PEKERJAAN:
            ss.setdefault(f"in_jn_{k}", False)

    with st.expander("📄 Detail form servis (diisi otomatis, tinggal cek)", expanded=new):
        # --- tanggal ---
        if new:
            tgl_d = st.date_input("Tanggal pekerjaan", key="in_tgl", format="DD/MM/YYYY")
        else:
            tgl_awal = parse_tanggal_id(e.get("Tanggal"))
            try:
                tgl_d = st.date_input("Tanggal pekerjaan (kosong = belum diisi)", value=tgl_awal,
                                      key=f"{prefix}_tgl", format="DD/MM/YYYY")
            except TypeError:
                tgl_d = st.date_input("Tanggal pekerjaan", value=tgl_awal or hari_ini_wib(),
                                      key=f"{prefix}_tgl", format="DD/MM/YYYY")

        # --- peralatan ---
        if new:
            alat = st.text_input("Nama peralatan / inventaris (otomatis dari kendala, bisa diubah)", key="in_alat")
        else:
            alat = st.text_input("Nama peralatan / inventaris", value=e.get("Peralatan", ""), key=f"{prefix}_alat")

        # --- jam ---
        c1, c2 = st.columns(2)
        with c1:
            if new:
                m_jam = st.text_input("Jam mulai (mis. 09:00)", key="in_mjam")
                st.button("⏱ Mulai = sekarang", key="btn_mjam", on_click=_stamp_jam, args=("in_mjam",))
            else:
                m_jam = st.text_input("Jam mulai", value=e.get("Mulai_Jam", ""), key=f"{prefix}_mjam")
        with c2:
            if new:
                s_jam = st.text_input("Jam selesai (mis. 09:45)", key="in_sjam")
                st.button("⏱ Selesai = sekarang", key="btn_sjam", on_click=_stamp_jam, args=("in_sjam",))
            else:
                s_jam = st.text_input("Jam selesai", value=e.get("Selesai_Jam", ""), key=f"{prefix}_sjam")
        if new:
            st.selectbox("Lama pengerjaan (menit) — dipakai kalau jam mulai dikosongkan",
                         [10, 15, 20, 30, 45, 60, 90, 120], key="in_durasi")
            st.caption("Kosongkan jam → otomatis: selesai = jam saat disimpan, mulai = selesai dikurangi lama pengerjaan "
                       "(hanya kalau tanggalnya hari ini).")

        # --- solusi/tindakan: centang ---
        st.markdown("**Solusi dan tindakan/pekerjaan** (otomatis tercentang dari teks, bisa diubah)")
        jenis_huruf = []
        for k, label in JENIS_PEKERJAAN:
            if new:
                ok = st.checkbox(f"{k}. {label}", key=f"in_jn_{k}")
            else:
                ok = st.checkbox(f"{k}. {label}", value=(k in e.get("Jenis", [])), key=f"{prefix}_jn_{k}")
            if ok:
                jenis_huruf.append(k)
        if new:
            lain = st.text_input("f. Lainnya", key="in_lain")
        else:
            lain = st.text_input("f. Lainnya", value=e.get("Lainnya", ""), key=f"{prefix}_lain")

        # --- suku cadang ---
        sc_def = "\n".join(f"{r.get('nama','')} | {r.get('volume','')} | {r.get('satuan','')}"
                           for r in e.get("SukuCadang", []))
        if new:
            sc_txt = st.text_area("Penggantian suku cadang (1 baris: Nama | Volume | Satuan)", key="in_sc")
        else:
            sc_txt = st.text_area("Penggantian suku cadang (1 baris: Nama | Volume | Satuan)",
                                  value=sc_def, key=f"{prefix}_sc")

    suku = []
    for ln in sc_txt.split("\n"):
        if ln.strip():
            parts = [x.strip() for x in ln.split("|")] + ["", ""]
            suku.append({"nama": parts[0], "volume": parts[1], "satuan": parts[2]})
    if lain.strip() and "f" not in jenis_huruf:
        jenis_huruf.append("f")
    return {"Tanggal": tanggal_fmt(tgl_d) if tgl_d else "", "NoReg": e.get("NoReg", ""), "Peralatan": alat,
            "Mulai_Tgl": e.get("Mulai_Tgl", ""), "Mulai_Jam": m_jam.strip(),
            "Selesai_Tgl": e.get("Selesai_Tgl", ""), "Selesai_Jam": s_jam.strip(),
            "Jenis": jenis_huruf, "Lainnya": lain.strip(), "SukuCadang": suku}

def lengkapi_entry(e, live):
    """Lengkapi entri sebelum disimpan/preview.
    live=True (input langsung): jam kosong diisi otomatis bila tanggal = hari ini.
    Selalu: tebak peralatan/jenis kalau kosong, dan samakan Bulan dengan tanggal."""
    warn = []
    ss = st.session_state
    for k_ in ("Mulai_Jam", "Selesai_Jam"):
        if e.get(k_):
            e[k_] = _norm_jam(e[k_])
    if live and e.get("Tanggal") == tanggal_hari_ini():
        if not e.get("Selesai_Jam"):
            e["Selesai_Jam"] = jam_sekarang()
        if not e.get("Mulai_Jam"):
            sel = _jam_ke_menit(e["Selesai_Jam"])
            if sel is not None:
                e["Mulai_Jam"] = _menit_ke_jam(sel - int(ss.get("in_durasi", 30)))
    g = tebak_detail(e.get("Kendala", ""), e.get("Solusi", ""))
    if not (e.get("Peralatan") or "").strip():
        e["Peralatan"] = g["Peralatan"]
    if not e.get("Jenis") and not e.get("Lainnya"):
        e["Jenis"] = g["Jenis"]
    d = parse_tanggal_id(e.get("Tanggal"))
    if d:
        bln = BULAN_ID[d.month - 1]
        if bln in BULAN_TRIWULAN:
            e["Bulan"] = bln
        else:
            warn.append(f"Tanggal {e['Tanggal']} di luar {selected_triwulan}; Bulan tetap {e.get('Bulan')}.")
    return e, warn

# ── Papan tanda tangan di layar (user tanda tangan pakai jari) ──
class _Bytes:
    def __init__(self, b): self._b = b
    def getvalue(self): return self._b

def _reset_pad():
    st.session_state["pad_n"] = st.session_state.get("pad_n", 0) + 1

def canvas_to_upload(img):
    """Array RGBA dari kanvas → objek ber-getvalue() (PNG), atau None kalau kosong."""
    import numpy as np
    from PIL import Image as PILImage
    arr = np.asarray(img)
    if arr.ndim != 3 or arr.shape[2] < 3:
        return None
    alpha = arr[..., 3] if arr.shape[2] == 4 else np.full(arr.shape[:2], 255)
    tinta = ((arr[..., :3].max(axis=2) < 150) & (alpha > 0)).sum()
    if tinta < 40:                       # kosong / cuma titik tak sengaja
        return None
    out = io.BytesIO()
    PILImage.fromarray(arr.astype("uint8")).save(out, "PNG")
    return _Bytes(out.getvalue())

def ttd_pad(key):
    """Kanvas ttd. Return objek getvalue() kalau sudah ada coretan, selain itu None."""
    try:
        from streamlit_drawable_canvas import st_canvas
    except Exception:
        st.caption("⚠️ Papan ttd belum aktif: tambahkan `streamlit-drawable-canvas` ke requirements.txt "
                   "lalu redeploy. Sementara pakai upload/foto di bawah.")
        return None
    n = st.session_state.get("pad_n", 0)
    kw = dict(stroke_width=4, stroke_color="#000000", background_color="#FFFFFF",
              height=170, width=320, drawing_mode="freedraw", update_streamlit=True,
              key=f"{key}_{n}")
    try:
        try:
            res = st_canvas(return_image_data=True, **kw)     # versi baru
        except TypeError:
            res = st_canvas(**kw)                             # versi lama
        img = res.image_data
    except Exception as ex:
        st.caption(f"⚠️ Papan ttd error: {ex}")
        return None
    st.button("🗑️ Hapus / ulangi ttd", key=f"clr_{key}", on_click=_reset_pad)
    return canvas_to_upload(img) if img is not None else None

def jumlah_gumpalan(img, sisi=200, min_piksel=6):
    """Jumlah gumpalan tinta terpisah pada gambar RGBA. Teks banyak (tiap huruf), ttd hanya beberapa."""
    import numpy as np
    from PIL import Image as PILImage
    a = img.convert("RGBA").getchannel("A")
    sc = sisi / max(a.size)
    if sc < 1.0:
        a = a.resize((max(1, int(a.width * sc)), max(1, int(a.height * sc))), PILImage.BOX)
    g = np.asarray(a) > 30
    gh, gw = g.shape
    seen = np.zeros_like(g, dtype=bool)
    n = 0
    for sy in range(gh):
        for sx in range(gw):
            if g[sy, sx] and not seen[sy, sx]:
                stack, cells = [(sy, sx)], 0
                seen[sy, sx] = True
                while stack:
                    y, x = stack.pop(); cells += 1
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < gh and 0 <= nx < gw and g[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True; stack.append((ny, nx))
                if cells >= min_piksel:
                    n += 1
    return n

def crop_persen(im, kiri, kanan, atas, bawah):
    """Potong gambar PIL dengan batas dalam persen (0-100)."""
    w, h = im.size
    x1, x2 = int(w * kiri / 100), int(w * kanan / 100)
    y1, y2 = int(h * atas / 100), int(h * bawah / 100)
    return im.crop((x1, y1, max(x2, x1 + 1), max(y2, y1 + 1)))

def ttd_crop_preview(uploaded, key):
    """Crop opsional + PREVIEW hasil pembersihan sebelum disimpan. Return objek ber-getvalue() atau None."""
    if not uploaded:
        return None
    from PIL import Image as PILImage, ImageOps
    try:
        im0 = ImageOps.exif_transpose(PILImage.open(io.BytesIO(uploaded.getvalue())))
        punya_alpha = im0.mode in ("RGBA", "LA", "PA") or (im0.mode == "P" and "transparency" in im0.info)
        # PNG transparan WAJIB tetap RGBA: kalau dipaksa RGB, area transparan jadi hitam (kotak hitam di form)
        im = im0.convert("RGBA" if punya_alpha else "RGB")
    except Exception as ex:
        st.error(f"❌ Gambar tidak bisa dibuka: {ex}")
        return None
    with st.expander("✂️ Potong gambar (opsional)"):
        st.caption("Geser untuk membuang tulisan/benda lain di sekitar ttd.")
        l, r = st.slider("Kiri – kanan (%)", 0, 100, (0, 100), key=f"{key}_cx")
        t, b = st.slider("Atas – bawah (%)", 0, 100, (0, 100), key=f"{key}_cy")
    cropped = crop_persen(im, l, r, t, b)
    buf = io.BytesIO(); cropped.save(buf, "PNG")
    obj = _Bytes(buf.getvalue())
    try:
        raw = base64.b64decode(img_to_b64(obj))
        pv = PILImage.open(io.BytesIO(raw)).convert("RGBA")
        bg = PILImage.new("RGBA", pv.size, (235, 235, 235, 255)); bg.alpha_composite(pv)
        st.image(bg.convert("RGB"), caption="Preview hasil (latar abu-abu = transparan)", width=200)
        n_g = jumlah_gumpalan(pv)
        if n_g >= 6:
            st.warning(f"⚠️ Terbaca {n_g} gumpalan terpisah — kemungkinan ada tulisan/nama ikut terbawa "
                       f"(ttd polos biasanya 1–3 gumpalan). Potong lagi, atau pakai gambar ttd saja.")
        else:
            st.caption("✅ Terbaca sebagai ttd polos.")
        if len(raw) > 250_000:
            st.warning("⚠️ File hasilnya besar. Biasanya karena foto layar monitor atau gambar yang sangat ramai.")
    except Exception as ex:
        st.caption(f"⚠️ Gagal memproses gambar: {ex}")
    return obj

# ── Kotak masuk ttd dari link khusus (Google Apps Script) ──
INBOX_PREFIX = "ttd_masuk_"

def daftar_ttd_masuk(service):
    """[(file_id, nama_file)] file kotak masuk ttd di folder Drive."""
    q = f"'{FOLDER_ID}' in parents and name contains '{INBOX_PREFIX}' and trashed=false"
    res = service.files().list(q=q, fields="files(id,name)", pageSize=100).execute()
    return [(f["id"], f["name"]) for f in res.get("files", []) if f["name"].startswith(INBOX_PREFIX)]

def baca_ttd_masuk(service, fid):
    req = service.files().get_media(fileId=fid)
    fh = io.BytesIO()
    dl = MediaIoBaseDownload(fh, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    return json.loads(fh.getvalue().decode("utf-8"))

def tandai_ttd_selesai(service, fid, nama, awalan="ttd_selesai_"):
    """Ganti nama file supaya tidak diproses ulang (tanpa perlu hak hapus)."""
    service.files().update(fileId=fid, body={"name": awalan + nama[len(INBOX_PREFIX):]}).execute()

def _waktu_indo(txt):
    try:
        d_ = datetime.strptime(str(txt), "%Y-%m-%d %H:%M")
        return f"{d_.day} {BULAN_ID[d_.month-1]} {d_.year} {d_.hour:02d}:{d_.minute:02d}"
    except Exception:
        return f"{tanggal_hari_ini()} {jam_sekarang()}"

def proses_ttd_masuk(service):
    """Tarik ttd yang masuk lewat link khusus ke laporan. Return (berhasil, yatim, daftar_galat)."""
    keys = list(TRIWULAN_CONFIG.keys())
    ok = yatim = 0
    galat, berubah = [], {}
    for fid, nama in daftar_ttd_masuk(service):
        try:
            rec = baca_ttd_masuk(service, fid)
            token, tw = str(rec["token"]), int(rec["tw"])
            png = base64.b64decode(rec["png_b64"], validate=True)
            if not (1 <= tw <= len(keys)) or not (100 < len(png) <= 400000):
                raise ValueError("rekaman tidak valid")
            cfgt = TRIWULAN_CONFIG[keys[tw - 1]]
            if not get_file_id(service, cfgt["json_name"]):
                raise ValueError(f"{cfgt['json_name']} tidak ada")
            data, jfid = load_json(service, cfgt["json_name"])
            idx = next((i for i, e_ in enumerate(data) if e_.get("TTD_Token") == token), None)
            if idx is None:                       # entri sudah dihapus / token sudah diganti
                tandai_ttd_selesai(service, fid, nama, "ttd_yatim_")
                yatim += 1
                continue
            e = data[idx]
            e["TTD_User"] = ttd_user_to_b64(_Bytes(png))
            nm = str(rec.get("nama", "")).strip()[:80]
            if nm:
                e["Pelapor"] = nm
            e["TTD_Waktu"] = _waktu_indo(rec.get("waktu"))
            kd = str(rec.get("kode", "") or "").strip().upper()          # kode verifikasi dari Apps Script
            if re.fullmatch(r"[0-9A-F]{4}(-[0-9A-F]{4}){3}", kd):
                e["TTD_Kode"] = kd
                e["TTD_Isi"] = _isi_digest(e)
            else:
                e.pop("TTD_Kode", None); e.pop("TTD_Isi", None)
            e.pop("TTD_Token", None)
            e.pop("TTD_Token_Exp", None)
            data = urutkan(data)
            save_json(service, data, jfid)        # file kotak masuk baru ditandai SETELAH laporan tersimpan
            try:
                simpan_bukti_ttd_png(service, e, base64.b64decode(e["TTD_User"]))
            except Exception as ex_png:
                galat.append(f"PNG {e.get('Unit', '-')}: {ex_png}")
            tandai_ttd_selesai(service, fid, nama)
            ok += 1
            berubah[tw] = data
        except Exception as ex:
            galat.append(f"{nama}: {ex}")
    for tw, data in berubah.items():              # PDF diperbarui sekali per triwulan
        cfgt = TRIWULAN_CONFIG[keys[tw - 1]]
        try:
            if get_file_id(service, cfgt["pdf_name"]):
                upload_pdf(service, generate_pdf(data, cfgt["pdf_title"], cfgt["header"], cfgt["romawi"]),
                           cfgt["pdf_name"])
        except Exception as ex:
            galat.append(f"PDF {cfgt['pdf_name']}: {ex}")
    return ok, yatim, galat

def _ttd_url():
    """URL web app Apps Script (link ttd khusus)."""
    try:
        u = st.secrets["TTD_URL"]
    except Exception:
        u = ""
    return str((st.session_state.get("ttd_cfg") or {}).get("ttd_url") or u or "").strip()

def url_apps_script_valid(u):
    return u.startswith("https://script.google.com/") and "/macros/s/" in u and u.endswith("/exec")

# ── Link tanda tangan untuk user (tanpa login, sekali pakai) ──
TOKEN_HARI = 7

def _css_daftar():
    """Rapikan daftar laporan: baris tombol aksi tetap sejajar (tidak numpuk) di layar HP."""
    st.markdown(
        "<style>"
        "div[data-testid='stHorizontalBlock']:has(.aksi-baris){flex-wrap:nowrap!important;gap:.5rem!important;}"
        "div[data-testid='stHorizontalBlock']:has(.aksi-baris)>div[data-testid='stColumn'],"
        "div[data-testid='stHorizontalBlock']:has(.aksi-baris)>div[data-testid='column']"
        "{min-width:0!important;flex:1 1 0!important;width:auto!important;}"
        "div[data-testid='stHorizontalBlock']:has(.aksi-baris) button{width:100%;white-space:nowrap;padding:.25rem .4rem;}"
        "div[data-testid='stHorizontalBlock']:has(.aksi-baris) div[data-testid='stElementContainer']{width:100%!important;}"
        "div[data-testid='stHorizontalBlock']:has(.aksi-baris) div[data-testid='stElementContainer']:has(.aksi-baris){display:none!important;}"
        "div[data-testid='stHorizontalBlock']:has(.aksi-baris) div[data-testid='stButton']{width:100%!important;}"
        ".aksi-baris{display:none;}"
        "</style>", unsafe_allow_html=True)

def _baris_aksi(n):
    """n kolom tombol yang tetap horizontal di HP."""
    cols = st.columns(n)
    with cols[0]:
        st.markdown('<span class="aksi-baris"></span>', unsafe_allow_html=True)
    return cols

def _token_aktif(e, token=None):
    """Token ada, cocok (kalau diberikan), dan belum kedaluwarsa."""
    tk = e.get("TTD_Token")
    if not tk or (token is not None and tk != token):
        return False
    try:
        exp = datetime.strptime(e.get("TTD_Token_Exp", ""), "%Y-%m-%d %H:%M").replace(tzinfo=WIB)
    except Exception:
        return False
    return datetime.now(WIB) <= exp

def _buat_token(e):
    e["TTD_Token"] = _secrets.token_urlsafe(16)
    e["TTD_Token_Exp"] = (datetime.now(WIB) + timedelta(days=TOKEN_HARI)).strftime("%Y-%m-%d %H:%M")
    return e["TTD_Token"]

def _app_url():
    try:
        u = st.secrets["APP_URL"]
    except Exception:
        u = ""
    return str(u or (st.session_state.get("ttd_cfg") or {}).get("app_url") or "").strip().rstrip("/")

def _admin_pin():
    try:
        return str(st.secrets["ADMIN_PIN"])
    except Exception:
        return ""

def _admin_key():
    """Kunci panjang untuk link bookmark (tanpa ketik PIN). Diisi di secrets: ADMIN_KEY."""
    try:
        return str(st.secrets["ADMIN_KEY"])
    except Exception:
        return ""

def halaman_ttd(service, token, tw):
    """Halaman publik: user melihat ringkasan servis, menandatangani di layar, ttd tersimpan ke data."""
    st.title("✍️ Konfirmasi Penerimaan Servis IT")
    st.caption("RSUD Kota Cilegon · IT SIRS")
    if st.session_state.get("_ttd_selesai"):
        st.success("✅ Terima kasih, tanda tangan Anda sudah tersimpan. Halaman ini boleh ditutup.")
        return
    keys = list(TRIWULAN_CONFIG.keys())
    try:
        cfgt = TRIWULAN_CONFIG[keys[int(tw) - 1]]
    except Exception:
        st.error("Link tidak valid.")
        return
    try:
        data, fid = load_json(service, cfgt["json_name"])
    except Exception:
        st.error("Data tidak dapat dimuat saat ini. Coba lagi sebentar lagi.")
        return
    cari = lambda d_: next((i for i, e_ in enumerate(d_) if _token_aktif(e_, token)), None)
    idx = cari(data)
    if idx is None:
        st.error("Link ini tidak valid, sudah dipakai, atau sudah kedaluwarsa. Silakan hubungi petugas IT.")
        return
    e = data[idx]
    st.markdown(f"**Tanggal:** {e.get('Tanggal') or '-'}  \n**Ruangan:** {e.get('Unit') or '-'}  \n"
                f"**Kendala:** {e.get('Kendala') or '-'}  \n**Tindakan:** {e.get('Solusi') or '-'}")
    nama = st.text_input("Nama penerima", value=e.get("Pelapor", ""), key="pub_nama")
    st.markdown("**Tanda tangan** — coret di kotak berikut dengan jari")
    pad = ttd_pad("pad_publik")
    setuju = st.checkbox("Saya menyatakan pekerjaan di atas telah dikerjakan dan hasilnya saya terima.", key="pub_setuju")
    if st.button("✅ Kirim tanda tangan", type="primary", key="pub_kirim"):
        if not nama.strip():
            st.warning("⚠️ Isi nama penerima dulu.")
        elif not pad:
            st.warning("⚠️ Coret tanda tangan dulu di kotak.")
        elif not setuju:
            st.warning("⚠️ Centang pernyataan dulu.")
        else:
            with st.spinner("Menyimpan..."):
                try:
                    data, fid = load_json(service, cfgt["json_name"])       # muat ulang (hindari menimpa perubahan lain)
                    idx = cari(data)
                    if idx is None:
                        st.error("Link ini sudah dipakai atau kedaluwarsa.")
                        return
                    data[idx]["TTD_User"] = ttd_user_to_b64(pad)
                    data[idx]["Pelapor"] = nama.strip()
                    data[idx]["TTD_Waktu"] = f"{tanggal_hari_ini()} {jam_sekarang()}"
                    data[idx].pop("TTD_Kode", None); data[idx].pop("TTD_Isi", None)
                    data[idx].pop("TTD_Token", None)
                    data[idx].pop("TTD_Token_Exp", None)
                    save_json(service, data, fid)
                except Exception:
                    st.error("Gagal menyimpan. Coba kirim sekali lagi.")
                    return
                try:                                                         # PDF diperbarui bila bisa
                    cfg_t, _ = load_ttd(service)
                    st.session_state["ttd_cfg"] = cfg_t
                    st.session_state["ttd_pengawas_nama"] = cfg_t.get("kanit_nama", "")
                    st.session_state["ttd_mode_ukuran"] = cfg_t.get("mode_ukuran", "luas")
                    upload_pdf(service, generate_pdf(data, cfgt["pdf_title"], cfgt["header"], cfgt["romawi"]),
                               cfgt["pdf_name"])
                except Exception:
                    pass
            st.session_state["_ttd_selesai"] = True
            st.rerun()

# ── UI ────────────────────────────────────────────────────────
_qp = st.query_params
if "ttd" in _qp:                                   # mode publik: HANYA halaman tanda tangan, tanpa menu admin
    halaman_ttd(get_drive_service(), _qp.get("ttd"), _qp.get("tw"))
    st.stop()

_pin = _admin_pin()                                # gerbang admin (aktif kalau ADMIN_PIN dan/atau ADMIN_KEY diisi di secrets)
_kunci = _admin_key()
_qk = str(_qp.get("k", "") or "")
if _kunci and _qk and hmac.compare_digest(_qk, _kunci):      # masuk lewat link bookmark ?k=<ADMIN_KEY>
    st.session_state["_admin_ok"] = True
if (_pin or _kunci) and not st.session_state.get("_admin_ok"):
    st.title("🔒 Masuk")
    if _pin:
        _masuk = st.text_input("PIN admin", type="password")
        if _masuk and hmac.compare_digest(_masuk, _pin):
            st.session_state["_admin_ok"] = True
            st.rerun()
        elif _masuk:
            st.error("PIN salah.")
    else:
        st.info("Buka aplikasi lewat link bookmark yang berisi kunci.")
    st.stop()

st.markdown('<div class="hero"><div class="hero-t">🖥️ Buat push dukung bukti EKIN</div>'
            '<div class="hero-s">Input laporan kendala IT dan simpan otomatis ke Google Drive</div></div>',
            unsafe_allow_html=True)

service = get_drive_service()

# ── Cek PDF yang belum ada di Drive ──────────────────────────
if "pdf_init_done" not in st.session_state:
    with st.spinner("🔍 Mengecek file PDF di Drive..."):
        missing_files = check_missing_files(service)
        if missing_files:
            st.warning(
                "⚠️ File berikut belum ada di folder Drive:\n\n" +
                "\n".join([f"- {f}" for f in missing_files]) +
                "\n\nUpload file yang kurang ke folder Drive dulu, lalu refresh."
            )
    st.session_state.pdf_init_done = True

# ── Pilih Triwulan ────────────────────────────────────────────
_kartu = st.container(border=True)
with _kartu:
    selected_triwulan = st.selectbox(
        "📅 Pilih Periode Triwulan",
        options=list(TRIWULAN_CONFIG.keys()),
        help="Pilih periode yang sesuai dengan eKinerja — Triwulan 1, 2, 3, atau 4"
    )
cfg       = TRIWULAN_CONFIG[selected_triwulan]
PDF_NAME  = cfg["pdf_name"]
PDF_TITLE = cfg["pdf_title"]
HDR_TEXT  = cfg["header"]
JSON_NAME = cfg["json_name"]
ROMAWI    = cfg["romawi"]
BULAN_TRIWULAN = cfg["bulan"]

with _kartu:
    st.caption(f"📄 PDF target: `{PDF_NAME}`")
    st.checkbox("📎 Sertakan lampiran form per tiket (1 halaman per laporan) di PDF", value=True, key="lampiran")

# Muat ttd permanen (IT & Kanit) sekali per sesi
if "ttd_cfg" not in st.session_state:
    try:
        cfg_loaded, fid_loaded = load_ttd(service)
    except Exception:
        cfg_loaded, fid_loaded = {}, None
    st.session_state.ttd_cfg = cfg_loaded
    st.session_state.ttd_fid = fid_loaded
    st.session_state.setdefault("ttd_pengawas_nama", cfg_loaded.get("kanit_nama", ""))
    st.session_state.setdefault("ttd_mode_ukuran", cfg_loaded.get("mode_ukuran", "luas"))

if not st.session_state.get("_inbox_done"):       # tarik ttd dari link khusus, sekali per sesi
    st.session_state["_inbox_done"] = True
    try:
        st.session_state["_inbox_msg"] = proses_ttd_masuk(service)
    except Exception as _ex:
        st.session_state["_inbox_msg"] = (0, 0, [str(_ex)])
_im = st.session_state.pop("_inbox_msg", None)
if _im:
    if _im[0]:
        st.success(f"📥 {_im[0]} tanda tangan dari link sudah masuk ke laporan.")
    if _im[1]:
        st.info(f"ℹ️ {_im[1]} tanda tangan dilewati karena entrinya sudah dihapus atau linknya diganti.")
    if _im[2]:
        st.warning("⚠️ Sebagian ttd belum bisa diproses: " + "; ".join(_im[2][:3]))

with st.expander("✍️ TTD Permanen IT & Kanit (upload foto sekali, tersimpan di Drive)"):
    cfg_t = st.session_state.ttd_cfg
    if not st.session_state.ttd_fid:
        st.warning(f"File `{TTD_JSON}` belum ada di folder Drive. Buat file teks kosong dengan nama itu "
                   f"(isi: `{{}}`) di folder yang sama, lalu refresh. Tanpa itu ttd permanen belum bisa disimpan.")

    st.markdown("**🔒 Permanen — IT & Kanit (upload sekali, tersimpan di Drive)**")
    p1, p2 = st.columns(2)
    with p1:
        st.caption("TTD IT (Isfan)")
        if cfg_t.get("it_img_b64"):
            st.image(base64.b64decode(cfg_t["it_img_b64"]), width=140)
        up_it = st.file_uploader("Ganti/upload TTD IT", type=["png","jpg","jpeg"], key="ttd_it_up")
        ready_it = ttd_crop_preview(up_it, "ttd_it")
    with p2:
        st.caption("TTD Kanit / Pengawas")
        if cfg_t.get("kanit_img_b64"):
            st.image(base64.b64decode(cfg_t["kanit_img_b64"]), width=140)
        up_kn = st.file_uploader("Ganti/upload TTD Kanit", type=["png","jpg","jpeg"], key="ttd_kanit_up")
        ready_kn = ttd_crop_preview(up_kn, "ttd_kanit")
        st.text_input("Nama Kanit / Pengawas (Petugas Unit SIMRS)", key="ttd_pengawas_nama")

    st.selectbox("Ukuran ttd di form", list(MODE_UKURAN_TTD.keys()), key="ttd_mode_ukuran",
                 format_func=lambda k: MODE_UKURAN_TTD[k],
                 help="Proporsi ttd tidak pernah digepengkan. Pilihan ini cuma menentukan ukuran acuannya. "
                      "Klik Simpan Permanen supaya pilihannya tersimpan.")
    if st.button("💾 Simpan Permanen ke Drive"):
        if not st.session_state.ttd_fid:
            st.error(f"❌ `{TTD_JSON}` belum ada di Drive (lihat peringatan di atas).")
        else:
            try:
                new_cfg = dict(cfg_t)
                if ready_it:
                    new_cfg["it_img_b64"] = img_to_b64(ready_it)
                if ready_kn:
                    new_cfg["kanit_img_b64"] = img_to_b64(ready_kn)
                new_cfg["kanit_nama"] = st.session_state.get("ttd_pengawas_nama", "")
                new_cfg["mode_ukuran"] = st.session_state.get("ttd_mode_ukuran", "luas")
                save_json(service, new_cfg, st.session_state.ttd_fid)
                st.session_state.ttd_cfg = new_cfg
                st.success("✅ TTD IT & Kanit tersimpan permanen.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Gagal menyimpan: {e}")

    st.caption("TTD user tidak perlu diupload: digambar langsung di layar tiap laporan (kanvas).")

st.divider()

# ── Session state untuk edit ──────────────────────────────────
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

tab1, tab2, tab3 = st.tabs(["📝 Input", "🗂️ Data", "🖨️ Form Cetak"])

# ══════════════════════════════════════════════════════════════
# TAB 1 — CREATE
# ══════════════════════════════════════════════════════════════
# Default bulan = bulan sekarang kalau masuk triwulan yang dipilih
_bln_now = BULAN_ID[datetime.now(WIB).month - 1]
if st.session_state.get("in_bulan") not in BULAN_TRIWULAN:
    st.session_state.in_bulan = _bln_now if _bln_now in BULAN_TRIWULAN else BULAN_TRIWULAN[0]

def entry_jam(e):
    return e.get("Selesai_Jam") or "-"

def _fill_form(entry):
    ss = st.session_state
    if entry["Bulan"] in BULAN_TRIWULAN:
        ss.in_bulan = entry["Bulan"]
    ss.in_unit    = entry["Unit"]
    ss.in_kendala = entry["Kendala"]
    ss.in_solusi  = entry["Solusi"]
    ss.in_pelapor = entry.get("Pelapor", "")
    d = parse_tanggal_id(entry.get("Tanggal"))
    if d:
        ss.in_tgl = d
    if entry.get("Mulai_Jam"):
        ss.in_mjam = entry["Mulai_Jam"]
    if entry.get("Selesai_Jam"):
        ss.in_sjam = entry["Selesai_Jam"]
    _auto_detail()

def _reset_input_form():
    """Kosongkan form input setelah simpan (dipanggil di awal run berikutnya)."""
    ss = st.session_state
    for k in ("in_unit", "in_kendala", "in_solusi", "in_pelapor", "in_alat",
              "in_mjam", "in_sjam", "in_lain", "in_sc"):
        ss[k] = ""
    for k, _ in JENIS_PEKERJAAN:
        ss[f"in_jn_{k}"] = False
    ss["in_tgl"] = hari_ini_wib()
    ss["_auto_prev"] = {"Peralatan": "", "Jenis": []}
    _reset_pad()

if st.session_state.pop("_reset_in", False):
    _reset_input_form()
if st.session_state.pop("_reset_wa", False):
    st.session_state["wa_text"] = ""

def _unit_hints():
    """Dari data tersimpan: (daftar ruangan yang pernah dipakai, peta nama pelapor -> ruangan paling sering)."""
    key = f"_ku_{JSON_NAME}"
    if key not in st.session_state:
        try:
            d_, _ = load_json(service, JSON_NAME)
        except Exception:
            d_ = []
        units = sorted({(e_.get("Unit") or "").strip() for e_ in d_ if e_.get("Unit")})
        cnt = {}
        for e_ in d_:
            pl, un = (e_.get("Pelapor") or "").strip().lower(), (e_.get("Unit") or "").strip()
            if pl and un:
                cnt.setdefault(pl, Counter())[un] += 1
        st.session_state[key] = (units, {pl: c.most_common(1)[0][0] for pl, c in cnt.items()})
    return st.session_state[key]

def _known_units():
    return _unit_hints()[0]

with tab1:
    with st.expander("📋 Paste laporan dari WhatsApp"):
        st.caption("Bisa tempel **chat WA langsung** (salin pesan apa adanya, termasuk jam & nama pengirim): "
                   "nama ruangan dibaca dari isi pesan, jam mulai dari jam pesan user, jam selesai dari jam "
                   "balasan IT. Format berlabel (`Unit:` `Kendala:` `Solusi:`) juga masih bisa.")
        c_it, c_sc = st.columns(2)
        with c_it:
            it_txt = st.text_input("Nama IT di WA (pisahkan koma)", value="Isfan", key="wa_it",
                                   help="Pesan dari nama ini dianggap balasan IT (solusi + jam selesai).")
        with c_sc:
            scope = st.selectbox("Balasan IT berlaku untuk",
                                 ["Semua laporan yang belum terjawab", "Hanya laporan terakhir"], key="wa_scope")
        wa_text = st.text_area("Tempel teks WA di sini", height=180, key="wa_text")
        if wa_text.strip():
            parsed = parse_wa_report(wa_text, st.session_state.in_bulan, known_units=_known_units(),
                                     it_names=[x.strip() for x in it_txt.split(",")],
                                     reply_all=scope.startswith("Semua"),
                                     pelapor_units=_unit_hints()[1])
            plus = st.selectbox("Jam selesai (perkiraan) untuk entri yang punya jam pesan WA",
                                ["Kosongkan", "+15 menit", "+30 menit", "+45 menit", "+60 menit"],
                                key="wa_plus",
                                help="Jam mulai diambil dari jam pesan WA. Jam selesai tidak ada di pesan, "
                                     "jadi default dikosongkan; pilih kalau mau diisi perkiraan.")
            if plus != "Kosongkan":
                tambah = int(plus.split()[0].replace("+", ""))
                for e_ in parsed:
                    mu = _jam_ke_menit(e_.get("Mulai_Jam"))
                    if mu is not None and not e_.get("Selesai_Jam"):
                        e_["Selesai_Jam"] = _menit_ke_jam(mu + tambah)
            luar = [e for e in parsed if e["Bulan"] not in BULAN_TRIWULAN]
            if luar:
                for e in luar:
                    e["Bulan"] = st.session_state.in_bulan
                st.warning(f"⚠️ {len(luar)} entri menyebut bulan di luar {selected_triwulan}. "
                           f"Bulannya diganti ke **{st.session_state.in_bulan}**. "
                           f"Kalau salah, pilih triwulan yang benar di atas.")
            st.write(f"Terbaca **{len(parsed)}** entri:")
            st.dataframe(parsed)
            tanpa_tgl = [e for e in parsed if not e.get("Tanggal")]
            if tanpa_tgl:
                st.info(f"ℹ️ {len(tanpa_tgl)} entri tidak punya tanggal di teks WA (tidak ada `Tanggal:` / "
                        f"timestamp chat). Tanggalnya dibiarkan kosong, bukan diisi hari ini. "
                        f"Isi lewat tab Edit kalau perlu.")
            lengkap = all(e["Unit"] and e["Kendala"] for e in parsed)
            if not lengkap:
                st.warning("⚠️ Ada entri yang ruangan/kendalanya kosong. Pakai **Isi ke form** lalu lengkapi manual.")
            tanpa_solusi = [e for e in parsed if not e["Solusi"]]
            if tanpa_solusi:
                st.info(f"ℹ️ {len(tanpa_solusi)} entri belum ada solusi (belum ada balasan IT di teks yang ditempel). "
                        f"Bisa dilengkapi lewat tab Edit. Cek juga kolom **Nama IT di WA** di atas kalau balasan harusnya kebaca.")
            w1, w2 = st.columns(2)
            with w1:
                st.button("📝 Isi ke form (entri pertama)", on_click=_fill_form, args=(parsed[0],))
            with w2:
                if st.button(f"✅ Simpan semua ({len(parsed)}) ke laporan", disabled=not lengkap):
                    with st.spinner("Menyimpan ke Drive..."):
                        try:
                            data, fid = load_json(service, JSON_NAME)
                            parsed = [lengkapi_entry(dict(e_), live=False)[0] for e_ in parsed]
                            ada = {(d_.get("Tanggal"), d_.get("Mulai_Jam"), (d_.get("Unit") or "").lower())
                                   for d_ in data if d_.get("Tanggal") and d_.get("Mulai_Jam")}
                            baru = [e_ for e_ in parsed
                                    if (e_.get("Tanggal"), e_.get("Mulai_Jam"), e_["Unit"].lower()) not in ada]
                            lewat = len(parsed) - len(baru)
                            data = urutkan(data + baru)
                            save_json(service, data, fid)
                            upload_pdf(service, generate_pdf(data, PDF_TITLE, HDR_TEXT, ROMAWI), PDF_NAME)
                            st.session_state["_flash"] = (
                                f"✅ {len(baru)} entri ditambahkan. **{PDF_NAME}** diperbarui di Drive."
                                + (f"  \nℹ️ {lewat} entri dilewati karena sudah ada (tanggal, jam, dan ruangan sama)."
                                   if lewat else ""))
                            st.session_state["_reset_wa"] = True
                            st.session_state.pop(f"_ku_{JSON_NAME}", None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Terjadi kesalahan: {e}")

    if "_flash" in st.session_state:
        st.success(st.session_state.pop("_flash"))

    bulan   = st.selectbox("Bulan", BULAN_TRIWULAN, key="in_bulan")
    unit    = st.text_input("Lokasi / Unit", key="in_unit")
    kendala = st.text_area("Jenis Kendala / Pekerjaan", key="in_kendala", on_change=_auto_detail)
    solusi  = st.text_area("Tindakan / Solusi", key="in_solusi", on_change=_auto_detail)
    pelapor = st.text_input("Nama Pelapor / User", key="in_pelapor")
    detail  = detail_inputs("in")

    st.markdown("**✍️ TTD User** — sodorkan HP, user coret pakai jari")
    pad_new = ttd_pad("pad_new")
    if pad_new:
        st.caption("✅ ttd terbaca, siap disimpan bersama laporan.")

    col1, col2 = st.columns(2)
    with col1: preview_btn = st.button("🔍 Preview PDF")
    with col2: submit_btn  = st.button("✅ Konfirmasi & Update Laporan", type="primary")

    def _entri_baru():
        e_ = {"Bulan": bulan, "Unit": unit, "Kendala": kendala, "Solusi": solusi,
              "Pelapor": pelapor,
              "TTD_User": ttd_user_to_b64(pad_new) if pad_new else "", **detail}
        return lengkapi_entry(e_, live=True)

    if preview_btn:
        if not unit or not kendala or not solusi:
            st.warning("⚠️ Isi semua field dulu untuk preview.")
        else:
            data, _ = load_json(service, JSON_NAME)
            entri, warn = _entri_baru()
            for w_ in warn: st.warning("⚠️ " + w_)
            st.info(f"👁️ Preview {len(data)+1} entri (belum tersimpan ke Drive)")
            show_pdf_preview(generate_pdf(urutkan(data + [entri]), PDF_TITLE, HDR_TEXT, ROMAWI))

    if submit_btn:
        if not unit or not kendala or not solusi:
            st.warning("⚠️ Mohon isi semua field sebelum submit.")
        else:
            with st.spinner("Menyimpan ke Drive..."):
                try:
                    data, fid = load_json(service, JSON_NAME)
                    entri, warn = _entri_baru()
                    data = urutkan(data + [entri])
                    save_json(service, data, fid)
                    upload_pdf(service, generate_pdf(data, PDF_TITLE, HDR_TEXT, ROMAWI), PDF_NAME)
                    ket = (f"{entri['Tanggal']} | jam {entri.get('Mulai_Jam') or '-'}–{entry_jam(entri)} | "
                           f"peralatan: {entri.get('Peralatan') or '-'} | "
                           f"jenis: {', '.join(entri.get('Jenis', [])) or '-'}")
                    st.session_state["_flash"] = (f"✅ Tersimpan. **{PDF_NAME}** diperbarui di Drive.  \n"
                                                  f"📝 {ket}" + ("".join(f"  \n⚠️ {w_}" for w_ in warn)))
                    st.session_state["_reset_in"] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Terjadi kesalahan: {e}")

# ══════════════════════════════════════════════════════════════
# TAB 2 — READ / UPDATE / DELETE
# ══════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📋 Data Laporan Tersimpan")
    data, fid = load_json(service, JSON_NAME)
    data = urutkan(data)

    if not data:
        st.info("Belum ada data tersimpan.")
    else:
        st.write(f"Total entri: **{len(data)}**")
        col_prev, col_upd = st.columns(2)
        with col_prev:
            if st.button("🔍 Preview PDF Tersimpan"):
                show_pdf_preview(generate_pdf(data, PDF_TITLE, HDR_TEXT, ROMAWI))
        with col_upd:
            if st.button("🔄 Update Ulang PDF ke Drive"):
                with st.spinner("Membuat ulang PDF dengan format terbaru..."):
                    upload_pdf(service, generate_pdf(data, PDF_TITLE, HDR_TEXT, ROMAWI), PDF_NAME)
                st.success("PDF berhasil diperbarui ke Drive dengan format terbaru ✅")

        if st.button("📥 Tarik ttd masuk dari link"):
            with st.spinner("Memeriksa kotak masuk ttd..."):
                try:
                    st.session_state["_inbox_msg"] = proses_ttd_masuk(service)
                except Exception as _ex:
                    st.session_state["_inbox_msg"] = (0, 0, [str(_ex)])
            st.session_state["_inbox_done"] = True
            st.rerun()

        if st.button("🖼️ Siapkan ZIP Bukti Terima Kasih per folder bulan (PNG)"):
            from PIL import Image as PILImage, ImageDraw, ImageFont
            def _buat_kartu_terimakasih(e_):
                W, H = 900, 320
                im = PILImage.new("RGB", (W, H), "#F4F6F8")
                dr = ImageDraw.Draw(im)
                dr.rectangle([0, 0, W, 72], fill="#1A5276")
                dr.rectangle([0, 72, W, 78], fill="#F39C12")
                f_hdr = ImageFont.load_default()
                dr.text((24, 18), "Konfirmasi Penerimaan Servis IT", fill="#FFFFFF", font=f_hdr)
                dr.text((24, 42), "RSUD Kota Cilegon - IT SIRS", fill="#D6EAF8", font=f_hdr)
                dr.rounded_rectangle([140, 115, W - 140, 275], radius=14, fill="#E8F6EE", outline="#B7E4C7", width=2)
                dr.text((W // 2, 155), "Terima kasih.", fill="#1E8449", font=f_hdr, anchor="mm")
                dr.text((W // 2, 185), "Tanda tangan Anda sudah tersimpan.", fill="#1E8449", font=f_hdr, anchor="mm")
                dr.text((W // 2, 215), "Halaman ini boleh ditutup.", fill="#1E8449", font=f_hdr, anchor="mm")
                info = f"{e_.get('Pelapor') or '-'} | {e_.get('Unit') or '-'} | {e_.get('Tanggal') or '-'}"
                dr.text((W // 2, 248), info, fill="#566573", font=f_hdr, anchor="mm")
                out = io.BytesIO()
                im.save(out, "PNG")
                return out.getvalue()

            zbuf = io.BytesIO()
            jml = 0
            with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
                for e_ in data:
                    if e_.get("TTD_User"):
                        bln = bulan_entri(e_)
                        if not bln or bln == "-":
                            bln = "Lainnya"
                        tgl = re.sub(r"[\\/:*?\"<>|']", "-", str(e_.get("Tanggal") or "tanpa_tgl")).strip()
                        unit = re.sub(r"[\\/:*?\"<>|']", "_", str(e_.get("Unit") or "Unit")).strip()
                        nama = re.sub(r"[\\/:*?\"<>|']", "_", str(e_.get("Pelapor") or "User")).strip()
                        zf.writestr(f"{bln}/Bukti_{tgl}_{unit}_{nama}.png", _buat_kartu_terimakasih(e_))
                        jml += 1
            st.session_state["_ttd_zip"] = zbuf.getvalue()
            st.success(f"✅ {jml} gambar bukti Terima Kasih siap didownload (terkelompok per folder bulan).")
        if st.session_state.get("_ttd_zip"):
            st.download_button("📥 Download ZIP Bukti Terima Kasih (PNG)", data=st.session_state["_ttd_zip"],
                               file_name=f"Bukti_TerimaKasih_{PDF_NAME.replace('.pdf', '.zip')}", mime="application/zip")

        # ── Download rekap SEMUA FORM (tanpa halaman tabel ringkasan) ──
        _sig_data = hash(json.dumps(data, sort_keys=True, default=str))
        col_siap, col_dl = st.columns(2)
        with col_siap:
            if st.button("📄 Siapkan Download Semua Form"):
                with st.spinner("Menyusun semua form..."):
                    st.session_state["_form_pdf"] = generate_pdf(
                        data, PDF_TITLE, HDR_TEXT, ROMAWI, hanya_form=True).getvalue()
                    st.session_state["_form_pdf_hash"] = _sig_data
        with col_dl:
            if st.session_state.get("_form_pdf") and st.session_state.get("_form_pdf_hash") == _sig_data:
                st.download_button("📥 Download Semua Form (PDF)", data=st.session_state["_form_pdf"],
                                   file_name=f"Form_Servis_{PDF_NAME}", mime="application/pdf")
            elif st.session_state.get("_form_pdf"):
                st.caption("Data berubah — klik **Siapkan** lagi biar file terbaru.")

        st.divider()

        _gas_now = _ttd_url()
        with st.expander("⚙️ Ubah URL Apps Script", expanded=not _gas_now):
            st.caption(f"URL aktif: {_gas_now or '(belum diatur)'}")
            _u_in = st.text_input("URL web app Apps Script", key="ttd_url_in",
                                  placeholder="https://script.google.com/macros/s/.../exec")
            if st.button("Simpan URL Apps Script", key="ttd_url_save") and _u_in.strip():
                if not url_apps_script_valid(_u_in.strip()):
                    st.error("URL harus berawalan https://script.google.com/ dan berakhiran /exec "
                             "(bukan /edit atau /dev).")
                elif not st.session_state.get("ttd_fid"):
                    st.error("File ttd_config.json belum ada di Drive.")
                else:
                    _c = dict(st.session_state.ttd_cfg); _c["ttd_url"] = _u_in.strip()
                    save_json(service, _c, st.session_state.ttd_fid)
                    st.session_state.ttd_cfg = _c
                    st.success("✅ URL Apps Script tersimpan.")
                    st.rerun()

        BULAN_OPTIONS = BULAN_TRIWULAN

        opsi_filter = ["Semua"] + BULAN_TRIWULAN
        if st.session_state.get("filter_bulan") not in opsi_filter:
            st.session_state["filter_bulan"] = "Semua"
        filter_b = st.selectbox("Filter bulan", opsi_filter, key="filter_bulan")
        bulan_sebelumnya = None
        _css_daftar()

        for i, entry in enumerate(data):
            bln_e = bulan_entri(entry)
            if filter_b != "Semua" and bln_e != filter_b:
                continue
            if filter_b == "Semua" and bln_e != bulan_sebelumnya and st.session_state.edit_index != i:
                st.markdown(f"##### 📆 {bln_e}")
                bulan_sebelumnya = bln_e
            # ── Mode EDIT aktif untuk baris ini ──────────────
            if st.session_state.edit_index == i:
                with st.container(border=True):
                    st.markdown(f"#### ✏️ Edit Entri #{i+1}")
                    with st.expander("✍️ TTD User — coret di layar (kosong = tidak berubah)"):
                        pad_edit = ttd_pad(f"pad_e{i}")
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
                        e_pelapor = st.text_input("Nama Pelapor / User",
                                                  value=entry.get("Pelapor",""))
                        if entry.get("TTD_User"):
                            st.caption("TTD tersimpan saat ini:")
                            st.image(base64.b64decode(entry["TTD_User"]), width=120)
                        e_detail = detail_inputs(f"e{i}", entry)
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
                                    data[i], _w = lengkapi_entry({
                                        **entry,
                                        "Bulan":   e_bulan,
                                        "Unit":    e_unit,
                                        "Kendala": e_kendala,
                                        "Solusi":  e_solusi,
                                        "Pelapor": e_pelapor,
                                        "TTD_User": ttd_user_to_b64(pad_edit) if pad_edit
                                                    else entry.get("TTD_User", ""),
                                        **e_detail,
                                    }, live=False)
                                    for w_ in _w: st.warning("⚠️ " + w_)
                                    if pad_edit:                       # ttd diganti: kode verifikasi lama tidak berlaku
                                        data[i].pop("TTD_Kode", None); data[i].pop("TTD_Isi", None)
                                    data = urutkan(data)
                                    save_json(service, data, fid)
                                    upload_pdf(service, generate_pdf(data, PDF_TITLE, HDR_TEXT, ROMAWI), PDF_NAME)
                                    st.success("✅ Entri berhasil diperbarui!")
                                    _reset_pad()
                                    st.session_state.edit_index = None
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Gagal menyimpan: {e}")

                    if cancel_edit:
                        st.session_state.edit_index = None
                        st.rerun()

            # ── Mode NORMAL (tampil biasa + tombol Edit/Hapus) ─
            else:
                sudah_ttd = bool(entry.get("TTD_User"))
                with st.container(border=True):
                    st.markdown(f"**{i+1}. {entry.get('Unit','-')}**")
                    st.caption(f"📅 {entry.get('Tanggal') or '⚠️ tanggal belum diisi'}  ·  "
                               f"🕘 {entry.get('Mulai_Jam') or '-'}–{entry.get('Selesai_Jam') or '-'}")
                    st.markdown(f"🔧 **Kendala:** {entry.get('Kendala','-')}  \n"
                                f"✅ **Tindakan:** {entry.get('Solusi','-')}")
                    st.markdown(f"👤 {entry.get('Pelapor') or '-'}  ·  "
                                + (":green[✍️ Sudah TTD]" if sudah_ttd else ":orange[▫️ Belum TTD]"))
                    if _token_aktif(entry):
                        st.caption(f"🔗 Link TTD aktif s.d. {entry.get('TTD_Token_Exp')}")
                    if entry.get("TTD_Kode"):
                        _utuh = entry.get("TTD_Isi") == _isi_digest(entry)
                        st.caption(f"🔐 Kode verifikasi: {entry['TTD_Kode']}"
                                   + ("" if _utuh else " · ⚠️ isi diubah setelah TTD"))

                    if st.session_state.get("_hapus_i") == i:
                        st.warning("Hapus entri ini? Tidak bisa dibatalkan.")
                        c_ya, c_batal = _baris_aksi(2)
                        with c_ya:
                            if st.button("🗑️ Ya, hapus", key=f"delyes_{i}", type="primary"):
                                with st.spinner("Menghapus..."):
                                    new_data = [e for j, e in enumerate(data) if j != i]
                                    save_json(service, new_data, fid)
                                    upload_pdf(service, generate_pdf(new_data, PDF_TITLE, HDR_TEXT, ROMAWI), PDF_NAME)
                                    st.session_state.pop("_hapus_i", None)
                                    st.success("✅ Dihapus!")
                                    st.rerun()
                        with c_batal:
                            if st.button("✖ Batal", key=f"delno_{i}"):
                                st.session_state.pop("_hapus_i", None)
                                st.rerun()
                    else:
                        cols = _baris_aksi(2 if sudah_ttd else 3)
                        k = 0
                        with cols[k]:
                            if st.button("✏️ Edit", key=f"edit_{i}", help="Edit entri ini"):
                                st.session_state.pop("_hapus_i", None)
                                st.session_state.edit_index = i
                                st.rerun()
                        if not sudah_ttd:
                            k += 1
                            with cols[k]:
                                if st.button("🔗 Link TTD", key=f"lnk_{i}",
                                             help="Minta ttd user lewat link (kirim ke WhatsApp)"):
                                    try:
                                        if not _token_aktif(entry):
                                            _buat_token(data[i])
                                            save_json(service, data, fid)
                                        st.session_state["_link_token"] = data[i]["TTD_Token"]
                                    except Exception as ex_:
                                        st.error(f"❌ Gagal membuat link: {ex_}")
                                    st.session_state.pop("_hapus_i", None)
                                    st.rerun()
                        k += 1
                        with cols[k]:
                            if st.button("🗑️ Hapus", key=f"del_{i}", help="Hapus entri ini"):
                                st.session_state["_hapus_i"] = i
                                st.rerun()

    # ── Blok link ttd (muncul setelah tombol 🔗 ditekan) ──────
    _tk = st.session_state.get("_link_token")
    _ent = next((e_ for e_ in data if _token_aktif(e_, _tk)), None) if _tk else None
    if _ent:
        with st.container(border=True):
            st.markdown(f"**🔗 Link tanda tangan — {_ent.get('Unit','-')}, {_ent.get('Tanggal') or '-'}**")
            _gas, _url = _ttd_url(), _app_url()
            _tw = list(TRIWULAN_CONFIG.keys()).index(selected_triwulan) + 1
            if _gas:
                _link = f"{_gas}?t={_ent['TTD_Token']}&tw={_tw}"
            elif _url:
                _link = f"{_url}/?ttd={_ent['TTD_Token']}&tw={_tw}"      # cadangan: membuka halaman di Streamlit
            else:
                _link = ""
            if not _gas:
                st.info("Mau link khusus yang tidak membuka Streamlit (tidak perlu menunggu app bangun)? "
                        "Tempel URL web app Apps Script di menu **⚙️ Ubah URL Apps Script** di atas.")
            if _link:
                _sap = st.selectbox("Panggilan penerima", ["Bapak/Ibu", "Bapak", "Ibu", "Teh", "Mas", "Mbak", "Dokter"],
                                    key=f"sapaan_{_ent.get('TTD_Token')}",
                                    help="Dipakai di salam pesan WhatsApp, misalnya: Assalamualaikum, Teh Nuning.")
                st.code(_link, language=None)
                _nama = str(_ent.get("Pelapor") or "").strip()
                _sapa = f"{_sap} {_nama}" if _nama and _nama != "-" else _sap
                _unit = str(_ent.get("Unit") or "").strip()
                _tgl = str(_ent.get("Tanggal") or "").strip()
                _di = f" di {_unit}" if _unit and _unit != "-" else ""
                _pada = f" pada {_tgl}" if _tgl and _tgl != "-" else ""
                _pesan = (f"Assalamualaikum, {_sapa}. Saya Isfan dari IT SIRS RSUD Kota Cilegon.\n\n"
                          f"Kami mohon konfirmasi bahwa tim IT sudah membantu{_di}{_pada}. "
                          f"Mohon tanda tangan di link berikut:\n{_link}\n\n"
                          f"Caranya: buka link, cek nama, tanda tangan dengan jari, centang pernyataan, "
                          f"lalu tekan Kirim. Setelah itu selesai, tidak perlu mengirim screenshot atau balasan ke saya. "
                          f"Link hanya bisa dipakai sekali.\n\n"
                          f"Terima kasih atas waktunya 🙏")
                st.markdown(f"[📲 Kirim via WhatsApp](https://wa.me/?text={quote(_pesan)})")
                st.caption(f"Sekali pakai, berlaku sampai {_ent.get('TTD_Token_Exp')} WIB. "
                           f"Yang membuka link hanya bisa menandatangani laporan ini.")

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
                    existing, fid_ex = load_json(service, JSON_NAME)
                    merged = urutkan(data_awal + existing)
                    save_json(service, merged, fid_ex)
                    upload_pdf(service, generate_pdf(merged, PDF_TITLE, HDR_TEXT, ROMAWI), PDF_NAME)
                    st.success(f"✅ Berhasil! Total sekarang {len(merged)} entri. Data lama tetap aman.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Gagal: {e}")


# ══════════════════════════════════════════════════════════════
# TAB 3 — Form cetak untuk tanda tangan basah
# ══════════════════════════════════════════════════════════════
def _cetak_pilih(idxs, val):
    for i_ in idxs:
        st.session_state[f"cetak_{i_}"] = val

with tab3:
    st.markdown("#### 🖨️ Form untuk tanda tangan basah")
    st.caption("Untuk laporan yang user-nya belum tanda tangan digital (atau kalau diminta dicetak). "
               "Ttd digital tetap dipakai untuk laporan EKIN; menu ini cuma menyiapkan form kosong-ttd untuk dicetak.")
    try:
        data_c, _ = load_json(service, JSON_NAME)
        data_c = urutkan(data_c)
    except Exception as e_:
        data_c = []
        st.error(f"❌ Gagal memuat data: {e_}")
    if not data_c:
        st.info("Belum ada data laporan.")
    else:
        semua = st.checkbox("Tampilkan juga yang sudah ttd digital", key="cetak_semua")
        opsi_c = ["Semua"] + BULAN_TRIWULAN
        if st.session_state.get("cetak_bulan") not in opsi_c:
            st.session_state["cetak_bulan"] = "Semua"
        fb_c = st.selectbox("Filter bulan", opsi_c, key="cetak_bulan")
        idxs = [i for i, e_ in enumerate(data_c)
                if (semua or not e_.get("TTD_User")) and (fb_c == "Semua" or bulan_entri(e_) == fb_c)]
        if not idxs:
            st.success("✅ Semua entri sudah punya ttd user digital.")
        else:
            st.write(f"**{len(idxs)}** entri" + ("" if semua else " belum ada ttd user") + ":")
            b1, b2 = st.columns(2)
            with b1: st.button("☑️ Pilih semua", on_click=_cetak_pilih, args=(idxs, True), key="cetak_all")
            with b2: st.button("⬜ Kosongkan pilihan", on_click=_cetak_pilih, args=(idxs, False), key="cetak_none")
            for i in idxs:
                e_ = data_c[i]
                st.checkbox(f"{i+1}. {e_.get('Tanggal') or '— tanggal kosong'} | {e_.get('Unit') or '-'} | "
                            f"{e_.get('Pelapor') or '-'}  {'✍️ sudah ttd' if e_.get('TTD_User') else '▫️ belum ttd'}",
                            key=f"cetak_{i}")
            pilih = [i for i in idxs if st.session_state.get(f"cetak_{i}")]
            kosong_staf = st.checkbox("Kosongkan juga ttd IT & Kanit (semua ttd basah)", value=True,
                                      key="cetak_kosong_staf")
            sig_c = hash((tuple(pilih), kosong_staf, json.dumps([data_c[i] for i in pilih], sort_keys=True, default=str)))
            if st.button(f"📄 Siapkan {len(pilih)} form untuk dicetak", disabled=not pilih, key="cetak_siap"):
                with st.spinner("Menyusun form..."):
                    st.session_state["_cetak_pdf"] = generate_pdf(
                        [data_c[i] for i in pilih], PDF_TITLE, HDR_TEXT, ROMAWI,
                        hanya_form=True, cetak=True, tanpa_ttd_staf=kosong_staf).getvalue()
                    st.session_state["_cetak_hash"] = sig_c
            if st.session_state.get("_cetak_pdf") and st.session_state.get("_cetak_hash") == sig_c and pilih:
                st.download_button("📥 Download Form Cetak (PDF)", data=st.session_state["_cetak_pdf"],
                                   file_name="Form_Cetak.pdf", mime="application/pdf", key="cetak_dl")
            elif st.session_state.get("_cetak_pdf"):
                st.caption("Pilihan berubah — klik **Siapkan** lagi biar file terbaru.")
