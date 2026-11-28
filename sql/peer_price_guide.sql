-- A price guide for a property manager: quoted nightly price of active entire homes by
-- council and bedrooms, for every peer group large enough to be scored (min_peers).
SELECT lga,
       CASE bed_band WHEN 0 THEN 'Studio' WHEN 1 THEN '1 bedroom' WHEN 5 THEN '5+ bedrooms'
                     ELSE bed_band || ' bedrooms' END                    AS size,
       bed_band,
       count(*)                                                          AS listings,
       CAST(round(quantile_cont(price, 0.25), 0) AS INTEGER)             AS price_p25,
       CAST(round(median(price), 0) AS INTEGER)                          AS price_median,
       CAST(round(quantile_cont(price, 0.75), 0) AS INTEGER)             AS price_p75
FROM priced_homes
GROUP BY lga, bed_band
HAVING count(*) >= getvariable('min_peers')
ORDER BY lga, bed_band;
