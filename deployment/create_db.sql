-- ============================================================
-- wlkserver: create the MariaDB database from scratch
-- ============================================================
-- Base schema: ../git/mysql/generateDB.sql (Java POS schema)
-- plus migrations/01..05 already applied:
--   * all datetimes are TIMESTAMP (UTC)
--   * user accounts, login log and `user_id` attribution columns
--   * voucher number counter
--   * art.bio / art.vegan
--   * no legacy `training_*` tables (training uses `kasse_training`)
--
-- WARNING: drops and recreates the databases `kasse` and `kasse_training`!
--
-- Run as MariaDB root, e.g.:  sudo mariadb < deployment/create_db.sql

DROP DATABASE IF EXISTS kasse;
CREATE DATABASE kasse CHARACTER SET utf8 COLLATE utf8_general_ci;
USE kasse;

CREATE TABLE `user` (
    user_id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    full_name VARCHAR(50) DEFAULT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'mitarbeiter', -- admin | mitarbeiter
    pref_theme VARCHAR(20) DEFAULT NULL,             -- light | dark
    active BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE anmeldung (
    anmeldung_id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id INTEGER(10) UNSIGNED NOT NULL,
    login_time TIMESTAMP NOT NULL,
    logout_time TIMESTAMP NULL DEFAULT NULL,
    PRIMARY KEY (anmeldung_id),
    FOREIGN KEY (user_id) REFERENCES `user`(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE lieferant (
    lieferant_id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    lieferant_name VARCHAR(50) NOT NULL,
    lieferant_kurzname VARCHAR(10) DEFAULT NULL,
    n_artikel INTEGER(10) UNSIGNED DEFAULT NULL,
    aktiv BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (lieferant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE mwst (
    mwst_id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    mwst_satz DECIMAL(6,5) NOT NULL,
    dsfinvk_ust_schluessel INTEGER(10) UNSIGNED NOT NULL,
    dsfinvk_ust_beschr VARCHAR(55) DEFAULT NULL,
    PRIMARY KEY (mwst_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE pfand (
    pfand_id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    artikel_id INTEGER(10) UNSIGNED NOT NULL,
    PRIMARY KEY (pfand_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE produktgruppe (
    produktgruppen_id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    toplevel_id INTEGER(10) UNSIGNED DEFAULT 1,
    sub_id INTEGER(10) UNSIGNED DEFAULT NULL,
    subsub_id INTEGER(10) UNSIGNED DEFAULT NULL,
    produktgruppen_name VARCHAR(50) NOT NULL,
    mwst_id INTEGER(10) UNSIGNED DEFAULT NULL,
    pfand_id INTEGER(10) UNSIGNED DEFAULT NULL,
    std_einheit VARCHAR(10) DEFAULT NULL,
    n_artikel INTEGER(10) UNSIGNED DEFAULT NULL,
    n_artikel_rekursiv INTEGER(10) UNSIGNED DEFAULT NULL,
    aktiv BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (produktgruppen_id),
    FOREIGN KEY (mwst_id) REFERENCES mwst(mwst_id),
    FOREIGN KEY (pfand_id) REFERENCES pfand(pfand_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE artikel (
    artikel_id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    produktgruppen_id INTEGER(10) UNSIGNED NOT NULL DEFAULT 8,
    lieferant_id INTEGER(10) UNSIGNED NOT NULL DEFAULT 1,
    artikel_nr VARCHAR(30) NOT NULL,
    artikel_name VARCHAR(180) NOT NULL,
    kurzname VARCHAR(50) DEFAULT NULL,
    menge DECIMAL(8,5) DEFAULT NULL,
    einheit VARCHAR(10) DEFAULT NULL,
    barcode VARCHAR(30) DEFAULT NULL,
    herkunft VARCHAR(100) DEFAULT NULL,
    vpe SMALLINT(5) UNSIGNED DEFAULT NULL,
    setgroesse SMALLINT(5) UNSIGNED NOT NULL DEFAULT 1,
    vk_preis DECIMAL(13,2) DEFAULT NULL,
    empf_vk_preis DECIMAL(13,2) DEFAULT NULL,
    ek_rabatt DECIMAL(6,5) DEFAULT NULL,
    ek_preis DECIMAL(13,2) DEFAULT NULL,
    variabler_preis BOOLEAN NOT NULL DEFAULT FALSE,
    sortiment BOOLEAN NOT NULL DEFAULT FALSE,
    lieferbar BOOLEAN NOT NULL DEFAULT FALSE,
    beliebtheit TINYINT(1) NOT NULL DEFAULT 0,
    bestand SMALLINT(5) DEFAULT NULL,
    von TIMESTAMP DEFAULT NULL,
    bis TIMESTAMP DEFAULT NULL,
    aktiv BOOLEAN NOT NULL DEFAULT TRUE,
    bio BOOLEAN DEFAULT NULL,
    vegan BOOLEAN DEFAULT NULL,
    PRIMARY KEY (artikel_id),
    FOREIGN KEY (lieferant_id) REFERENCES lieferant(lieferant_id),
    FOREIGN KEY (produktgruppen_id) REFERENCES produktgruppe(produktgruppen_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
ALTER TABLE pfand ADD FOREIGN KEY (artikel_id) REFERENCES artikel(artikel_id);

CREATE TABLE rabattaktion (
    rabatt_id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    aktionsname VARCHAR(50) DEFAULT NULL,
    rabatt_relativ DECIMAL(6,5) DEFAULT NULL,
    rabatt_absolut DECIMAL(13,2) DEFAULT NULL,
    mengenrabatt_schwelle INTEGER(10) UNSIGNED DEFAULT NULL,
    mengenrabatt_anzahl_kostenlos INTEGER(10) UNSIGNED DEFAULT NULL,
    mengenrabatt_relativ DECIMAL(6,5) DEFAULT NULL,
    von TIMESTAMP NOT NULL,
    bis TIMESTAMP,
    produktgruppen_id INTEGER(10) UNSIGNED DEFAULT NULL,
    artikel_id INTEGER(10) UNSIGNED DEFAULT NULL,
    PRIMARY KEY (rabatt_id),
    FOREIGN KEY (produktgruppen_id) REFERENCES produktgruppe(produktgruppen_id),
    FOREIGN KEY (artikel_id) REFERENCES artikel(artikel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE verkauf (
    rechnungs_nr INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    verkaufsdatum TIMESTAMP NOT NULL,
    storno_von INTEGER(10) UNSIGNED DEFAULT NULL,
    ec_zahlung BOOLEAN NOT NULL DEFAULT FALSE,
    kunde_gibt DECIMAL(13,2) DEFAULT NULL,
    user_id INTEGER(10) UNSIGNED DEFAULT NULL,
    PRIMARY KEY (rechnungs_nr),
    FOREIGN KEY (storno_von) REFERENCES verkauf(rechnungs_nr),
    FOREIGN KEY (user_id) REFERENCES `user`(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
CREATE TABLE verkauf_mwst (
    rechnungs_nr INTEGER(10) UNSIGNED NOT NULL,
    mwst_satz DECIMAL(6,5) NOT NULL,
    mwst_netto DECIMAL(13,2) NOT NULL,
    mwst_betrag DECIMAL(13,2) NOT NULL,
    PRIMARY KEY (rechnungs_nr, mwst_satz),
    FOREIGN KEY (rechnungs_nr) REFERENCES verkauf(rechnungs_nr)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
CREATE TABLE verkauf_details (
    vd_id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    rechnungs_nr INTEGER(10) UNSIGNED NOT NULL,
    position SMALLINT(5) UNSIGNED DEFAULT NULL,
    artikel_id INTEGER(10) UNSIGNED DEFAULT NULL,
    rabatt_id INTEGER(10) UNSIGNED DEFAULT NULL,
    stueckzahl SMALLINT(5) NOT NULL DEFAULT 1,
    ges_preis DECIMAL(13,2) NOT NULL,
    mwst_satz DECIMAL(6,5) NOT NULL,
    PRIMARY KEY (vd_id),
    FOREIGN KEY (rechnungs_nr) REFERENCES verkauf(rechnungs_nr),
    FOREIGN KEY (artikel_id) REFERENCES artikel(artikel_id),
    FOREIGN KEY (rabatt_id) REFERENCES rabattaktion(rabatt_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE kassenstand (
    kassenstand_id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    buchungsdatum TIMESTAMP NOT NULL,
    neuer_kassenstand DECIMAL(13,2) NOT NULL,
    manuell BOOLEAN NOT NULL DEFAULT FALSE,
    entnahme BOOLEAN NOT NULL DEFAULT FALSE,
    rechnungs_nr INTEGER(10) UNSIGNED DEFAULT NULL,
    kommentar VARCHAR(70),
    user_id INTEGER(10) UNSIGNED DEFAULT NULL,
    PRIMARY KEY (kassenstand_id),
    FOREIGN KEY (rechnungs_nr) REFERENCES verkauf(rechnungs_nr),
    FOREIGN KEY (user_id) REFERENCES `user`(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE anzahlung (
    anzahlung_id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    datum TIMESTAMP NOT NULL,
    anzahlung_in_rech_nr INTEGER(10) UNSIGNED NOT NULL,
    aufloesung_in_rech_nr INTEGER(10) UNSIGNED DEFAULT NULL,
    user_id INTEGER(10) UNSIGNED DEFAULT NULL,
    PRIMARY KEY (anzahlung_id),
    FOREIGN KEY (anzahlung_in_rech_nr) REFERENCES verkauf(rechnungs_nr),
    FOREIGN KEY (aufloesung_in_rech_nr) REFERENCES verkauf(rechnungs_nr),
    FOREIGN KEY (user_id) REFERENCES `user`(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
CREATE TABLE anzahlung_details (
    ad_id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    rechnungs_nr INTEGER(10) UNSIGNED NOT NULL,
    vd_id INTEGER(10) UNSIGNED NOT NULL,
    ges_preis DECIMAL(13,2) NOT NULL,
    PRIMARY KEY (ad_id),
    FOREIGN KEY (rechnungs_nr) REFERENCES verkauf_details(rechnungs_nr),
    FOREIGN KEY (vd_id) REFERENCES verkauf_details(vd_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE gutschein (
    gutschein_id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    gutschein_nr INTEGER(10) UNSIGNED NOT NULL,
    datum TIMESTAMP NOT NULL,
    gutschein_in_vd_id INTEGER(10) UNSIGNED DEFAULT NULL,
    einloesung_in_vd_id INTEGER(10) UNSIGNED DEFAULT NULL,
    restbetrag DECIMAL(13,2) NOT NULL,
    user_id INTEGER(10) UNSIGNED DEFAULT NULL,
    PRIMARY KEY (gutschein_id),
    FOREIGN KEY (gutschein_in_vd_id) REFERENCES verkauf_details(vd_id),
    FOREIGN KEY (einloesung_in_vd_id) REFERENCES verkauf_details(vd_id),
    FOREIGN KEY (user_id) REFERENCES `user`(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Single-row counter for `gutschein_nr`; voucher creation locks this row.
CREATE TABLE gutschein_counter (
    id TINYINT NOT NULL,
    last_nr INTEGER(10) UNSIGNED NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- CREATE TABLE abrechnung_tag (
--     id INTEGER(10) UNSIGNED NOT NULL,
--     zeitpunkt TIMESTAMP NOT NULL,
--     zeitpunkt_real TIMESTAMP NOT NULL,
--     mwst_satz DECIMAL(6,5) NOT NULL,
--     mwst_netto DECIMAL(13,2) NOT NULL,
--     mwst_betrag DECIMAL(13,2) NOT NULL,
--     bar_brutto DECIMAL(13,2) NOT NULL,
--     kassenstand_id INTEGER(10) UNSIGNED DEFAULT NULL,
--     PRIMARY KEY (id, mwst_satz),
--     FOREIGN KEY (kassenstand_id) REFERENCES kassenstand(kassenstand_id)
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
CREATE TABLE abrechnung_tag (
    id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    z_kasse_id VARCHAR(30) NOT NULL,
    zeitpunkt TIMESTAMP NOT NULL,
    zeitpunkt_real TIMESTAMP NOT NULL,
    kassenstand_id INTEGER(10) UNSIGNED DEFAULT NULL,
    rechnungs_nr_von INTEGER(10) UNSIGNED NOT NULL,
    rechnungs_nr_bis INTEGER(10) UNSIGNED NOT NULL,
    last_tse_sig_counter INTEGER(10) DEFAULT NULL,
    user_id INTEGER(10) UNSIGNED DEFAULT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (kassenstand_id) REFERENCES kassenstand(kassenstand_id),
    FOREIGN KEY (rechnungs_nr_von) REFERENCES verkauf(rechnungs_nr),
    FOREIGN KEY (rechnungs_nr_bis) REFERENCES verkauf(rechnungs_nr),
    FOREIGN KEY (user_id) REFERENCES `user`(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
CREATE TABLE abrechnung_tag_mwst (
    id INTEGER(10) UNSIGNED NOT NULL,
    mwst_satz DECIMAL(6,5) NOT NULL,
    mwst_netto DECIMAL(13,2) NOT NULL,
    mwst_betrag DECIMAL(13,2) NOT NULL,
    bar_brutto DECIMAL(13,2) NOT NULL,
    PRIMARY KEY (id, mwst_satz)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
CREATE TABLE abrechnung_tag_tse (
    id INTEGER(10) UNSIGNED NOT NULL,
    tse_id INTEGER(10) UNSIGNED DEFAULT NULL,
    tse_serial VARCHAR(68) DEFAULT NULL,
    tse_sig_algo VARCHAR(21) DEFAULT NULL,
    tse_time_format VARCHAR(31) DEFAULT NULL,
    tse_pd_encoding VARCHAR(5) DEFAULT NULL,
    tse_public_key VARCHAR(512) DEFAULT NULL,
    tse_cert_i VARCHAR(1000) DEFAULT NULL,
    tse_cert_ii VARCHAR(1000) DEFAULT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (id) REFERENCES abrechnung_tag(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
CREATE TABLE zaehlprotokoll (
    id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    abrechnung_tag_id INTEGER(10) UNSIGNED NOT NULL,
    zeitpunkt TIMESTAMP NOT NULL,
    kommentar TEXT NOT NULL,
    aktiv BOOLEAN NOT NULL DEFAULT TRUE,
    user_id INTEGER(10) UNSIGNED DEFAULT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (abrechnung_tag_id) REFERENCES abrechnung_tag(id),
    FOREIGN KEY (user_id) REFERENCES `user`(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
CREATE TABLE zaehlprotokoll_details (
    id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    zaehlprotokoll_id INTEGER(10) UNSIGNED NOT NULL,
    anzahl SMALLINT(5) UNSIGNED NOT NULL,
    einheit DECIMAL(13,2) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (zaehlprotokoll_id) REFERENCES zaehlprotokoll(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- CREATE TABLE abrechnung_monat (
--     id INTEGER(10) UNSIGNED NOT NULL,
--     monat DATE NOT NULL,
--     mwst_satz DECIMAL(6,5) NOT NULL,
--     mwst_netto DECIMAL(13,2) NOT NULL,
--     mwst_betrag DECIMAL(13,2) NOT NULL,
--     bar_brutto DECIMAL(13,2) NOT NULL,
--     PRIMARY KEY (id, mwst_satz)
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
CREATE TABLE abrechnung_monat (
    id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    monat DATE NOT NULL,
    abrechnung_tag_id_von INTEGER(10) UNSIGNED NOT NULL,
    abrechnung_tag_id_bis INTEGER(10) UNSIGNED NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (abrechnung_tag_id_von) REFERENCES abrechnung_tag(id),
    FOREIGN KEY (abrechnung_tag_id_bis) REFERENCES abrechnung_tag(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
CREATE TABLE abrechnung_monat_mwst (
    id INTEGER(10) UNSIGNED NOT NULL,
    mwst_satz DECIMAL(6,5) NOT NULL,
    mwst_netto DECIMAL(13,2) NOT NULL,
    mwst_betrag DECIMAL(13,2) NOT NULL,
    bar_brutto DECIMAL(13,2) NOT NULL,
    PRIMARY KEY (id, mwst_satz)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- CREATE TABLE abrechnung_jahr (
--     id INTEGER(10) UNSIGNED NOT NULL,
--     jahr YEAR NOT NULL,
--     mwst_satz DECIMAL(6,5) NOT NULL,
--     mwst_netto DECIMAL(13,2) NOT NULL,
--     mwst_betrag DECIMAL(13,2) NOT NULL,
--     bar_brutto DECIMAL(13,2) NOT NULL,
--     PRIMARY KEY (id, mwst_satz)
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
CREATE TABLE abrechnung_jahr (
    id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    jahr YEAR NOT NULL,
    abrechnung_tag_id_von INTEGER(10) UNSIGNED NOT NULL,
    abrechnung_tag_id_bis INTEGER(10) UNSIGNED NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (abrechnung_tag_id_von) REFERENCES abrechnung_tag(id),
    FOREIGN KEY (abrechnung_tag_id_bis) REFERENCES abrechnung_tag(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
CREATE TABLE abrechnung_jahr_mwst (
    id INTEGER(10) UNSIGNED NOT NULL,
    mwst_satz DECIMAL(6,5) NOT NULL,
    mwst_netto DECIMAL(13,2) NOT NULL,
    mwst_betrag DECIMAL(13,2) NOT NULL,
    bar_brutto DECIMAL(13,2) NOT NULL,
    PRIMARY KEY (id, mwst_satz)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE bestellung (
    bestell_nr INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    typ VARCHAR(12) NOT NULL DEFAULT "",
    bestell_datum TIMESTAMP NOT NULL,
    jahr YEAR NOT NULL DEFAULT 2000,
    kw TINYINT(2) UNSIGNED NOT NULL DEFAULT 1,
    user_id INTEGER(10) UNSIGNED DEFAULT NULL,
    PRIMARY KEY (bestell_nr, typ),
    FOREIGN KEY (user_id) REFERENCES `user`(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
CREATE TABLE bestellung_details (
    bestell_nr INTEGER(10) UNSIGNED NOT NULL,
    typ VARCHAR(12) NOT NULL DEFAULT "",
    position SMALLINT(5) UNSIGNED NOT NULL,
    artikel_id INTEGER(10) UNSIGNED NOT NULL,
    stueckzahl SMALLINT(5) NOT NULL DEFAULT 1,
    PRIMARY KEY (bestell_nr, typ, position),
    FOREIGN KEY (bestell_nr) REFERENCES bestellung(bestell_nr),
    FOREIGN KEY (artikel_id) REFERENCES artikel(artikel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE tse_transaction (
    transaction_id INTEGER(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    transaction_number INTEGER(10) UNSIGNED DEFAULT NULL,
    rechnungs_nr INTEGER(10) UNSIGNED DEFAULT NULL,
    training BOOLEAN NOT NULL DEFAULT FALSE,
    transaction_start CHAR(29) DEFAULT NULL,
    transaction_end CHAR(29) DEFAULT NULL,
    process_type VARCHAR(30) DEFAULT NULL,
    signature_counter INTEGER(10) UNSIGNED DEFAULT NULL,
    signature_base64 VARCHAR(512) DEFAULT NULL,
    tse_error TINYTEXT DEFAULT NULL,
    process_data VARCHAR(65) DEFAULT NULL,
    user_id INTEGER(10) UNSIGNED DEFAULT NULL,
    PRIMARY KEY (transaction_id),
    -- If planning to use method `getTransactionByTxNumber()`, can also create index on column `transaction_number`
    FOREIGN KEY (rechnungs_nr) REFERENCES verkauf(rechnungs_nr),
    FOREIGN KEY (user_id) REFERENCES `user`(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
-- tx start and end times are prepared in format '2021-01-17T19:13:45.000+01:00' in Java,
--     so they have a fixed length of 29 chars
-- process_type will probably only ever need 14 chars (e.g. initially Kassenbeleg-V1, then Kassenbeleg-V2, ...)
--     but in the specs, it has (up to) 30 characters, so better make sure it works
-- Example signature in Base64:
--     XLBGMLidNi+vICwIAPO4B/PyDgSna+5EluXgchQOdNvNYfxcdJS/32mnmars0BxM+Dwk4W3kYaCavU7IEmPnIQ==
-- so 88 chars, but let's stick to specs where it says up to 512 chars
-- Example process_data with absurdly large amounts:
--         Beleg^2190.00_1795.00_0.00_0.00_0.00^3985.00:Unbar
--         AVBelegabbruch^0.00_0.00_0.00_0.00_0.00^
--     Just to make sure, let's assume each tax class has a sum with 4 digits:
--         Beleg^9999.00_9999.00_9999.00_9999.00_9999.00^49995.00:Unbar
--         AVTraining^9999.00_9999.00_9999.00_9999.00_9999.00^49995.00:Unbar
--     Even this extreme case would fit into a 65 chars long field

-- Internal master data (lieferant, mwst, produktgruppe, artikel, pfand)
-- ============================================================
INSERT INTO lieferant (lieferant_id, lieferant_name, lieferant_kurzname, n_artikel, aktiv)
VALUES (1, 'unbekannt', 'unbekannt', NULL, 1);

INSERT INTO mwst (mwst_id, mwst_satz, dsfinvk_ust_schluessel, dsfinvk_ust_beschr) VALUES
(1, 0.00000, 6, 'Umsatzsteuerfrei'),
(2, 0.07000, 2, 'Geltender ermäßigter Steuersatz (§ 12 Abs. 2 UStG)'),
(3, 0.19000, 1, 'Geltender allgemeiner Steuersatz (§ 12 Abs. 2 UStG)'),
(4, 0.05500, 4, 'Durchschnittsatz (§ 24 Abs. 1 Nr. 1 UStG)'),
(5, 0.10700, 3, 'Durchschnittsatz (§ 24 Abs. 1 Nr. 3 UStG) übrige Fälle');

INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (1,NULL,NULL,NULL,'Intern',NULL,NULL,NULL,NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (2,NULL,1,NULL,'Rabatt',NULL,NULL,NULL,NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (3,NULL,1,1,'Rabatt 0% MwSt',1,NULL,NULL,NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (4,NULL,1,2,'Rabatt 7% MwSt',2,NULL,NULL,NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (5,NULL,1,3,'Rabatt 19% MwSt',3,NULL,NULL,NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (6,NULL,2,NULL,'Gutschein',1,NULL,NULL,NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (7,NULL,3,NULL,'Pfand',3,NULL,NULL,NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (8,NULL,4,NULL,'Pfand optional',3,NULL,NULL,NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (9,1,NULL,NULL,'Sonstiges',NULL,NULL,NULL,NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (10,1,1,NULL,'Sonstiges 0% MwSt',1,NULL,NULL,NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (11,1,2,NULL,'Sonstiges 7% MwSt',2,NULL,NULL,NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (12,1,3,NULL,'Sonstiges 19% MwSt',3,NULL,NULL,NULL,NULL,1);

INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (1,2,1,'RABATT1','Manueller Rabatt','Rabatt',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (2,2,1,'RABATT2','Rabatt auf Rechnung','Rabatt',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (3,2,1,'ANPASSUNG','Manuelle Preisanpassung','Preisanpassung',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (4,2,1,'ANZAHLUNG','Anzahlung','Anzahlung',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (5,2,1,'ANZAHLAUFLOES','Anzahlungsauflösung','Anzahl.auflös.',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (6,6,1,'GUTSCHEIN','Gutschein','Gutschein',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (7,6,1,'GUTSCHEINEINLOES','Gutscheineinlösung','Gutscheineinlösung',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (8,7,1,'PFAND1','Pfand 0,08 €','Pfand',NULL,NULL,NULL,NULL,NULL,1,0.08,0.08,NULL,0.08,0,1,0,-1,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (9,7,1,'PFAND2','Pfand 0,15 €','Pfand',NULL,NULL,NULL,NULL,NULL,1,0.15,0.15,NULL,0.15,0,1,0,-1,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (10,7,1,'PFAND3','Pfand 0,25 €','Pfand',NULL,NULL,NULL,NULL,NULL,1,0.25,0.25,NULL,0.25,0,1,0,-1,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (11,8,1,'PFANDKISTE','Pfand Kiste, Pfandkiste','Pfand Kiste',NULL,NULL,NULL,NULL,NULL,1,1.50,1.50,NULL,1.50,0,1,0,-1,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (12,8,1,'COLAKISTE','Pfand Cola-Kiste, Colakiste','Pfand Cola-Kiste',NULL,NULL,NULL,NULL,NULL,1,3.18,3.18,NULL,3.18,0,1,0,-1,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (13,8,1,'PFAND6','Pfand Kaffee-Eimer','Pfand Kaffee-Eimer',NULL,NULL,NULL,NULL,NULL,1,2.60,2.60,NULL,2.60,0,0,0,-1,NULL,NULL,NULL,1);

INSERT INTO pfand (pfand_id, artikel_id) VALUES
(1, 8), (2, 9), (3, 10), (4, 11), (5, 12), (6, 13);

-- ============================================================
-- Example master data (from ../git/mysql/fillWithExampleData.sql)
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (16,2,NULL,NULL,'Lebensmittel',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (17,2,1,NULL,'Sonstige Lebensmittel',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (18,2,2,NULL,'Kaffeeprodukte',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (19,2,2,1,'Kaffee',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (20,2,2,2,'Espresso',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (21,2,2,3,'Kaffeepads',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (22,2,2,4,'Entkoffeiniert',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (23,2,2,5,'Getreidekaffee',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (24,2,2,6,'Guarana',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (25,2,2,7,'Instantkaffee',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (26,2,3,NULL,'Tee',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (27,2,3,1,'Grüner Tee',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (28,2,3,2,'Weißer Tee',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (29,2,3,3,'Schwarzer Tee',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (30,2,3,4,'Kräuter- und Früchtetee',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (31,2,3,5,'Gewürztee',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (32,2,3,6,'Rotbuschtee',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (33,2,3,7,'Mate',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (34,2,4,NULL,'Kakao und Trinkschokolade',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (35,2,5,NULL,'Gewürze und Kräuter',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (36,2,6,NULL,'Bananen',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (37,2,7,NULL,'Nudeln',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (38,2,8,NULL,'Nüsse',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (39,2,9,NULL,'Trockenfrüchte',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (40,2,10,NULL,'Süßwaren und Snacks',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (41,2,10,1,'Tafelschokolade',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (42,2,10,2,'Schokoriegel',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (43,2,10,3,'Nuss- und Fruchtriegel',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (44,2,10,4,'Gebäck',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (45,2,10,5,'Confiserie',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (46,2,10,6,'Bonbons',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (47,2,10,7,'Fruchtgummi',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (48,2,10,8,'Chips und Knabbereien',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (49,2,11,NULL,'Zucker',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (50,2,12,NULL,'Brotaufstriche',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (51,2,12,1,'Honig',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (52,2,12,2,'Marmeladen und Konfitüren',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (53,2,12,3,'Nuss- und Schokoladencremes',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (54,2,12,4,'Herzhafte Brotaufstriche',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (55,2,13,NULL,'Soßen und Würzpasten',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (56,2,14,NULL,'Essig und Öl',2,NULL,'l',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (57,2,15,NULL,'Feinkost',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (58,2,16,NULL,'Getreide und Hülsenfrüchte',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (59,2,16,1,'Sonstige Getreide',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (60,2,16,2,'Reis',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (61,2,16,3,'Quinoa',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (62,2,16,4,'Hülsenfrüchte',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (63,2,16,5,'Müsli',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (64,2,17,NULL,'Saisonartikel',2,NULL,'kg',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (65,3,NULL,NULL,'Getränke',3,NULL,'l',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (66,3,1,NULL,'Sonstige Getränke',3,NULL,'l',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (67,3,2,NULL,'Alkoholische Getränke pfandfrei',3,NULL,'l',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (68,3,2,1,'Sonstige alkoholische Getränke',3,NULL,'l',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (69,3,2,2,'Wein',3,NULL,'l',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (70,3,2,3,'Rum',3,NULL,'l',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (71,3,3,NULL,'Alkoholfreie Getränke pfandfrei',3,NULL,'l',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (72,3,4,NULL,'Alkoholfreie Getränke 8 Cent Pfand',3,1,'l',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (73,3,5,NULL,'Alkoholfreie Getränke 15 Cent Pfand',3,2,'l',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (74,3,6,NULL,'Alkoholfreie Getränke 25 Cent Pfand',3,3,'l',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (75,4,NULL,NULL,'Kunsthandwerk',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (76,4,1,NULL,'Sonstiges Kunsthandwerk',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (77,4,2,NULL,'Schmuck',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (78,4,3,NULL,'Geschirr und Glaswaren',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (79,4,4,NULL,'Dekoartikel',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (80,4,5,NULL,'Körbe',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (81,4,6,NULL,'Musikinstrumente',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (82,4,7,NULL,'Spielzeug',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (83,4,8,NULL,'Textilwaren',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (84,4,9,NULL,'Lederwaren',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (85,4,10,NULL,'Taschen',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (86,4,11,NULL,'Handytaschen',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (87,4,12,NULL,'Geldbörsen',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (88,4,13,NULL,'Brillenetuis',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (89,4,14,NULL,'Kosmetik',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (90,4,15,NULL,'Kerzen und Räucherwerk',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (91,4,16,NULL,'Saisonartikel KHW',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (92,4,17,NULL,'CDs',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (93,4,17,1,'Sonstige CDs',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (94,4,17,2,'Putumayo',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (95,4,18,NULL,'Kleidung',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (96,4,18,1,'Sonstige Kleidung',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (97,4,18,2,'Kleidung Erwachsene',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (98,4,18,3,'Kleidung Kinder',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (99,4,18,4,'Textile Accessoires',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (100,4,18,5,'Schuhe',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (101,4,19,NULL,'Papier',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (102,4,19,1,'Sonstiges Papier',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (103,4,19,2,'Grußkarten',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (104,4,19,3,'Kalender',2,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (105,4,19,4,'Bücher',2,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (106,4,19,5,'Briefpapier und -umschläge',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (107,5,NULL,NULL,'Ergänzungsprodukte',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (108,4,19,6,'Notizbücher und Fotoalben',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `produktgruppe` (`produktgruppen_id`, `toplevel_id`, `sub_id`, `subsub_id`, `produktgruppen_name`, `mwst_id`, `pfand_id`, `std_einheit`, `n_artikel`, `n_artikel_rekursiv`, `aktiv`) VALUES (109,4,19,7,'Infomaterial',3,NULL,'St.',NULL,NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (2,'FHZ Rheinland','FHZ',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (3,'GEPA','GEPA',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (4,'GEPA/and.','GEPA',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (5,'EP','EP',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (6,'dwp','dwp',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (7,'Ethiquable','Eth',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (8,'CTM','CTM',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (9,'Libera Terra','LT',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (10,'Café Libertad','CL',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (11,'Bannmühle','BM',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (12,'Bannmühle/dwp','BM/dwp',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (13,'Fairkauf','FK',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (14,'Salinas','Sal',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (15,'Olaf Müller','OM',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (16,'Globo','Globo',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (17,'Fairtrade Center Breisgau','FTC',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (18,'BanaFair','BF',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (19,'Exil Music','Exil',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (20,'Memo','Memo',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (21,'LamuLamu','Lamu',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (22,'FairMail','FM',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (23,'Biologische Station Bonn','BS',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (24,'Postkarten Ackermann','Ack',NULL,1);
INSERT INTO `lieferant` (`lieferant_id`, `lieferant_name`, `lieferant_kurzname`, `n_artikel`, `aktiv`) VALUES (25,'Taguaprodukte Ecuador','Tagua',NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (100,11,1,'SONSTIGES1','Variabler Preis 7% MwSt, Sonstige','Var. Preis 7%',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (101,12,1,'SONSTIGES2','Variabler Preis 19% MwSt, Sonstige','Var. Preis 19%',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (102,17,1,'SONSTIGES3','Lebensmittel, Sonstige','Lebensmittel',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (103,67,1,'SONSTIGES4','Alkohol pfandfrei, Sonstige','Alkohol pfandfrei',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (104,71,1,'SONSTIGES5','Getränk pfandfrei, Sonstige','Getränk pfandfrei',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (105,72,1,'SONSTIGES6','Getränk 8 ct. Pfand, Sonstige','Getränk 8 ct. Pfand',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (106,73,1,'SONSTIGES7','Getränk 15 ct. Pfand, Sonstige','Getränk 15 ct. Pfand',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (107,74,1,'SONSTIGES8','Getränk 25 ct. Pfand, Sonstige','Getränk 25 ct. Pfand',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (108,76,1,'SONSTIGES9','Kunsthandwerk, Sonstige','Kunsthandwerk',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (109,77,1,'SONSTIGES10','Schmuck, Sonstige','Schmuck',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (110,78,1,'SONSTIGES11','Geschirr/Glaswaren, Sonstige','Geschirr/Glaswaren',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (111,79,1,'SONSTIGES12','Dekoartikel, Sonstige','Dekoartikel',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (112,80,1,'SONSTIGES13','Korb, Sonstige','Korb',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (113,81,1,'SONSTIGES14','Musikinstrument, Sonstige','Musikinstrument',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (114,82,1,'SONSTIGES15','Spielzeug, Sonstige','Spielzeug',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (115,83,1,'SONSTIGES16','Textilware, Sonstige','Textilware',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (116,84,1,'SONSTIGES17','Lederware, Sonstige','Lederware',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (117,85,1,'SONSTIGES18','Tasche, Sonstige','Tasche',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (118,86,1,'SONSTIGES19','Handytasche, Sonstige','Handytasche',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (119,87,1,'SONSTIGES20','Geldbörse, Sonstige','Geldbörse',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (120,88,1,'SONSTIGES21','Brillenetui, Sonstige','Brillenetui',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (121,89,1,'SONSTIGES22','Kosmetik, Sonstige','Kosmetik',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (122,90,1,'SONSTIGES23','Kerze/Räucherwerk, Sonstige','Kerze/Räucherwerk',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (123,93,1,'SONSTIGES24','CD, Sonstige','CD',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (124,94,1,'SONSTIGES25','Putumayo, Sonstige','Putumayo',NULL,NULL,NULL,NULL,NULL,1,15.90,NULL,NULL,NULL,0,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (125,96,1,'SONSTIGES26','Kleidung, Sonstige','Kleidung',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (126,99,1,'SONSTIGES27','Textiles Accessoire, Sonstige','Text. Accessoire',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (127,100,1,'SONSTIGES28','Schuhe, Sonstige','Schuhe',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (128,102,1,'SONSTIGES29','Papierware, Sonstige','Papierware',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (129,103,1,'SONSTIGES30','Grußkarte, Sonstige','Grußkarte',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (130,104,1,'SONSTIGES31','Kalender, Sonstige','Kalender',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (131,105,1,'SONSTIGES32','Buch, Sonstige','Buch',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (132,106,1,'SONSTIGES33','Briefpapier/-umschlag, Sonstige','Briefpapier/-umschlag',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
INSERT INTO `artikel` (`artikel_id`, `produktgruppen_id`, `lieferant_id`, `artikel_nr`, `artikel_name`, `kurzname`, `menge`, `einheit`, `barcode`, `herkunft`, `vpe`, `setgroesse`, `vk_preis`, `empf_vk_preis`, `ek_rabatt`, `ek_preis`, `variabler_preis`, `sortiment`, `lieferbar`, `beliebtheit`, `bestand`, `von`, `bis`, `aktiv`) VALUES (133,107,1,'SONSTIGES34','Ergänzungsprodukt, Sonstige','Ergänzungsprodukt',NULL,NULL,NULL,NULL,NULL,1,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,1);
-- ============================================================

-- Bootstrap admin user, password: changeme (bcrypt) - change it after first login!
INSERT INTO `user` (username, password_hash, role, active)
VALUES ('admin', '$2b$12$0Hm8ZRJY/DoPvFihPWckBOsAhqUzP.t8RFJeZFnC5Xq1ogtZI7rYK', 'admin', 1);

-- First API/Java POS voucher number is 200; legacy paper vouchers are below that.
INSERT INTO gutschein_counter (id, last_nr) VALUES (1, 199);

-- ============================================================
-- Privileges for the API users (create the users first, see README)
-- ============================================================
GRANT ALL PRIVILEGES ON kasse.* TO 'kassenadmin'@'localhost';
GRANT SELECT ON kasse.* TO 'mitarbeiter'@'localhost';
GRANT INSERT, UPDATE ON kasse.artikel TO 'mitarbeiter'@'localhost';
GRANT INSERT, UPDATE ON kasse.mwst TO 'mitarbeiter'@'localhost';
GRANT INSERT, UPDATE ON kasse.lieferant TO 'mitarbeiter'@'localhost';
GRANT INSERT, UPDATE ON kasse.produktgruppe TO 'mitarbeiter'@'localhost';
GRANT INSERT ON kasse.verkauf TO 'mitarbeiter'@'localhost';
GRANT INSERT ON kasse.verkauf_mwst TO 'mitarbeiter'@'localhost';
GRANT INSERT ON kasse.verkauf_details TO 'mitarbeiter'@'localhost';
GRANT INSERT ON kasse.kassenstand TO 'mitarbeiter'@'localhost';
GRANT INSERT ON kasse.anzahlung TO 'mitarbeiter'@'localhost';
GRANT INSERT ON kasse.anzahlung_details TO 'mitarbeiter'@'localhost';
GRANT INSERT ON kasse.gutschein TO 'mitarbeiter'@'localhost';
GRANT INSERT, UPDATE ON kasse.rabattaktion TO 'mitarbeiter'@'localhost';
GRANT INSERT, UPDATE ON kasse.pfand TO 'mitarbeiter'@'localhost';
GRANT INSERT ON kasse.abrechnung_tag TO 'mitarbeiter'@'localhost';
GRANT INSERT ON kasse.abrechnung_tag_mwst TO 'mitarbeiter'@'localhost';
GRANT INSERT ON kasse.abrechnung_tag_tse TO 'mitarbeiter'@'localhost';
GRANT INSERT, UPDATE ON kasse.zaehlprotokoll TO 'mitarbeiter'@'localhost';
GRANT INSERT ON kasse.zaehlprotokoll_details TO 'mitarbeiter'@'localhost';
GRANT INSERT, DELETE ON kasse.abrechnung_monat TO 'mitarbeiter'@'localhost';
GRANT INSERT, DELETE ON kasse.abrechnung_monat_mwst TO 'mitarbeiter'@'localhost';
GRANT INSERT, DELETE ON kasse.abrechnung_jahr TO 'mitarbeiter'@'localhost';
GRANT INSERT, DELETE ON kasse.abrechnung_jahr_mwst TO 'mitarbeiter'@'localhost';
GRANT INSERT, UPDATE, DELETE ON kasse.bestellung TO 'mitarbeiter'@'localhost';
GRANT INSERT, UPDATE, DELETE ON kasse.bestellung_details TO 'mitarbeiter'@'localhost';
GRANT INSERT ON kasse.tse_transaction TO 'mitarbeiter'@'localhost';
GRANT SELECT, INSERT, UPDATE ON kasse.gutschein_counter TO 'mitarbeiter'@'localhost';

-- ============================================================
-- Separate training database (TRAINING_MODE + TRAINING_DB_URL)
-- ============================================================
-- The API itself creates the tables and seeds the test catalog on startup.
DROP DATABASE IF EXISTS kasse_training;
CREATE DATABASE kasse_training CHARACTER SET utf8 COLLATE utf8_general_ci;
GRANT ALL PRIVILEGES ON kasse_training.* TO 'kassenadmin'@'localhost';

FLUSH PRIVILEGES;
