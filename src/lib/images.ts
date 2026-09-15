const UPLOAD_PREFIX = '/uploads/';
/** Versioned card crop dir — bump when optimize-thumbs geometry/quality changes */
const THUMB_PREFIX = '/thumbs/640x400/';

export function cardImage(src?: string) {
  if (!src) return undefined;
  if (!src.startsWith(UPLOAD_PREFIX)) return src;
  const relative = src.slice(UPLOAD_PREFIX.length).replace(/\.[^.]+$/, '');
  return `${THUMB_PREFIX}${relative}.webp`;
}
