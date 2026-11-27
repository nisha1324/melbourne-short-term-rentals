-- Quoted nightly price of active listings in bands, for entire homes and private rooms.
WITH banded AS (
    SELECT room_type,
           CASE WHEN price < 100 THEN 1 WHEN price < 150 THEN 2 WHEN price < 200 THEN 3
                WHEN price < 300 THEN 4 WHEN price < 500 THEN 5 WHEN price < 1000 THEN 6
                WHEN price < 2000 THEN 7 ELSE 8 END AS band
    FROM active
    WHERE price IS NOT NULL AND room_type IN ('Entire home/apt', 'Private room')
)
SELECT room_type, band,
       ['under $100', '$100-149', '$150-199', '$200-299', '$300-499', '$500-999', '$1,000-1,999', '$2,000+'][band] AS price_band,
       count(*) AS listings,
       round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY room_type), 1) AS share_pct
FROM banded
GROUP BY room_type, band
ORDER BY room_type, band;
