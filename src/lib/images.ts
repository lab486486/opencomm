const UPLOAD_PREFIX = '/uploads/';

export function cardImage(src?: string) {
  if (!src) return undefined;
  if (!src.startsWith(UPLOAD_PREFIX)) return src;
  const relative = src.slice(UPLOAD_PREFIX.length).replace(/\.[^.]+$/, '');
  return `/thumbs/${relative}.webp`;
}
