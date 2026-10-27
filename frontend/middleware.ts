import { NextRequest, NextResponse } from "next/server";

const ACCESS_COOKIE = "ims_access_token";

interface JwtPayload {
  sub?: string;
  role?: "CANDIDATE" | "HR_REVIEWER" | "ADMIN";
  exp?: number;
}

function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const jsonStr = atob(padded);
    return JSON.parse(jsonStr) as JwtPayload;
  } catch {
    return null;
  }
}

function getRoleHomePath(role?: string): string {
  if (role === "ADMIN") return "/admin/dashboard";
  if (role === "HR_REVIEWER") return "/hr/dashboard";
  return "/candidate/dashboard";
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get(ACCESS_COOKIE)?.value;
  const payload = token ? decodeJwtPayload(token) : null;
  const isExpired = payload?.exp ? payload.exp * 1000 < Date.now() : true;
  const isAuthenticated = Boolean(payload && !isExpired && payload.role);

  const isAuthPage = pathname === "/login" || pathname === "/register";
  const isProtectedRoute =
    pathname.startsWith("/candidate") ||
    pathname.startsWith("/hr") ||
    pathname.startsWith("/admin");

  if (isAuthPage && isAuthenticated) {
    return NextResponse.redirect(new URL(getRoleHomePath(payload?.role), request.url));
  }

  if (isProtectedRoute && !isAuthenticated) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (isAuthenticated && payload?.role) {
    const role = payload.role;
    if (pathname.startsWith("/candidate") && role !== "CANDIDATE") {
      return NextResponse.redirect(new URL(getRoleHomePath(role), request.url));
    }
    if (pathname.startsWith("/hr") && role !== "HR_REVIEWER" && role !== "ADMIN") {
      return NextResponse.redirect(new URL(getRoleHomePath(role), request.url));
    }
    if (pathname.startsWith("/admin") && role !== "ADMIN") {
      return NextResponse.redirect(new URL(getRoleHomePath(role), request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/login",
    "/register",
    "/candidate/:path*",
    "/hr/:path*",
    "/admin/:path*",
  ],
};