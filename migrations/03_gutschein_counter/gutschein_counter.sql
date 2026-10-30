-- ============================================================
-- Migration: Voucher number counter
-- ============================================================
-- Creates the single-row counter the API uses to assign `gutschein_nr`.
-- Voucher creation reads it with `SELECT ... FOR UPDATE`, so concurrent cash
-- registers cannot pick the same number. The row is seeded from the highest
-- existing voucher number (legacy paper vouchers are below 200, the first
-- API/Java POS voucher is 200).
--
-- Run as kassenadmin (full privileges). Back up first.

CREATE TABLE IF NOT EXISTS `gutschein_counter` (
    id TINYINT NOT NULL PRIMARY KEY,
    last_nr INT UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

INSERT INTO `gutschein_counter` (id, last_nr)
SELECT 1, GREATEST(IFNULL(MAX(gutschein_nr), 199), 199)
FROM `gutschein`
ON DUPLICATE KEY UPDATE last_nr = GREATEST(last_nr, VALUES(last_nr));

-- Only needed if the API runs as `mitarbeiter` instead of `kassenadmin`.
GRANT SELECT, INSERT, UPDATE ON kasse.gutschein_counter TO 'mitarbeiter'@'localhost';
GRANT SELECT, INSERT, UPDATE ON kasse.gutschein_counter TO 'mitarbeiter'@'192.168.2.%';
