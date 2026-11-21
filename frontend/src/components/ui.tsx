import { type ReactNode, useEffect, useRef } from "react";
import type { ApiError } from "../api/client";

export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    overview: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
      </>
    ),
    orders: (
      <>
        <path d="M8 3h8l3 4v14H5V7z" />
        <path d="M8 3v5h8V3M9 12h6m-6 4h6" />
      </>
    ),
    resources: (
      <>
        <path d="M3 21V10l6 3V8l6 3V3h6v18zM7 17h1m4 0h1m4 0h1" />
      </>
    ),
    capacity: (
      <>
        <path d="M4 3v18h17M8 16v-5m5 5V6m5 10v-7" />
      </>
    ),
    system: (
      <>
        <rect x="3" y="4" width="18" height="7" rx="2" />
        <rect x="3" y="14" width="18" height="7" rx="2" />
        <path d="M7 7.5h.01M7 17.5h.01M11 7.5h6m-6 10h6" />
      </>
    ),
    arrow: <path d="M5 12h14m-6-6 6 6-6 6" />,
    search: (
      <>
        <circle cx="10.5" cy="10.5" r="6.5" />
        <path d="m16 16 5 5" />
      </>
    ),
    close: <path d="m6 6 12 12M6 18 18 6" />,
    menu: <path d="M4 6h16M4 12h16M4 18h16" />,
    info: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 11v6m0-10v.01" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    link: (
      <>
        <path d="m10 8 3-3a5 5 0 0 1 7 7l-3 3M14 16l-3 3a5 5 0 0 1-7-7l3-3m1 5 8-8" />
      </>
    ),
  };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name] ?? paths.info}
    </svg>
  );
}
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "teal" | "amber" | "red";
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
export function Panel({
  title,
  description,
  action,
  children,
  className = "",
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`} aria-label={title}>
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {description && <p>{description}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Stat({
  label,
  value,
  unit,
  detail,
  icon,
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  detail: string;
  icon?: string;
}) {
  return (
    <div className="stat">
      <div className="stat-top">
        <span>{label}</span>
        {icon && <Icon name={icon} size={18} />}
      </div>
      <div className="stat-value">
        {value}
        {unit && <span className="stat-unit">{unit}</span>}
      </div>
      <p>{detail}</p>
    </div>
  );
}
export function Empty({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="empty">
      <Icon name="info" size={25} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}

export function TableScroll({ label, children }: { label: string; children: ReactNode }) {
  return (
    // biome-ignore lint/a11y/noNoninteractiveTabindex: A named scroll region must be reachable for horizontal keyboard scrolling.
    <section className="table-scroll" tabIndex={0} aria-label={label}>
      {children}
    </section>
  );
}
export function ErrorNotice({ error }: { error: ApiError }) {
  return (
    <div className="notice notice-error" role="alert">
      <Icon name="info" />
      <div>
        <strong>Request unavailable</strong>
        <p>{error.message}</p>
        {error.requestId && <small>Request ID: {error.requestId}</small>}
      </div>
    </div>
  );
}
export function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="notice">
      <Icon name="info" />
      <div>{children}</div>
    </div>
  );
}
export function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement;
    const element = dialog.current;
    element?.showModal();
    return () => {
      element?.close();
      if (previous instanceof HTMLElement) previous.focus({ preventScroll: true });
    };
  }, []);
  return (
    <dialog ref={dialog} className="modal" aria-label={title} onCancel={onClose}>
      <div className="modal-heading">
        <h2>{title}</h2>
        <button className="icon-button" type="button" aria-label="Close dialog" onClick={onClose}>
          <Icon name="close" />
        </button>
      </div>
      {children}
    </dialog>
  );
}
