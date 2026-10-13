// Callender ortak davranışları. Satır içi JS (onsubmit=, onchange=, <script>) kullanılmaz;
// İçerik Güvenlik Politikası (CSP) "script-src 'self'" ile sadece bu tür dosyalara izin verir.
(function () {
  // <form data-confirm="Mesaj"> : göndermeden önce onay iste
  document.addEventListener("submit", function (event) {
    var message = event.target.getAttribute("data-confirm");
    if (message && !window.confirm(message)) event.preventDefault();
  });

  // <select data-autosubmit> : seçim değişince formu gönder (bağlam seçici)
  document.addEventListener("change", function (event) {
    if (event.target.matches("select[data-autosubmit]")) event.target.form.submit();
  });

  // <button data-copy="#hedef"> : hedefin metnini panoya kopyala (davet kodu)
  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-copy]");
    if (!button) return;
    var target = document.querySelector(button.getAttribute("data-copy"));
    if (!target) return;
    var original = button.textContent;
    var done = function () {
      button.textContent = "Kopyalandı ✓";
      setTimeout(function () { button.textContent = original; }, 2000);
    };
    if (navigator.clipboard) {
      navigator.clipboard.writeText(target.textContent.trim()).then(done);
    } else {
      done();
    }
  });
})();
