# ============================================================
# 1. KÜTÜPHANELER VE TEST EDİLECEK FONKSİYONLAR
# ============================================================

import pandas as pd

from reconciliation import (
    summarize_payments,
    merge_orders_and_payments,
    classify_reconciliation,
    build_financial_summary,
)


# ============================================================
# 2. MUTABAKAT HESAPLAMA AKIŞININ TESTİ
# ============================================================

def test_reconciliation_flow() -> None:
    """Beş ödeme durumunu ve parasal özeti birlikte kontrol eder."""

    # --------------------------------------------------------
    # 2.1. ÖRNEK SİPARİŞLERİ HAZIRLAMA
    # --------------------------------------------------------

    # Bütün tutarlar kuruştur.
    orders = pd.DataFrame(
        {
            "order_id": [
                "ORD-001",
                "ORD-002",
                "ORD-003",
                "ORD-004",
            ],
            "order_total_cents": [
                100000,
                75000,
                50000,
                120000,
            ],
        }
    )

    # --------------------------------------------------------
    # 2.2. ÖRNEK ÖDEMELERİ HAZIRLAMA
    # --------------------------------------------------------

    # ORD-001 için iki ayrı ödeme var.
    # ORD-003 için ödeme yok.
    # ORD-999 için sipariş kaydı yok.
    payments = pd.DataFrame(
        {
            "payment_id": [
                "PAY-001",
                "PAY-002",
                "PAY-003",
                "PAY-004",
                "PAY-005",
            ],
            "order_id": [
                "ORD-001",
                "ORD-001",
                "ORD-002",
                "ORD-004",
                "ORD-999",
            ],
            "amount_cents": [
                60000,
                40000,
                70000,
                125000,
                20000,
            ],
        }
    )

    # --------------------------------------------------------
    # 2.3. GERÇEK HESAPLAMA FONKSİYONLARINI ÇALIŞTIRMA
    # --------------------------------------------------------

    payment_summary = summarize_payments(payments)

    report = merge_orders_and_payments(
        orders=orders,
        payment_summary=payment_summary,
    )

    report = classify_reconciliation(report)
    summary = build_financial_summary(report)

    # --------------------------------------------------------
    # 2.4. KAYIT SAYISINI VE BENZERSİZLİĞİ KONTROL ETME
    # --------------------------------------------------------

    # Dört sipariş ve bir eşleşmeyen ödeme kimliği olmalı.
    assert len(report) == 5
    assert report["order_id"].is_unique

    # Kimliği kullanarak satırlara kolayca erişmek için
    # ayrı bir tabloda order_id sütununu indeks yapıyoruz.
    indexed_report = report.set_index("order_id")

    # --------------------------------------------------------
    # 2.5. BÜTÜN ÖDEME DURUMLARINI KONTROL ETME
    # --------------------------------------------------------

    expected_statuses = {
        "ORD-001": "PAID",
        "ORD-002": "UNDERPAID",
        "ORD-003": "UNPAID",
        "ORD-004": "OVERPAID",
        "ORD-999": "UNMATCHED_PAYMENT",
    }

    actual_statuses = indexed_report["status"].to_dict()

    assert actual_statuses == expected_statuses

    # --------------------------------------------------------
    # 2.6. PARÇALI ÖDEMENİN DOĞRU TOPLANDIĞINI KONTROL ETME
    # --------------------------------------------------------

    assert indexed_report.loc["ORD-001", "paid_total_cents"] == 100000
    assert indexed_report.loc["ORD-001", "payment_count"] == 2

    # --------------------------------------------------------
    # 2.7. FARKLARI VE EKSİK BİLGİLERİ KONTROL ETME
    # --------------------------------------------------------

    assert indexed_report.loc["ORD-001", "difference_cents"] == 0
    assert indexed_report.loc["ORD-002", "difference_cents"] == -5000
    assert indexed_report.loc["ORD-003", "difference_cents"] == -50000
    assert indexed_report.loc["ORD-004", "difference_cents"] == 5000

    assert indexed_report.loc["ORD-003", "paid_total_cents"] == 0
    assert indexed_report.loc["ORD-003", "payment_count"] == 0

    assert pd.isna(
        indexed_report.loc["ORD-999", "order_total_cents"]
    )

    assert pd.isna(
        indexed_report.loc["ORD-999", "difference_cents"]
    )

    # --------------------------------------------------------
    # 2.8. PARASAL ÖZETİ KONTROL ETME
    # --------------------------------------------------------

    expected_summary = {
        "total_order_cents": 345000,
        "total_payment_cents": 315000,
        "shortfall_cents": 55000,
        "overpayment_cents": 5000,
        "unmatched_payment_cents": 20000,
    }

    assert summary == expected_summary