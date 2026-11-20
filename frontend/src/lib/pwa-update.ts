import { registerSW } from "virtual:pwa-register";
import { api } from "./api";

type PwaFailureType = "PWA_REGISTRATION_FAILED" | "PWA_UPDATE_CHECK_FAILED" | "PWA_ACTIVATION_FAILED";
const reportedFailures = new Set<PwaFailureType>();

function reportFailure(eventType: PwaFailureType, error: unknown) {
  if (reportedFailures.has(eventType)) return;
  reportedFailures.add(eventType);
  const message = (error instanceof Error ? error.message : String(error)).replace(/[\r\n]+/g, " ").slice(0, 240) || "Unknown PWA update error";
  void api<void>("/api/v1/system/client-events", {
    method: "POST",
    body: JSON.stringify({ event_type: eventType, frontend_version: __APP_BUILD_INFO__.version, frontend_revision: __APP_BUILD_INFO__.revision, message }),
    keepalive: true,
  }).catch(() => undefined);
}

export function registerAppUpdate() {
  if (!import.meta.env.PROD || !("serviceWorker" in navigator)) return;

  let registration: ServiceWorkerRegistration | undefined;
  let checkedWhileVisible = false;
  const checkForUpdate = () => {
    if (!registration || checkedWhileVisible) return;
    checkedWhileVisible = true;
    void registration.update().catch((error) => reportFailure("PWA_UPDATE_CHECK_FAILED", error));
  };

  const updateServiceWorker = registerSW({
    immediate: true,
    onRegisteredSW: (_swUrl, currentRegistration) => {
      registration = currentRegistration;
      checkForUpdate();
    },
    onRegisterError: (error) => reportFailure("PWA_REGISTRATION_FAILED", error),
    onNeedRefresh: () => {
      void updateServiceWorker(true).catch((error) => reportFailure("PWA_ACTIVATION_FAILED", error));
    },
  });

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") checkedWhileVisible = false;
    else checkForUpdate();
  });
  window.addEventListener("pageshow", () => {
    checkedWhileVisible = false;
    checkForUpdate();
  });
}
