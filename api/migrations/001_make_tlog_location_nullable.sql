-- Migration: Make tlog location fields nullable
-- Description: Allow logs without specific location data (osgb_eastings, osgb_northings, osgb_gridref)
-- Date: 2025-11-04
-- Author: System

-- Make location fields nullable in tlog table
ALTER TABLE tlog 
  MODIFY COLUMN osgb_eastings INT NULL,
  MODIFY COLUMN osgb_northings INT NULL,
  MODIFY COLUMN osgb_gridref VARCHAR(14) NULL;

-- Verify the changes
DESCRIBE tlog;

