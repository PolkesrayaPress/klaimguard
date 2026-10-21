import pandas as pd
import streamlit as st

from detect import cari_tumpang_tindih, cek_kelengkapan, porsi_keparahan_rs, skor_risiko

st.set_page_config(page_title="KlaimGuard AI", layout="wide")
st.title("KlaimGuard AI")
st.caption(
    "Deteksi dini anomali klaim FKRTL JKN. Struktur data mengikuti kode variabel Data Sampel BPJS Kesehatan; "
    "seluruh isi data di aplikasi ini sintetis. Hasil adalah rekomendasi pemeriksaan, keputusan tetap pada verifikator."
)

LABEL = {
    "FKL02": "ID Kunjungan", "PSTV01": "No. Peserta", "FKL03": "Tgl Datang", "FKL04": "Tgl Pulang",
    "FKL10": "Pelayanan", "FKL18": "Diagnosis", "FKL19": "INA-CBG", "FKL23": "Keparahan",
    "FKL47": "Biaya Tagih", "nama_faskes_sintetis": "Faskes",
}


@st.cache_data
def muat():
    df = pd.read_csv("klaim.csv", parse_dates=["PSTV03", "FKL03", "FKL04"], dtype={"PSTV01": str, "FKL05": str, "FKL06": str})
    return df, skor_risiko(df), cek_kelengkapan(df), cari_tumpang_tindih(df)


def rapi(t):
    # hanya untuk tampilan: tanggal tanpa jam, rupiah dengan pemisah ribuan
    t = t.copy()
    for c in t.columns:
        if pd.api.types.is_datetime64_any_dtype(t[c]):
            t[c] = t[c].dt.strftime("%d-%m-%Y")
        elif c in ("FKL47", "total_tagih"):
            t[c] = t[c].map(lambda v: f"Rp {v:,.0f}".replace(",", "."))
    return t


df, risiko, lengkap, tumpang = muat()
gabung = df.merge(risiko, on="FKL02")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Klaim FKRTL", len(df))
c2.metric("Risiko Tinggi", int((risiko["kategori"] == "Tinggi").sum()))
c3.metric("Berkas tidak lengkap", int((~lengkap["lengkap"]).sum()))
c4.metric("Pasangan tumpang tindih", len(tumpang))

tab1, tab2, tab3 = st.tabs(["Kelengkapan", "Skor Risiko", "Korelasi Lintas Faskes"])

with tab1:
    st.subheader("Klaim dengan berkas pendukung tidak lengkap")
    kurang = df.merge(lengkap[~lengkap["lengkap"]], on="FKL02")
    tampil = kurang[["FKL02", "nama_faskes_sintetis", "FKL10", "FKL18", "berkas_kurang"]]
    st.dataframe(rapi(tampil).rename(columns={**LABEL, "berkas_kurang": "Berkas Kurang"}), hide_index=True)

with tab2:
    st.subheader("Antrean pemeriksaan, diurutkan dari risiko tertinggi")
    pilih_kat = st.multiselect("Kategori", ["Tinggi", "Sedang", "Rendah"], default=["Tinggi"])
    antre = gabung[gabung["kategori"].isin(pilih_kat)].sort_values("skor_risiko", ascending=False)
    kolom = ["FKL02", "nama_faskes_sintetis", "FKL18", "FKL19", "FKL47", "skor_risiko", "kategori"]
    st.dataframe(rapi(antre[kolom]).rename(columns={**LABEL, "skor_risiko": "Skor", "kategori": "Kategori"}), hide_index=True)

    if len(antre):
        klaim = st.selectbox("Lihat alasan untuk klaim", antre["FKL02"])
        k = antre.set_index("FKL02").loc[klaim]
        st.markdown(f"**Skor {k['skor_risiko']}** (aturan {k['skor_aturan']}, anomali statistik {k['skor_anomali']:.0f})")
        for teks in k["alasan"].split("; "):
            st.markdown(f"- {teks}")

    st.subheader("Porsi keparahan III rawat inap per rumah sakit")
    st.bar_chart((porsi_keparahan_rs(df) * 100).rename("Persen keparahan III"))

    with st.expander("Validasi terhadap label data sintetis"):
        fraud = gabung["label_sintetis"] != "normal"
        hit = gabung["kategori"] == "Tinggi"
        v1, v2 = st.columns(2)
        v1.metric("Presisi kategori Tinggi", f"{(fraud & hit).sum() / max(hit.sum(), 1):.0%}")
        v2.metric("Recall kategori Tinggi", f"{(fraud & hit).sum() / max(fraud.sum(), 1):.0%}")
        per_pola = gabung[fraud].groupby("label_sintetis")["kategori"].apply(lambda s: (s == "Tinggi").mean() * 100)
        st.dataframe(per_pola.round().rename("Tertangkap (%)"))
        st.caption("Pola kecurangan ditanam sendiri di data sintetis, jadi angka ini menguji logika, bukan kinerja di data nyata.")

with tab3:
    st.subheader("Rawat inap tumpang tindih untuk peserta yang sama di faskes berbeda")
    tt = tumpang[["PSTV01", "nama_faskes_sintetis_a", "FKL03_a", "FKL04_a", "nama_faskes_sintetis_b", "FKL03_b", "FKL04_b",
                  "hari_tumpang_tindih", "total_tagih"]]
    st.dataframe(rapi(tt).rename(columns={"PSTV01": "No. Peserta", "nama_faskes_sintetis_a": "Faskes A", "FKL03_a": "Masuk A",
                                    "FKL04_a": "Pulang A", "nama_faskes_sintetis_b": "Faskes B", "FKL03_b": "Masuk B",
                                    "FKL04_b": "Pulang B", "hari_tumpang_tindih": "Hari Tumpang Tindih",
                                    "total_tagih": "Total Tagih"}), hide_index=True)
    st.subheader("Riwayat klaim per peserta")
    pid = st.text_input("Nomor peserta", value=tumpang["PSTV01"].iloc[0] if len(tumpang) else "")
    riwayat = gabung[gabung["PSTV01"] == pid].sort_values("FKL03")
    st.dataframe(rapi(riwayat[["FKL02", "nama_faskes_sintetis", "FKL03", "FKL04", "FKL18", "skor_risiko", "alasan"]])
                 .rename(columns={**LABEL, "skor_risiko": "Skor", "alasan": "Alasan"}), hide_index=True)
