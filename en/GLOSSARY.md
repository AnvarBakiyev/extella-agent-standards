# Glossary — Russian → English, canonical terms

Every English document under `en/` uses these terms and no synonyms. The Russian corpus is the
source of truth; `NAMING.md` defines the product names (kept in English there already).
When a term is missing here, add it here first, then use it.

## Platform objects

| Russian | English | Notes |
|---|---|---|
| агент | agent | |
| эксперт | expert | saved, versioned, executable code; never "skill", never "tool" |
| концепт | concept | agent memory unit; not "concept note" |
| правило | rule | agent-level boundary; numbered rules of this repo are `H<n>` |
| паспорт (агента) | Agent Passport / passport | declaration about an agent |
| геном | Agent Genome / genome | |
| общий ген | Shared Gene | |
| кабинет | cabinet | one-agent view (Agent Cabinet); also "cabinet" as a product for a department |
| консоль | Evolution Console / console | fleet view |
| квитанция | receipt (Evolution Receipt) | |
| способность | capability | declared in passports; `capabilities_declared.json` |
| устройство | device | never "machine" for the platform object |
| целевое устройство, таргет | target | `targets`, `device_id` |
| слушатель | listener | the on-device process that runs experts |
| ядро | core | the on-device core; not "kernel" |
| окно | window | an app's UI as a platform object; "app window" where ambiguous |
| приложение | app | "application" only in prose where "app" reads oddly |
| модуль | module | |
| тулкит | toolkit | `toolkit_*` |
| издание | edition | `editions/` |
| обработчик | handler | CSPL handler, request handler |
| контейнер | container | interpretable container; never "Docker" unless Docker is meant |
| среда (исполнения) | (execution) environment | |
| CSPL | CSPL | keep; "Container-Specific Programming Language" on first mention |
| fython | fython | keep, lowercase |
| профиль | profile | |
| ключ | key | API key, PIN key; keep "KeyVault" as is |
| токен | token | both auth tokens and model tokens — disambiguate in prose |

## Store and delivery

| Russian | English | Notes |
|---|---|---|
| магазин, витрина | store / storefront | "store" for the marketplace, "storefront" for the listing surface |
| листинг | listing | |
| публикация, опубликовать | publish, publication | Publish button stays "Publish" |
| предрелиз | pre-release | hyphenated |
| релиз, выпуск | release | |
| версия | version | |
| покупка | purchase | "buyer" for покупатель |
| установка, установщик | install, installer | `install.py`, `installer_expert` |
| доставка | delivery | in the GTM sense: getting the product onto someone else's machine |
| архив | archive | the zip payload |

## Method and quality

| Russian | English | Notes |
|---|---|---|
| гейт | gate | CI checks `tools/check_*.py`; "All gates" = `Все гейты` |
| канон | canon | canonical rule set; "canonical" as adjective |
| самопроверка | self-check | `selfcheck.json` stays as filename |
| доказательство | evidence | `evidence/` |
| проба | probe | a lightweight check run |
| стенд | test stand | a clean-machine setup used for verification |
| заглушка | stub | |
| симптом | symptom | `SYMPTOMS.md` |
| инцидент | incident | |
| маршрут (запуска) | route / routing | execution route to a device |
| конвейер | pipeline | |
| доктор | doctor | `extella_doctor.py` |
| декларация | declaration | |
| владелец | owner | |
| мастер (установки) | wizard | UI wizard; not "master" |
| чистая машина | clean machine | a machine where Extella was never installed |
| проверялка | checker | a small script that checks one thing; a gate is a checker wired into CI |
| отказ (состояние интерфейса) | refusal | the product declining and saying why; never "error" when the source says отказ |
| разъехаться (о двух копиях) | drift apart | |
| опровергнутое правило | refuted rule | a rule shown wrong by an incident |
| лазейка | loophole | |
| контур / периметр клиента | client's perimeter | the client's own machines and network |
| маршрут по задачам (в README) | task-based route | reading path through the corpus; not the execution "route" |
| прошивается / флешится целиком | flashed as a whole | firmware metaphor, keep it |
| полка (модулей) | shelf | `build_modules_shelf` |
| белое окно | white window | the blank-window failure state of an app; keep literal, it is a named symptom |

## Rules of use

- Product names from `NAMING.md` stay exactly as written there (Extella Evolution, Agent Passport, Agent Cabinet, Evolution Console, Evolution Lab, Evolution Loop, Evolution Receipt, Shared Gene).
- Rule identifiers `H<n>` and gate script names are never translated.
- File names, paths, JSON keys, YAML keys and code stay as in the Russian original, including Russian identifiers inside code. Only prose and comments explaining prose are translated; comments inside code samples are translated only when the sample is illustrative, not when it is a verbatim file.
- Dates: `18.09.2026` → `18 Sep 2026`.
- Money: `₸` stays `₸`; "tenge" on first mention in a document.
- "ЗАЧЕМ." paragraphs at the top of gate docstrings become "WHY." — the incident stays; that is the point of this corpus.
