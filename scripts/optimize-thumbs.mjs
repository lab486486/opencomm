import { mkdir, readFile, readdir, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SHOWS_DIR = path.join(ROOT, 'src', 'content', 'shows');
const UPLOADS_DIR = path.join(ROOT, 'public', 'uploads');
const THUMBS_DIR = path.join(ROOT, 'public', 'thumbs', '640x400');
/** Match .show-thumb aspect-ratio 16/10 card display size */
const WIDTH = 640;
const HEIGHT = 400;
const QUALITY = 65;

async function showFiles() {
  const names = await readdir(SHOWS_DIR);
  return names.filter((name) => name.endsWith('.md')).map((name) => path.join(SHOWS_DIR, name));
}

function thumbnailFromFrontmatter(text) {
  const match = text.match(/^thumbnail:\s*["']?([^"'\n]+)["']?/m);
  return match?.[1]?.trim() || '';
}

async function collectThumbnails() {
  const files = await showFiles();
  const thumbs = new Set();
  for (const file of files) {
    const text = await readFile(file, 'utf8');
    const value = thumbnailFromFrontmatter(text);
    if (value.startsWith('/uploads/')) thumbs.add(value);
  }
  return [...thumbs];
}

async function ensureDir(dir) {
  await mkdir(dir, { recursive: true });
}

async function isNewer(target, source) {
  try {
    const [a, b] = await Promise.all([stat(target), stat(source)]);
    return a.mtimeMs >= b.mtimeMs;
  } catch {
    return false;
  }
}

async function needsRebuild(dest, source) {
  try {
    const meta = await sharp(dest).metadata();
    if (meta.width !== WIDTH || meta.height !== HEIGHT) return true;
    return !(await isNewer(dest, source));
  } catch {
    return true;
  }
}

async function convert(srcUrl) {
  const relative = srcUrl.slice('/uploads/'.length);
  const source = path.join(UPLOADS_DIR, relative);
  const destRel = relative.replace(/\.[^.]+$/, '.webp');
  const dest = path.join(THUMBS_DIR, destRel);
  await ensureDir(path.dirname(dest));
  if (!(await needsRebuild(dest, source))) return 'skip';
  try {
    await sharp(source)
      .rotate()
      .resize({ width: WIDTH, height: HEIGHT, fit: 'cover', position: 'attention' })
      .webp({ quality: QUALITY, effort: 6 })
      .toFile(dest);
    return 'ok';
  } catch (error) {
    console.warn(`thumb fail ${srcUrl}: ${error.message}`);
    return 'fail';
  }
}

const thumbs = await collectThumbnails();
let ok = 0;
let skip = 0;
let fail = 0;
for (const src of thumbs) {
  const result = await convert(src);
  if (result === 'ok') ok += 1;
  else if (result === 'skip') skip += 1;
  else fail += 1;
}

const stamp = `${new Date().toISOString()}\n`;
await ensureDir(THUMBS_DIR);
await writeFile(path.join(THUMBS_DIR, '.stamp'), stamp);
console.log(`thumbs ${thumbs.length}개: 생성 ${ok}, 유지 ${skip}, 실패 ${fail}`);
