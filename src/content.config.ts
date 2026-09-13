import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const shows = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/shows' }),
  schema: z.object({
    title: z.string(),
    name: z.string(),
    category: z.enum(['drama', 'entertainment', 'sport', 'movie', 'channel', 'archive']),
    channel: z.string().optional(),
    watchUrl: z.string().optional(),
    youtubeUrl: z.string().optional(),
    thumbnail: z.string().optional(),
    period: z.string().optional(),
    time: z.string().optional(),
    episodes: z.string().optional(),
    cast: z.string().optional(),
    excerpt: z.string().optional(),
    featured: z.boolean().default(false),
    date: z.coerce.date(),
    updated: z.coerce.date().optional(),
    tags: z.array(z.string()).default([]),
    entrySlug: z.string(),
    legacyPath: z.string(),
    canonical: z.string().optional(),
    hiddenFromList: z.boolean().default(false),
    showKey: z.string().optional(),
    legacyId: z.number().optional(),
  }),
});

export const collections = { shows };
