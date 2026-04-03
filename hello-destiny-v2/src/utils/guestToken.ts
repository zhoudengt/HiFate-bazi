const KEY = 'v2_guest_token';

export function ensureGuestToken(): string {
  let t = localStorage.getItem(KEY);
  if (!t || t.length < 8) {
    t = crypto.randomUUID();
    localStorage.setItem(KEY, t);
  }
  return t;
}

export function getGuestToken(): string | null {
  return localStorage.getItem(KEY);
}
