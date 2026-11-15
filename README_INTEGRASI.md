# PestCycle AI — Integrated MVP

Dashboard pemantauan WBC Jawa Timur yang menggabungkan:
- NASA POWER harian per 38 kabupaten/kota, 1 Januari 2020–31 Oktober 2026.
- Rekap observasi SiPerDitTan Januari–Oktober 2026 (38 kabupaten/kota).
- Prakiraan BBPOPT 2022–2025, tetap dipisahkan dari data observasi.
- Ringkasan evaluasi awal model klasifikasi dan regresi.

## Menjalankan di Windows

### 1. Backend (Terminal PowerShell pertama)
```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```
API: http://127.0.0.1:8000  
Dokumentasi API: http://127.0.0.1:8000/docs

### 2. Frontend (Terminal PowerShell kedua, dari folder utama)
```powershell
npm install
npm run dev
```
Buka alamat yang muncul, biasanya http://localhost:5173.

## Catatan interpretasi
- Data cuaca NASA POWER yang dipakai dashboard adalah agregasi harian per 38 kabupaten/kota.
- Rekap SiPerDitTan merupakan observasi WBC Januari–Oktober 2026.
- Prakiraan BBPOPT bukan kejadian aktual.
- Evaluasi model masih eksperimental. Klasifikasi memiliki hasil awal yang menjanjikan, tetapi regresi luas serangan belum layak untuk keputusan operasional.
- Dashboard menampilkan kondisi dan rekap aktual; bukan klaim prediksi risiko operasional tervalidasi.
