# Mutabakat Asistanı

Sipariş kayıtları ile ödeme kayıtlarını karşılaştıran Python uygulaması.

Aynı siparişe ait parçalı ödemeleri toplar; tam, eksik, fazla ve
hiç ödenmemiş siparişleri belirler. Sipariş kaydı bulunmayan
ödemeleri ayrıca gösterir.

## Özellikler

- Tarayıcı üzerinden sipariş ve ödeme CSV dosyası yükleme.
- Gerekli sütun, boş alan ve benzersiz kimlik kontrolü.
- Para tutarlarını doğrulama ve tam sayı kuruşa dönüştürme.
- Sipariş kimliğine göre ödemeleri gruplama.
- Eşleşmeyen kayıtları koruyarak tabloları birleştirme.
- Ödeme durumuna göre filtreleme.
- Eksik, fazla ve eşleşmeyen ödeme toplamlarını gösterme.
- Tam veya filtrelenmiş raporu CSV olarak indirme.
- Üç sayfalı Excel raporu indirme.
- Terminal üzerinden rapor üretme.
- Para dönüşümü ve mutabakat hesaplama akışı için otomatik testler.

## Teknolojiler

- Python
- pandas
- Streamlit
- openpyxl
- pytest

Geliştirme ve test ortamı: Windows, Python 3.12.6 ve PyCharm.

Paket sürümleri `requirements.txt` dosyasında kayıtlıdır.

## Kurulum

Aşağıdaki komutları Windows PowerShell'de proje klasörünün
içinde çalıştırın.

### 1. Sanal ortam oluşturun

Python 3.12'nin kurulu olması gerekir.

```powershell
py -3.12 -m venv .venv
```

PyCharm ile proje için zaten bir `.venv` oluşturduysanız
bu adımı atlayabilirsiniz.

### 2. Paketleri kurun

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Komutlar doğrudan sanal ortamın Python yorumlayıcısını kullandığı
için ayrıca ortamı etkinleştirmek gerekmez.

## Tarayıcı Arayüzünü Çalıştırma

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Terminalde gösterilen Local URL adresini tarayıcıda açın.
Varsayılan adres genellikle `http://localhost:8501` olur.

1. Sipariş alanına `data/orders.csv` dosyasını yükleyin.
2. Ödeme alanına `data/payments.csv` dosyasını yükleyin.
3. Parasal özeti inceleyin.
4. Ödeme durumu filtresiyle kayıtları seçin.
5. Raporları CSV veya Excel olarak indirin.

Filtrelenmiş CSV, seçilen durumdaki kayıtları içerir.
Tam CSV ve Excel raporu durum filtresinden etkilenmez.
Parasal özet kartları bütün verinin toplamlarını gösterir.

Uygulamayı durdurmak için terminalde `Ctrl+C` kullanın.

## Terminal Üzerinden Çalıştırma

Girdi dosyalarını aşağıdaki konumlara yerleştirin:

- `data/orders.csv`
- `data/payments.csv`

Ardından çalıştırın:

```powershell
.\.venv\Scripts\python.exe main.py
```

Raporlar `output` klasörüne kaydedilir:

- `mutabakat_raporu.csv`
- `mutabakat_raporu.xlsx`

Aynı isimli raporlar her çalıştırmada yenilenir.
Excel dosyası açıkken üzerine yazılamıyorsa dosyayı kapatıp
programı yeniden çalıştırın.

## Girdi Dosyaları

CSV dosyaları UTF-8 kodlamalı ve virgülle ayrılmış olmalıdır.
Tutarlar TL cinsindedir; ondalık ayırıcı noktadır.

### Siparişler

Gerekli sütunlar:

```csv
order_id,order_date,customer,order_total
ORD-001,2026-10-01,Ali,1000.00
```

- `order_id`: Benzersiz sipariş kimliği.
- `order_date`: Sipariş tarihi; beklenen biçim `YYYY-MM-DD`.
- `customer`: Müşteri adı.
- `order_total`: Pozitif sipariş tutarı.

### Ödemeler

Gerekli sütunlar:

```csv
payment_id,order_id,amount
PAY-001,ORD-001,600.00
PAY-002,ORD-001,400.00
```

- `payment_id`: Benzersiz ödeme işlemi kimliği.
- `order_id`: Ödemenin ilişkilendirildiği sipariş kimliği.
- `amount`: Pozitif ödeme tutarı.

Bir siparişe birden fazla ödeme yapılabilir.
Bu nedenle ödeme tablosundaki `order_id` tekrar edebilir.

## Hesaplama Kuralları

Para hesaplamaları tam sayı kuruş üzerinden yapılır.

Örnek: `179.19` TL, `17919` kuruş olarak saklanır.

```text
Fark = Toplam ödeme − Sipariş tutarı
```

| Durum | Açıklama |
|---|---|
| PAID | Sipariş ile ödeme toplamı eşit. |
| UNDERPAID | Ödeme var ancak sipariş tutarından az. |
| OVERPAID | Ödeme toplamı sipariş tutarından fazla. |
| UNPAID | Sipariş için ödeme kaydı bulunmuyor. |
| UNMATCHED_PAYMENT | Ödeme var ancak sipariş kaydı bulunmuyor. |

Sipariş kaydı olmayan ödemelerde sipariş tutarı ve fark
bilinmediği için boş bırakılır; sıfır kabul edilmez.

Eksik ödeme toplamı, eksik ödenmiş ve hiç ödenmemiş
siparişlerin kalan tutarlarını içerir.

## Excel Raporu

| Sayfa | İçerik |
|---|---|
| Tum_Kayitlar | Bütün mutabakat sonuçları. |
| Incelenecek_Kayitlar | PAID dışındaki kayıtlar. |
| Parasal_Ozet | Beş parasal gösterge. |

Raporlardaki `_cents` ve `tutar_kurus` alanları kuruş cinsindedir.
`tutar_tl_gosterim` alanı okunabilir metindir.

## Örnek Veri Seti

`data` klasöründeki veriler eğitim amacıyla üretilmiştir.

- 1.000 sipariş.
- 1.450 ödeme işlemi.
- 1.050 mutabakat sonuç kaydı.

Beklenen durum dağılımı:

| Durum | Kayıt sayısı |
|---|---:|
| PAID | 650 |
| UNDERPAID | 150 |
| OVERPAID | 100 |
| UNPAID | 100 |
| UNMATCHED_PAYMENT | 50 |

## Testleri Çalıştırma

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

Mevcut testlerde beklenen sonuç: `15 passed`.

Test kapsamı:

- Yedi geçerli para girdisinin dönüşümü.
- Yedi geçersiz para girdisinin reddedilmesi.
- Parçalı ödeme, beş ödeme durumu, eksik bilgiler ve
  parasal özeti kapsayan bir hesaplama akışı testi.

Tarayıcı etkileşimleri ve dosya indirme işlemleri
mevcut otomatik testlerin kapsamında değildir.

## Dosyaların Görevleri

| Dosya | Görevi |
|---|---|
| app.py | Streamlit arayüzü. |
| main.py | Terminal üzerinden çalışma akışı. |
| reconciliation.py | Doğrulama ve mutabakat hesaplamaları. |
| formatting.py | Para tutarlarını TL metnine dönüştürme. |
| export.py | CSV ve Excel çıktıları oluşturma. |
| tests/test_money.py | Para dönüşüm testleri. |
| tests/test_reconciliation.py | Mutabakat akışı testi. |

## Mevcut Kapsam ve Sınırlar

- Girdi olarak CSV desteklenir; Excel çıktı olarak üretilir.
- Bütün tutarların aynı para biriminde, TL olduğu varsayılır.
- Sıfır ve negatif tutarlar reddedilir; iadeler modellenmez.
- Tutarlar en fazla iki ondalık basamak içerebilir.
- Benzersiz olması gereken kimliklerdeki tekrarlar reddedilir.
- Tarih alanının boş olmaması kontrol edilir; tarih biçiminin
  ve takvim açısından geçerliliğinin kontrolü henüz yoktur.
- Kalıcı işlem geçmişi veya veritabanı kaydı yoktur.
- Kullanıcı hesabı ve banka bağlantısı yoktur.