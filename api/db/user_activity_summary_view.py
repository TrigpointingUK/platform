"""Reusable SQL snippets for the user_activity_summary materialised view."""

CREATE_USER_ACTIVITY_SUMMARY_VIEW_STATEMENTS = [
    """
    CREATE MATERIALIZED VIEW user_activity_summary AS
    WITH log_stats AS (
        SELECT
            user_id,
            COUNT(*) AS total_logs,
            COUNT(DISTINCT trig_id) AS total_trigs_logged
        FROM tlog
        GROUP BY user_id
    ),
    photo_counts AS (
        SELECT
            tl.user_id,
            COUNT(*) AS total_photos
        FROM tphoto tp
        JOIN tlog tl ON tl.id = tp.tlog_id
        WHERE tp.deleted_ind <> 'Y'
        GROUP BY tl.user_id
    )
    SELECT
        u.id AS user_id,
        u.crt_date AS member_since,
        COALESCE(log_stats.total_logs, 0) AS total_logs,
        COALESCE(log_stats.total_trigs_logged, 0) AS total_trigs_logged,
        COALESCE(photo_counts.total_photos, 0) AS total_photos
    FROM "user" u
    LEFT JOIN log_stats ON log_stats.user_id = u.id
    LEFT JOIN photo_counts ON photo_counts.user_id = u.id
    WHERE
        COALESCE(log_stats.total_logs, 0) > 0
        OR COALESCE(log_stats.total_trigs_logged, 0) > 0
        OR COALESCE(photo_counts.total_photos, 0) > 0
    WITH DATA;
    """,
    """
    CREATE UNIQUE INDEX idx_user_activity_summary_user_id
    ON user_activity_summary (user_id)
    """,
    """
    CREATE INDEX idx_user_activity_summary_trigs_desc
    ON user_activity_summary (total_trigs_logged DESC, user_id DESC)
    """,
    """
    CREATE INDEX idx_user_activity_summary_photos_desc
    ON user_activity_summary (total_photos DESC, user_id DESC)
    """,
    """
    CREATE INDEX idx_user_activity_summary_member_since_desc
    ON user_activity_summary (member_since DESC, user_id DESC)
    """,
]

DROP_USER_ACTIVITY_SUMMARY_VIEW_STATEMENTS = [
    "DROP INDEX IF EXISTS idx_user_activity_summary_member_since_desc",
    "DROP INDEX IF EXISTS idx_user_activity_summary_photos_desc",
    "DROP INDEX IF EXISTS idx_user_activity_summary_trigs_desc",
    "DROP INDEX IF EXISTS idx_user_activity_summary_user_id",
    "DROP MATERIALIZED VIEW IF EXISTS user_activity_summary",
]
