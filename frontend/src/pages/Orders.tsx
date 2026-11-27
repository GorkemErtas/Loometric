import { useMemo, useState } from "react";
import { Badge, Empty, Icon, Modal, Notice, Panel, TableScroll } from "../components/ui";
import { compareExact } from "../domain/exact";
import type { Order } from "../domain/models";
import { useI18n } from "../i18n/I18n";
import { useWorkspace } from "../state/Workspace";

type SortKey = "id" | "styleId" | "quantity" | "priority" | "release" | "due";
const columns: { key: SortKey; label: string }[] = [
  { key: "id", label: "Order ID" },
  { key: "styleId", label: "Style" },
  { key: "quantity", label: "Quantity (pieces)" },
  { key: "priority", label: "Priority" },
  { key: "release", label: "Release date" },
  { key: "due", label: "Due date" },
];
export function Orders() {
  const {
    t,
    backendText,
    locale,
    label: textLabel,
    codeLabel,
    formatExact,
    dateLabel,
    stageName,
  } = useI18n();

  const { dataset } = useWorkspace();
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; direction: "ascending" | "descending" }>({
    key: "id",
    direction: "ascending",
  });
  const [selected, setSelected] = useState<Order | null>(null);
  const planning = dataset?.planning;
  const rows = useMemo(
    () =>
      (planning?.orders ?? [])
        .filter((order) =>
          [order.id, order.styleId, ...order.stages]
            .join(" ")
            .toLocaleLowerCase(locale)
            .includes(search.trim().toLocaleLowerCase(locale)),
        )
        .sort((a, b) => {
          const comparison =
            sort.key === "quantity" || sort.key === "priority"
              ? compareExact(a[sort.key], b[sort.key])
              : a[sort.key].localeCompare(b[sort.key], locale);
          return sort.direction === "ascending" ? comparison : -comparison;
        }),
    [planning, search, sort, locale],
  );
  if (!planning)
    return <Empty title={t("No planning dataset")}>{t("Choose a synthetic dataset first.")}</Empty>;
  const changeSort = (key: SortKey) =>
    setSort((current) => ({
      key,
      direction:
        current.key === key && current.direction === "ascending" ? "descending" : "ascending",
    }));
  return (
    <div className="page-stack">
      <Panel
        title={t("Order register")}
        description={t("{p0} unique orders · source inputs, not scheduled output", {
          p0: planning.orders.length,
        })}
        action={<Badge>{t("Planning inputs")}</Badge>}
      >
        <div className="table-toolbar">
          <label className="search-field">
            <Icon name="search" size={18} />
            <input
              type="search"
              aria-label={t("Search orders")}
              placeholder={t("Search order, style or stage…")}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <span className="muted" aria-live="polite">
            {t("{p0} of {p1} orders", { p0: rows.length, p1: planning.orders.length })}
          </span>
        </div>
        <TableScroll label={t("Order register scrollable table")}>
          <table>
            <caption className="sr-only">
              {t("Synthetic order register. Activate a column header to change sort order.")}
            </caption>
            <thead>
              <tr>
                {columns.map((column) => (
                  <th
                    key={column.key}
                    scope="col"
                    aria-sort={sort.key === column.key ? sort.direction : undefined}
                  >
                    <button
                      type="button"
                      className="sort-button"
                      onClick={() => changeSort(column.key)}
                    >
                      {textLabel(column.label)}
                      <span aria-hidden="true">
                        {sort.key === column.key
                          ? sort.direction === "ascending"
                            ? "↑"
                            : "↓"
                          : "↕"}
                      </span>
                    </button>
                  </th>
                ))}
                <th scope="col">{t("Required stages")}</th>
                <th scope="col">
                  <span className="sr-only">{t("Details")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((order) => (
                <tr key={order.id}>
                  <th scope="row" className="cell-primary">
                    {order.id}
                  </th>
                  <td>{order.styleId}</td>
                  <td className="numeric">{formatExact(order.quantity)}</td>
                  <td>
                    <Badge tone={order.priority !== "1" ? "amber" : "neutral"}>
                      P{order.priority}
                    </Badge>
                  </td>
                  <td className="nowrap">{dateLabel(order.release)}</td>
                  <td className="nowrap">{dateLabel(order.due)}</td>
                  <td>
                    <div className="badge-row">
                      {order.stages.map((stage) => (
                        <Badge key={stage}>{stageName(stage)}</Badge>
                      ))}
                    </div>
                  </td>
                  <td>
                    <button
                      className="text-link"
                      type="button"
                      aria-label={t("Inspect {p0}", { p0: order.id })}
                      onClick={() => setSelected(order)}
                    >
                      {t("Inspect")} <Icon name="arrow" size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>
        {rows.length === 0 && (
          <Empty title={t("No matching orders")}>
            {t("Try another order ID, style or required stage.")}
          </Empty>
        )}
        <p className="table-footnote">
          {t(
            "Priority is the declared input value; 1 is highest priority in the existing scheduling policy.",
          )}
        </p>
      </Panel>
      <Notice>
        {t(
          "Routing below reflects declared line–style capabilities. Release dates, material readiness and shared capacity still require scheduling verification.",
        )}
      </Notice>
      {selected && (
        <Modal title={t("Order {p0}", { p0: selected.id })} onClose={() => setSelected(null)}>
          <div className="order-detail">
            <Badge tone="amber">{t("SYNTHETIC INPUT")}</Badge>
            <dl className="detail-grid">
              <div>
                <dt>{t("Style")}</dt>
                <dd>{selected.styleId}</dd>
              </div>
              <div>
                <dt>{t("Quantity")}</dt>
                <dd>{t("{p0} pieces", { p0: formatExact(selected.quantity) })}</dd>
              </div>
              <div>
                <dt>{t("Priority")}</dt>
                <dd>P{selected.priority}</dd>
              </div>
              <div>
                <dt>{t("Release / due")}</dt>
                <dd>
                  {dateLabel(selected.release)} / {dateLabel(selected.due)}
                </dd>
              </div>
            </dl>
            <h3>{t("Declared routing compatibility")}</h3>
            {selected.stages.map((stage) => {
              const routes = planning.capabilities.filter(
                (route) => route.styleId === selected.styleId && route.stage === stage,
              );
              const standard = planning.styles
                .find((style) => style.id === selected.styleId)
                ?.standards.find((item) => item.stage === stage);
              return (
                <div key={stage} className="route-detail">
                  <strong>{stageName(stage)}</strong>
                  <p>
                    {standard
                      ? t("{p0} standard worker-minutes / piece · {p1}", {
                          p0: formatExact(standard.minutes),
                          p1: codeLabel(standard.unit),
                        })
                      : t("No standard declared")}
                  </p>
                  {routes.length ? (
                    routes.map((route) => (
                      <p key={route.id}>
                        <code>{route.lineId}</code> · {route.id} ·{" "}
                        {dataset?.validatedFingerprint ? route.basis : backendText(route.basis)}
                      </p>
                    ))
                  ) : (
                    <p>{t("No compatible line declared.")}</p>
                  )}
                </div>
              );
            })}
            <p className="field-help">
              {t(
                "Capability does not mean this order has been allocated or can meet its due date.",
              )}
            </p>
          </div>
        </Modal>
      )}
    </div>
  );
}
