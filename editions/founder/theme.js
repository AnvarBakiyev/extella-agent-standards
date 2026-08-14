// Тема издания для основателя: спокойная, без цвета ради цвета.
(function () {
  var ИЗДАНИЕ = "edition-founder";
  if (window["__тема_" + ИЗДАНИЕ]) return;
  window["__тема_" + ИЗДАНИЕ] = true;

  var СВОИ = [                                    // listing_id приложений издания
    "a1dd57d1-5322-4e34-b38a-a23cdc99535d",       // Решения
  ];
  var это_оболочка = location.pathname.indexOf("/app-page/") !== 0;
  var это_своё = СВОИ.some(function (id) { return location.pathname.indexOf(id) >= 0; });
  if (!это_оболочка && !это_своё) return;         // чужое окно — молчим

  var стиль = document.createElement("style");
  стиль.setAttribute("data-издание", ИЗДАНИЕ);
  // Имена переменных оболочки ОС — свои (--p акцент, --ph при наведении).
  // Наш --a оболочка не знает, поэтому тема на --a не красила бы ничего.
  стиль.textContent = это_оболочка
    ? ":root{--p:#2F6B66;--ph:#24544F;}"
    : ":root{--a:#2F6B66;}";
  document.head.appendChild(стиль);
})();
