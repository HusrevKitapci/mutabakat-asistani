# ============================================================
# 1. KÜTÜPHANELER VE TEST EDİLECEK FONKSİYON
# ============================================================

import pytest

from reconciliation import parse_money_to_cents


# ============================================================
# 2. GEÇERLİ TUTARLARIN DÖNÜŞÜMÜ
# ============================================================

# Her ikili:
# (Fonksiyona verilecek metin, beklenen kuruş değeri)
@pytest.mark.parametrize(
    "value, expected_cents",
    [
        ("1000.00", 100000),
        ("179.19", 17919),
        ("25.5", 2550),
        ("12", 1200),
        ("0.01", 1),
        ("1.05", 105),
        ("0012.50", 1250),
    ],
)
def test_valid_money_values(value: str, expected_cents: int) -> None:
    # 2.1. Gerçek fonksiyonu çalıştır
    result = parse_money_to_cents(
        value,
        field_name="Test tutarı",
    )

    # 2.2. Sonucun beklediğimiz değer olduğunu doğrula
    assert result == expected_cents

    # 2.3. Sonucun tam sayı olduğunu doğrula
    assert isinstance(result, int)


# ============================================================
# 3. GEÇERSİZ TUTARLARIN REDDEDİLMESİ
# ============================================================

@pytest.mark.parametrize(
    "value",
    [
        "",
        "abc",
        "150,50",
        "12.345",
        "-50.00",
        "0.00",
        "1e3",
    ],
)
def test_invalid_money_values(value: str) -> None:
    # Fonksiyonun bu girdilerde ValueError vermesini bekliyoruz.
    with pytest.raises(ValueError):
        parse_money_to_cents(
            value,
            field_name="Test tutarı",
        )