#!/usr/bin/env bash
# Callender statik güvenlik taraması (sadece okur, hiçbir şeyi değiştirmez).
# Kullanım: bash .claude/skills/callender-security-audit/scripts/scan.sh [proje_kökü]
# Not: Bu tarama kaba bir kalıp aramasıdır. Bulgular KESİN açık değil, "incelenecek yer" demektir.
# Temiz çıkması güvenli olduğu anlamına gelmez; SKILL.md'deki elle denetim da yapılmalı.

ROOT="${1:-.}"
cd "$ROOT" || { echo "Klasör bulunamadı: $ROOT"; exit 1; }

EXCL=(--exclude-dir=.git --exclude-dir=.venv --exclude-dir=venv --exclude-dir=node_modules \
      --exclude-dir=__pycache__ --exclude-dir=staticfiles --exclude-dir=.claude --exclude-dir=docs \
      --exclude-dir=migrations --exclude-dir=.vercel)
TOTAL=0

emit() { # $1=önem $2=başlık $3=ipucu $4=satırlar
  TOTAL=$((TOTAL+1))
  echo
  echo "[$1] $2"
  [ -n "$3" ] && echo "    Neden/çözüm: $3"
  echo "$4" | head -n 15 | sed 's/^/    /'
  local n; n=$(echo "$4" | wc -l)
  [ "$n" -gt 15 ] && echo "    ... ve $((n-15)) satır daha"
}

scan() { # $1=önem $2=başlık $3=ipucu $4=regex, kalanlar: grep --include seçenekleri
  local sev="$1" title="$2" hint="$3" pat="$4"; shift 4
  local out; out=$(grep -rnIE "${EXCL[@]}" "$@" -e "$pat" . 2>/dev/null)
  [ -n "$out" ] && emit "$sev" "$title" "$hint" "$out"
  return 0
}

PY=(--include=*.py)
HTML=(--include=*.html)
JS=(--include=*.js --include=*.html)

echo "== Callender güvenlik taraması: $(pwd) =="

# --- Gizli bilgiler -------------------------------------------------------
scan KRİTİK "Koda gömülü gizli bilgi olabilir" "Gizli bilgiler sadece ortam değişkeninden okunmalı." \
  "(SECRET_KEY|PASSWORD|API_KEY|TOKEN|SERVICE_ROLE|DATABASE_URL)[A-Z_]*[[:space:]]*=[[:space:]]*['\"][^'\"]{8,}['\"]" "${PY[@]}"
scan KRİTİK "JWT/anahtar benzeri değer bulundu (Supabase anon/service_role olabilir)" "Anahtarı sil, Supabase'ten yenile." \
  "eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}" --include=*.py --include=*.js --include=*.html --include=*.json --include=*.md
scan KRİTİK "postgres bağlantı adresi koda yazılmış" "DATABASE_URL sadece .env/Vercel env'de olmalı." \
  "postgres(ql)?://[^[:space:]\"']+:[^[:space:]\"'@]+@" --include=*.py --include=*.js --include=*.json --include=*.md --include=*.txt --include=*.example
if [ -d .git ]; then
  tracked=$(git ls-files 2>/dev/null | grep -E '(^|/)\.env($|\.)' | grep -v '\.example$')
  [ -n "$tracked" ] && emit KRİTİK ".env dosyası git'e eklenmiş" "git rm --cached ile çıkar, anahtarları yenile (geçmişte kaldı)." "$tracked"
fi
if [ -f .gitignore ]; then
  grep -qE '^\.env' .gitignore || emit YÜKSEK ".gitignore içinde .env yok" ".env satırı ekle." ".gitignore"
else
  emit YÜKSEK ".gitignore dosyası yok" ".env, .venv vb. dışarıda bırakılmalı." "(yok)"
fi

# --- Django ayarları ------------------------------------------------------
scan KRİTİK "DEBUG sabit True" "DEBUG ortam değişkeninden gelmeli, varsayılanı False olmalı." "^[[:space:]]*DEBUG[[:space:]]*=[[:space:]]*True" "${PY[@]}"
scan KRİTİK "ALLOWED_HOSTS içinde '*'" "Sadece gerçek alan adları ve .vercel.app." "ALLOWED_HOSTS.*['\"]\*['\"]" "${PY[@]}"
SETTINGS=$(find . -name settings.py -not -path './.venv/*' -not -path './venv/*' -not -path './node_modules/*' 2>/dev/null | head -n1)
if [ -n "$SETTINGS" ]; then
  miss=""
  for key in SESSION_COOKIE_SECURE CSRF_COOKIE_SECURE SECURE_HSTS_SECONDS SECURE_PROXY_SSL_HEADER \
             SECURE_SSL_REDIRECT X_FRAME_OPTIONS CSRF_TRUSTED_ORIGINS SECURE_CONTENT_TYPE_NOSNIFF \
             DATA_UPLOAD_MAX_MEMORY_SIZE CONN_MAX_AGE AUTH_PASSWORD_VALIDATORS; do
    grep -q "$key" "$SETTINGS" || miss="$miss$key\n"
  done
  [ -n "$miss" ] && emit YÜKSEK "settings.py'de eksik güvenlik ayarları" "Üretimde (DEBUG=False) bu ayarlar tanımlı olmalı; ayrıntı docs/callender.md bölüm 12." "$(printf "$miss")"
else
  emit İNCELE "settings.py bulunamadı (proje henüz kurulmamış olabilir)" "" "(yok)"
fi
scan ORTA "Django admin varsayılan /admin/ adresinde" "Adresi değiştir ya da prototipte kapat; admin için güçlü parola şart." \
  "path\([\"']admin/[\"']" --include=urls.py

# --- Yetkilendirme (IDOR) -------------------------------------------------
scan YÜKSEK "Nesne doğrudan pk/id ile çekiliyor (IDOR adayı)" "Sorguyu kullanıcının/ailesinin kapsamıyla filtrele (ör. Model.objects.for_user(request.user)). Başkasının nesnesi 404 dönmeli." \
  "(get_object_or_404\([A-Za-z_.]+,[[:space:]]*(pk|id)=|\.objects\.get\([[:space:]]*(pk|id)=)" "${PY[@]}"
scan KRİTİK "csrf_exempt kullanılmış" "Çok özel bir gerekçe yoksa kaldır." "csrf_exempt" "${PY[@]}"

VIEWS=$(find . -name 'views*.py' -not -path './.venv/*' -not -path './venv/*' -not -path './node_modules/*' 2>/dev/null)
if [ -n "$VIEWS" ]; then
  res=""
  for f in $VIEWS; do
    r=$(awk -v F="$f" '
      { lines[NR]=$0 }
      /^def [A-Za-z_0-9]+\(request/ {
        ok=0
        for (i=NR-1; i>=1 && lines[i] ~ /^@/; i--)
          if (lines[i] ~ /login_required|permission_required|user_passes_test|member_required/) ok=1
        if (!ok) printf "%s:%d: %s\n", F, NR, $0
      }' "$f")
    [ -n "$r" ] && res="$res$r"$'\n'
  done
  res=$(echo "$res" | sed '/^$/d')
  [ -n "$res" ] && emit İNCELE "Giriş zorunluluğu dekoratörü görünmeyen view'lar" "Giriş/kayıt gibi herkese açık olması gereken view'lar normaldir; diğerlerine @login_required ekle." "$res"
fi
scan YÜKSEK "Sınıf tabanlı view'da LoginRequiredMixin görünmüyor" "Mixin ekle." \
  "^class [A-Za-z_]+\((View|TemplateView|ListView|DetailView|CreateView|UpdateView|DeleteView|FormView)\)" "${PY[@]}"

# --- Girdi / çıktı (XSS, mass assignment, SQL) ----------------------------
scan YÜKSEK "XSS: |safe / mark_safe / autoescape off" "Kullanıcı girdisi asla güvenli işaretlenmemeli." "(\|[[:space:]]*safe\b|mark_safe|autoescape[[:space:]]+off)" --include=*.py --include=*.html
scan YÜKSEK "XSS: innerHTML/outerHTML/insertAdjacentHTML/document.write/eval" "Kullanıcı metni için textContent kullan. Başlık/not aile üyelerine de gösterildiği için kalıcı (stored) XSS riski var." \
  "(innerHTML|outerHTML|insertAdjacentHTML|document\.write|[^a-zA-Z]eval\(|new Function\()" "${JS[@]}"
scan YÜKSEK "ModelForm'da fields='__all__' veya exclude" "Alanları tek tek yaz; owner/family gibi alanları sunucu atasın (mass assignment)." \
  "(fields[[:space:]]*=[[:space:]]*['\"]__all__['\"]|^[[:space:]]*exclude[[:space:]]*=)" "${PY[@]}"
scan ORTA "Ham SQL kullanımı" "Parametre kullan, f-string/format ile SQL kurma." "(\.raw\(|\.extra\(|RawSQL|cursor\.execute\()" "${PY[@]}"
scan YÜKSEK "Açık yönlendirme riski: next parametresi" "url_has_allowed_host_and_scheme ile doğrula." "(GET|POST)\.get\([\"']next[\"']" "${PY[@]}"
if grep -rqE "(GET|POST)\.get\([\"']next[\"']" "${EXCL[@]}" "${PY[@]}" . 2>/dev/null; then
  grep -rqE "url_has_allowed_host_and_scheme|is_safe_url" "${EXCL[@]}" "${PY[@]}" . 2>/dev/null || \
    emit YÜKSEK "next parametresi kullanılıyor ama doğrulama fonksiyonu yok" "url_has_allowed_host_and_scheme ekle." "(repo genelinde bulunamadı)"
fi

# CSRF: POST formu olup csrf_token içermeyen şablonlar
nocsrf=""
for f in $(grep -rliE "${EXCL[@]}" --include=*.html -e '<form[^>]*method=["'"'"']?post' . 2>/dev/null); do
  grep -q "csrf_token" "$f" || nocsrf="$nocsrf$f"$'\n'
done
nocsrf=$(echo "$nocsrf" | sed '/^$/d')
[ -n "$nocsrf" ] && emit KRİTİK "POST formunda {% csrf_token %} yok" "Forma {% csrf_token %} ekle." "$nocsrf"
scan ORTA "fetch/XHR ile POST var; X-CSRFToken başlığı görünmüyor olabilir" "JSON isteklerinde CSRF token başlığı gönder." "method:[[:space:]]*['\"](POST|PUT|PATCH|DELETE)['\"]" "${JS[@]}"
scan DÜŞÜK "target=\"_blank\" rel=noopener olmadan" "rel=\"noopener noreferrer\" ekle." "target=[\"']_blank[\"'](([^>])*)>" "${HTML[@]}" 
scan ORTA "Hassas bilgi loglanıyor olabilir" "Parola, davet kodu, token loglanmamalı." "(print|logger\.[a-z]+|logging\.[a-z]+)\(.*(password|parola|invite_code|token|secret)" "${PY[@]}"

# --- İş kuralları / limitler ----------------------------------------------
if [ -d core ] || [ -f core/limits.py ]; then
  [ -f core/limits.py ] || emit YÜKSEK "core/limits.py yok" "Tüm limitler tek dosyada olmalı." "core/"
fi
scan ORTA "Limit değeri koda gömülmüş olabilir (20, 2)" "Sabitleri core/limits.py'den oku." "(>=|>|<=|<|==)[[:space:]]*(20|2)[[:space:]]*(:|\)|and|or)" --include=views.py --include=services.py --include=forms.py --include=models.py
if grep -rqE "MAX_ITEMS_PER_DAY|MAX_FAMILIES_PER_USER" "${EXCL[@]}" "${PY[@]}" . 2>/dev/null; then
  grep -rqE "select_for_update|transaction\.atomic" "${EXCL[@]}" "${PY[@]}" . 2>/dev/null || \
    emit YÜKSEK "Limit kontrolü var ama transaction.atomic/select_for_update yok" "Aynı anda gelen isteklerle limit aşılabilir (race condition); kontrol ve kayıt tek transaction'da, kullanıcı satırı kilitli olmalı." "(bulunamadı)"
  grep -rqE "Throttle|throttle|rate_limit|JoinAttempt|LoginAttempt|axes" "${EXCL[@]}" "${PY[@]}" . 2>/dev/null || \
    emit YÜKSEK "Giriş/aile kodu için deneme sınırı (rate limit) görünmüyor" "Davet kodu ve parola kaba kuvvetle denenebilir; docs/callender.md bölüm 12'ye bak." "(bulunamadı)"
fi

# --- Veritabanı / Supabase ------------------------------------------------
rls=$(grep -rlIE "ENABLE ROW LEVEL SECURITY|enable row level security|lock_supabase|REVOKE ALL" --include=*.py --include=*.sql . 2>/dev/null | grep -v -E '/(\.venv|venv|node_modules)/' | head -n3)
[ -z "$rls" ] && emit YÜKSEK "Supabase Data API/RLS kilidi için bir iz bulunamadı" "Django tabloları public şemada, Supabase REST API'si üzerinden anon anahtarıyla açık kalabilir. Data API'yi kapat ve RLS aç (scripts/supabase_check.sql)." "(RLS/REVOKE içeren migration, komut veya .sql yok)"
scan KRİTİK "service_role anahtarı kullanılıyor gibi" "service_role anahtarı tarayıcıya/koda ASLA girmemeli." "service_role" "${JS[@]}" --include=*.py

# --- Bağımlılıklar --------------------------------------------------------
if [ -f requirements.txt ]; then
  unp=$(grep -vE '^[[:space:]]*(#|$)' requirements.txt | grep -vE '==' )
  [ -n "$unp" ] && emit ORTA "requirements.txt içinde sürümü sabitlenmemiş paketler" "== ile sabitle; sonra pip-audit çalıştır (kurmadan önce bana sor)." "$unp"
else
  emit İNCELE "requirements.txt bulunamadı" "" "(yok)"
fi

echo
echo "== Bitti: $TOTAL bulgu grubu. Bunlar kalıp eşleşmesidir; her birini dosyada doğrula. =="
exit 0
