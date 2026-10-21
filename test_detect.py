import pandas as pd
from detect import cari_tumpang_tindih, cari_pecah_episode, cek_kelengkapan, skor_risiko

def baris(i, pid, rs, tipe, masuk, pulang, dx="A09"):
    return {"FKL02": i, "PSTV01": pid, "PSTV05": 2, "FKL03": pd.Timestamp(masuk), "FKL04": pd.Timestamp(pulang) if pulang else pd.NaT,
            "FKL06": "6271", "FKL07": "Swasta", "FKL09": tipe, "FKL10": "Rawat Inap", "FKL18": dx, "FKL19": "K-4-17-I",
            "FKL23": "I", "FKL47": 3_500_000, "nama_faskes_sintetis": rs, "berkas_pendukung": "sep;resume_medis;rincian_biaya;surat_perintah_rawat_inap"}

kasus = pd.DataFrame([
    baris("K1", "P1", "RS A", "B", "2026-03-01", "2026-03-05"), baris("K2", "P1", "RS C", "C", "2026-03-04", "2026-03-06"),  # tumpang tindih
    baris("K3", "P2", "RS A", "B", "2026-03-01", "2026-03-05"), baris("K4", "P2", "RS C", "C", "2026-03-06", "2026-03-08"),  # berurutan
    baris("K5", "P3", "RS A", "B", "2026-03-01", None),         baris("K6", "P3", "RS C", "C", "2026-03-01", "2026-03-02"),  # pulang kosong
    baris("K7", "P4", "RS A", "B", "2026-03-01", "2026-03-04"), baris("K8", "P4", "RS A", "B", "2026-03-06", "2026-03-09"),  # pecah episode
    baris("K9", "P5", "RS A", "B", "2026-03-01", "2026-03-04"), baris("K10", "P5", "RS A", "B", "2026-04-20", "2026-04-22"),  # rawat ulang wajar
])
tt = cari_tumpang_tindih(kasus)
assert set(zip(tt.FKL02_a, tt.FKL02_b)) == {("K1", "K2"), ("K5", "K6")}, tt
assert cari_pecah_episode(kasus) == {"K7", "K8"}
kasus.loc[0, "berkas_pendukung"] = "sep;rincian_biaya"
assert cek_kelengkapan(kasus).set_index("FKL02").loc["K1", "berkas_kurang"] == "resume_medis;surat_perintah_rawat_inap"

df = pd.read_csv("klaim.csv", parse_dates=["PSTV03", "FKL03", "FKL04"], dtype={"PSTV01": str, "FKL06": str})
r = skor_risiko(df).merge(df[["FKL02", "PSTV01", "label_sintetis"]], on="FKL02")
for pid, harus in [("9001871", True), ("9001851", True), ("9001901", False), ("9001916", False)]:
    tinggi = (r[r.PSTV01 == pid].kategori == "Tinggi").any()
    assert tinggi == harus, (pid, r[r.PSTV01 == pid][["skor_risiko", "alasan"]])
fraud = r.label_sintetis != "normal"; hit = r.kategori == "Tinggi"
print(f"presisi {(fraud & hit).sum() / hit.sum():.2f} | recall {(fraud & hit).sum() / fraud.sum():.2f} | ditandai Tinggi {hit.sum()}")
print(r[fraud].groupby("label_sintetis").apply(lambda g: f"{(g.kategori == 'Tinggi').mean():.0%}").to_string())
print("normal tertandai Tinggi:", (~fraud & hit).sum())
print("semua tes lulus")
