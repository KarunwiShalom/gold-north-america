with source as (
    select * from {{ source('raw', 'results') }}
),

renamed as (
    select
        date,
        home_team,
        away_team,
        home_score,
        away_score,
        tournament,
        city,
        country,
        neutral,

        case
            when home_score > away_score  then home_team
            when away_score > home_score  then away_team
            else 'Draw'
        end as result,

        case
            when tournament = 'FIFA World Cup'               then 'World Cup'
            when tournament like '%World Cup qualification%' then 'Qualification'
            when tournament in (
                'UEFA Euro', 'Copa América', 'Africa Cup of Nations',
                'AFC Asian Cup', 'CONCACAF Gold Cup', 'FIFA Confederations Cup'
            )                                                then 'Continental'
            when tournament = 'Friendly'                     then 'Friendly'
            else 'Other'
        end as tournament_category,

        -- base weight by tournament type
        case
            when tournament = 'FIFA World Cup'               then 4.0
            when tournament like '%World Cup qualification%' then 2.5
            when tournament in (
                'UEFA Euro', 'Copa América', 'Africa Cup of Nations',
                'AFC Asian Cup', 'CONCACAF Gold Cup', 'FIFA Confederations Cup'
            )                                                then 3.0
            when tournament = 'Friendly'                     then 1.0
            else 1.5
        end as base_weight,

        -- Adding a recency multiplier to add a prioritise recent form in the model
        -- recency multiplier: decays linearly from 2.0 (today) to 0.5 (10 years ago)
        -- matches in last 12 months get ~1.8-2.0x
        -- matches 5 years ago get ~1.0x
        -- matches 10 years ago get ~0.5x
        greatest(
            0.5,
            2.0 - (1.5 * date_diff(current_date(), cast(date as date), day) / 3650.0)
        ) as recency_multiplier,

        -- final weight = base * recency
        case
            when tournament = 'FIFA World Cup'               then 4.0
            when tournament like '%World Cup qualification%' then 2.5
            when tournament in (
                'UEFA Euro', 'Copa América', 'Africa Cup of Nations',
                'AFC Asian Cup', 'CONCACAF Gold Cup', 'FIFA Confederations Cup'
            )                                                then 3.0
            when tournament = 'Friendly'                     then 1.0
            else 1.5
        end *
        greatest(
            0.5,
            2.0 - (1.5 * date_diff(current_date(), cast(date as date), day) / 3650.0)
        ) as match_weight,

        case
            when home_score is null then true
            else false
        end as is_future_fixture

    from source
)

select * from renamed