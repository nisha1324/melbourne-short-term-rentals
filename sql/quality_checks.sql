-- Each check: what was found and what a clean file would give (expected is
-- empty for counts reported for information only). A mismatch does not stop
-- the build; it is reported, and the profile says how it is handled.
WITH cal AS (
    SELECT listing_id, count(*) AS days, count(*) FILTER (WHERE available) AS open_days,
           min(date) AS first_day, max(date) AS last_day
    FROM calendar GROUP BY listing_id
), rev AS (
    SELECT r.listing_id, count(*) AS n, min(r.date) AS first_date, max(r.date) AS last_date,
           count(*) FILTER (WHERE r.date >= l.last_scraped - INTERVAL 365 DAY) AS n_ltm
    FROM reviews r JOIN listings l USING (listing_id)
    GROUP BY r.listing_id
), hosts AS (
    SELECT host_id, count(*) AS n FROM listings GROUP BY host_id
), joined AS (
    SELECT l.*, cal.days, cal.open_days, rev.n AS rev_n, rev.first_date, rev.last_date, rev.n_ltm, hosts.n AS host_n
    FROM listings l
    LEFT JOIN cal USING (listing_id)
    LEFT JOIN rev USING (listing_id)
    LEFT JOIN hosts USING (host_id)
)
SELECT * FROM (
    SELECT 1 AS check_no, 'Duplicate listing ids' AS check_name,
           (SELECT count(*) - count(DISTINCT listing_id) FROM listings) AS found, 0 AS expected
    UNION ALL SELECT 2, 'Listings outside the 30 councils in the boundary file',
           (SELECT count(*) FROM listings WHERE lga IS NULL OR lga NOT IN (SELECT lga FROM lgas)), 0
    UNION ALL SELECT 3, 'Councils with no listing', (SELECT count(*) FROM lgas WHERE lga NOT IN (SELECT lga FROM listings)), 0
    UNION ALL SELECT 4, 'Prices that do not parse as a number',
           (SELECT count(*) FROM listings WHERE price_text IS NOT NULL AND price IS NULL), 0
    UNION ALL SELECT 5, 'Price differs from the quoted total / nights',
           (SELECT count(*) FROM listings WHERE price IS NOT NULL
              AND abs(price - quote_total / date_diff('day', quote_checkin, quote_checkout)) > 0.01), 0
    UNION ALL SELECT 6, 'Price quoted for a check-in before the scrape date',
           (SELECT count(*) FROM listings WHERE quote_checkin < last_scraped), 0
    UNION ALL SELECT 7, 'Listings with no calendar', (SELECT count(*) FROM joined WHERE days IS NULL), 0
    UNION ALL SELECT 8, 'Calendar rows for listings not in the snapshot',
           (SELECT count(*) FROM calendar WHERE listing_id NOT IN (SELECT listing_id FROM listings)), 0
    UNION ALL SELECT 9, 'Listings whose calendar is not exactly 365 days', (SELECT count(*) FROM joined WHERE days <> 365), 0
    UNION ALL SELECT 10, 'availability_365 differs from the open days in the calendar',
           (SELECT count(*) FROM joined WHERE availability_365 <> open_days), 0
    UNION ALL SELECT 11, 'Reviews for listings not in the snapshot',
           (SELECT count(*) FROM reviews WHERE listing_id NOT IN (SELECT listing_id FROM listings)), 0
    UNION ALL SELECT 12, 'number_of_reviews differs from the review file',
           (SELECT count(*) FROM joined WHERE number_of_reviews <> coalesce(rev_n, 0)), 0
    UNION ALL SELECT 13, 'first_review or last_review differs from the review file',
           (SELECT count(*) FROM joined WHERE first_review IS DISTINCT FROM first_date OR last_review IS DISTINCT FROM last_date), 0
    UNION ALL SELECT 14, 'number_of_reviews_ltm differs from reviews in the 365 days to the scrape',
           (SELECT count(*) FROM joined WHERE number_of_reviews_ltm <> coalesce(n_ltm, 0)), 0
    UNION ALL SELECT 15, 'Host listing count differs from a count by host_id',
           (SELECT count(*) FROM joined WHERE host_listings_in_snapshot <> host_n), 0
    UNION ALL SELECT 16, 'Reviews dated after the scrape',
           (SELECT count(*) FROM reviews r JOIN listings l USING (listing_id) WHERE r.date > l.last_scraped), 0
    UNION ALL SELECT 17, 'Listings with no quoted price', (SELECT count(*) FROM listings WHERE price IS NULL), NULL::INTEGER
    UNION ALL SELECT 18, 'Quoted price under $20 a night', (SELECT count(*) FROM listings WHERE price < 20), NULL::INTEGER
    UNION ALL SELECT 19, 'Quoted price of $2,000 a night or more', (SELECT count(*) FROM listings WHERE price >= 2000), NULL::INTEGER
    UNION ALL SELECT 20, 'Listings with a licence or registration number', (SELECT count(*) FROM listings WHERE licence IS NOT NULL), NULL::INTEGER
)
ORDER BY check_no;
