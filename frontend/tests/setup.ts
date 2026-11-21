import "@testing-library/jest-dom/vitest";

// jsdom does not implement native dialog lifecycle; keyboard/focus trapping is
// checked separately in the real browser, without this test-only shim.
HTMLDialogElement.prototype.showModal = function () {
  this.setAttribute("open", "");
};
HTMLDialogElement.prototype.close = function () {
  this.removeAttribute("open");
};

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(cleanup);
