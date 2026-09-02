-- 0005_agent_runs_trusted.sql
-- Marks orb runs made by the operator (request carried the demo write
-- token). The Dashboard feed shows the raw prompt only for trusted runs;
-- anonymous visitors' prompts are replaced with a generated label so one
-- visitor cannot put arbitrary text in front of the next.

ALTER TABLE agent_runs
    ADD COLUMN trusted TINYINT(1) NOT NULL DEFAULT 0 AFTER error_count;
