import * as React from "react";
import { useEffect, useRef } from "react";
import { AlertCircle, CheckCircle2, LoaderCircle, X } from "lucide-react";

export function BusyButton({
  busy,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { busy?: boolean }) {
  return (
    <button
      {...props}
      disabled={busy || props.disabled}
      aria-busy={busy || undefined}
    >
      {busy && <LoaderCircle className="spin" size={16} aria-hidden="true" />}
      {children}
    </button>
  );
}

function stripModalCancelButtons(node: React.ReactNode): React.ReactNode {
  return React.Children.map(node, (child) => {
    if (!React.isValidElement(child)) return child;
    if (
      child.type === "button" &&
      typeof child.props.children === "string" &&
      child.props.children.trim() === "Cancel"
    )
      return null;
    return child.props.children
      ? React.cloneElement(
          child,
          undefined,
          stripModalCancelButtons(child.props.children),
        )
      : child;
  });
}

export function Modal({
  title,
  description,
  children,
  onClose,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    closeRef.current?.focus();
    const key = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [onClose]);
  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <div className="modal-heading">
          <div>
            <h2 id="modal-title">{title}</h2>
            {description && <p className="muted">{description}</p>}
          </div>
          <button
            ref={closeRef}
            className="icon-button"
            aria-label="Close dialog"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>
        {stripModalCancelButtons(children)}
      </section>
    </div>
  );
}

export function ConfirmDialog({
  title,
  description,
  confirmLabel,
  destructive,
  busy,
  onConfirm,
  onClose,
}: {
  title: string;
  description: string;
  confirmLabel: string;
  destructive?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Modal title={title} description={description} onClose={onClose}>
      <div className="dialog-actions">
        <BusyButton
          className={destructive ? "danger" : "primary"}
          busy={busy}
          onClick={onConfirm}
        >
          {confirmLabel}
        </BusyButton>
      </div>
    </Modal>
  );
}

export function SkeletonBlock() {
  return (
    <div className="skeleton-stack" aria-label="Loading">
      <span className="skeleton" />
      <span className="skeleton" />
      <span className="skeleton" />
    </div>
  );
}

export function EmptyState({ text }: { text: string }) {
  return (
    <div className="empty">
      <CheckCircle2 size={20} aria-hidden="true" />
      <p className="muted">{text}</p>
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="error-panel" role="alert">
      <AlertCircle size={18} />
      <span>{message}</span>
      <button className="secondary" onClick={onRetry}>
        Retry
      </button>
    </div>
  );
}

export function Page({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <>
      <div className="page-heading">
        <h1>{title}</h1>
      </div>
      {children}
    </>
  );
}
