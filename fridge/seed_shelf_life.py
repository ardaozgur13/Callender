"""
Açıldıktan sonra önerilen tüketim süreleri: başlangıç tohum verisi.
Kaynak: docs/callender.md bölüm 8 (USDA FoodKeeper ve üniversite kaynakları).
`usda` = kaynakta doğrulandı, `estimate` = muhafazakâr tahmin, ürün etiketi kontrol edilmeli.
Bu değerleri belge dışında değiştirme ya da uydurma; yeni ürün ancak kaynağıyla eklenir.
"""

SHELF_LIFE_RULES = [
    # (key, name_tr, category, storage, opened_days, source, note)
    ("sut-pastorize", "Süt (pastörize, laktozlu)", "Süt ürünleri", "fridge", 5, "usda",
     "USDA ~1 hafta; güvenli tarafta 5 gün seçildi. Kapı rafında tutma."),
    ("sut-laktozsuz", "Süt (laktozsuz)", "Süt ürünleri", "fridge", 3, "estimate",
     "Üretici talimatına bak."),
    ("uht-sut-acilmis", "UHT süt (açılmış)", "Süt ürünleri", "fridge", 4, "estimate",
     "Açılmamış UHT oda sıcaklığında durur."),
    ("yogurt", "Yoğurt", "Süt ürünleri", "fridge", 7, "usda",
     "USDA 7–14 gün (satın almadan itibaren); açıldıktan sonra 7 gün güvenli."),
    ("kefir", "Kefir", "Süt ürünleri", "fridge", 2, "usda",
     "USDA açıldıktan sonra 1–2 gün."),
    ("krem-peynir-labne", "Krem peynir / labne", "Süt ürünleri", "fridge", 14, "usda", ""),
    ("lor-suzme-peynir", "Lor / süzme peynir", "Süt ürünleri", "fridge", 7, "usda", ""),
    ("sert-peynir", "Sert peynir (kaşar, çedar)", "Süt ürünleri", "fridge", 21, "usda",
     "USDA 3–4 hafta."),
    ("beyaz-peynir", "Beyaz peynir (salamurada)", "Süt ürünleri", "fridge", 7, "estimate",
     "Salamurası içinde sakla; salamura değişimi önemli."),
    ("taze-yumusak-peynir", "Taze/yumuşak peynir", "Süt ürünleri", "fridge", 7, "usda",
     "USDA ~1 hafta."),
    ("tereyagi", "Tereyağı", "Süt ürünleri", "fridge", 30, "estimate",
     "Oda sıcaklığında 1–2 gün (usda)."),
    ("yumurta", "Yumurta (kırılmamış)", "Yumurta", "fridge", 21, "usda",
     "USDA 3–5 hafta."),
    ("haslanmis-yumurta", "Haşlanmış yumurta", "Yumurta", "fridge", 7, "usda", ""),
    ("pismis-yemek", "Pişmiş et / yemek", "Et ve yemek", "fridge", 3, "usda",
     "USDA 3–4 gün."),
    ("sarkuteri", "Şarküteri / dilimli et ürünleri (açılmış)", "Et ve yemek", "fridge", 4, "usda",
     "USDA 3–5 gün."),
    ("konserve-salca", "Açılmış konserve / salça (cam kavanoz)", "Konserve", "fridge", 7, "estimate",
     "Metal kutudan çıkarıp kapaklı kaba aktar."),
    ("recel-bal", "Reçel / bal", "Kahvaltılık", "room", 90, "estimate",
     "Reçel açıldıktan sonra dolapta tercih edilir."),
]


def load_rules(ShelfLifeRule):
    """Kuralları ekler ya da günceller (key'e göre). Migration'dan ve testlerden çağrılır."""
    for key, name_tr, category, storage, opened_days, source, note in SHELF_LIFE_RULES:
        ShelfLifeRule.objects.update_or_create(
            key=key,
            defaults={
                "name_tr": name_tr, "category": category, "storage": storage,
                "opened_days": opened_days, "source": source, "note": note,
            },
        )
