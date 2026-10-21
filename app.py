import pandas as pd
import streamlit as st

st.set_page_config(page_title="KlaimGuard AI", layout="wide")
st.title("KlaimGuard AI")
st.caption(
    "Deteksi dini anomali klaim FKRTL JKN. Struktur data mengikuti kode variabel Data Sampel BPJS Kesehatan; "
    "seluruh isi data di aplikasi ini sintetis."
)

LABEL = {
    "FKL02": "ID Kunjungan", "PSTV01": "No. Peserta", "PSTV03": "Tgl Lahir", "PSTV05": "Jenis Kelamin",
    "FKL03": "Tgl Datang", "FKL04": "Tgl Pulang", "FKL05": "Provinsi", "FKL06": "Kab/Kota",
    "FKL07": "Kepemilikan", "FKL09": "Tipe RS", "FKL10": "Tingkat Pelayanan", "FKL18": "Diagnosis Primer",
    "FKL19": "Kode INA-CBG", "FKL23": "Keparahan", "FKL47": "Biaya Tagih", "FKL48": "Biaya Verifikasi",
    "nama_faskes_sintetis": "Faskes", "berkas_pendukung": "Berkas Pendukung",
}


@st.cache_data
def load_claims():
    return pd.read_csv("klaim.csv", parse_dates=["PSTV03", "FKL03", "FKL04"], dtype={"PSTV01": str, "FKL05": str, "FKL06": str})


df = load_claims()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Klaim FKRTL", len(df))
c2.metric("Peserta", df["PSTV01"].nunique())
c3.metric("Faskes", df["nama_faskes_sintetis"].nunique())
c4.metric("Total biaya tagih", f"Rp {df['FKL47'].sum() / 1e9:.1f} M")

tab1, tab2, tab3 = st.tabs(["Kelengkapan", "Skor Risiko", "Korelasi Lintas Faskes"])
with tab1:
    # label_sintetis adalah kunci jawaban data sintetis, tidak ditampilkan ke verifikator
    view = df.drop(columns=["label_sintetis", "FKL08"]).rename(columns=LABEL)
    st.dataframe(view.head(50), hide_index=True)
with tab2:
    st.info("Belum diisi")
with tab3:
    st.info("Belum diisi")
