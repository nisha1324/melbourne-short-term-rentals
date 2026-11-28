-- Entire-home prices by council, as quoted and allowing for size.
--   raw_vs_market_pct  : council median against the median of all priced entire homes
--   same_size_vs_market_pct : median of (price / market median for the same bedrooms), minus 1;
--                       how a council's homes price against same-size homes market-wide
--   studio_or_1bed_pct : share of the council's priced entire homes that are studios or 1-bedroom
-- Councils with fewer than min_council_listings priced entire homes are left out.
WITH market AS (SELECT median(price) AS m FROM priced_homes),
by_size AS (SELECT bed_band, median(price) AS size_median FROM priced_homes GROUP BY bed_band),
c AS (
    SELECT lga,
           count(*)                                         AS listings,
           median(price)                                    AS price_median,
           median(bedrooms)                                 AS median_bedrooms,
           100.0 * count(*) FILTER (WHERE bed_band <= 1) / count(*) AS small_pct,
           median(price / size_median)                      AS same_size_index,
           count(*) FILTER (WHERE bed_band = 2)             AS two_bed_listings,
           median(price) FILTER (WHERE bed_band = 2)        AS two_bed_median
    FROM priced_homes JOIN by_size USING (bed_band)
    GROUP BY lga
    HAVING count(*) >= getvariable('min_council_listings')
)
SELECT lga, listings,
       CAST(round(price_median, 0) AS INTEGER)                                      AS price_median,
       median_bedrooms,
       round(small_pct, 1)                                                          AS studio_or_1bed_pct,
       round(100 * (price_median / (SELECT m FROM market) - 1), 1)                  AS raw_vs_market_pct,
       round(100 * (same_size_index - 1), 1)                                        AS same_size_vs_market_pct,
       CAST(rank() OVER (ORDER BY price_median DESC) AS INTEGER)                    AS raw_rank,
       CAST(rank() OVER (ORDER BY same_size_index DESC) AS INTEGER)                 AS same_size_rank,
       two_bed_listings,
       CAST(round(two_bed_median, 0) AS INTEGER)                                    AS two_bed_median
FROM c
ORDER BY same_size_index DESC, lga;
