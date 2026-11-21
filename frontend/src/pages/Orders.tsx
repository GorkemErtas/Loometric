import { useMemo, useState } from "react";
import { Badge, Empty, Icon, Modal, Notice, Panel, TableScroll } from "../components/ui";
import { compareExact, dateLabel, formatExact, stageName } from "../domain/exact";
import type { Order } from "../domain/models";
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
            .toLowerCase()
            .includes(search.trim().toLowerCase()),
        )
        .sort((a, b) => {
          const comparison =
            sort.key === "quantity" || sort.key === "priority"
              ? compareExact(a[sort.key], b[sort.key])
              : a[sort.key].localeCompare(b[sort.key]);
          return sort.direction === "ascending" ? comparison : -comparison;
        }),
    [planning, search, sort],
  );
  if (!planning)
    return <Empty title="No planning dataset">Choose a synthetic dataset first.</Empty>;
  const changeSort = (key: SortKey) =>
    setSort((current) => ({
      key,
      direction:
        current.key === key && current.direction === "ascending" ? "descending" : "ascending",
    }));
  return (
    <div className="page-stack">
      <Panel
        title="Order register"
        description={`${planning.orders.length} unique orders · source inputs, not scheduled output`}
        action={<Badge>Planning inputs</Badge>}
      >
        <div className="table-toolbar">
          <label className="search-field">
            <Icon name="search" size={18} />
            <input
              type="search"
              aria-label="Search orders"
              placeholder="Search order, style or stage…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <span className="muted" aria-live="polite">
            {rows.length} of {planning.orders.length} orders
          </span>
        </div>
        <TableScroll label="Order register scrollable table">
          <table>
            <caption className="sr-only">
              Synthetic order register. Activate a column header to change sort order.
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
                      {column.label}
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
                <th scope="col">Required stages</th>
                <th scope="col">
                  <span className="sr-only">Details</span>
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
                        <Badge key={stage}>{stage}</Badge>
                      ))}
                    </div>
                  </td>
                  <td>
                    <button
                      className="text-link"
                      type="button"
                      aria-label={`Inspect ${order.id}`}
                      onClick={() => setSelected(order)}
                    >
                      Inspect <Icon name="arrow" size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>
        {rows.length === 0 && (
          <Empty title="No matching orders">Try another order ID, style or required stage.</Empty>
        )}
        <p className="table-footnote">
          Priority is the declared input value; a larger value is more important in the existing
          scheduling policy.
        </p>
      </Panel>
      <Notice>
        Routing below reflects declared line–style capabilities. Release dates, material readiness
        and shared capacity still require scheduling verification.
      </Notice>
      {selected && (
        <Modal title={`Order ${selected.id}`} onClose={() => setSelected(null)}>
          <div className="order-detail">
            <Badge tone="amber">SYNTHETIC INPUT</Badge>
            <dl className="detail-grid">
              <div>
                <dt>Style</dt>
                <dd>{selected.styleId}</dd>
              </div>
              <div>
                <dt>Quantity</dt>
                <dd>{formatExact(selected.quantity)} pieces</dd>
              </div>
              <div>
                <dt>Priority</dt>
                <dd>P{selected.priority}</dd>
              </div>
              <div>
                <dt>Release / due</dt>
                <dd>
                  {dateLabel(selected.release)} / {dateLabel(selected.due)}
                </dd>
              </div>
            </dl>
            <h3>Declared routing compatibility</h3>
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
                      ? `${formatExact(standard.minutes)} standard worker-minutes / piece · ${standard.unit}`
                      : "No standard declared"}
                  </p>
                  {routes.length ? (
                    routes.map((route) => (
                      <p key={route.id}>
                        <code>{route.lineId}</code> · {route.id} · {route.basis}
                      </p>
                    ))
                  ) : (
                    <p>No compatible line declared.</p>
                  )}
                </div>
              );
            })}
            <p className="field-help">
              Capability does not mean this order has been allocated or can meet its due date.
            </p>
          </div>
        </Modal>
      )}
    </div>
  );
}
