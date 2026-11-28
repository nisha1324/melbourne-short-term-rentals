-- For each of the first eight weekends after the scrape: the share of scored entire homes
-- with the Friday or the Saturday night still open in the calendar (the rest are booked
-- or blocked by the host; the calendar cannot tell which).
WITH weekends AS (
    SELECT d::DATE AS friday FROM generate_series(DATE '2026-09-18', DATE '2026-11-06', INTERVAL 7 DAY) t(d)
),
scored AS (SELECT listing_id FROM priced_homes WHERE ratio IS NOT NULL)
SELECT w.friday,
       count(DISTINCT c.listing_id) FILTER (WHERE c.available)                           AS open_listings,
       (SELECT count(*) FROM scored)                                                     AS scored_listings,
       round(100.0 * count(DISTINCT c.listing_id) FILTER (WHERE c.available)
             / (SELECT count(*) FROM scored), 1)                                         AS open_pct
FROM weekends w
JOIN calendar c ON c.date IN (w.friday, w.friday + 1)
JOIN scored USING (listing_id)
GROUP BY w.friday
ORDER BY w.friday;
