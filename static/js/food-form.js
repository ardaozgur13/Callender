// Buzdolabı ürün formu: ad bir öneriyle eşleşince gün ve saklama yerini doldurur.
// JS kapalıysa sunucu yine eşleştirir ve boş günü kuraldan doldurur.
(function () {
  var form = document.getElementById("food-form");
  var dataTag = document.getElementById("rules-data");
  if (!form || !dataTag) return;

  var rules = JSON.parse(dataTag.textContent);
  var name = form.querySelector("[name=name]");
  var days = form.querySelector("[name=suggested_days]");
  var storage = form.querySelector("[name=storage]");
  var hint = document.getElementById("rule-hint");
  var sourceLabels = { usda: "USDA kaynağında doğrulandı", estimate: "muhafazakâr tahmin, ürün etiketine bak" };
  var lastAutoDays = null;

  function findRule(value) {
    var wanted = value.trim().toLocaleLowerCase("tr");
    for (var i = 0; i < rules.length; i++) {
      if (rules[i].name.toLocaleLowerCase("tr") === wanted) return rules[i];
    }
    return null;
  }

  function apply() {
    var rule = findRule(name.value);
    if (!rule) {
      hint.hidden = true;
      return;
    }
    // Kullanıcı günü elle değiştirdiyse üzerine yazma
    if (days.value === "" || days.value === String(lastAutoDays)) {
      days.value = rule.days;
      lastAutoDays = rule.days;
    }
    if (storage) storage.value = rule.storage;
    hint.textContent = "Öneri: açıldıktan sonra " + rule.days + " gün (" + sourceLabels[rule.source] + ")" +
      (rule.note ? ". " + rule.note : "");
    hint.hidden = false;
  }

  name.addEventListener("input", apply);
  name.addEventListener("change", apply);
  if (name.value) {
    lastAutoDays = days.value === "" ? null : Number(days.value);
    apply();
  }
})();
