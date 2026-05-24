-- 0004_property_ml_features.sql
-- Add the ML feature columns that the trained RandomForest expects.
-- These come straight from the Domain CSV and are read by:
--   backend/src/app/services/model.py::_baselines()
--   the Valuation agent + /api/valuations/predict
-- Restored here (after 0001_initial) so the ETL into DuckDB keeps the
-- columns the model was trained on.

ALTER TABLE properties
    ADD COLUMN suburb_population        INT          NULL AFTER property_size,
    ADD COLUMN suburb_median_income     DECIMAL(12,2) NULL AFTER suburb_population,
    ADD COLUMN suburb_sqkm              DECIMAL(8,3) NULL AFTER suburb_median_income,
    ADD COLUMN suburb_elevation         DECIMAL(8,2) NULL AFTER suburb_sqkm,
    ADD COLUMN cash_rate                DECIMAL(6,3) NULL AFTER suburb_elevation,
    ADD COLUMN property_inflation_index DECIMAL(8,3) NULL AFTER cash_rate;
