select
    cast(id as varchar) as id,
    _fivetran_deleted,
    cast(categories_commitment as varchar) as categories_commitment,
    cast(categories_location as varchar) as categories_location,
    cast(categories_team as varchar) as categories_team,
    cast(content_description as varchar) as content_description,
    cast(created_at as date) as created_at,
    cast(creator_id as varchar) as creator_id,
    cast(owner_id as varchar) as owner_id,
    cast(state as varchar) as state,
    cast(text as varchar) as text,
    cast(updated_at as date) as updated_at
from {{ source('raw', 'posting') }}
