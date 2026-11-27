import { type ReactNode, useEffect, useRef } from "react";
import type { ApiError } from "../api/client";
import { apiFailureMessages } from "../i18n/errors";
import { useI18n } from "../i18n/I18n";

export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    predictions: (
      <>
        <path d="M4 19V5m0 14h16M7 15l4-5 4 2 5-7" />
        <circle cx="11" cy="10" r="1.5" />
        <circle cx="15" cy="12" r="1.5" />
      </>
    ),
    data: (
      <>
        <rect x="4" y="3" width="16" height="18" rx="2" />
        <path d="M8 7h8M8 11h8M8 15h3m4 0h1M8 18h3" />
      </>
    ),
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
    scheduling: (
      <>
        <path d="M4 4v16h17M8 7h9v4H8zm3 7h9v4h-9z" />
      </>
    ),
    scenarios: (
      <>
        <path d="M5 4v16m7-16v16m7-16v16M2 8h6m1 8h6m1-9h6" />
        <circle cx="5" cy="8" r="2" />
        <circle cx="12" cy="16" r="2" />
        <circle cx="19" cy="7" r="2" />
      </>
    ),
    jobs: (
      <>
        <rect x="4" y="3" width="16" height="18" rx="2" />
        <path d="m8 8 2 2 4-4M8 15h8m-8 3h5" />
      </>
    ),
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
  const { label: textLabel } = useI18n();

  return (
    <div className="stat">
      <div className="stat-top">
        <span>{textLabel(String(label))}</span>
        {icon && <Icon name={icon} size={18} />}
      </div>
      <div className="stat-value">
        {value}
        {unit && <span className="stat-unit">{textLabel(unit)}</span>}
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
  const { label: textLabel } = useI18n();

  return (
    // biome-ignore lint/a11y/noNoninteractiveTabindex: A named scroll region must be reachable for horizontal keyboard scrolling.
    <section className="table-scroll" tabIndex={0} aria-label={textLabel(String(label))}>
      {children}
    </section>
  );
}
export function JsonBlock({ label, children }: { label: string; children: string }) {
  const { label: textLabel } = useI18n();

  return (
    // biome-ignore lint/a11y/noNoninteractiveTabindex: A named JSON scroll region needs keyboard access to its complete contents.
    <section className="json-scroll" tabIndex={0} aria-label={textLabel(String(label))}>
      <pre>{children}</pre>
    </section>
  );
}
export function ErrorNotice({ error }: { error: ApiError }) {
  const { t, codeLabel } = useI18n();

  return (
    <div className="notice notice-error" role="alert">
      <Icon name="info" />
      <div>
        <strong>{t("Request unavailable")}</strong>
        <p>{t(apiFailureMessages[error.kind])}</p>
        {error.code && (
          <p>
            <span>{codeLabel(error.code)}</span>
          </p>
        )}
        {error.retryAfterMs !== null && (
          <small>
            {t("Retry guidance: wait at least {p0} seconds.", {
              p0: Math.ceil(error.retryAfterMs / 1000),
            })}
          </small>
        )}
        {error.requestId && <small>{t("Request ID: {p0}", { p0: error.requestId })}</small>}
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
  const { t } = useI18n();

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
        <button
          className="icon-button"
          type="button"
          aria-label={t("Close dialog")}
          onClick={onClose}
        >
          <Icon name="close" />
        </button>
      </div>
      {children}
    </dialog>
  );
}
