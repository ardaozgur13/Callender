# Callender: Claude Code ile başlangıç

## 1. Klasörü hazırla
```bash
mkdir callender && cd callender
git init
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
```
Bu pakettekilerin hepsini (gizli klasör `.claude/` dahil) proje köküne kopyala:

```
callender/
├── CLAUDE.md
├── KURULUM.md
├── .gitignore
├── .claude/
│   ├── settings.json
│   └── commands/ (asama.md, kontrol.md, kaydet.md)
└── docs/
    ├── callender.md
    └── ILERLEME.md
```

## 2. Claude Code'u aç
```bash
claude
```
İçeride `/memory` ile `CLAUDE.md`'nin yüklendiğini, `/help` ile `/asama`, `/kontrol`, `/kaydet` komutlarının göründüğünü doğrula.

## 3. Çalışma döngüsü
1. `/asama 1` yaz. İstersen önce Shift+Tab ile plan moduna geçip planı okuyabilirsin.
2. Bitince uygulamayı çalıştır, elle dene.
3. `/kontrol` ile gözden geçirt, bulguları düzelttir.
4. `/kaydet` ile commit.
5. `docs/ILERLEME.md`'de aşamayı ✅ yap, `/clear` ile temiz oturum aç, sonraki aşamaya geç.

Her aşamayı ayrı oturumda yapmak bağlamı temiz tutar; belge dosyaları bilgiyi zaten taşıyor.

## 4. Supabase ve güvenlik
- Supabase bağlantı adresini (pooler, port 6543) `.env` içine `DATABASE_URL` olarak yaz. `.env` commit'lenmez; `settings.json` Claude'un bu dosyayı okumasını da engeller.
- Geliştirme ve canlı için **ayrı iki Supabase projesi** kullanmanı öneririm. Aksi halde yerelde denediğin her şey canlı veriyi etkiler.
- `migrate` komutu Claude Code'da her seferinde senden onay ister, bu bilerek böyle.
- `git push`'u da sen yaparsın; Vercel'e GitHub bağlayınca push canlıya gider.
