#!/usr/bin/env node
import { initializeDatabase, checkDatabaseHealth, closeDatabase } from '../lib/knowledgeBase.js';
import dotenv from 'dotenv';

dotenv.config();

async function main() {
  console.log('🗄️  Setting up PostgreSQL database with pgvector...\n');

  // Check database connection
  console.log('Checking database connection...');
  const isHealthy = await checkDatabaseHealth();
  
  if (!isHealthy) {
    console.error('❌ Cannot connect to database. Please check:');
    console.error('   1. PostgreSQL is running');
    console.error('   2. DATABASE_URL in .env is correct');
    console.error('   3. Database exists and is accessible\n');
    process.exit(1);
  }

  console.log('✅ Database connection successful\n');

  // Initialize schema
  console.log('Creating tables and indexes...');
  try {
    await initializeDatabase();
    console.log('✅ Database schema created successfully\n');
    
    console.log('📋 Created:');
    console.log('   - antibiotic_guidelines table');
    console.log('   - pgvector extension');
    console.log('   - Vector similarity indexes');
    console.log('   - Full-text search indexes');
    console.log('   - Metadata indexes\n');
    
    console.log('✅ Database setup complete!');
    console.log('Next step: Run "npm run load:knowledge" to populate guidelines\n');
  } catch (error) {
    console.error('❌ Database setup failed:', error.message);
    process.exit(1);
  } finally {
    await closeDatabase();
  }
}

main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
