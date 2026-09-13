import { getCollection, type CollectionEntry } from 'astro:content';
import { getCategory } from './categories';

export type ShowEntry = CollectionEntry<'shows'>;

export async function getShows() {
  const entries = await getCollection('shows');
  return entries.sort((a, b) => b.data.date.getTime() - a.data.date.getTime());
}

export async function getListedShows() {
  const entries = await getShows();
  return entries.filter((entry) => !entry.data.hiddenFromList);
}

export async function getShowsByCategory(slug: string) {
  const entries = await getListedShows();
  return entries.filter((entry) => entry.data.category === slug);
}

export async function getFeaturedShows() {
  const entries = await getListedShows();
  const featured = entries.filter((entry) => entry.data.featured);
  if (featured.length >= 8) return featured.slice(0, 12);
  return entries.filter((entry) => entry.data.category !== 'archive').slice(0, 12);
}

export async function getRelatedShows(entry: ShowEntry, limit = 8) {
  const entries = await getListedShows();
  return entries
    .filter((item) => item.id !== entry.id && item.data.category === entry.data.category)
    .slice(0, limit);
}

export function entryPath(entry: ShowEntry) {
  return `/${entry.data.entrySlug}/`;
}

export function categoryLabel(entry: ShowEntry) {
  return getCategory(entry.data.category)?.name ?? entry.data.category;
}

export function showDate(entry: ShowEntry) {
  const value = entry.data.updated ?? entry.data.date;
  return value.toISOString().slice(0, 10).replaceAll('-', '.');
}

export function byName(entries: ShowEntry[]) {
  return [...entries].sort((a, b) => a.data.name.localeCompare(b.data.name, 'ko'));
}

export function pageDescription(entry: ShowEntry) {
  const text = String(entry.body ?? '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/!\[[^\]]*]\([^)]+\)/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  const sentences = text.match(/[^.!?。！？]+[.!?。！？]/g) ?? [];
  let out = '';
  for (const sentence of sentences) {
    const next = `${out}${sentence}`.trim();
    if (next.length > 160 && out) break;
    out = next;
    if (out.length >= 90) break;
  }
  return out || entry.data.title;
}
