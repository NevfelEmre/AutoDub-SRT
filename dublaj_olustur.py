import sys
import os
import warnings
import datetime 
import subprocess
import asyncio 
import edge_tts 
import shutil
import json

# --- UYARILARI GİZLEME ---
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

# --- PORTABLE AYARLAR ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- FFMPEG YOLU ---
ffmpeg_dir = os.path.join(BASE_DIR, 'Library')
os.environ['PATH'] = f"{ffmpeg_dir};{os.environ.get('PATH', '')}"
FFMPEG_EXE = os.path.join(ffmpeg_dir, 'ffmpeg.exe')

# --- Script'in geri kalanı ---
from pysubparser import parser
from pydub import AudioSegment
from pathlib import Path

# --- AYARLAR ---
OUTPUT_KLASORU = os.path.join(BASE_DIR, "outputs")
INPUT_KLASORU = os.path.join(BASE_DIR, "input_subtitles")
TEMP_KLASOR = os.path.join(BASE_DIR, "temp_audio")
CONFIG_DOSYASI = os.path.join(BASE_DIR, "languages.json")

# --- YARDIMCI FONKSIYONLAR ---
def time_to_millis(time_obj: datetime.time) -> int:
    return (time_obj.hour * 3600000) + \
           (time_obj.minute * 60000) + \
           (time_obj.second * 1000) + \
           (time_obj.microsecond // 1000)

def speed_up_audio(input_path: str, output_path: str, speed_ratio: float):
    if not os.path.exists(FFMPEG_EXE):
        shutil.copy2(input_path, output_path) 
        return

    speed_ratio = max(1.0, speed_ratio) 
    filter_chain = []
    while speed_ratio > 2.0:
        filter_chain.append("atempo=2.0")
        speed_ratio /= 2.0
    filter_chain.append(f"atempo={speed_ratio}")
    filter_string = ",".join(filter_chain)

    command = [FFMPEG_EXE, '-y', '-i', input_path, '-filter:a', filter_string, output_path]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"     !!! Hızlandırma Hatası: {e}")
        if input_path != output_path: 
            shutil.copy2(input_path, output_path)

# --- ANA ASENKRON FONKSIYON ---
async def main():
    Path(OUTPUT_KLASORU).mkdir(exist_ok=True)
    Path(INPUT_KLASORU).mkdir(exist_ok=True)
    Path(TEMP_KLASOR).mkdir(exist_ok=True)

    print(">>> Dublaj Otomasyonu (Final Versiyon)")
    
    if not os.path.exists(CONFIG_DOSYASI):
        print(f"!!! HATA: Ayar dosyasi bulunamadi: {CONFIG_DOSYASI}")
        input("Kapatmak icin Enter'a basin...")
        return

    try:
        with open(CONFIG_DOSYASI, 'r', encoding='utf-8') as f:
            IS_LISTESI = json.load(f)
    except Exception as e:
        print(f"!!! HATA: JSON dosyasi bozuk: {e}")
        input("Kapatmak icin Enter'a basin...")
        return

    print(f">>> Toplam {len(IS_LISTESI)} adet dil islenecek...")

    for i, is_tanimi in enumerate(IS_LISTESI):
        altyazi_dosyasi_adi = is_tanimi.get('altyazi')
        dil_kodu = is_tanimi.get('dil')
        secilen_ses = is_tanimi.get('ses')
        cikti_adi = is_tanimi.get('cikti')

        if not all([altyazi_dosyasi_adi, dil_kodu, secilen_ses, cikti_adi]):
            continue

        altyazi_tam_yolu = os.path.join(INPUT_KLASORU, altyazi_dosyasi_adi)
        cikti_yolu = os.path.join(OUTPUT_KLASORU, cikti_adi)

        print(f"\n--- İŞLEM {i+1}/{len(IS_LISTESI)}: {dil_kodu.upper()} -> SES: {secilen_ses} ---")

        try:
            subs = list(parser.parse(altyazi_tam_yolu, encoding='utf-8-sig'))
        except Exception as e:
            print(f"!!! HATA: Altyazi okunamadi: {e}")
            continue

        try:
            toplam_sure_ms = time_to_millis(subs[-1].end)
        except IndexError:
            print("!!! HATA: Altyazi dosyasi bos.")
            continue
            
        final_dublaj = AudioSegment.silent(duration=toplam_sure_ms)
        print(f">>> {len(subs)} satir isleniyor...")

        for sub_index, sub in enumerate(subs):
            baslama_ms = time_to_millis(sub.start)
            bitis_ms = time_to_millis(sub.end)
            altyazi_suresi_ms = bitis_ms - baslama_ms
            metin = sub.text
            
            # --- HER SATIRI YAZDIR ---
            print(f"  {sub_index+1}/{len(subs)}: [{sub.start.strftime('%H:%M:%S')}]")
            
            temp_wav_path_raw = os.path.join(TEMP_KLASOR, f"temp_{dil_kodu}_{sub_index}_raw.mp3") 
            temp_wav_path_final = os.path.join(TEMP_KLASOR, f"temp_{dil_kodu}_{sub_index}_final.wav")

            try:
                communicate = edge_tts.Communicate(metin, secilen_ses)
                await communicate.save(temp_wav_path_raw)
                
                if not os.path.exists(temp_wav_path_raw) or os.path.getsize(temp_wav_path_raw) == 0:
                     print(f"!!! HATA: Ses dosyasi olusturulamadi (Satir {sub_index+1})")
                     continue

                # MP3'ü otomatik tanı
                temp_ses_obj = AudioSegment.from_file(temp_wav_path_raw)
                uretilen_sure_ms = len(temp_ses_obj)

                if uretilen_sure_ms > altyazi_suresi_ms and altyazi_suresi_ms > 0:
                    hiz_orani = uretilen_sure_ms / altyazi_suresi_ms
                    if hiz_orani > 1.05: 
                        # Hizlandirirken MP3 -> WAV donusumu otomatik olur
                        print(f"     -> Hızlandırılıyor: {hiz_orani:.2f}x")
                        speed_up_audio(temp_wav_path_raw, temp_wav_path_final, hiz_orani)
                        uretilen_ses = AudioSegment.from_wav(temp_wav_path_final)
                    else:
                         uretilen_ses = AudioSegment.from_file(temp_wav_path_raw)
                else:
                     # Hizlandirma yoksa direkt MP3'ü kullan
                     uretilen_ses = AudioSegment.from_file(temp_wav_path_raw)

                final_dublaj = final_dublaj.overlay(uretilen_ses, position=baslama_ms)
                
            except Exception as e:
                print(f"!!! Satir hatasi ({sub_index+1}): {e}")
                continue

        print(f">>> {dil_kodu.upper()} tamamlandi. Kaydediliyor...")
        final_dublaj.export(cikti_yolu, format="wav")

    print("\n>>> Gecici dosyalar temizleniyor...")
    try:
        shutil.rmtree(TEMP_KLASOR)
    except:
        pass

    print("\n--- TUM ISLEMLER TAMAMLANDI! ---")
    print(f"Çıktılarınız '{OUTPUT_KLASORU}' klasörüne kaydedildi.")

if __name__ == "__main__":
    asyncio.run(main())