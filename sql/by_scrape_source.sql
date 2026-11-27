-- Listings carried over from an earlier scrape look very different from the rest.
SELECT
    scrape_source,
    count(*)                                                          AS listings,
    count(*) FILTER (WHERE price IS NOT NULL)                         AS with_price,
    count(*) FILTER (WHERE availability_365 = 0)                      AS no_open_nights,
    count(*) FILTER (WHERE number_of_reviews_ltm > 0)                 AS reviewed_last_12m,
    count(*) FILTER (WHERE number_of_reviews = 0)                     AS never_reviewed,
    quantile_disc(last_review, 0.5)                                   AS median_last_review
FROM listings
GROUP BY scrape_source
ORDER BY listings DESC;
