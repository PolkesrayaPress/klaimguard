"""Logika deteksi KlaimGuard AI. Semua fungsi menerima dan mengembalikan DataFrame."""
import pandas as pd
from sklearn.ensemble import IsolationForest

REQUIRED_DOCS = {
    "Rawat Inap": ["sep", "resume_medis", "rincian_biaya", "surat_perintah_rawat_inap"],
    "Rawat Jalan": ["sep", "resume_medis", "rincian_biaya"],
}
BOBOT = {
    "tumpang_tindih": 70, "demografi": 70, "phantom": 60, "pecah_episode": 50, "upcoding_rs": 40, "berkas": 10,
}
JEDA_PECAH_EPISODE = 7  # hari; rawat ulang di RS sama dengan diagnosis sama dalam jeda ini dicurigai


def profil_faskes(df):
    # data sampel asli tidak punya ID RS; kombinasi kab/kota, kepemilikan, tipe dipakai sebagai gantinya
    return df["FKL06"].astype(str) + "|" + df["FKL07"] + "|" + df["FKL09"]


def cek_kelengkapan(df):
    def kurang(row):
        ada = set(str(row["berkas_pendukung"]).split(";"))
        return ";".join(d for d in REQUIRED_DOCS[row["FKL10"]] if d not in ada)
    out = df[["FKL02"]].copy()
    out["berkas_kurang"] = df.apply(kurang, axis=1)
    out["lengkap"] = out["berkas_kurang"] == ""
    return out


def cari_tumpang_tindih(df):
    inap = df[df["FKL10"] == "Rawat Inap"].copy()
    inap["pulang_ada"] = inap["FKL04"].notna()
    inap["FKL04"] = inap["FKL04"].fillna(inap["FKL03"])  # tanggal pulang kosong dianggap pulang hari itu
    inap["profil"] = profil_faskes(inap)
    cols = ["FKL02", "PSTV01", "FKL03", "FKL04", "pulang_ada", "profil", "nama_faskes_sintetis", "FKL47"]
    pair = inap[cols].merge(inap[cols], on="PSTV01", suffixes=("_a", "_b"))
    pair = pair[
        (pair["FKL02_a"] < pair["FKL02_b"])
        & (pair["profil_a"] != pair["profil_b"])
        & (pair["FKL03_a"] <= pair["FKL04_b"])
        & (pair["FKL03_b"] <= pair["FKL04_a"])
    ].copy()
    akhir = pair[["FKL04_a", "FKL04_b"]].min(axis=1)
    awal = pair[["FKL03_a", "FKL03_b"]].max(axis=1)
    pair["hari_tumpang_tindih"] = (akhir - awal).dt.days + 1
    # rujukan sah: pulang tercatat dari RS pertama pada hari yang sama dengan masuk RS kedua
    rujukan = (pair["hari_tumpang_tindih"] == 1) & (
        ((pair["FKL04_a"] == pair["FKL03_b"]) & pair["pulang_ada_a"])
        | ((pair["FKL04_b"] == pair["FKL03_a"]) & pair["pulang_ada_b"]))
    pair = pair[~rujukan].copy()
    pair["total_tagih"] = pair["FKL47_a"] + pair["FKL47_b"]
    return pair.reset_index(drop=True)


def cari_pecah_episode(df):
    inap = df[df["FKL10"] == "Rawat Inap"].copy()
    inap["profil"] = profil_faskes(inap)
    inap = inap.sort_values(["PSTV01", "profil", "FKL18", "FKL03"])
    prev_pulang = inap.groupby(["PSTV01", "profil", "FKL18"])["FKL04"].shift()
    jeda = (inap["FKL03"] - prev_pulang).dt.days
    kedua = inap[(jeda >= 0) & (jeda <= JEDA_PECAH_EPISODE)]
    pertama = inap.groupby(["PSTV01", "profil", "FKL18"])["FKL02"].shift().loc[kedua.index]
    return set(kedua["FKL02"]) | set(pertama)


def porsi_keparahan_rs(df):
    inap = df[df["FKL10"] == "Rawat Inap"]
    porsi = inap.groupby("nama_faskes_sintetis")["FKL23"].apply(lambda s: (s == "III").mean())
    return porsi.sort_values(ascending=False)


def skor_anomali(df):
    fitur = pd.DataFrame({
        "rasio_tagih": df["FKL47"] / df.groupby("FKL19")["FKL47"].transform("median"),
        "lama_rawat": (df["FKL04"] - df["FKL03"]).dt.days,
        "inap": (df["FKL10"] == "Rawat Inap").astype(int),
    }).fillna(0)
    model = IsolationForest(n_estimators=200, contamination="auto", random_state=0).fit(fitur)
    s = -model.score_samples(fitur)  # makin tinggi makin janggal
    return ((s - s.min()) / (s.max() - s.min()) * 100).round()


def skor_risiko(df):
    alasan = {k: [] for k in df["FKL02"]}
    lama_rawat = (df["FKL04"] - df["FKL03"]).dt.days

    def tandai(mask_or_ids, kunci, teks):
        ids = df.loc[mask_or_ids, "FKL02"] if not isinstance(mask_or_ids, set) else mask_or_ids
        for i in ids:
            alasan[i].append((kunci, teks))

    tandai((df["FKL10"] == "Rawat Inap") & (lama_rawat == 0), "phantom", "Rawat inap 0 hari, tidak ada jejak perawatan")
    tandai(df["FKL18"].str.startswith("O") & (df["PSTV05"] == 1), "demografi", "Diagnosis kebidanan pada peserta laki-laki")
    tandai(cari_pecah_episode(df), "pecah_episode", f"Rawat ulang di RS sama, diagnosis sama, jeda {JEDA_PECAH_EPISODE} hari atau kurang")

    tt = cari_tumpang_tindih(df)
    tandai(set(tt["FKL02_a"]) | set(tt["FKL02_b"]), "tumpang_tindih", "Rawat inap tumpang tindih di faskes lain")

    porsi = porsi_keparahan_rs(df)
    median = porsi.median()
    for rs, p in porsi[porsi > 2 * median].items():
        tandai((df["nama_faskes_sintetis"] == rs) & (df["FKL23"] == "III"), "upcoding_rs",
               f"Keparahan III di RS dengan porsi {p:.0%}, median regional {median:.0%}")

    kel = cek_kelengkapan(df).set_index("FKL02")["lengkap"]
    tandai(df["FKL02"].map(~kel).astype(bool), "berkas", "Berkas pendukung tidak lengkap")

    out = df[["FKL02"]].copy()
    out["skor_aturan"] = out["FKL02"].map(lambda i: min(100, sum(BOBOT[k] for k, _ in alasan[i])))
    out["skor_anomali"] = skor_anomali(df)
    # aturan menentukan dasar skor; anomali statistik hanya menambah paling banyak 30 poin
    out["skor_risiko"] = (out["skor_aturan"] + 0.3 * out["skor_anomali"]).clip(upper=100).round().astype(int)
    out["kategori"] = pd.cut(out["skor_risiko"], [-1, 29, 49, 100], labels=["Rendah", "Sedang", "Tinggi"])
    out["alasan"] = out["FKL02"].map(lambda i: "; ".join(t for _, t in alasan[i]) or "Tidak ada aturan yang menyala")
    return out


KOLOM_WAJIB = ["FKL02", "PSTV01", "PSTV05", "FKL03", "FKL04", "FKL06", "FKL07", "FKL09", "FKL10", "FKL18",
               "FKL19", "FKL23", "FKL47", "nama_faskes_sintetis", "berkas_pendukung"]


def baca_klaim(sumber):
    """Baca CSV klaim dari path atau berkas unggahan. Mengembalikan (df, pesan_error)."""
    try:
        df = pd.read_csv(sumber, dtype={"PSTV01": str, "FKL05": str, "FKL06": str})
    except Exception as e:  # berkas rusak atau bukan CSV
        return None, f"Berkas tidak bisa dibaca sebagai CSV: {e}"
    kurang = [k for k in KOLOM_WAJIB if k not in df.columns]
    if kurang:
        return None, "Kolom wajib tidak ada: " + ", ".join(kurang)
    if df.empty:
        return None, "Berkas tidak berisi baris klaim"
    ganda = df.loc[df["FKL02"].duplicated(), "FKL02"].astype(str).unique()
    if len(ganda):
        return None, "ID kunjungan (FKL02) ganda: " + ", ".join(ganda[:3]) + (" dan lainnya" if len(ganda) > 3 else "")
    for k in ["FKL03", "FKL04"]:
        df[k] = pd.to_datetime(df[k], errors="coerce")
    if df["FKL03"].isna().any():
        return None, "Ada baris dengan tanggal datang (FKL03) kosong atau tidak valid"
    df["PSTV05"] = pd.to_numeric(df["PSTV05"], errors="coerce")
    df["FKL47"] = pd.to_numeric(df["FKL47"], errors="coerce").fillna(0)
    return df, None
