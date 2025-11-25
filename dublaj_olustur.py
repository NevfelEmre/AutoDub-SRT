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

# --- KLASÖR AYARLARI ---
OUTPUT_KLASORU = os.path.join(BASE_DIR, "outputs")
INPUT_KLASORU = os.path.join(BASE_DIR, "input_subtitles")
TEMP_KLASOR = os.path.join(BASE_DIR, "temp_audio")
CONFIG_DOSYASI = os.path.join(BASE_DIR, "languages.json")
SETTINGS_DOSYASI = os.path.join(BASE_DIR, "settings.json")

# --- VARSAYILAN AYARLAR ---
DEFAULT_SETTINGS = {
    "genel_hiz": "+20%",
    "sinirsiz_bosluk_kullanimi": True,
    "max_ek_sure_ms": 2500
}

# --- YARDIMCI FONKSIYONLAR ---
def time_to_millis(time_obj: datetime.time) -> int:
    return (time_obj.hour * 3600000) + \
           (time_obj.minute * 60000) + \
           (time_obj.second * 1000) + \
           (time_obj.microsecond // 1000)

def speed_up_audio(input_path, output_path, speed_ratio: float):
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

# --- AYARLARI YUKLEME ---
def load_settings():
    if not os.path.exists(SETTINGS_DOSYASI):
        try:
            with open(SETTINGS_DOSYASI, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_SETTINGS, f, indent=4)
            return DEFAULT_SETTINGS
        except:
            return DEFAULT_SETTINGS
    
    try:
        with open(SETTINGS_DOSYASI, 'r', encoding='utf-8') as f:
            user_settings = json.load(f)
            final_settings = {**DEFAULT_SETTINGS, **user_settings}
            return final_settings
    except Exception as e:
        print(f"!!! Ayar dosyasi bozuk ({e}). Varsayilanlar kullaniliyor.")
        return DEFAULT_SETTINGS

# --- ANA ASENKRON FONKSIYON ---
async def main():
    Path(OUTPUT_KLASORU).mkdir(exist_ok=True)
    Path(INPUT_KLASORU).mkdir(exist_ok=True)
    Path(TEMP_KLASOR).mkdir(exist_ok=True)

    print(f">>> Dublaj Otomasyonu")
    
    # --- AYARLARI OKU ---
    settings = load_settings()
    GENEL_HIZ = settings.get("genel_hiz", "+20%")
    SINIRSIZ_BOSLUK = settings.get("sinirsiz_bosluk_kullanimi", True)
    MAX_EK_SURE = settings.get("max_ek_sure_ms", 2500)
    
    print(f">>> Ayarlar Yuklendi -> Hiz: {GENEL_HIZ} | Esnek Zaman: {SINIRSIZ_BOSLUK} | Max Ek: {MAX_EK_SURE}ms")
    
    if not os.path.exists(CONFIG_DOSYASI):
        print(f"!!! HATA: Dil dosyasi bulunamadi: {CONFIG_DOSYASI}")
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
            final_end_time = time_to_millis(subs[-1].end)
        except IndexError:
            print("!!! HATA: Altyazi dosyasi bos.")
            continue
            
        # Videonun sonuna sadece MAX_EK_SURE kadar milisaniye pay birak
        final_dublaj = AudioSegment.silent(duration=final_end_time + MAX_EK_SURE) 
        
        print(f">>> {len(subs)} satir isleniyor...")

        for sub_index, sub in enumerate(subs):
            baslama_ms = time_to_millis(sub.start)
            kendi_bitis_ms = time_to_millis(sub.end)
            
            # --- AKILLI SURE HESABI ---
            if sub_index + 1 < len(subs):
                # -- ARADAKİ SATIRLAR --
                sonraki_baslama_ms = time_to_millis(subs[sub_index+1].start)
                
                if SINIRSIZ_BOSLUK:
                    # Sonraki cümleye kadar her yeri kullan
                    max_kullanilabilir_bitis = max(kendi_bitis_ms, sonraki_baslama_ms - 100)
                else:
                    # Limitli uzat
                    limitli_bitis = kendi_bitis_ms + MAX_EK_SURE
                    max_kullanilabilir_bitis = min(sonraki_baslama_ms - 100, limitli_bitis)
            else:
                # -- SON SATIR (BURASI DÜZELDİ) --
                # Son satırda asla sınırsız boşluk kullanma.
                # Video bittiği için MAX_EK_SURE kuralına sadık kal.
                # Böylece sığmazsa hızlandırmak zorunda kalır.
                max_kullanilabilir_bitis = kendi_bitis_ms + MAX_EK_SURE
            
            hedef_sure_ms = max_kullanilabilir_bitis - baslama_ms
            metin = sub.text
            
            print(f"  {sub_index+1}/{len(subs)}: [{sub.start.strftime('%H:%M:%S')}]", end="")
            
            temp_wav_path_raw = os.path.join(TEMP_KLASOR, f"temp_{dil_kodu}_{sub_index}_raw.mp3") 
            temp_wav_path_final = os.path.join(TEMP_KLASOR, f"temp_{dil_kodu}_{sub_index}_final.wav")

            try:
                communicate = edge_tts.Communicate(metin, secilen_ses, rate=GENEL_HIZ)
                await communicate.save(temp_wav_path_raw)
                
                if not os.path.exists(temp_wav_path_raw) or os.path.getsize(temp_wav_path_raw) == 0:
                     print(" -> HATA: Dosya olusmadi")
                     continue

                temp_ses_obj = AudioSegment.from_file(temp_wav_path_raw)
                uretilen_sure_ms = len(temp_ses_obj)

                if uretilen_sure_ms > hedef_sure_ms:
                    hiz_orani = uretilen_sure_ms / hedef_sure_ms
                    if hiz_orani > 1.05: 
                        print(f" -> Hizlandiriliyor: {hiz_orani:.2f}x")
                        speed_up_audio(temp_wav_path_raw, temp_wav_path_final, hiz_orani)
                        uretilen_ses = AudioSegment.from_wav(temp_wav_path_final)
                    else:
                         print("")
                         uretilen_ses = AudioSegment.from_file(temp_wav_path_raw)
                else:
                     print("")
                     uretilen_ses = AudioSegment.from_file(temp_wav_path_raw)

                final_dublaj = final_dublaj.overlay(uretilen_ses, position=baslama_ms)
                
            except Exception as e:
                print(f"\n!!! Satir hatasi ({sub_index+1}): {e}")
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