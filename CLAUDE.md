# Callender

Kişisel + aile odaklı takvim uygulaması (doğum günü/yıldönümü, görevler, buzdolabı SKT takibi, ev işleri, aile grupları). Şu an **prototip** aşamasında; sade tut.

Tam proje belgesi: `docs/callender.md` (model, limitler, sayfalar, aşamalar). Bir aşamaya başlamadan önce ilgili bölümleri oku. Aşama durumu: `docs/ILERLEME.md`.

## Teknoloji (sabit)
- Python 3.11+, Django (LTS), Django ORM
- Veritabanı: Supabase PostgreSQL (sadece Postgres; Supabase auth/JS SDK yok)
- Deploy: Vercel. Statik: WhiteNoise
- Frontend: aynı repoda Django template + saf HTML/CSS/JS. Framework, Tailwind, build adımı YOK
- Yeni bağımlılık eklemeden önce sor

## Komutlar
- Çalıştır: `python manage.py runserver`
- Kontrol: `python manage.py check`
- Test: `python manage.py test`
- Migration üret: `python manage.py makemigrations`
- Migration uygula: `python manage.py migrate` (**sadece kullanıcı onayıyla**, bkz. aşağı)

## Kurallar
- Aşama aşama ilerle. Kullanıcı `/asama N` demeden sonraki aşamaya geçme. Aşama sonunda `docs/ILERLEME.md`'yi güncelle, özet ver, dur.
- Kod yorumları ve arayüz metinleri Türkçe; model, değişken, fonksiyon adları İngilizce.
- Tüm limitler ve sabitler tek yerde: `core/limits.py`. Kod içine sayı gömme.
- `.env`, SECRET_KEY, Supabase şifresi koda/commit'e girmez. Sadece ortam değişkeni. `.env.example` güncel tutulur.
- `migrate` komutunu kendi başına çalıştırma: bu canlı Supabase'e yazar. Komutu kullanıcıya ver.
- Her view'da yetki kontrolü: kullanıcı sadece kendi verisini ve üyesi olduğu ailelerin verisini görür.
- Limitler (günlük 20 öğe, 2 aile, karakter sınırları) sunucu tarafında zorlanır.
- Vercel serverless: SQLite ve kalıcı dosya yazma yok. Supabase pooler (port 6543) için `CONN_MAX_AGE=0`, `DISABLE_SERVER_SIDE_CURSORS=True`.
- Saat dilimi `Europe/Istanbul`, dil `tr`.

## Tasarım
Tozsal mat pastel (kremsi mavi, pembe, sarı, çayır yeşili), yuvarlak köşe, hafif gölge, mobil öncelikli. Renkler CSS değişkeni olarak `static/css/theme.css` içinde; palet `docs/callender.md` bölüm 3. Renk kodunu bileşenlere gömme, değişken kullan.

## Çalışma tarzı
- Önce kısa plan, sonra uygula. Büyük değişikliklerden önce neyi değiştireceğini söyle.
- Her aşamadan sonra testleri/`check`'i çalıştır, sonucu özetle.
- Emin olmadığın üründe/gıda verisinde uydurma; `docs/callender.md` bölüm 8'deki kaynak etiketlerine (`usda`/`estimate`) uy.
