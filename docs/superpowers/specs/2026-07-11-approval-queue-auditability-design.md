# Approval Queue Auditability Design

## Problem

The approval queue can contain pending requests from several runs, but each card currently shows only the tool name and policy message. Reviewers cannot distinguish runs or inspect the proposed arguments, model rationale, or expected result. All cards also share one reviewer/reason form state.

## Decision

Keep the persisted global queue and the existing API contract. Each card will display its run ID, action ID, tool arguments, model reason, expected result, and triggered rules. Reviewer and review-reason values will be stored per approval ID so editing one card cannot alter another card.

Historical pending requests remain visible for auditability. The application will not automatically approve, reject, or delete them.

## Error Handling And Security

Arguments are rendered as escaped text with `JSON.stringify`; they are never interpreted as markup. Existing authentication, exactly-once approval transitions, and server-side guardrails remain unchanged.

## Verification

Frontend component tests will cover visible action context and independent form values for multiple approvals. The full frontend suite, production build, backend suite, Docker health check, and a browser-driven real calculator run must pass.
