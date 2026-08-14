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
  стиль.textContent = ":root{--a:#2F6B66;}";      // петроль вместо золота: рабочее, не праздничное
  document.head.appendChild(стиль);
})();
