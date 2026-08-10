/** Explicit error types keep expected user failures separate from programming faults. */

export class UserFacingError extends Error {
  public constructor(
    public readonly code: string,
    message: string,
    options?: ErrorOptions,
  ) {
    super(message, options);
    this.name = "UserFacingError";
  }
}
