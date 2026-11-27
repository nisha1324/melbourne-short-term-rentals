-- How long a stay active listings require. 28 nights or more is in effect a
-- medium-term rental rather than a holiday let. A few listings give no minimum.
WITH b AS (
    SELECT room_type,
           CASE WHEN minimum_nights = 1 THEN 1 WHEN minimum_nights = 2 THEN 2
                WHEN minimum_nights <= 6 THEN 3 WHEN minimum_nights <= 27 THEN 4
                WHEN minimum_nights >= 28 THEN 5 ELSE 6 END AS bucket
    FROM active
)
SELECT bucket,
       ['1 night', '2 nights', '3-6 nights', '7-27 nights', '28+ nights', 'not given'][bucket] AS minimum_stay,
       count(*) AS active_listings,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS share_pct,
       count(*) FILTER (WHERE room_type = 'Entire home/apt') AS entire_homes
FROM b
GROUP BY bucket
ORDER BY bucket;
