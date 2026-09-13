import { access, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { expandGalleries, toLocalSrc } from './wp-content.mjs';

const ROOT = path.resolve(import.meta.dirname, '..');
const DEFAULT_XML = path.join(ROOT, 'live.WordPress.2026-09-13.xml');
const IMAGE_BASE = process.env.PUBLIC_IMAGE_BASE ?? '';
const HEADERS = {
  Accept: 'application/json,text/html;q=0.9,*/*;q=0.8',
  'User-Agent':
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
};

const WP_CATEGORY = {
  drama: 'drama',
  sport: 'sport',
  movie: 'movie',
  entertainment: 'entertainment',
};

const CHANNEL_RULES = [
  [/kbs\s*1|kbs1/i, 'KBS1'],
  [/kbs\s*2|kbs2/i, 'KBS2'],
  [/\bmbc\b|엠비씨/i, 'MBC'],
  [/\bsbs\b|스브스/i, 'SBS'],
  [/jtbc|제이티비씨/i, 'JTBC'],
  [/tv\s*조선|티비조선/i, 'TV조선'],
  [/채널\s*a|채널에이/i, '채널A'],
  [/\bmbn\b|엠비엔/i, 'MBN'],
  [/\btvn\b|티비엔|티빙/i, 'tvN'],
  [/\bena\b|이엔에이/i, 'ENA'],
];

function tag(block, name) {
  const match = block.match(
    new RegExp(`<${name}(?:\\s[^>]*)?>(?:<!\\[CDATA\\[(.*?)\\]\\]>|(.*?))</${name}>`, 's'),
  );
  if (!match) return '';
  return (match[1] ?? match[2] ?? '').trim();
}

function decodeSlug(value) {
  let text = String(value || '').trim();
  for (let i = 0; i < 3; i += 1) {
    try {
      const next = decodeURIComponent(text);
      if (next === text) break;
      text = next;
    } catch {
      break;
    }
  }
  return text;
}

function decodeHtml(value = '') {
  return value
    .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number(code)))
    .replace(/&#x([0-9a-f]+);/gi, (_, code) => String.fromCharCode(Number.parseInt(code, 16)))
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#039;|&apos;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&nbsp;/g, ' ')
    .trim();
}

function stripHtml(value = '') {
  return decodeHtml(value.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ')).trim();
}

function yamlValue(value) {
  if (value === undefined || value === null || value === '') return '';
  const text = String(value)
    .replace(/[\u0000-\u001F\u007F]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  return JSON.stringify(text);
}

function toYaml(data) {
  const lines = ['---'];
  for (const [key, value] of Object.entries(data)) {
    if (value === undefined || value === null || value === '') continue;
    if (Array.isArray(value)) {
      if (value.length === 0) {
        lines.push(`${key}: []`);
        continue;
      }
      lines.push(`${key}:`);
      for (const item of value) lines.push(`  - ${yamlValue(item)}`);
    } else if (typeof value === 'boolean' || typeof value === 'number') {
      lines.push(`${key}: ${value}`);
    } else {
      lines.push(`${key}: ${yamlValue(value)}`);
    }
  }
  lines.push('---', '');
  return lines.join('\n');
}

function showName(title) {
  return (
    title
      .replace(/\s*[|\-–].*$/, '')
      .replace(/\s*(실시간|무료|온에어|바로가기|보는법|보는방법|다시보기|재방송).*$/u, '')
      .replace(/^드라마\s*/, '')
      .trim() || title
  );
}

function showKey(name) {
  return name.toLowerCase().replace(/[^\w가-힣]+/g, '') || 'show';
}

function detectChannel(title, html) {
  const haystack = `${title} ${stripHtml(html)}`;
  for (const [pattern, name] of CHANNEL_RULES) {
    if (pattern.test(haystack)) return name;
  }
  return '';
}

function guessCategory(wpCats, title) {
  for (const cat of wpCats) {
    if (WP_CATEGORY[cat]) return WP_CATEGORY[cat];
  }
  if (/다운로드|엑셀|알약|고클린|곰플레이어|한셀|엣지|유니버셜|호스팅|도메인|콘서트|동덕여대/.test(title)) {
    return 'archive';
  }
  if (
    /^(ENA|KBS\s*1|KBS\s*2|KBS1|KBS2|MBC|SBS|JTBC|MBN|티비엔|티비조선|채널에이|채널A|티빙 할인|유플러스|지니티비|모바일 Btv|쿠팡플레이)/i.test(
      title,
    ) ||
    /온에어 티비|편성표|포인트 사용/.test(title)
  ) {
    return 'channel';
  }
  if (/올림픽|월드컵|중계|비보이|핸드볼|축구|테니스|펜싱|배드민턴|수영|태권도/.test(title) && !/드라마/.test(title)) {
    return 'sport';
  }
  if (/결말|원작|웹툰/.test(title) && !/실시간|온에어|보는법|보러가기/.test(title)) {
    return 'movie';
  }
  if (/예능|미스터트롯|음악일주/.test(title)) return 'entertainment';
  if (/실시간|온에어|보는법|보러가기|드라마/.test(title)) return 'drama';
  return 'archive';
}

function extractField(html, labels) {
  for (const label of labels) {
    const pattern = new RegExp(
      `${label}</div>\\s*<div[^>]*>\\s*([^<]+)`,
      'i',
    );
    const match = html.match(pattern);
    if (match) return decodeHtml(match[1]);
    const strong = html.match(
      new RegExp(`>${label}</strong>\\s*<span[^>]*>\\s*([^<]+)`, 'i'),
    );
    if (strong) return decodeHtml(strong[1]);
  }
  return '';
}

function extractWatchUrl(html) {
  const button = html.match(
    /<a[^>]+href=["']([^"']+)["'][^>]*>[\s\S]{0,120}(?:실시간|바로보기|온에어)/i,
  );
  if (button?.[1]) return button[1];
  return '';
}

function extractYoutube(html) {
  const embed = html.match(/\[embed\](https?:\/\/[^\]]+)\[\/embed\]/i);
  if (embed) return embed[1];
  const link = html.match(/https?:\/\/(?:www\.)?(?:youtube\.com|youtu\.be)[^\s"'<]+/i);
  return link?.[0] || '';
}

function cleanHtml(html) {
  return html
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/<blockquote class="wp-embedded-content"[\s\S]*?<\/blockquote>/gi, '')
    .replace(/<iframe class="wp-embedded-content"[\s\S]*?<\/iframe>/gi, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

async function saveImage(url) {
  if (!url || !url.includes('opencomm.net')) return url;
  const parsed = new URL(url);
  const relative = decodeURIComponent(parsed.pathname.replace('/wp-content/uploads/', ''));
  const dest = path.join(ROOT, 'public/uploads', relative);
  const publicPath = `/uploads/${relative.split(path.sep).join('/')}`;
  const served = IMAGE_BASE ? `${IMAGE_BASE}${publicPath}` : publicPath;
  try {
    await access(dest);
    return served;
  } catch {
    // download below
  }
  await mkdir(path.dirname(dest), { recursive: true });
  const response = await fetch(url, { headers: HEADERS });
  if (!response.ok) return url;
  await writeFile(dest, Buffer.from(await response.arrayBuffer()));
  return served;
}

async function rewriteImages(html) {
  const urls = [...html.matchAll(/src=["']([^"']+)["']/gi)].map((match) => match[1]);
  let next = html;
  for (const url of urls) {
    if (!url.includes('/wp-content/uploads/')) continue;
    const local = await saveImage(url);
    next = next.replaceAll(url, local);
  }
  return next;
}

function parseItems(xml) {
  return [...xml.matchAll(/<item>(.*?)<\/item>/gs)].map((match) => match[1]);
}

async function main() {
  const { readFile } = await import('node:fs/promises');
  const xmlPath = process.argv[2] || DEFAULT_XML;
  const xml = await readFile(xmlPath, 'utf8');
  await mkdir(path.join(ROOT, 'src/content/shows'), { recursive: true });

  const attachments = new Map();
  for (const block of parseItems(xml)) {
    if (tag(block, 'wp:post_type') !== 'attachment') continue;
    attachments.set(tag(block, 'wp:post_id'), tag(block, 'wp:attachment_url') || tag(block, 'guid'));
  }
  const attachmentIndex = Object.fromEntries(
    [...attachments].map(([id, url]) => [id, { src: toLocalSrc(url) || url, alt: '' }]),
  );

  const prepared = [];
  for (const block of parseItems(xml)) {
    if (tag(block, 'wp:post_type') !== 'post' || tag(block, 'wp:status') !== 'publish') {
      continue;
    }
    const id = Number(tag(block, 'wp:post_id'));
    const title = decodeHtml(tag(block, 'title'));
    const link = tag(block, 'link');
    const rawPath = new URL(link).pathname.replace(/\/$/, '').replace(/^\//, '');
    const entrySlug = decodeSlug(rawPath || tag(block, 'wp:post_name'));
    const wpCats = [...block.matchAll(/<category domain="category"[^>]*nicename="([^"]*)"/g)].map(
      (match) => decodeSlug(match[1]),
    );
    const html = expandGalleries(
      await rewriteImages(cleanHtml(tag(block, 'content:encoded'))),
      attachmentIndex,
    );
    const thumbId = block.match(/<wp:meta_key><!\[CDATA\[_thumbnail_id\]\]><\/wp:meta_key>\s*<wp:meta_value><!\[CDATA\[(\d+)\]\]>/);
    const featuredUrl = thumbId ? attachments.get(thumbId[1]) : '';
    const firstImg = html.match(/src=["']([^"']+)["']/);
    const thumbnail = featuredUrl ? await saveImage(featuredUrl) : firstImg?.[1];
    const name = showName(title);
    const category = guessCategory(wpCats, title);
    const excerpt = stripHtml(tag(block, 'excerpt:encoded') || html).slice(0, 180);

    prepared.push({
      title,
      name,
      category,
      channel: detectChannel(title, html),
      watchUrl: extractWatchUrl(html),
      youtubeUrl: extractYoutube(html),
      thumbnail,
      period: extractField(html, ['방송 기간']),
      time: extractField(html, ['방송 시간']),
      episodes: extractField(html, ['회차', '회차 정보']),
      cast: extractField(html, ['출연', '주요 출연']),
      excerpt,
      date: tag(block, 'wp:post_date') || tag(block, 'pubDate'),
      updated: tag(block, 'wp:post_modified') || tag(block, 'wp:post_date'),
      tags: [...block.matchAll(/<category domain="post_tag"[^>]*nicename="([^"]*)"/g)].map((match) =>
        decodeSlug(match[1]),
      ),
      entrySlug,
      legacyPath: `/${entrySlug}/`,
      showKey: showKey(name),
      legacyId: id,
      featured: category !== 'archive',
      hiddenFromList: category === 'archive' && /다운로드|유니버셜|엑셀|알약/.test(title),
      body: html,
    });
    console.log(`converted ${id} ${title}`);
  }

  const groups = Map.groupBy(prepared, (item) => item.showKey);
  for (const group of groups.values()) {
    const sorted = [...group].sort((a, b) => Date.parse(b.date) - Date.parse(a.date));
    const [canonical, ...dupes] = sorted;
    canonical.hiddenFromList = Boolean(canonical.hiddenFromList);
    for (const dupe of dupes) {
      dupe.hiddenFromList = true;
      dupe.canonical = canonical.legacyPath;
      dupe.featured = false;
    }
  }

  for (const item of prepared) {
    const { body, ...frontmatter } = item;
    const file = path.join(ROOT, 'src/content/shows', `${item.legacyId}.md`);
    await writeFile(file, `${toYaml(frontmatter)}${body}\n`);
  }

  console.log(`Wrote ${prepared.length} markdown files.`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
