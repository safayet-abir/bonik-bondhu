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
