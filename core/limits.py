"""
Callender limitleri ve sabitleri. Tek kaynak burasıdır; kodun içine sayı gömme.
İleride paket/fiyatlandırma sistemi eklenince değerler buradan değiştirilir.
(bkz. docs/callender.md bölüm 5)
"""

# Üyelik ve kapasite limitleri
MAX_FAMILIES_PER_USER = 2           # Bir kullanıcının üye olabileceği aile sayısı (kurucu da sayılır)
MAX_ITEMS_PER_DAY = 20              # Bir kullanıcının bir takvim gününe ekleyebileceği öğe toplamı
MAX_FAMILY_MEMBERS = 8              # Bir ailedeki üye sayısı
MAX_FRIDGE_ITEMS_PER_FAMILY = 150   # Aktif (tüketilmemiş) gıda kaydı
MAX_CHORES_PER_FAMILY = 50          # Aktif ev işi tanımı

# Karakter sınırları
TITLE_MAX = 80                      # Etkinlik/görev/iş başlığı
DESCRIPTION_MAX = 500               # Açıklama / not
FOOD_NAME_MAX = 60                  # Gıda adı
FOOD_NOTE_MAX = 200                 # Gıda notu
FAMILY_NAME_MAX = 40                # Aile adı
USER_NAME_MAX = 40                  # Kullanıcı görünen adı
USER_NAME_MIN = 2                   # Kullanıcı görünen adı en az
PASSWORD_MIN = 8                    # Parola en az

# Aile davet kodu: karışabilen 0/O/1/I karakterleri hariç
INVITE_CODE_LENGTH = 8
INVITE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# Yaklaşan SKT uyarısı (gün)
EXPIRY_WARNING_DAYS = 3
