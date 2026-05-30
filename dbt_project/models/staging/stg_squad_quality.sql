with source as (
    select * from {{ source('raw', 'squad_quality') }}
),

cleaned as (
    select
        -- fixing team name mismatches detected in the dataset
        case
            when team_name = 'UEFA Playoff A'  then 'Bosnia and Herzegovina'
            when team_name = 'UEFA Playoff B'  then 'Sweden'
            when team_name = 'UEFA Playoff C'  then 'Turkey'
            when team_name = 'UEFA Playoff D'  then 'Czech Republic'
            when team_name = 'Intercont PO 1'  then 'DR Congo'
            when team_name = 'Intercont PO 2'  then 'Iraq'
            when team_name = 'Curacaio'        then 'Curaçao'
            when team_name = 'United States'   then 'USA'
            else team_name
        end as team,

        confederation,
        fifa_ranking_jan2026        as fifa_rank,
        fifa_points_jan2026         as fifa_points,
        star_player_rating,
        avg_player_age,
        goalkeeper_rating,
        squad_depth_score,
        squad_score,
        h2h_vs_top10_winrate,
        knockout_stage_reach_rate,
        composite_strength,

        -- normalise composite_strength to a multiplier around 1.0
        -- range is roughly 48 - 85, we map to 0.75 - 1.25
        round(
            0.75 + (0.50 * safe_divide(
                composite_strength - 48.0,
                85.0 - 48.0
            ))
        , 4) as squad_multiplier

    from source
    -- filtering out Nigeria (did not qualify) and TBD placeholders already mapped
    where team_name != 'Nigeria'
    and team_name not like 'is_tbd%'
)

select * from cleaned