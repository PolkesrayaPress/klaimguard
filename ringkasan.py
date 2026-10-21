"""Ringkasan klaim untuk verifikator: Gemini bila tersedia, versi aturan bila tidak."""
import requests

# dicoba berurutan; seri 2.x dibatasi atau sudah dimatikan untuk pengguna baru (cek Oktober 2026)
MODEL_CADANGAN = ["gemini-3.5-flash-lite", "gemini-flash-latest", "gemini-3.6-flash"]
URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"


def buat_prompt(k):
    return f"""Anda membantu verifikator klaim BPJS Kesehatan. Data di bawah ini SINTETIS untuk demo.
Klaim {k['FKL02']} di {k['nama_faskes_sintetis']}: {k['FKL10']}, diagnosis {k['FKL18']}, INA-CBG {k['FKL19']},
tanggal {k['FKL03']:%d-%m-%Y} sampai {k['FKL04']:%d-%m-%Y}, biaya tagih Rp {k['FKL47']:,.0f}.
Skor risiko {k['skor_risiko']} ({k['kategori']}). Alasan dari sistem: {k['alasan']}.

Tulis dalam bahasa Indonesia, tanpa markdown tebal:
1. Ringkasan temuan, maksimal 3 kalimat. Sebut sebagai indikasi, bukan tuduhan kecurangan.
2. Dokumen yang perlu diminta ke faskes, maksimal 3 butir.
3. Satu pertanyaan klarifikasi untuk faskes."""


def ringkasan_aturan(k):
    alasan = [a for a in k["alasan"].split("; ") if a != "Tidak ada aturan yang menyala"]
    if not alasan:
        return "Tidak ada indikasi dari aturan. Klaim dapat diproses sesuai prosedur biasa."
    return (f"Klaim {k['FKL02']} di {k['nama_faskes_sintetis']} berskor {k['skor_risiko']} karena: "
            + "; ".join(a[0].lower() + a[1:] for a in alasan)
            + ". Disarankan meminta resume medis, rincian biaya, dan riwayat rawat peserta sebelum klaim dibayar.")


def ringkasan_gemini(api_key, prompt, model_pilihan=None, timeout=25):
    """Mengembalikan (teks, model, None) bila berhasil, atau (None, None, pesan_error)."""
    error = "kunci API belum diatur"
    for model in ([model_pilihan] if model_pilihan else []) + MODEL_CADANGAN:
        if not api_key:
            break
        try:
            r = requests.post(URL.format(model), headers={"x-goog-api-key": api_key}, timeout=timeout, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.2},
            })
        except requests.RequestException as e:
            error = f"koneksi gagal ({type(e).__name__})"
            continue
        if r.status_code != 200:
            error = f"{model}: HTTP {r.status_code}"
            continue
        parts = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
        teks = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
        if teks:
            return teks, model, None
        error = f"{model}: jawaban kosong"
    return None, None, error
