"""Use authoritative daily rollups for step totals."""

from alembic import op

revision = "20260724_0006"
down_revision = "20260724_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO gh_sync_job (
            connection_id,
            data_type,
            fetch_method,
            enabled,
            poll_interval_minutes,
            initial_lookback_days,
            incremental_overlap_minutes,
            page_size,
            priority,
            next_poll_at,
            status,
            consecutive_failures,
            record_count
        )
        SELECT
            connection_id,
            data_type,
            'daily_rollup',
            enabled,
            poll_interval_minutes,
            initial_lookback_days,
            incremental_overlap_minutes,
            1000,
            priority,
            NOW(),
            'queued',
            0,
            0
        FROM gh_sync_job
        WHERE data_type = 'steps' AND fetch_method = 'reconcile'
        ON CONFLICT (connection_id, data_type, fetch_method) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE gh_sync_job
        SET
            enabled = FALSE,
            status = 'completed',
            error = 'fetch_method_superseded',
            range_start = NULL,
            range_end = NULL,
            next_page_token = NULL,
            lease_until = NULL
        WHERE data_type = 'steps' AND fetch_method <> 'daily_rollup'
        """
    )
    op.execute(
        """
        UPDATE gh_records
        SET deleted_at = NOW()
        WHERE
            data_type = 'steps'
            AND fetch_method <> 'daily_rollup'
            AND deleted_at IS NULL
        """
    )


def downgrade() -> None:
    raise RuntimeError("Step rollup migration preserves superseded records and is not reversible")
