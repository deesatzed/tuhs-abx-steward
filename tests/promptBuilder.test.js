import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildPromptVariables } from '../lib/promptBuilder.js';

test('buildPromptVariables - handles complete valid input', () => {
  const input = {
    age: '65',
    weight_kg: '70',
    gfr: '60',
    acuity: 'Ward',
    source_category: 'Pneumonia',
    allergies: 'Penicillin',
    culture_results: 'Pending',
    prior_resistance: 'None',
    source_risk: 'Recent surgery',
    inf_risks: 'None',
    current_outpt_abx: 'None',
    current_inp_abx: 'None',
  };

  const result = buildPromptVariables(input);

  assert.equal(result.age, '65');
  assert.equal(result.weight_kg, '70');
  assert.equal(result.gfr, '60');
  assert.equal(result.acuity, 'Ward');
  assert.equal(result.source_category, 'Pneumonia');
  assert.equal(result.allergies, 'Penicillin');
});

test('buildPromptVariables - handles missing values with fallbacks', () => {
  const input = {};
  const result = buildPromptVariables(input);

  assert.equal(result.age, 'not provided');
  assert.equal(result.weight_kg, 'not provided');
  assert.equal(result.gfr, 'not provided');
  assert.equal(result.allergies, 'none');
  assert.equal(result.culture_results, 'pending');
  assert.equal(result.prior_resistance, 'none');
});

test('buildPromptVariables - handles empty strings', () => {
  const input = {
    age: '',
    weight_kg: '  ',
    allergies: '',
  };

  const result = buildPromptVariables(input);

  assert.equal(result.age, 'not provided');
  assert.equal(result.weight_kg, 'not provided');
  assert.equal(result.allergies, 'none');
});

test('buildPromptVariables - handles numeric values', () => {
  const input = {
    age: 65,
    weight_kg: 70.5,
    gfr: 60,
  };

  const result = buildPromptVariables(input);

  assert.equal(result.age, '65');
  assert.equal(result.weight_kg, '70.5');
  assert.equal(result.gfr, '60');
});

test('buildPromptVariables - handles null and undefined', () => {
  const input = {
    age: null,
    weight_kg: undefined,
    allergies: null,
  };

  const result = buildPromptVariables(input);

  assert.equal(result.age, 'not provided');
  assert.equal(result.weight_kg, 'not provided');
  assert.equal(result.allergies, 'none');
});

test('buildPromptVariables - handles alternate field names', () => {
  const input = {
    weight: '75',
    source: 'UTI',
    culture: 'E. coli',
    resistance: 'ESBL',
  };

  const result = buildPromptVariables(input);

  assert.equal(result.weight_kg, '75');
  assert.equal(result.source_category, 'UTI');
  assert.equal(result.culture_results, 'E. coli');
  assert.equal(result.prior_resistance, 'ESBL');
});

test('buildPromptVariables - trims whitespace', () => {
  const input = {
    age: '  65  ',
    allergies: '  Penicillin  ',
  };

  const result = buildPromptVariables(input);

  assert.equal(result.age, '65');
  assert.equal(result.allergies, 'Penicillin');
});
