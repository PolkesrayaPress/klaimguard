"""Generator Benchmark v2 KlaimGuard, mengikuti SPEK_BENCHMARK_V2.md. Semua data sintetis.

Pemakaian: python3 gen_bench.py benchmark
Menulis benchmark/D0..D4/klaim.csv (tanpa label) dan truth.csv (label untuk evaluasi saja).
Tarif, kode INA-CBG, lama rawat, dan sebaran keparahan dikarang tim, belum dikalibrasi.
"""
import sys
from datetime import date, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

START = date(2026, 1, 1)
N_NORMAL = 9_800  # klaim normal identik di semua kondisi; total = normal + fraud
# nama, prov, kab, kepemilikan, tipe, bobot volume, boleh berisi fraud
FASKES = [
    ("RS Fiktif Alpha", "62", "6271", "Pemerintah", "B", 0.11, True),
    ("RS Fiktif Beta", "62", "6271", "Swasta", "C", 0.09, True),
    ("RSUD Fiktif Gamma", "62", "6203", "Pemerintah", "C", 0.09, True),
    ("RS Fiktif Delta", "62", "6202", "Swasta", "C", 0.10, True),
    ("RS Fiktif Epsilon", "63", "6371", "Pemerintah", "B", 0.09, True),
    ("RS Fiktif Zeta", "63", "6372", "Swasta", "D", 0.07, True),
    ("RS Fiktif Eta", "64", "6471", "Pemerintah", "B", 0.08, True),
    ("RS Fiktif Theta", "64", "6472", "Swasta", "C", 0.07, True),
    ("RS Fiktif Omikron", "61", "6171", "Swasta", "C", 0.07, True),
    ("RSUP Fiktif Kappa", "62", "6271", "Pemerintah", "A", 0.14, False),  # rujukan kelas A, jujur
    ("RSUD Fiktif Lambda", "63", "6303", "Pemerintah", "C", 0.07, False),  # jujur
    ("RS Fiktif Iota", "64", "6403", "Swasta", "D", 0.02, False),  # RS baru volume kecil, jujur
]
FW = np.array([f[5] for f in FASKES]); FW = FW / FW.sum()
FRAUD_RS = [i for i, f in enumerate(FASKES) if f[6]]
KLASTER_RS = [2, 3]  # Gamma dan Delta, untuk kondisi D3
KAPPA, IOTA = 9, 11

# ICD-10 primer -> (prefix INA-CBG, tarif dasar keparahan I, rentang lama rawat)
UMUM = {"A09": ("K-4-17", 3_500_000, (2, 5)), "J18.9": ("J-4-15", 7_000_000, (3, 7)),
        "A91": ("A-4-14", 5_000_000, (3, 6)), "O80": ("O-6-10", 4_000_000, (1, 3)),
        "K35.8": ("K-1-12", 9_000_000, (2, 5)), "I63.9": ("G-4-14", 15_000_000, (4, 10))}
LANGKA = {"C91.0": ("C-4-11", 28_000_000, (7, 14)), "I21.9": ("I-4-10", 22_000_000, (4, 9))}
TERJADWAL = {"Z51.1": ("Z-3-15", 6_000_000, (1, 3)), "D56.1": ("D-4-13", 3_000_000, (1, 2))}
INAP = {**UMUM, **LANGKA, **TERJADWAL}
JALAN = {"J06.9": ("Q-5-44", 250_000), "I10": ("Q-5-42", 300_000), "E11.9": ("Q-5-37", 350_000),
         "K29.7": ("Q-5-44", 275_000), "M54.5": ("Q-5-35", 300_000)}
SEV_MULT = {"I": 1.0, "II": 1.4, "III": 1.9}
DOCS = {"Rawat Inap": ["sep", "resume_medis", "rincian_biaya", "surat_perintah_rawat_inap"],
        "Rawat Jalan": ["sep", "resume_medis", "rincian_biaya"]}
POTONG_VERIFIKATOR = 0.10  # sama untuk klaim normal dan fraud, agar FKL48 tidak membocorkan label
KONDISI = {"D0": (0.02, "sebar", "sedang"), "D1": (0.01, "sebar", "sedang"), "D2": (0.05, "sebar", "sedang"),
           "D3": (0.02, "klaster", "sedang"), "D4": (0.02, "sebar", "halus")}
PORSI_MODUS = {"upcoding": 0.35, "phantom_billing": 0.15, "unbundling": 0.15,
               "tumpang_tindih_lintas_faskes": 0.15, "inkonsistensi_demografi": 0.05}  # sisanya held-out


class Pembuat:
    def __init__(self, seed, id_pool, id_awal):
        self.rng, self.pool, self.n = np.random.default_rng(seed), id_pool, id_awal

    def pasien(self, female=None):
        r = self.rng; self.n += 1
        sex = (2 if r.random() < 0.52 else 1) if female is None else (2 if female else 1)
        return {"PSTV01": str(self.pool[self.n]), "PSTV05": sex,
                "PSTV03": date(1950, 1, 1) + timedelta(days=int(r.integers(0, 365 * 55)))}

    def klaim(self, p, inap, f=None, adm=None, los=None, dx=None, sev=None):
        r = self.rng
        f = int(r.choice(len(FASKES), p=FW)) if f is None else f
        tipe = FASKES[f][4]
        if inap and dx is None:
            p_langka = 0.08 if tipe == "A" else 0.01
            pilihan = [d for d in UMUM if not (d == "O80" and p["PSTV05"] == 1)]
            dx = str(r.choice(list(LANGKA))) if r.random() < 2 * p_langka else str(r.choice(pilihan))
        elif dx is None:
            dx = str(r.choice(list(JALAN)))
        prefix, tarif = (INAP[dx][:2] if inap else JALAN[dx])
        if sev is None:
            sev = str(r.choice(["I", "II", "III"], p=[0.40, 0.25, 0.35] if tipe == "A" else [0.60, 0.28, 0.12])) if inap else "0"
        adm = adm or START + timedelta(days=int(r.integers(0, 300)))
        if los is None:
            los = int(r.integers(INAP[dx][2][0], INAP[dx][2][1] + 1)) if inap else 0
        faktor = float(r.lognormal(0, 0.10))
        tagih = round(tarif * SEV_MULT.get(sev, 1.0) * faktor, -3)
        nama, prov, kab, milik, tipe, _, _ = FASKES[f]
        jenis = "Rawat Inap" if inap else "Rawat Jalan"
        return {**p, "FKL03": adm, "FKL04": adm + timedelta(days=los), "FKL05": prov, "FKL06": kab,
                "FKL07": milik, "FKL08": "Rumah Sakit Umum", "FKL09": tipe, "FKL10": jenis,
                "FKL18": dx, "FKL19": f"{prefix}-{sev}", "FKL23": sev, "FKL47": tagih, "FKL48": tagih,
                "nama_faskes_sintetis": nama, "berkas_pendukung": list(DOCS[jenis]),
                "label": 0, "modus": "", "excess_rupiah": 0, "jenis_normal": "",
                "_f": f, "_tarif": tarif, "_faktor": faktor}

    def verifikasi(self, c):
        if self.rng.random() < POTONG_VERIFIKATOR:
            c["FKL48"] = round(c["FKL47"] * float(self.rng.uniform(0.55, 0.95)), -3)
        return c


def basis_normal(id_pool):
    g = Pembuat(2026, id_pool, -1); rows = []
    for _ in range(60):  # HN1 rujukan antar-RS pada hari yang sama
        p = g.pasien(); f1, f2 = g.rng.choice(len(FASKES), 2, replace=False)
        a = g.klaim(p, True, f=int(f1)); b = g.klaim(p, True, f=int(f2), adm=a["FKL04"])
        a["jenis_normal"] = b["jenis_normal"] = "rujukan_hari_sama"; rows += [a, b]
    for _ in range(40):  # HN3 rawat ulang terjadwal: kemoterapi atau transfusi berkala
        p = g.pasien(); f = int(g.rng.choice(len(FASKES), p=FW)); dx = str(g.rng.choice(list(TERJADWAL)))
        adm = START + timedelta(days=int(g.rng.integers(0, 200)))
        for _ in range(3):
            c = g.klaim(p, True, f=f, adm=adm, dx=dx); c["jenis_normal"] = "rawat_ulang_terjadwal"; rows.append(c)
            adm = c["FKL04"] + timedelta(days=int(g.rng.integers(14, 29)))
    for _ in range(30):  # HN4 rawat ulang sah karena komplikasi, 2 sampai 7 hari, diagnosis sama
        p = g.pasien(); a = g.klaim(p, True)
        b = g.klaim(p, True, f=a["_f"], dx=a["FKL18"], adm=a["FKL04"] + timedelta(days=int(g.rng.integers(2, 8))))
        a["jenis_normal"] = b["jenis_normal"] = "rawat_ulang_komplikasi"; rows += [a, b]
    while len(rows) < N_NORMAL:
        rows.append(g.klaim(g.pasien(), inap=g.rng.random() < 0.38))
    for c in rows:
        if not c["jenis_normal"]:
            c["jenis_normal"] = ("dx_langka_biaya_tinggi" if c["FKL18"] in LANGKA else
                                 "rs_kelas_a" if c["_f"] == KAPPA else "rs_baru" if c["_f"] == IOTA else "")
        if g.rng.random() < 0.05:  # berkas kurang tanpa unsur fraud
            c["berkas_pendukung"].remove(str(g.rng.choice(c["berkas_pendukung"][1:])))
        g.verifikasi(c)
    return rows


def sisip_fraud(rate, sebaran, upcoding, seed, id_pool):
    g = Pembuat(seed, id_pool, 19_999); rows = []
    rs = FRAUD_RS if sebaran == "sebar" else KLASTER_RS
    w = FW[rs] / FW[rs].sum()
    pilih = lambda: int(g.rng.choice(rs, p=w))
    n_f = round(rate / (1 - rate) * N_NORMAL)
    n = {m: round(p * n_f) for m, p in PORSI_MODUS.items()}
    n["held_out_lama_rawat"] = n_f - sum(n.values())

    def tandai(c, modus, excess):
        c.update(label=1, modus=modus, excess_rupiah=int(max(excess, 0))); rows.append(g.verifikasi(c))

    for _ in range(n["upcoding"]):
        p = g.pasien(); asli = "I" if upcoding == "halus" else str(g.rng.choice(["I", "II"], p=[0.7, 0.3]))
        baru = "II" if upcoding == "halus" else "III"
        c = g.klaim(p, True, f=pilih(), sev=baru)
        tandai(c, "upcoding", c["FKL47"] - round(c["_tarif"] * SEV_MULT[asli] * c["_faktor"], -3))
    for _ in range(n["phantom_billing"]):
        c = g.klaim(g.pasien(), True, f=pilih(), los=0); c["berkas_pendukung"].remove("resume_medis")
        tandai(c, "phantom_billing", c["FKL47"])
    for _ in range(n["unbundling"] // 2):
        p = g.pasien(); a = g.klaim(p, True, f=pilih())
        b = g.klaim(p, True, f=a["_f"], dx=a["FKL18"], adm=a["FKL04"] + timedelta(days=int(g.rng.integers(1, 4))))
        tandai(a, "unbundling", 0); tandai(b, "unbundling", b["FKL47"])
    for _ in range(n["tumpang_tindih_lintas_faskes"] // 2):
        p = g.pasien(); f1, f2 = g.rng.choice(rs, 2, replace=False)
        a = g.klaim(p, True, f=int(f1), los=int(g.rng.integers(3, 8)), dx="A09")
        b = g.klaim(p, True, f=int(f2), los=int(g.rng.integers(2, 6)),
                    adm=a["FKL03"] + timedelta(days=int(g.rng.integers(0, (a["FKL04"] - a["FKL03"]).days))))
        tandai(a, "tumpang_tindih_lintas_faskes", 0); tandai(b, "tumpang_tindih_lintas_faskes", b["FKL47"])
    for _ in range(n["inkonsistensi_demografi"]):
        c = g.klaim(g.pasien(female=False), True, f=pilih(), dx="O80"); tandai(c, "inkonsistensi_demografi", c["FKL47"])
    for _ in range(n["held_out_lama_rawat"]):
        p = g.pasien(); dx = str(g.rng.choice([d for d in UMUM if d != "O80"]))
        lo, hi = INAP[dx][2]; median = (lo + hi) / 2
        c = g.klaim(p, True, f=pilih(), dx=dx, los=int(round(median * g.rng.uniform(2, 3))))
        asli = c["FKL47"]; c["FKL47"] = c["FKL48"] = round(asli * g.rng.uniform(1.3, 1.6), -3)
        tandai(c, "held_out_lama_rawat", c["FKL47"] - asli)
    return rows


COLS = ["FKL02", "PSTV01", "PSTV03", "PSTV05", "FKL03", "FKL04", "FKL05", "FKL06", "FKL07", "FKL08", "FKL09",
        "FKL10", "FKL18", "FKL19", "FKL23", "FKL47", "FKL48", "nama_faskes_sintetis", "berkas_pendukung"]


def buat(out):
    id_pool = np.random.default_rng(7).choice(9_000_000, 40_000, replace=False) + 1_000_000
    normal = basis_normal(id_pool)
    sidik_normal = None
    for i, (kode, (rate, sebaran, upc)) in enumerate(KONDISI.items()):
        df = pd.DataFrame([dict(c, berkas_pendukung=list(c["berkas_pendukung"])) for c in normal]
                          + sisip_fraud(rate, sebaran, upc, 100 + i, id_pool))
        df = df.sample(frac=1, random_state=200 + i).reset_index(drop=True)  # urutan baris acak
        df.insert(0, "FKL02", [f"K{j:07d}" for j in range(1, len(df) + 1)])
        df["berkas_pendukung"] = df["berkas_pendukung"].map(";".join)
        df[["FKL47", "FKL48"]] = df[["FKL47", "FKL48"]].astype(int)

        # pemeriksaan: struktur sesuai spesifikasi
        assert df.FKL02.is_unique and (df.FKL04 >= df.FKL03).all()
        prof = df.FKL06 + "|" + df.FKL07 + "|" + df.FKL09
        assert prof.groupby(df.nama_faskes_sintetis).nunique().max() == 1 and prof.nunique() == len(FASKES)
        assert df[df._f.isin([KAPPA, IOTA, 10])].label.sum() == 0, "RS jujur berisi fraud"
        assert abs(df.label.mean() - rate) < 0.002, (kode, df.label.mean())
        n_ = df[df.label == 0].drop(columns=["FKL02"]).sort_values(["PSTV01", "FKL03", "_f"]).reset_index(drop=True)
        sidik = pd.util.hash_pandas_object(n_.drop(columns=["_faktor"]), index=False).sum()
        assert sidik_normal in (None, sidik), "klaim normal berbeda antar kondisi"
        sidik_normal = sidik

        d = Path(out) / kode; d.mkdir(parents=True, exist_ok=True)
        df[COLS].to_csv(d / "klaim.csv", index=False)
        df[["FKL02", "label", "modus", "excess_rupiah", "jenis_normal"]].rename(columns={"FKL02": "entity_id"}).to_csv(
            d / "truth.csv", index=False)
        print(kode, len(df), "klaim | fraud", int(df.label.sum()), f"({df.label.mean():.1%})",
              df[df.label == 1].modus.value_counts().to_dict())


if __name__ == "__main__":
    buat(sys.argv[1] if len(sys.argv) > 1 else "benchmark")
