import streamlit as st

st.set_page_config(page_title="KlaimGuard AI", layout="wide")
st.title("KlaimGuard AI")
st.caption("Verifikasi klaim JKN berbasis aturan dan anomali")

tab1, tab2, tab3 = st.tabs(["Kelengkapan", "Skor Risiko", "Korelasi Lintas Faskes"])
with tab1:
    st.info("Belum diisi")
with tab2:
    st.info("Belum diisi")
with tab3:
    st.info("Belum diisi")
