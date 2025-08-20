import os
from collections import Counter
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

# === Ambil variabel dari environment Railway ===
TOKEN = os.getenv("TOKEN")  # Token bot dari @BotFather
URL = os.getenv("URL")      # URL Railway app, contoh: https://nama-app.up.railway.app

# === Mapping posisi roda Mega Wheel ===
POSISI_RODA = {
    0: 1,  1: 2,  2: 5,  3: 1,  4: 2,  5: 10, 6: 1,  7: 5,  8: 1,  9: 2,
    10: 8, 11: 1, 12: 20, 13: 2, 14: 1, 15: 10, 16: 2, 17: 5,  18: 1, 19: 15,
    20: 2, 21: 1, 22: 5,  23: 1, 24: 8,  25: 1, 26: 30, 27: 2,  28: 1, 29: 5,
    30: 2, 31: 1, 32: 10, 33: 2, 34: 1,  35: 2,  36: 8,  37: 1,  38: 2, 39: 20,
    40: 1, 41: 5,  42: 1,  43: 10, 44: 1,  45: 2,  46: 15, 47: 1,  48: 5,  49: 1,
    50: 8, 51: 1,  52: 2,  53: 40
}
TOTAL_POSISI = len(POSISI_RODA)

# === Kelompok posisi roda ===
KELOMPOK_POSISI = {
    1: [53,0,1,2,3,4,5],
    2: [6,7,8,9,10,11,12],
    3: [13,14,15,16,17,18,19],
    4: [20,21,22,23,24,25,26],
    5: [26,27,28,29,30,31,32],
    6: [33,34,35,36,37,38,39],
    7: [40,41,42,43,44,45,46],
    8: [47,48,49,50,51,52,53]
}

# === Jumlah segmen per angka ===
SEGMEN = {
    1: 20,
    2: 13,
    5: 7,
    8: 4,
    10: 4,
    15: 2,
    20: 2,
    30: 1,
    40: 1
}

def get_kelompok(pos):
    for k, posisi_list in KELOMPOK_POSISI.items():
        if pos in posisi_list:
            return k
    return None

# === Variabel global ===
history_posisi = []
history_kelompok = []
transisi_kelompok_counter = Counter()
prev_skor_angka = Counter()

# === Fungsi cari posisi tengah dari pola input ===
def cari_posisi_dari_pola(pola):
    angka_roda = [POSISI_RODA[i] for i in range(TOTAL_POSISI)]
    for i in range(TOTAL_POSISI):
        cek = [angka_roda[(i + j - 3) % TOTAL_POSISI] for j in range(7)]
        if cek == pola:
            return i
    pola_reverse = pola[::-1]
    for i in range(TOTAL_POSISI):
        cek = [angka_roda[(i + j - 3) % TOTAL_POSISI] for j in range(7)]
        if cek == pola_reverse:
            return i
    return None

# === Handler input manual ===
async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global prev_skor_angka
    try:
        pola = [int(x.strip()) for x in update.message.text.split(",")]
        if len(pola) != 7:
            await update.message.reply_text("❌ Masukkan 7 angka (3 kiri, 1 tengah, 3 kanan), pisahkan dengan koma.")
            return

        posisi_tengah = cari_posisi_dari_pola(pola)
        if posisi_tengah is None:
            await update.message.reply_text("❌ Pola tidak ditemukan di roda.")
            return

        # === Transisi kelompok ===
        kelompok_sekarang = get_kelompok(posisi_tengah)
        if kelompok_sekarang:
            if history_kelompok:
                prev_kelompok = history_kelompok[-1]
                pasangan = (prev_kelompok, kelompok_sekarang)
                transisi_kelompok_counter[pasangan] += 1
            history_kelompok.append(kelompok_sekarang)

        # === Simpan posisi untuk sektor panas ===
        history_posisi.append(posisi_tengah)
        nomor_putaran = len(history_posisi)

        # === Hitung sektor panas ===
        counter = Counter(history_posisi)
        posisi_sorted = sorted(counter.items(), key=lambda x: x[1], reverse=True)

        teks = f"🎯 Putaran {nomor_putaran}\n"
        teks += f"✅ : {posisi_tengah} (angka {POSISI_RODA[posisi_tengah]}) - Kelompok {kelompok_sekarang}\n"

        # === Hitung skor angka (dibagi segmen) ===
        skor_angka = Counter()

        # 1. Sektor panas
        for pos, freq in posisi_sorted[:3]:
            num = POSISI_RODA[pos]
            skor_angka[num] += (7 * freq) / SEGMEN.get(num, 1)

        # 2. 5 angka panas
        angka_counter = Counter()
        for pos, freq in counter.items():
            for offset in range(-3, 4):
                posisi_target = (pos + offset) % TOTAL_POSISI
                angka_counter[POSISI_RODA[posisi_target]] += freq
        angka_filtered = [(num, freq) for num, freq in angka_counter.items()]
        for num, _ in sorted(angka_filtered, key=lambda x: x[1], reverse=True)[:5]:
            skor_angka[num] += 4 / SEGMEN.get(num, 1)

        # 3. Kelompok paling sering muncul
        if history_kelompok:
            k_teratas, _ = Counter(history_kelompok).most_common(1)[0]
            for p in KELOMPOK_POSISI[k_teratas]:
                num = POSISI_RODA[p]
                skor_angka[num] += 3 / SEGMEN.get(num, 1)

        # 4. Prediksi kelompok berikutnya
        if kelompok_sekarang:
            kandidat = {k2: count for (k1, k2), count in transisi_kelompok_counter.items() if k1 == kelompok_sekarang}
            if kandidat:
                prediksi_kelompok = sorted(kandidat, key=kandidat.get, reverse=True)[:2]
                for k in prediksi_kelompok:
                    for p in KELOMPOK_POSISI[k]:
                        num = POSISI_RODA[p]
                        skor_angka[num] += 3 / SEGMEN.get(num, 1)

        # 5. Transisi antar kelompok
        if kelompok_sekarang and history_kelompok:
            prev_kelompok = history_kelompok[-1]
            pasangan = (prev_kelompok, kelompok_sekarang)
            if transisi_kelompok_counter[pasangan] > 1:
                for p in KELOMPOK_POSISI[kelompok_sekarang]:
                    num = POSISI_RODA[p]
                    skor_angka[num] += 4 / SEGMEN.get(num, 1)

        # === Buat tabel skor ===
        rows = []
        rows.append("Angka   Status")
        rows.append("----------------")
        for num, val in sorted(skor_angka.items(), key=lambda x: x[1], reverse=True):
            prev_val = prev_skor_angka.get(num, 0)
            if val > prev_val:
                tanda = "🔝"
            elif val < prev_val:
                tanda = "⬇️"
            else:
                tanda = "🔜"
            rows.append(f"{str(num).ljust(6)} {tanda}")
            rows.append("----------------")

        tabel_skor = "\n".join(rows)
        teks += f"\n\n🏆 <b>Skor angka</b> :\n<pre>{tabel_skor}</pre>"

        prev_skor_angka = skor_angka.copy()
        await update.message.reply_text(teks, parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}", parse_mode="Markdown")

# === Reset histori ===
async def reset_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global history_posisi, history_kelompok, transisi_kelompok_counter, prev_skor_angka
    
    history_posisi = []
    history_kelompok = []
    transisi_kelompok_counter = Counter()
    prev_skor_angka = Counter()

    await update.message.reply_text(
        "♻️ Semua histori (sektor panas, transisi, kelompok, skor) berhasil direset."
    )
# === Main bot (Webhook) ===
if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8080))
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CommandHandler("reset", reset_history))

    print("Bot berjalan dengan webhook...")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{URL}/{TOKEN}"
    )
