# Hasil Benchmark v2 KlaimGuard

Diuji sesuai [SPEK_BENCHMARK_V2.md](SPEK_BENCHMARK_V2.md), yang di-commit sebelum generator ditulis ([riwayat commit spesifikasi](https://github.com/PolkesrayaPress/klaimguard/commits/main/SPEK_BENCHMARK_V2.md) lawan [riwayat commit generator](https://github.com/PolkesrayaPress/klaimguard/commits/main/gen_bench.py)). Detektor: `detect.py` v1.1, tanpa perubahan sesudah hasil terlihat. Alat ukur: healthkathon-eval-kit dari Workshop Healthkathon 2026 (bootstrap 1.000 kali, resampling per RS, rentang 95%).

**Semua data sintetis dan dibuat tim sendiri. Distribusi belum dikalibrasi ke statistik publik. Angka di bawah menguji logika KlaimGuard pada kondisi yang kami rancang, bukan kinerja pada klaim BPJS nyata.**

Reproduksi: `python3 gen_bench.py benchmark` lalu `python3 run_bench.py benchmark <folder-eval-kit>`. Tabel lengkap ada di `benchmark/hasil/`, kartu bukti kit di `benchmark/hasil/evidence_D0.html`.

## 1. Angka utama (D0: 10.000 klaim, fraud 2%, 12 RS, 3 RS jujur)

| Kapasitas audit | Klaim diaudit | Presisi (rentang 95%) | Lift atas acak | Recall | Recall rupiah | RS jujur ikut teraudit |
|---|---|---|---|---|---|---|
| 1% | 100 | 0,75 (0,45 sampai 1,00) | 37,5× | 0,38 | 0,42 | 2 dari 3 |
| **2% (utama)** | **200** | **0,49 (0,30 sampai 0,71)** | **24,5×** | **0,49** | **0,52** | **2 dari 3** |
| 5% | 500 | 0,26 (0,12 sampai 0,36) | 12,9× | 0,65 | 0,64 | 3 dari 3 |

Kapasitas 2% adalah asumsi tim, belum bersumber dari verifikator. Uji permutasi label: PR-AUC 0,48 lawan 0,02 bila label diacak (p = 0,001).

## 2. Per kondisi (kapasitas 2%, skor aturan + model)

| Kondisi | Yang diubah | Presisi (rentang 95%) | Lift | Recall |
|---|---|---|---|---|
| D0 | baseline | 0,49 (0,30 sampai 0,71) | 24,5× | 0,49 |
| D1 | fraud 1% | 0,24 (0,12 sampai 0,43) | 24,7× | 0,50 |
| D2 | fraud 5% | 0,93 (0,66 sampai 1,00) | 18,6× | 0,37 |
| D3 | fraud terkumpul di 2 RS | 0,48 (0,00 sampai 0,91) | 24,0× | 0,48 |
| D4 | upcoding halus | 0,50 (0,30 sampai 0,71) | 24,8× | 0,50 |

Catatan: pada D1 jumlah fraud (97) lebih kecil dari slot audit (198), sehingga presisi maksimum yang mungkin hanya 0,49. Pada D3 rentangnya sangat lebar karena bukti hanya datang dari 2 RS, dan 8 dari 10 RS jujur ikut teraudit.

## 3. Ablation: apakah model (IsolationForest) menambah sesuatu?

| Kondisi, kapasitas | Presisi aturan saja | Presisi aturan + model | Selisih | p |
|---|---|---|---|---|
| D0, 1% | 0,77 | 0,75 | -0,02 | 0,70 |
| D0, 2% | 0,50 | 0,49 | -0,01 | 0,96 |
| D0, 5% | 0,20 | 0,26 | +0,06 | 0,51 |
| D1 sampai D4, 2% | | | -0,02 sampai 0,00 | 1,00 |

Model saja: presisi 0,16 pada D0 kapasitas 2%.

## 4. Recall per modus (D0)

| Modus | Kapasitas 2%, aturan saja | Kapasitas 2%, aturan + model | Kapasitas 5%, aturan + model |
|---|---|---|---|
| Tumpang tindih lintas faskes | 1,00 | 1,00 | 1,00 |
| Phantom billing | 1,00 | 1,00 | 1,00 |
| Inkonsistensi demografi | 1,00 | 1,00 | 1,00 |
| Pecah episode (unbundling) | 1,00 | 0,93 | 1,00 |
| **Upcoding (35% dari semua fraud)** | **0,00** | **0,00** | **0,01** |
| **Held-out: lama rawat digelembungkan** | **0,00** | **0,00** | **0,93** |

## 5. Kasus jujur yang mirip fraud (D0, kapasitas 2%)

| Jenis | Jumlah klaim | Masuk antrean audit |
|---|---|---|
| Rujukan antar-RS hari yang sama | 120 | 0 |
| Rawat ulang terjadwal (kemoterapi, transfusi) | 120 | 3 |
| Rawat ulang sah karena komplikasi, 7 hari atau kurang | 60 | **55** |
| RS kelas A rujukan | 1.225 | **27** |
| Diagnosis langka berbiaya tinggi | 164 | 17 |
| RS baru bervolume kecil | 199 | 0 |

## 6. Hipotesis pra-registrasi

| Hipotesis | Hasil |
|---|---|
| H1: model tidak menaikkan presisi@2% | **Terbukti.** Selisih -0,01 (p = 0,96). |
| H2: model menaikkan recall held-out pada 2% | **Gagal.** Recall 0 untuk kedua varian. |
| H3: rujukan hari sama tidak masuk 2% teratas | **Terbukti.** 0 dari 120. |
| H4: aturan upcoding menandai RS kelas A yang jujur | **Terbukti.** 27 klaim RS kelas A masuk antrean. |

**Temuan eksploratif (tidak dipra-registrasi):** pada kapasitas 5%, model menangkap 93% kasus held-out yang sama sekali tidak dikenali aturan, dan recall naik dari 0,50 ke 0,65. Model gagal pada 2% karena rancangan skor: model hanya bisa menambah paling banyak 30 poin, sehingga temuan model saja tidak pernah melampaui klaim yang menyalakan aturan.

## 7. Leakage scan

Empat kolom melewati AUC 0,80 (FKL23 0,85; FKL47 0,82; FKL48 0,82; berkas 0,81). Semuanya hilang bila scan dibatasi pada klaim rawat inap (tertinggi FKL23 0,63), jadi penyebabnya struktural: semua modus fraud dalam benchmark ini adalah rawat inap. ID klaim, ID peserta, dan urutan baris tidak membocorkan label.

## 8. Titik lemah yang kami laporkan

1. **Upcoding tidak tertangkap** bila tersebar di banyak RS. Aturan membandingkan porsi keparahan III per RS dengan median semua RS, sehingga hanya RS dengan lonjakan besar yang tertandai.
2. **RS kelas A yang jujur justru tertandai** oleh aturan yang sama, karena pasiennya memang lebih berat.
3. **Rawat ulang sah karena komplikasi** tidak bisa dibedakan dari pecah episode dengan kolom yang tersedia. Ini beban verifikator terbesar.
4. **Model baru berguna pada kapasitas besar** dan belum berguna pada antrean kecil.
5. Tinjauan pakar buta belum dilakukan. Lembarnya (20 klaim teratas + 20 acak, tanpa skor) siap di `benchmark/review/review_sheet.csv`. Kunci jawabannya disimpan terpisah dan tidak boleh diperlihatkan kepada penilai.

## 9. Kalimat untuk juri

Pada benchmark sintetis yang spesifikasinya kami kunci lebih dulu, dari 200 klaim yang diaudit (2%) sekitar separuh (0,49; rentang 0,30 sampai 0,71) adalah fraud, 24 kali lebih baik dari pemilihan acak. Empat dari lima modus yang dikenali aturan tertangkap hampir semuanya, upcoding belum tertangkap, dan komponen model belum menambah presisi pada kapasitas ini.
