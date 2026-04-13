// @ts-nocheck
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Use full original pathname (includes basePath, not stripped)
  const path = new URL(request.url).pathname;

  if (path.startsWith('/codebot/codebot/') || path === '/codebot/codebot') {
    const newPath = path.replace(/^\/codebot\/codebot/, '/codebot');
    const url = request.nextUrl.clone();
    url.pathname = newPath;
    return NextResponse.redirect(url, 307);
  }

  return NextResponse.next();
}

export const config = {
  matcher: '/codebot/:path*',
};
EOF