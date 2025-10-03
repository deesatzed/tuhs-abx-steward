import { appendFile, mkdir } from 'node:fs/promises';
import { extname, join, resolve } from 'node:path';

const DEFAULT_LOG_DIR = 'logs';
const DEFAULT_PREFIX = 'audit';
const preparedDirectories = new Set();

const isFilePath = (value) => Boolean(value && extname(value));

const ensureDirectory = async (directory) => {
  const absolute = resolve(directory);
  if (preparedDirectories.has(absolute)) {
    return absolute;
  }

  await mkdir(absolute, { recursive: true });
  preparedDirectories.add(absolute);
  return absolute;
};

const buildFilePath = async ({ customPath, date }) => {
  if (isFilePath(customPath)) {
    const absoluteFile = resolve(customPath);
    await ensureDirectory(resolve(absoluteFile, '..'));
    return absoluteFile;
  }

  const directory = await ensureDirectory(customPath || DEFAULT_LOG_DIR);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const fileName = `${DEFAULT_PREFIX}-${year}-${month}-${day}.log`;
  return join(directory, fileName);
};

export const recordAuditEntry = async ({
  request_id,
  input,
  recommendation,
  confidence,
  tool_calls,
  duration_ms,
  status = 'success',
  error,
  logPath,
  timestamp,
}) => {
  const date = timestamp instanceof Date ? timestamp : new Date();
  const filePath = await buildFilePath({ customPath: logPath, date });

  const entry = {
    timestamp: date.toISOString(),
    request_id,
    status,
    input,
    recommendation,
    confidence,
    tool_calls,
    duration_ms,
    error,
  };

  await appendFile(filePath, `${JSON.stringify(entry)}\n`, 'utf8');
};
