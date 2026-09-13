import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { expandGalleries, loadAttachmentsFromXml } from './wp-content.mjs';

const ROOT = path.resolve(import.meta.dirname, '..');
const args = process.argv.slice(2).filter((arg) => arg !== '--download');
const shouldDownload = process.argv.includes('--download');
const XML_PATH = args[0] || path.join(ROOT, 'live.WordPress.2026-09-13.xml');
const SHOWS_DIR = path.join(ROOT, 'src', 'content', 'shows');
const ATTACHMENTS_JSON = path.join(ROOT, 'src', 'data', 'attachments.json');
const HEADERS = {
  Accept: 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
  'User-Agent':
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
};

function collectGalleryIds(text) {
  const ids = new Set();
  for (const match of text.matchAll(/\[gallery\s+([^\]]+)\]/gi)) {
    const attrs = match[1].replace(/[“”]/g, '"');
    const raw = attrs.match(/ids\s*=\s*["']([^"']+)["']/i)?.[1] ?? '';
    for (const id of raw.split(',')) {
      if (id.trim()) ids.add(id.trim());
    }
  }
  return ids;
}

async function downloadMissing(attachments, neededIds) {
  let saved = 0;
  let skipped = 0;
  for (const id of neededIds) {
    const item = attachments[id];
    if (!item?.src) {
      skipped += 1;
      continue;
    }
    const dest = path.join(ROOT, 'public', item.src.replace(/^\//, ''));
    try {
      await readFile(dest);
      continue;
    } catch {
      // download
    }
    const remote = `https://opencomm.net/wp-content/${item.src.replace(/^\/uploads\//, 'uploads/')}`;
    try {
      await mkdir(path.dirname(dest), { recursive: true });
      const response = await fetch(remote, { headers: HEADERS });
      const type = response.headers.get('content-type') || '';
      if (!response.ok || !type.startsWith('image/')) {
        skipped += 1;
        continue;
      }
      await writeFile(dest, Buffer.from(await response.arrayBuffer()));
      saved += 1;
      console.log(`saved ${id} ${item.src}`);
    } catch {
      skipped += 1;
    }
  }
  return { saved, skipped };
}

async function main() {
  const attachments = await loadAttachmentsFromXml(XML_PATH);
  await writeFile(ATTACHMENTS_JSON, `${JSON.stringify(attachments, null, 2)}\n`);

  const { readdir } = await import('node:fs/promises');
  const files = (await readdir(SHOWS_DIR)).filter((name) => name.endsWith('.md'));
  const neededIds = new Set();
  let updated = 0;

  for (const file of files) {
    const filePath = path.join(SHOWS_DIR, file);
    const raw = await readFile(filePath, 'utf8');
    for (const id of collectGalleryIds(raw)) neededIds.add(id);
    const next = expandGalleries(raw, attachments);
    if (next !== raw) {
      await writeFile(filePath, next);
      updated += 1;
    }
  }

  console.log(`attachments ${Object.keys(attachments).length}`);
  console.log(`updated ${updated} markdown files`);
  console.log(`gallery ids ${neededIds.size}`);
  console.log(`wrote ${path.relative(ROOT, ATTACHMENTS_JSON)}`);

  if (shouldDownload) {
    const { saved, skipped } = await downloadMissing(attachments, neededIds);
    console.log(`downloaded ${saved}, missing ${skipped}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
