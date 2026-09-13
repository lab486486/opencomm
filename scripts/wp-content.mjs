import { readFile } from 'node:fs/promises';

export function tag(block, name) {
  const match = block.match(
    new RegExp(`<${name}(?:\\s[^>]*)?>(?:<!\\[CDATA\\[(.*?)\\]\\]>|(.*?))</${name}>`, 's'),
  );
  if (!match) return '';
  return (match[1] ?? match[2] ?? '').trim();
}

export function parseItems(xml) {
  return [...xml.matchAll(/<item>(.*?)<\/item>/gs)].map((match) => match[1]);
}

export function toLocalSrc(url = '') {
  const match = String(url).match(/\/(?:wp-content\/)?uploads\/(.+)$/i);
  if (!match) return '';
  try {
    return `/uploads/${decodeURIComponent(match[1])}`;
  } catch {
    return `/uploads/${match[1]}`;
  }
}

export function parseAttachments(xml) {
  const attachments = {};
  for (const block of parseItems(xml)) {
    if (tag(block, 'wp:post_type') !== 'attachment') continue;
    const id = tag(block, 'wp:post_id');
    const src = toLocalSrc(tag(block, 'wp:attachment_url') || tag(block, 'guid'));
    if (!id || !src) continue;
    attachments[id] = {
      src,
      alt: tag(block, 'title') || tag(block, 'excerpt:encoded') || '',
    };
  }
  return attachments;
}

export function expandGalleries(html, attachments) {
  return html.replace(/\[gallery\s+([^\]]+)\]/gi, (_, rawAttrs) => {
    const attrs = String(rawAttrs).replace(/[“”]/g, '"').replace(/[‘’]/g, "'");
    const ids = (attrs.match(/ids\s*=\s*["']([^"']+)["']/i)?.[1] ?? '')
      .split(',')
      .map((id) => id.trim())
      .filter(Boolean);
    const columns = Number(attrs.match(/columns\s*=\s*["']?(\d+)/i)?.[1] || Math.min(ids.length, 3) || 2);
    const images = ids
      .map((id) => attachments[id])
      .filter(Boolean)
      .map(
        (item) =>
          `<img src="${item.src}" alt="${escapeAttr(item.alt)}" class="wp-gallery-image" loading="lazy">`,
      )
      .join('');
    if (!images) return '';
    return `<div class="wp-gallery cols-${columns}">${images}</div>`;
  });
}

function escapeAttr(value = '') {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('"', '&quot;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

export async function loadAttachmentsFromXml(xmlPath) {
  const xml = await readFile(xmlPath, 'utf8');
  return parseAttachments(xml);
}
