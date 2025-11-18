# 🎙️ Otomatik Video Dublaj Aracı (SRT to Audio)

Bu araç, elinizdeki altyazı dosyalarını (**SRT**) kullanarak saniyeler içinde **profesyonel kalitede, senkronize dublaj ses dosyaları (WAV)** oluşturur.

Python veya karmaşık kütüphaneler kurmanıza gerek yoktur. **Tamamen taşınabilir (Portable)** tek bir `.exe` dosyası olarak çalışır.

## 🌟 Özellikler

* **Yüksek Kalite Ses:** Microsoft'un Neural (Sinirsel) TTS motorunu kullanır. Sesler robotik değil, haber spikeri kalitesindedir.
* **Tam Otomasyon:** 12 (veya daha fazla) dili tek tıklamayla sırayla işler.
* **Akıllı Zamanlama:** Eğer üretilen ses, altyazı süresinden uzunsa, **ses perdesini (pitch) bozmadan** sesi hızlandırarak süreye sığdırır.
* **Kolay Yapılandırma:** Kod bilgisi gerektirmez. Tüm ayarlar `languages.json` dosyasından yönetilir.
* **Taşınabilir:** USB bellekte veya herhangi bir diskte çalışabilir. Kurulum gerektirmez.

## 🚀 Nasıl Kullanılır?
1. Altyazıları Hazırlayın: .srt formatındaki altyazı dosyalarınızı input_subtitles klasörüne kopyalayın.

2. Çalıştırın: DublajAraci.exe dosyasına çift tıklayın.

**Sonuç**: İşlem bittiğinde ses dosyalarınızı outputs klasöründe bulabilirsiniz.

Not: Bu araç ses üretmek için İnternet Bağlantısı gerektirir.

Not2: Dil ekleyip çıkartmak için languages.json dosyasını Not Defteri ile açın ve yapıyı bozmadan değişikliklerinizi yapın.

## ⚠️ Sorun Giderme
* **Program açılıp hemen kapanıyor:** languages.json dosyasında yazım hatası olabilir (örneğin fazladan bir virgül).

* **Ses dosyası oluşmuyor:** input_subtitles klasöründe, JSON dosyasında belirttiğiniz isimde bir .srt dosyası olduğundan emin olun.

* **Hızlandırma hatası:** Library klasörünün içinde ffmpeg.exe olduğundan emin olun.
