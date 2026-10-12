---
description: Mevcut aşamayı gözden geçirir (kurallara uyum, güvenlik, limitler)
---

Son yapılan değişiklikleri (`git diff` ve yeni dosyalar) `docs/callender.md` ve `CLAUDE.md` kurallarına göre gözden geçir. Kontrol et:

- Yetki: kullanıcı başkasının veya üyesi olmadığı ailenin verisine erişebiliyor mu?
- Limitler (günlük 20, 2 aile, karakter sınırları) sunucu tarafında zorlanıyor mu, sabitler `core/limits.py`'de mi?
- Gizli bilgi, sabit renk kodu, gereksiz bağımlılık, Türkçe/İngilizce adlandırma kuralı ihlali var mı?
- CSRF, girdi doğrulama, açık bırakılmış debug ayarı var mı?
- `python manage.py check` ve testleri çalıştır.

Bulguları önem sırasına göre kısa listele. Hiçbir şeyi otomatik düzeltme; önce ne bulduğunu söyle, onayımla düzelt.
