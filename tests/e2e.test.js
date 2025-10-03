import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildPromptVariables } from '../lib/promptBuilder.js';
import { calculateComplexity, selectModel } from '../lib/modelRouter.js';
import {
  allergyCheckerTool,
  resistanceValidatorTool,
  dosingCalculatorTool,
} from '../lib/clinicalTools.js';

/**
 * E2E Test Suite - Full Clinical Workflow
 * Tests the complete decision pipeline without external dependencies
 */

test('E2E - Simple Community-Acquired Pneumonia (CAP) case', async () => {
  // 1. Patient input
  const rawInput = {
    age: '45',
    weight_kg: '70',
    gfr: '90',
    acuity: 'Ward',
    source_category: 'Pneumonia',
    allergies: 'None',
    culture_results: 'Pending',
    prior_resistance: 'None',
    inf_risks: 'None',
  };

  // 2. Normalize input
  const variables = buildPromptVariables(rawInput);
  assert.equal(variables.age, '45');
  assert.equal(variables.allergies, 'None');

  // 3. Calculate complexity
  const complexity = calculateComplexity(variables);
  assert.ok(complexity.score <= 3, 'Simple case should have low complexity');

  // 4. Select model
  const model = selectModel(complexity, variables);
  assert.ok(model.includes('gemini') || model.includes('flash'), `Should use fast model for simple case, got: ${model}`);

  // 5. Check allergies for ceftriaxone (common CAP choice)
  const allergyCheck = await allergyCheckerTool.handler({
    antibiotic: 'ceftriaxone',
    allergies: variables.allergies,
  });
  assert.equal(allergyCheck.safe, true, 'Ceftriaxone should be safe with no allergies');

  // 6. No resistance to validate
  const resistanceCheck = await resistanceValidatorTool.handler({
    antibiotic: 'ceftriaxone',
    resistance_history: variables.prior_resistance,
  });
  assert.equal(resistanceCheck.adequate, true);

  // 7. Calculate dosing
  const dosingCheck = await dosingCalculatorTool.handler({
    antibiotic: 'ceftriaxone',
    gfr: variables.gfr,
  });
  assert.equal(dosingCheck.adjustment_level, 'normal', 'Ceftriaxone needs no renal adjustment with normal GFR');
  assert.ok(dosingCheck.dose.includes('1-2g'), 'Should have standard ceftriaxone dose');

  console.log('✅ E2E Simple CAP: All checks passed');
});

test('E2E - Complex ICU case with penicillin allergy and MRSA', async () => {
  // 1. Patient input
  const rawInput = {
    age: '72',
    weight_kg: '85',
    gfr: '35',
    acuity: 'ICU',
    source_category: 'Pneumonia',
    allergies: 'Penicillin (anaphylaxis)',
    culture_results: 'Pending',
    prior_resistance: 'MRSA colonization',
    inf_risks: 'Septic shock',
  };

  // 2. Normalize input
  const variables = buildPromptVariables(rawInput);

  // 3. Calculate complexity
  const complexity = calculateComplexity(variables);
  assert.ok(complexity.factors.length >= 3, 'Should have multiple complexity factors');

  // 4. Select model
  const model = selectModel(complexity, variables);
  assert.ok(
    model.includes('grok') || model.includes('x-ai'),
    `Should use advanced model for ICU (got ${model})`
  );

  // 5. Check allergies for cephalosporin
  const cephAllergyCheck = await allergyCheckerTool.handler({
    antibiotic: 'cefepime',
    allergies: variables.allergies,
    reaction_type: 'anaphylaxis',
  });
  assert.equal(cephAllergyCheck.safe, false, 'High PENFAST should block cephalosporin');
  assert.ok(cephAllergyCheck.penfast_score >= 3);
  assert.ok(cephAllergyCheck.alternative, 'Should suggest alternative');

  // 6. Check aztreonam (safe alternative)
  const aztreonamCheck = await allergyCheckerTool.handler({
    antibiotic: 'aztreonam',
    allergies: variables.allergies,
  });
  assert.equal(aztreonamCheck.safe, true, 'Aztreonam should be safe despite penicillin allergy');

  // 7. Validate MRSA coverage with vancomycin
  const resistanceCheck = await resistanceValidatorTool.handler({
    antibiotic: 'vancomycin',
    resistance_history: variables.prior_resistance,
  });
  assert.equal(resistanceCheck.adequate, true, 'Vancomycin should cover MRSA');
  assert.ok(resistanceCheck.covered_organisms.includes('MRSA'));

  // 8. Calculate vancomycin dosing with renal impairment
  const dosingCheck = await dosingCalculatorTool.handler({
    antibiotic: 'vancomycin',
    gfr: variables.gfr,
    weight_kg: variables.weight_kg,
  });
  assert.ok(dosingCheck.dose.includes('levels'), 'Vancomycin should require level monitoring');
  assert.ok(dosingCheck.monitoring, 'Should have monitoring instructions');

  console.log('✅ E2E Complex ICU: All checks passed');
});

test('E2E - Renal impairment with ESBL resistance', async () => {
  // 1. Patient input
  const rawInput = {
    age: '68',
    weight_kg: '78',
    gfr: '22',
    acuity: 'Ward',
    source_category: 'UTI',
    allergies: 'None',
    culture_results: 'E. coli ESBL+',
    prior_resistance: 'ESBL',
    inf_risks: 'None',
  };

  // 2. Normalize input
  const variables = buildPromptVariables(rawInput);

  // 3. Calculate complexity
  const complexity = calculateComplexity(variables);
  assert.ok(complexity.score >= 1, 'ESBL resistance should increase complexity');

  // 4. Check ceftriaxone (won't cover ESBL)
  const ceftriaxoneResistance = await resistanceValidatorTool.handler({
    antibiotic: 'ceftriaxone',
    resistance_history: variables.prior_resistance,
  });
  assert.equal(ceftriaxoneResistance.adequate, false, 'Ceftriaxone should not cover ESBL');
  assert.ok(ceftriaxoneResistance.uncovered_organisms.includes('ESBL'));
  assert.ok(ceftriaxoneResistance.alternative_agents.length > 0, 'Should suggest alternatives');

  // 5. Check meropenem (covers ESBL)
  const meropenemResistance = await resistanceValidatorTool.handler({
    antibiotic: 'meropenem',
    resistance_history: variables.prior_resistance,
  });
  assert.equal(meropenemResistance.adequate, true, 'Meropenem should cover ESBL');

  // 6. Calculate meropenem dosing with severe renal impairment
  const dosingCheck = await dosingCalculatorTool.handler({
    antibiotic: 'meropenem',
    gfr: variables.gfr,
  });
  assert.equal(dosingCheck.adjustment_level, 'severe', 'Should flag severe renal adjustment');
  assert.ok(dosingCheck.dose.includes('500mg') || dosingCheck.dose.includes('q12h'), 'Should adjust dose/frequency');
  assert.ok(dosingCheck.monitoring, 'Should monitor renal function');

  console.log('✅ E2E Renal + ESBL: All checks passed');
});

test('E2E - Multiple allergies and CRE resistance (highest complexity)', async () => {
  // 1. Patient input
  const rawInput = {
    age: '75',
    weight_kg: '65',
    gfr: '18',
    acuity: 'ICU',
    source_category: 'Intra-abdominal infection',
    allergies: 'Penicillin (anaphylaxis), Fluoroquinolone (rash)',
    culture_results: 'Pending',
    prior_resistance: 'CRE, VRE',
    inf_risks: 'Septic shock, recent transplant',
  };

  // 2. Normalize input
  const variables = buildPromptVariables(rawInput);

  // 3. Calculate complexity (should be maximal)
  const complexity = calculateComplexity(variables);
  assert.ok(complexity.score >= 8, `Maximum complexity case should score high (got ${complexity.score})`);
  assert.ok(complexity.factors.length >= 4, 'Should have many complexity factors');

  // 4. Select model (should use most advanced)
  const model = selectModel(complexity, variables);
  assert.ok(
    model.includes('grok') || model.includes('x-ai'),
    `Should use most advanced model, got: ${model}`,
  );

  // 5. Check CRE coverage (very limited options)
  const ceftriaxoneCheck = await resistanceValidatorTool.handler({
    antibiotic: 'ceftriaxone',
    resistance_history: variables.prior_resistance,
  });
  assert.equal(ceftriaxoneCheck.adequate, false, 'Standard agents should not cover CRE');
  assert.ok(ceftriaxoneCheck.uncovered_organisms.includes('CRE'));

  // 6. Check if tigecycline or colistin suggested
  const hasAdvancedAgent = ceftriaxoneCheck.alternative_agents.some(
    agent => agent.includes('tigecycline') || agent.includes('colistin'),
  );
  assert.ok(hasAdvancedAgent, 'Should suggest advanced agents for CRE');

  // 7. Check allergy safety for multiple drugs
  const vancomycinCheck = await allergyCheckerTool.handler({
    antibiotic: 'vancomycin',
    allergies: variables.allergies,
  });
  assert.equal(vancomycinCheck.safe, true, 'Vancomycin should be safe');

  const aztreonamCheck = await allergyCheckerTool.handler({
    antibiotic: 'aztreonam',
    allergies: variables.allergies,
  });
  assert.equal(aztreonamCheck.safe, true, 'Aztreonam should be safe');

  console.log('✅ E2E Maximum Complexity: All checks passed');
});

test('E2E - Dialysis patient with complex medication history', async () => {
  // 1. Patient input
  const rawInput = {
    age: '58',
    weight_kg: '72',
    gfr: '8',
    acuity: 'Ward',
    source_category: 'Skin and soft tissue',
    allergies: 'Cephalosporin',
    culture_results: 'MSSA',
    prior_resistance: 'None',
    inf_risks: 'Dialysis-dependent',
  };

  // 2. Normalize input
  const variables = buildPromptVariables(rawInput);

  // 3. Check cephalosporin allergy blocks cefazolin
  const cefazolinCheck = await allergyCheckerTool.handler({
    antibiotic: 'cefazolin',
    allergies: variables.allergies,
  });
  assert.equal(cefazolinCheck.safe, false, 'Cephalosporin allergy should block cefazolin');

  // 4. Check vancomycin (alternative for MSSA with ceph allergy)
  const vancoResistance = await resistanceValidatorTool.handler({
    antibiotic: 'vancomycin',
    resistance_history: variables.prior_resistance,
  });
  assert.equal(vancoResistance.adequate, true);

  // 5. Calculate vancomycin dosing for dialysis
  const dosingCheck = await dosingCalculatorTool.handler({
    antibiotic: 'vancomycin',
    gfr: variables.gfr,
    weight_kg: variables.weight_kg,
  });
  assert.equal(dosingCheck.adjustment_level, 'dialysis', 'Should recognize dialysis status');
  assert.ok(dosingCheck.dose.includes('levels') || dosingCheck.dose.includes('Load'), 'Dialysis dosing is specialized');

  // 6. Check cefepime dosing for dialysis
  const cefepimeDosing = await dosingCalculatorTool.handler({
    antibiotic: 'cefepime',
    gfr: variables.gfr,
  });
  assert.equal(cefepimeDosing.adjustment_level, 'dialysis');
  assert.ok(cefepimeDosing.dose.includes('q24h') || cefepimeDosing.dose.includes('dialysis'));

  console.log('✅ E2E Dialysis Patient: All checks passed');
});

test('E2E - Workflow integration test', async () => {
  // Test that all components work together in sequence
  const testCases = [
    { desc: 'Simple', input: { age: '45', acuity: 'Ward', allergies: 'None' }, expectedComplexity: 'low' },
    { desc: 'Moderate', input: { age: '65', acuity: 'ED', allergies: 'Penicillin (rash)' }, expectedComplexity: 'medium' },
    { desc: 'Complex', input: { age: '78', acuity: 'ICU', allergies: 'Penicillin (anaphylaxis)', prior_resistance: 'MRSA' }, expectedComplexity: 'high' },
  ];

  for (const testCase of testCases) {
    const variables = buildPromptVariables(testCase.input);
    const complexity = calculateComplexity(variables);
    const model = selectModel(complexity, variables);

    // Verify complexity classification matches expectation
    if (testCase.expectedComplexity === 'low') {
      assert.ok(complexity.score <= 3, `${testCase.desc}: Should be low complexity (got ${complexity.score})`);
      assert.ok(model.includes('gemini') || model.includes('flash'), `${testCase.desc}: Should use appropriate model, got: ${model}`);
    } else if (testCase.expectedComplexity === 'medium') {
      assert.ok(complexity.score >= 1 && complexity.score <= 7, `${testCase.desc}: Should be medium complexity (got ${complexity.score})`);
    } else if (testCase.expectedComplexity === 'high') {
      assert.ok(complexity.score >= 7, `${testCase.desc}: Should be high complexity (got ${complexity.score})`);
      assert.ok(model.includes('grok') || model.includes('x-ai'), `${testCase.desc}: Should use advanced model, got: ${model}`);
    }

    console.log(`  ✓ ${testCase.desc} case: Complexity=${complexity.score}, Model=${model.split('/').pop()}`);
  }

  console.log('✅ E2E Workflow Integration: All test cases passed');
});
