-- The "active" market used from here on: listings with at least one review in
-- the 365 days up to their scrape date (number_of_reviews_ltm > 0, which the
-- quality checks confirm against the review file). A temporary view, so every later
-- query starts from the same definition.
CREATE OR REPLACE TEMP VIEW active AS
SELECT *
FROM listings
WHERE number_of_reviews_ltm > 0;
