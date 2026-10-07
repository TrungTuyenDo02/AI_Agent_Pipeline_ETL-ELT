with application_metrics as (
    select
        a.posting_id,
        count(case when a.type = 'referral' then a.id end)::bigint as count_referred_applications,
        count(case when a.type in ('posting', 'agency') then a.id end)::bigint as count_posting_applications,
        count(case when a.type = 'user' then a.id end)::bigint as count_manual_user_applications,
        count(distinct a.opportunity_id)::bigint as count_opportunities,
        count(distinct case when o.archived_at is null then a.opportunity_id end)::bigint as count_open_opportunities
    from {{ ref('stg_application') }} a
    left join {{ ref('stg_opportunity') }} o
        on o.id = a.opportunity_id
    group by a.posting_id
), interview_metrics as (
    select
        pi.posting_id,
        count(distinct pi.interview_id)::bigint as count_interviews,
        count(distinct i.opportunity_id)::bigint as count_interviewees
    from {{ ref('stg_posting_interview') }} pi
    inner join {{ ref('stg_interview') }} i
        on i.id = pi.interview_id
    where i.canceled_at is null
    group by pi.posting_id
), requisition_metrics as (
    select
        rp.posting_id,
        count(distinct rp.requisition_id)::bigint as count_requisitions
    from {{ ref('stg_requisition_posting') }} rp
    inner join {{ ref('stg_requisition') }} r
        on r.id = rp.requisition_id
    where rp._fivetran_deleted = false
      and r._fivetran_deleted = false
    group by rp.posting_id
)
select
    p.categories_commitment as job_commitment,
    p.categories_location as job_location,
    p.categories_team as job_team,
    p.content_description,
    p.created_at,
    p.creator_id as creator_user_id,
    p.id as posting_id,
    p.owner_id as owner_user_id,
    p.state as current_state,
    p.text as job_title,
    p.updated_at,
    coalesce(am.count_referred_applications, 0)::bigint as count_referred_applications,
    coalesce(am.count_posting_applications, 0)::bigint as count_posting_applications,
    coalesce(am.count_manual_user_applications, 0)::bigint as count_manual_user_applications,
    coalesce(am.count_opportunities, 0)::bigint as count_opportunities,
    coalesce(am.count_open_opportunities, 0)::bigint as count_open_opportunities,
    coalesce(im.count_interviews, 0)::bigint as count_interviews,
    coalesce(im.count_interviewees, 0)::bigint as count_interviewees,
    coalesce(rm.count_requisitions, 0)::bigint as count_requisitions,
    case when coalesce(rm.count_requisitions, 0) > 0 then 'true' else 'false' end as has_requisition
from {{ ref('stg_posting') }} p
left join application_metrics am
    on am.posting_id = p.id
left join interview_metrics im
    on im.posting_id = p.id
left join requisition_metrics rm
    on rm.posting_id = p.id
where p._fivetran_deleted = false
