with match_results as (
    select * from {{ ref('stg_match_results') }}
    where is_future_fixture = false
    and date >= '2016-01-01'
),

home_stats as (
    select
        home_team                           as team,
        count(*)                            as matches_played,
        sum(home_score * match_weight)      as weighted_goals_scored,
        sum(away_score * match_weight)      as weighted_goals_conceded,
        sum(match_weight)                   as total_weight
    from match_results
    where home_score is not null
    group by home_team
),

away_stats as (
    select
        away_team                           as team,
        count(*)                            as matches_played,
        sum(away_score * match_weight)      as weighted_goals_scored,
        sum(home_score * match_weight)      as weighted_goals_conceded,
        sum(match_weight)                   as total_weight
    from match_results
    where away_score is not null
    group by away_team
),

combined as (
    select
        coalesce(h.team, a.team)                        as team,
        coalesce(h.matches_played, 0)
            + coalesce(a.matches_played, 0)             as total_matches,
        coalesce(h.weighted_goals_scored, 0)
            + coalesce(a.weighted_goals_scored, 0)      as weighted_goals_scored,
        coalesce(h.weighted_goals_conceded, 0)
            + coalesce(a.weighted_goals_conceded, 0)    as weighted_goals_conceded,
        coalesce(h.total_weight, 0)
            + coalesce(a.total_weight, 0)               as total_weight
    from home_stats h
    full outer join away_stats a on h.team = a.team
),

rates as (
    select
        team,
        total_matches,
        weighted_goals_scored,
        weighted_goals_conceded,
        total_weight,
        safe_divide(weighted_goals_scored, total_weight)    as attack_rate,
        safe_divide(weighted_goals_conceded, total_weight)  as defence_rate
    from combined
    where total_matches >= 5
),

global_avg as (
    select
        avg(attack_rate)    as avg_attack,
        avg(defence_rate)   as avg_defence
    from rates
),

normalised as (
    select
        r.team,
        r.total_matches,
        r.attack_rate,
        r.defence_rate,
        safe_divide(r.attack_rate, g.avg_attack)    as raw_attack_rating,
        safe_divide(r.defence_rate, g.avg_defence)  as raw_defence_rating,
        g.avg_attack,
        g.avg_defence
    from rates r
    cross join global_avg g
),

-- join FIFA rankings
with_rankings as (
    select
        n.*,
        f.fifa_rank,
        f.fifa_points,
        f.tier,

        -- FIFA-based rating: convert points to a 0-2 scale
        -- top team ~1877 pts, bottom WC team ~1300 pts
        -- mapping this to 0.5 - 1.8 range
        0.5 + (1.3 * safe_divide(
            f.fifa_points - 1200,
            1877 - 1200
        )) as fifa_attack_rating,

        0.5 + (1.3 * safe_divide(
            f.fifa_points - 1200,
            1877 - 1200
        )) as fifa_defence_proxy

    from normalised n
    left join {{ ref('stg_fifa_rankings') }} f
        on n.team = f.team
),

-- blending historical rating with FIFA rating (this is to avoid debut teams skewing the data)
-- trust = how much the model should trust the historical data
-- more matches = more trust in team's historical data
-- fewer matches = fall back to FIFA's ranking
blended as (
    select
        team,
        total_matches,
        fifa_rank,
        fifa_points,
        tier,
        raw_attack_rating,
        raw_defence_rating,
        fifa_attack_rating,

        -- trust score: caps at 1.0 after 300 weighted matches
        least(safe_divide(total_matches, 300), 1.0) as history_trust,

        -- blended attack rating with ceiling of 2.0
        round(
            least(
                2.0,
                least(safe_divide(total_matches, 300), 1.0) * raw_attack_rating
                + (1 - least(safe_divide(total_matches, 300), 1.0)) * fifa_attack_rating
            )
        , 4) as attack_rating,

        -- blended defence rating with floor of 0.50
        round(
            greatest(
                0.50,
                least(safe_divide(total_matches, 300), 1.0) * raw_defence_rating
                + (1 - least(safe_divide(total_matches, 300), 1.0)) * (2.0 - fifa_attack_rating)
            )
        , 4) as defence_rating,

        avg_attack,
        avg_defence

    from with_rankings
)

select * from blended