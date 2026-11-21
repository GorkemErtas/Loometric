import capacityInput from "../../../examples/planning/capacity-demo.json?raw";
import capacityScenario from "../../../examples/scenarios/capacity-baseline.json?raw";
import routingScenario from "../../../examples/scenarios/routing-baseline.json?raw";
import competitionInput from "../../../examples/scheduling/competition.json?raw";
import parallel from "../../../examples/scheduling/parallel-routing.json?raw";
import capacitySnapshot from "../../fixtures/capacity-demo.report.json?raw";
import competitionCapacity from "../../fixtures/competition.capacity.json?raw";
import proposal from "../../fixtures/competition.schedule.json?raw";
import verified from "../../fixtures/competition.verification.json?raw";
import sources from "../../fixtures/sources.json";
import { capacityReport, planningInput, scheduleReport } from "../domain/adapters";
import { object, parseExact } from "../domain/json";
import type { Dataset } from "../domain/models";

const capacityRaw = object(parseExact(capacityInput));
const competitionRaw = object(parseExact(competitionInput));

export const datasets: readonly Dataset[] = [
  {
    key: "capacity",
    name: "Capacity foundation",
    description: "M02 · varied crews, downtime and independent checks",
    sourceFile: sources.capacity.file,
    sourceHash: sources.capacity.sha256,
    planning: planningInput(capacityRaw),
    instance: null,
    previewCapacity: capacityReport(parseExact(capacitySnapshot)),
    previewSchedule: null,
    savedProposal: null,
  },
  {
    key: "competition",
    name: "Competing orders",
    description: "M03A · one shared line and a saved partial schedule",
    sourceFile: sources.competition.file,
    sourceHash: sources.competition.sha256,
    planning: planningInput(competitionRaw.planning),
    instance: competitionRaw,
    previewCapacity: capacityReport(parseExact(competitionCapacity)),
    previewSchedule: scheduleReport(parseExact(verified)),
    savedProposal: object(parseExact(proposal)),
  },
  ...(
    [
      [
        "capacityScenario",
        "Capacity what-if",
        "M04 · one qualified crew, downtime and a declared reserve shift",
        capacityScenario,
      ],
      [
        "routingScenario",
        "Routing trade-off",
        "M04 · additional capacity can worsen greedy choices",
        routingScenario,
      ],
      [
        "parallel",
        "Parallel production",
        "M03A · multiple stages, routing and late completions",
        parallel,
      ],
    ] as const
  ).map(([key, name, description, source]) => {
    const raw = object(parseExact(source));
    return {
      key,
      name,
      description,
      sourceFile: sources[key].file,
      sourceHash: sources[key].sha256,
      planning: planningInput(raw.planning),
      instance: raw,
      previewCapacity: null,
      previewSchedule: null,
      savedProposal: null,
    };
  }),
];
