-- ============================================================
-- Migration: Organic / vegan flags for articles
-- ============================================================
-- Both columns are optional (NULL = unknown), mainly meaningful for food.
-- Product images are NOT stored in the DB; they live in the directory from
-- IMAGES_DIR and are named <artikel_id>.<ext>.
--
-- Run as kassenadmin (full privileges). Back up first.

ALTER TABLE `artikel` ADD COLUMN `bio` BOOLEAN DEFAULT NULL;
ALTER TABLE `artikel` ADD COLUMN `vegan` BOOLEAN DEFAULT NULL;
