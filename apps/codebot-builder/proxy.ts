// @ts-nocheck
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function proxy(request: NextRequest) {
  const path = new URL(request.url).pathname;

  // Redirect root to /codebot/
  if (path === '/' || path === '') {
    return NextResponse.redirect(new URL('/codebot/', request.url), 307);
  }

  // Fix double /codebot/codebot/ paths
  if (path.startsWith('/codebot/codebot/') || path === '/codebot/codebot') {
    const newPath = path.replace(/^\/codebot\/codebot/, '/codebot');
    const newUrl = new URL(newPath, request.url);
    return NextResponse.redirect(newUrl, 307);
  }

  return NextResponse.next();
}

export const config = {
  matcher: '/:path*',
};
