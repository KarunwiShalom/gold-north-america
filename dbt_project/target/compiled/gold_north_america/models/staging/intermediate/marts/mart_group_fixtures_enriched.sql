with fixtures as (
    select * from `gold-north-america`.`gold_north_america`.`stg_wc2026_fixtures`
    where is_future_fixture = true
),

strength as (
    select * from `gold-north-america`.`gold_north_america`.`int_team_strength`
),

squad as (
    select * from `gold-north-america`.`gold_north_america`.`stg_squad_quality`
),

global_avg as (
    select
        avg(avg_attack) as avg_attack
    from strength
),

enriched as (
    select
        f.date,
        f.group_name,
        f.home_team,
        f.away_team,
        f.city,
        f.country,

        -- home team ratings
        coalesce(h.attack_rating,  1.0) as home_attack,
        coalesce(h.defence_rating, 1.0) as home_defence,
        coalesce(h.fifa_points,    1200) as home_fifa_points,
        coalesce(h.fifa_rank,      100)  as home_fifa_rank,
        coalesce(hs.squad_multiplier, 1.0) as home_squad_multiplier,

        -- away team ratings
        coalesce(a.attack_rating,  1.0) as away_attack,
        coalesce(a.defence_rating, 1.0) as away_defence,
        coalesce(a.fifa_points,    1200) as away_fifa_points,
        coalesce(a.fifa_rank,      100)  as away_fifa_rank,
        coalesce(as_.squad_multiplier, 1.0) as away_squad_multiplier,

        -- expected goals (lambda) with squad quality multiplier
        round(
            coalesce(h.attack_rating, 1.0)
            * coalesce(a.defence_rating, 1.0)
            * g.avg_attack
            * coalesce(hs.squad_multiplier, 1.0),
        4) as lambda_home,

        round(
            coalesce(a.attack_rating, 1.0)
            * coalesce(h.defence_rating, 1.0)
            * g.avg_attack
            * coalesce(as_.squad_multiplier, 1.0),
        4) as lambda_away

    from fixtures f
    left join strength h  on f.home_team = h.team
    left join strength a  on f.away_team = a.team
    left join squad hs    on f.home_team = hs.team
    left join squad as_   on f.away_team = as_.team
    cross join global_avg g
)

select * from enriched
order by date, group_name