---
description: Callender'ın belirtilen aşamasını uygular (örn. /asama 1)
argument-hint: <aşama numarası>
---

Aşama $ARGUMENTS'ı uygula.

1. `docs/ILERLEME.md` dosyasını oku; önceki aşamalar ✅ değilse dur ve bana söyle.
2. `docs/callender.md` içinde "## 10. Aşamalar" bölümündeki bu aşamayı ve ilgili olduğu diğer bölümleri (veri modeli, limitler, tasarım, sayfalar) oku.
3. Kısa bir plan çıkar (hangi dosyalar oluşacak/değişecek) ve uygulamaya geç. Belirsiz bir nokta varsa tahmin etmek yerine tek bir net soru sor.
4. Sadece bu aşamayı yap. Sonraki aşamalara taşma, ek bağımlılık ekleme.
5. `python manage.py check` ve varsa testleri çalıştır. `docs/callender.md` bölüm 12'deki bu aşamaya ait güvenlik maddelerini uyguladığından emin ol, `bash .claude/skills/callender-security-audit/scripts/scan.sh` taramasını çalıştırıp çıkan bulguları özetle. `migrate` komutunu çalıştırma; gerekiyorsa komutu bana ver.
6. `docs/ILERLEME.md` içinde bu aşamayı 🟨 yap ve alınan kararları nota ekle (✅ işaretini ben onaylayınca koyacağız).
7. Özetle: ne yapıldı, nasıl çalıştırılır, nasıl test edilir. Sonra dur ve onayımı bekle.
