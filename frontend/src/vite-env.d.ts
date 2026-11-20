/// <reference types="vite/client" />

declare const __APP_BUILD_INFO__: {
  version: string;
  revision: string;
  built_at: string;
};

declare module "virtual:pwa-register" {
  export function registerSW(options?: {
    immediate?: boolean;
    onRegisteredSW?: (swUrl: string, registration: ServiceWorkerRegistration | undefined) => void;
    onNeedRefresh?: () => void;
    onRegisterError?: (error: unknown) => void;
  }): (reloadPage?: boolean) => Promise<void>;
}
