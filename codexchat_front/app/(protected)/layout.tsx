import { redirect } from "next/navigation";
import { hasSessionCookie } from "@/lib/auth-session";
import SafetyGuardrailBanner from "@/components/ui/safety-guardrail-banner";

export default async function ProtectedLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const authenticated = await hasSessionCookie();

  if (!authenticated) {
    redirect("/login");
  }

  return (
    <>
      <SafetyGuardrailBanner />
      {children}
    </>
  );
}
