/**
 * Calculate case complexity score (0-10 scale)
 */
export function calculateComplexity(patientData) {
  let score = 0;
  const factors = [];

  // Allergy complexity (0-3 points)
  if (patientData.allergies && patientData.allergies.toLowerCase() !== 'none') {
    if (patientData.allergies.toLowerCase().includes('anaphylaxis')) {
      score += 3;
      factors.push('Severe allergy (anaphylaxis)');
    } else if (patientData.allergies.toLowerCase().includes('allergy')) {
      score += 2;
      factors.push('Moderate allergy');
    } else {
      score += 1;
      factors.push('Mild allergy history');
    }
  }

  // Resistance complexity (0-3 points)
  if (patientData.prior_resistance && patientData.prior_resistance.toLowerCase() !== 'none') {
    const resistancePatterns = patientData.prior_resistance.toLowerCase();
    if (resistancePatterns.includes('cre') || resistancePatterns.includes('carbapenem')) {
      score += 3;
      factors.push('Carbapenem resistance');
    } else if (resistancePatterns.includes('mrsa') || resistancePatterns.includes('vre')) {
      score += 2;
      factors.push('MRSA/VRE history');
    } else {
      score += 1;
      factors.push('Other resistance');
    }
  }

  // Acuity (0-2 points) - Ward is baseline (0 points)
  if (patientData.acuity === 'ICU') {
    score += 2;
    factors.push('ICU level care');
  } else if (patientData.acuity === 'ED') {
    score += 1;
    factors.push('ED level care');
  }
  // Ward acuity adds 0 points (baseline)

  // Infection risks (0-2 points)
  if (patientData.inf_risks && patientData.inf_risks.toLowerCase() !== 'none') {
    if (patientData.inf_risks.toLowerCase().includes('shock') ||
        patientData.inf_risks.toLowerCase().includes('neutropenia')) {
      score += 2;
      factors.push('Critical infection risk');
    } else {
      score += 1;
      factors.push('Elevated infection risk');
    }
  }

  return {
    score: Math.min(score, 10),
    factors,
  };
}

/**
 * Select optimal model based on complexity
 */
export function selectModel(complexity, patientData) {
  const score = complexity.score;

  // Simple cases: use faster, cheaper model
  if (score < 3) {
    console.log('Simple case - using fast model');
    return process.env.FALLBACK_MODEL || 'google/gemini-2.5-flash-lite-preview-09-2025';
  }

  // ICU or very complex cases: use most capable model
  if (patientData.acuity === 'ICU' || score > 7) {
    console.log('Complex/ICU case - using advanced model');
    return process.env.ICU_MODEL || 'x-ai/grok-4-fast';
  }

  // Standard cases: use balanced model
  console.log('Standard case - using default model');
  return process.env.DEFAULT_MODEL || 'x-ai/grok-4-fast';
}

/**
 * Get model fallback chain
 */
export function getModelFallbackChain() {
  return [
    process.env.DEFAULT_MODEL || 'x-ai/grok-4-fast',
    process.env.FALLBACK_MODEL || 'google/gemini-2.5-flash-lite-preview-09-2025',
    'openai/gpt-3.5-turbo', // Ultimate fallback
  ];
}
