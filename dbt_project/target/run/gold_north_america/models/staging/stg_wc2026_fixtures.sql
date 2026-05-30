

  create or replace view `gold-north-america`.`gold_north_america`.`stg_wc2026_fixtures`
  OPTIONS()
  as with source as (
    select * from `gold-north-america`.`gold_north_america`.`results`
),

wc2026 as (
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

        -- extracting group from fixtures
        -- this will be joined with groups data later
        case
            when home_team in ('Mexico', 'South Korea', 'Czech Republic', 'South Africa')
                then 'A'
            when home_team in ('Canada', 'Qatar', 'Switzerland', 'Bosnia and Herzegovina')
                then 'B'
            when home_team in ('Brazil', 'Morocco', 'Haiti', 'Scotland')
                then 'C'
            when home_team in ('United States', 'Australia', 'Turkey', 'Paraguay')
                then 'D'
            when home_team in ('Germany', 'Ecuador', 'Ivory Coast', 'Curaçao')
                then 'E'
            when home_team in ('Netherlands', 'Japan', 'Sweden', 'Tunisia')
                then 'F'
            when home_team in ('Belgium', 'Iran', 'Egypt', 'New Zealand')
                then 'G'
            when home_team in ('Spain', 'Uruguay', 'Saudi Arabia', 'Cape Verde')
                then 'H'
            when home_team in ('France', 'Senegal', 'Norway', 'Iraq')
                then 'I'
            when home_team in ('Argentina', 'Austria', 'Algeria', 'Jordan')
                then 'J'
            when home_team in ('Portugal', 'Colombia', 'DR Congo', 'Uzbekistan')
                then 'K'
            when home_team in ('England', 'Croatia', 'Panama', 'Ghana')
                then 'L'
            else 'Unknown'
        end as group_name,

         -- flagging as future fixture
        case
            when home_score is null then true
            else false
        end as is_future_fixture

    from source
    where tournament = 'FIFA World Cup'
    and date >= '2026-06-11'
)

select * from wc2026;

