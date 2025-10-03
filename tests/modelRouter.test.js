import { test } from 'node:test';
import assert from 'node:assert/strict';
import { calculateComplexity, selectModel } from '../lib/modelRouter.js';

test('calculateComplexity - simple case (no allergies, no resistance)', () => {
  const patient = {
    allergies: 'none',
    prior_resistance: 'none',
    acuity: 'Ward',
    inf_risks: 'none',
  };

  const result = calculateComplexity(patient);

  assert.equal(result.score, 0);
  assert.equal(result.factors.length, 0);
});

test('calculateComplexity - mild allergy adds points', () => {
  const patient = {
    allergies: 'Mild rash to penicillin',
    prior_resistance: 'none',
    acuity: 'Ward',
    inf_risks: 'none',
  };

  const result = calculateComplexity(patient);

  assert.ok(result.score >= 1 && result.score <= 2);
  assert.ok(result.factors.some(f => f.includes('allergy')));
});

test('calculateComplexity - anaphylaxis is high complexity', () => {
  const patient = {
    allergies: 'Penicillin (anaphylaxis)',
    prior_resistance: 'none',
    acuity: 'Ward',
    inf_risks: 'none',
  };

  const result = calculateComplexity(patient);

  assert.ok(result.score >= 3);
  assert.ok(result.factors.some(f => f.includes('anaphylaxis')));
});

test('calculateComplexity - MRSA/VRE adds medium complexity', () => {
  const patient = {
    allergies: 'none',
    prior_resistance: 'MRSA colonization',
    acuity: 'Ward',
    inf_risks: 'none',
  };

  const result = calculateComplexity(patient);

  assert.ok(result.score >= 2);
  assert.ok(result.factors.some(f => f.includes('MRSA')));
});

test('calculateComplexity - CRE is highest resistance complexity', () => {
  const patient = {
    allergies: 'none',
    prior_resistance: 'CRE documented',
    acuity: 'Ward',
    inf_risks: 'none',
  };

  const result = calculateComplexity(patient);

  assert.ok(result.score >= 3);
  assert.ok(result.factors.some(f => f.includes('Carbapenem')));
});

test('calculateComplexity - ICU acuity adds points', () => {
  const patient = {
    allergies: 'none',
    prior_resistance: 'none',
    acuity: 'ICU',
    inf_risks: 'none',
  };

  const result = calculateComplexity(patient);

  assert.ok(result.score >= 2);
  assert.ok(result.factors.some(f => f.includes('ICU')));
});

test('calculateComplexity - ED acuity adds one point', () => {
  const patient = {
    allergies: 'none',
    prior_resistance: 'none',
    acuity: 'ED',
    inf_risks: 'none',
  };

  const result = calculateComplexity(patient);

  assert.ok(result.score >= 1);
  assert.ok(result.factors.some(f => f.includes('ED')));
});

test('calculateComplexity - septic shock increases complexity', () => {
  const patient = {
    allergies: 'none',
    prior_resistance: 'none',
    acuity: 'Ward',
    inf_risks: 'Septic shock',
  };

  const result = calculateComplexity(patient);

  assert.ok(result.score >= 2);
  assert.ok(result.factors.some(f => f.includes('Critical infection risk')));
});

test('calculateComplexity - complex case sums all factors', () => {
  const patient = {
    allergies: 'Penicillin (anaphylaxis)',
    prior_resistance: 'CRE',
    acuity: 'ICU',
    inf_risks: 'Septic shock',
  };

  const result = calculateComplexity(patient);

  assert.ok(result.score >= 8); // 3 + 3 + 2 + 2
  assert.ok(result.factors.length >= 4);
});

test('calculateComplexity - max score is 10', () => {
  const patient = {
    allergies: 'Penicillin (anaphylaxis), cephalosporin',
    prior_resistance: 'CRE, MRSA, VRE',
    acuity: 'ICU',
    inf_risks: 'Septic shock, neutropenia',
  };

  const result = calculateComplexity(patient);

  assert.ok(result.score <= 10);
});

test('selectModel - simple case uses fallback model', () => {
  const complexity = { score: 2, factors: [] };
  const patient = { acuity: 'Ward' };

  const model = selectModel(complexity, patient);

  assert.ok(model.includes('gemini') || model.includes('flash'));
});

test('selectModel - ICU case uses advanced model', () => {
  const complexity = { score: 5, factors: [] };
  const patient = { acuity: 'ICU' };

  const model = selectModel(complexity, patient);

  assert.ok(model.includes('grok') || model.includes('x-ai'));
});

test('selectModel - high complexity uses advanced model', () => {
  const complexity = { score: 8, factors: [] };
  const patient = { acuity: 'Ward' };

  const model = selectModel(complexity, patient);

  assert.ok(model.includes('grok') || model.includes('x-ai'));
});

test('selectModel - standard case uses default model', () => {
  const complexity = { score: 5, factors: [] };
  const patient = { acuity: 'Ward' };

  const model = selectModel(complexity, patient);

  assert.ok(model.includes('grok') || model.includes('x-ai'));
});
