# ============================================================
# 1. KÜTÜPHANELER VE YARDIMCI FONKSİYONLAR
# ============================================================

from io import BytesIO
from pathlib import Path

import pandas as pd

from formatting import format_cents_as_try


# ============================================================
# 2. MUTABAKAT RAPORUNU DOSYALARA KAYDETME
# ============================================================

def export_reports(
    report: pd.DataFrame,
    summary: dict[str, int],
    output_dir: Path,
) -> dict[str, Path]:
    """
    Mutabakat sonuçlarını CSV ve Excel olarak kaydeder.
    Oluşturulan dosyaların yollarını sözlük olarak döndürür.
    Aynı isimli dosyalar varsa üzerlerine yazar.
    """

    # --------------------------------------------------------
    # 2.1. ÇIKTI KLASÖRÜNÜ HAZIRLAMA
    # --------------------------------------------------------

    # Gerekirse üst klasörlerle birlikte çıktı klasörünü oluştur.
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "mutabakat_raporu.csv"
    excel_path = output_dir / "mutabakat_raporu.xlsx"

    # --------------------------------------------------------
    # 2.2. RAPOR SÜTUNLARINI SEÇME VE SIRALAMA
    # --------------------------------------------------------

    # Dosyada hangi sütunların, hangi sırayla bulunacağını belirle.
    # Para sütunlarının isimleri birimin kuruş olduğunu belirtir.
    export_columns = [
        "order_id",
        "order_date",
        "customer",
        "order_total_cents",
        "paid_total_cents",
        "difference_cents",
        "payment_count",
        "status",
        "match_source",
    ]

    export_table = report.loc[:, export_columns].copy()

    # --------------------------------------------------------
    # 2.3. İNCELENMESİ GEREKEN KAYITLARI SEÇME
    # --------------------------------------------------------

    # Tam ödenmiş kayıtların dışındaki bütün durumları seç.
    review_table = export_table.loc[
        export_table["status"] != "PAID"
    ].copy()

    # --------------------------------------------------------
    # 2.4. PARASAL ÖZET TABLOSUNU OLUŞTURMA
    # --------------------------------------------------------

    summary_fields = [
        ("Toplam sipariş tutarı", "total_order_cents"),
        ("Toplam gelen ödeme", "total_payment_cents"),
        ("Eksik ödeme toplamı", "shortfall_cents"),
        ("Fazla ödeme toplamı", "overpayment_cents"),
        ("Eşleşmeyen ödeme toplamı", "unmatched_payment_cents"),
    ]

    summary_rows = []

    for label, key in summary_fields:
        amount_cents = summary[key]

        summary_rows.append(
            {
                "gosterge": label,
                "tutar_kurus": amount_cents,
                "tutar_tl_gosterim": format_cents_as_try(amount_cents),
            }
        )

    summary_table = pd.DataFrame(summary_rows)

    # --------------------------------------------------------
    # 2.5. BÜTÜN KAYITLARI CSV DOSYASINA YAZMA
    # --------------------------------------------------------

    export_table.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig",
        na_rep="",
    )

    # --------------------------------------------------------
    # 2.6. ÜÇ SAYFALI EXCEL DOSYASINI OLUŞTURMA
    # --------------------------------------------------------

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        # 2.6.1. Bütün mutabakat kayıtları
        export_table.to_excel(
            writer,
            sheet_name="Tum_Kayitlar",
            index=False,
            na_rep="",
        )

        # 2.6.2. İncelenmesi gereken kayıtlar
        review_table.to_excel(
            writer,
            sheet_name="Incelenecek_Kayitlar",
            index=False,
            na_rep="",
        )

        # 2.6.3. Parasal özet
        summary_table.to_excel(
            writer,
            sheet_name="Parasal_Ozet",
            index=False,
        )

    # --------------------------------------------------------
    # 2.7. OLUŞTURULAN DOSYALARIN YOLLARINI DÖNDÜRME
    # --------------------------------------------------------

    return {
        "csv": csv_path,
        "excel": excel_path,
    }

# ============================================================
# 3. TARAYICIDAN İNDİRME İÇİN EXCEL İÇERİĞİ OLUŞTURMA
# ============================================================

def build_excel_download(
    report: pd.DataFrame,
    summary: dict[str, int],
) -> bytes:
    """
    Üç sayfalı Excel raporunu bellekte oluşturur.
    İndirme düğmesine verilecek dosya baytlarını döndürür.
    """

    # --------------------------------------------------------
    # 3.1. RAPOR TABLOLARINI HAZIRLAMA
    # --------------------------------------------------------

    export_columns = [
        "order_id",
        "order_date",
        "customer",
        "order_total_cents",
        "paid_total_cents",
        "difference_cents",
        "payment_count",
        "status",
        "match_source",
    ]

    full_table = report.loc[:, export_columns].copy()

    review_table = full_table.loc[
        full_table["status"] != "PAID"
    ].copy()

    # --------------------------------------------------------
    # 3.2. PARASAL ÖZET TABLOSUNU HAZIRLAMA
    # --------------------------------------------------------

    summary_fields = [
        ("Toplam sipariş tutarı", "total_order_cents"),
        ("Toplam gelen ödeme", "total_payment_cents"),
        ("Eksik ödeme toplamı", "shortfall_cents"),
        ("Fazla ödeme toplamı", "overpayment_cents"),
        ("Eşleşmeyen ödeme toplamı", "unmatched_payment_cents"),
    ]

    summary_rows = []

    for label, key in summary_fields:
        amount_cents = summary[key]

        summary_rows.append(
            {
                "gosterge": label,
                "tutar_kurus": amount_cents,
                "tutar_tl_gosterim": format_cents_as_try(amount_cents),
            }
        )

    summary_table = pd.DataFrame(summary_rows)

    # --------------------------------------------------------
    # 3.3. EXCEL DOSYASINI BELLEKTE OLUŞTURMA
    # --------------------------------------------------------

    with BytesIO() as buffer:
        # Dosya yolu yerine bellekteki buffer nesnesine yazıyoruz.
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            full_table.to_excel(
                writer,
                sheet_name="Tum_Kayitlar",
                index=False,
                na_rep="",
            )

            review_table.to_excel(
                writer,
                sheet_name="Incelenecek_Kayitlar",
                index=False,
                na_rep="",
            )

            summary_table.to_excel(
                writer,
                sheet_name="Parasal_Ozet",
                index=False,
            )

        # ExcelWriter kapandıktan ve dosya içeriği tamamlandıktan
        # sonra bellekteki dosyanın bütün baytlarını alıyoruz.
        excel_bytes = buffer.getvalue()

    return excel_bytes