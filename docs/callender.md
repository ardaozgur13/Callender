# Callender — Proje Rehberi (Claude Code için)

> Bu dosya projenin tek kaynak belgesidir (single source of truth). Claude Code, bir aşamaya başlamadan önce ilgili bölümleri okumalı, sadece istenen aşamayı yapmalı, bitirince `docs/ILERLEME.md` dosyasını güncelleyip dururup onay beklemelidir. Kısa kurallar kökteki `CLAUDE.md` içindedir.

## 0. Claude Code için çalışma kuralları

1. **Aşama aşama ilerle.** Kullanıcı `/asama N` demeden sonraki aşamaya geçme. Her aşama sonunda: ne yapıldı, nasıl çalıştırılır, nasıl test edilir kısa özet ver ve `docs/ILERLEME.md` dosyasını güncelle.
2. **Prototip hedefi:** Aşırı mühendislik yapma. Ek kütüphane, Docker, Celery, Redis, React/Vue, Tailwind build adımı, REST framework gibi şeyler **kullanma**. Gerekirse önce sor.
3. **Kod yorumları ve arayüz metinleri Türkçe**, değişken/model/fonksiyon adları İngilizce olsun.
4. **Gizli bilgiler** (Supabase şifresi, SECRET_KEY) asla koda yazılmaz; sadece ortam değişkeni (`.env`, Vercel env) olarak okunur. `.env` dosyası `.gitignore`'da olmalı, `.env.example` repoda olmalı.
5. Her formda CSRF koruması açık kalsın, kullanıcı girdileri sunucuda doğrulansın (Django form/validators). Sadece istemci tarafı doğrulamaya güvenme.
6. **`python manage.py migrate` komutunu kendi başına çalıştırma.** Migration dosyalarını üret, komutu kullanıcıya ver; canlı Supabase veritabanına dokunmadan önce onay iste.
7. Bir kullanıcı **yalnızca kendi** verisine ve **üyesi olduğu** ailelerin verisine erişebilir. Her view'da bu yetki kontrolü yapılmalı.
8. Güvenlik gereksinimleri **bölüm 12**'dedir ve her aşamanın parçasıdır (sonradan eklenecek bir şey değil). Her aşama sonunda `/guvenlik` ile denetim yapılır.

## 1. Proje özeti

**Ad:** Callender (iki "l" ile, bilinçli yazım)

**Amaç:** Kişisel ve aile odaklı kapsamlı bir takvim uygulaması. Google Takvim'in yaptığı basit işlerin (doğum günü, yıldönümü, etkinlik) ötesinde:

- Kişisel hedefler, yapılacaklar ve saatleri
- Buzdolabı / gıda takibi: açılan ürünün ne zaman bozulacağı, ambalajdaki son kullanma tarihi (SKT)
- Ev işleri: hangi iş hangi gün kimin
- Aile grupları: aynı buzdolabını ve ev durumlarını (bulaşık, çamaşır) paylaşma
- Hem bireysel hem ortak (aile) görünüm

**Hedef kitle:** Teknik olmayan, günlük hayatını kolaylaştırmak isteyen bireyler ve aileler. Arayüz sade, anlaşılır olmalı.

## 2. Teknoloji yığını (sabit, değiştirme)

| Katman | Seçim |
|---|---|
| Dil / backend | Python 3.11+, Django (güncel LTS) |
| Veritabanı | Supabase (PostgreSQL). Django ORM ile doğrudan Postgres'e bağlanılır; Supabase'in kendi auth/JS SDK'sı **kullanılmaz** |
| Kimlik doğrulama | Django'nun kendi auth sistemi (özelleştirilmiş User modeli) |
| Deployment | Vercel (Python runtime) |
| Frontend | Aynı repo içinde, framework yok: Django template + saf HTML, CSS, JavaScript |
| Statik dosyalar | WhiteNoise |
| Ortam değişkenleri | `python-dotenv` veya `django-environ` (biri yeterli) |
| İzin verilen ek paketler | `psycopg[binary]`, `dj-database-url`, `whitenoise`, `django-environ`. Bunun dışında paket eklemeden önce sor. **İstisna (2026-10-13, kullanıcı onayı):** projede `django-environ` yerine `python-dotenv` kullanılıyor (sadece yerelde `.env` okur) |

### Vercel + Supabase için kritik notlar
- Vercel serverless olduğu için **SQLite kullanılamaz**, dosya sistemine kalıcı yazılamaz. Tüm veri Supabase'te.
- Supabase'in **connection pooler** (Transaction mode, port 6543) adresi kullanılmalı. Bu modda `DISABLE_SERVER_SIDE_CURSORS = True` ve `CONN_MAX_AGE = 0` ayarlanmalı.
- `DATABASE_URL` ortam değişkeninden okunur (`dj-database-url` kullanılabilir).
- `vercel.json` ile tüm istekler Django WSGI uygulamasına yönlendirilir. `ALLOWED_HOSTS` içine `.vercel.app` ve özel alan adı eklenir. `CSRF_TRUSTED_ORIGINS` de ayarlanır.
- Migration'lar Vercel build'inde değil, **yerelden** Supabase'e karşı çalıştırılır (`python manage.py migrate`). Bunu README'ye yaz.
- Zaman dilimi: `TIME_ZONE = "Europe/Istanbul"`, `USE_TZ = True`, dil: `LANGUAGE_CODE = "tr"`.
- **Supabase Data API'si kapatılmalı** (bölüm 12.1). Uygulama veritabanına sadece Django üzerinden, doğrudan Postgres bağlantısıyla gider; Supabase'in otomatik REST uç noktasına ihtiyacı yoktur ve açık kalması veriyi herkese açabilir.
- Geliştirme ve canlı için **ayrı iki Supabase projesi** kullan. Vercel'de **Preview** ortamının `DATABASE_URL`'i canlı veritabanını göstermemeli.

## 3. Arayüz / tasarım dili

**His:** Sanki bahar çayırında huzurlu bir gün. Yumuşak, tatlış, temiz ve güven veren. Keskin kontrast, neon, ağır gölgeler yok.

**Renk paleti (toz/mat pastel).** CSS değişkeni olarak `static/css/theme.css` içinde tanımla:

```css
:root {
  --cream:        #FFF9EE; /* ana arka plan, kremsi beyaz */
  --cream-deep:   #F7EEDC; /* kart/ikincil zemin */
  --blue:         #BFD8E6; /* kremsi toz mavi (ana vurgu) */
  --blue-deep:    #8FB3C9; /* buton hover, aktif öğe */
  --pink:         #F2CFCF; /* kremsi toz pembe (ikincil vurgu) */
  --pink-deep:    #E3AFB0;
  --yellow:       #F6E3A1; /* mat tereyağı sarısı (uyarı/vurgu) */
  --sage:         #CFE0C3; /* çayır yeşili, "tamamlandı/taze" durumu */
  --text:         #4A4A55; /* koyu gri-lacivert, saf siyah YOK */
  --text-soft:    #7C7C8A;
  --danger-soft:  #E8A9A0; /* bozuldu/süresi geçti, bağırmayan kırmızı */
  --radius:       16px;
  --shadow:       0 4px 14px rgba(120, 110, 90, 0.10);
}
```

**Tasarım kuralları:**
- Yuvarlak köşeler (16px), çok hafif gölgeler, bol boşluk.
- Yazı tipi: Google Fonts'tan yuvarlak hatlı, okunaklı bir font (örn. **Nunito** veya **Quicksand**); sistem fontu yedek olarak tanımlı.
- Mobil öncelikli (mobile-first), tek sütundan başlayıp masaüstünde genişleyen responsive düzen. Alt gezinme çubuğu (mobil) / yan menü (masaüstü).
- Durum renkleri: taze = `--sage`, yaklaşıyor = `--yellow`, süresi geçti = `--danger-soft`.
- Küçük, sade emoji/ikon kullanımı serbest (🥛 🧺 🍽️ 🎂), ama aşırıya kaçma.
- Erişilebilirlik: yeterli metin kontrastı, odak (focus) halkaları, butonlarda anlamlı etiketler.
- Boş durumlar (empty state) için sıcak, kısa Türkçe mesajlar ("Bugün için planın yok, çayırda gezinme zamanı 🌼").

## 4. Kullanıcı ve hesap kuralları

- Kayıt alanları: **e-posta, parola, görünen ad (isim)**.
- Giriş e-posta + parola ile. `username` alanı kullanılmaz; `AbstractBaseUser` ile e-posta `USERNAME_FIELD` olur.
- E-posta benzersiz ve küçük harfe normalize edilir.
- Parola: en az 8 karakter, Django'nun parola doğrulayıcıları açık.
- İsim: 2–40 karakter.
- Çıkış, parola değiştirme, hesap silme ayarlar sayfasında olur. (Parola sıfırlama e-postası prototipte **yok**, sonraki aşama.)
- E-posta doğrulama prototipte **yok**.

## 5. Limitler (tek yerde tanımla: `core/limits.py`)

Hepsi sabit olarak tek dosyada dursun ki sonra fiyatlandırma/paket sistemi eklenirken kolayca değiştirilebilsin. Sabitleri kodun içine dağıtma.

| Sabit | Değer | Açıklama |
|---|---|---|
| `MAX_FAMILIES_PER_USER` | 2 | Bir kullanıcı en fazla 2 aileye üye olabilir (kurucu da sayılır). Sonradan ücretli paketle artabilir |
| `MAX_ITEMS_PER_DAY` | 20 | Bir kullanıcının **bir takvim gününe** ekleyebileceği görev/etkinlik/hatırlatma toplamı. Kişisel + kendi oluşturduğu aile öğeleri birlikte sayılır |
| `MAX_FAMILY_MEMBERS` | 8 | Bir ailedeki üye sayısı (öneri, kolay değişir) |
| `MAX_FRIDGE_ITEMS_PER_FAMILY` | 150 | Aktif (tüketilmemiş) gıda kaydı |
| `MAX_CHORES_PER_FAMILY` | 50 | Aktif ev işi tanımı |
| `TITLE_MAX` | 80 | Etkinlik/görev/iş başlığı |
| `DESCRIPTION_MAX` | 500 | Açıklama / not |
| `FOOD_NAME_MAX` | 60 | Gıda adı |
| `FOOD_NOTE_MAX` | 200 | Gıda notu |
| `FAMILY_NAME_MAX` | 40 | Aile adı |
| `USER_NAME_MAX` | 40 | Kullanıcı görünen adı |
| `INVITE_CODE_LENGTH` | 8 | Davet kodu uzunluğu (32 karakterlik alfabeyle yaklaşık 1,1 trilyon olasılık) |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES` | 5 / 15 | Aynı e-postaya art arda yanlış parola denemesi sınırı |
| `JOIN_MAX_ATTEMPTS` / `JOIN_LOCKOUT_MINUTES` | 5 / 15 | Bir kullanıcının yanlış davet kodu deneme sınırı |
| `FAMILY_CREATE_PER_DAY` | 3 | Bir kullanıcının günde oluşturabileceği aile sayısı (kötüye kullanım önleme) |

Limit aşıldığında kullanıcıya nazik bir Türkçe mesaj göster ("Bu güne en fazla 20 kayıt ekleyebilirsin.") ve kaydı oluşturma. Limit kontrolü **sunucu tarafında** (servis fonksiyonunda) yapılır; arayüzde sayaç göstermek isteğe bağlı.

**Günlük 20 limitinin tam tanımı (varsayım, değiştirilebilir):**
- "Gün", öğenin **takvimdeki tarihidir** (`date`), eklendiği gün değil. Bir kullanıcının aynı tarihe en fazla 20 öğesi olabilir.
- `owner` olarak kullanıcı olan kişisel ve aile öğeleri birlikte sayılır. Tamamlanmış öğeler de sayılır, silinenler sayılmaz.
- Yıllık tekrar eden öğe (doğum günü vb.) sadece **ilk kaydedildiği tarihte** sayılır; tekrar günlerinde ayrıca sayılmaz.
- Kontrol ve kayıt aynı `transaction.atomic` içinde, kullanıcı satırı `select_for_update` ile kilitlenerek yapılır (bölüm 12.6). Aksi halde aynı anda gelen isteklerle limit aşılabilir.

## 6. Aile grupları

- Kullanıcı aile oluşturur → sistem benzersiz bir **davet kodu** üretir (8 karakter, büyük harf + rakam, karışabilen `0/O/1/I` karakterleri hariç, `secrets` modülüyle).
- Başka bir kullanıcı bu kodu girerek katılır. Katılmadan önce kullanıcının 2 aile limiti kontrol edilir.
- Roller: `owner` (kurucu) ve `member`. Kurucu: aileyi yeniden adlandırabilir, davet kodunu yenileyebilir, üyeyi çıkarabilir, aileyi silebilir. Üye: istediği zaman ayrılabilir.
- Kurucu ayrılırsa: başka üye varsa en eski üye otomatik kurucu olur; kimse kalmazsa aile silinir.
- Davet kodu yenilenince eski kod geçersiz olur.
- Davet kodu sadece aile üyelerine gösterilir. Kod `secrets` ile üretilir, loglara yazılmaz.
- Yanlış kod denemeleri sınırlanır (`JOIN_MAX_ATTEMPTS`). Hata mesajı hep aynıdır ("Kod geçersiz"); kodun var olup olmadığını, süresinin dolup dolmadığını ayırt ettirmez.
- (Önerilen) Davet kodunun geçerlilik süresi olabilir (örn. 7 gün); kurucu yenileyebilir.
- Aileden ayrılan/çıkarılan kullanıcı o ailenin verisine **anında** erişimini kaybeder.
- Aile öğesini silme/düzenleme: üyeler kendi eklediğini düzenler/siler; kurucu ailedeki her şeyi yönetir.
- Aile içinde herkes aynı buzdolabını, ev işlerini ve ev durumlarını görür/düzenler (prototipte tüm üyeler eşit yetkili, sadece silme/üye çıkarma kurucuda).
- Kullanıcı arayüzde bağlam seçici ile **"Bireysel"** ya da bir **aile** görünümüne geçer.

## 7. Veri modeli (Django modelleri)

Öneri uygulama yapısı: `accounts`, `calendar_app`, `families`, `fridge`, `home` (ev işleri + durumlar), `core` (limitler, ortak yardımcılar).

### `accounts.User`
`email` (unique), `display_name`, `is_active`, `date_joined`.

### `families.Family`
`name`, `invite_code` (unique), `created_by` (FK User), `created_at`.

### `families.FamilyMember`
`family` (FK), `user` (FK), `role` (`owner`/`member`), `joined_at`. `(family, user)` benzersiz.

### `calendar_app.CalendarItem`
- `owner` (FK User, oluşturan)
- `family` (FK Family, **null** = kişisel öğe; dolu = aile öğesi)
- `kind`: `event` (etkinlik), `task` (görev), `goal` (amaç), `birthday`, `anniversary`, `reminder`
- `title`, `description`
- `date` (DateField), `start_time` / `end_time` (null olabilir), `all_day` (bool)
- `repeat`: `none` / `yearly` / `monthly` / `weekly` (prototipte `none` ve `yearly` yeterli; doğum günü ve yıldönümü varsayılan `yearly`)
- `is_done` (bool, görev/amaç için)
- `created_at`, `updated_at`

Tekrar eden öğeler için veritabanında tek satır tutulur; takvimde gösterilirken ilgili ay/gün için hesaplanarak türetilir (satırları çoğaltma).

### `fridge.ShelfLifeRule` (öneri tablosu, seed ile doldurulur)
`key` (slug), `name_tr`, `category`, `storage` (`fridge`/`room`), `opened_days` (açıldıktan sonra önerilen gün), `source` (`usda`/`estimate`), `note`.

### `fridge.FoodItem`
- `family` (FK, null olabilir; kişisel buzdolabı için `owner`)
- `owner` (FK User, ekleyen)
- `name`, `rule` (FK ShelfLifeRule, null olabilir)
- `storage`: `fridge` / `room` / `freezer`
- `opened_on` (date, null = henüz açılmadı)
- `package_expiry` (date, null olabilir; ambalajdaki SKT)
- `suggested_days` (açıldığında kuraldan kopyalanır, kullanıcı değiştirebilir)
- `use_by` (date, null olabilir; `save()` içinde otomatik hesaplanıp **saklanır**, istemciden alınmaz; aşağıya bak)
- `note`, `is_consumed` (bool), `consumed_at`
- `created_at`

**`use_by` hesabı:** açılmışsa `opened_on + suggested_days`, ambalaj SKT'si de girilmişse ikisinin **erken olanı** geçerli son tüketim tarihidir. Sadece SKT varsa o, hiçbiri yoksa `use_by = null`. Bu hesabı modelde tek bir metotta/property'de yap, arayüzde "SKT'ye kalan gün" ve durum rengi buradan gelsin.

### `home.Chore` (ev işi)
`family`, `title`, `assigned_to` (FK User, null = herkes), `weekday` (0–6) veya `repeat` (haftalık), `is_active`.

### `home.ChoreLog`
`chore`, `date`, `done_by`, `done_at`. Bir iş o gün yapıldı mı buradan okunur.

### `home.HomeStatus` (aile başına durum kartları)
`family`, `kind` (`dishwasher` / `laundry`), `status`, `updated_by`, `updated_at`.

Durumlar:
- Bulaşık makinesi: `idle` (boş) → `loaded` (dolu) → `running` (çalışıyor) → `done` (bitti) → `needs_unloading` (boşaltılmalı) → `idle`
- Çamaşır: `washing` (yıkanıyor) → `washed` (yıkandı, serilmesi gerek) → `hanging` (serildi) → `dry` (kurudu, toplanmalı) → `done` (toplandı)

Her durum değişikliğinde kimin ne zaman güncellediği görünür ("Ayşe, 14:20'de yıkandı yaptı"). Basit tutmak için durum değişimi tek tıkla "bir sonraki adıma geç" butonuyla olsun, geri alma/serbest seçim de bulunsun.

### Giriş/aile denemelerini sınırlamak için (ek paket olmadan)
`core.AuthAttempt`: `kind` (`login`/`join`), `key` (giriş için küçük harfli e-posta, aile katılımı için kullanıcı id'si), `created_at`. Son `*_LOCKOUT_MINUTES` içinde `*_MAX_ATTEMPTS`'ı aşan anahtar için istek reddedilir; başarılı girişte o anahtarın kayıtları silinir; eski kayıtlar tembel temizlenir. Anahtar IP'ye değil hesaba bağlıdır (Vercel arkasında IP'ye güvenmek hatalıdır).

### İlişki silme kuralları, kısıtlar, indeksler
- `FamilyMember`: `family` ve `user` silinince CASCADE. `(family, user)` benzersiz.
- Aile silinince o ailenin öğeleri, gıdaları, işleri, durumları CASCADE ile silinir.
- `CalendarItem.owner`, `FoodItem.owner`, `Chore.assigned_to`, `ChoreLog.done_by`, `HomeStatus.updated_by`: **SET_NULL** (null=True). Arayüzde null kullanıcı "Silinmiş kullanıcı" olarak görünür. Hesap silinirken kişisel (`family=NULL`) öğeler ve kişisel gıdalar ayrıca açıkça silinir.
- Hesap silen kişi bir ailenin tek kurucusuysa: en eski üye kurucu olur; üye yoksa aile silinir.
- `User.email`: küçük harfe normalize + veritabanı düzeyinde büyük/küçük harf duyarsız benzersizlik (`UniqueConstraint(Lower("email"))`).
- `FoodItem`: `CheckConstraint` ile `family` ya da `owner`'dan en az biri dolu olmalı.
- İndeksler: `CalendarItem(owner, date)`, `CalendarItem(family, date)`, `FoodItem(family, is_consumed, use_by)`, `Family(invite_code)` benzersiz.
- Yıllık tekrar: 29 Şubat doğum günü artık olmayan yıllarda 28 Şubat'ta gösterilir. Doğum yılı bilinmiyorsa yaş gösterilmez.

## 8. Son kullanma önerileri (açıldıktan sonra)

Kullanıcı ürün adı girerken/seçerken sistem `ShelfLifeRule`'a göre **öneri** gösterir; kullanıcı gün sayısını istediği gibi değiştirebilir. Arayüzde mutlaka şu uyarı bulunmalı: *"Bu süreler genel önerilerdir. Ürün ambalajındaki üretici talimatı ve görünüm/koku kontrolü önceliklidir. Şüpheliysen at."*

### Doğrulama durumu (araştırma notu)
Aşağıdaki değerler için ABD Tarım Bakanlığı (USDA) **FoodKeeper** verisi ve üniversite/uzantı kaynakları referans alındı. Bu kaynaklar Türkiye ürünlerine birebir uyar diye **garanti edilemez**; özellikle UHT, ESL, çiğ ve köy ürünleri farklılık gösterir. Bu yüzden her satırda `source` alanı var: `usda` = kaynakta doğrulandı, `estimate` = muhafazakâr tahmin, ürün etiketi kontrol edilmeli.

**Önemli bulgu:** İstekte "laktozlu süt 5 gün, laktozsuz 3 gün" örneği vardı. USDA tarafında normal süt açıldıktan sonra yaklaşık **1 hafta** olarak geçiyor; laktozsuz süt için ayrı net bir USDA "açıldıktan sonra" rakamı bulunamadı (kaynakta laktozsuz süt ayrı kategori olarak listeleniyor ama süre görünmüyor). Bu yüzden laktozsuz süt **3 gün (estimate, muhafazakâr)** olarak bırakıldı ve normal süt de güvenli tarafta **5 gün** seçildi. Kullanıcı ayarlayabilir; üretici etiketi önceliklidir.

### Başlangıç tohum verisi (`fridge/seed_shelf_life.py`)

| Ürün (name_tr) | Saklama | Açıldıktan sonra (gün) | Kaynak | Not |
|---|---|---|---|---|
| Süt (pastörize, laktozlu) | buzdolabı | 5 | usda (muhafazakâr) | USDA ~1 hafta. Kapı rafında tutma |
| Süt (laktozsuz) | buzdolabı | 3 | estimate | Üretici talimatına bak |
| UHT süt (açılmış) | buzdolabı | 4 | estimate | Açılmamış UHT oda sıcaklığında durur |
| Yoğurt | buzdolabı | 7 | usda | USDA 7–14 gün (satın almadan itibaren); açıldıktan sonra 7 güvenli |
| Kefir | buzdolabı | 2 | usda | USDA açıldıktan sonra 1–2 gün |
| Krem peynir / labne | buzdolabı | 14 | usda | |
| Lor / süzme peynir | buzdolabı | 7 | usda | |
| Sert peynir (kaşar, çedar) | buzdolabı | 21 | usda | USDA 3–4 hafta |
| Beyaz peynir (salamurada) | buzdolabı | 7 | estimate | Salamurası içinde, salamura değişimi önemli |
| Taze/yumuşak peynir | buzdolabı | 7 | usda | USDA ~1 hafta |
| Tereyağı | buzdolabı | 30 | estimate | Oda sıcaklığında 1–2 gün (usda) |
| Yumurta (kırılmamış) | buzdolabı | 21 | usda | USDA 3–5 hafta |
| Haşlanmış yumurta | buzdolabı | 7 | usda | |
| Pişmiş et / yemek | buzdolabı | 3 | usda | USDA 3–4 gün |
| Şarküteri / dilimli et ürünleri (açılmış) | buzdolabı | 4 | usda | USDA 3–5 gün |
| Açılmış konserve / salça (cam kavanoz) | buzdolabı | 7 | estimate | Metal kutudan çıkarıp kapaklı kaba aktar |
| Reçel / bal | oda | 90 | estimate | Reçel açıldıktan sonra dolapta tercih edilir |

> Bu liste sadece başlangıçtır. Kullanıcı ileride kendi ürününü ekleyebilir (özel kural). Listeyi genişletmek ayrı bir aşama olabilir.

## 9. Sayfalar ve akışlar

1. **Giriş / Kayıt** (kayıtta: isim, e-posta, parola)
2. **Ana sayfa (Bugün):** Bugünün öğeleri, yaklaşan SKT'ler (3 gün içinde), ev durum kartları (aile seçiliyse), bugünkü ev işleri
3. **Takvim:** Aylık görünüm + gün detayı. Öğe ekle/düzenle/sil, tamamlandı işaretle. Bağlam seçici: Bireysel / Aile
4. **Buzdolabım:** Gıda listesi, durum renkleri, SKT'ye göre sıralama, ekleme formu (ad yazınca öneri çıkar), "tüketildi" işareti
5. **Ev işleri:** Haftalık görünüm, kim ne yapacak, "yaptım" butonu
6. **Ev durumu:** Bulaşık ve çamaşır kartları
7. **Aile:** Oluştur, kodla katıl, üyeleri gör, davet kodunu göster/kopyala, ayrıl
8. **Ayarlar:** İsim değiştir, parola değiştir, çıkış, hesabı sil

JavaScript sadece gerektiği yerde: takvim gezinmesi, modal formlar, öneri otomatik doldurma, davet kodu kopyalama, durum butonları. Sayfa geçişleri Django template ile sunucuda render edilir; küçük işlemler için `fetch` ile Django view'larına JSON istekleri yapılabilir (CSRF token ile).

## 10. Aşamalar

Aşağıdaki aşamaları **sırayla ve ayrı ayrı** uygula. Her aşamanın sonunda dur.

### Aşama 1: İskelet ve tasarım sistemi
- Django projesi (`callender`), uygulamalar, ayarlar (env üzerinden), `limits.py`
- Supabase Postgres bağlantısı (pooler), WhiteNoise, `vercel.json`, `requirements.txt`, `.env.example`, `.gitignore`, README (kurulum + migration + deploy)
- `theme.css`, ortak `base.html` (gezinme, yazı tipi, renkler), boş bir ana sayfa
- Güvenlik temeli (bölüm 12.1, 12.5): üretim ayarları (`DEBUG` ortamdan, `SECRET_KEY` varsayılansız), güvenlik başlıkları middleware'i, Supabase Data API'sini kapatma ve `supabase_check.sql` ile kontrol (bunu kullanıcıya adım adım yaptır)
- Bitti ölçütü: yerelde açılıyor, Supabase'e bağlanıyor, Vercel'e deploy edilebilir durumda, `/guvenlik` temiz

### Aşama 2: Kimlik doğrulama
- Özel User modeli (e-posta + isim), kayıt / giriş / çıkış sayfaları, ayarlar (isim/parola)
- Giriş zorunluluğu (login_required), güzel hata mesajları
- Güvenlik (bölüm 12.4): `AuthAttempt` ile giriş denemesi sınırı, `next` yönlendirme doğrulaması, genel hata mesajı, e-posta büyük/küçük harf duyarsız benzersizlik, kayıtta KVKK aydınlatma metni onayı (bölüm 13.2)
- Bitti ölçütü: kayıt ol, çık, tekrar gir, art arda yanlış parola sınırlanıyor

### Aşama 3: Kişisel takvim
- `CalendarItem` modeli, aylık görünüm, gün detayı, ekleme/düzenleme/silme, tamamlandı işareti
- Doğum günü/yıldönümü yıllık tekrar
- Günlük 20 öğe limiti ve karakter limitleri
- Güvenlik: `for_user()` queryset yöntemi (bölüm 12.2); başkasının öğesi 404; eşzamanlı isteklerle limit aşılamaz; yetki testleri
- Bitti ölçütü: farklı türde öğe ekleyip aylık takvimde görme, limit mesajını test etme

### Aşama 4: Aile grupları
- Aile oluştur, davet kodu, kodla katıl, 2 aile limiti, roller, ayrılma/çıkarma
- Bağlam seçici (Bireysel / Aile) ve takvimde aile öğeleri
- Güvenlik: davet kodu deneme sınırı, kodun sadece üyelere gösterilmesi, aileden çıkınca anında erişim kaybı, ayrılma/silme kuralları (bölüm 7)
- Bitti ölçütü: iki test hesabıyla aynı aileye katılıp ortak öğe görme, üçüncü hesap erişemiyor

### Aşama 5: Buzdolabı ve son kullanma
- `ShelfLifeRule` seed, `FoodItem`, ekleme formu (öneri + düzenlenebilir gün + ambalaj SKT), `use_by` hesabı, durum renkleri, "tüketildi"
- Ana sayfada yaklaşan SKT'ler
- Bitti ölçütü: süt ekle, öneri otomatik gelsin, SKT daha erkense ona göre hesaplansın

### Aşama 6: Ev işleri ve ev durumu
- `Chore`, `ChoreLog`, haftalık görünüm, "yaptım"
- `HomeStatus` bulaşık/çamaşır kartları ve adım geçişleri
- Bitti ölçütü: iki kullanıcıyla durum güncelleyip birbirinin değişikliğini görme

### Aşama 7: Cilalama ve yayın
- Boş durumlar, hata sayfaları (404/500), mobil kontrol, erişilebilirlik gözden geçirme
- Vercel'e canlı deploy, ortam değişkenleri kontrol listesi
- Basit testler: limit kuralları, `use_by` hesabı, aile yetkilendirme, davet kodu
- KVKK sayfaları, hesap silme, veri dışa aktarma (bölüm 13.2); `/guvenlik` ile tam denetim ve bulguların kapatılması

### Sonraki aşamalar (şimdilik YAPMA)
Parola sıfırlama e-postası (güvenlik açısından ilk sıradaki), e-posta doğrulama, bildirimler (SKT/etkinlik hatırlatma), ücretli paketler ve limit artırma, takvim dışa aktarma (iCal), PWA, barkod okuma ile ürün girişi, genişletilmiş gıda süre veritabanı.

## 11. Claude Code ile kullanım

Kurulum için `CLAUDE.md` (kısa kurallar), `.claude/commands/` (slash komutları), `.claude/settings.json` (izinler) ve `docs/ILERLEME.md` (aşama takibi) dosyaları kullanılır. Ayrıntılar için kökteki `KURULUM.md` dosyasına bak.

Aşama başlatmak için:

```
/asama 1
```

Aşama bitince testleri ve kontrolü yaptırmak için `/kontrol`, commit için `/kaydet`.

## 12. Güvenlik gereksinimleri

Bu bölüm her aşamanın parçasıdır. Doğrulamak için `/guvenlik` komutu (skill: `callender-security-audit`) kullanılır.

### 12.1 En kritik risk: Supabase Data API
Django tabloları `public` şemasında oluşur. Supabase, `public` şemasını varsayılan olarak otomatik REST API'siyle yayınlar; `anon` ve `authenticated` rolleri bu tablolara varsayılan yetkilidir ve `anon` anahtarı herkese açık bir anahtardır. Tablolarda RLS kapalıysa o anahtarla veri okunup yazılabilir. Uygulama Supabase'in REST API'sini hiç kullanmadığı için:

1. Supabase panelinde **Data API'yi kapat** (Project Settings > Data API > Enable Data API: kapalı). En güçlü önlem budur.
2. Ek katman olarak `scripts/supabase_check.sql` içindeki düzeltme bloğuyla tüm tablolarda RLS aç ve `anon`/`authenticated` yetkilerini geri al. Django `postgres` rolüyle bağlandığı için etkilenmez; sonrasında uygulamayı dene.
3. Her yeni migration'dan sonra kontrol sorgusunu tekrar çalıştır.
4. Supabase anon/service_role anahtarlarını bu projede **hiçbir yerde** kullanma, kopyalama, loglama.

### 12.2 Yetkilendirme (IDOR)
Nesneye `pk` ile erişen her yer kapsam filtresinden geçer:

```python
class CalendarItemQuerySet(models.QuerySet):
    def for_user(self, user):
        family_ids = FamilyMember.objects.filter(user=user).values("family_id")
        return self.filter(Q(owner=user, family__isnull=True) | Q(family_id__in=family_ids))

# view içinde, asla get_object_or_404(CalendarItem, pk=pk) tek başına değil:
item = get_object_or_404(CalendarItem.objects.for_user(request.user), pk=pk)
```
- Aynı desen `FoodItem`, `Chore`, `HomeStatus` için de uygulanır; aile detay sayfaları `get_family_or_404(user, family_id)` yardımcısını kullanır.
- Yetkisiz erişim **404** döner (403 değil), nesnenin var olduğunu sızdırmaz.
- Form/serializer'larda `owner`, `family`, `is_done`, `use_by` istemciden alınmaz; sunucuda atanır. `fields = "__all__"` yasak.

### 12.3 XSS ve girdi
- Django şablon otomatik kaçışı açık kalır; `|safe`, `mark_safe`, `autoescape off` yasak.
- JavaScript'te kullanıcı metni `textContent` ile basılır; `innerHTML` ile kullanıcı verisi **asla** basılmaz. Başlık, not, gıda adı, aile adı ve isim aile üyelerine de gösterildiği için kalıcı (stored) XSS riski gerçektir.
- Inline `<script>`, `onclick=` gibi satır içi olay yok; JS dosyaları `static/js/` altında. (CSP için gerekli, bölüm 12.8.)
- Tüm uzunluk/biçim doğrulamaları sunucuda yapılır; tarih/saat tutarlılığı (bitiş < başlangıç) doğrulanır.
- JSON isteklerinde `X-CSRFToken` başlığı gönderilir. `csrf_exempt` yasak.

### 12.4 Kimlik doğrulama ve oturum
- Giriş ve davet kodu denemeleri `AuthAttempt` ile sınırlanır (bölüm 5 ve 7).
- Giriş hatası tek mesajdır: "E-posta veya parola hatalı". Kayıtta "bu e-posta zaten kayıtlı" bilgisi sızıyor olabilir; prototipte kabul edilir, e-posta doğrulama gelince çözülür (bölüm 13.5).
- `next` parametresi `url_has_allowed_host_and_scheme` ile doğrulanır.
- Parola doğrulayıcıları açık; parola, davet kodu, token asla loglanmaz.
- Hesap silme ve parola değiştirme mevcut parolayı ister.

### 12.5 Üretim ayarları
```python
DEBUG = env.bool("DEBUG", default=False)
SECRET_KEY = env("SECRET_KEY")          # varsayılanı YOK; yoksa uygulama açılmasın
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[".vercel.app"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")   # Vercel proxy arkasında
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
DATA_UPLOAD_MAX_MEMORY_SIZE = 100_000   # 100 KB
```
- Django admin prototipte **kapalı** (URL'e eklenmez). Gerekirse sonradan, varsayılan olmayan adreste ve güçlü parolayla.
- 404/500 sayfaları sade; iç bilgi, yığın izi göstermez.

### 12.6 Limit ve yarış durumu
```python
@transaction.atomic
def create_item(user, data):
    User.objects.select_for_update().get(pk=user.pk)   # aynı kullanıcının eşzamanlı isteklerini sıraya sokar
    if CalendarItem.objects.filter(owner=user, date=data["date"]).count() >= MAX_ITEMS_PER_DAY:
        raise LimitReached("Bu güne en fazla 20 kayıt ekleyebilirsin.")
    ...
```
Aynı yöntem aile üyeliği (2 aile limiti) ve aile oluşturma günlük sınırı için de kullanılır.

### 12.7 Gizli bilgi ve ortamlar
- `.env` git'e girmez; `.env.example` yalnızca örnek/boş değer içerir. Bir anahtar yanlışlıkla commit'lenirse silmek yetmez, **anahtarı yenile**.
- Vercel ortam değişkenleri Production ve Preview için ayrı tanımlanır; Preview canlı veritabanına bağlanmaz.
- `requirements.txt` sürümleri `==` ile sabitlenir. Yeni paket eklemeden önce kullanıcıya sorulur.

### 12.8 Güvenlik başlıkları
Küçük bir middleware ile (ek paket yok):
```python
class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault("Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; script-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response
```
CSP'nin çalışması için satır içi script ve `style=""` kullanılmaz (stil sınıflarla verilir). Bir yerde zorunlu kalırsa kullanıcıya sor.

## 13. Eksikler ve iyileştirmeler

### 13.1 İlk taslaktaki tutarsızlıklar (bu belgede düzeltildi)
- `use_by` hem "hesaplanan" hem alan olarak geçiyordu; artık `save()` içinde hesaplanıp saklanıyor.
- "Günde 20" tanımı belirsizdi; bölüm 5'te netleştirildi (öğenin tarihine göre, tekrarlar sayılmaz).
- Hesap/aile/üye silinince verilerin ne olacağı tanımsızdı; bölüm 7'de ilişki kuralları eklendi.
- Giriş/davet kodu deneme sınırı ve yarış durumu (limit aşımı) yoktu; eklendi.

### 13.2 KVKK / gizlilik
Uygulama Türkiye'den kullanıcıların kişisel verisini (e-posta, isim, aile bilgisi, günlük planlar) işler. Yayına almadan önce şunlar olmalı (hukuki danışmanlık değildir, metinleri bir uzmana okut):
- Kayıtta **aydınlatma metni** bağlantısı ve onay kutusu; gizlilik/kullanım koşulları sayfası.
- `User.accepted_terms_at` alanı (onay tarihi).
- **Hesap silme:** kişisel veriyi gerçekten siler (bölüm 7 kuralları).
- **Veri dışa aktarma:** kullanıcı kendi verisini JSON olarak indirebilir.
- Gereksiz veri toplanmaz (telefon, adres, doğum tarihi istenmez; doğum günü kaydı bir takvim öğesidir).

### 13.3 Gıda önerisi ifadeleri
Arayüz "güvenle tüketebilirsin" gibi bir garanti vermez; "önerilen tüketim tarihi" der. Süresi geçen gıda için "atmayı düşün" tonu kullanılır. Şüphede at uyarısı her gıda ekranında kalır (bölüm 8).

### 13.4 İşletme notları
- Supabase planını kontrol et: ücretsiz projeler belirli süre kullanılmazsa duraklatılabilir ve yedekleme olanakları plana bağlıdır. Canlıya çıkmadan önce yedekleme durumunu doğrula.
- Hata takibi için başlangıçta Vercel logları yeter; loglara kişisel veri/gizli bilgi yazılmaz.
- Listeler için sayfalama (örn. 50 kayıt) ve takvim görünümlerinde sadece o aya ait sorgu kullanılır.

### 13.5 Önerilen sonraki özellikler (öncelik sırasıyla)
1. Parola sıfırlama + e-posta doğrulama (hesap kurtarma ve e-posta sızıntısını kapatır)
2. Hatırlatmalar/bildirimler (etkinlik saati, SKT yaklaşan gıda). Takvimin asıl faydası bu; prototipten sonra ilk iş
3. Alışveriş listesi (bitirilen gıdadan otomatik ekleme)
4. Tüketilen gıda geçmişi ve israf özeti
5. iCal dışa aktarma, PWA, barkod okuma

### 13.6 Test stratejisi (her aşamada)
Django test istemcisiyle: yetki testleri (bölüm 12.2 ve skill'deki şablon), limit testleri (21. kayıt, 3. aile), `use_by` hesabı (SKT erken ise o geçerli), davet kodu deneme sınırı, hesap silme sonrası veri durumu. Testler `python manage.py test` ile çalışır.
