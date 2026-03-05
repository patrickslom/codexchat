import Link from "next/link";
import { redirect } from "next/navigation";
import { hasSessionCookie } from "@/lib/auth-session";

export default async function ProtectedLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const authenticated = await hasSessionCookie();

  if (!authenticated) {
    redirect("/login");
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border bg-background/95">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-4">
            <Link href="/chat" className="text-sm font-semibold tracking-wide uppercase">
              CodexChat
            </Link>
            <nav className="flex items-center gap-3 text-sm text-zinc-600 dark:text-zinc-300">
              <Link href="/chat" className="hover:underline">
                Chat
              </Link>
              <Link href="/settings" className="hover:underline">
                Settings
              </Link>
              <Link href="/settings/admin" className="hover:underline">
                Admin
              </Link>
            </nav>
          </div>

          <form method="post" action="/logout">
            <button
              type="submit"
              className="rounded-md border border-border px-3 py-1.5 text-sm font-medium hover:bg-muted"
            >
              Log out
            </button>
          </form>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6">{children}</main>
    </div>
  );
}
