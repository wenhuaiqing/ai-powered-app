-- 0003_agent_runs.sql
-- Persisted record of every orb invocation. Powers the Dashboard "Recent
-- agent activity" feed and is the foundation for the eval pipeline that
-- wants to replay real prompts against new model versions.

CREATE TABLE IF NOT EXISTS agent_runs (
    run_id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_message     TEXT NOT NULL,
    page_module      VARCHAR(60),
    agents_called    JSON NOT NULL,
    final_message    MEDIUMTEXT,
    used_web_search  TINYINT(1) NOT NULL DEFAULT 0,
    error_count      INT NOT NULL DEFAULT 0,
    duration_ms      INT,
    related_lead_id  VARCHAR(16),
    related_listing_id VARCHAR(16),
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_agent_runs_lead FOREIGN KEY (related_lead_id) REFERENCES leads(lead_id) ON DELETE SET NULL,
    CONSTRAINT fk_agent_runs_listing FOREIGN KEY (related_listing_id) REFERENCES listings(listing_id) ON DELETE SET NULL,
    INDEX idx_agent_runs_created (created_at DESC),
    INDEX idx_agent_runs_module (page_module)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
