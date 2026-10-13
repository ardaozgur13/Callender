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

`migrate` gerçek veritabanına yazar. Canlıya uygulamadan önce `.env` içindeki `DATABASE_URL`'in doğru projeyi gösterdiğinden emin ol.

## Vercel'e deploy

1. Repoyu GitHub'a gönder, Vercel'de "Import Project" ile bağla (Framework: Other).
2. Vercel > Settings > Environment Variables:
   - `SECRET_KEY` (yerelden farklı, uzun rastgele değer)
   - `DEBUG=False`
   - `DATABASE_URL` (canlı Supabase pooler adresi, port 6543)
   - `ALLOWED_HOSTS` (özel alan adı varsa; `.vercel.app` zaten ekli)
   - `CSRF_TRUSTED_ORIGINS` (örn. `https://callender.vercel.app`)
3. Deploy. `vercel.json` tüm istekleri `callender/wsgi.py`'ye yönlendirir.
   Statik dosyaları WhiteNoise doğrudan sunar (`WHITENOISE_USE_FINDERS`), `collectstatic`/build adımı yoktur.
4. Migration'ları yerelden canlı veritabanına uygula (yukarıya bak).

## Yapı

```
callender/      proje ayarları, urls, wsgi
core/           ortak: limits.py (tüm limitler), ana sayfa
accounts/ calendar_app/ families/ fridge/ home/   ilgili aşamalarda dolacak uygulamalar
templates/      base.html ve sayfa şablonları
static/css/     theme.css (renk değişkenleri), base.css (düzen ve bileşenler)
```
