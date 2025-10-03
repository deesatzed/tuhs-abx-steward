import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  allergyCheckerTool,
  resistanceValidatorTool,
  dosingCalculatorTool,
} from '../lib/clinicalTools.js';

// Allergy Checker Tests
test('allergyChecker - no allergies returns safe', async () => {
  const result = await allergyCheckerTool.handler({
    antibiotic: 'ceftriaxone',
    allergies: 'None',
  });

  assert.equal(result.safe, true);
  assert.ok(result.reason.includes('No allergies'));
});

test('allergyChecker - direct allergy blocks drug', async () => {
  const result = await allergyCheckerTool.handler({
    antibiotic: 'vancomycin',
    allergies: 'Vancomycin',
  });

  assert.equal(result.safe, false);
  assert.ok(result.reason.includes('Direct allergy'));
  assert.ok(result.alternative);
});

test('allergyChecker - high PENFAST blocks cephalosporin', async () => {
  const result = await allergyCheckerTool.handler({
    antibiotic: 'ceftriaxone',
    allergies: 'Penicillin (anaphylaxis)',
    reaction_type: 'anaphylaxis',
  });

  assert.equal(result.safe, false);
  assert.ok(result.penfast_score >= 3);
  assert.ok(result.reason.includes('PENFAST'));
  assert.ok(result.alternative);
});

test('allergyChecker - low PENFAST allows cephalosporin with monitoring', async () => {
  const result = await allergyCheckerTool.handler({
    antibiotic: 'ceftriaxone',
    allergies: 'Penicillin (mild rash 10 years ago)',
    reaction_type: 'rash',
  });

  assert.equal(result.safe, true);
  assert.ok(result.penfast_score < 3);
  assert.ok(result.reason.includes('Low-risk'));
});

test('allergyChecker - aztreonam safe with penicillin allergy', async () => {
  const result = await allergyCheckerTool.handler({
    antibiotic: 'aztreonam',
    allergies: 'Penicillin (anaphylaxis)',
  });

  assert.equal(result.safe, true);
  assert.ok(result.reason.includes('minimal cross-reactivity'));
});

test('allergyChecker - carbapenem risk with high PENFAST', async () => {
  const result = await allergyCheckerTool.handler({
    antibiotic: 'meropenem',
    allergies: 'Penicillin (anaphylaxis)',
    reaction_type: 'anaphylaxis',
  });

  assert.equal(result.safe, false);
  assert.ok(result.reason.includes('Carbapenem'));
});

test('allergyChecker - cephalosporin allergy blocks cephalosporin', async () => {
  const result = await allergyCheckerTool.handler({
    antibiotic: 'cefepime',
    allergies: 'Cephalosporin allergy',
  });

  assert.equal(result.safe, false);
  assert.ok(result.alternative);
});

// Resistance Validator Tests
test('resistanceValidator - no resistance returns adequate', async () => {
  const result = await resistanceValidatorTool.handler({
    antibiotic: 'ceftriaxone',
    resistance_history: 'None',
  });

  assert.equal(result.adequate, true);
  assert.ok(result.reason.includes('No prior resistance'));
});

test('resistanceValidator - vancomycin covers MRSA', async () => {
  const result = await resistanceValidatorTool.handler({
    antibiotic: 'vancomycin',
    resistance_history: 'MRSA colonization',
  });

  assert.equal(result.adequate, true);
  assert.ok(result.covered_organisms.includes('MRSA'));
});

test('resistanceValidator - ceftriaxone does not cover MRSA', async () => {
  const result = await resistanceValidatorTool.handler({
    antibiotic: 'ceftriaxone',
    resistance_history: 'MRSA',
  });

  assert.equal(result.adequate, false);
  assert.ok(result.uncovered_organisms.includes('MRSA'));
  assert.ok(result.alternative_agents.length > 0);
});

test('resistanceValidator - meropenem covers ESBL', async () => {
  const result = await resistanceValidatorTool.handler({
    antibiotic: 'meropenem',
    resistance_history: 'ESBL E. coli',
  });

  assert.equal(result.adequate, true);
  assert.ok(result.covered_organisms.includes('ESBL'));
});

test('resistanceValidator - linezolid covers VRE', async () => {
  const result = await resistanceValidatorTool.handler({
    antibiotic: 'linezolid',
    resistance_history: 'VRE',
  });

  assert.equal(result.adequate, true);
  assert.ok(result.covered_organisms.includes('VRE'));
});

test('resistanceValidator - suggests alternatives for gaps', async () => {
  const result = await resistanceValidatorTool.handler({
    antibiotic: 'cefepime',
    resistance_history: 'CRE',
  });

  assert.equal(result.adequate, false);
  assert.ok(result.uncovered_organisms.includes('CRE'));
  assert.ok(result.alternative_agents.length > 0);
});

// Dosing Calculator Tests
test('dosingCalculator - normal GFR no adjustment', async () => {
  const result = await dosingCalculatorTool.handler({
    antibiotic: 'cefepime',
    gfr: '90',
  });

  assert.ok(result.dose.includes('q8h'));
  assert.equal(result.adjustment_level, 'normal');
  assert.equal(result.monitoring, null);
});

test('dosingCalculator - moderate renal impairment adjusts dose', async () => {
  const result = await dosingCalculatorTool.handler({
    antibiotic: 'cefepime',
    gfr: '45',
  });

  assert.ok(result.dose.includes('q12h'));
  assert.equal(result.adjustment_level, 'moderate');
  assert.ok(result.monitoring);
});

test('dosingCalculator - severe renal impairment reduces dose', async () => {
  const result = await dosingCalculatorTool.handler({
    antibiotic: 'cefepime',
    gfr: '20',
  });

  assert.ok(result.dose.includes('1g'));
  assert.equal(result.adjustment_level, 'severe');
  assert.ok(result.monitoring);
});

test('dosingCalculator - dialysis has special dosing', async () => {
  const result = await dosingCalculatorTool.handler({
    antibiotic: 'cefepime',
    gfr: '5',
  });

  assert.equal(result.adjustment_level, 'dialysis');
  assert.ok(result.monitoring);
});

test('dosingCalculator - vancomycin requires levels', async () => {
  const result = await dosingCalculatorTool.handler({
    antibiotic: 'vancomycin',
    gfr: '45',
    weight_kg: '70',
  });

  assert.ok(result.dose.includes('levels'));
  assert.ok(result.monitoring);
});

test('dosingCalculator - ceftriaxone no adjustment needed', async () => {
  const result = await dosingCalculatorTool.handler({
    antibiotic: 'ceftriaxone',
    gfr: '20',
  });

  assert.ok(result.dose.includes('No adjustment'));
});

test('dosingCalculator - unknown drug returns verify dosing', async () => {
  const result = await dosingCalculatorTool.handler({
    antibiotic: 'unknown_antibiotic',
    gfr: '45',
  });

  assert.equal(result.dose, 'verify dosing');
  assert.ok(result.note);
});

test('dosingCalculator - invalid GFR returns verify dosing', async () => {
  const result = await dosingCalculatorTool.handler({
    antibiotic: 'cefepime',
    gfr: 'invalid',
  });

  assert.equal(result.dose, 'verify dosing');
  assert.ok(result.note.includes('GFR not provided'));
});

test('dosingCalculator - meropenem adjusts for renal function', async () => {
  const result = await dosingCalculatorTool.handler({
    antibiotic: 'meropenem',
    gfr: '35',
  });

  assert.ok(result.dose.includes('q12h'));
  assert.equal(result.adjustment_level, 'moderate');
});
