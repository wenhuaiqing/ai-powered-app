-- 0002_listings.sql
-- Active listings (for-sale / for-lease snapshots). A listing references the
-- canonical property row + the agent who owns it. Status + stage progress
-- here via UPDATEs from the Properties drawer + the Listing Drafter agent.

CREATE TABLE IF NOT EXISTS listings (
    listing_id       VARCHAR(16) PRIMARY KEY,
    property_id      VARCHAR(16) NOT NULL,
    status           ENUM('For Sale','For Lease') NOT NULL,
    stage            ENUM('New','Listed','Under Offer','Sold','Withdrawn') NOT NULL DEFAULT 'New',
    asking_price     DECIMAL(12,2),
    listed_date      DATE NOT NULL,
    days_on_market   INT,
    agent_id         VARCHAR(16),
    headline         VARCHAR(255),
    body_markdown    MEDIUMTEXT,
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_listings_property FOREIGN KEY (property_id) REFERENCES properties(property_id) ON DELETE CASCADE,
    CONSTRAINT fk_listings_agent FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE SET NULL,
    INDEX idx_listings_status (status),
    INDEX idx_listings_stage (stage),
    INDEX idx_listings_listed_date (listed_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
