# PestCycle AI — Dashboard Terintegrasi

Versi ini mempertahankan antarmuka dashboard awal `PestCycle_AI_Web_v1` (peta interaktif 38 kabupaten/kota Jawa Timur, Wilayah Saya, dan Prediksi WBC) serta menggunakan backend dan dataset dari `PestCycleAI_Web_Integrated`.

## Menjalankan aplikasi (Windows)
1. Ekstrak ZIP ke folder lokal.
2. Pastikan Python 3.10+ dan Node.js sudah terpasang.
3. Jalankan `RUN_PESTCYCLE.bat`.
4. Buka `http://localhost:5173`.

Jika file batch tidak membuka keduanya, jalankan manual:
- Terminal 1: `cd backend` lalu `run_api.bat`
- Terminal 2 (folder utama): `npm.cmd install` lalu `npm.cmd run dev`

API tersedia di `http://127.0.0.1:8000`; dokumentasi API di `/docs`.

## Data yang terhubung
- Cuaca NASA POWER regional Jawa Timur 2020–31 Oktober 2026.
- Observasi WBC SiPerDitTan 38 kabupaten/kota, Januari–Oktober 2026.
- Prakiraan BBPOPT tersedia melalui endpoint API terpisah.
- Metrik evaluasi model dua tahap ditampilkan sebagai evaluasi eksperimental.

## Catatan interpretasi penting
- Peta menampilkan skala relatif luas serangan pada bulan observasi terakhir yang tersedia; warna bukan ambang risiko resmi.
- Grafik tren menampilkan luas serangan aktual (hektare), bukan populasi ekor/m².
- Data 2026 berhenti pada Oktober pada arsip yang disertakan.
- Model AI dan metriknya masih eksperimental. Hasil prediksi belum tervalidasi untuk keputusan pengendalian operasional.
- Dashboard memerlukan backend tetap berjalan selama frontend digunakan.

## Struktur
- `src/`, `public/`: frontend asli beserta gambar 38 wilayah dan koordinat peta.
- `backend/`: FastAPI dan skrip pemrosesan.
- `data/`: dataset NASA POWER, SiPerDitTan, BBPOPT, audit, dan metrik.
- `models/`: artefak model hasil training.
