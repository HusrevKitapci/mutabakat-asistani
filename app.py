# ============================================================
# 1. KÜTÜPHANELER VE PROJE FONKSİYONLARI
# ============================================================
import pandas as pd
import streamlit as st

from reconciliation import (
    validate_table,
    parse_money_to_cents,
    summarize_payments,
    merge_orders_and_payments,
    classify_reconciliation,
    build_financial_summary,
)

from formatting import format_cents_as_try
from export import build_excel_download





# ============================================================
# 2. UYGULAMA ARAYÜZÜ
# ============================================================

def main() -> None:
    """CSV dosyalarını yükler, temel kontrolleri yapar ve gösterir."""

    # --------------------------------------------------------
    # 2.1. SAYFA AYARLARI VE BAŞLIK
    # --------------------------------------------------------

    st.set_page_config(
        page_title="Mutabakat Asistanı",
        layout="wide",
    )

    st.title("Mutabakat Asistanı")

    st.write(
        "Sipariş ve ödeme dosyalarını yükleyerek "
        "kayıtların yapısını kontrol edin."
    )

    st.caption(
        "Dosya biçimi: UTF-8 CSV. "
        "Sütun ayırıcı: virgül. Ondalık ayırıcı: nokta."
    )

    # --------------------------------------------------------
    # 2.2. DOSYA YÜKLEME ALANLARI
    # --------------------------------------------------------

    orders_column, payments_column = st.columns(2)

    # 2.2.1. Sipariş dosyası
    with orders_column:
        orders_file = st.file_uploader(
            "Sipariş dosyası — orders.csv",
            type=["csv"],
            key="orders_upload",
        )

    # 2.2.2. Ödeme dosyası
    with payments_column:
        payments_file = st.file_uploader(
            "Ödeme dosyası — payments.csv",
            type=["csv"],
            key="payments_upload",
        )

    # --------------------------------------------------------
    # 2.3. İKİ DOSYANIN DA YÜKLENMESİNİ BEKLEME
    # --------------------------------------------------------

    if orders_file is None or payments_file is None:
        st.info("Devam etmek için iki CSV dosyasını da yükleyin.")
        st.stop()

    # --------------------------------------------------------
    # 2.4. DOSYALARI OKUMA VE TEMEL DOĞRULAMA
    # --------------------------------------------------------

    try:
        # 2.4.1. Dosyaları metin sütunları olarak oku
        orders = pd.read_csv(
            orders_file,
            dtype="string",
            keep_default_na=False,
            encoding="utf-8-sig",
        )

        payments = pd.read_csv(
            payments_file,
            dtype="string",
            keep_default_na=False,
            encoding="utf-8-sig",
        )

        # 2.4.2. Sipariş tablosunu doğrula
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

        # 2.4.3. Ödeme tablosunu doğrula
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

    except (
        UnicodeDecodeError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        ValueError,
    ) as error:
        # Beklenen dosya okuma ve veri doğrulama hatalarını göster.
        st.error(f"Dosyalar işlenemedi: {error}")
        st.stop()

    st.success(
        "Dosyalar okundu. Sütun, zorunlu alan ve "
        "benzersiz kimlik kontrolleri geçti."
    )

    # --------------------------------------------------------
    # 2.5. KAYIT SAYILARINI GÖSTERME
    # --------------------------------------------------------

    orders_metric, payments_metric = st.columns(2)

    orders_metric.metric(
        label="Sipariş kaydı",
        value=len(orders),
    )

    payments_metric.metric(
        label="Ödeme kaydı",
        value=len(payments),
    )

    # --------------------------------------------------------
    # 2.6. TABLOLARI SEKME İÇİNDE GÖSTERME
    # --------------------------------------------------------

    orders_tab, payments_tab = st.tabs(
        ["Siparişler", "Ödemeler"]
    )

    with orders_tab:
        st.caption("Sipariş tablosunun ilk 20 kaydı.")
        st.dataframe(
            orders.head(20),
            hide_index=True,
        )

    with payments_tab:
        st.caption("Ödeme tablosunun ilk 20 kaydı.")
        st.dataframe(
            payments.head(20),
            hide_index=True,
        )

    # --------------------------------------------------------
    # 2.7. MUTABAKAT HESAPLAMASINI ÇALIŞTIRMA
    # --------------------------------------------------------
    # --------------------------------------------------------
    # 2.7. MUTABAKAT HESAPLAMASINI ÇALIŞTIRMA
    # --------------------------------------------------------

    try:
        # 2.7.1. Sipariş tutarlarını kuruşa dönüştür
        orders["order_total_cents"] = orders["order_total"].map(
            lambda value: parse_money_to_cents(
                value,
                field_name="Siparişler / order_total",
            )
        )

        # 2.7.2. Ödeme tutarlarını kuruşa dönüştür
        payments["amount_cents"] = payments["amount"].map(
            lambda value: parse_money_to_cents(
                value,
                field_name="Ödemeler / amount",
            )
        )

        # 2.7.3. Aynı siparişe ait ödemeleri birleştir
        payment_summary = summarize_payments(payments)

        # Gruplama sırasında toplam tutarın korunduğunu doğrula.
        original_total = int(payments["amount_cents"].sum())
        grouped_total = int(payment_summary["paid_total_cents"].sum())

        if original_total != grouped_total:
            raise ValueError(
                "Gruplama sırasında toplam ödeme tutarı değişti."
            )

        # 2.7.4. Siparişler ile ödeme özetini eşleştir
        report = merge_orders_and_payments(
            orders=orders,
            payment_summary=payment_summary,
        )

        # 2.7.5. Ödeme durumlarını belirle
        report = classify_reconciliation(report)

        # 2.7.6. Parasal özeti hesapla
        summary = build_financial_summary(report)

        # 2.7.7. Parasal özetin tutarlılığını kontrol et
        reconstructed_payment_cents = (
            summary["total_order_cents"]
            - summary["shortfall_cents"]
            + summary["overpayment_cents"]
            + summary["unmatched_payment_cents"]
        )

        if reconstructed_payment_cents != summary["total_payment_cents"]:
            raise ValueError(
                "Parasal özetin tutarları birbiriyle uyuşmuyor."
            )

    except ValueError as error:
        st.error(f"Mutabakat hesaplanamadı: {error}")
        st.stop()

    st.success("Mutabakat hesaplandı; tutarlılık kontrolleri geçti.")

    # --------------------------------------------------------
    # 2.8. PARASAL ÖZETİ GÖSTERME
    # --------------------------------------------------------

    st.subheader("Parasal özet")

    # 2.8.1. Genel toplamlar
    order_total_column, payment_total_column = st.columns(2)

    order_total_column.metric(
        label="Toplam sipariş tutarı",
        value=format_cents_as_try(summary["total_order_cents"]),
    )

    payment_total_column.metric(
        label="Toplam gelen ödeme",
        value=format_cents_as_try(summary["total_payment_cents"]),
    )

    # 2.8.2. İncelenmesi gereken tutarlar
    shortfall_column, overpayment_column, unmatched_column = st.columns(3)

    shortfall_column.metric(
        label="Eksik ödeme toplamı",
        value=format_cents_as_try(summary["shortfall_cents"]),
    )

    overpayment_column.metric(
        label="Fazla ödeme toplamı",
        value=format_cents_as_try(summary["overpayment_cents"]),
    )

    unmatched_column.metric(
        label="Eşleşmeyen ödeme toplamı",
        value=format_cents_as_try(summary["unmatched_payment_cents"]),
    )

    st.caption(
        "Eksik ödeme toplamı, hiç ödenmemiş siparişleri de içerir. "
        "Eşleşmeyen ödemeler ayrı gösterilir."
    )

    # --------------------------------------------------------
    # 2.9. MUTABAKAT SONUÇLARINI FİLTRELEME
    # --------------------------------------------------------

    st.subheader("Mutabakat sonuçları")

    # 2.9.1. Programdaki durum kodlarının kullanıcıya gösterilen adları
    status_labels = {
        "ALL": "Tüm kayıtlar",
        "PAID": "Tam ödenmiş",
        "UNDERPAID": "Eksik ödenmiş",
        "OVERPAID": "Fazla ödenmiş",
        "UNPAID": "Ödenmemiş",
        "UNMATCHED_PAYMENT": "Eşleşmeyen ödeme",
    }

    # 2.9.2. Kullanıcının incelemek istediği durumu seçmesi
    selected_status = st.selectbox(
        "Gösterilecek ödeme durumu",
        options=list(status_labels.keys()),
        format_func=lambda code: status_labels[code],
        key="status_filter",
    )

    # 2.9.3. Seçime göre gösterilecek kayıtları belirle
    if selected_status == "ALL":
        filtered_report = report.copy()
    else:
        filtered_report = report.loc[
            report["status"] == selected_status
        ].copy()

    # --------------------------------------------------------
    # 2.10. FİLTRELENMİŞ SONUÇ TABLOSUNU GÖSTERME
    # --------------------------------------------------------

    # 2.10.1. Görünen durum adlarını Türkçeye çevir
    # Asıl rapordaki durum kodlarını değiştirmiyoruz.
    filtered_report["status_label"] = (
        filtered_report["status"].map(status_labels)
    )

    # 2.10.2. Gösterilecek sütunlar ve başlıkları
    display_columns = {
        "order_id": "Sipariş kimliği",
        "customer": "Müşteri",
        "order_total_cents": "Sipariş tutarı (kuruş)",
        "paid_total_cents": "Ödenen tutar (kuruş)",
        "difference_cents": "Fark (kuruş)",
        "payment_count": "Ödeme sayısı",
        "status_label": "Durum",
    }

    display_table = filtered_report[
        list(display_columns.keys())
    ].rename(columns=display_columns)

    st.write(
        f"Toplam {len(report)} kaydın "
        f"{len(filtered_report)} tanesi gösteriliyor."
    )

    st.caption(
        "Tablodaki tutarlar kuruştur. "
        "Fark = ödenen tutar − sipariş tutarı. "
        "Sipariş kaydı bulunmayan ödemelerde "
        "sipariş tutarı ve fark bilgisi eksiktir."
    )

    st.dataframe(
        display_table,
        hide_index=True,
    )

    # --------------------------------------------------------
    # 2.11. RAPORLARI TARAYICIDAN İNDİRME
    # --------------------------------------------------------

    st.subheader("Raporları indir")

    st.caption(
        "CSV dosyalarındaki tutarlar kuruştur. "
        "Tüm rapor bütün kayıtları, filtrelenmiş rapor "
        "ise yukarıda seçtiğiniz durumdaki kayıtları içerir."
    )

    # 2.11.1. İndirilecek dosyaların sütunlarını belirle
    download_columns = [
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

    # 2.11.2. Tam raporu ve filtrelenmiş raporu hazırla
    full_download_table = report.loc[:, download_columns]

    filtered_download_table = filtered_report.loc[
        :,
        download_columns,
    ]

    # 2.11.3. Tabloları CSV metnine, ardından baytlara dönüştür
    full_csv_bytes = full_download_table.to_csv(
        index=False,
        na_rep="",
    ).encode("utf-8-sig")

    filtered_csv_bytes = filtered_download_table.to_csv(
        index=False,
        na_rep="",
    ).encode("utf-8-sig")

    # 2.11.4. İndirme düğmelerini yan yana yerleştir
    full_download_column, filtered_download_column = st.columns(2)

    # 2.11.5. Bütün kayıtları indir
    with full_download_column:
        st.download_button(
            label=f"Tüm raporu indir — {len(full_download_table)} kayıt",
            data=full_csv_bytes,
            file_name="mutabakat_tum_kayitlar.csv",
            mime="text/csv",
            key="download_full_csv",
            on_click="ignore",
        )

    # 2.11.6. Seçili filtredeki kayıtları indir
    with filtered_download_column:
        st.download_button(
            label=(
                "Filtrelenmiş raporu indir — "
                f"{len(filtered_download_table)} kayıt"
            ),
            data=filtered_csv_bytes,
            file_name=f"mutabakat_{selected_status.lower()}.csv",
            mime="text/csv",
            key="download_filtered_csv",
            on_click="ignore",
        )

    # --------------------------------------------------------
    # 2.12. TAM EXCEL RAPORUNU İNDİRME
    # --------------------------------------------------------

    # Ekrandaki filtreden bağımsız olarak bütün raporu kullan.
    excel_bytes = build_excel_download(
        report=report,
        summary=summary,
    )

    st.caption(
        "Excel raporu bütün kayıtları, incelenecek kayıtları "
        "ve parasal özeti ayrı sayfalarda içerir. "
        "Yukarıdaki durum filtresi Excel raporunu etkilemez."
    )

    st.download_button(
        label="Üç sayfalı Excel raporunu indir",
        data=excel_bytes,
        file_name="mutabakat_raporu.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        key="download_excel",
        on_click="ignore",
    )


# ============================================================
# 3. PROGRAMIN BAŞLANGIÇ NOKTASI
# ============================================================

if __name__ == "__main__":
    main()