from datetime import datetime
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

from ringkasan import buat_prompt, ringkasan_aturan, ringkasan_gemini
from detect import KOLOM_WAJIB, baca_klaim, cari_tumpang_tindih, cek_kelengkapan, porsi_keparahan_rs, skor_risiko

st.set_page_config(page_title="KlaimGuard AI", page_icon="🛡️", layout="wide")

LABEL = {
    "FKL02": "ID Kunjungan", "PSTV01": "No. Peserta", "FKL03": "Tgl Datang", "FKL04": "Tgl Pulang",
    "FKL10": "Pelayanan", "FKL18": "Diagnosis", "FKL19": "INA-CBG", "FKL23": "Keparahan",
    "FKL47": "Biaya Tagih", "nama_faskes_sintetis": "Faskes", "skor_risiko": "Skor", "kategori": "Kategori",
    "alasan": "Alasan",
}
WARNA = {"Tinggi": "🔴", "Sedang": "🟠", "Rendah": "🟢"}
WARNA_HEX = {"Tinggi": "#F06A6A", "Sedang": "#F5A524", "Rendah": "#3DD6A4"}
KOLOM_SKOR = {"Skor": st.column_config.ProgressColumn("Skor", min_value=0, max_value=100, format="%d", color="#F06A6A")}


def rupiah(v):
    return f"Rp {v:,.0f}".replace(",", ".")


def rapi(t):
    # hanya untuk tampilan: tanggal tanpa jam, rupiah dengan pemisah ribuan
    t = t.copy()
    for c in t.columns:
        if pd.api.types.is_datetime64_any_dtype(t[c]):
            t[c] = t[c].dt.strftime("%d-%m-%Y")
        elif c in ("FKL47", "total_tagih"):
            t[c] = t[c].map(rupiah)
        elif c == "kategori":
            t[c] = t[c].map(lambda k: f"{WARNA.get(k, '')} {k}")
    return t.rename(columns=LABEL)


def kartu(kolom, judul, nilai, ket):
    with kolom.container(border=True):
        st.caption(judul)
        st.markdown(f"## {nilai}")
        st.caption(ket)


@st.cache_data
def analisis(df):
    return skor_risiko(df), cek_kelengkapan(df), cari_tumpang_tindih(df)


with st.sidebar:
    st.markdown("## 🛡️ KlaimGuard AI")
    st.caption("Deteksi dini anomali klaim FKRTL JKN untuk verifikator.")
    st.markdown(":green-badge[Data sintetis] :blue-badge[Skema Data Sampel BPJS] :orange-badge[Manusia memutuskan]")
    st.divider()
    st.markdown("**Sumber data**")
    unggah = st.file_uploader("Unggah CSV klaim (opsional)", type="csv")
    st.caption("Tanpa unggahan, aplikasi memakai 2.000 klaim sintetis bawaan.")
    with st.expander("Kolom wajib"):
        st.caption(", ".join(KOLOM_WAJIB))
    st.divider()
    st.markdown("**Cara membaca skor**")
    st.caption("Skor = bobot aturan yang menyala + 0,3 × anomali statistik. Tinggi mulai 50, Sedang 30 sampai 49.")
    st.caption("[Kode sumber di GitHub](https://github.com/PolkesrayaPress/klaimguard)")

df, err = baca_klaim(unggah if unggah else "klaim.csv")
if err:
    st.error(err)
    st.stop()
risiko, lengkap, tumpang = analisis(df)
gabung = df.merge(risiko, on="FKL02")
tinggi = gabung[gabung["kategori"] == "Tinggi"]

st.title("Ruang Kerja Verifikasi Klaim")
st.caption("Hasil adalah rekomendasi pemeriksaan. Keputusan tetap pada verifikator.")

k1, k2, k3, k4 = st.columns(4)
kartu(k1, "Klaim dianalisis", f"{len(df):,}".replace(",", "."), "Rawat inap dan rawat jalan FKRTL")
kartu(k2, "Risiko tinggi", f"{len(tinggi)}", f"{len(tinggi) / max(len(df), 1):.1%} klaim masuk antrean prioritas".replace(".", ",", 1))
kartu(k3, "Nilai klaim risiko tinggi", f"Rp {tinggi['FKL47'].sum() / 1e9:.2f} miliar".replace(".", ","), "Ditinjau sebelum dibayar")
kartu(k4, "Rawat tumpang tindih", f"{len(tumpang)} pasangan", "Peserta sama, waktu sama, RS berbeda")

tab1, tab2, tab3 = st.tabs(["📋 Antrean Verifikasi", "🔗 Korelasi Lintas Faskes", "📊 Kelengkapan & Pola RS"])

with tab1:
    kiri, kanan = st.columns([3, 2], gap="large")
    with kiri:
        pilih_kat = st.segmented_control("Kategori", ["Tinggi", "Sedang", "Rendah"], default=["Tinggi"], selection_mode="multi")
        antre = gabung[gabung["kategori"].isin(pilih_kat or [])].sort_values("skor_risiko", ascending=False)
        kolom = ["FKL02", "nama_faskes_sintetis", "FKL18", "FKL47", "skor_risiko", "kategori"]
        st.dataframe(rapi(antre[kolom]), hide_index=True, height=520, column_config=KOLOM_SKOR)
        st.caption(f"{len(antre)} klaim ditampilkan, diurutkan dari skor tertinggi.")
    with kanan:
        if len(antre):
            klaim = st.selectbox("Periksa klaim", antre["FKL02"])
            k = antre.set_index("FKL02").loc[klaim]
            with st.container(border=True):
                st.markdown(
                    f"<span style='color:{WARNA_HEX[k['kategori']]};font-size:2.2rem;font-weight:700'>{k['skor_risiko']}</span>"
                    f"<span style='color:{WARNA_HEX[k['kategori']]};font-weight:600'> &nbsp;Risiko {k['kategori']}</span>",
                    unsafe_allow_html=True)
                st.caption(f"{k['nama_faskes_sintetis']} · {k['FKL10']} · {k['FKL18']} · {k['FKL19']} · {rupiah(k['FKL47'])}")
                st.markdown("**Alasan**")
                for teks in k["alasan"].split("; "):
                    st.markdown(f"- {teks}")
                st.caption(f"Aturan {k['skor_aturan']} + anomali statistik {k['skor_anomali']:.0f} × 0,3")
                if st.button("✨ Ringkasan untuk verifikator (GenAI)", width="stretch"):
                    cache = st.session_state.setdefault("ringkasan", {})
                    if klaim not in cache:
                        try:
                            kunci, model = st.secrets.get("GEMINI_API_KEY"), st.secrets.get("GEMINI_MODEL")
                        except Exception:  # aplikasi tanpa berkas secrets
                            kunci, model = None, None
                        if unggah:  # data unggahan bisa berisi data nyata: jangan kirim ke AI publik
                            kunci = None
                        with st.spinner("Menyusun ringkasan..."):
                            cache[klaim] = ringkasan_gemini(kunci, buat_prompt({**k.to_dict(), "FKL02": klaim}), model)
                    teks, model_dipakai, err = cache[klaim]
                    if teks:
                        st.info(teks)
                        st.caption(f"Dibuat oleh {model_dipakai} dari data sintetis. Periksa sebelum dipakai.")
                    else:
                        st.info(ringkasan_aturan({**k.to_dict(), "FKL02": klaim}))
                        st.caption(f"Ringkasan versi aturan; GenAI tidak tersedia ({err}).")
            with st.container(border=True):
                keputusan = st.radio("Keputusan verifikator", ["Setujui", "Tunda, minta klarifikasi faskes", "Teruskan ke investigasi"])
                catatan = st.text_input("Catatan")
                if st.button("Simpan keputusan", type="primary", width="stretch"):
                    # shortcut: log hanya bertahan selama sesi browser, untuk produksi perlu basis data
                    st.session_state.setdefault("log", []).append({
                        "Waktu (WIB)": datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d-%m-%Y %H:%M"), "ID Kunjungan": klaim,
                        "Skor": int(k["skor_risiko"]), "Keputusan": keputusan, "Catatan": catatan,
                    })
                    st.toast("Keputusan tersimpan di log audit", icon="✅")
        else:
            st.info("Pilih minimal satu kategori.")
    log = pd.DataFrame(st.session_state.get("log", []))
    st.markdown("#### Log audit keputusan")
    if len(log):
        st.dataframe(log, hide_index=True)
        st.download_button("Unduh log audit (CSV)", log.to_csv(index=False), "log_audit_klaimguard.csv")
    else:
        st.caption("Belum ada keputusan di sesi ini.")

with tab2:
    st.markdown("#### Garis waktu klaim per peserta")
    pid = st.text_input("Ketik nomor peserta lalu tekan Enter", value=tumpang["PSTV01"].iloc[0] if len(tumpang) else "")
    riwayat = gabung[gabung["PSTV01"] == pid.strip()].sort_values("FKL03")
    if len(riwayat):
        g = riwayat.assign(selesai=riwayat["FKL04"].fillna(riwayat["FKL03"]) + pd.Timedelta(days=1))
        bar = alt.Chart(g).mark_bar(height=28, cornerRadius=6).encode(
            x=alt.X("FKL03:T", title="Tanggal", axis=alt.Axis(format="%d-%m-%Y", labelAngle=0, tickCount="day", labelOverlap=True)),
            x2="selesai:T",
            y=alt.Y("nama_faskes_sintetis:N", title=None),
            color=alt.Color("kategori:N", scale=alt.Scale(domain=list(WARNA_HEX), range=list(WARNA_HEX.values())), title="Risiko"),
            tooltip=["FKL02", "nama_faskes_sintetis", "FKL18", "skor_risiko", "alasan"],
        ).properties(height=70 + 44 * riwayat["nama_faskes_sintetis"].nunique())
        with st.container(border=True):
            st.altair_chart(bar, width="stretch")
        st.dataframe(rapi(riwayat[["FKL02", "nama_faskes_sintetis", "FKL03", "FKL04", "FKL18", "skor_risiko", "alasan"]]),
                     hide_index=True, column_config=KOLOM_SKOR)
    elif pid:
        st.warning("Nomor peserta tidak ditemukan")

    st.markdown("#### Rawat inap tumpang tindih: peserta sama, waktu sama, RS berbeda")
    tt = tumpang[["PSTV01", "nama_faskes_sintetis_a", "FKL03_a", "FKL04_a", "nama_faskes_sintetis_b", "FKL03_b", "FKL04_b",
                  "hari_tumpang_tindih", "total_tagih"]]
    st.dataframe(rapi(tt).rename(columns={
        "nama_faskes_sintetis_a": "Faskes A", "FKL03_a": "Masuk A", "FKL04_a": "Pulang A", "nama_faskes_sintetis_b": "Faskes B",
        "FKL03_b": "Masuk B", "FKL04_b": "Pulang B", "hari_tumpang_tindih": "Hari Tumpang Tindih", "total_tagih": "Total Tagih"}),
        hide_index=True)

with tab3:
    kiri, kanan = st.columns([1, 1], gap="large")
    with kiri:
        st.markdown("#### Porsi keparahan III rawat inap per RS")
        porsi = (porsi_keparahan_rs(df) * 100).rename("persen").reset_index()
        ambang = 2 * porsi["persen"].median()
        porsi["status"] = porsi["persen"].map(lambda p: "Dicurigai upcoding" if p > ambang else "Wajar")
        dasar = alt.Chart(porsi)
        batang = dasar.mark_bar(cornerRadius=4).encode(
            x=alt.X("persen:Q", title="Persen keparahan III"),
            y=alt.Y("nama_faskes_sintetis:N", sort="-x", title=None),
            color=alt.Color("status:N", scale=alt.Scale(domain=["Dicurigai upcoding", "Wajar"], range=["#F06A6A", "#3D5A80"]), title=None),
            tooltip=["nama_faskes_sintetis", alt.Tooltip("persen:Q", format=".1f")],
        )
        garis = alt.Chart(pd.DataFrame({"x": [ambang]})).mark_rule(strokeDash=[6, 4], color="#E8EEF0").encode(x="x:Q")
        with st.container(border=True):
            st.altair_chart((batang + garis).properties(height=360), width="stretch")
        st.caption(f"Garis putus-putus: ambang {ambang:.0f}%, dua kali median regional.")
    with kanan:
        kurang = df.merge(lengkap[~lengkap["lengkap"]], on="FKL02")
        st.markdown(f"#### {len(kurang)} klaim dengan berkas tidak lengkap")
        st.dataframe(rapi(kurang[["FKL02", "nama_faskes_sintetis", "FKL10", "berkas_kurang"]])
                     .rename(columns={"berkas_kurang": "Berkas Kurang"}), hide_index=True, height=400)
    if "label_sintetis" in gabung:
        with st.expander("Validasi terhadap label data sintetis"):
            fraud = gabung["label_sintetis"] != "normal"
            hit = gabung["kategori"] == "Tinggi"
            v1, v2 = st.columns(2)
            v1.metric("Presisi kategori Tinggi", f"{(fraud & hit).sum() / max(hit.sum(), 1):.0%}")
            v2.metric("Recall kategori Tinggi", f"{(fraud & hit).sum() / max(fraud.sum(), 1):.0%}")
            per_pola = gabung[fraud].groupby("label_sintetis")["kategori"].apply(lambda s: (s == "Tinggi").mean() * 100)
            st.dataframe(per_pola.round().rename("Tertangkap (%)"))
            st.caption("Pola kecurangan ditanam sendiri di data sintetis, jadi angka ini menguji logika, bukan kinerja di data nyata.")
