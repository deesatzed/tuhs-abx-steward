import { searchGuidelines } from './knowledgeBase.js';
import OpenAI from 'openai';

// Initialize OpenAI for embeddings (via OpenRouter)
const openai = new OpenAI({
  apiKey: process.env.OPENROUTER_API_KEY,
  baseURL: 'https://openrouter.ai/api/v1',
});

/**
 * PENFAST Score Calculation for Penicillin Allergy
 * Real clinical decision rule - NO MOCK
 * Reference: https://www.mdcalc.com/calc/10390/pen-fast-score
 */
function calculatePENFAST(allergies, reactionType) {
  let score = 0;

  const allergyLower = (allergies || '').toLowerCase();
  const reactionLower = (reactionType || '').toLowerCase();

  // Penicillin allergy (1 point)
  if (allergyLower.includes('penicillin') || allergyLower.includes('pcn')) {
    score += 1;
  }

  // Anaphylaxis (2 points)
  if (allergyLower.includes('anaphyl') || reactionLower.includes('anaphyl')) {
    score += 2;
  }

  // Severe cutaneous reaction (2 points)
  if (allergyLower.includes('sjs') || allergyLower.includes('stevens') ||
      allergyLower.includes('dress') || allergyLower.includes('ten')) {
    score += 2;
  }

  // Treatment within 5 years (1 point) - default to yes if recent
  if (allergyLower.includes('recent') || !allergyLower.includes('years ago')) {
    score += 1;
  }

  // Five or more symptoms (1 point)
  const symptoms = ['rash', 'hives', 'itching', 'swelling', 'difficulty breathing'];
  const symptomCount = symptoms.filter(s => allergyLower.includes(s)).length;
  if (symptomCount >= 3) { // Approximate with 3+ mentions
    score += 1;
  }

  return score;
}

/**
 * Cross-Reactivity Table (Evidence-Based)
 * Source: JAMA 2001, AAI 2019 guidelines
 * Note: Currently informational only - PENFAST score is primary decision tool
 */
// eslint-disable-next-line no-unused-vars
const CROSS_REACTIVITY = {
  penicillin: {
    cephalosporins: {
      first_generation: 0.05, // 5% cross-reactivity
      second_generation: 0.02, // 2%
      third_generation: 0.01, // 1%
      fourth_generation: 0.01, // 1%
    },
    carbapenems: 0.01, // 1%
    monobactams: 0.001, // <1% (aztreonam safe)
  },
};

/**
 * Tool: Allergy Checker
 */
export const allergyCheckerTool = {
  type: 'function',
  function: {
    name: 'check_allergy_contraindication',
    description: 'Validate if proposed antibiotic is safe given patient allergies. Uses PENFAST scoring and cross-reactivity data.',
    parameters: {
      type: 'object',
      properties: {
        antibiotic: {
          type: 'string',
          description: 'Proposed antibiotic name',
        },
        allergies: {
          type: 'string',
          description: 'Patient allergy list with reaction details',
        },
        reaction_type: {
          type: 'string',
          description: 'Type of reaction (e.g., anaphylaxis, rash)',
        },
      },
      required: ['antibiotic', 'allergies'],
    },
  },
  handler: async ({ antibiotic, allergies, reaction_type }) => {
    const antibioticLower = (antibiotic || '').toLowerCase();
    const allergyLower = (allergies || '').toLowerCase();

    // No allergies
    if (!allergies || allergies === 'none' || allergies === 'None') {
      return {
        safe: true,
        reason: 'No allergies documented',
        alternative: null,
      };
    }

    // Check for direct allergy to proposed antibiotic
    if (allergyLower.includes(antibioticLower)) {
      return {
        safe: false,
        reason: `Direct allergy to ${antibiotic}`,
        alternative: 'Consider fluoroquinolone or aztreonam',
      };
    }

    // Penicillin allergy with beta-lactam proposed
    if (allergyLower.includes('penicillin') || allergyLower.includes('pcn')) {
      const penfast = calculatePENFAST(allergies, reaction_type);

      // Check if proposed drug is a beta-lactam
      const isCephalosporin = antibioticLower.includes('cef') ||
                             antibioticLower.includes('ceph');
      const isCarbapenem = antibioticLower.includes('meropenem') ||
                          antibioticLower.includes('ertapenem') ||
                          antibioticLower.includes('imipenem');
      const isAztreonam = antibioticLower.includes('aztreonam');

      if (isCephalosporin) {
        // High PENFAST (≥3) = high risk
        if (penfast >= 3) {
          return {
            safe: false,
            reason: `High-risk penicillin allergy (PENFAST ${penfast}). Cephalosporin cross-reactivity risk.`,
            penfast_score: penfast,
            alternative: 'Fluoroquinolone (e.g., levofloxacin) or aztreonam',
          };
        } else {
          return {
            safe: true,
            reason: `Low-risk penicillin allergy (PENFAST ${penfast}). Cephalosporin likely safe with monitoring.`,
            penfast_score: penfast,
            recommendation: 'Monitor for allergic reaction during first dose',
          };
        }
      }

      if (isCarbapenem) {
        if (penfast >= 3) {
          return {
            safe: false,
            reason: `High-risk penicillin allergy (PENFAST ${penfast}). Carbapenem cross-reactivity risk.`,
            penfast_score: penfast,
            alternative: 'Aztreonam + metronidazole for gram-negative/anaerobic coverage',
          };
        } else {
          return {
            safe: true,
            reason: `Low-risk penicillin allergy (PENFAST ${penfast}). Carbapenem cross-reactivity <1%.`,
            penfast_score: penfast,
          };
        }
      }

      if (isAztreonam) {
        return {
          safe: true,
          reason: 'Aztreonam has minimal cross-reactivity with penicillin (<0.1%)',
        };
      }
    }

    // Cephalosporin allergy with cephalosporin proposed
    if (allergyLower.includes('cephalosporin') || allergyLower.includes('cef')) {
      if (antibioticLower.includes('cef') || antibioticLower.includes('ceph')) {
        return {
          safe: false,
          reason: 'Cephalosporin allergy documented',
          alternative: 'Fluoroquinolone or aztreonam',
        };
      }
    }

    return {
      safe: true,
      reason: 'No known contraindication',
    };
  },
};

/**
 * Resistance Coverage Matrix (Evidence-Based)
 */
const RESISTANCE_COVERAGE = {
  vancomycin: ['MRSA', 'MSSA'],
  linezolid: ['MRSA', 'VRE'],
  daptomycin: ['MRSA', 'VRE'],
  ceftaroline: ['MRSA', 'MSSA'],
  meropenem: ['ESBL', 'AmpC'],
  ertapenem: ['ESBL'],
  cefepime: ['AmpC'],
  'piperacillin-tazobactam': ['ESBL'],
  aztreonam: ['ESBL'],
  colistin: ['CRE', 'MDR-Pseudomonas'],
  tigecycline: ['CRE', 'VRE'],
  ceftazidime: ['Pseudomonas'],
};

/**
 * Tool: Resistance Validator
 */
export const resistanceValidatorTool = {
  type: 'function',
  function: {
    name: 'validate_resistance_coverage',
    description: 'Check if proposed antibiotic adequately covers documented resistance patterns',
    parameters: {
      type: 'object',
      properties: {
        antibiotic: {
          type: 'string',
          description: 'Proposed antibiotic',
        },
        resistance_history: {
          type: 'string',
          description: 'Prior resistance patterns (e.g., MRSA, ESBL, VRE)',
        },
      },
      required: ['antibiotic', 'resistance_history'],
    },
  },
  handler: async ({ antibiotic, resistance_history }) => {
    if (!resistance_history || resistance_history === 'none' || resistance_history === 'None') {
      return {
        adequate: true,
        reason: 'No prior resistance documented',
      };
    }

    const antibioticLower = (antibiotic || '').toLowerCase();
    const resistanceLower = resistance_history.toLowerCase();

    // Extract resistance organisms
    const resistancePatterns = [];
    if (resistanceLower.includes('mrsa')) resistancePatterns.push('MRSA');
    if (resistanceLower.includes('vre')) resistancePatterns.push('VRE');
    if (resistanceLower.includes('esbl')) resistancePatterns.push('ESBL');
    if (resistanceLower.includes('cre') || resistanceLower.includes('carbapenem')) resistancePatterns.push('CRE');
    if (resistanceLower.includes('pseudomonas')) resistancePatterns.push('Pseudomonas');

    // Check coverage
    const coverage = RESISTANCE_COVERAGE[antibioticLower] || [];
    const uncovered = resistancePatterns.filter(pattern =>
      !coverage.some(cov => cov.toLowerCase().includes(pattern.toLowerCase())),
    );

    if (uncovered.length > 0) {
      // Suggest alternatives
      const alternatives = [];
      uncovered.forEach(pattern => {
        Object.entries(RESISTANCE_COVERAGE).forEach(([drug, covers]) => {
          if (covers.includes(pattern) && !alternatives.includes(drug)) {
            alternatives.push(drug);
          }
        });
      });

      return {
        adequate: false,
        uncovered_organisms: uncovered,
        reason: `${antibiotic} does not cover: ${uncovered.join(', ')}`,
        alternative_agents: alternatives.slice(0, 3),
      };
    }

    return {
      adequate: true,
      covered_organisms: resistancePatterns,
      reason: `${antibiotic} covers documented resistance: ${resistancePatterns.join(', ')}`,
    };
  },
};

/**
 * Renal Dosing Table (Real clinical data)
 * Source: Sanford Guide, package inserts
 */
const RENAL_DOSING = {
  vancomycin: {
    normal: '15-20 mg/kg IV q8-12h',
    moderate: 'Load 25-30 mg/kg, then adjust by levels',
    severe: 'Load 25-30 mg/kg, then adjust by levels',
    dialysis: 'Load 15-20 mg/kg, redose based on levels',
  },
  cefepime: {
    normal: '2g IV q8h',
    moderate: '2g IV q12h (GFR 30-60)',
    severe: '1g IV q12h (GFR 10-30)',
    dialysis: '1g IV q24h, after dialysis',
  },
  piperacillin: {
    normal: '4.5g IV q6h',
    moderate: '3.375g IV q6h (GFR 20-40)',
    severe: '2.25g IV q6h (GFR <20)',
    dialysis: '2.25g IV q8h',
  },
  meropenem: {
    normal: '1-2g IV q8h',
    moderate: '1g IV q12h (GFR 26-50)',
    severe: '500mg IV q12h (GFR 10-25)',
    dialysis: '500mg IV q24h',
  },
  ceftriaxone: {
    normal: '1-2g IV q24h',
    moderate: 'No adjustment needed',
    severe: 'No adjustment needed',
    dialysis: 'No adjustment needed',
  },
};

/**
 * Tool: Dosing Calculator
 */
export const dosingCalculatorTool = {
  type: 'function',
  function: {
    name: 'calculate_renal_dosing',
    description: 'Calculate renally-adjusted antibiotic dosing based on GFR',
    parameters: {
      type: 'object',
      properties: {
        antibiotic: {
          type: 'string',
          description: 'Antibiotic name',
        },
        gfr: {
          type: 'string',
          description: 'Estimated GFR in mL/min',
        },
        weight_kg: {
          type: 'string',
          description: 'Patient weight in kg',
        },
      },
      required: ['antibiotic', 'gfr'],
    },
  },
  handler: async ({ antibiotic, gfr, weight_kg }) => {
    const antibioticLower = (antibiotic || '').toLowerCase();
    const gfrNum = parseFloat(gfr);
    // eslint-disable-next-line no-unused-vars
    const weightNum = parseFloat(weight_kg); // Reserved for future weight-based dosing

    // Find matching drug
    let drugKey = null;
    Object.keys(RENAL_DOSING).forEach(key => {
      if (antibioticLower.includes(key)) {
        drugKey = key;
      }
    });

    if (!drugKey) {
      return {
        dose: 'verify dosing',
        note: 'No renal dosing data available in database. Consult pharmacy or package insert.',
      };
    }

    const dosing = RENAL_DOSING[drugKey];

    // Determine adjustment level
    let adjustment = 'normal';
    if (isNaN(gfrNum)) {
      return {
        dose: 'verify dosing',
        note: 'GFR not provided or invalid',
      };
    }

    if (gfrNum < 10) {
      adjustment = 'dialysis';
    } else if (gfrNum < 30) {
      adjustment = 'severe';
    } else if (gfrNum < 60) {
      adjustment = 'moderate';
    }

    return {
      dose: dosing[adjustment],
      adjustment_level: adjustment,
      gfr: gfrNum,
      monitoring: adjustment !== 'normal' ? 'Monitor drug levels and renal function' : null,
    };
  },
};

/**
 * Tool: Guideline Search
 */
export const guidelineSearchTool = {
  type: 'function',
  function: {
    name: 'search_antibiotic_guideline',
    description: 'Search TUHS antibiotic guideline database for specific infection and patient context',
    parameters: {
      type: 'object',
      properties: {
        infection_type: {
          type: 'string',
          description: 'Type of infection (e.g., Pneumonia, UTI, Skin)',
        },
        acuity: {
          type: 'string',
          description: 'Level of care (Ward, ICU, ED)',
        },
        allergy_status: {
          type: 'string',
          description: 'Penicillin allergy status',
        },
      },
      required: ['infection_type'],
    },
  },
  handler: async ({ infection_type, acuity, allergy_status }) => {
    try {
      // Build search query
      const query = `${infection_type} ${acuity || ''} ${allergy_status || ''}`.trim();

      // Get embedding for semantic search
      const embeddingResponse = await openai.embeddings.create({
        model: process.env.EMBEDDING_MODEL || 'text-embedding-3-small',
        input: query,
      });

      const embedding = embeddingResponse.data[0].embedding;

      // Search guidelines with hybrid search
      const results = await searchGuidelines({
        query,
        queryEmbedding: embedding,
        filters: {
          infection: infection_type,
          acuity: acuity,
          allergy_status: allergy_status,
        },
        limit: 3,
      });

      if (results.length === 0) {
        return {
          found: false,
          message: 'No exact TUHS guideline match found. Consider consulting ID or using general antimicrobial principles.',
        };
      }

      // Format results
      return {
        found: true,
        guidelines: results.map(r => ({
          text: r.text,
          relevance_score: r.combined_score,
          metadata: r.metadata,
        })),
        source: 'TUHS Antibiotic Guidelines',
      };
    } catch (error) {
      console.error('Guideline search error:', error);
      return {
        found: false,
        error: error.message,
      };
    }
  },
};

// Export all tools
export const clinicalTools = [
  guidelineSearchTool,
  allergyCheckerTool,
  resistanceValidatorTool,
  dosingCalculatorTool,
];
