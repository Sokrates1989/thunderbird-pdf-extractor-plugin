/** Small explicit state machine for review-popup transitions. */

import { UserFacingError } from "../domain/errors";

export type PopupPhase = "loading" | "review" | "working" | "success" | "error";

const ALLOWED_TRANSITIONS: Readonly<Record<PopupPhase, ReadonlySet<PopupPhase>>> = {
  error: new Set(),
  loading: new Set(["review", "error"]),
  review: new Set(["working", "error"]),
  success: new Set(),
  working: new Set(["success", "error"]),
};

export function transitionPhase(current: PopupPhase, next: PopupPhase): PopupPhase {
  if (current === next) {
    return current;
  }
  if (!ALLOWED_TRANSITIONS[current].has(next)) {
    throw new UserFacingError("invalid_ui_transition", `Cannot transition from ${current} to ${next}.`);
  }
  return next;
}
