with event_candidates as (
    select
        e.device_id,
        e.id,
        e.amplitude_id,
        e.app,
        e.country,
        e.data,
        e.event_type,
        e.event_type_id,
        e.groups,
        e.ip_address,
        e.project_name,
        e.session_id,
        e.user_id,
        e.user_creation_time,
        e.client_event_time,
        e.client_upload_time,
        e.server_received_time,
        e.server_upload_time,
        case
            when abs(epoch(e.server_received_time - e.client_upload_time)) < 60
                then e.client_event_time
            else e.client_event_time + (e.server_received_time - e.client_upload_time)
        end as calculated_event_time,
        t.name as event_type_name,
        t.totals,
        t.value,
        row_number() over (
            partition by e.id
            order by case
                when e.event_type_id is not null and e.event_type_id = t.id then 1
                when e.event_type_id is null and e.event_type = t.value then 2
                else 3
            end,
            t.id
        ) as type_match_number
    from {{ ref('stg_event') }} e
    left join {{ ref('stg_event_type') }} t
        on e.project_name = t.project_name
        and (
            e.event_type_id = t.id
            or (e.event_type_id is null and e.event_type = t.value)
        )
),
event_enriched as (
    select
        device_id,
        id,
        amplitude_id,
        app,
        country,
        data,
        event_type,
        event_type_id,
        groups,
        ip_address,
        project_name,
        session_id,
        user_id,
        user_creation_time,
        client_event_time,
        client_upload_time,
        server_received_time,
        server_upload_time,
        calculated_event_time,
        event_type_name,
        totals,
        value
    from event_candidates
    where type_match_number = 1
),
sessionized as (
    select
        *,
        min(calculated_event_time) over (
            partition by coalesce(nullif(trim(user_id), ''), cast(amplitude_id as varchar)), session_id
        ) as session_started_timestamp,
        max(calculated_event_time) over (
            partition by coalesce(nullif(trim(user_id), ''), cast(amplitude_id as varchar)), session_id
        ) as session_ended_timestamp,
        count(*) over (
            partition by coalesce(nullif(trim(user_id), ''), cast(amplitude_id as varchar)), session_id
        ) as events_per_session,
        row_number() over (
            partition by coalesce(nullif(trim(user_id), ''), cast(amplitude_id as varchar)), session_id
            order by calculated_event_time, id
        ) as session_event_number,
        row_number() over (
            partition by coalesce(nullif(trim(user_id), ''), cast(amplitude_id as varchar))
            order by calculated_event_time, id
        ) as user_event_number
    from event_enriched
),
session_list as (
    select distinct
        coalesce(nullif(trim(user_id), ''), cast(amplitude_id as varchar)) as session_user_key,
        session_id,
        session_started_timestamp
    from sessionized
),
ranked_sessions as (
    select
        session_user_key,
        session_id,
        session_started_timestamp,
        dense_rank() over (
            partition by session_user_key
            order by session_started_timestamp, session_id
        ) as user_session_number
    from session_list
),
finalized as (
    select
        s.*,
        r.user_session_number
    from sessionized s
    left join ranked_sessions r
        on coalesce(nullif(trim(s.user_id), ''), cast(s.amplitude_id as varchar)) = r.session_user_key
        and s.session_id = r.session_id
        and s.session_started_timestamp = r.session_started_timestamp
)
select
    md5(concat_ws('|', cast(id as varchar), device_id, cast(client_event_time as varchar))) as unique_event_id,
    md5(concat_ws('|', coalesce(nullif(trim(user_id), ''), cast(amplitude_id as varchar)), cast(session_id as varchar))) as unique_session_id,
    coalesce(nullif(trim(user_id), ''), cast(amplitude_id as varchar)) as amplitude_user_id,
    cast(id as bigint) as event_id,
    cast(event_type as varchar) as event_type,
    cast(calculated_event_time as varchar) as event_time,
    cast(calculated_event_time as date) as event_day,
    md5(concat_ws('|', cast(project_name as varchar), cast(event_type_id as varchar), coalesce(event_type_name, value))) as unique_event_type_id,
    cast(event_type_id as bigint) as event_type_id,
    cast(event_type_name as varchar) as event_type_name,
    cast(session_id as bigint) as session_id,
    cast(session_event_number as bigint) as session_event_number,
    cast(user_event_number as bigint) as user_event_number,
    cast(groups as varchar) as group_types,
    cast(user_id as varchar) as user_id,
    cast(user_creation_time as varchar) as user_creation_time,
    cast(amplitude_id as bigint) as amplitude_id,
    cast(app as bigint) as app,
    cast(project_name as bigint) as project_name,
    cast(client_event_time as varchar) as client_event_time,
    cast(client_upload_time as varchar) as client_upload_time,
    cast(server_received_time as varchar) as server_received_time,
    cast(server_upload_time as varchar) as server_upload_time,
    cast(country as varchar) as country,
    cast(data as varchar) as data,
    cast(device_id as varchar) as device_id,
    cast(ip_address as varchar) as ip_address,
    cast(totals as bigint) as totals,
    cast(value as varchar) as value,
    cast(events_per_session as bigint) as events_per_session,
    cast(session_started_timestamp as varchar) as session_started_at,
    cast(session_ended_timestamp as varchar) as session_ended_at,
    cast(user_session_number as bigint) as user_session_number,
    cast(session_started_timestamp as date) as session_started_at_day,
    cast(session_ended_timestamp as date) as session_ended_at_day,
    cast(epoch(session_ended_timestamp - session_started_timestamp) / 60.0 as double) as session_length_in_minutes,
    case when user_session_number = 1 then 'true' else 'false' end as is_first_user_session
from finalized
