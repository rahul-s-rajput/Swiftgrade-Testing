// Image preparation before upload: optional compression + content hashing.
// Uploads are stored at a path derived from the SHA-256 of their bytes, so the same
// image (e.g. re-uploaded through "Use as Template") never takes up space twice.

const COMPRESS_SETTING_KEY = 'swiftgrade.compressUploads';

// Claude downscales anything over ~1568px on the long edge anyway, and handwriting
// stays readable at this size.
const MAX_LONG_EDGE = 2000;
const JPEG_QUALITY = 0.85;
// Images already within MAX_LONG_EDGE and under this size are uploaded untouched, so a
// previously compressed image hashes identically when uploaded again.
const SKIP_BELOW_BYTES = 600 * 1024;
const COMPRESSIBLE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp'];

export function isCompressionEnabled(): boolean {
  try {
    return localStorage.getItem(COMPRESS_SETTING_KEY) !== 'false';
  } catch {
    return true;
  }
}

export function setCompressionEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(COMPRESS_SETTING_KEY, String(enabled));
  } catch {
    // Setting just won't persist; compression stays at its default.
  }
}

export async function sha256Hex(file: Blob): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
  return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
}

/** Downscale and re-encode large images as JPEG. Returns the original file when
 * compression is off, not applicable, or wouldn't help. */
export async function prepareImageForUpload(file: File): Promise<File> {
  if (!isCompressionEnabled() || !COMPRESSIBLE_TYPES.includes(file.type)) return file;

  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    return file;
  }

  const scale = Math.min(1, MAX_LONG_EDGE / Math.max(bitmap.width, bitmap.height));
  if (scale === 1 && file.size <= SKIP_BELOW_BYTES) {
    bitmap.close();
    return file;
  }

  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    bitmap.close();
    return file;
  }
  // JPEG has no alpha; paint transparent PNG areas white like paper.
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();

  const blob = await new Promise<Blob | null>(res => canvas.toBlob(res, 'image/jpeg', JPEG_QUALITY));
  if (!blob || blob.size >= file.size) return file;

  const base = file.name.replace(/\.[^.]+$/, '') || 'image';
  return new File([blob], `${base}.jpg`, { type: 'image/jpeg' });
}
