# Callender: İlerleme

Her aşama bitince Claude Code bu dosyayı günceller. Yeni oturumda önce bunu oku.

| Aşama | Konu | Durum |
|---|---|---|
| 1 | İskelet ve tasarım sistemi | ✅ |
| 2 | Kimlik doğrulama | 🟨 sürüyor |
| 3 | Kişisel takvim | ⬜ |
| 4 | Aile grupları | ⬜ |
| 5 | Buzdolabı ve son kullanma | ⬜ |
| 6 | Ev işleri ve ev durumu | ⬜ |
| 7 | Cilalama ve yayın | ⬜ |

Durumlar: ⬜ başlamadı · 🟨 sürüyor · ✅ bitti (kullanıcı onayladı)

## Notlar / kararlar

### Aşama 1
- **Bağımlılıklar:** Django 5.2 LTS, psycopg 3 (binary), dj-database-url, whitenoise, python-dotenv. Başka bağımlılık yok.
- **Limitler `core/limits.py`'de.** `docs/callender.md` bölüm 5 `callender/limits.py` diyor, ama CLAUDE.md ve `/kontrol` komutu `core/limits.py` diyor; bu yüzden `core/limits.py` seçildi. Belgedeki yolun düzeltilmesi önerilir. Davet kodu alfabesi/uzunluğu, SKT uyarı günü (3) ve isim/parola alt sınırları da buraya eklendi.
- **Ayarlar:** `SECRET_KEY` ve `DATABASE_URL` zorunlu; yoksa açık bir Türkçe hata verilir. SQLite'a düşülmez. `CONN_MAX_AGE=0`, `DISABLE_SERVER_SIDE_CURSORS=True`. psycopg 3, Django'da varsayılan olarak istemci taraflı bağlama kullandığı için pooler'ın transaction modunda prepared statement sorunu çıkmaz.
- **Statik dosyalar:** `WHITENOISE_USE_FINDERS=True`, `STATIC_ROOT` yok; Vercel'de `collectstatic`/build adımı gerekmez.
- **Güvenlik (DEBUG=False):** Güvenli çerezler ve proxy SSL başlığı açık. HSTS ve `SECURE_SSL_REDIRECT` bilinçli olarak kapalı (Vercel zaten HTTPS'e yönlendiriyor); Aşama 7'de yeniden gözden geçirilecek.
- **Uygulamalar:** `core`, `accounts`, `calendar_app`, `families`, `fridge`, `home` oluşturuldu; modeller boş.
- **⚠️ Aşama 2'den önce `migrate` ÇALIŞTIRMA.** Özel User modeli (`AUTH_USER_MODEL`) ilk migrate'ten önce tanımlanmalı. Aksi halde auth tabloları varsayılan User ile oluşur ve sonradan değiştirmek zahmetli olur. Aşama 1'de bağlantıyı `python manage.py check --database default` ile test et.
- **Testler:** `core/tests.py` dosyasındaki testler `SimpleTestCase` (veritabanı gerektirmez, Supabase'te test DB açılmaz). 6 test geçti, `check` temiz. `check --deploy` sadece HSTS/SSL redirect uyarısı veriyor (yukarıya bak).
- **Arayüz:** `theme.css` (palet ve ölçü değişkenleri), `base.css` (mobilde alt gezinme, ≥768px'te yan menü, kart/buton/rozet/boş durum bileşenleri, odak halkası, "içeriğe geç" bağlantısı). Henüz yapılmamış sayfalar menüde pasif ("Yakında").
- **Doğrulama:** `.env` hazır. Supabase pooler bağlantısı gerçek bir sorguyla doğrulandı (PostgreSQL 17, port 6543). Ana sayfa tarayıcıda masaüstü (yan menü) ve mobil (alt çubuk) görünümde kontrol edildi.
- **Not:** Veritabanı şifresinde `@ ? # / : %` gibi işaretler `DATABASE_URL`'i bozar. Şifre sadece harf ve rakamdan oluşmalı (ya da URL-encode edilmeli).
- **Not:** `check --database default` Postgres'te bağlantıyı her zaman gerçekten açmaz. Bağlantıyı asıl kanıtlayan gerçek bir sorgu.

### Aşama 2
- **`accounts.User`** (`AbstractBaseUser` + `PermissionsMixin`): `email` (benzersiz, kaydederken ve girişte küçük harfe çevrilir), `display_name` (2–40, `core/limits.py`), `is_active`, `is_staff`, `date_joined`. `username` yok. `AUTH_USER_MODEL = "accounts.User"`. Migration: `accounts/0001_initial.py`.
- **Giriş zorunluluğu:** Django 5.1+ `LoginRequiredMiddleware`; her sayfa varsayılan olarak korunur. Açık olanlar: giriş (`/giris/`) ve kayıt (`/kayit/`). Sonraki aşamalarda yeni view'lar otomatik korunur.
- **Sayfalar:** kayıt (isim, e-posta, parola ×2; kayıt sonrası otomatik giriş), giriş, çıkış (sadece POST), ayarlar (`/ayarlar/`: isim değiştir, parola değiştir ve oturum açık kalır, çıkış, hesabı sil). Hesap silme bölüm 4/9 gereği eklendi; parola tekrarı ve tarayıcı onayı ister.
- **Parola kuralları:** en az 8 karakter (`limits.PASSWORD_MIN`); isim/e-postaya benzer, yaygın ya da sadece rakamdan oluşan parolalar reddedilir. Hata mesajları Türkçe.
- **Arayüz:** giriş yapmamış kullanıcıya menüsüz, ortalanmış düzen; mesaj kutuları, form stilleri. Mobilde üst çubukta ⚙️ ile ayarlara gidilir, masaüstünde yan menüde "Ayarlar".
- **Admin:** özel `UserAdmin` (e-posta ile).
- **Testler:** 26 test geçti (`accounts/tests.py`, `core/tests.py`). Testler artık veritabanı kullanıyor. Supabase pooler test veritabanını kapatırken bağlantıyı tuttuğu için `python manage.py test --keepdb` kullanılmalı. Düz `test` komutunda testler yine geçer, ama sonda "database is being accessed by other users" hatası çıkar. `/kontrol` komutu da bu yüzden `--keepdb` ile çalıştırılmalı.
- **Supabase'te kalan:** `test_callender` adlı test veritabanı (boş tablolar, `--keepdb` ile yeniden kullanılıyor). İstenirse Supabase SQL Editor'da `DROP DATABASE test_callender WITH (FORCE);` ile silinebilir.
