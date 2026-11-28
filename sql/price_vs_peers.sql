-- Listings by how far their price sits from their peers' median, with demand signals.
-- reviews_ltm: reviews in the 12 months to the scrape (each needs a completed stay);
-- open_30: open nights in the next 30 days (fewer = booked or blocked).
SELECT CASE WHEN ratio < 1 / 1.5 THEN 1 WHEN ratio < 0.9 THEN 2 WHEN ratio <= 1 / 0.9 THEN 3
            WHEN ratio < 1.5 THEN 4 ELSE 5 END                                      AS band,
       ['A third or more below', '10-33% below', 'Within 10%', '11-49% above', '50% or more above'][band] AS price_vs_peers,
       count(*)                                                                     AS listings,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)                           AS share_pct,
       CAST(round(median(price), 0) AS INTEGER)                                     AS price_median,
       median(accommodates)                                                         AS median_guests,
       median(number_of_reviews_ltm)                                                AS reviews_ltm_median,
       round(avg(number_of_reviews_ltm), 1)                                         AS reviews_ltm_mean,
       median(open_30)                                                              AS open_30_median,
       median(open_90)                                                              AS open_90_median,
       round(median(review_scores_rating), 2)                                       AS rating_median
FROM priced_homes
WHERE ratio IS NOT NULL
GROUP BY band
ORDER BY band;
