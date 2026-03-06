"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getApiBaseUrl } from "@/lib/network-config";

type WarningPayload = {
  id: string;
  title: string;
  content: string;
  severity: "info" | "warning" | "critical";
};

type SharedWorkspaceWarning = {
  enabled: boolean;
  content: string;
};

type SettingsResponse = {
  execution_mode_default: "regular" | "yolo";
  destructive_operations_warning: WarningPayload;
  yolo_mode_warning: WarningPayload;
  shared_workspace_warning: SharedWorkspaceWarning;
};

type SettingsApiPayload = {
  settings?: SettingsResponse;
};

const BANNER_BASE = "rounded-xl border px-4 py-3 text-sm";

function toneClass(severity: WarningPayload["severity"]): string {
  if (severity === "critical") {
    return "border-red-300 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100";
  }
  if (severity === "warning") {
    return "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100";
  }
  return "border-zinc-300 bg-muted text-foreground dark:border-zinc-700";
}

export default function SafetyGuardrailBanner() {
  const router = useRouter();
  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);

  useEffect(() => {
    let mounted = true;

    const loadSettings = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/settings`, {
          method: "GET",
          credentials: "include",
          cache: "no-store",
        });

        if (response.status === 401 || response.status === 403) {
          router.replace("/login");
          return;
        }

        if (!response.ok) {
          return;
        }

        const payload = (await response.json()) as SettingsApiPayload;
        if (!payload.settings || !mounted) {
          return;
        }

        setSettings(payload.settings);
      } catch {
        // Keep page usable when settings fetch fails.
      }
    };

    void loadSettings();

    return () => {
      mounted = false;
    };
  }, [apiBaseUrl, router]);

  if (!settings) {
    return null;
  }

  const cards: Array<{ key: string; title: string; content: string; severity: WarningPayload["severity"] }> = [];

  cards.push({
    key: settings.destructive_operations_warning.id,
    title: settings.destructive_operations_warning.title,
    content: settings.destructive_operations_warning.content,
    severity: settings.destructive_operations_warning.severity,
  });

  if (settings.execution_mode_default === "yolo") {
    cards.push({
      key: settings.yolo_mode_warning.id,
      title: settings.yolo_mode_warning.title,
      content: settings.yolo_mode_warning.content,
      severity: settings.yolo_mode_warning.severity,
    });
  }

  if (settings.shared_workspace_warning.enabled) {
    cards.push({
      key: "shared-workspace-notice",
      title: "Shared Workspace Notice",
      content: settings.shared_workspace_warning.content,
      severity: "critical",
    });
  }

  if (cards.length === 0) {
    return null;
  }

  return (
    <section className="mx-auto mt-4 w-full max-w-7xl px-4 sm:px-6">
      <div className="space-y-2">
        {cards.map((card) => (
          <article key={card.key} className={`${BANNER_BASE} ${toneClass(card.severity)}`}>
            <p className="font-semibold">{card.title}</p>
            <p className="mt-1 text-xs leading-relaxed opacity-90">{card.content}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
