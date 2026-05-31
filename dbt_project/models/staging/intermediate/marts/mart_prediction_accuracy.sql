with predictions as (
    select
        date,
        `group` as group_name,
        home_team,
        away_team,
        prob_home_win,
        prob_draw,
        prob_away_win,
        most_likely_score,
        case
            when prob_home_win >= prob_draw and prob_home_win >= prob_away_win then 'home_win'
            when prob_draw >= prob_home_win and prob_draw >= prob_away_win then 'draw'
            else 'away_win'
        end as predicted_outcome
    from {{ source('raw', 'predictions_group_stage') }}
),

actuals as (
    select
        date,
        group_name,
        home_team,
        away_team,
        home_goals,
        away_goals,
        result as actual_outcome,
        status
    from {{ source('raw', 'actual_results') }}
    where status = 'FINISHED'
),

joined as (
    select
        p.date,
        p.group_name,
        p.home_team,
        p.away_team,
        p.prob_home_win,
        p.prob_draw,
        p.prob_away_win,
        p.most_likely_score,
        p.predicted_outcome,
        a.home_goals,
        a.away_goals,
        a.actual_outcome,
        case when p.predicted_outcome = a.actual_outcome then 1 else 0 end
            as correct_outcome,
        round(
            pow(p.prob_home_win - case when a.actual_outcome = 'home_win' then 1 else 0 end, 2) +
            pow(p.prob_draw     - case when a.actual_outcome = 'draw'     then 1 else 0 end, 2) +
            pow(p.prob_away_win - case when a.actual_outcome = 'away_win' then 1 else 0 end, 2),
        4) as brier_score
    from predictions p
    inner join actuals a
        on p.home_team = a.home_team
        and p.away_team = a.away_team
        and p.date = a.date
)

select * from joined
order by date, group_name
