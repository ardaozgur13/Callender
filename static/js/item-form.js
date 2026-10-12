// Takvim öğesi formu: küçük kolaylıklar. JS kapalıysa form yine çalışır, kurallar sunucuda.
(function () {
  var form = document.getElementById("item-form");
  if (!form) return;

  var kind = form.querySelector("[name=kind]");
  var repeat = form.querySelector("[name=repeat]");
  var allDay = form.querySelector("[name=all_day]");
  var timeFields = ["start_time", "end_time"].map(function (name) {
    var input = form.querySelector("[name=" + name + "]");
    return input ? input.closest(".field") : null;
  });

  // Doğum günü ve yıldönümü seçilince tekrar otomatik "Her yıl" olsun
  var yearlyKinds = ["birthday", "anniversary"];
  if (kind && repeat) {
    kind.addEventListener("change", function () {
      if (yearlyKinds.indexOf(kind.value) !== -1) repeat.value = "yearly";
    });
  }

  // "Tüm gün" işaretliyse saat alanlarını gizle
  function syncTimes() {
    timeFields.forEach(function (field) {
      if (field) field.hidden = allDay.checked;
    });
  }
  if (allDay) {
    allDay.addEventListener("change", syncTimes);
    syncTimes();
  }
})();
