# Postcode API Migration Summary

## Overview

The Find Trigs API uses the `postcodes` table populated from the NSPL (National Statistics Postcode Lookup) dataset.

## What changed

- A `postcodes` table is used as the primary source of postcode coordinates.
- The API and CRUD code paths were updated to query `postcodes` for postcode lookups.

## Notes

This document intentionally omits the names of older legacy postcode tables to avoid reintroducing stale references.
