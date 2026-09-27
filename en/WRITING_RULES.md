<!-- source: WRITING_RULES.md sha256:3384a4e25aec42a84477798550d10565a1c7f698e154dce58efd510b1084d346 -->

# The instruction-language rule

The author of this rule is a designer. It appeared on 18 Aug 2026, when the "Development
on Extella" guide had to be rewritten entirely: the text was clear to the people who wrote
it and unclear to the people it was written for.

The rule applies to everything read by a person outside the team: guides, product
descriptions in the store, interface text, error messages, letters to clients. Internal
comments in code do not fall under it.

**The boundary is at rule four.** A measurement record is not an instruction. In a line
like "the measurement was taken before this," who measured it matters: authorship is part
of the fact, and erasing it for the sake of form is not allowed. That's why engineering
records — `DEPLOY_REQUIREMENTS.md`, `AGENT_BUILD_GUIDE.md`, breakage post-mortems — are
checked with the key `--без-местоимений` (pronoun-free): jargon and terms are caught,
pronouns are not. Text for the buyer (the store guide, `README.md`, interface copy) is
checked in full.

All the examples below are real "before — after" pairs from that same guide.

## 1. A sentence has a subject and a predicate

A fragment is clear to its author, because the author remembers what was left unsaid. The
reader does not remember it.

| Before | After |
|---|---|
| Проверять доступность именем у конкретного агента, а не по флагу. (Check availability by name on the specific agent, not by a flag.) | Проверяй доступность Expert по имени именно у того агента, который будет им пользоваться. Не полагайся только на флаг или общий список. (Check the Expert's availability by name specifically on the agent that will use it. Don't rely only on a flag or a general list.) |
| Пустые права = продукт молча мёртв. (Empty rights = the product is silently dead.) | Если не указать права, продукт не сможет работать. Страница откроется, но каждый вызов агента получит отказ. (If rights aren't specified, the product won't be able to work. The page will open, but every call to the agent will get a refusal.) |

## 2. A term is explained where it first appears

The reader came for an instruction, not for a dictionary. A definition takes one line and
removes half the questions.

| Before | After |
|---|---|
| Скоуп решает всё. У каждого агента свой мир. (Scope decides everything. Every agent has its own world.) | Скоуп — это набор объектов, доступных конкретному агенту. У каждого агента он свой. (A scope is the set of objects available to a specific agent. Every agent has its own.) |
| Листинг собирается из независимых частей. (A listing is assembled from independent parts.) | Листинг — это карточка продукта в магазине. Он собирается из независимых частей. (A listing is the product's card in the store. It is assembled from independent parts.) |

## 3. Internal jargon does not go outside

Professional jargon and team in-jokes save time inside the team and cost time outside it.
A section heading is text too.

| Before | After |
|---|---|
| Грабли, на которые наступают все (The rakes everyone steps on) | Шесть вещей, из-за которых продукт ломается не у тебя, а у клиента (Six things that break the product not at your place, but at the client's) |
| Пушь сразу, а не в конце. (Push right away, not at the end.) | Отправляй изменения в удалённый репозиторий сразу, а не в конце. (Send changes to the remote repository right away, not at the end.) |
| Эксперт обязан ехать с кодом. (The Expert must travel with the code.) | Если код вызывает Expert, Expert должен поставляться вместе с кодом. (If the code calls an Expert, the Expert must ship together with the code.) |

## 4. "We" and "we have" do not appear in an instruction

The reader is not part of the team. They need the fact, not the team's story about that
fact.

| Before | After |
|---|---|
| У нас уже приезжал продукт, умевший снести агента покупателя. (We've already had a product ship that could wipe out the buyer's agent.) | Уже был продукт, который мог удалить агента покупателя. (There has already been a product that could delete the buyer's agent.) |
| Почти каждое правило здесь куплено настоящей поломкой. (Almost every rule here was bought with a real breakage of ours.) | Почти каждое из них появилось после реальной поломки. (Almost every one of them appeared after a real breakage.) |

## 5. A judgment is replaced by a fact

"Cheap," "honest," "correct" are the author's judgments. The reader wants to know what will
happen.

| Before | After |
|---|---|
| Эти шесть правил дешёвые. (These six rules are cheap.) | Эти шесть правил несложно соблюдать. Но если их нарушить, быстрая разработка станет опасной для клиента. (These six rules aren't hard to follow. But breaking them makes fast development dangerous for the client.) |
| Честный отказ дешевле молчания. (An honest refusal is cheaper than silence.) | Деньги списываются после установки, поэтому явная ошибка лучше, чем молчаливое зависание. (Money is charged after install, so an explicit error is better than a silent hang.) |

## 6. A quantity is stated in full

Abbreviating it saves three characters and makes the reader reconstruct the unit of
measurement.

| Before | After |
|---|---|
| Вызов со страницы до устройства — 13–17 с. (Page-to-device call — 13–17 s.) | Вызов со страницы к устройству занимает от тринадцати до семнадцати секунд. (A call from the page to the device takes from thirteen to seventeen seconds.) |
| Прод — двадцать одна. (Prod — twenty-one.) | Вторая стадия — продакшен: продукт доступен любому покупателю. Для этой стадии обязательна двадцать одна проверка. (The second stage is production: the product is available to any buyer. This stage requires twenty-one checks.) |

## 7. The address to the reader stays even

Neither familiarity nor lecturing. One form of address for the whole text — "you" (informal)
— and it does not change from section to section.

| Before | After |
|---|---|
| Порядок один и тот же, кем бы ты ни был. (The order is the same no matter who you are.) | Порядок работы всегда один и тот же. Отличается только количество проверок. (The order of work is always the same. Only the number of checks differs.) |

## 8. The reason stands next to the rule

A rule without a reason looks arbitrary, and it's the first one people break. The reason
is one sentence, not a story.

> Проверка, которая не может провалиться, хуже, чем отсутствие проверки: она
> создаёт ложную уверенность.
> (A check that can never fail is worse than no check at all: it creates false
> confidence.)

## What the machine checks

`tools/check_writing_style.py` reads a file and looks for what can be counted: internal
jargon from a list, "we" and "we have," terms without a definition at first appearance.
The remaining rules are checked by a human — a machine can't tell a fact from a judgment.

```bash
python3 tools/check_writing_style.py README.md store_app/content.json
```

This check is not part of the mandatory build and production stages: text that no outsider
reads doesn't have to obey it. It's run on the guide, product descriptions, and interface
text.
