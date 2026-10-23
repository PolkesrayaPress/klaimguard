# Spesifikasi Benchmark v2 KlaimGuard (pra-registrasi)

Dokumen ini di-commit **sebelum** generator v2 ditulis dan sebelum detektor dijalankan padanya. Timestamp commit adalah buktinya. Tim beranggota satu orang, jadi pemisahan penulis generator dan detektor (Rule 1, healthkathon-eval-kit) diganti dengan pra-registrasi ini.

Detektor yang diuji: `detect.py` versi commit ini (v1.1: aturan tumpang tindih tidak lagi menandai rujukan pada hari yang sama). Setiap perubahan detektor sesudah hasil terlihat dilaporkan sebagai versi baru, bukan menimpa hasil ini.

## 1. Data

- Semua data sintetis. Tidak ada data peserta nyata.
- 10.000 klaim, 12 RS fiktif. **3 RS tanpa fraud sama sekali**, salah satunya RS kelas A rujukan.
- ID peserta, ID klaim, dan urutan baris diacak, sehingga tidak ada yang menyandikan label.
- Label disimpan di `truth.csv` terpisah (entity_id, label, modus, excess_rupiah). Detektor tidak pernah membacanya.
- Klaim normal identik di semua kondisi (seed sama); yang berubah hanya fraud yang disisipkan.

## 2. Kondisi (satu dial diubah sekali waktu, Rule 2)

| Kode | Tingkat fraud | Sebaran | Kesulitan upcoding |
|---|---|---|---|
| D0 baseline | 2% | menyebar di 9 RS | sedang |
| D1 | 1% | menyebar | sedang |
| D2 | 5% | menyebar | sedang |
| D3 | 2% | terkumpul di 2 RS | sedang |
| D4 | 2% | menyebar | halus (pergeseran keparahan kecil) |

Tingkat fraud nyata BPJS tidak diketahui tim; karena itu dilaporkan tiga tingkat (Rule 4). Data uji tidak diseimbangkan.

## 3. Modus fraud

Dikenal aturan: tumpang tindih lintas faskes, pecah episode, upcoding tingkat RS, phantom (rawat inap 0 hari), inkonsistensi demografi.

**Modus held-out (tidak ada aturan untuknya):** lama rawat digelembungkan, yaitu lama rawat 2 sampai 3 kali median diagnosisnya dengan tagihan ikut naik. Modus ini dipakai untuk menguji apakah komponen model (IsolationForest) menangkap pola yang tidak dikenal aturan.

## 4. Kasus jujur yang mirip fraud (hard negatives, Rule 3)

Semua berlabel normal:

1. Rujukan antar-RS pada hari yang sama (pulang RS A tanggal X, masuk RS B tanggal X).
2. RS kelas A rujukan dengan porsi keparahan III tinggi secara wajar.
3. Rawat ulang terjadwal yang sah: kemoterapi dan transfusi berkala, jeda 14 sampai 28 hari.
4. Rawat ulang sah dalam 7 hari dengan diagnosis sama (komplikasi). Secara data ini tidak bisa dibedakan dari pecah episode; sengaja dimasukkan untuk mengukur ongkos salah tandainya.
5. Diagnosis langka berbiaya tinggi yang wajar.
6. RS baru bervolume kecil.

## 5. Kalibrasi (Rule 5)

Belum dikalibrasi ke statistik publik. Tarif, kode INA-CBG, lama rawat, dan sebaran keparahan **dikarang oleh tim** dan dilabeli begitu di setiap laporan. Struktur kolom mengikuti Data Sampel BPJS (kode FKL dan PSTV).

## 6. Kapasitas dan metrik

- Kapasitas audit utama: **2% klaim** (200 dari 10.000). Ini asumsi tim, belum bersumber dari verifikator; dilaporkan juga pada 1% dan 5%.
- Metrik (healthkathon-eval-kit, bootstrap 1.000 kali dengan resampling per RS): presisi@k dengan rentang 95%, lift atas acak, recall@k, recall rupiah, PR-AUC, recall per modus, porsi RS jujur yang ikut teraudit per kelas RS.
- Uji tekanan: leakage scan (ambang AUC 0,80), uji permutasi label, ablation berpasangan.

## 7. Hipotesis yang dikunci sekarang

- **H1.** Pada D0, presisi@2% aturan+model tidak lebih tinggi dari aturan saja. (Pada data v1 selisihnya 0,00.)
- **H2.** Pada modus held-out, recall@2% aturan+model lebih tinggi dari aturan saja. Jika tidak, komponen model dilaporkan tidak terbukti berguna.
- **H3.** Hard negative 1 (rujukan hari sama) tidak masuk 2% teratas.
- **H4 (kelemahan yang diperkirakan).** Aturan upcoding tingkat RS menandai RS kelas A yang jujur, karena porsinya dibandingkan dengan median semua RS, bukan RS sekelas.

Semua hasil dilaporkan, termasuk yang gagal.
