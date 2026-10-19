-- ============================================================
-- Migration: User accounts, login auditing, transaction attribution
-- (Phase 7.4)
-- ============================================================
--
-- Run as kassenadmin (full privileges). Idempotent-ish: uses
-- CREATE TABLE IF NOT EXISTS and ADD COLUMN with a guard via
-- INFORMATION_SCHEMA checks is NOT done here; re-running will error
-- on duplicate columns. Back up first.
--
-- Bootstrapped admin user: username='admin', password='changeme'
-- (bcrypt hash). CHANGE THIS PASSWORD IMMEDIATELY after first login.

CREATE TABLE IF NOT EXISTS `user` (
    user_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'mitarbeiter',
    active TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `anmeldung` (
    anmeldung_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    login_time TIMESTAMP NOT NULL,
    logout_time TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES `user`(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Transaction attribution: nullable user_id FK on transaction tables.
ALTER TABLE verkauf ADD COLUMN user_id INT NULL;
ALTER TABLE verkauf ADD CONSTRAINT fk_verkauf_user FOREIGN KEY (user_id) REFERENCES `user`(user_id);

ALTER TABLE kassenstand ADD COLUMN user_id INT NULL;
ALTER TABLE kassenstand ADD CONSTRAINT fk_kassenstand_user FOREIGN KEY (user_id) REFERENCES `user`(user_id);

ALTER TABLE anzahlung ADD COLUMN user_id INT NULL;
ALTER TABLE anzahlung ADD CONSTRAINT fk_anzahlung_user FOREIGN KEY (user_id) REFERENCES `user`(user_id);

ALTER TABLE gutschein ADD COLUMN user_id INT NULL;
ALTER TABLE gutschein ADD CONSTRAINT fk_gutschein_user FOREIGN KEY (user_id) REFERENCES `user`(user_id);

ALTER TABLE zaehlprotokoll ADD COLUMN user_id INT NULL;
ALTER TABLE zaehlprotokoll ADD CONSTRAINT fk_zaehlprotokoll_user FOREIGN KEY (user_id) REFERENCES `user`(user_id);

ALTER TABLE abrechnung_tag ADD COLUMN user_id INT NULL;
ALTER TABLE abrechnung_tag ADD CONSTRAINT fk_abrechnung_tag_user FOREIGN KEY (user_id) REFERENCES `user`(user_id);

ALTER TABLE bestellung ADD COLUMN user_id INT NULL;
ALTER TABLE bestellung ADD CONSTRAINT fk_bestellung_user FOREIGN KEY (user_id) REFERENCES `user`(user_id);

ALTER TABLE tse_transaction ADD COLUMN user_id INT NULL;
ALTER TABLE tse_transaction ADD CONSTRAINT fk_tse_transaction_user FOREIGN KEY (user_id) REFERENCES `user`(user_id);

-- Bootstrap admin user (password: changeme)
INSERT INTO `user` (username, password_hash, role, active)
SELECT 'admin', '$2b$12$0Hm8ZRJY/DoPvFihPWckBOsAhqUzP.t8RFJeZFnC5Xq1ogtZI7rYK', 'admin', 1
WHERE NOT EXISTS (SELECT 1 FROM `user` WHERE username = 'admin');