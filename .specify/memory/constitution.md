<!--
================================================================================================
SYNC IMPACT REPORT
================================================================================================
Version Change: 0.0.0 → 1.0.0
Date: 2025-11-03

Type of Change: MAJOR (initial constitution creation)

Principles Defined:
  1. Specification-Driven Development (NEW)
  2. Type Safety & Code Quality (NEW)
  3. User-Centric Design (NEW)
  4. Test Independence (NEW)
  5. Incremental Delivery (NEW)

Sections Added:
  - Core Principles (5 principles)
  - Code Quality Standards
  - Governance

Templates Requiring Updates:
  ✅ .specify/templates/spec-template.md - Already enforces user stories, priorities, independent testing
  ✅ .specify/templates/plan-template.md - UPDATED: Constitution Check now includes all 5 principles
  ✅ .specify/templates/tasks-template.md - Already organizes by user story with independent testing
  ✅ .specify/templates/checklist-template.md - Generic template, customized by /speckit.checklist command

Follow-up TODOs:
  - None required - all templates aligned with constitution principles

================================================================================================
-->

# r/progmetal Album Catalog Constitution

## Core Principles

### I. Specification-Driven Development

Every feature begins with a complete, technology-agnostic specification before any implementation planning occurs. Specifications MUST:

- Define user value through prioritized user stories (P1, P2, P3...)
- Establish measurable success criteria without implementation details
- Identify functional requirements that are testable and unambiguous
- Document assumptions, constraints, and scope boundaries explicitly

**Rationale**: Separating WHAT from HOW ensures business needs are fully understood before technical decisions constrain the solution. This enables better design choices and prevents premature optimization.

### II. Type Safety & Code Quality (NON-NEGOTIABLE)

All Python code MUST meet strict quality standards enforced by automated tools:

- **Type annotations**: Required on all function parameters and return values
- **Type checking**: Zero `pyright` errors in strict mode (no `Any` types without justification)
- **Linting**: Zero `ruff check` errors, full PEP 8 compliance
- **Formatting**: Automated via `ruff format` (100 char line limit)
- **Documentation**: Docstrings required for all functions and classes

**Validation Process**: Run `pyright`, `ruff check .`, and `ruff format .` before every commit.

**Rationale**: Type safety catches bugs at development time, reduces cognitive load during code review, and enables confident refactoring. This is non-negotiable because the cost of runtime type errors far exceeds the investment in type annotations.

### III. User-Centric Design

Features are organized around user stories that deliver independent, testable value. Each user story MUST:

- Be independently implementable and testable
- Deliver standalone value (viable MVP at P1)
- Include clear acceptance scenarios (Given/When/Then)
- Have measurable success criteria from user perspective

**Rationale**: User story independence enables iterative delivery, parallel development, and early validation. Users receive value incrementally rather than in a single "big bang" release.

### IV. Test Independence

Testing requirements are explicitly defined in specifications, not assumed. When tests are requested:

- Contract tests validate API contracts/interfaces
- Integration tests verify user journeys end-to-end
- Unit tests (optional) validate isolated component behavior
- Tests are written FIRST and MUST FAIL before implementation begins (TDD)

**Rationale**: Not all features require the same testing rigor. Explicit test requirements prevent over-testing simple features and under-testing complex ones. Test-first development ensures requirements are testable before implementation.

### V. Incremental Delivery

Features are built in priority order (P1 → P2 → P3) with checkpoints after each user story. At any checkpoint:

- All completed user stories remain independently functional
- The application can be deployed/demoed with partial feature set
- No user story depends on lower-priority stories for core functionality

**Rationale**: Incremental delivery de-risks development, enables early user feedback, and ensures the most critical functionality is always delivered first. If time/budget constraints arise, lower-priority stories can be deferred without losing core value.

## Code Quality Standards

### Enforcement Tools

- **pyright**: Type checking (strict mode, zero errors)
- **Ruff**: Linting, formatting, PEP 8 compliance (zero errors)
- **pytest**: Test execution (when tests are specified)

### Pre-Commit Checklist

1. Run `pyright` → resolve all type errors
2. Run `ruff check .` → resolve all lint errors
3. Run `ruff format .` → apply consistent formatting
4. Run `pytest` → verify all tests pass (if tests exist)
5. Verify no `Any` types without justification comments

### Type Annotation Guidelines

- Use `typing` module types: `list[T]`, `dict[K, V]`, `Optional[T]`, etc.
- Django querysets: Use proper generic types (`QuerySet[Model]`)
- Return types: Always annotate, including `None` for void functions
- Justification required for `Any`: Comment explaining why typing is impossible/impractical

## Governance

### Amendment Process

1. **Proposal**: Document proposed changes with rationale and impact analysis
2. **Review**: Evaluate alignment with project goals and template consistency
3. **Version Bump**: Follow semantic versioning (MAJOR.MINOR.PATCH)
   - MAJOR: Backward-incompatible changes (principle removal/redefinition)
   - MINOR: New principles or sections added
   - PATCH: Clarifications, wording improvements, typo fixes
4. **Propagation**: Update all dependent templates, commands, and documentation
5. **Sync Report**: Document changes in HTML comment at top of this file

### Compliance Review

- All feature specifications MUST be validated against constitution principles
- Implementation plans MUST include "Constitution Check" section verifying compliance
- Tasks MUST be organized according to user story structure (Principle III)
- Code reviews MUST verify type safety and quality standards (Principle II)

### Violation Justification

When constitution principles cannot be followed, violations MUST be:

1. **Documented**: Explain why the principle doesn't apply
2. **Justified**: Demonstrate that simpler alternatives were considered
3. **Tracked**: Record in implementation plan's "Complexity Tracking" table
4. **Reviewed**: Require explicit approval in code review

### Related Documentation

- Feature specifications: `specs/###-feature-name/spec.md`
- Implementation plans: `specs/###-feature-name/plan.md`
- Agent guidance: `CLAUDE.md` (for Claude Code development)
- Project README: `README.md` (for contributors)

**Version**: 1.0.0 | **Ratified**: 2025-11-03 | **Last Amended**: 2025-11-03
