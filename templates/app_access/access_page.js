/* Модуль допуска, сторона страницы Extella OS: сессия по app_token, мост к серверу,
   карточка администратора «Кто видит данные» (Дать доступ / Отозвать).
   Откуда: «Учёт клейм НацЭкс», os-app/index.html (25.09.2026). Подключение — README.md.

   Требует в странице: var APP_TOKEN = '{{app_token}}' (подставляет ОС), var SERVER = 'https://…',
   элементы #whoLine, #accessCard (hidden), #accessList, #accessRefresh, функции $(id), esc(s), toast(msg).
   ЗАПРЕЩЕНО: window.prompt/confirm/alert — в окне ОС страница живёт в cross-origin iframe, где
   браузер возвращает prompt→null и confirm→false молча (воспроизведено 25.09.2026): кнопка
   «Дать доступ» с prompt не делала ничего. Все подтверждения — встроенные (форма, двухшаговая кнопка). */

var SESSION_HEADER = 'X-App-Session';
var SESSION = '';
var ME = null;

async function ensureSession(force){
  if (SESSION && !force) return {ok:true};
  var ctl = new AbortController();
  var tm = setTimeout(function(){ ctl.abort(); }, 40000);
  try {
    var r = await fetch(SERVER+'/api/session', { method:'POST',
      headers:{'Content-Type':'application/json'}, body:JSON.stringify({app_token: APP_TOKEN}), signal:ctl.signal });
    var d = null;
    try { d = await r.json(); } catch(e){ d = null; }
    if (r.status===200 && d && d.session){
      SESSION = d.session; ME = d;
      $('whoLine').textContent = (d.name || d.email || '') + (d.role==='admin' ? ' · администратор' : '');
      $('accessCard').hidden = (d.role !== 'admin');
      if (d.role === 'admin') loadUsers();
      return {ok:true};
    }
    if (r.status===403 && d && d.no_role){
      return {ok:false, noRole:true, error:'Доступ к данным ещё не выдан. Ваш адрес '+(d.email||'')+' передан администратору — после подтверждения нажмите «Обновить данные».'};
    }
    if (r.status===401) return {ok:false, error:'Extella не подтвердила ключ приложения. Закройте и откройте приложение из Extella.'};
    if (r.status===502) return {ok:false, error:'Сервер не смог спросить Extella, кто вы: '+esc((d&&d.reason)||'платформа недоступна')+'. Попробуйте через минуту.'};
    return {ok:false, error:'Сервер ответил '+r.status+(d&&d.reason?(': '+d.reason):'')};
  } catch(e){
    return {ok:false, error:(e && e.name==='AbortError') ? 'Сервер не отвечает 40 секунд.' : 'Сервер недоступен: '+String(e && e.message || e)};
  } finally { clearTimeout(tm); }
}

/* Один мост для всех вызовов: 401 → одна попытка пересоздать сессию, 403 → «только администратор». */
async function bridge(method, args, _retry){
  var s = await ensureSession(false);
  if (!s.ok) return s;
  var ctl = new AbortController();
  var tm = setTimeout(function(){ ctl.abort(); }, 120000);
  try {
    var headers = {'Content-Type':'application/json'}; headers[SESSION_HEADER] = SESSION;
    var r = await fetch(SERVER+'/api/call', { method:'POST', headers: headers,
      body:JSON.stringify({method: method, args: args||{}}), signal:ctl.signal });
    if (r.status===401){
      SESSION = '';
      if (!_retry){ var s2 = await ensureSession(true); if (!s2.ok) return s2; return bridge(method, args, true); }
      return {ok:false, error:'Сессия не действует. Закройте и откройте приложение из Extella.'};
    }
    if (r.status===403) return {ok:false, error:'Это действие доступно только администратору.'};
    if (r.status===502||r.status===503||r.status===504) return {ok:false, error:'Сервер временно недоступен ('+r.status+'). Попробуйте через минуту.'};
    var d = await r.json();
    if (!d) return {ok:false, error:'Пустой ответ сервера.'};
    if (d.status==='error') return {ok:false, error:(d.reason||'Сервер ответил ошибкой без причины.')};
    if (typeof d.result !== 'object' || d.result === null) return {ok:false, error:'Сервер вернул не данные.'};
    return {ok:true, data:d.result};
  } catch(e){
    return {ok:false, error: (e && e.name==='AbortError') ? 'Ответа нет 2 минуты — сервер молчит.' : 'Сервер недоступен: '+String(e && e.message || e)};
  } finally { clearTimeout(tm); }
}

/* ---------- карточка администратора: кто просит, кто допущен ---------- */
async function loadUsers(){
  var r = await bridge('list_users', {});
  var box = $('accessList');
  if (!r.ok){ box.innerHTML = '<div class="li"><div class="txt"><div class="t">'+esc(r.error)+'</div></div></div>'; return; }
  var d = r.data || {}, h = '';
  Object.keys(d.pending || {}).forEach(function(u){
    var p = d.pending[u];
    h += '<div class="li"><div class="txt"><div class="t"><span class="dot y"></span>'+esc(p.email||u)+'</div>'+
      '<div class="d">просит доступ · '+esc(p.last_seen||'')+'</div>'+
      '<div class="grant-form" id="gf_'+esc(u)+'" hidden style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">'+
      '<input class="grant-name" data-user="'+esc(u)+'" value="'+esc(p.email||'')+'" aria-label="Имя сотрудника">'+
      '<button class="btn" data-grant-ok="'+esc(u)+'" data-email="'+esc(p.email||'')+'">Подтвердить</button></div></div>'+
      '<button class="btn link" data-grant="'+esc(u)+'">Дать доступ</button></div>';
  });
  Object.keys(d.users || {}).forEach(function(u){
    var p = d.users[u];
    h += '<div class="li"><div class="txt"><div class="t"><span class="dot g"></span>'+esc(p.name||p.email||u)+
      (p.role==='admin' ? ' <span class="pill g">администратор</span>' : '')+'</div>'+
      '<div class="d">'+esc(p.email||'')+' · с '+esc(p.granted||'')+'</div></div>'+
      (ME && u===ME.user ? '' : '<button class="btn link" data-revoke="'+esc(u)+'">Отозвать</button>')+'</div>';
  });
  box.innerHTML = h || '<div class="li"><div class="txt"><div class="t">Пока только вы</div></div></div>';
  /* «Дать доступ» — встроенная форма с именем вместо prompt */
  Array.prototype.forEach.call(document.querySelectorAll('[data-grant]'), function(b){
    b.onclick = function(){
      var f = document.getElementById('gf_'+b.getAttribute('data-grant'));
      if (f){ f.hidden = false; var inp = f.querySelector('input'); if (inp) inp.focus(); }
      b.hidden = true;
    };
  });
  Array.prototype.forEach.call(document.querySelectorAll('[data-grant-ok]'), function(b){
    b.onclick = async function(){
      var u = b.getAttribute('data-grant-ok');
      var inp = document.querySelector('.grant-name[data-user="'+u+'"]');
      var name = (inp && inp.value.trim()) || b.getAttribute('data-email') || u;
      b.disabled = true; b.textContent = 'Выдаю…';
      var g = await bridge('grant_user', {user: u, name: name, email: b.getAttribute('data-email')});
      toast(g.ok ? 'Доступ выдан: '+name : g.error); loadUsers();
    };
  });
  /* «Отозвать» — двухшаговая кнопка вместо confirm: первое нажатие «Точно отозвать?», 6 секунд на второе */
  Array.prototype.forEach.call(document.querySelectorAll('[data-revoke]'), function(b){
    b.onclick = async function(){
      if (b.getAttribute('data-armed') !== '1'){
        b.setAttribute('data-armed', '1'); b.textContent = 'Точно отозвать?'; b.style.color = 'var(--err)';
        setTimeout(function(){ b.setAttribute('data-armed', '0'); b.textContent = 'Отозвать'; b.style.color = ''; }, 6000);
        return;
      }
      b.disabled = true; b.textContent = 'Отзываю…';
      var g = await bridge('revoke_user', {user: b.getAttribute('data-revoke')});
      toast(g.ok ? 'Доступ отозван' : g.error); loadUsers();
    };
  });
}
