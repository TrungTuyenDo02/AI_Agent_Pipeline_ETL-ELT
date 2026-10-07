SELECT
    CAST(p_id AS BIGINT) AS p_id,
    CAST(professor AS BIGINT) AS professor,
    CAST(student AS BIGINT) AS student,
    CAST(hasPosition AS VARCHAR) AS hasposition,
    CAST(inPhase AS VARCHAR) AS inphase,
    CAST(yearsInProgram AS VARCHAR) AS yearsinprogram
FROM {{ source('raw', 'person') }}
