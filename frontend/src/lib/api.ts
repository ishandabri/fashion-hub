export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const csrf = typeof document !== "undefined" ? document.cookie.split(";").map(part => part.trim()).find(part => part.startsWith("csrf_token="))?.split("=")[1] : undefined;
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const headers = { ...(isFormData ? {} : { "Content-Type": "application/json" }), ...(csrf ? { "X-CSRF-Token": decodeURIComponent(csrf) } : {}), ...init?.headers };
  let response: Response;
  try {
    response = await fetch(path, { credentials: "include", headers, ...init });
    if (typeof window !== "undefined") window.dispatchEvent(new Event("app:online"));
  } catch (error) {
    if (typeof window !== "undefined") window.dispatchEvent(new Event("app:offline"));
    throw error;
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Something went wrong");
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

