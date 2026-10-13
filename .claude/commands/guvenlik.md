---
description: Callender güvenlik denetimi (callender-security-audit skill ile)
---

callender-security-audit skill'ini kullanarak projeyi denetle. Önce scripts/scan.sh taramasını çalıştır ve bulguları ilgili dosyada doğrula. Sonra skill içindeki kontrol listesini (yetki/IDOR, XSS, kimlik doğrulama, üretim ayarları, Supabase, limitler, KVKK) şu ana kadar yazılmış koda göre yürüt. Supabase için scripts/supabase_check.sql dosyasını bana ver, çıktısını yapıştırayım.

Raporu önem sırasına göre ver ve "henüz yazılmadığı için denetlenemeyenler"i ayrı listele. Hiçbir şeyi ben onaylamadan düzeltme.
