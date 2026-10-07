select
    cast(id as bigint) as keyword_id,
    cast(ad_group_id as bigint) as ad_group_id,
    cast(advertiser_id as bigint) as advertiser_id,
    lower(cast(archived as varchar)) = 'true' as archived,
    case
        when upper(cast(match_type as varchar)) = 'BROAD' then 'Broad'
        when upper(cast(match_type as varchar)) = 'EXACT' then 'Exact'
        else cast(match_type as varchar)
    end as match_type,
    case
        when upper(cast(parent_type as varchar)) = 'AD_GROUP' then 'Ad group'
        when lower(cast(parent_type as varchar)) = 'CAMPAIGN' then 'campaign'
        else cast(parent_type as varchar)
    end as parent_type,
    cast(value as varchar) as keyword_value
from {{ source('raw', 'keyword_history') }}
