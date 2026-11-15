# PestCycle AI Web v1.0

Prototipe antarmuka website untuk sistem pemantauan dan prediksi Wereng Batang Cokelat (WBC) di Jawa Timur.

## Fitur
- Dua fitur utama: **Wilayah Saya** dan **Prediksi WBC**.
- Pemilihan kabupaten/kota.
- Pemilihan rentang tanggal pada halaman prediksi.
- Peta risiko Jawa Timur (saat ini berupa ilustrasi skematis, bukan batas administrasi GIS resmi).
- Grafik tren populasi, indikator risiko, perbandingan wilayah, dan rekomendasi.
- Notifikasi singkat (toast) dan panel riwayat notifikasi.
- Desain responsif untuk desktop dan ponsel.
- Tidak ada login, registrasi, atau menu profil.

## Menjalankan di komputer
Persyaratan: Node.js 18 atau lebih baru.

1. Ekstrak ZIP.
2. Buka terminal pada folder proyek.
3. Jalankan:
   ```bash
   npm install
   npm run dev
   ```
4. Buka alamat yang ditampilkan Vite, biasanya `http://localhost:5173`.

Untuk membuat versi produksi:
```bash
npm run build
```
Hasil build berada di folder `dist`.

## Struktur
```text
PestCycle_AI_Web_v1/
├── index.html
├── package.json
├── README.md
└── src/
    ├── App.jsx
    ├── main.jsx
    └── styles.css
```

## Catatan data dan model
Seluruh angka, grafik, skor risiko, dan isi notifikasi dalam prototipe ini adalah **data simulasi untuk demonstrasi antarmuka**. Prototipe ini belum terhubung ke dataset NASA/WBC, belum menjalankan model Machine Learning, belum memakai geolocation browser, dan belum mengirim push notification sungguhan.

Sebelum dipakai untuk keputusan pertanian:
- Ganti data contoh di `src/App.jsx` dengan data hasil audit dan integrasi.
- Ganti peta skematis `EastJavaMap` dengan GeoJSON batas kabupaten/kota Jawa Timur yang tervalidasi.
- Definisikan dan validasi ambang risiko berdasarkan pedoman POPT/instansi berwenang.
- Hubungkan hasil model AI yang telah diuji dengan validasi berbasis waktu.
- Pastikan rekomendasi pengendalian mengacu pada pedoman resmi dan pengamatan lapangan.
