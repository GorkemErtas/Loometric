import capacityInput from "../../../examples/planning/capacity-demo.json?raw";
import competitionInput from "../../../examples/scheduling/competition.json?raw";
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
];
