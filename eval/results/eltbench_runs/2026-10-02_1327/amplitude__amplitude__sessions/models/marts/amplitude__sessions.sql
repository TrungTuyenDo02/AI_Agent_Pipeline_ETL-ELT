WITH session_aggregates AS (
    SELECT
        user_id,
        session_id,
        CAST(user_id || '-' || CAST(session_id AS VARCHAR) AS VARCHAR) AS unique_session_id,
        CAST(COUNT(*) AS BIGINT) AS events_per_session,
        MIN(event_time) AS session_started_at_ts,
        MAX(event_time) AS session_ended_at_ts,
        CAST(date_diff('microsecond', MIN(event_time), MAX(event_time)) / 60000000.0 AS DOUBLE) AS session_length_in_minutes,
        CAST(MIN(event_time) AS DATE) AS session_started_at_day,
        CAST(MAX(event_time) AS DATE) AS session_ended_at_day
    FROM {{ ref('stg_event') }}
    GROUP BY user_id, session_id
), numbered_sessions AS (
    SELECT
        unique_session_id,
        user_id,
        events_per_session,
        CAST(session_started_at_ts AS VARCHAR) AS session_started_at,
        CAST(session_ended_at_ts AS VARCHAR) AS session_ended_at,
        session_length_in_minutes,
        session_started_at_day,
        session_ended_at_day,
        CAST(ROW_NUMBER() OVER (
            PARTITION BY user_id
            ORDER BY session_started_at_ts, session_id
        ) AS BIGINT) AS user_session_number
    FROM session_aggregates
)
SELECT
    unique_session_id,
    user_id,
    events_per_session,
    session_started_at,
    session_ended_at,
    session_length_in_minutes,
    session_started_at_day,
    session_ended_at_day,
    user_session_number,
    CAST(CASE WHEN user_session_number = 1 THEN 1 ELSE 0 END AS BIGINT) AS is_first_user_session
FROM numbered_sessions
