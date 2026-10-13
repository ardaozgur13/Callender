---
name: callender-security-audit
description: Callender (Django + Supabase + Vercel) projesinin güvenlik denetimi. Kullanıcı "güvenlik", "açık var mı", "denetle", "audit", "/guvenlik" dediğinde ya da bir aşama bittiğinde kullan. Yetki/IDOR, XSS, CSRF, Supabase Data API ve RLS, gizli bilgi, üretim ayarları, rate limit ve limit kurallarını kontrol eder. Denetler ve raporlar; kullanıcı onaylamadan düzeltme yapmaz.
---

# Callender güvenlik denetimi

Bu skill sadece **denetler ve raporlar**. Dosyaları kendiliğinden değiştirme, canlı veritabanına bağlanma, `migrate` çalıştırma. Bulguları sunduktan sonra hangilerini düzelteceğini kullanıcıya sor.

Gereksinimlerin tamamı `docs/callender.md` bölüm 12'dedir. Denetim o bölüme göre yapılır.

## Adımlar

1. **Otomatik tarama:** `bash .claude/skills/callender-security-audit/scripts/scan.sh` çalıştır. Çıktı kalıp eşleşmesidir; her bulguyu ilgili dosyayı açıp doğrula (yanlış alarm olabilir, ör. giriş/kayıt view'larının `login_required`sız olması normaldir). Temiz çıkması güvenli demek değildir.
2. **Elle denetim:** Aşağıdaki kontrol listesini, projede o ana kadar yazılmış kod için sırayla yürüt. Henüz yazılmamış bir özelliği "açık" diye raporlama; "henüz yok" olarak ayır.
3. **Supabase:** `scripts/supabase_check.sql` dosyasını kullanıcıya ver, Supabase SQL Editor'de çalıştırıp sonucu yapıştırmasını iste. (Claude Code'da Supabase bağlayıcısı kuruluysa danışma/advisor çıktısı da kullanılabilir; yoksa SQL yeter.) Canlı veritabanına kendin bağlanma.
4. **Yetki testi:** Kod varsa, iki farklı kullanıcıyla başkasının nesnesine erişmeyi deneyen Django testleri yazılmasını öner (aşağıda).
5. **Rapor:** Aşağıdaki biçimde yaz. Önem sırası: KRİTİK > YÜKSEK > ORTA > DÜŞÜK.

## Kontrol listesi

**A. Yetkilendirme (en sık görülen açık)**
- Her view giriş ister mi (`login_required` / `LoginRequiredMixin`), halka açık olanlar bilinçli mi?
- Her nesne sorgusu kullanıcının kendi verisi ya da üyesi olduğu aile ile **filtreleniyor** mu? `get_object_or_404(Model, pk=pk)` tek başına IDOR'dur: başka kullanıcının id'sini yazınca veri gelir.
- Başkasının/üye olunmayan ailenin nesnesi **404** dönüyor mu (403 değil; varlığını sızdırmasın)?
- Aileden çıkarılan/ayrılan kullanıcı o ailenin verisine anında erişimini kaybediyor mu?
- Aile davet kodu sadece üyelere gösteriliyor mu? Rol kuralları (silme/üye çıkarma sadece kurucu) sunucuda zorlanıyor mu?
- Kişisel (family=NULL) öğeler hiçbir aile görünümünde sızıyor mu?

**B. Girdi ve çıktı**
- Şablonlarda `|safe`, `mark_safe`, `autoescape off` yok mu?
- JS'te kullanıcı metni `innerHTML` ile basılıyor mu? (başlık, not, gıda adı, aile adı, isim aile üyelerine de gösterilir: kalıcı XSS) `textContent` olmalı.
- Formlarda `fields` tek tek yazılmış mı? `owner`, `family`, `is_done` gibi alanlar istemciden alınmıyor, sunucuda atanıyor mu?
- Karakter limitleri model/form/doğrulayıcıda var mı (istemci tarafı yetmez)? Tarih/saat değerleri sunucuda doğrulanıyor mu (ör. bitiş < başlangıç)?
- Ham SQL varsa parametreli mi?

**C. Kimlik doğrulama ve oturum**
- Giriş ve davet kodu denemelerinde sınır (rate limit) var mı? (davet kodu 8 karakter; kaba kuvvetle denenebilir)
- `next` yönlendirmesi `url_has_allowed_host_and_scheme` ile doğrulanıyor mu?
- Giriş hata mesajı "e-posta mı parola mı yanlış" ayrımını sızdırıyor mu? E-posta büyük/küçük harf duyarsız benzersiz mi?
- Parola doğrulayıcıları açık mı? Parola loglanıyor mu? Oturum çerezleri `Secure`, `HttpOnly`, `SameSite` ayarlı mı?
- Hesap silme parola/oturum onayı istiyor mu?

**D. Üretim ayarları**
- `DEBUG` ortamdan, varsayılan False; `SECRET_KEY` ortamdan; `ALLOWED_HOSTS` gerçek alan adları; `CSRF_TRUSTED_ORIGINS` ayarlı.
- `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`, `SECURE_PROXY_SSL_HEADER` (Vercel için), `X_FRAME_OPTIONS=DENY`, `SECURE_CONTENT_TYPE_NOSNIFF`, `DATA_UPLOAD_MAX_MEMORY_SIZE`.
- Admin paneli varsayılan adreste mi, kapalı/korunaklı mı? Hata sayfaları (404/500) iç bilgi sızdırmıyor mu?
- Yanıtlarda temel güvenlik başlıkları var mı (Referrer-Policy, Permissions-Policy, mümkünse CSP)?

**E. Supabase / veritabanı**
- Tablolar `public` şemasında ve Supabase'in otomatik REST (Data API) yüzeyi bu şemayı varsayılan olarak yayınlar. RLS kapalı + anon anahtarı herkese açık = veri herkese açık. Ya Data API kapalı olmalı ya da RLS açık ve `anon`/`authenticated` yetkileri geri alınmış olmalı.
- `service_role` anahtarı hiçbir yerde (kod, JS, repo, log) yok; Supabase anon/service anahtarı bu projede hiç kullanılmıyor olmalı.
- Bağlantı adresi sadece ortam değişkeninde; geliştirme ve canlı ayrı veritabanı; Vercel **Preview** ortamı canlı veritabanına bağlanmıyor.

**F. İş kuralları ve limitler**
- Günlük 20 öğe, 2 aile, karakter sınırları **sunucuda** ve `core/limits.py` sabitlerinden zorlanıyor mu?
- Limit kontrolü ve kayıt aynı `transaction.atomic` içinde, kullanıcı satırı `select_for_update` ile kilitli mi? (yoksa aynı anda gönderilen isteklerle limit aşılır)
- Aile oluşturma, öğe ekleme gibi uçlarda kötüye kullanım (spam) sınırı var mı?

**G. Gizlilik (KVKK) ve veri**
- Aydınlatma metni ve gizlilik sayfası, kayıtta onay kutusu var mı? Hesap silme tüm kişisel veriyi siliyor mu (ilişki kuralları bölüm 7)? Veri dışa aktarma var mı?
- Loglarda e-posta, parola, davet kodu, token yok mu?

**H. Bağımlılıklar**
- `requirements.txt` sürümleri sabit mi? Bilinen açık taraması için `pip-audit` kullanılabilir; kurmadan önce kullanıcıya sor.

## Yetki testi şablonu

Her pk alan view için (takvim öğesi, gıda, ev işi, aile detayı) şu desende Django testi yaz:
- A kullanıcısı bir nesne oluşturur. B kullanıcısı (aynı ailede olmayan) aynı URL'ye GET/POST/DELETE yapar. Beklenen: **404** ve veri değişmemiş.
- A ve B aynı ailede iken aile nesnesi erişilebilir; B aileden çıkınca erişim 404 olur.
- Giriş yapmamış kullanıcı giriş sayfasına yönlenir.
- Aynı gün 21. kayıt reddedilir; 3. aileye katılım reddedilir; ardışık yanlış davet kodu denemeleri sınırlanır.

## Rapor biçimi

Her bulgu için:

```
[ÖNEM] Kısa başlık
Yer: dosya:satır
Sorun: ne yanlış, saldırgan bununla ne yapabilir (1-2 cümle)
Çözüm: somut düzeltme
```

Sonda: kaç bulgu, en acil 3 madde ve "Henüz yazılmadığı için denetlenemeyenler" listesi. Düzeltmeleri kullanıcı onaylamadan yapma.
