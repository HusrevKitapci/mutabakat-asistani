import pandas as pd
import re
import pandas as pd


def validate_table(
        df:pd.DataFrame,
        required_columns: list[str],
        id_column: str,
        table_name: str,
) -> pd.DataFrame:
    # Gerekli Stünlardan Handilerinin eksik Olduğunu Bul
    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{table_name}: Eksik Sütunlar: {missing_columns}"

        )
    # Başlıları Olan ancak hiç Kayıt İçermeyen tabloları reddet
    if df.empty:
        raise ValueError(
            f"{table_name}: Dosyada Veri Satırı Bulunmuyor"

        )
    # Orjinal Dosyayaı Değiştirmemek İçin Bir Kopyasını Oluştur.
    cleaned_df = df.copy()

    # Gerekli alanların başındaki ve sonundaki boşlukları temizle.
    for column in required_columns:
        cleaned_df[column] = cleaned_df[column].str.strip()

        #Hem Eksik değerleri hemde boş değerleri kontrol et.
        empty_mask = (
            cleaned_df[column].isna()
            | cleaned_df[column].eq("")
        )

        if empty_mask.any():
            empty_count = int(empty_mask.sum())

            raise ValueError(
                f"{table_name}: '{column}' sütununda"
                f"{empty_count} boş alan var"
            )
    # Benzersiz olması gereken kimliklerde tekrar olup olmadığını bul
    duplicate_mask = cleaned_df[id_column].duplicated(keep=False)

    if duplicate_mask.any():
        dublicate_ids = (
            cleaned_df.loc[duplicate_mask, id_column]
            .unique()
            .tolist()

        )

        raise ValueError(
            f"{table_name}: Tekrarlanan '{id_column}' değerleri var."
            f"ilk 5 değer {dublicate_ids[:5]}"

        )
    return cleaned_df

def parse_money_to_cents(value: str, field_name: str) -> int:
    # Tam sayı veya en fazla iki ondalık basamak içeren tutarları kabul et.
    pattern = r"[0-9]+(?:\.[0-9]{1,2})?"

    if re.fullmatch(pattern, value)is None:
        raise ValueError(
            f"{field_name}: Geçersiz tutar: {value!r}. "
            "Örnek geçerli biçim: 150.50"
        )

    #tutarı tam lira ve kuruş bölümlerine ayır.
    lira_text, separator, kurus_text = value.partition(".")

    # Ondalık bölüm yoksa veya tek basamaklıysa iki basamağa tamamla.
    kurus_text = kurus_text.ljust(2,"0")

    # Hesaplamayı yanlızca tam sayılar kullanarak yap.
    cents = int(lira_text) * 100 + int(kurus_text)

    if cents <= 0:
        raise ValueError(
            f"{field_name}: Tutar sıfırdan büyük olmalı: {value!r}"
        )
    return cents

def summarize_payments(paymnets: pd.DataFrame) -> pd.DataFrame:
    # Aynı sipariş kimliğine ait ödemeleri bir araya getir.
    payments_summary = paymnets.groupby(
        "order_id",
        as_index=False,
    ).agg(
        paid_total_cents = ("amount_cents", "sum"),
        payment_count=("payment_id", "size"),
    )

    return payments_summary

# ============================================================
# SİPARİŞLERİ VE ÖDEME ÖZETİNİ BİRLEŞTİRME
# ============================================================

def merge_orders_and_payments(
        orders: pd.DataFrame,
        payment_summary: pd.DataFrame,
) -> pd.DataFrame:
    """
       Siparişleri ve ödeme özetini order_id üzerinden birleştirir.
       İki tablodaki eşleşmeyen kayıtları da sonuçta korur.
       """

    # --------------------------------------------------------
    # 1. EKSİK DEĞER DESTEKLEYEN TAM SAYI TİPLERİNİ HAZIRLAMA
    # --------------------------------------------------------

    # Birleştirme sonucunda bazı alanlar boş kalabilir.
    # Büyük "I" ile Int64, tam sayılarla birlikte eksik değerleri
    # de saklayabilir. Böylece para sütunları float'a dönüşmez.
    orders_for_merge = orders.astype(
        {
            "order_total_cents": "Int64",
        }

    )
    payments_for_merge = payment_summary.astype(
        {
            "paid_total_cents": "Int64",
            "payment_count": "Int64",
        }
    )
    # --------------------------------------------------------
    # 2. İKİ TABLOYU SİPARİŞ KİMLİĞİ ÜZERİNDEN BİRLEŞTİRME
    # --------------------------------------------------------

    report = orders_for_merge.merge(
        payments_for_merge,
        on="order_id",
        how="outer",
        validate="one_to_one",
        indicator="match_source",
    )

    # --------------------------------------------------------
    # 3. ÖDEMESİ OLMAYAN SİPARİŞLERİN ÖDEME ALANLARI
    # --------------------------------------------------------

    # Yalnızca sipariş tablosunda bulunan kayıtları seç.
    unpaid_mask = report["match_source"] == "left_only"

    # Bu kayıtlarda gelen ödeme ve ödeme işlemi sayısı sıfırdır.

    report.loc[unpaid_mask, "paid_total_cents"] = 0
    report.loc[unpaid_mask, "payment_count"] = 0

    # Siparişi bulunmayan ödemelerde order_total_cents alanını
    # boş bırakıyoruz. Bilinmeyen sipariş tutarı sıfır değildir.

    return report

# ============================================================
# MUTABAKAT SONUÇLARINI SINIFLANDIRMA
# ============================================================

def classify_reconciliation(report: pd.DataFrame) -> pd.DataFrame:
    """
    Birleştirilmiş tabloya tutar farkını ve ödeme durumunu ekler.
    Siparişi bulunmayan ödemelerin tutar farkını boş bırakır.
    """

    # --------------------------------------------------------
    # 1. ÇALIŞMA TABLOSUNU HAZIRLAMA
    # --------------------------------------------------------

    # Fonksiyona verilen tabloyu doğrudan değiştirmemek için
    # sonuçları bir kopya üzerinde oluştururuz.
    result = report.copy()

    # --------------------------------------------------------
    # 2. ÖDEME İLE SİPARİŞ ARASINDAKİ FARKI HESAPLAMA
    # --------------------------------------------------------

    # Pozitif fark: Fazla ödeme.
    # Negatif fark: Eksik ödeme veya hiç ödeme yapılmaması.
    # Sıfır fark: Tutarlar eşit.
    # Sipariş tutarı eksikse sonuç da eksik kalır.
    result["difference_cents"] = (
        result["paid_total_cents"]
        - result["order_total_cents"]
    )

    # --------------------------------------------------------
    # 3. DURUM SÜTUNUNU HAZIRLAMA
    # --------------------------------------------------------

    # Başlangıçta bütün satırların durumu bilinmiyor.
    # Aşağıdaki kurallarla her satıra bir durum atayacağız.
    result["status"] = pd.Series(
        pd.NA,
        index=result.index,
        dtype="string",
    )

    # --------------------------------------------------------
    # 4. KAYITLARIN KAYNAĞINA GÖRE MASKELER OLUŞTURMA
    # --------------------------------------------------------

    matched_mask = result["match_source"] == "both"
    unpaid_mask = result["match_source"] == "left_only"
    unmatched_mask = result["match_source"] == "right_only"

    # --------------------------------------------------------
    # 5. TEK TARAFTA BULUNAN KAYITLARI SINIFLANDIRMA
    # --------------------------------------------------------

    # Sipariş var, ödeme kaydı yok.
    result.loc[unpaid_mask, "status"] = "UNPAID"

    # Ödeme var, sipariş kaydı yok.
    result.loc[unmatched_mask, "status"] = "UNMATCHED_PAYMENT"

    # --------------------------------------------------------
    # 6. EŞLEŞEN KAYITLARI TUTAR FARKINA GÖRE SINIFLANDIRMA
    # --------------------------------------------------------

    # 6.1. Tam ödenmiş
    result.loc[
        matched_mask & (result["difference_cents"] == 0),
        "status",
    ] = "PAID"

    # 6.2. Eksik ödenmiş
    result.loc[
        matched_mask & (result["difference_cents"] < 0),
        "status",
    ] = "UNDERPAID"

    # 6.3. Fazla ödenmiş
    result.loc[
        matched_mask & (result["difference_cents"] > 0),
        "status",
    ] = "OVERPAID"

    # --------------------------------------------------------
    # 7. SINIFLANDIRILMAMIŞ KAYIT KALDI MI?
    # --------------------------------------------------------

    if result["status"].isna().any():
        raise ValueError(
            "Bazı kayıtların ödeme durumu belirlenemedi. "
            "Birleştirme sonucunu ve tutar sütunlarını kontrol edin."
        )

    return result


# ============================================================
# MUTABAKAT RAPORUNUN PARASAL ÖZETİNİ HESAPLAMA
# ============================================================

def build_financial_summary(report: pd.DataFrame) -> dict[str, int]:
    """
    Sınıflandırılmış rapordan parasal özet üretir.
    Döndürülen bütün tutarlar tam sayı kuruştur.
    """

    # --------------------------------------------------------
    # 1. HESAPLAMADA KULLANILACAK KAYITLARI SEÇME
    # --------------------------------------------------------

    # Sipariş kaydı bulunan satırlar.
    order_mask = report["match_source"].isin(
        ["both", "left_only"]
    )

    # Eksik ödeme veya hiç ödeme yapılmamış siparişler.
    shortfall_mask = report["status"].isin(
        ["UNDERPAID", "UNPAID"]
    )

    # Sipariş tutarından fazla ödeme yapılmış kayıtlar.
    overpaid_mask = report["status"] == "OVERPAID"

    # Sipariş kaydı bulunmayan ödemeler.
    unmatched_mask = report["status"] == "UNMATCHED_PAYMENT"

    # --------------------------------------------------------
    # 2. TOPLAM TUTARLARI HESAPLAMA
    # --------------------------------------------------------

    # Yalnızca sipariş kaydı bulunan satırlardan hesaplanır.
    total_order_cents = int(
        report.loc[order_mask, "order_total_cents"].sum()
    )

    # Rapordaki bütün ödemeler hesaba katılır.
    total_payment_cents = int(
        report["paid_total_cents"].sum()
    )

    # Eksik tutarların farkı negatiftir.
    # Başına eksi koyarak kalan borcu pozitif tutar olarak gösteririz.
    shortfall_cents = -int(
        report.loc[shortfall_mask, "difference_cents"].sum()
    )

    # Fazla ödemelerde fark zaten pozitiftir.
    overpayment_cents = int(
        report.loc[overpaid_mask, "difference_cents"].sum()
    )

    # Eşleşmeyen ödemelerde fark bilinmez.
    # Bu nedenle difference_cents yerine ödeme tutarını toplarız.
    unmatched_payment_cents = int(
        report.loc[unmatched_mask, "paid_total_cents"].sum()
    )

    # --------------------------------------------------------
    # 3. SONUÇLARI SÖZLÜK OLARAK DÖNDÜRME
    # --------------------------------------------------------

    return {
        "total_order_cents": total_order_cents,
        "total_payment_cents": total_payment_cents,
        "shortfall_cents": shortfall_cents,
        "overpayment_cents": overpayment_cents,
        "unmatched_payment_cents": unmatched_payment_cents,
    }





