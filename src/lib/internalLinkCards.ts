import { cardImage } from './images';
import { entryPath, type ShowEntry } from './shows';

export type InternalLinkCard = {
  href: string;
  title: string;
  thumbnail?: string;
};

/** Normalize /foo/ and /%xx/ forms to a decoded trailing-slash path for lookups. */
export function normalizeInternalPath(path: string): string {
  let value = path.trim();
  if (!value) return '';
  try {
    value = decodeURIComponent(value);
  } catch {
    // keep raw when malformed
  }
  if (!value.startsWith('/')) value = `/${value}`;
  if (!value.endsWith('/')) value = `${value}/`;
  return value;
}

export function isBareInternalPath(text: string): boolean {
  const value = text.trim();
  // Absolute internal paths only (no protocol, query, or hash).
  return /^\/(?:[A-Za-z0-9\-._~]|%[0-9A-Fa-f]{2}|[가-힣])+\/?$/.test(value);
}

export function collectBareInternalPaths(body: string): string[] {
  const found = new Set<string>();
  for (const line of body.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (isBareInternalPath(trimmed)) found.add(trimmed);
  }
  return [...found];
}

export function buildInternalLinkCatalog(entries: ShowEntry[]): Map<string, InternalLinkCard> {
  const catalog = new Map<string, InternalLinkCard>();
  for (const entry of entries) {
    const card: InternalLinkCard = {
      href: entryPath(entry),
      title: entry.data.title,
      thumbnail: cardImage(entry.data.thumbnail),
    };
    for (const raw of [entryPath(entry), entry.data.legacyPath, `/${entry.data.entrySlug}/`]) {
      if (!raw) continue;
      catalog.set(normalizeInternalPath(raw), card);
    }
  }
  return catalog;
}

export function cardsForBody(
  body: string,
  catalog: Map<string, InternalLinkCard>,
): Record<string, InternalLinkCard> {
  const out: Record<string, InternalLinkCard> = {};
  for (const raw of collectBareInternalPaths(body)) {
    const key = normalizeInternalPath(raw);
    const card =
      catalog.get(key) ??
      ({
        href: key,
        title: key.replace(/^\/|\/$/g, '').replace(/-/g, ' ') || key,
      } satisfies InternalLinkCard);
    out[key] = card;
    out[raw.trim()] = card;
  }
  return out;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

export function toInternalLinkCardHtml(card: InternalLinkCard): string {
  const thumb = card.thumbnail
    ? `<img src="${escapeHtml(card.thumbnail)}" alt="" width="64" height="64" loading="lazy" decoding="async" />`
    : `<span class="internal-link-card-ph" aria-hidden="true">${escapeHtml((card.title || '?').slice(0, 1))}</span>`;
  return `<a class="internal-link-card" href="${escapeHtml(card.href)}">${thumb}<span class="internal-link-card-title">${escapeHtml(card.title)}</span></a>`;
}

/**
 * Replace bare internal paths in article HTML/markdown body with preview cards.
 * Handles both lone lines (`/slug/`) and paragraph wrappers (`<p>/slug/</p>`).
 */
export function injectInternalLinkCards(
  body: string,
  cards: Record<string, InternalLinkCard>,
): string {
  if (!body || Object.keys(cards).length === 0) return body;

  const resolve = (raw: string) => cards[raw.trim()] || cards[normalizeInternalPath(raw)] || null;

  let html = body.replace(/<p>\s*(\/[^<>\s]+\/?)\s*<\/p>/gi, (full, path: string) => {
    if (!isBareInternalPath(path)) return full;
    const card = resolve(path);
    return card ? toInternalLinkCardHtml(card) : full;
  });

  html = html
    .split(/\r?\n/)
    .map((line) => {
      const trimmed = line.trim();
      if (!isBareInternalPath(trimmed)) return line;
      // Skip if this line was already turned into a card (contains class).
      if (line.includes('internal-link-card')) return line;
      const card = resolve(trimmed);
      return card ? toInternalLinkCardHtml(card) : line;
    })
    .join('\n');

  return html;
}
