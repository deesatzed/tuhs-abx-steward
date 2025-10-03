import OpenAI from 'openai';
import { selectModel, calculateComplexity } from './modelRouter.js';
import {
  allergyCheckerTool,
  resistanceValidatorTool,
  dosingCalculatorTool,
  guidelineSearchTool,
} from './clinicalTools.js';
import { buildPromptVariables } from './promptBuilder.js';

/**
 * Create OpenAI client configured for OpenRouter
 */
function createOpenRouterClient() {
  return new OpenAI({
    apiKey: process.env.OPENROUTER_API_KEY,
    baseURL: process.env.OPENROUTER_BASE_URL || 'https://openrouter.ai/api/v1',
    defaultHeaders: {
      'HTTP-Referer': process.env.OPENROUTER_SITE_URL || '',
      'X-Title': process.env.OPENROUTER_SITE_NAME || 'TUHS Antibiotic Steward',
    },
  });
}

/**
 * Build system instructions
 */
function buildSystemInstructions() {
  return [
    'You are a clinical antibiotic stewardship assistant for TUHS (Temple University Health System).',
    'Your role is to provide evidence-based antibiotic recommendations following TUHS guidelines.',
    '',
    'CRITICAL RULES:',
    '1. ALWAYS search the TUHS guideline knowledge base FIRST before considering any other approach',
    '2. ALWAYS check allergies for beta-lactam antibiotics (penicillins, cephalosporins, carbapenems)',
    '3. ALWAYS validate resistance coverage when prior resistance is documented',
    '4. ALWAYS calculate renal-adjusted dosing when GFR < 60',
    '5. Prioritize TUHS guideline > External literature > General knowledge',
    '',
    'MANDATORY WORKFLOW:',
    'FIRST: Use the search_antibiotic_guideline tool to query TUHS guidelines',
    'THEN: Use allergy and resistance tools as needed based on patient data',
    'FINALLY: Provide recommendation with TUHS guidelines as primary evidence',
    '',
    'OUTPUT FORMAT (CONCISE & CLINICIAN-FOCUSED):',
    '## Clinical Assessment (2-3 sentences)',
    '## Primary Recommendation',
    '## Alternative Options (if applicable)',
    '## Monitoring & Stewardship',
    '## Confidence & Rationale',
    '## Citations',
    '',
    'BRIEF_JSON FORMAT (no code block):',
    '{"top_recommendation":{"agent":"<drug>","route":"<IV/PO>","dose":"<adjusted dose>","rationale":"<clinical justification>"},"confidence":"<High|Medium|Low>","alternative_or_considerations":"<brief alternatives>","non_tuhs_source":"<source if not TUHS>"}',
    '',
    'KEY PRINCIPLES:',
    '- Be concise: Focus on actionable recommendations, not lengthy explanations',
    '- Prioritize: Most important information first',
    '- Structure: Use clear sections for quick scanning',
    '- Evidence-based: Cite TUHS guidelines when available',
    '- Renal dosing: Always adjust for GFR < 60',
    '- Avoid repetition: Don\'t repeat patient data or obvious information',
  ].join('\n');
}

/**
 * Convert clinical tools to OpenAI function format
 */
function getToolDefinitions() {
  return [
    guidelineSearchTool,
    allergyCheckerTool,
    resistanceValidatorTool,
    dosingCalculatorTool,
  ].map(tool => ({
    type: 'function',
    function: tool.function,
  }));
}

/**
 * Calculate confidence score based on agent output
 */
function calculateConfidence(agentResult, toolResults) {
  let score = 0;
  const factors = [];

  // Factor 1: Guideline source (0-40 points)
  if (agentResult.sources?.includes('TUHS JSON')) {
    score += 40;
    factors.push({ factor: 'TUHS JSON guideline match', points: 40 });
  } else if (agentResult.sources?.includes('TUHS PDF')) {
    score += 30;
    factors.push({ factor: 'TUHS PDF guideline match', points: 30 });
  } else {
    score += 10;
    factors.push({ factor: 'External source only', points: 10 });
  }

  // Factor 2: Allergy validation (0-15 points)
  const allergyCheck = toolResults.find(t => t.tool === 'check_allergy_contraindication');
  if (allergyCheck?.result?.safe !== false) {
    score += 15;
    factors.push({ factor: 'No allergy contraindications', points: 15 });
  }

  // Factor 3: Resistance coverage (0-15 points)
  const resistanceCheck = toolResults.find(t => t.tool === 'validate_resistance_coverage');
  if (resistanceCheck?.result?.adequate) {
    score += 15;
    factors.push({ factor: 'Adequate resistance coverage', points: 15 });
  }

  // Factor 4: No conflicts (0-20 points)
  if (!agentResult.conflicts || agentResult.conflicts.length === 0) {
    score += 20;
    factors.push({ factor: 'No guideline conflicts', points: 20 });
  }

  // Factor 5: Culture-directed (0-10 points)
  if (agentResult.culture_directed) {
    score += 10;
    factors.push({ factor: 'Culture-directed therapy', points: 10 });
  }

  const level = score >= 80 ? 'High' : score >= 50 ? 'Medium' : 'Low';

  return {
    score: Math.min(score, 100),
    level,
    factors,
  };
}

/**
 * Extract BRIEF_JSON from markdown output
 */
function extractBriefJson(text) {
  if (!text) return null;

  // Look for BRIEF_JSON followed by a JSON object (more robust parsing)
  const briefJsonRegex = /BRIEF_JSON[:\s]*({[\s\S]*?})(?:\s*$|\s*(?:\r?\n){2}|\s*```)/i;
  const match = text.match(briefJsonRegex);

  if (match) {
    try {
      const jsonText = match[1].trim();
      // Clean up any trailing content that might be in the JSON
      const cleanedJson = jsonText.replace(/,\s*}$/, '}').replace(/}\s*,/, '}');
      return JSON.parse(cleanedJson);
    } catch (e) {
      console.warn('Failed to parse BRIEF_JSON:', e);
      console.warn('Raw JSON text:', match[1]);
      return null;
    }
  }

  // Fallback: look for any JSON object at the end
  const lines = text.trim().split('\n');
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i].trim();
    if (line.startsWith('{') && line.endsWith('}')) {
      try {
        return JSON.parse(line);
      } catch (e) {
        // Continue searching
      }
    }
  }

  return null;
}

/**
 * Execute tool calls
 */
async function executeToolCalls(toolCalls) {
  const results = [];
  const toolHandlers = {
    'search_antibiotic_guideline': guidelineSearchTool.handler,
    'check_allergy_contraindication': allergyCheckerTool.handler,
    'validate_resistance_coverage': resistanceValidatorTool.handler,
    'calculate_renal_dosing': dosingCalculatorTool.handler,
  };

  for (const toolCall of toolCalls) {
    const handler = toolHandlers[toolCall.function.name];
    if (handler) {
      const args = JSON.parse(toolCall.function.arguments);
      const result = await handler(args);
      results.push({
        tool: toolCall.function.name,
        args,
        result,
      });
    }
  }

  return results;
}

/**
 * Main recommendation function with streaming
 */
export async function* getRecommendation(patientData) {
  const startTime = Date.now();

  try {
    // Normalize input variables
    const variables = buildPromptVariables(patientData);

    // Calculate complexity and select model
    const complexity = calculateComplexity(variables);
    const modelId = selectModel(complexity, variables);

    console.log(`Selected model: ${modelId} (complexity: ${complexity.score})`);

    // Create OpenRouter client
    const client = createOpenRouterClient();

    // Build patient narrative
    const patientNarrative = buildPatientNarrative(variables);

    // Track tool calls
    let toolResults = [];
    let fullContent = '';
    
    // Initial messages
    const messages = [
      { role: 'system', content: buildSystemInstructions() },
      { role: 'user', content: patientNarrative },
    ];

    // Agentic loop - allow up to 3 iterations for tool use
    for (let iteration = 0; iteration < 3; iteration++) {
      // Force guideline search on first iteration
      const forceGuidelineSearch = iteration === 0;

      const response = await client.chat.completions.create({
        model: modelId,
        messages,
        tools: getToolDefinitions(),
        tool_choice: forceGuidelineSearch ? 'required' : 'auto', // Force guideline search first
        stream: true,
        temperature: parseFloat(process.env.TEMPERATURE) || 0.1,
        max_tokens: parseInt(process.env.MAX_TOKENS) || 2000,
      });

      let assistantMessage = '';
      let toolCalls = [];

      // Stream chunks
      for await (const chunk of response) {
        const delta = chunk.choices[0]?.delta;

        if (delta?.content) {
          assistantMessage += delta.content;
          fullContent += delta.content;
          yield {
            type: 'content',
            content: delta.content,
          };
        }

        if (delta?.tool_calls) {
          // Accumulate tool calls
          for (const toolCall of delta.tool_calls) {
            if (!toolCalls[toolCall.index]) {
              toolCalls[toolCall.index] = {
                id: toolCall.id,
                type: 'function',
                function: { name: '', arguments: '' },
              };
            }
            if (toolCall.function?.name) {
              toolCalls[toolCall.index].function.name = toolCall.function.name;
            }
            if (toolCall.function?.arguments) {
              toolCalls[toolCall.index].function.arguments += toolCall.function.arguments;
            }
          }
        }
      }

      // If no tool calls, we're done (shouldn't happen on first iteration due to required)
      if (toolCalls.length === 0) {
        if (forceGuidelineSearch) {
          console.warn('No tools called despite required tool_choice');
        }
        break;
      }

      // Execute tools
      yield {
        type: 'tool_call',
        tool: toolCalls[0].function.name,
        status: 'executing',
      };

      const executedResults = await executeToolCalls(toolCalls);
      toolResults.push(...executedResults);

      yield {
        type: 'tool_call',
        tool: toolCalls[0].function.name,
        status: 'completed',
      };

      // Add assistant message and tool results to conversation
      messages.push({
        role: 'assistant',
        content: assistantMessage || null,
        tool_calls: toolCalls,
      });

      for (let i = 0; i < toolCalls.length; i++) {
        messages.push({
          role: 'tool',
          tool_call_id: toolCalls[i].id,
          content: JSON.stringify(executedResults[i].result),
        });
      }
    }

    // Extract BRIEF_JSON
    const briefJson = extractBriefJson(fullContent);

    // Calculate confidence
    const confidence = calculateConfidence(
      {
        sources: fullContent.includes('TUHS') ? ['TUHS JSON'] : [],
        culture_directed: variables.culture_results?.includes('susceptible'),
      },
      toolResults,
    );

    // Send completion event
    yield {
      type: 'complete',
      confidence,
      brief_json: briefJson,
      model_used: modelId,
      duration_ms: Date.now() - startTime,
    };

  } catch (error) {
    console.error('Agent service error:', error);

    // Try fallback model if primary fails
    if (!error.fallback_attempted) {
      console.log('Attempting fallback to simpler model...');
      error.fallback_attempted = true;

      const fallbackModel = process.env.FALLBACK_MODEL || 'openai/gpt-4o-mini';
      const variables = buildPromptVariables(patientData);
      
      try {
        const client = createOpenRouterClient();
        const response = await client.chat.completions.create({
          model: fallbackModel,
          messages: [
            { role: 'system', content: buildSystemInstructions() },
            { role: 'user', content: buildPatientNarrative(variables) },
          ],
          stream: true,
          temperature: 0.2,
          max_tokens: 1500,
        });

        let fullContent = '';
        for await (const chunk of response) {
          const delta = chunk.choices[0]?.delta;
          if (delta?.content) {
            fullContent += delta.content;
            yield { type: 'content', content: delta.content };
          }
        }

        yield {
          type: 'complete',
          confidence: { score: 60, level: 'Medium', factors: [{ factor: 'Fallback model used', points: 60 }] },
          brief_json: extractBriefJson(fullContent),
          model_used: fallbackModel,
        };

        return;
      } catch (fallbackError) {
        console.error('Fallback also failed:', fallbackError);
      }
    }

    throw new Error(`Failed to generate recommendation: ${error.message}`);
  }
}

/**
 * Build patient narrative for agent
 */
function buildPatientNarrative(variables) {
  const lines = [
    'Patient Case:',
    '',
    `Age: ${variables.age}`,
    `Weight: ${variables.weight_kg} kg`,
    `Estimated GFR: ${variables.gfr} mL/min`,
    `Acuity: ${variables.acuity}`,
    `Infection Source: ${variables.source_category}`,
    '',
    `Allergies: ${variables.allergies}`,
    `Culture Results: ${variables.culture_results}`,
    `Prior Resistance: ${variables.prior_resistance}`,
    `Source Risk Factors: ${variables.source_risk}`,
    `Infection-Specific Risks: ${variables.inf_risks}`,
    '',
    `Current Outpatient Antibiotics: ${variables.current_outpt_abx}`,
    `Current Inpatient Antibiotics: ${variables.current_inp_abx}`,
    '',
    'Please provide antibiotic recommendations following the output format specified in your instructions.',
  ];

  return lines.join('\n');
}
