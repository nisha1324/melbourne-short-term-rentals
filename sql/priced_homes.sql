-- Part 2 base view: active entire homes with a quoted price and a bedroom count,
-- each compared with its peers (same council, same bedrooms, 5+ grouped).
-- Runs after sql/active_listings.sql. Thresholds come from DuckDB variables set
-- in str_market/pricing.py: min_peers (smallest peer group that is scored).
--
--   ratio       = price / median price of the listing's peer group (the group includes
--                 the listing itself), NULL when the group has fewer than min_peers listings
--   stay_nights = nights in the quoted stay (price = quote total / nights)
--   lead_days   = days from the scrape to the quoted check-in
--   open_30/90  = open nights in the calendar's first 30/90 days from the scrape
--   gf_weekend  = the quoted stay includes the night of Fri 25 or Sat 26 Sep 2026
--                 (Grand Final eve public holiday and AFL Grand Final day)
--   has_weekend = the quoted stay includes a Friday or Saturday night
CREATE OR REPLACE TEMP VIEW priced_homes AS
WITH homes AS (
    SELECT *,
           least(bedrooms, 5)                                   AS bed_band,
           date_diff('day', quote_checkin, quote_checkout)      AS stay_nights,
           date_diff('day', last_scraped, quote_checkin)        AS lead_days
    FROM active
    WHERE room_type = 'Entire home/apt' AND price IS NOT NULL AND bedrooms IS NOT NULL
),
peers AS (
    SELECT lga, bed_band, median(price) AS peer_median, count(*) AS peer_n
    FROM homes GROUP BY lga, bed_band
),
open_nights AS (
    SELECT c.listing_id,
           count(*) FILTER (WHERE c.available AND c.date < h.last_scraped + 30) AS open_30,
           count(*) FILTER (WHERE c.available AND c.date < h.last_scraped + 90) AS open_90
    FROM calendar c JOIN homes h USING (listing_id)
    WHERE c.date >= h.last_scraped
    GROUP BY c.listing_id
),
nights AS (
    -- the nights of each quoted stay, to test whether they include a weekend
    SELECT listing_id, unnest(generate_series(quote_checkin, quote_checkout - 1, INTERVAL 1 DAY))::DATE AS night
    FROM homes WHERE stay_nights BETWEEN 1 AND 28
),
stay_flags AS (
    SELECT listing_id,
           bool_or(night IN (DATE '2026-09-25', DATE '2026-09-26')) AS gf_weekend,
           bool_or(dayofweek(night) IN (5, 6))                      AS has_weekend
    FROM nights GROUP BY listing_id
)
SELECT h.*, p.peer_median, p.peer_n,
       CASE WHEN p.peer_n >= getvariable('min_peers') THEN h.price / p.peer_median END AS ratio,
       coalesce(o.open_30, 0) AS open_30, coalesce(o.open_90, 0) AS open_90,
       s.gf_weekend, s.has_weekend
FROM homes h
JOIN peers p USING (lga, bed_band)
LEFT JOIN open_nights o USING (listing_id)
LEFT JOIN stay_flags s USING (listing_id);
