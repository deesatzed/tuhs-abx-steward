import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { getRecommendation } from './lib/agentService.js';
import { recordAuditEntry } from './lib/auditLogger.js';
import { checkDatabaseHealth } from './lib/knowledgeBase.js';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));
app.use(express.json({ limit: '256kb' }));
app.use(express.static('public'));

// Health check endpoint
app.get('/api/health', async (req, res) => {
  try {
    const dbHealthy = await checkDatabaseHealth();
    
    res.json({
      status: 'healthy',
      version: '2.0.0',
      database: dbHealthy ? 'connected' : 'disconnected',
      llm_provider: 'openrouter',
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    res.status(503).json({
      status: 'unhealthy',
      error: error.message,
      timestamp: new Date().toISOString(),
    });
  }
});

// Main recommendation endpoint with streaming
app.post('/api/recommendation', async (req, res) => {
  const requestId = `req_${Date.now()}_${Math.random().toString(36).substring(7)}`;
  const startTime = Date.now();

  try {
    // Set headers for Server-Sent Events
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('X-Accel-Buffering', 'no'); // Disable nginx buffering

    // Send initial connection event
    res.write(`data: ${JSON.stringify({ type: 'connected', request_id: requestId })}\n\n`);

    // Get streaming recommendation
    const stream = await getRecommendation(req.body);

    let fullContent = '';
    let toolCalls = [];
    let confidence = null;

    // Stream chunks to client
    for await (const chunk of stream) {
      if (chunk.type === 'content') {
        fullContent += chunk.content;
        res.write(`data: ${JSON.stringify({ type: 'chunk', content: chunk.content })}\n\n`);
      } else if (chunk.type === 'tool_call') {
        toolCalls.push(chunk);
        res.write(`data: ${JSON.stringify({ type: 'tool_call', tool: chunk.tool, status: chunk.status })}\n\n`);
      } else if (chunk.type === 'complete') {
        confidence = chunk.confidence;
        res.write(`data: ${JSON.stringify({
          type: 'complete',
          confidence: chunk.confidence,
          brief_json: chunk.brief_json,
          model_used: chunk.model_used,
        })}\n\n`);
      }
    }

    // Send completion event
    const duration = Date.now() - startTime;
    res.write(`data: ${JSON.stringify({ type: 'done', duration_ms: duration })}\n\n`);
    res.end();

    // Audit logging (async, non-blocking)
    recordAuditEntry({
      request_id: requestId,
      input: req.body,
      recommendation: fullContent,
      confidence,
      tool_calls: toolCalls.map(t => t.tool),
      model_used: modelId,
      duration_ms: duration,
      status: 'success',
    }).catch(err => console.error('Audit log error:', err));

  } catch (error) {
    console.error('Recommendation error:', error);

    const duration = Date.now() - startTime;

    // Send error event
    res.write(`data: ${JSON.stringify({
      type: 'error',
      error: error.message,
      code: error.code || 'INTERNAL_ERROR',
    })}\n\n`);
    res.end();

    // Audit error
    recordAuditEntry({
      request_id: requestId,
      input: req.body,
      error: error.message,
      duration_ms: duration,
      status: 'error',
    }).catch(err => console.error('Audit log error:', err));
  }
});

// Non-streaming fallback endpoint (optional, for compatibility)
app.post('/api/recommendation/sync', async (req, res) => {
  const startTime = Date.now();

  try {
    const stream = await getRecommendation(req.body);

    let fullContent = '';
    let confidence = null;
    let briefJson = null;
    let modelUsed = null;

    for await (const chunk of stream) {
      if (chunk.type === 'content') {
        fullContent += chunk.content;
      } else if (chunk.type === 'complete') {
        confidence = chunk.confidence;
        briefJson = chunk.brief_json;
        modelUsed = chunk.model_used;
      }
    }

    const duration = Date.now() - startTime;

    res.json({
      success: true,
      recommendation: fullContent,
      confidence,
      brief_json: briefJson,
      model_used: modelUsed,
      duration_ms: duration,
    });

    recordAuditEntry({
      input: req.body,
      recommendation: fullContent,
      confidence,
      duration_ms: duration,
      status: 'success',
    }).catch(err => console.error('Audit log error:', err));

  } catch (error) {
    console.error('Sync recommendation error:', error);

    res.status(500).json({
      success: false,
      error: error.message,
    });

    recordAuditEntry({
      input: req.body,
      error: error.message,
      duration_ms: Date.now() - startTime,
      status: 'error',
    }).catch(err => console.error('Audit log error:', err));
  }
});

// Start server
const server = app.listen(PORT, () => {
  console.log(`🚀 Server running on http://localhost:${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/api/health`);
  console.log('🏥 Using OpenRouter for LLM access');
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, closing server gracefully...');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

export { app };
