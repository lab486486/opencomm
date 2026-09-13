import type { APIRoute } from 'astro';
import { categoryLabel, entryPath, getListedShows, showDate } from '../lib/shows';

export const GET: APIRoute = async () => {
  const entries = await getListedShows();
  const payload = entries.map((entry) => ({
    name: entry.data.name,
    title: entry.data.title,
    excerpt: entry.data.excerpt ?? '',
    href: entryPath(entry),
    category: categoryLabel(entry),
    channel: entry.data.channel ?? '',
    date: showDate(entry),
    thumbnail: entry.data.thumbnail,
    tags: entry.data.tags,
  }));

  return new Response(JSON.stringify(payload), {
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
    },
  });
};
