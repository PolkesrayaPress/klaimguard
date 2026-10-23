"""Evaluasi KlaimGuard pada Benchmark v2 dengan healthkathon-eval-kit (SPEK_BENCHMARK_V2.md bagian 6 dan 7).

Pemakaian: python3 run_bench.py benchmark /path/ke/healthkathon-eval-kit
"""
import sys
from pathlib import Path
import pandas as pd

BENCH, KIT = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(KIT))
from hkeval import metrics, report, review, stress  # noqa: E402
from detect import baca_klaim, skor_risiko  # noqa: E402

K = 0.02  # kapasitas utama dari spesifikasi
# urutan penting: uji berpasangan membandingkan tiap varian dengan varian sebelumnya (H1: aturan+model vs aturan)
VARIAN = {"model saja": "skor_anomali", "aturan saja": "skor_aturan", "aturan + model": "skor_risiko"}
OUT = BENCH / "hasil"; OUT.mkdir(exist_ok=True)
ringkas, modus_rows, hn_rows, jujur_rows = [], [], [], []

for d in sorted(p for p in BENCH.iterdir() if p.name.startswith("D")):
    df, err = baca_klaim(d / "klaim.csv"); assert err is None, err
    truth = pd.read_csv(d / "truth.csv", keep_default_na=False)
    r = skor_risiko(df)
    base = pd.DataFrame({"entity_id": df["FKL02"], "group_id": df["nama_faskes_sintetis"], "kelas_rs": df["FKL09"]})
    files = {}
    for nama, kol in VARIAN.items():
        files[nama] = OUT / f"scores_{d.name}_{nama.replace(' ', '').replace('+', '_')}.csv"
        base.assign(score=r[kol].to_numpy()).to_csv(files[nama], index=False)
    t = truth.set_index("entity_id").loc[df["FKL02"]]
    y, g = t["label"].to_numpy(), base["group_id"].to_numpy()
    for k in ([0.01, K, 0.05] if d.name == "D0" else [K]):
        ab = stress.ablation(files, d / "truth.csv", k)
        for nama, row in zip(VARIAN, ab.to_dict("records")):
            s = r[VARIAN[nama]].to_numpy(float)
            ringkas.append({"kondisi": d.name, "kapasitas": k, "n_audit": metrics.n_top(len(s), k), "varian": nama,
                            "presisi": row["precision_at_k"], "ci_bawah": row["ci_low"], "ci_atas": row["ci_high"],
                            "lift": row["lift"], "recall": metrics.recall_at_k(y, s, k),
                            "recall_rupiah": row.get("rupiah_recall"), "pr_auc": row["pr_auc"],
                            "rs_jujur_teraudit": row["honest_group_audit_rate"],
                            "selisih_vs_sebelumnya": row["diff"], "p_value": row["p_value"]})
    for nama in ["aturan saja", "aturan + model"]:
        s = r[VARIAN[nama]].to_numpy(float)
        for k in ([K, 0.05] if d.name == "D0" else [K]):
            pm = metrics.per_modus_recall_at_k(y, s, t["modus"].to_numpy(), k)
            modus_rows += pm.assign(kondisi=d.name, kapasitas=k, varian=nama).to_dict("records")
        jujur_rows += metrics.stratified_honest_group_audit_rate(
            y, s, g, base[["kelas_rs"]], K).assign(kondisi=d.name, varian=nama).to_dict("records")
    top = set(df["FKL02"].iloc[metrics.top_k(r["skor_risiko"].to_numpy(float), K)])
    for jenis, part in t[t["jenis_normal"] != ""].groupby("jenis_normal"):
        hn_rows.append({"kondisi": d.name, "jenis_normal": jenis, "n": len(part),
                        "masuk_audit": int(part.index.isin(top).sum())})
    if d.name == "D0":
        fitur = df.rename(columns={"FKL02": "entity_id"})
        stress.leakage_scan(fitur, d / "truth.csv").to_csv(OUT / "leakage_D0.csv", index=False)
        pt = stress.permutation_test(y, r["skor_risiko"].to_numpy(float))
        pd.DataFrame([{k: v for k, v in pt.items() if k != "null"}]).to_csv(OUT / "permutasi_D0.csv", index=False)
        card = report.build_card(pd.read_csv(files["aturan + model"]), truth, capacity=K, group_col="group_id",
                                 strata=["kelas_rs"], conditions={
                                     "data_source": "synthetic", "benchmark": "Benchmark v2 KlaimGuard, kondisi D0",
                                     "generator_author": "tim yang sama, spesifikasi di-commit lebih dulu",
                                     "calibration_sources": "belum dikalibrasi; distribusi dikarang tim", "seed": "2026"},
                                 review=None, entity_noun="klaim", group_noun="rumah sakit", n_boot=1000, seed=0)
        (OUT / "evidence_D0.html").write_text(report.render_html(card, "id"), encoding="utf-8")
        print(report.jury_sentence(card, "id"))
        sheet, _ = review.make_review_sheet(pd.read_csv(d / "klaim.csv").rename(columns={"FKL02": "entity_id"}),
                                            pd.read_csv(files["aturan + model"]), k=20, n_random=20, seed=0,
                                            out_dir=BENCH / "review")
        assert not {"entity_id", "score", "FKL02"} & set(sheet.columns), "lembar membocorkan identitas"

for nama, rows in [("ringkasan", ringkas), ("recall_per_modus", modus_rows), ("hard_negative", hn_rows),
                   ("rs_jujur_per_kelas", jujur_rows)]:
    pd.DataFrame(rows).to_csv(OUT / f"{nama}.csv", index=False)
print(pd.DataFrame(ringkas).round(3).to_string(index=False))
print(pd.DataFrame(modus_rows).pivot_table(index=["kondisi", "kapasitas", "modus"], columns="varian", values="recall").round(2).to_string())
print(pd.DataFrame(hn_rows).to_string(index=False))
print(pd.DataFrame(jujur_rows).to_string(index=False))
print(pd.read_csv(OUT / "leakage_D0.csv").head(8).round(3).to_string(index=False))
print(pd.read_csv(OUT / "permutasi_D0.csv").to_string(index=False))
