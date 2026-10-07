with normalized_events as (
    select
        coalesce(nullif(user_id, ''), cast(amplitude_id as varchar)) as amplitude_user_id,
        event_time,
        session_id
    from {{ ref('stg_event') }}
),
session_metrics as (
    select
        amplitude_user_id,
        session_id,
        min(event_time) as session_start_at,
        max(event_time) as session_end_at
    from normalized_events
    group by amplitude_user_id, session_id
),
user_metrics as (
    select
        amplitude_user_id,
        min(event_time) as user_created_at_value,
        min(event_time) as first_session_at_value,
        max(event_time) as last_session_at_value,
        count(*) as total_events_per_user_value
    from normalized_events
    group by amplitude_user_id
),
user_session_metrics as (
    select
        amplitude_user_id,
        count(*) as total_sessions_per_user_value,
        avg(date_diff('second', session_start_at, session_end_at) / 60.0) as average_session_length_in_minutes_value
    from session_metrics
    group by amplitude_user_id
)
select
    user_metrics.amplitude_user_id as amplitude_user_id,
    cast(user_metrics.user_created_at_value as varchar) as user_created_at,
    cast(user_metrics.first_session_at_value as varchar) as first_session_at,
    cast(user_metrics.last_session_at_value as varchar) as last_session_at,
    user_metrics.total_events_per_user_value as total_events_per_user,
    user_session_metrics.total_sessions_per_user_value as total_sessions_per_user,
    user_session_metrics.average_session_length_in_minutes_value as average_session_length_in_minutes
from user_metrics
inner join user_session_metrics
    on user_metrics.amplitude_user_id = user_session_metrics.amplitude_user_id
