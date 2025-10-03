import pg from 'pg';
import dotenv from 'dotenv';

dotenv.config();

const { Pool } = pg;

// Create connection pool
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

/**
 * Check database health
 */
export async function checkDatabaseHealth() {
  try {
    const result = await pool.query('SELECT 1');
    return result.rowCount === 1;
  } catch (error) {
    console.error('Database health check failed:', error);
    return false;
  }
}

/**
 * Initialize database schema
 */
export async function initializeDatabase() {
  const client = await pool.connect();

  try {
    await client.query('BEGIN');

    // Enable pgvector extension
    await client.query('CREATE EXTENSION IF NOT EXISTS vector');

    // Create guidelines table
    await client.query(`
      CREATE TABLE IF NOT EXISTS antibiotic_guidelines (
        id SERIAL PRIMARY KEY,
        document_id VARCHAR(100) NOT NULL,
        chunk_text TEXT NOT NULL,
        chunk_metadata JSONB NOT NULL DEFAULT '{}',
        embedding vector(${process.env.EMBEDDING_DIMENSIONS || 1536}),
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
      )
    `);

    // Create indexes for hybrid search
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_embedding_cosine 
      ON antibiotic_guidelines 
      USING ivfflat (embedding vector_cosine_ops)
      WITH (lists = 100)
    `);

    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_metadata_gin 
      ON antibiotic_guidelines 
      USING gin (chunk_metadata)
    `);

    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_fulltext 
      ON antibiotic_guidelines 
      USING gin (to_tsvector('english', chunk_text))
    `);

    // Create indexes on metadata fields
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_metadata_infection 
      ON antibiotic_guidelines ((chunk_metadata->>'infection'))
    `);

    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_metadata_acuity 
      ON antibiotic_guidelines ((chunk_metadata->>'acuity'))
    `);

    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_document_id 
      ON antibiotic_guidelines (document_id)
    `);

    await client.query('COMMIT');
    console.log('✅ Database schema initialized successfully');
  } catch (error) {
    await client.query('ROLLBACK');
    console.error('❌ Database initialization failed:', error);
    throw error;
  } finally {
    client.release();
  }
}

/**
 * Insert guideline chunk with embedding
 */
export async function insertGuidelineChunk({
  documentId,
  chunkText,
  metadata,
  embedding,
}) {
  const client = await pool.connect();

  try {
    const result = await client.query(
      `INSERT INTO antibiotic_guidelines 
       (document_id, chunk_text, chunk_metadata, embedding) 
       VALUES ($1, $2, $3, $4) 
       RETURNING id`,
      [documentId, chunkText, JSON.stringify(metadata), JSON.stringify(embedding)],
    );

    return result.rows[0].id;
  } catch (error) {
    console.error('Failed to insert guideline chunk:', error);
    throw error;
  } finally {
    client.release();
  }
}

/**
 * Hybrid search: combines semantic (vector) and keyword (full-text) search
 */
export async function searchGuidelines({
  query,
  queryEmbedding,
  filters = {},
  limit = 3,
  semanticWeight = 0.6,
  keywordWeight = 0.4,
}) {
  const client = await pool.connect();

  try {
    // Build metadata filter conditions
    const filterConditions = [];
    const filterValues = [];
    let paramIndex = 1;

    if (filters.infection) {
      filterConditions.push(`chunk_metadata->>'infection' = $${paramIndex}`);
      filterValues.push(filters.infection);
      paramIndex++;
    }

    if (filters.acuity) {
      filterConditions.push(`chunk_metadata->>'acuity' LIKE $${paramIndex}`);
      filterValues.push(`%${filters.acuity}%`);
      paramIndex++;
    }

    if (filters.allergy_status) {
      filterConditions.push(`chunk_metadata->>'allergy_status' = $${paramIndex}`);
      filterValues.push(filters.allergy_status);
      paramIndex++;
    }

    const whereClause = filterConditions.length > 0
      ? `WHERE ${filterConditions.join(' AND ')}`
      : '';

    // Hybrid search query
    const queryText = `
      SELECT 
        id,
        chunk_text,
        chunk_metadata,
        (embedding <=> $${paramIndex}::vector) AS semantic_distance,
        ts_rank(to_tsvector('english', chunk_text), plainto_tsquery('english', $${paramIndex + 1})) AS keyword_score,
        (
          ($${paramIndex + 2}::float * (1 - (embedding <=> $${paramIndex}::vector))) + 
          ($${paramIndex + 3}::float * ts_rank(to_tsvector('english', chunk_text), plainto_tsquery('english', $${paramIndex + 1})))
        ) AS combined_score
      FROM antibiotic_guidelines
      ${whereClause}
      ORDER BY combined_score DESC
      LIMIT $${paramIndex + 4}
    `;

    const queryParams = [
      ...filterValues,
      JSON.stringify(queryEmbedding),
      query,
      semanticWeight,
      keywordWeight,
      limit,
    ];

    const result = await client.query(queryText, queryParams);

    return result.rows.map(row => ({
      id: row.id,
      text: row.chunk_text,
      metadata: row.chunk_metadata,
      semantic_distance: parseFloat(row.semantic_distance),
      keyword_score: parseFloat(row.keyword_score),
      combined_score: parseFloat(row.combined_score),
    }));
  } catch (error) {
    console.error('Search failed:', error);
    throw error;
  } finally {
    client.release();
  }
}

/**
 * Get guideline count
 */
export async function getGuidelineCount() {
  const client = await pool.connect();
  try {
    const result = await client.query('SELECT COUNT(*) FROM antibiotic_guidelines');
    return parseInt(result.rows[0].count);
  } finally {
    client.release();
  }
}

/**
 * Clear all guidelines
 */
export async function clearGuidelines() {
  const client = await pool.connect();
  try {
    await client.query('TRUNCATE antibiotic_guidelines RESTART IDENTITY CASCADE');
    console.log('✅ Guidelines cleared');
  } finally {
    client.release();
  }
}

/**
 * Get knowledge base for Agno agent
 */
export function getKnowledgeBase() {
  // This will be used by Agno's knowledge parameter
  // For now, we handle knowledge retrieval via tools
  return null;
}

/**
 * Close database connection pool
 */
export async function closeDatabase() {
  await pool.end();
  console.log('Database connection pool closed');
}
