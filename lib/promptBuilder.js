const toCleanString = (value, fallback) => {
  if (value === undefined || value === null) {
    return fallback;
  }

  if (typeof value === 'number') {
    return Number.isFinite(value) ? String(value) : fallback;
  }

  const trimmed = String(value).trim();
  return trimmed.length > 0 ? trimmed : fallback;
};

export const buildPromptVariables = (source) => ({
  age: toCleanString(source.age, 'not provided'),
  weight_kg: toCleanString(source.weight_kg || source.weight, 'not provided'),
  gfr: toCleanString(source.gfr, 'not provided'),
  acuity: toCleanString(source.acuity, 'not provided'),
  source_category: toCleanString(source.source_category || source.source, 'not provided'),
  allergies: toCleanString(source.allergies, 'none'),
  culture_results: toCleanString(source.culture_results || source.culture, 'pending'),
  prior_resistance: toCleanString(source.prior_resistance || source.resistance, 'none'),
  source_risk: toCleanString(source.source_risk, 'none'),
  inf_risks: toCleanString(source.inf_risks, 'none'),
  current_outpt_abx: toCleanString(source.current_outpt_abx, 'none'),
  current_inp_abx: toCleanString(source.current_inp_abx, 'none'),
});
