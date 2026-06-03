# Review Status Template

Use this structure in `docs/internal/review-status.md` (tracked). Commit it in the **same** commit as the reviewed feature change — never as a standalone commit.

```md
## branch: <branch-name>
- last_reviewed_commit: <sha>
- last_reviewed_at: <iso-datetime>
- last_review_context: review-w-auto-doc
- last_action: post_commit_synced | reviewed | skipped_pending
- findings_resolved: yes | no
- doc_decisions_made: yes | no
- ready_to_commit: yes | no | n/a
- raw_log_decision: add | update_existing | skip_trivial
- adr_file_decision: add | update_existing | skip_trivial
- user_value_log_decision: add | update_existing | skip_trivial
- raw_log_status: done | pending | n/a
- adr_file_status: done | pending | n/a
- user_value_log_status: done | pending | n/a
- notes: <optional short note>
```
