

  create or replace view `gold-north-america`.`gold_north_america`.`stg_fifa_rankings`
  OPTIONS()
  as with source as (
    select * from `gold-north-america`.`gold_north_america`.`fifa_rankings`
),

renamed as (
    select
        rank as fifa_rank,

        -- normalise team names to match results table
        case
            when team = 'USA'                  then 'United States'
            when team = 'Türkiye'              then 'Turkey'
            when team = 'Côte d\'Ivoire'       then 'Ivory Coast'
            when team = 'Czechia'              then 'Czech Republic'
            when team = 'Bosnia & Herzegovina' then 'Bosnia and Herzegovina'
            when team = 'Curacao'              then 'Curaçao'
            else team
        end as team,

        points as fifa_points,

        case
            when rank <= 10  then 1
            when rank <= 25  then 2
            when rank <= 50  then 3
            when rank <= 100 then 4
            else 5
        end as tier

    from source
)

select * from renamed;

