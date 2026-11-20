import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Page } from "../components/app-ui";
import { api } from "../lib/api";

type BuildInfo = { version: string; revision: string; built_at: string };

const frontendBuild = __APP_BUILD_INFO__;

function BuildBlock({ title, build }: { title: string; build?: BuildInfo }) {
  return (
    <section className="card diagnostics-block">
      <h2>{title}</h2>
      {build ? (
        <dl>
          <div><dt>Version</dt><dd>{build.version}</dd></div>
          <div><dt>Revision</dt><dd>{build.revision}</dd></div>
          <div><dt>Built</dt><dd>{build.built_at}</dd></div>
        </dl>
      ) : <p className="error" role="alert">Build information unavailable.</p>}
    </section>
  );
}

export function DiagnosticsPage() {
  const [controlled, setControlled] = useState(() => Boolean(navigator.serviceWorker?.controller));
  const backend = useQuery({ queryKey: ["backend-build"], queryFn: () => api<BuildInfo>("/api/v1/system/build"), retry: false });
  useEffect(() => {
    const onControllerChange = () => setControlled(true);
    navigator.serviceWorker?.addEventListener("controllerchange", onControllerChange);
    return () => navigator.serviceWorker?.removeEventListener("controllerchange", onControllerChange);
  }, []);
  const mismatch = backend.data && backend.data.revision !== frontendBuild.revision;

  return (
    <Page title="Diagnostics">
      <p className="muted diagnostics-intro">Support information for this installed build.</p>
      {mismatch && <p className="warning-panel" role="alert">Frontend and API builds do not match.</p>}
      <div className="diagnostics-grid">
        <BuildBlock title="Frontend" build={frontendBuild} />
        <BuildBlock title="API" build={backend.data} />
      </div>
      <section className="card diagnostics-block">
        <h2>Service worker</h2>
        <p className="muted">{controlled ? "Active and controlling this page." : "Not currently controlling this page."}</p>
      </section>
    </Page>
  );
}
