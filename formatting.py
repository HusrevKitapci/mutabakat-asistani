# ============================================================
# PARA TUTARLARINI EKRANDA GÖSTERME
# ============================================================

def format_cents_as_try(cents: int) -> str:
    """
    Tam sayı kuruş değerini Türkçe TL metnine dönüştürür.
    Örnek: 123456 -> "1.234,56 TL"
    """

    # --------------------------------------------------------
    # 1. İŞARETİ BELİRLEME
    # --------------------------------------------------------

    sign = "-" if cents < 0 else ""

    # --------------------------------------------------------
    # 2. TAM LİRA VE KURUŞU AYIRMA
    # --------------------------------------------------------

    lira, kurus = divmod(abs(cents), 100)

    # --------------------------------------------------------
    # 3. TÜRKÇE SAYI BİÇİMİNİ OLUŞTURMA
    # --------------------------------------------------------

    # Binlik grupları noktayla ayır.
    lira_text = f"{lira:,}".replace(",", ".")

    # Kuruş bölümünü her zaman iki basamakla göster.
    return f"{sign}{lira_text},{kurus:02d} TL"