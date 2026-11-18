# F5 Applicant details ? validation and release status (18 Nov 2026)

## Result

F5 is implemented on `feature/f5-applicant` in an isolated worktree.
Baseline is `f3dc8fc`; schema-compatible recovery commit is `92d2faf`.
The original worktree's unrelated modified and untracked files were preserved.

## Implemented

- Optional three-step owner identity form on Sharing, seven-field completeness.
- NID: 10/13/17 digits, Bangla digit normalization; birth date validation; optional licence.
- GET/PUT are owner-scoped; ordinary responses mask NID and do not return birth date.
- Omitted private values are retained; explicit null clears them through the API.
- Applicant consent is off by default even if requested by a lender.
- Incomplete identity cannot be shared. Failed approval leaves the request pending.
- Only an explicitly approved, authorized case snapshot includes the full declaration.
- Lists, audit metadata and AI tools do not gain identity fields.
- Identity edits preserve the previous snapshot and do not stale financial assessments.
- Shop and farm declarations are separate; seeded declarations are fictional DEMO data.
- Migration 0002 is additive; 0001 now reads its frozen original schema.
- Populated downgrade refuses to erase F5 data; use the compatible recovery build instead.
- CaseFile's narrow-screen grid/table overflow was corrected while adding the section.

## Privacy decision

SUG-63 uses handoff option (b): NID is stored as TEXT without separate field-level
cryptography. The owner UI states this. No provider-at-rest encryption, verified
identity, production compliance or completed legal review is claimed. F5 does not
verify NIDs, lend or approve credit. Real-person use still needs the privacy review.

## Executed validation

All data-affecting tests used a newly initialized PostgreSQL 16 cluster bound to
127.0.0.1:15432. No data-affecting test or write targeted the existing development/test databases or Neon.
A read-only capability check on the configured local test role preceded creation
of the separate disposable cluster. Neon was accessed later only for the owner-authorized
private backup and read-only release verification.

| Check | Result |
|---|---|
| Full backend suite | 297 passed; no skips (before two additional privacy cases) |
| Final F5 API/privacy suite | 24 passed, including those two additional cases |
| TypeScript and Vite production build | Passed |
| Bangla/English parity | 1,029 keys each |
| F5 browser | Passed: form, masked response, unchecked consent, lender snapshot, revocation |
| axe-core 4.10.3 | Zero WCAG 2 A/AA + 2.1 AA violations on Sharing and CaseFile at 360/1440px |
| Reflow | Sharing and CaseFile fit 360/1440px after settling responsive transitions |
| Existing browser suites | p1, p2, p3, p4, p5, p6 AI-off, p7, ultra-fit and f4-graph all passed |
| Backup and restore demonstration | Local demo dump restored into a separate local database |
| Recovery build | 92d2faf started on restored 0002 database; financial totals, identity row count and snapshot fingerprints unchanged |

Fresh credentials were generated for disposable fixtures; they were not printed.
Existing browser-suite screenshots were suppressed. F5 screenshots mask the NID.
AI-on external-provider evaluation was not repeated: F5 adds no AI capability and
no provider credentials were used. Docker build is left to GitHub CI (no local Docker).

## Pre-release checkpoint (superseded by release record below)

No push to `feature/p7`, main merge, live reset, Neon migration, or live data write
was performed. A localhost demo runs at port 18080; recovery demo at 18081.
The owner requested a demo when asked about live backup/restore readiness.
Live backup, restore capability and Render dashboard access remain unverified.

Before a live release, confirm those access/recovery prerequisites and CI for the
exact release commit, then advance the deploy branch without overwriting unrelated
work. Render starts by running Alembic, so a push can change the database.

For an application regression, revert only the F5 feature commit while retaining
92d2faf's migration chain, test it, then deploy. Alternatively rebuild 92d2faf.
Do not blindly roll back to f3dc8fc after 0002: its startup cannot resolve 0002.
Do not downgrade a populated live database or restore a backup merely for a UI bug.
A database restore is a separate recovery action and can lose later writes.


## Later release verification ? F5 is LIVE

Release code: `41b61fe06f58ec0b6ca7e8f9c31f1f945c88f403` on `feature/p7`.
URL: https://bonik-bondhu.onrender.com/
Main was not merged. Source work continued in the isolated F5 worktree; original
user modifications were not overwritten. Post-release documentation is committed
on feature/f5-applicant without causing another live deployment.

The owner explicitly allowed the existing configured Neon connection for private
backup and release work only. A pre-release custom archive was saved outside all
Git worktrees with Windows ACL access restricted to the owner and SYSTEM. Full
archive decoding was verified into a null sink. Real production records were NOT
restored into the trust-authenticated localhost demo cluster. The earlier complete
restore drill used only fictional demo records. No configuration values, backup
content, hashes of user credentials or personal records were published.

Prepared emergency branch: `recovery/f5-ready-20261118`, commit
`a7e05daf08f343a505c9ddc42e2470d8228dbc86`. Its tree exactly matches `92d2faf`
(the old app with both migrations). It is an append-only revert of the F5 feature
commit, so it can fast-forward the current release branch without rewriting Git
history. This retains applicant data and the 0002 revision. It has NOT been used
on live because release verification passed. If more commits land on feature/p7,
rebuild/review the revert on that new head; never force-push this checkpoint.

Verified after Render changed over:
- HTTP 200 for the public SPA and health; database status ok.
- Live JS SHA-256 matches the tested local release bundle exactly.
- F5 public route exists and anonymous GET returns 401 AUTH_REQUIRED.
- Neon revision is 0002_applicant_details; applicant table and both new consent
  allowlists are present.
- Transactions, debts, financing requests, shared reports and business profiles
  match private pre-release fingerprints. No reset or reseed was run on live.

CI passed for all three jobs (backend, frontend, Docker) on each:
- F5 source: https://github.com/safayet-abir/bonik-bondhu/actions/runs/44245040205
- Prepared recovery: https://github.com/safayet-abir/bonik-bondhu/actions/runs/44246316384
- Live branch: https://github.com/safayet-abir/bonik-bondhu/actions/runs/44246744264

Limit: authenticated owner/lender end-to-end tests were executed on isolated
fictional demo data, not on live accounts. No discovered demo credentials were
used to log into production. No real-user identity data was used for testing.
F6/F7, institution self-registration and additional farm types remain out of scope.
The NID plaintext-storage/privacy-review limitation above still applies.
