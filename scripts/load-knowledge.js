#!/usr/bin/env node
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { insertGuidelineChunk, getGuidelineCount, clearGuidelines, closeDatabase } from '../lib/knowledgeBase.js';
import OpenAI from 'openai';
import dotenv from 'dotenv';

dotenv.config();

// Initialize OpenAI for embeddings via OpenRouter
const openai = new OpenAI({
  apiKey: process.env.OPENROUTER_API_KEY,
  baseURL: 'https://openrouter.ai/api/v1',
});

/**
 * Parse ABXguideInp.json and create chunks
 */
async function parseGuidelines() {
  console.log('📖 Reading ABXguideInp.json...');
  
  const filePath = resolve(process.cwd(), 'ABXguideInp.json');
  const content = await readFile(filePath, 'utf-8');
  const data = JSON.parse(content);

  console.log(`✅ Loaded guideline: ${data.document_title}\n`);

  const chunks = [];

  // Process each infection guideline
  for (const guideline of data.infection_guidelines || []) {
    const infection = guideline.infection;

    for (const subSection of guideline.sub_sections || []) {
      const subtype = subSection.type;

      // Each empiric regimen becomes a chunk
      for (const regimen of subSection.empiric_regimens || []) {
        const chunkText = buildChunkText({
          infection,
          subtype,
          allergyStatus: regimen.pcp_allergy_status,
          allergyDetails: regimen.allergy_details,
          regimen: regimen.regimen,
          duration: regimen.duration,
          generalNotes: subSection.general_notes,
        });

        const metadata = {
          source: 'ABXguideInp.json',
          infection: infection,
          subtype: subtype,
          allergy_status: regimen.pcp_allergy_status,
          keywords: extractKeywords(regimen.regimen),
        };

        chunks.push({
          documentId: 'TUHS-ABX-2024',
          chunkText,
          metadata,
        });
      }
    }
  }

  console.log(`✅ Created ${chunks.length} guideline chunks\n`);
  return chunks;
}

/**
 * Build readable chunk text
 */
function buildChunkText({ infection, subtype, allergyStatus, allergyDetails, regimen, duration, generalNotes }) {
  const lines = [
    `Infection: ${infection}`,
    `Type: ${subtype}`,
    `Allergy Status: ${allergyStatus}`,
  ];

  if (allergyDetails) {
    lines.push(`Allergy Details: ${allergyDetails}`);
  }

  lines.push('');
  lines.push('Empiric Regimen:');
  
  if (Array.isArray(regimen)) {
    regimen.forEach(item => lines.push(`- ${item}`));
  } else {
    lines.push(`- ${regimen}`);
  }

  lines.push('');
  lines.push(`Duration: ${duration}`);

  if (generalNotes && generalNotes.length > 0) {
    lines.push('');
    lines.push('Notes:');
    generalNotes.forEach(note => lines.push(`- ${note}`));
  }

  return lines.join('\n');
}

/**
 * Extract antibiotic keywords from regimen
 */
function extractKeywords(regimen) {
  const keywords = [];
  const text = Array.isArray(regimen) ? regimen.join(' ') : regimen;
  const lowerText = text.toLowerCase();

  const antibiotics = [
    'vancomycin', 'ceftriaxone', 'cefepime', 'azithromycin', 'levofloxacin',
    'piperacillin', 'tazobactam', 'meropenem', 'aztreonam', 'metronidazole',
    'ampicillin', 'sulbactam', 'doxycycline', 'linezolid', 'daptomycin',
  ];

  antibiotics.forEach(abx => {
    if (lowerText.includes(abx)) {
      keywords.push(abx);
    }
  });

  return keywords;
}

/**
 * Generate embeddings for chunks
 */
async function generateEmbeddings(chunks) {
  console.log('🧠 Generating embeddings...');
  const embeddingModel = process.env.EMBEDDING_MODEL || 'text-embedding-3-small';
  
  const chunksWithEmbeddings = [];
  const batchSize = 100; // OpenAI allows batching

  for (let i = 0; i < chunks.length; i += batchSize) {
    const batch = chunks.slice(i, i + batchSize);
    const texts = batch.map(c => c.chunkText);

    console.log(`   Processing batch ${Math.floor(i / batchSize) + 1}/${Math.ceil(chunks.length / batchSize)}...`);

    try {
      const response = await openai.embeddings.create({
        model: embeddingModel,
        input: texts,
      });

      batch.forEach((chunk, idx) => {
        chunksWithEmbeddings.push({
          ...chunk,
          embedding: response.data[idx].embedding,
        });
      });
    } catch (error) {
      console.error(`   ❌ Error generating embeddings for batch: ${error.message}`);
      throw error;
    }
  }

  console.log(`✅ Generated ${chunksWithEmbeddings.length} embeddings\n`);
  return chunksWithEmbeddings;
}

/**
 * Insert chunks into database
 */
async function insertChunks(chunks) {
  console.log('💾 Inserting chunks into database...');
  
  let inserted = 0;
  for (const chunk of chunks) {
    try {
      await insertGuidelineChunk(chunk);
      inserted++;
      
      if (inserted % 10 === 0) {
        process.stdout.write(`   Inserted ${inserted}/${chunks.length}\r`);
      }
    } catch (error) {
      console.error(`\n   ❌ Error inserting chunk: ${error.message}`);
      throw error;
    }
  }

  console.log(`\n✅ Inserted ${inserted} chunks into database\n`);
}

/**
 * Main execution
 */
async function main() {
  console.log('🚀 Loading TUHS Antibiotic Guidelines into Knowledge Base\n');

  try {
    // Check if guidelines already exist
    const existingCount = await getGuidelineCount();
    
    if (existingCount > 0) {
      console.log(`⚠️  Found ${existingCount} existing guideline chunks.`);
      console.log('   Clearing database to reload fresh data...\n');
      await clearGuidelines();
    }

    // Parse guidelines
    const chunks = await parseGuidelines();

    // Generate embeddings
    const chunksWithEmbeddings = await generateEmbeddings(chunks);

    // Insert into database
    await insertChunks(chunksWithEmbeddings);

    // Verify
    const finalCount = await getGuidelineCount();
    console.log('✅ Knowledge base loaded successfully!');
    console.log(`📊 Total chunks in database: ${finalCount}\n`);

    console.log('Next step: Start the server with "npm start"\n');

  } catch (error) {
    console.error('❌ Failed to load knowledge base:', error.message);
    console.error(error.stack);
    process.exit(1);
  } finally {
    await closeDatabase();
  }
}

main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
