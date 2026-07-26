#!/usr/bin/env node
'use strict';

// Dependency-free render/security selftest for the canonical Agent Cabinet
// and help widgets. It executes the exact templates in an isolated VM.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');

function fakeElement() {
  return {
    innerHTML: '',
    style: {},
    querySelectorAll: function () { return []; }
  };
}

function cabinetFixture() {
  return {
    schema: 'extella.agent_cabinet.v1.1',
    passport: {
      identity: {
        name: '<img src=x onerror=alert(1)>',
        owner: 'Owner "unsafe"',
        platform_agent_id: 'agent_qwen_widget_test',
        active_version: '1.0.0',
        model_profile: 'qwen-3.7',
        languages: ['ru', 'en']
      },
      genome: [{
        element_type: 'capability',
        gene_id: null,
        name: '<svg onload=alert(2)>',
        version: '1.0.0',
        autonomy: 'A1',
        provenance: 'agent',
        side_effects: 'none',
        confirmation: 'never',
        limits: []
      }, {
        element_type: 'rule',
        gene_id: 'rule.widget-policy',
        name: 'Widget policy',
        version: '2.0.0',
        autonomy: null,
        provenance: 'global',
        side_effects: null,
        confirmation: null,
        limits: []
      }],
      attention: {
        shared_genes: [{
          gene_id: 'rule.widget-policy',
          kind: 'rule',
          name: 'Widget policy',
          version: '2.0.0'
        }],
        legacy_global_capabilities: [],
        external_or_physical: [],
        human_required: []
      }
    },
    declared_behaviour: {
      steps: [{capability: 'Read data', autonomy: 'A1', side_effects: 'none'}]
    },
    actual_behaviour: {
      evidence_sources: [{
        id: 'run_history',
        what_ru: 'История управляемых прогонов',
        what_en: 'Managed run history'
      }],
      limits: {
        ru: ['Прямые чаты не видны'],
        en: ['Direct chats are not visible']
      }
    },
    evolution: {
      cycle: [{
        step: 'draft',
        what_ru: 'Создать черновик',
        what_en: 'Create a draft'
      }],
      shared_change_guard: {
        prompt_ru: 'Используют ещё {N} агентов',
        prompt_en: 'Used by {N} more agents',
        choices_ru: ['Локально', 'Весь класс', 'Отмена'],
        choices_en: ['Local', 'Whole class', 'Cancel'],
        must_show_ru: 'Показать ВСЕХ затронутых агентов',
        must_show_en: 'Show ALL affected agents',
        affected_count: 2,
        candidates: [{
          gene_id: 'rule.widget-policy',
          kind: 'rule',
          name: 'Widget policy',
          version: '2.0.0'
        }]
      }
    }
  };
}

function renderCabinet(lang, tab, fixture) {
  const host = fakeElement();
  const context = {
    WLANG: lang,
    window: {},
    document: {getElementById: function () { return host; }}
  };
  vm.createContext(context);
  vm.runInContext(
    fs.readFileSync(path.join(ROOT, 'templates', 'cabinet_widget.js'), 'utf8'),
    context
  );
  context.renderCabinet(fixture || cabinetFixture(), 'cabinet-host', tab);
  return host.innerHTML;
}

function renderHelp(lang) {
  const body = fakeElement();
  const wrap = fakeElement();
  const context = {
    WLANG: lang,
    localStorage: {getItem: function () { return null; }, setItem: function () {}},
    el: function (id) { return id === 'xtl_help_body' ? body : wrap; }
  };
  vm.createContext(context);
  vm.runInContext(
    fs.readFileSync(path.join(ROOT, 'templates', 'help_widget.js'), 'utf8'),
    context
  );
  context.HELP.my_surface[lang].title = '<img src=x onerror=alert(3)>';
  context.openHelp('my_surface');
  return body.innerHTML;
}

function run() {
  const passportRu = renderCabinet('ru', 'passport');
  const passportEn = renderCabinet('en', 'passport');
  const actualRu = renderCabinet('ru', 'actual');
  const actualEn = renderCabinet('en', 'actual');
  const evolutionRu = renderCabinet('ru', 'evolution');
  const evolutionEn = renderCabinet('en', 'evolution');
  const legacy = cabinetFixture();
  delete legacy.passport.identity.platform_agent_id;
  legacy.passport.attention.shared_genes = ['Legacy global capability'];
  delete legacy.passport.attention.legacy_global_capabilities;
  legacy.actual_behaviour.evidence_sources = [{id: 'legacy', what: 'Legacy evidence'}];
  legacy.evolution.cycle = [{step: 'legacy', what: 'Legacy cycle'}];
  legacy.evolution.shared_change_guard.must_show = 'Legacy impact';
  delete legacy.evolution.shared_change_guard.must_show_ru;
  delete legacy.evolution.shared_change_guard.must_show_en;
  legacy.evolution.shared_change_guard.candidates = ['Legacy global capability'];
  const legacyActual = renderCabinet('en', 'actual', legacy);
  const legacyEvolution = renderCabinet('en', 'evolution', legacy);
  const helpRu = renderHelp('ru');
  const helpEn = renderHelp('en');

  assert(passportRu.includes('Agent Passport'));
  assert(passportEn.includes('Agent Passport'));
  assert(actualRu.includes('История управляемых прогонов'));
  assert(actualEn.includes('Managed run history'));
  assert(!actualEn.includes('История управляемых прогонов'));
  assert(evolutionRu.includes('Создать черновик'));
  assert(evolutionEn.includes('Create a draft'));
  assert(evolutionEn.includes('Show ALL affected agents'));
  assert(!evolutionEn.includes('Показать ВСЕХ'));
  assert(legacyActual.includes('Legacy evidence'));
  assert(legacyEvolution.includes('Legacy cycle'));
  assert(legacyEvolution.includes('Legacy impact'));
  assert(legacyEvolution.includes('Legacy global capability'));

  assert(helpRu.includes('Как это работает'));
  assert(helpRu.includes('Что гарантировано'));
  assert(helpEn.includes('How it works'));
  assert(helpEn.includes('What is guaranteed'));
  assert(helpEn.includes('What we do NOT promise'));
  assert(!helpEn.includes('Как это работает'));
  assert(!helpEn.includes('Что гарантировано'));

  for (const html of [passportRu, passportEn, helpRu, helpEn]) {
    assert(!html.includes('<img src=x onerror='));
    assert(html.includes('&lt;img src=x onerror='));
  }
  assert(!passportRu.includes('<svg onload='));
  assert(passportRu.includes('&lt;svg onload='));

  const cabinetSource = fs.readFileSync(
    path.join(ROOT, 'templates', 'cabinet_widget.js'), 'utf8'
  );
  const helpSource = fs.readFileSync(
    path.join(ROOT, 'templates', 'help_widget.js'), 'utf8'
  );
  assert(!cabinetSource.includes('onclick='));
  assert(!helpSource.includes('innerHTML = h') || helpSource.includes('helpEsc'));

  console.log('PASS: Agent Cabinet 3 tabs × RU/EN render from canonical v1.1 data');
  console.log('PASS: help widget RU/EN headings and content are complete');
  console.log('PASS: untrusted strings are HTML-escaped; no inline Cabinet handlers');
}

run();
