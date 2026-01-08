-- Foreign key integrity audit queries (pre-validation)
--
-- This repo adds several FK constraints as NOT VALID to minimise migration impact.
-- Use this file to assess whether legacy data contains orphaned references before
-- validating constraints in production/staging.
--
-- How to use:
--   - Run each query and ensure orphan_count is 0 before VALIDATE CONSTRAINT.
--   - Where ON DELETE SET NULL is used, you may choose to NULL out orphaned
--     references rather than deleting rows.

-- -------------------------------------------------------------------------
-- tlog
-- -------------------------------------------------------------------------
SELECT COUNT(*) AS orphan_count
FROM tlog tl
LEFT JOIN trig t ON t.id = tl.trig_id
WHERE tl.trig_id IS NOT NULL AND t.id IS NULL;

SELECT COUNT(*) AS orphan_count
FROM tlog tl
LEFT JOIN "user" u ON u.id = tl.user_id
WHERE tl.user_id IS NOT NULL AND u.id IS NULL;

-- -------------------------------------------------------------------------
-- tphoto
-- -------------------------------------------------------------------------
SELECT COUNT(*) AS orphan_count
FROM tphoto p
LEFT JOIN tlog tl ON tl.id = p.tlog_id
WHERE p.tlog_id IS NOT NULL AND tl.id IS NULL;

SELECT COUNT(*) AS orphan_count
FROM tphoto p
LEFT JOIN server s ON s.id = p.server_id
WHERE p.server_id IS NOT NULL AND s.id IS NULL;

-- -------------------------------------------------------------------------
-- tphotovote
-- -------------------------------------------------------------------------
SELECT COUNT(*) AS orphan_count
FROM tphotovote v
LEFT JOIN tphoto p ON p.id = v.tphoto_id
WHERE v.tphoto_id IS NOT NULL AND p.id IS NULL;

SELECT COUNT(*) AS orphan_count
FROM tphotovote v
LEFT JOIN "user" u ON u.id = v.user_id
WHERE v.user_id IS NOT NULL AND u.id IS NULL;

-- -------------------------------------------------------------------------
-- trig
-- -------------------------------------------------------------------------
SELECT COUNT(*) AS orphan_count
FROM trig t
LEFT JOIN status s ON s.id = t.status_id
WHERE t.status_id IS NOT NULL AND s.id IS NULL;

SELECT COUNT(*) AS orphan_count
FROM trig t
LEFT JOIN "user" u ON u.id = t.crt_user_id
WHERE t.crt_user_id IS NOT NULL AND u.id IS NULL;

SELECT COUNT(*) AS orphan_count
FROM trig t
LEFT JOIN "user" u ON u.id = t.admin_user_id
WHERE t.admin_user_id IS NOT NULL AND u.id IS NULL;

-- -------------------------------------------------------------------------
-- attr*
-- -------------------------------------------------------------------------
SELECT COUNT(*) AS orphan_count
FROM attr a
LEFT JOIN attrsource s ON s.id = a.attrsource_id
WHERE s.id IS NULL;

SELECT COUNT(*) AS orphan_count
FROM attrset aset
LEFT JOIN trig t ON t.id = aset.trig_id
WHERE t.id IS NULL;

SELECT COUNT(*) AS orphan_count
FROM attrset aset
LEFT JOIN attrsource s ON s.id = aset.attrsource_id
WHERE s.id IS NULL;

SELECT COUNT(*) AS orphan_count
FROM attrval av
LEFT JOIN attr a ON a.id = av.attr_id
WHERE a.id IS NULL;

SELECT COUNT(*) AS orphan_count
FROM attrset_attrval j
LEFT JOIN attrset aset ON aset.id = j.attrset_id
WHERE aset.id IS NULL;

SELECT COUNT(*) AS orphan_count
FROM attrset_attrval j
LEFT JOIN attrval av ON av.id = j.attrval_id
WHERE av.id IS NULL;

-- -------------------------------------------------------------------------
-- trigstats (special: ON DELETE CASCADE from trig)
-- -------------------------------------------------------------------------
SELECT COUNT(*) AS orphan_count
FROM trigstats ts
LEFT JOIN trig t ON t.id = ts.id
WHERE t.id IS NULL;


