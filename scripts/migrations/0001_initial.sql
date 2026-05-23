-- 0001_initial.sql
-- Core OLTP tables: properties (sales reference), suburbs, agents, leads.
-- Source of truth — the pipeline (scripts/etl_mysql_to_duckdb.py)
-- denormalises these into DuckDB for analytics + agent text-to-SQL.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(64) PRIMARY KEY,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS agents (
    agent_id      VARCHAR(16) PRIMARY KEY,
    name          VARCHAR(120) NOT NULL,
    email         VARCHAR(180),
    INDEX idx_agents_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS suburbs (
    suburb_id                 INT AUTO_INCREMENT PRIMARY KEY,
    name                      VARCHAR(120) NOT NULL,
    region                    VARCHAR(120),
    population                INT,
    postcode                  INT,
    median_house_price_2020   DECIMAL(12,2),
    median_house_price_2021   DECIMAL(12,2),
    pct_change                DECIMAL(6,3),
    median_house_rent_pw      DECIMAL(8,2),
    median_apt_price_2020     DECIMAL(12,2),
    median_apt_rent_pw        DECIMAL(8,2),
    public_housing_pct        DECIMAL(6,3),
    avg_years_held            DECIMAL(5,2),
    time_to_cbd_pt_min        DECIMAL(5,2),
    time_to_cbd_drive_min     DECIMAL(5,2),
    nearest_train_station     VARCHAR(180),
    highlights                TEXT,
    ideal_for                 TEXT,
    traffic                   DECIMAL(4,2),
    public_transport          DECIMAL(4,2),
    affordability_rental      DECIMAL(4,2),
    affordability_buying      DECIMAL(4,2),
    nature                    DECIMAL(4,2),
    noise                     DECIMAL(4,2),
    things_to_see_do          TEXT,
    family_friendliness       DECIMAL(4,2),
    pet_friendliness          DECIMAL(4,2),
    safety                    DECIMAL(4,2),
    overall_rating            DECIMAL(4,2),
    review_link               VARCHAR(500),
    UNIQUE KEY uq_suburbs_name (name),
    INDEX idx_suburbs_region (region)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS properties (
    property_id      VARCHAR(16) PRIMARY KEY,
    suburb           VARCHAR(120) NOT NULL,
    postcode         INT,
    price            DECIMAL(12,2) NOT NULL,
    property_type    VARCHAR(60),
    num_bed          INT,
    num_bath         INT,
    num_parking      INT,
    property_size    DECIMAL(10,2),
    km_from_cbd      DECIMAL(6,2),
    suburb_lat       DECIMAL(9,6),
    suburb_lng       DECIMAL(9,6),
    date_sold        DATE,
    INDEX idx_properties_suburb (suburb),
    INDEX idx_properties_date_sold (date_sold)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS leads (
    lead_id            VARCHAR(16) PRIMARY KEY,
    name               VARCHAR(180) NOT NULL,
    email              VARCHAR(180),
    phone              VARCHAR(40),
    intent             ENUM('Buying','Renting','Selling appraisal') NOT NULL,
    status             ENUM('New','Contacted','Qualified','Viewed','Offered','Closed Won','Closed Lost') NOT NULL DEFAULT 'New',
    min_bed            INT,
    min_bath           INT,
    min_parking        INT,
    preferred_suburb   VARCHAR(120),
    max_km_from_cbd    INT,
    budget_min         DECIMAL(12,2),
    budget_max         DECIMAL(12,2),
    urgency            ENUM('low','medium','high') NOT NULL DEFAULT 'medium',
    notes              TEXT,
    assigned_agent_id  VARCHAR(16),
    created_date       DATE NOT NULL,
    created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_leads_agent FOREIGN KEY (assigned_agent_id) REFERENCES agents(agent_id) ON DELETE SET NULL,
    INDEX idx_leads_status (status),
    INDEX idx_leads_urgency (urgency),
    INDEX idx_leads_created (created_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Append-only audit log of lead status transitions.
CREATE TABLE IF NOT EXISTS lead_events (
    event_id     BIGINT AUTO_INCREMENT PRIMARY KEY,
    lead_id      VARCHAR(16) NOT NULL,
    event_type   VARCHAR(40) NOT NULL,
    from_status  VARCHAR(40),
    to_status    VARCHAR(40),
    note         TEXT,
    actor        VARCHAR(120),
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_lead_events_lead FOREIGN KEY (lead_id) REFERENCES leads(lead_id) ON DELETE CASCADE,
    INDEX idx_lead_events_lead (lead_id),
    INDEX idx_lead_events_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
