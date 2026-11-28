-- What listings look like by the size of the host that runs them.
--   vs_peers_pct / far_above_pct / open_30_median: priced entire homes in a scored peer
--   group (Part 2), i.e. median of price / peer median - 1, the share 50%+ above peers,
--   and open nights in the next 30 days.
--   superhost_pct and median_councils are per host; everything else is per listing.
WITH by_listing AS (
    SELECT host_band,
           count(*)                                                            AS active_listings,
           round(100.0 * count(*) / sum(count(*)) OVER (), 1)                  AS share_of_listings_pct,
           round(100.0 * count(*) FILTER (WHERE is_entire) / count(*), 1)      AS entire_pct,
           median(bedrooms) FILTER (WHERE is_entire)                           AS entire_median_bedrooms,
           CAST(round(median(price) FILTER (WHERE is_entire), 0) AS INTEGER)   AS entire_price_median,
           round(100 * (median(ratio) - 1), 1)                                 AS vs_peers_pct,
           round(100.0 * count(*) FILTER (WHERE ratio >= 1.5) / nullif(count(ratio), 0), 1) AS far_above_pct,
           median(open_30) FILTER (WHERE ratio IS NOT NULL)                    AS open_30_median,
           median(number_of_reviews_ltm)                                       AS reviews_ltm_median,
           round(median(review_scores_rating), 2)                              AS rating_median,
           median(minimum_nights)                                              AS min_nights_median,
           round(100.0 * count(*) FILTER (WHERE minimum_nights >= 28) / count(*), 1) AS min_28_pct
    FROM host_listings GROUP BY host_band
), by_host AS (
    SELECT host_band, count(*) AS hosts,
           round(100.0 * count(*) FILTER (WHERE superhost) / count(*), 1)      AS superhost_pct,
           median(councils)                                                    AS median_councils
    FROM hosts GROUP BY host_band
)
SELECT host_band AS band,
       ['1 listing', '2-4 listings', '5-9 listings', '10-49 listings', '50+ listings'][host_band] AS host_size,
       h.hosts, l.*  EXCLUDE (host_band), h.superhost_pct, h.median_councils
FROM by_listing l JOIN by_host h USING (host_band)
ORDER BY band;
