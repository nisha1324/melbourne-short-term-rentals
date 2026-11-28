-- Part 3 base views. Runs after sql/active_listings.sql and sql/priced_homes.sql.
--
-- A host's size is the number of ACTIVE listings it runs anywhere in the 30 councils,
-- counted from host_id (not Inside Airbnb's calculated_host_listings_count, which also
-- counts dormant listings). A "host" is one Airbnb account: a management company may
-- run several accounts, and one account may manage homes for many owners.
--
-- Bands as in Part 1: 1, 2-4, 5-9, 10-49, 50+ listings; "operators" are bands 4-5 (10 or more).
--
--   host_listings: one row per active listing, with its host's size and band and,
--                  for priced entire homes in a scored peer group, Part 2's price ratio
--   hosts:         one row per host (never written to results/; only aggregated)
CREATE OR REPLACE TEMP VIEW host_listings AS
WITH sizes AS (
    SELECT host_id, count(*) AS host_n FROM active GROUP BY host_id
)
SELECT a.listing_id, a.host_id, a.lga, a.room_type, a.price, a.bedrooms, a.minimum_nights,
       a.number_of_reviews_ltm, a.review_scores_rating, a.host_is_superhost,
       s.host_n,
       CASE WHEN s.host_n = 1 THEN 1 WHEN s.host_n <= 4 THEN 2 WHEN s.host_n <= 9 THEN 3
            WHEN s.host_n <= 49 THEN 4 ELSE 5 END                       AS host_band,
       a.room_type = 'Entire home/apt'                                   AS is_entire,
       p.ratio, p.open_30
FROM active a
JOIN sizes s USING (host_id)
LEFT JOIN priced_homes p USING (listing_id);

CREATE OR REPLACE TEMP VIEW hosts AS
WITH main_council AS (
    SELECT host_id, max(k) AS in_main_council
    FROM (SELECT host_id, lga, count(*) AS k FROM host_listings GROUP BY host_id, lga)
    GROUP BY host_id
)
SELECT h.host_id,
       any_value(h.host_n)                                      AS listings,
       any_value(h.host_band)                                   AS host_band,
       count(*) FILTER (WHERE h.is_entire)                      AS entire_homes,
       count(DISTINCT h.lga)                                    AS councils,
       any_value(m.in_main_council)                             AS in_main_council,
       count(*) FILTER (WHERE h.lga IN ('Melbourne', 'Port Phillip', 'Yarra')) AS in_inner3,
       bool_or(h.host_is_superhost)                             AS superhost,
       median(h.ratio)                                          AS median_ratio
FROM host_listings h
JOIN main_council m USING (host_id)
GROUP BY h.host_id;
