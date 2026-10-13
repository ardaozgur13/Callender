# Callender

Kişisel ve aile odaklı takvim uygulaması (prototip). Django + Supabase PostgreSQL + Vercel.
Proje belgesi: `docs/callender.md` · Aşama durumu: `docs/ILERLEME.md`.

## Yerel kurulum

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
```

`.env` içini doldur:

- `SECRET_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(50))"` çıktısı
- `DEBUG=True`
- `DATABASE_URL`: Supabase > Project Settings > Database > **Connection pooling**, **Transaction mode** (port **6543**) adresi, sonuna `?sslmode=require`

Geliştirme ve canlı için ayrı iki Supabase projesi önerilir.

```bash
python manage.py check                       # yapılandırma kontrolü (veritabanına bağlanmaz)
python manage.py check --database default    # Supabase bağlantısını da dener
python manage.py test
python manage.py runserver                   # http://127.0.0.1:8000
```

Testler Supabase'te geçici bir `test_callender` veritabanı kullanır ve sonunda siler. Supabase pooler bu veritabanına açık bir bağlantı tuttuğu için silme `DROP DATABASE … WITH (FORCE)` ile yapılır (`core/test_runner.py`). Asıl `postgres` veritabanına dokunulmaz. Uzak veritabanı yüzünden testler birkaç dakika sürer; hızlandırmak için `--keepdb` kullanılabilir.

## Migration

Migration'lar Vercel build'inde **çalışmaz**; yerelden, hedef Supabase veritabanına karşı elle çalıştırılır:

```bash
python manage.py makemigrations
python manage.py migrate
```

`migrate` gerçek veritabanına yazar. Hangi veritabanına yazdığından emin ol:

- **Geliştirme veritabanı:** `.env` içindeki `DATABASE_URL` → `python manage.py migrate`
- **Canlı veritabanı:** canlı adresi git'e girmeyen ayrı bir dosyada tut (`.env.production`, `.gitignore` kapsamında) ve sadece o komut için göster. Böylece şifre terminal geçmişine yazılmaz:

  ```powershell
  $env:CALLENDER_ENV_FILE = ".env.production"; python manage.py migrate; Remove-Item Env:CALLENDER_ENV_FILE
  ```

Her `migrate` sonunda `core/db.py` yeni tablolarda RLS'yi otomatik açar.

## Canlıya çıkış kontrol listesi

**Supabase (canlı proje)**
- [ ] Canlı için geliştirmeden **ayrı** bir Supabase projesi var (bölge: Frankfurt).
- [ ] Project Settings → Data API → **Enable Data API: kapalı**.
- [ ] `supabase_check.sql`'deki 1. sorgu: tüm tablolarda `rowsecurity = true`; 2. sorgu: **boş** sonuç. Boş değilse aynı dosyadaki DÜZELTME bloğu çalıştırılır.
- [ ] Veritabanı şifresi sadece harf ve rakam (URL'yi bozan `@ ? # / : %` yok) ve yalnızca `.env.production` + Vercel'de duruyor.
- [ ] Yedekleme: plandaki yedekleme durumu kontrol edildi (ücretsiz planda proje 7 gün kullanılmazsa duraklatılabilir, yedek olanakları sınırlıdır).

**Vercel**
- [ ] Proje GitHub deposundan içe aktarıldı (Framework Preset: Other). `vercel.json` tüm istekleri `callender/wsgi.py`'ye yönlendirir; Python sürümü `.python-version` (3.12).
- [ ] Environment Variables, **Production** ortamı:
  - `SECRET_KEY`: yerelden farklı, yeni üretilmiş uzun değer
  - `DEBUG`: `False`
  - `DATABASE_URL`: **canlı** Supabase Transaction pooler adresi (port 6543, `?sslmode=require`)
  - `CSRF_TRUSTED_ORIGINS`: `https://<proje>.vercel.app` (özel alan adı varsa o da, virgülle)
  - `ALLOWED_HOSTS`: sadece özel alan adı varsa (`.vercel.app` kodda zaten var)
- [ ] **Preview** ortamı: kendi `SECRET_KEY`'i ve **geliştirme** veritabanının `DATABASE_URL`'i. Preview asla canlı veritabanına bağlanmaz.
- [ ] Development ortamı Vercel'de boş bırakılabilir (yerelde `.env` kullanılıyor).

**Yayından önce / hemen sonra**
- [ ] `python manage.py test` yeşil, `/guvenlik` raporunda açık YÜKSEK/KRİTİK yok.
- [ ] Canlı veritabanına `migrate` (yukarıdaki komut).
- [ ] Hukuki metinlerdeki `[köşeli parantez]` alanları dolduruldu, metinler bir uzmana okutuldu.
- [ ] Canlı adreste: kayıt ol → çıkış → giriş; tarayıcı geliştirici araçlarında yanıt başlıklarında `Content-Security-Policy`, `Strict-Transport-Security` var; `http://` adresi `https://`'e yönleniyor; `/admin/` 404.
- [ ] Vercel → Logs'ta hata yok; loglarda e-posta/parola/davet kodu görünmüyor.

## Yapı

```
callender/      proje ayarları, urls, wsgi
core/           limits.py (tüm limitler), Bugün sayfası, hukuki sayfalar, deneme sınırı (AuthAttempt),
                güvenlik başlıkları middleware'i, RLS kancası (db.py), test çalıştırıcısı
accounts/       kullanıcı, kayıt/giriş, ayarlar, hesap silme, veri dışa aktarma
calendar_app/   takvim (aylık/gün görünümü, yıllık tekrar, günlük limit)
families/       aileler, davet kodu, bağlam seçici, aile içi yetki (permissions.py)
fridge/         buzdolabı, raf ömrü önerileri, SKT
home/           ev işleri, bulaşık/çamaşır durumu
templates/      base.html ve sayfa şablonları (satır içi JS yok; CSP)
static/css/     theme.css (renk değişkenleri), base.css (düzen ve bileşenler)
static/js/      app.js (onaylar, bağlam seçici, kopyalama), form yardımcıları
```
