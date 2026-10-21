from unittest import mock
import pandas as pd
import ringkasan as R

k = {"FKL02": "K1", "nama_faskes_sintetis": "RS A", "FKL10": "Rawat Inap", "FKL18": "A09", "FKL19": "K-4-17-III",
     "FKL03": pd.Timestamp("2026-03-01"), "FKL04": pd.Timestamp("2026-03-04"), "FKL47": 7_000_000,
     "skor_risiko": 90, "kategori": "Tinggi", "alasan": "Rawat inap 0 hari; Berkas pendukung tidak lengkap"}
assert "indikasi" in R.buat_prompt(k) and "Rp 7,000,000" in R.buat_prompt(k)
assert "rawat inap 0 hari" in R.ringkasan_aturan(k)
assert "Tidak ada indikasi" in R.ringkasan_aturan({**k, "alasan": "Tidak ada aturan yang menyala"})
assert R.ringkasan_gemini(None, "x") == (None, None, "kunci API belum diatur")

def resp(code, parts=None):
    m = mock.Mock(status_code=code); m.json.return_value = {"candidates": [{"content": {"parts": parts or []}}]}; return m
ok = resp(200, [{"text": "pikir", "thought": True}, {"text": "Ringkasan siap."}])
with mock.patch("requests.post", side_effect=[resp(404), ok]) as p:  # model pertama tidak ada, cadangan berhasil
    assert R.ringkasan_gemini("k", "x") == ("Ringkasan siap.", R.MODEL_CADANGAN[1], None)
    assert p.call_args.kwargs["headers"] == {"x-goog-api-key": "k"}
with mock.patch("requests.post", return_value=resp(429)):
    t, m, e = R.ringkasan_gemini("k", "x"); assert t is None and "429" in e
import requests
with mock.patch("requests.post", side_effect=requests.ConnectionError()):
    assert "koneksi gagal" in R.ringkasan_gemini("k", "x")[2]
print("tes ringkasan lulus")
