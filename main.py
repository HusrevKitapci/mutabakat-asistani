# ============================================================
# 1. KÜTÜPHANELER VE PROJE FONKSİYONLARI
# ============================================================

# 1.1. Python'ın standart kütüphanesi
# Path: Dosya ve klasör yollarıyla çalışmamızı sağlar.
from pathlib import Path

# 1.2. Dışarıdan kurduğumuz kütüphane
# pandas: Dosyaları okumak ve tablolar üzerinde işlem yapmak için kullanılır.
import pandas as pd

# 1.3. Kendi yazdığımız fonksiyonlar
# Bu fonksiyonlar, aynı klasördeki reconciliation.py dosyasından gelir.
from reconciliation import (
    validate_table,
    parse_money_to_cents,
    summarize_payments,
    merge_orders_and_payments,
    classify_reconciliation,
    build_financial_summary,
)
from formatting import format_cents_as_try

from formatting import format_cents_as_try
from export import export_reports


# ============================================================
# 2. ANA PROGRAM
# ============================================================

def main() -> None:
    """
    Sipariş ve ödeme dosyalarını okur, temel kontrolleri yapar,
    tutarları kuruşa dönüştürür ve ödemeleri siparişe göre özetler.
    """

    # --------------------------------------------------------
    # 2.1. KLASÖR VE DOSYA YOLLARI
    # --------------------------------------------------------

    # 2.1.1. Proje klasörü
    # Yolları, terminalin açık olduğu yere değil,
    # bu main.py dosyasının bulunduğu klasöre göre belirleriz.
    project_dir = Path(__file__).resolve().parent

    # 2.1.2. Veri ve çıktı klasörleri
    data_dir = project_dir / "data"
    output_dir = project_dir / "output"

    # Klasörler yoksa oluşturulur; zaten varsa hata verilmez.
    # Bu aşamada output klasörüne henüz rapor yazmıyoruz.
    data_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    # 2.1.3. Okunacak dosyalar
    orders_path = data_dir / "orders.csv"
    payments_path = data_dir / "payments.csv"

    # 2.1.4. Ekranda gösterilecek örnek kayıt sayısı
    # Bu değer yalnızca gösterimi sınırlar, hesaplamaları etkilemez.
    preview_row_count = 10

    # --------------------------------------------------------
    # 2.2. CSV DOSYALARINI OKUMA
    # --------------------------------------------------------

    # Okuma ayarları:
    # dtype="string": Değerleri başlangıçta metin olarak alırız.
    # keep_default_na=False: Boş alanları boş metin olarak koruruz.
    # encoding="utf-8": Dosyanın karakter kodlamasını belirtiriz.

    # 2.2.1. Sipariş tablosu
    orders = pd.read_csv(
        orders_path,
        dtype="string",
        keep_default_na=False,
        encoding="utf-8",
    )

    # 2.2.2. Ödeme tablosu
    payments = pd.read_csv(
        payments_path,
        dtype="string",
        keep_default_na=False,
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # 2.3. TABLOLARIN YAPISINI VE ZORUNLU ALANLARINI DOĞRULAMA
    # --------------------------------------------------------

    # validate_table fonksiyonu:
    # - Gerekli sütunları ve veri satırlarının varlığını kontrol eder.
    # - Metinlerin başındaki ve sonundaki boşlukları temizler.
    # - Zorunlu alanların boş olmadığını kontrol eder.
    # - Belirttiğimiz kimlik sütunundaki tekrarları reddeder.
    # - Kontroller geçerse temizlenmiş tabloyu döndürür.

    # 2.3.1. Siparişleri doğrula
    # Her siparişin order_id değeri benzersiz olmalıdır.
    orders = validate_table(
        df=orders,
        required_columns=[
            "order_id",
            "order_date",
            "customer",
            "order_total",
        ],
        id_column="order_id",
        table_name="Siparişler",
    )

    # 2.3.2. Ödemeleri doğrula
    # Her ödeme işleminin payment_id değeri benzersiz olmalıdır.
    # Aynı siparişe birden fazla ödeme yapılabileceği için
    # ödeme tablosundaki order_id değerleri tekrar edebilir.
    payments = validate_table(
        df=payments,
        required_columns=[
            "payment_id",
            "order_id",
            "amount",
        ],
        id_column="payment_id",
        table_name="Ödemeler",
    )

    print("Tablo yapısı, zorunlu alan ve benzersiz kimlik kontrolleri geçti.")

    # --------------------------------------------------------
    # 2.4. PARA TUTARLARINI DOĞRULAMA VE KURUŞA DÖNÜŞTÜRME
    # --------------------------------------------------------

    # Hesaplamalarda tam sayı kuruş kullanırız.
    # Örnek: "179.19" TL metni -> 17919 kuruş.
    #
    # map(), sütundaki her değeri dönüşüm fonksiyonuna gönderir.
    # Orijinal tutar sütunlarını koruyup yeni sütunlar oluştururuz.

    # 2.4.1. Sipariş tutarları
    orders["order_total_cents"] = orders["order_total"].map(
        lambda value: parse_money_to_cents(
            value,
            field_name="Siparişler / order_total",
        )
    )

    # 2.4.2. Ödeme tutarları
    payments["amount_cents"] = payments["amount"].map(
        lambda value: parse_money_to_cents(
            value,
            field_name="Ödemeler / amount",
        )
    )

    print("Para tutarları doğrulandı ve kuruşa dönüştürüldü.")

    # --------------------------------------------------------
    # 2.5. ÖDEMELERİ SİPARİŞ KİMLİĞİNE GÖRE GRUPLAMA
    # --------------------------------------------------------

    # Aynı order_id değerine ait ödemeleri tek satırda özetler.
    # Sonuç sütunları:
    # order_id: Ödemelerin ilişkilendirildiği sipariş kimliği.
    # paid_total_cents: Bu kimliğe ait toplam ödeme tutarı.
    # payment_count: Bu kimliğe ait ödeme işlemi sayısı.
    #
    # Orijinal payments tablosu korunur.
    payment_summary = summarize_payments(payments)

    # --------------------------------------------------------
    # 2.6. GRUPLAMA SONRASINDA TOPLAM TUTARI KONTROL ETME
    # --------------------------------------------------------

    # Gruplama, satır sayısını azaltabilir.
    # Ancak toplam ödeme tutarını değiştirmemelidir.

    # 2.6.1. Gruplama öncesi ve sonrası toplamlar
    original_total = payments["amount_cents"].sum()
    summary_total = payment_summary["paid_total_cents"].sum()

    # 2.6.2. Toplamlar farklıysa işlemi durdur
    if original_total != summary_total:
        raise ValueError(
            "Gruplama sırasında toplam ödeme tutarı değişti. "
            f"Önce: {original_total} kuruş, "
            f"sonra: {summary_total} kuruş."
        )

    print("Gruplama tamamlandı; toplam ödeme tutarı korundu.")

    # --------------------------------------------------------
    # 2.6.3. SİPARİŞLERİ VE ÖDEME ÖZETİNİ BİRLEŞTİRME
    # --------------------------------------------------------

    # Her sipariş kimliğinin sipariş ve ödeme bilgilerini
    # aynı satırda topla. Eşleşmeyen kayıtları da koru.
    report = merge_orders_and_payments(
        orders=orders,
        payment_summary=payment_summary,
    )

    print("Siparişler ve ödeme özeti birleştirildi.")

    # --------------------------------------------------------
    # 2.6.4. MUTABAKAT DURUMLARINI BELİRLEME
    # --------------------------------------------------------

    # Birleştirilmiş tabloya fark ve durum sütunlarını ekle.
    report = classify_reconciliation(report)

    print("Tutar farkları hesaplandı ve ödeme durumları belirlendi.")

    # --------------------------------------------------------
    # 2.6.5. PARASAL ÖZETİ HESAPLAMA
    # --------------------------------------------------------

    summary = build_financial_summary(report)

    # --------------------------------------------------------
    # 2.7. SONUÇLARI EKRANDA İNCELEME
    # --------------------------------------------------------

    # 2.7.1. Sipariş tablosundan örnek kayıtlar
    print(f"\nSİPARİŞLER — İLK {preview_row_count} KAYIT")
    print(orders.head(preview_row_count).to_string(index=False))

    # 2.7.2. Ödeme tablosundan örnek kayıtlar
    print(f"\nÖDEMELER — İLK {preview_row_count} KAYIT")
    print(payments.head(preview_row_count).to_string(index=False))

    # 2.7.3. Gruplandırılmış ödeme tablosundan örnek kayıtlar
    print(f"\nÖDEME ÖZETİ — İLK {preview_row_count} KAYIT")
    print(payment_summary.head(preview_row_count).to_string(index=False))

    # 2.7.4. Tabloların tamamının satır ve sütun sayıları
    print("\nTABLO BOYUTLARI")
    print(
        f"Sipariş tablosu: "
        f"{orders.shape[0]} satır, {orders.shape[1]} sütun"
    )
    print(
        f"Ödeme tablosu: "
        f"{payments.shape[0]} satır, {payments.shape[1]} sütun"
    )
    print(
        f"Ödeme özeti: "
        f"{payment_summary.shape[0]} satır, "
        f"{payment_summary.shape[1]} sütun"
    )

    # 2.7.5. Parçalı ödeme örneği
    # Eğitim verisindeki ORD-0401 siparişine ait özeti seçeriz.
    # Bu seçim yalnızca gösterim içindir; hesaplamaları değiştirmez.
    example_order_id = "ORD-0401"

    example_summary = payment_summary.loc[
        payment_summary["order_id"] == example_order_id
    ]

    print(f"\nPARÇALI ÖDEME ÖRNEĞİ — {example_order_id}")

    if example_summary.empty:
        print("Bu sipariş kimliği için ödeme özeti bulunamadı.")
    else:
        print(example_summary.to_string(index=False))

    # 2.7.6. Kontrolden geçen toplam ödeme tutarları
    print("\nTOPLAM TUTAR KONTROLÜ")
    print(f"Gruplama öncesi: {original_total} kuruş")
    print(f"Gruplama sonrası: {summary_total} kuruş")

    # 2.7.7. Sütun adları ve veri tipleri
    print("\nSİPARİŞ SÜTUNLARI")
    print(orders.columns.tolist())

    print("\nSİPARİŞ VERİ TİPLERİ")
    print(orders.dtypes)

    print("\nÖDEME ÖZETİ VERİ TİPLERİ")
    print(payment_summary.dtypes)

    # --------------------------------------------------------
    # 2.8. BİRLEŞTİRİLMİŞ TABLOYU KONTROL ETME
    # --------------------------------------------------------

    # 2.8.1. Kaynak durumlarına göre kayıt sayıları
    print("\nBİRLEŞTİRME KONTROLÜ")
    print(f"Rapor satır sayısı: {len(report)}")

    source_counts = report["match_source"].value_counts()

    print(f"İki tabloda da bulunan: {source_counts.get('both', 0)}")
    print(f"Yalnızca siparişi bulunan: {source_counts.get('left_only', 0)}")
    print(f"Yalnızca ödemesi bulunan: {source_counts.get('right_only', 0)}")

    # 2.8.2. Üç farklı eşleşme durumundan örnekler
    example_ids = [
        "ORD-0401",
        "ORD-0901",
        "ORD-EXT-001",
    ]

    example_columns = [
        "order_id",
        "order_total_cents",
        "paid_total_cents",
        "payment_count",
        "match_source",
    ]

    example_report = report.loc[
        report["order_id"].isin(example_ids),
        example_columns,
    ]

    print("\nBİRLEŞTİRME ÖRNEKLERİ")
    print(example_report.to_string(index=False))

    # 2.8.3. Para sütunlarının veri tipleri
    print("\nRAPOR PARA SÜTUNLARININ VERİ TİPLERİ")
    print(
        report[
            ["order_total_cents", "paid_total_cents"]
        ].dtypes
    )


    # --------------------------------------------------------
    # 2.9. MUTABAKAT DURUMLARINI İNCELEME
    # --------------------------------------------------------

    # 2.9.1. Durumların ekranda gösterileceği sıra
    status_order = [
        "PAID",
        "UNDERPAID",
        "OVERPAID",
        "UNPAID",
        "UNMATCHED_PAYMENT",
    ]

    # 2.9.2. Her durumdaki kayıt sayısı
    # reindex(), sonuçları istediğimiz sıraya yerleştirir.
    # Bir durum hiç yoksa sayısını sıfır gösterir.
    status_counts = (
        report["status"]
        .value_counts()
        .reindex(status_order, fill_value=0)
    )

    print("\nMUTABAKAT DURUM SAYILARI")
    print(status_counts.to_string())

    print(f"\nToplam sınıflandırılan kayıt: {status_counts.sum()}")

    # 2.9.3. Her durumdan bir örnek
    # Bu kimlikler eğitim veri setimizde farklı durumları temsil eder.
    status_example_ids = [
        "ORD-0401",
        "ORD-0651",
        "ORD-0801",
        "ORD-0901",
        "ORD-EXT-001",
    ]

    status_example_columns = [
        "order_id",
        "order_total_cents",
        "paid_total_cents",
        "difference_cents",
        "status",
    ]

    status_examples = report.loc[
        report["order_id"].isin(status_example_ids),
        status_example_columns,
    ]

    print("\nMUTABAKAT DURUM ÖRNEKLERİ — TUTARLAR KURUŞ")
    print(status_examples.to_string(index=False))


    # --------------------------------------------------------
    # 2.10. PARASAL ÖZETİ EKRANDA GÖSTERME
    # --------------------------------------------------------

    # Ekranda gösterilecek açıklamalar ve sözlük anahtarları.
    summary_fields = [
        ("Toplam sipariş tutarı", "total_order_cents"),
        ("Toplam gelen ödeme", "total_payment_cents"),
        ("Eksik ödeme toplamı", "shortfall_cents"),
        ("Fazla ödeme toplamı", "overpayment_cents"),
        ("Eşleşmeyen ödeme toplamı", "unmatched_payment_cents"),
    ]

    print("\nPARASAL ÖZET")

    for label, key in summary_fields:
        formatted_amount = format_cents_as_try(summary[key])
        print(f"{label}: {formatted_amount}")

    # --------------------------------------------------------
    # 2.11. PARASAL ÖZETİN TUTARLILIĞINI KONTROL ETME
    # --------------------------------------------------------

    # Siparişlerden kalan borcu çıkar.
    # Fazla ödemeleri ve eşleşmeyen ödemeleri ekle.
    # Sonuç, bütün gelen ödemelerin toplamına eşit olmalıdır.
    reconstructed_payment_cents = (
        summary["total_order_cents"]
        - summary["shortfall_cents"]
        + summary["overpayment_cents"]
        + summary["unmatched_payment_cents"]
    )

    if reconstructed_payment_cents != summary["total_payment_cents"]:
        raise ValueError("Parasal özetin tutarları birbiriyle uyuşmuyor.")

    print("\nParasal özet tutarlılık kontrolü geçti.")


    # --------------------------------------------------------
    # 2.12. RAPORLARI CSV VE EXCEL OLARAK KAYDETME
    # --------------------------------------------------------

    # Dosyaları, parasal tutarlılık kontrolü geçtikten sonra yaz.
    saved_files = export_reports(
        report=report,
        summary=summary,
        output_dir=output_dir,
    )

    print("\nKAYDEDİLEN RAPORLAR")
    print(f"CSV dosyası: {saved_files['csv']}")
    print(f"Excel dosyası: {saved_files['excel']}")


    print("\nBu aşamadaki işlemler tamamlandı.")


# ============================================================
# 3. PROGRAMIN BAŞLANGIÇ NOKTASI
# ============================================================

# Dosya doğrudan çalıştırıldığında main() fonksiyonunu çağırır.
# Başka bir dosyadan import edildiğinde main() otomatik çalışmaz.
if __name__ == "__main__":
    main()