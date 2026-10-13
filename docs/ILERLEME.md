# Callender: İlerleme

Her aşama bitince Claude Code bu dosyayı günceller. Yeni oturumda önce bunu oku.

| Aşama | Konu | Durum |
|---|---|---|
| 1 | İskelet ve tasarım sistemi | ✅ |
| 2 | Kimlik doğrulama | ✅ |
| 3 | Kişisel takvim | ✅ |
| 4 | Aile grupları | ✅ |
| 5 | Buzdolabı ve son kullanma | ✅ |
| 6 | Ev işleri ve ev durumu | 🟨 sürüyor |
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
- **Migrate uygulandı** (2026-10-12): `accounts`, `admin`, `auth`, `contenttypes`, `sessions` tabloları Supabase'te.
- **Güvenlik, RLS:** Supabase `public` şemasını kendi REST API'si (PostgREST) üzerinden dışarıya açar. RLS kapalıyken `accounts_user` (parola özetleri) ve `django_session` anon anahtarla okunabiliyordu. Tüm tablolarda RLS açıldı, hiç kural tanımlanmadı, yani API erişimi tamamen kapalı. Django tablo sahibi `postgres` rolüyle bağlandığı için etkilenmiyor. `core/db.py` + `core/apps.py` içindeki `post_migrate` sinyali her migrate'ten sonra yeni tablolarda RLS'yi otomatik açar. Supabase güvenlik danışmanında yalnızca bilgi seviyesinde "RLS enabled no policy" notu kalır; bu bilinçli bir durum.
- **Git:** depo `main` dalında, uzak depo `origin` = https://github.com/ardaozgur13/Callender
- **Supabase'te kalan:** `test_callender` adlı test veritabanı (boş tablolar, `--keepdb` ile yeniden kullanılıyor). İstenirse Supabase SQL Editor'da `DROP DATABASE test_callender WITH (FORCE);` ile silinebilir.

### Aşama 3
- **`calendar_app.CalendarItem`:** `owner`, `kind` (etkinlik, görev, amaç, doğum günü, yıldönümü, hatırlatma), `title` (80), `description` (500), `date`, `all_day`, `start_time`/`end_time`, `repeat` (`none`/`yearly`), `is_done`, zaman damgaları. `(owner, date)` indeksli.
- **`family` alanı henüz yok:** `families.Family` modeli Aşama 4'te gelecek. Alan orada `null=True` ile eklenecek; mevcut öğeler kişisel kalır.
- **Tekrar:** Prototipte sadece `none` ve `yearly` var (belgeye uygun); haftalık/aylık daha sonra. Yıllık öğeler tek satırda tutulur, `services.occurrences_between` ile hesaplanır. İlk tarihten önceki yıllarda görünmez; 29 Şubat artık olmayan yıllarda 28 Şubat'ta gösterilir. Doğum günü/yıldönümünde "(N. yıl)" gösterilir.
- **Günlük limit (20):** `services.save_item` içinde, sunucu tarafında. Sayım öğenin kayıtlı `date`'ine göre yapılır; yıllık tekrarlar sadece ilk tarihlerinde sayılır. Aynı anda iki istek limiti aşmasın diye kullanıcı satırı `select_for_update` ile kilitlenir. Düzenlemede öğe kendi gününde kalıyorsa kendisi sayılmaz.
- **Silme:** Yıllık öğe silinince tüm yılları silinir (onay mesajında belirtiliyor). Tek bir yılı atlama özelliği yok.
- **"Tamamlandı":** sadece görev ve amaç için.
- **Sayfalar:** `/takvim/` (bu ay), `/takvim/<yıl>/<ay>/`, `/takvim/<yıl>/<ay>/<gün>/`, `/takvim/ekle/?tarih=…`, `/takvim/oge/<id>/duzenle|sil|tamamla/`. Ay görünümü Pazartesi'den başlar; mobilde hücrelerde sadece ikonlar, masaüstünde başlıklar görünür. "Bugün" sayfası günün öğelerini gösterir.
- **Yetki:** Tüm sorgular `owner=request.user`; başkasının öğesi 404. `next` yönlendirmesi sadece site içi adreslere izin verir.
- **JS:** `static/js/item-form.js`: doğum günü/yıldönümü seçilince tekrar "Her yıl" olur, "Tüm gün" işaretliyken saat alanları gizlenir. JS olmadan da form çalışır.
- **Migrate uygulandı** (2026-10-13), yeni tabloda RLS otomatik açıldı. 55 test geçti.
- **Görsel kontrol:** Giriş gerektiren sayfalar tarayıcıda Claude tarafından kontrol edilmedi; bunun için hesap açmak gerekirdi. Kullanıcı kontrol edecek.

### Aşama 4
- **Modeller:** `families.Family` (`name` 40, `invite_code` benzersiz, `created_by` SET_NULL), `families.FamilyMember` (`role` owner/member, `joined_at`, `(family, user)` benzersiz). `CalendarItem.family` eklendi (null = kişisel; aile silinince aile öğeleri de silinir).
- **Servisler (`families/services.py`):** kurma (kurucu = owner), kodla katılma, ayrılma, üye çıkarma, kod yenileme, aileyi silme. Davet kodu `secrets` ile, `limits.INVITE_CODE_ALPHABET` (0/O/1/I yok), 8 karakter. Girilen kod büyük harfe çevrilir; boşluk ve tireler atılır.
- **Limitler:** 2 aile (kurma + katılma), aile başına 8 üye. Kullanıcı ve aile satırı kilitlenerek kontrol edilir (eşzamanlı isteklere karşı).
- **Ayrılma:** Kurucu ayrılırsa en eski üye kurucu olur; son üye ayrılırsa aile ve aile kayıtları silinir. Hesap silinirken önce tüm ailelerden bu kurallarla ayrılınır. Not: silinen hesabın aile kayıtları da silinir (`owner` CASCADE).
- **Yetki:** Aile sayfaları ve işlemleri üye olmayana 404 döner (ailenin var olduğu bile sızmaz). Yeniden adlandırma, kod yenileme, üye çıkarma ve silme sadece kurucuda. Aile takvim kayıtlarını her üye düzenleyip silebilir (belge: "tüm üyeler eşit yetkili"). Düzenleyen değişse de kaydın `owner`'ı değişmez.
- **Bağlam seçici:** Sayfanın üstünde "👤 Bireysel / 👨‍👩‍👧 Aile adı" seçimi (en az bir ailesi olana görünür). Seçim oturumda (`active_family_id`) tutulur, her istekte üyelik yeniden doğrulanır; üyelik bittiyse Bireysel'e döner. Bireysel = sadece kişisel kayıtlar; Aile = o ailenin tüm kayıtları (kimin eklediği yazar). Yeni kayıt seçili bağlama eklenir; form başlığı nereye ekleneceğini söyler. Bugün sayfası da bağlama göre.
- **Günlük limit:** Belgeye uygun olarak kişisel + kendi eklediğin aile kayıtları birlikte sayılır; başka üyenin eklediği kayıtlar senin kotana sayılmaz.
- **Kod kopyalama:** Aile sayfasında "Kopyala" butonu (Clipboard API).
- **Testler:** 85 test geçti. Testlerde parola özeti için MD5 kullanılıyor (`settings.py`, sadece `manage.py test`). Test süresi 7,5 dakikadan 3 dakikaya indi; kalan süre Supabase'e (Frankfurt) ağ gecikmesi.
- **Migrate uygulandı** (2026-10-13), aile tablolarında RLS otomatik açıldı.
- **Bilinçli olarak yapılmayanlar:** Davet kodu deneme sınırı (rate limit) yok; 32^8 ≈ 10^12 olasılık prototip için yeterli. Aile kaydını kişisele (ya da tersine) taşıma yok.

### Aşama 5
- **`fridge.ShelfLifeRule`:** Belgenin 8. bölümündeki 17 satır `fridge/seed_shelf_life.py` içinde; değerler ve `usda`/`estimate` etiketleri belgeyle birebir (11 usda, 6 estimate). Veri migration'ı `0002_seed_shelf_life_rules` yükler (`key`'e göre update_or_create). Yeni ürün eklemek için tabloya satır ekle ve yeni bir veri migration'ı yaz; değer uydurma.
- **`fridge.FoodItem`:** belgedeki alanlar. `use_by` tek yerde, `FoodItem.compute_use_by()` içinde hesaplanır: açılmışsa açılma + gün, ambalaj SKT'si de varsa erken olanı, sadece SKT varsa o, hiçbiri yoksa boş. `save()` her kayıtta (`update_fields` ile de) yeniden hesaplayıp veritabanına yazar; sıralama ve "yaklaşanlar" sorgusu bu sayede veritabanında yapılır.
- **Durum:** taze (>3 gün), yaklaşıyor (≤3 gün, `limits.EXPIRY_WARNING_DAYS`), süresi geçti (<0), tarih yok. Etiketler: "5 gün kaldı", "Yarın son gün", "Bugün son gün", "2 gün geçti". Renkler `--status-*` değişkenlerinden.
- **Öneri:** Ürün adı alanında `<datalist>` öneri listesi var. Ad bir kuralla eşleşince JS gün ve saklama yerini doldurur, kaynağı ve notu gösterir; kullanıcının değiştirdiği güne dokunmaz. Sunucu da adı büyük/küçük harf duyarsız eşleştirip kuralı bağlar; gün boşsa kuraldan doldurur. Zorunlu uyarı metni liste ve form sayfasında var.
- **İşlemler:** ekle, düzenle, sil, "Bugün açtım" (açılma = bugün, gün boşsa kuraldan), "Tüketildi" (listeden kalkar, `consumed_at` dolar). Açılma tarihi ileri bir tarih olamaz; gün en fazla 365 (`limits.SUGGESTED_DAYS_MAX`).
- **Bağlam ve yetki:** Takvimle aynı model. Bireysel = kişisel buzdolabı, Aile = ortak buzdolabı (her üye görür ve düzenler, kimin eklediği yazar). Erişimi olmayana 404.
- **Limit:** 150 aktif (tüketilmemiş) ürün. Belge bunu aile için tanımlıyor; kişisel buzdolabına da aynı sınır uygulandı. Aile ya da kullanıcı satırı kilitlenerek kontrol edilir.
- **Bugün sayfası:** 3 gün içinde biten ya da süresi geçmiş ürünler (bağlama göre), oradan "Tüketildi" denebilir.
- **Migrate uygulandı** (2026-10-13), RLS açık. 110 test geçti (~4 dk).

### Aşama 6
- **Modeller (`home`):**
  - `Chore`: `family` (zorunlu), `title` (80), `assigned_to` (boş = Herkes, SET_NULL), `weekday` (0–6, boş = her gün), `is_active`. Her hafta tekrar eder.
  - `ChoreLog`: `(chore, date)` benzersiz, `done_by`, `done_at`.
  - `HomeStatus`: `(family, kind)` benzersiz, `status`, `updated_by`, `updated_at`.
- **Ev işleri sadece ailede:** Belgedeki modelde `family` zorunlu. Bireysel görünümde `/ev/` "bir aile seç" mesajı gösterir.
- **Haftalık görünüm:** `/ev/` sayfasında Pazartesi–Pazar, önceki/sonraki hafta (`?hafta=YYYY-MM-DD`). "Yaptım" aç/kapat yapar ve kimin yaptığını yazar. Gelecek günler ve o güne planlanmamış işler işaretlenemez. Aynı anda iki işaretlemeye karşı benzersizlik kısıtı var.
- **Atama:** Sadece aile üyelerine atanabilir (form queryset'i). Üye ayrılır ya da çıkarılırsa işleri "Herkes"e döner (`families.services._unassign_chores`).
- **Limit:** Ailede 50 aktif iş (`limits.MAX_CHORES_PER_FAMILY`), aile satırı kilitlenerek kontrol edilir; pasif işler sayılmaz.
- **Ev durumu kartları:** Belgedeki akışlar.
  - Bulaşık: Boş → Dolu → Çalışıyor → Bitti → Boşaltılmalı → Boş.
  - Çamaşır: Yıkanıyor → Yıkandı, serilmeli → Serildi → Kurudu, toplanmalı → Toplandı → (yeni yıkama).
  - İlk durum: bulaşık "Boş", çamaşır "Toplandı". Kartlar ilk açılışta oluşturulur.
  - Tek tıkla "Sonraki adım"; "Başka bir duruma geç / geri al" ile serbest seçim.
  - Kartta "Son güncelleme: Ayşe, bugün 14:20 → Yıkandı" yazar. Saatten sonra gelen Türkçe ek (’de/’da) ses uyumuna göre değiştiği için ek kullanılmadı.
- **Çakışma koruması:** Her durum formu kullanıcının gördüğü durumu (`expected`) gönderir. Bu arada başkası değiştirdiyse adım ilerletilmez ve "Can bu arada durumu … yaptı" mesajı çıkar; çift tıklama ya da iki kişinin aynı anda basması adımı iki kez atlatmaz.
- **Güncelleme görünürlüğü:** Diğer üyenin değişikliği sayfa yenilenince görünür ("↻ Yenile" butonu). Canlı (otomatik) yenileme yok.
- **Bugün sayfası:** Aile seçiliyse ev durumu kartları ve bugünün işleri; buradan da "Yaptım" ve "Sonraki adım" denebilir.
- **Migrate uygulandı** (2026-10-13), RLS açık. 131 test geçti (~6 dk).
