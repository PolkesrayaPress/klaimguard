# KlaimGuard AI

Deteksi dini anomali klaim FKRTL Program JKN, dibuat untuk **BPJS Kesehatan Healthkathon 2026**.

**Demo:** https://klaimguard.streamlit.app

> Seluruh data di repositori dan aplikasi ini **sintetis**. Tidak ada data peserta JKN asli. Struktur kolom mengikuti kode variabel Data Sampel BPJS Kesehatan (PSTV, FKL), sedangkan isi, tarif, dan kode INA-CBG bersifat ilustratif.

## Apa yang dilakukan

KlaimGuard membaca klaim lintas kunjungan dan lintas faskes, lalu menyusun antrean pemeriksaan untuk verifikator. Setiap skor disertai alasan tertulis. Keputusan akhir tetap pada verifikator.

| Pola | Cara deteksi |
| --- | --- |
| Rawat inap tumpang tindih lintas faskes | Peserta sama, rentang tanggal rawat beririsan, profil faskes berbeda |
| Pecah episode (unbundling) | Rawat ulang di RS sama, diagnosis sama, jeda 7 hari atau kurang |
| Upcoding tingkat RS | Porsi keparahan INA-CBG III di satu RS lebih dari dua kali median regional |
| Phantom billing | Rawat inap 0 hari tanpa jejak perawatan |
| Inkonsistensi demografi | Diagnosis kebidanan pada peserta laki-laki |
| Anomali statistik | IsolationForest pada rasio tagih terhadap median INA-CBG, lama rawat, jenis layanan |

Skor risiko = jumlah bobot aturan yang menyala + 0,3 × skor anomali, dibatasi 100. Kategori Tinggi mulai skor 50.

Fitur verifikator: antrean berwarna, alasan per klaim, ringkasan GenAI (Gemini) dengan cadangan ringkasan berbasis aturan, keputusan Setujui / Tunda / Investigasi dengan log audit yang bisa diunduh, garis waktu klaim per peserta, dan unggah CSV dengan validasi kolom. GenAI dinonaktifkan otomatis untuk data unggahan.

## Validasi

Bukti utama ada di **[HASIL_BENCHMARK_V2.md](HASIL_BENCHMARK_V2.md)**: benchmark sintetis 10.000 klaim dengan 5 kondisi, kasus jujur yang mirip fraud, satu modus yang tidak dikenal aturan, dan ablation aturan lawan aturan + model. Spesifikasinya di-commit lebih dulu ([SPEK_BENCHMARK_V2.md](SPEK_BENCHMARK_V2.md)).

Ringkasnya, pada fraud 2% dan kapasitas audit 2%: presisi 0,49 (rentang 0,30 sampai 0,71), 24,5 kali lebih baik dari acak. Upcoding belum tertangkap, dan model belum menambah presisi pada kapasitas ini. Data demo di aplikasi (`klaim.csv`, 2.000 klaim) hanya untuk peragaan, bukan untuk mengukur kinerja.

## Struktur

| Berkas | Isi |
| --- | --- |
| `app.py` | Antarmuka Streamlit |
| `detect.py` | Aturan, korelator, skor anomali, validasi berkas unggahan |
| `ringkasan.py` | Ringkasan Gemini dan cadangan berbasis aturan |
| `klaim.csv` | Data sintetis untuk demo |
| `gen_bench.py`, `run_bench.py` | Pembuat dan penguji Benchmark v2 |
| `benchmark/` | Data benchmark D0 sampai D4, hasil, dan lembar tinjauan pakar |
| `test_detect.py`, `test_ringkasan.py` | Uji kasus tepi dan kontrol negatif |

## Menjalankan sendiri

```
pip install -r requirements.txt
streamlit run app.py
python test_detect.py && python test_ringkasan.py
```

Untuk GenAI, isi `GEMINI_API_KEY` di `.streamlit/secrets.toml`. Tanpa kunci, aplikasi tetap berjalan dengan ringkasan berbasis aturan.

## Batasan

- Data Sampel BPJS tidak memuat ID rumah sakit, jadi faskes dikenali dari kombinasi kabupaten/kota, kepemilikan, dan tipe.
- Data Sampel tidak memuat informasi berkas pendukung; lapis kelengkapan hanya dapat didemokan dengan data sintetis.
- Log audit hanya bertahan selama sesi browser. Produksi membutuhkan basis data dan integrasi dengan sistem verifikasi yang ada.

Dibuat oleh Deddy Eko Heryanto.
