# F5 release and recovery

Baseline: f3dc8fc on feature/p7. Unrelated owner changes remain in the original
worktree. Implementation is isolated on feature/f5-applicant.

The schema-only recovery commit immediately preceding the F5 feature commit has
the existing UI/API behaviour and both migration revisions. Keep this commit as
the recovery target. Do not blindly deploy f3dc8fc after applying 0002: that
build's startup runs Alembic but cannot resolve revision 0002.

Before the live push: verify a private database backup and a successful isolated
restore, the current Render deployment and rollback access. Never commit dumps,
environment values, private applicant data or recordings containing those data.

Deploying the recovery commit keeps the new table and all data. It removes F5's
UI/API while retaining a valid migration chain. No database restore or downgrade
is needed for an application regression. Retained Render artifacts are optional;
the recovery commit can also be rebuilt. A Render rollback does not restore Neon.

Migration 0002 only adds a table and extends consent section allowlists. It never
deletes financial records. Downgrade refuses to run when F5 data exists. Test
fresh migration, populated 0001 upgrade, and recovery startup on a 0002 database.

Do not reset live demo data or run the destructive pytest fixtures against Neon.
The health endpoint tests connectivity only; validate the sharing workflow too.
Do not merge main as part of F5. Never push unrelated dirty files.


## Tested live-release recovery checkpoint

F5 release: 41b61fe (feature/p7), verified live 18 Nov 2026.
Prepared append-only recovery: a7e05da on recovery/f5-ready-20261118; its tree
exactly matches 92d2faf and its backend/frontend/Docker CI passed. As long as the
live head is 41b61fe, advancing to a7e05da is a normal fast-forward revert, with
no database downgrade and no force push. If live advances, prepare a new revert
on that head instead. The original 0001-only build is not the recovery target.

A private pre-release Neon archive exists outside Git with owner/SYSTEM-only
Windows ACLs and verified archive decoding. Real production data was not restored
into the local test cluster. The successful restore/startup drill used DEMO data.
No rollback was needed for the verified F5 deployment.
