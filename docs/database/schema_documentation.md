# Database Schema Documentation

**Database:** trigpoin_trigs
**Export Date:** 2025-08-22 00:06:18.288963
**Total Tables:** 38

## Table Overview

- **OSGBIW**: 31,518 rows, 15 columns
- **ad2user**: 0 rows, 4 columns
- **attr**: 14 rows, 12 columns
- **attrset**: 31,518 rows, 5 columns
- **attrset_attrval**: 441,252 rows, 3 columns
- **attrsource**: 2 rows, 6 columns
- **attrval**: 142,930 rows, 8 columns
- **barrytools**: 76 rows, 21 columns
- **cache**: 0 rows, 37 columns
- **coord2county**: 35,247 rows, 4 columns
- **county**: 72 rows, 8 columns
- **nearest**: 72 rows, 8 columns
- **os_net_web**: 844 rows, 2 columns
- **percentile**: 0 rows, 4 columns
- **place**: 39,134 rows, 15 columns
- **postcode6**: 8,481 rows, 10 columns
- **postcode8**: 54,552 rows, 5 columns
- **route_item**: 0 rows, 4 columns
- **server**: 3 rows, 4 columns
- **sms**: 518 rows, 13 columns
- **status**: 7 rows, 4 columns
- **tlog**: 468,414 rows, 15 columns
- **town**: 1,915 rows, 6 columns
- **tphoto**: 402,671 rows, 19 columns
- **tphotoclass**: 5,292 rows, 2 columns
- **tphotostats**: 0 rows, 4 columns
- **tphotovote**: 94,832 rows, 5 columns
- **tquery**: 2,456,719 rows, 13 columns
- **tquizscores**: 3,277 rows, 8 columns
- **trig**: 25,810 rows, 36 columns
- **trigdata**: 7,314 rows, 33 columns
- **trigdatafields**: 32 rows, 10 columns
- **trigstats**: 25,066 rows, 11 columns
- **tuserstats**: 0 rows, 2 columns
- **twatch**: 5 rows, 5 columns
- **user**: 14,682 rows, 55 columns

## Detailed Table Schemas

### OSGBIW

**Rows:** 31,518

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | INTEGER | No |  | ✅ |
| Trig Name | VARCHAR(255) COLLATE "utf8mb3_general_ci" | Yes |  |  |
| Original Name | VARCHAR(255) COLLATE "utf8mb3_general_ci" | Yes |  |  |
| New Name | VARCHAR(255) COLLATE "utf8mb3_general_ci" | Yes |  |  |
| EASTING | DECIMAL(10, 2) | Yes |  |  |
| NORTHING | DECIMAL(10, 2) | Yes |  |  |
| HEIGHT | DECIMAL(9, 3) | Yes |  |  |
| ORDER | INTEGER | Yes |  |  |
| TYPE OF MARK | VARCHAR(255) COLLATE "utf8mb3_general_ci" | Yes |  |  |
| Computing Date | VARCHAR(10) COLLATE "utf8mb3_general_ci" | Yes |  |  |
| CLASS OF LEVELLING | INTEGER | Yes |  |  |
| Date of Levelling | VARCHAR(255) COLLATE "utf8mb3_general_ci" | Yes |  |  |
| LEVELLING DATUM | VARCHAR(255) COLLATE "utf8mb3_general_ci" | Yes |  |  |
| DESTROYED MARK INDICATOR | INTEGER | Yes |  |  |
| COMMENTS | VARCHAR(255) COLLATE "utf8mb3_general_ci" | Yes |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "Trig Name": "Thoresby Wtr Twr",
    "Original Name": "/PP154",
    "New Name": "0",
    "EASTING": "463765.24",
    "NORTHING": "367685.93",
    "HEIGHT": "94.599",
    "ORDER": 2,
    "TYPE OF MARK": "BOLT",
    "Computing Date": "01/06/1987",
    "CLASS OF LEVELLING": 2,
    "Date of Levelling": "01/06/1987",
    "LEVELLING DATUM": "N",
    "DESTROYED MARK INDICATOR": 0,
    "COMMENTS": "N CEN ENGLAND ADJUSTMENT"
  },
  {
    "id": 2,
    "Trig Name": "Wingreen (old)",
    "Original Name": "/PP17",
    "New Name": "PPP17",
    "EASTING": "392498.78",
    "NORTHING": "120648.73",
    "HEIGHT": "0.000",
    "ORDER": 3,
    "TYPE OF MARK": "OLD TRIG",
    "Computing Date": "01/06/1936",
    "CLASS OF LEVELLING": 0,
    "Date of Levelling": "",
    "LEVELLING DATUM": "",
    "DESTROYED MARK INDICATOR": 0,
    "COMMENTS": ""
  },
  {
    "id": 3,
    "Trig Name": "East Grinstead Ch Twr",
    "Original Name": "/PP170",
    "New Name": "0",
    "EASTING": "539633.26",
    "NORTHING": "137997.00",
    "HEIGHT": "0.000",
    "ORDER": 3,
    "TYPE OF MARK": "PINNACLE",
    "Computing Date": "01/06/1975",
    "CLASS OF LEVELLING": 0,
    "Date of Levelling": "",
    "LEVELLING DATUM": "",
    "DESTROYED MARK INDICATOR": 0,
    "COMMENTS": "SE pinnacle"
  }
]
```

### ad2user

**Rows:** 0

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| ad_code | CHAR(6) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| user_id | MEDIUMINT | No |  | ✅ |
| eligible_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |
### attr

**Rows:** 14

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | INTEGER | No |  | ✅ |
| attrsource_id | INTEGER | No |  |  |
| name | VARCHAR(45) COLLATE "utf8mb3_general_ci" | No |  |  |
| description | VARCHAR(255) COLLATE "utf8mb3_general_ci" | No |  |  |
| mandatory | TINYINT | No |  |  |
| multivalued | TINYINT | No |  |  |
| grouped | TINYINT | No |  |  |
| sort_order | INTEGER | No |  |  |
| style | VARCHAR(45) COLLATE "utf8mb3_general_ci" | Yes |  |  |
| url_javaclass | VARCHAR(45) COLLATE "utf8mb3_general_ci" | Yes |  |  |
| type | VARCHAR(45) COLLATE "utf8mb3_general_ci" | Yes |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "attrsource_id": 2,
    "name": "Trig Name",
    "description": "",
    "mandatory": 1,
    "multivalued": 0,
    "grouped": 0,
    "sort_order": 1,
    "style": null,
    "url_javaclass": null,
    "type": null,
    "upd_timestamp": "2014-05-21 21:24:03"
  },
  {
    "id": 2,
    "attrsource_id": 2,
    "name": "Original Name",
    "description": "",
    "mandatory": 1,
    "multivalued": 0,
    "grouped": 0,
    "sort_order": 2,
    "style": null,
    "url_javaclass": null,
    "type": null,
    "upd_timestamp": "2014-05-21 21:24:03"
  },
  {
    "id": 3,
    "attrsource_id": 2,
    "name": "New Name",
    "description": "",
    "mandatory": 1,
    "multivalued": 0,
    "grouped": 0,
    "sort_order": 3,
    "style": null,
    "url_javaclass": null,
    "type": null,
    "upd_timestamp": "2014-05-21 21:24:03"
  }
]
```

### attrset

**Rows:** 31,518

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | INTEGER | No |  | ✅ |
| trig_id | INTEGER | No |  |  |
| attrsource_id | INTEGER | No |  |  |
| sort_order | INTEGER | No |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "trig_id": 7977,
    "attrsource_id": 2,
    "sort_order": 1,
    "upd_timestamp": "2014-05-19 13:54:34"
  },
  {
    "id": 2,
    "trig_id": 738,
    "attrsource_id": 2,
    "sort_order": 2,
    "upd_timestamp": "2014-05-19 13:54:34"
  },
  {
    "id": 3,
    "trig_id": 9062,
    "attrsource_id": 2,
    "sort_order": 3,
    "upd_timestamp": "2014-05-19 13:54:34"
  }
]
```

### attrset_attrval

**Rows:** 441,252

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| attrset_id | INTEGER | No |  | ✅ |
| attrval_id | INTEGER | No |  | ✅ |
| upd_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "attrset_id": 1,
    "attrval_id": 556716,
    "upd_timestamp": "2014-05-19 13:54:44"
  },
  {
    "attrset_id": 1,
    "attrval_id": 579956,
    "upd_timestamp": "2014-05-19 13:54:47"
  },
  {
    "attrset_id": 1,
    "attrval_id": 604341,
    "upd_timestamp": "2014-05-19 13:54:51"
  }
]
```

### attrsource

**Rows:** 2

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | INTEGER | No |  | ✅ |
| name | VARCHAR(50) COLLATE "utf8mb3_general_ci" | No |  |  |
| descr | TEXT COLLATE "utf8mb3_general_ci" | Yes |  |  |
| url | VARCHAR(255) COLLATE "utf8mb3_general_ci" | Yes |  |  |
| sort_order | INTEGER | No |  |  |
| crt_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "name": "TrigpointingUK",
    "descr": "Data maintained by the TrigpointingUK admins",
    "url": "http://www.trigpointinguk.com",
    "sort_order": 1,
    "crt_timestamp": "2014-05-12 21:17:52"
  },
  {
    "id": 2,
    "name": "OSGB36 trig archive spreadsheet - IW",
    "descr": "Every OS trig point known - IW 15-7-09",
    "url": "https://groups.yahoo.com/neo/groups/trigonomy/files/OS%20data/",
    "sort_order": 2,
    "crt_timestamp": "2014-05-21 21:21:49"
  }
]
```

### attrval

**Rows:** 142,930

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | INTEGER | No |  | ✅ |
| attr_id | INTEGER | No |  |  |
| value_string | VARCHAR(255) COLLATE "utf8mb3_general_ci" | Yes |  |  |
| value_double | DOUBLE | Yes |  |  |
| value_bool | TINYINT | Yes |  |  |
| value_point | NULL | Yes |  |  |
| group_name | VARCHAR(255) COLLATE "utf8mb3_general_ci" | Yes |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "id": 556716,
    "attr_id": 1,
    "value_string": "Thoresby Wtr Twr",
    "value_double": null,
    "value_bool": null,
    "value_point": null,
    "group_name": null,
    "upd_timestamp": "2014-05-19 13:53:57"
  },
  {
    "id": 556717,
    "attr_id": 1,
    "value_string": "Wingreen (old)",
    "value_double": null,
    "value_bool": null,
    "value_point": null,
    "group_name": null,
    "upd_timestamp": "2014-05-19 13:53:57"
  },
  {
    "id": 556718,
    "attr_id": 1,
    "value_string": "East Grinstead Ch Twr",
    "value_double": null,
    "value_bool": null,
    "value_point": null,
    "group_name": null,
    "upd_timestamp": "2014-05-19 13:53:57"
  }
]
```

### barrytools

**Rows:** 76

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | INTEGER | No |  | ✅ |
| name | VARCHAR(64) COLLATE "latin1_swedish_ci" | No |  |  |
| used_by | SET | No |  |  |
| theme | ENUM | No |  |  |
| theme_others | SET | No |  |  |
| type | ENUM | No |  |  |
| status | ENUM | No |  |  |
| linkable_ind | ENUM | No |  |  |
| title | VARCHAR(64) COLLATE "latin1_swedish_ci" | No |  |  |
| short_desc | VARCHAR(64) COLLATE "latin1_swedish_ci" | No |  |  |
| description | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| p_u | ENUM | No |  |  |
| p_by | ENUM | No |  |  |
| p_county | ENUM | No |  |  |
| p_type | ENUM | No |  |  |
| p_size | ENUM | No |  |  |
| p_date | ENUM | No |  |  |
| p_q | ENUM | No |  |  |
| p_others | TEXT COLLATE "latin1_swedish_ci" | No |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |
| crt_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "name": "active_cachers.php",
    "used_by": "C",
    "theme": "cachers",
    "theme_others": "logs,cachers",
    "type": "groupby",
    "status": "public",
    "linkable_ind": "Y",
    "title": "Active Cachers in the last...",
    "short_desc": "",
    "description": "Shows now many cachers have been logging cachers in the past",
    "p_u": "N",
    "p_by": "N",
    "p_county": "N",
    "p_type": "N",
    "p_size": "N",
    "p_date": "N",
    "p_q": "N",
    "p_others": "",
    "upd_timestamp": "2005-06-17 12:05:53",
    "crt_timestamp": "2005-06-10 00:26:47"
  },
  {
    "id": 3,
    "name": "active_users.php",
    "used_by": "T",
    "theme": "users",
    "theme_others": "logs",
    "type": "groupby",
    "status": "public",
    "linkable_ind": "Y",
    "title": "Active Users in the last...",
    "short_desc": "",
    "description": "",
    "p_u": "N",
    "p_by": "N",
    "p_county": "N",
    "p_type": "N",
    "p_size": "N",
    "p_date": "N",
    "p_q": "N",
    "p_others": "",
    "upd_timestamp": "2005-06-17 12:13:29",
    "crt_timestamp": "0000-00-00 00:00:00"
  },
  {
    "id": 4,
    "name": "album.php",
    "used_by": "T",
    "theme": "photos",
    "theme_others": "trigs,logs,users",
    "type": "album",
    "status": "public",
    "linkable_ind": "Y",
    "title": "Highly Rated Photographs",
    "short_desc": "",
    "description": "",
    "p_u": "O",
    "p_by": "N",
    "p_county": "O",
    "p_type": "O",
    "p_size": "N",
    "p_date": "N",
    "p_q": "N",
    "p_others": "big - D\r\nalt - O\r\npage - D\r\nskipped - O\r\neach - O \r\nclass -O\r\nmean - O",
    "upd_timestamp": "2005-06-17 12:23:01",
    "crt_timestamp": "0000-00-00 00:00:00"
  }
]
```

### cache

**Rows:** 0

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | MEDIUMINT | No |  | ✅ |
| owner_id | MEDIUMINT | Yes |  |  |
| name | VARCHAR(80) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| placed_date | DATE | Yes |  |  |
| type | CHAR(1) COLLATE "latin1_swedish_ci" | Yes |  |  |
| size | CHAR(1) COLLATE "latin1_swedish_ci" | Yes |  |  |
| difficulty | DECIMAL(2, 1) | Yes |  |  |
| terrain | DECIMAL(2, 1) | Yes |  |  |
| waypoint | VARCHAR(8) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| wgs_lat | DECIMAL(9, 6) | Yes |  |  |
| wgs_long | DECIMAL(9, 6) | Yes |  |  |
| osgb_eastings | MEDIUMINT | Yes |  |  |
| osgb_northings | MEDIUMINT | Yes |  |  |
| osgb_gridref | VARCHAR(14) COLLATE "latin1_swedish_ci" | Yes |  |  |
| postcode6 | VARCHAR(6) COLLATE "latin1_swedish_ci" | Yes |  |  |
| county | VARCHAR(20) COLLATE "latin1_swedish_ci" | No |  |  |
| town | VARCHAR(50) COLLATE "latin1_swedish_ci" | No |  |  |
| available_ind | CHAR(1) COLLATE "latin1_swedish_ci" | Yes |  |  |
| archived_ind | CHAR(1) COLLATE "latin1_swedish_ci" | Yes |  |  |
| archived_date | DATE | Yes |  |  |
| country_id | SMALLINT | No |  |  |
| uk_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| short_description | TEXT COLLATE "latin1_swedish_ci" | No |  |  |
| long_description | TEXT COLLATE "latin1_swedish_ci" | No |  |  |
| encoded_hints | TEXT COLLATE "latin1_swedish_ci" | No |  |  |
| guid | VARCHAR(36) COLLATE "latin1_swedish_ci" | No |  |  |
| problem_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |
| process_xml_timestamp | TIMESTAMP | Yes |  |  |
| process_xml_warning | VARCHAR(20) COLLATE "latin1_swedish_ci" | No |  |  |
| process_web_timestamp | TIMESTAMP | Yes |  |  |
| process_web_warning | VARCHAR(20) COLLATE "latin1_swedish_ci" | No |  |  |
| update_xml_timestamp | TIMESTAMP | Yes |  |  |
| update_web_timestamp | TIMESTAMP | Yes |  |  |
| update_xml_auditid | MEDIUMINT | No |  |  |
| changed_timestamp | TIMESTAMP | Yes |  |  |
| crt_timestamp | TIMESTAMP | Yes |  |  |
### coord2county

**Rows:** 35,247

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| osgb_eastings | MEDIUMINT | No |  | ✅ |
| osgb_northings | MEDIUMINT | No |  | ✅ |
| county_id | TINYINT | No |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "osgb_eastings": 54900,
    "osgb_northings": 780256,
    "county_id": 49,
    "upd_timestamp": "2012-07-28 16:04:51"
  },
  {
    "osgb_eastings": 54903,
    "osgb_northings": 780255,
    "county_id": 49,
    "upd_timestamp": "2012-07-29 16:05:54"
  },
  {
    "osgb_eastings": 57032,
    "osgb_northings": 780143,
    "county_id": 49,
    "upd_timestamp": "2012-07-28 15:51:03"
  }
]
```

### county

**Rows:** 72

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | TINYINT | No |  | ✅ |
| name | CHAR(50) COLLATE "latin1_swedish_ci" | No |  |  |
| country | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| type | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| pop | INTEGER | No |  |  |
| hectares | INTEGER | No |  |  |
| coast_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| grey | TINYINT | No |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "name": "Avon",
    "country": "E",
    "type": "C",
    "pop": 963000,
    "hectares": 129307,
    "coast_ind": "Y",
    "grey": 2
  },
  {
    "id": 2,
    "name": "Bedfordshire",
    "country": "E",
    "type": "C",
    "pop": 535400,
    "hectares": 123443,
    "coast_ind": "N",
    "grey": 4
  },
  {
    "id": 3,
    "name": "Berkshire",
    "country": "E",
    "type": "C",
    "pop": 759500,
    "hectares": 125888,
    "coast_ind": "N",
    "grey": 6
  }
]
```

### nearest

**Rows:** 72

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | MEDIUMINT | No |  | ✅ |
| user_id | MEDIUMINT | No |  |  |
| osgb_eastings | MEDIUMINT | No |  |  |
| osgb_northings | MEDIUMINT | No |  |  |
| osgb_gridref | VARCHAR(14) COLLATE "latin1_swedish_ci" | No |  |  |
| comment | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| url | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "user_id": 1,
    "osgb_eastings": 405000,
    "osgb_northings": 372998,
    "osgb_gridref": "SK 05000 72998",
    "comment": "Buxton",
    "url": "http://www.geocacheuk.com/",
    "upd_timestamp": "2003-06-23 14:55:02"
  },
  {
    "id": 2,
    "user_id": 1,
    "osgb_eastings": 514999,
    "osgb_northings": 206998,
    "osgb_gridref": "TL 14999 06998",
    "comment": "St Albans",
    "url": "http://www.trigpointinguk.com",
    "upd_timestamp": "2003-06-23 14:56:06"
  },
  {
    "id": 4,
    "user_id": 1,
    "osgb_eastings": 412200,
    "osgb_northings": 434500,
    "osgb_gridref": "SE 12200 34500",
    "comment": "Somewhere new",
    "url": "http://www.google.com",
    "upd_timestamp": "2003-06-23 15:35:43"
  }
]
```

### os_net_web

**Rows:** 844

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| stn_number | VARCHAR(14) COLLATE "utf8mb3_general_ci" | Yes |  |  |
| os_net_web_id | INTEGER | Yes |  |  |

#### Sample Data
```json
[
  {
    "stn_number": "H2NJ9409",
    "os_net_web_id": 609
  },
  {
    "stn_number": "H1NJ9605",
    "os_net_web_id": 354
  },
  {
    "stn_number": "H2SO3214",
    "os_net_web_id": 620
  }
]
```

### percentile

**Rows:** 0

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| type | CHAR(6) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| percent | TINYINT | No |  | ✅ |
| value | DECIMAL(6, 2) | No |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |
### place

**Rows:** 39,134

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| type | CHAR(6) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| name | CHAR(50) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| addr1 | CHAR(50) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| addr2 | CHAR(50) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| addr3 | CHAR(50) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| addr4 | CHAR(50) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| addr5 | CHAR(50) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| addr6 | CHAR(50) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| postcode8 | CHAR(8) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| phone | CHAR(15) COLLATE "latin1_swedish_ci" | No |  |  |
| wgs_lat | DECIMAL(6, 5) | No |  |  |
| wgs_long | DECIMAL(6, 5) | No |  |  |
| osgb_eastings | MEDIUMINT | No |  |  |
| osgb_northings | MEDIUMINT | No |  |  |
| osgb_gridref | CHAR(14) COLLATE "latin1_swedish_ci" | No |  |  |

#### Sample Data
```json
[
  {
    "type": "MWAY",
    "name": "M1 Junction 1",
    "addr1": "",
    "addr2": "",
    "addr3": "",
    "addr4": "",
    "addr5": "",
    "addr6": "",
    "postcode8": "",
    "phone": "",
    "wgs_lat": "0.00000",
    "wgs_long": "0.00000",
    "osgb_eastings": 522780,
    "osgb_northings": 187560,
    "osgb_gridref": "TQ 22780 87560"
  },
  {
    "type": "MWAY",
    "name": "M1 Junction 10",
    "addr1": "",
    "addr2": "",
    "addr3": "",
    "addr4": "",
    "addr5": "",
    "addr6": "",
    "postcode8": "",
    "phone": "",
    "wgs_lat": "0.00000",
    "wgs_long": "0.00000",
    "osgb_eastings": 508668,
    "osgb_northings": 218409,
    "osgb_gridref": "TL 08668 18409"
  },
  {
    "type": "MWAY",
    "name": "M1 Junction 11",
    "addr1": "",
    "addr2": "",
    "addr3": "",
    "addr4": "",
    "addr5": "",
    "addr6": "",
    "postcode8": "",
    "phone": "",
    "wgs_lat": "0.00000",
    "wgs_long": "0.00000",
    "osgb_eastings": 505393,
    "osgb_northings": 222814,
    "osgb_gridref": "TL 05393 22814"
  }
]
```

### postcode6

**Rows:** 8,481

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| code | CHAR(6) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| code4 | CHAR(4) COLLATE "latin1_swedish_ci" | No |  |  |
| wgs_lat | DECIMAL(6, 5) | No |  |  |
| wgs_long | DECIMAL(6, 5) | No |  |  |
| osgb_eastings | MEDIUMINT | No |  |  |
| osgb_northings | MEDIUMINT | No |  |  |
| osgb_gridref | CHAR(14) COLLATE "latin1_swedish_ci" | No |  |  |
| county | CHAR(20) COLLATE "latin1_swedish_ci" | No |  |  |
| town | CHAR(50) COLLATE "latin1_swedish_ci" | No |  |  |
| postal_town | CHAR(50) COLLATE "latin1_swedish_ci" | No |  |  |

#### Sample Data
```json
[
  {
    "code": "AB1 0",
    "code4": "AB1",
    "wgs_lat": "9.99999",
    "wgs_long": "-2.26172",
    "osgb_eastings": 384240,
    "osgb_northings": 800680,
    "osgb_gridref": "NJ 84240 00680",
    "county": "Grampian Region",
    "town": "ABERDEEN",
    "postal_town": "ABERDEEN"
  },
  {
    "code": "AB1 1",
    "code4": "AB1",
    "wgs_lat": "9.99999",
    "wgs_long": "-2.11531",
    "osgb_eastings": 393120,
    "osgb_northings": 805640,
    "osgb_gridref": "NJ 93120 05640",
    "county": "Grampian Region",
    "town": "ABERDEEN",
    "postal_town": "ABERDEEN"
  },
  {
    "code": "AB1 2",
    "code4": "AB1",
    "wgs_lat": "9.99999",
    "wgs_long": "-2.10340",
    "osgb_eastings": 393840,
    "osgb_northings": 805640,
    "osgb_gridref": "NJ 93840 05640",
    "county": "Grampian Region",
    "town": "ABERDEEN",
    "postal_town": "ABERDEEN"
  }
]
```

### postcode8

**Rows:** 54,552

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| code | CHAR(8) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| osgb_eastings | MEDIUMINT | No |  |  |
| osgb_northings | MEDIUMINT | No |  |  |
| source | CHAR(20) COLLATE "latin1_swedish_ci" | No |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "code": " \t NG884",
    "osgb_eastings": 280465,
    "osgb_northings": 871775,
    "source": "Multimap",
    "upd_timestamp": "2010-04-28 15:33:30"
  },
  {
    "code": "",
    "osgb_eastings": 530142,
    "osgb_northings": 180561,
    "source": "Multimap",
    "upd_timestamp": "2009-09-19 18:53:00"
  },
  {
    "code": "    SK13",
    "osgb_eastings": 402440,
    "osgb_northings": 394654,
    "source": "Streetmap",
    "upd_timestamp": "2006-07-24 11:36:28"
  }
]
```

### route_item

**Rows:** 0

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| route_id | MEDIUMINT | No |  |  |
| routeitem_id | MEDIUMINT | No |  | ✅ |
| osgb_eastings | MEDIUMINT | No |  |  |
| osgb_northings | MEDIUMINT | No |  |  |
### server

**Rows:** 3

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | MEDIUMINT | No |  | ✅ |
| url | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| path | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| name | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "url": "http://trigpointinguk-photos.s3.amazonaws.com/",
    "path": "trigpointinguk-photos",
    "name": "Amazon S3"
  },
  {
    "id": 2,
    "url": "http://www.trigpointinguk.com/photos/",
    "path": "/home/trigpoin/public_html/photos/",
    "name": "EUK Server"
  },
  {
    "id": 3,
    "url": "http://trigpointinguk-test.s3.amazonaws.com/",
    "path": "trigpointinguk-test",
    "name": "Amazon S3 Test"
  }
]
```

### sms

**Rows:** 518

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | MEDIUMINT | No |  | ✅ |
| in_keyword | VARCHAR(20) COLLATE "latin1_swedish_ci" | No |  |  |
| in_message | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| in_sender | VARCHAR(12) COLLATE "latin1_swedish_ci" | No |  |  |
| in_time | VARCHAR(19) COLLATE "latin1_swedish_ci" | No |  |  |
| user_id | MEDIUMINT | No |  |  |
| proc_sql | TEXT COLLATE "latin1_swedish_ci" | No |  |  |
| proc_debug1 | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| proc_debug2 | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| out_message | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| out_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| out_error | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "in_keyword": "trig",
    "in_message": " tq1865173160 LT",
    "in_sender": "447932761671",
    "in_time": "2003-05-04 19:39:38",
    "user_id": 0,
    "proc_sql": "\t\tSELECT DISTINCT\n\t\t\t   trig.osgb_gridref\n\t\t     , trig.physical_type\n\t\t\t , coalesce(logu.user_id = 18, 0) as log_user\n\t\t\t , count(distinct(logo.id)) as log_count\n\t\tFROM trig\n\t\t\t left outer join log logu on trig.id = logu.trig_id and logu.user_id = 18\n\t\t\t left outer join log logo on trig.id = logo.trig_id\n\t\t \n\t\tGROUP BY trig.osgb_gridref\n\t\t       , trig.physical_type\n\t\t\t   , log_user\n\t\tORDER BY pow(trig.osgb_eastings - 518651,2) + pow(trig.osgb_northings - 173160,2)\n\t\tLIMIT 0,10\n",
    "proc_debug1": "",
    "proc_debug2": "",
    "out_message": "Trigs near TQ186731\nTQ18657316 P*\nTQ16967319 O*\nTQ18216332 P?\nTQ17808406 P?\nTQ16188438 P*\nTQ30346881 P?\nTQ12108410 P?\nTQ16676036 P?\nTQ30627838 A\nTQ19308736 P?\n",
    "out_ind": "N",
    "out_error": "Test facility - no SMS sent.  Reply would have been:\n Trigs near TQ186731\nTQ18657316 P*\nTQ16967319 O*\nTQ18216332 P?\nTQ17808406 P?\nTQ16188438 P*\nTQ30346881 P?\nTQ12108410 P?\nTQ16676036 P?\nTQ30627838 A\nTQ19308736 P?\n",
    "upd_timestamp": "2003-05-04 11:52:25"
  },
  {
    "id": 2,
    "in_keyword": "trig",
    "in_message": " su972774",
    "in_sender": "447876648764",
    "in_time": "2003-05-05 21:40:22",
    "user_id": 0,
    "proc_sql": "\t\tSELECT DISTINCT\n\t\t\t   trig.osgb_gridref\n\t\t     , trig.physical_type\n\t\t\t , coalesce(logu.user_id = 1, 0) as log_user\n\t\t\t , count(distinct(logo.id)) as log_count\n\t\tFROM trig\n\t\t\t left outer join log logu on trig.id = logu.trig_id and logu.user_id = 1\n\t\t\t left outer join log logo on trig.id = logo.trig_id\n\t\tWHERE  logu.user_id is null  \n\t\tGROUP BY trig.osgb_gridref\n\t\t       , trig.physical_type\n\t\t\t   , log_user\n\t\tORDER BY pow(trig.osgb_eastings - 497200,2) + pow(trig.osgb_northings - 177400,2)\n\t\tLIMIT 0,10\n",
    "proc_debug1": "",
    "proc_debug2": "",
    "out_message": "Trigs near SU972774\nSU97377757 O?\nSU97307697 F?\nSU99417215 P?\nSU87527656 P?\nSU87108261 P?\nSU86958444 P?\nSU97266479 P?\nSU97246478 O?\nSU82408110 P?\nTQ12108410 P?\n",
    "out_ind": "Y",
    "out_error": "",
    "upd_timestamp": "2003-05-05 13:53:26"
  },
  {
    "id": 3,
    "in_keyword": "trig",
    "in_message": " se246241",
    "in_sender": "447876648764",
    "in_time": "2003-05-07 18:31:13",
    "user_id": 0,
    "proc_sql": "\t\tSELECT DISTINCT\n\t\t\t   trig.osgb_gridref\n\t\t     , trig.physical_type\n\t\t\t , coalesce(logu.user_id = 1, 0) as log_user\n\t\t\t , count(distinct(logo.id)) as log_count\n\t\tFROM trig\n\t\t\t left outer join log logu on trig.id = logu.trig_id and logu.user_id = 1\n\t\t\t left outer join log logo on trig.id = logo.trig_id\n\t\tWHERE  logu.user_id is null  \n\t\tGROUP BY trig.osgb_gridref\n\t\t       , trig.physical_type\n\t\t\t   , log_user\n\t\tORDER BY pow(trig.osgb_eastings - 424600,2) + pow(trig.osgb_northings - 424100,2)\n\t\tLIMIT 0,10\n",
    "proc_debug1": "",
    "proc_debug2": "",
    "out_message": "Trigs near SE246241\nSE25942435 P\nSE22062469 P\nSE21652164 P?\nSE28092609 P\nSE27142089 P\nSE20582270 P\nSE24841928 P\nSE26171921 P\nSE28222801 P?\nSE24722944 P?\n",
    "out_ind": "Y",
    "out_error": "",
    "upd_timestamp": "2003-05-07 10:44:30"
  }
]
```

### status

**Rows:** 7

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | INTEGER | No |  | ✅ |
| name | CHAR(20) COLLATE "latin1_swedish_ci" | No |  |  |
| descr | VARCHAR(50) COLLATE "latin1_swedish_ci" | No |  |  |
| limit_descr | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |

#### Sample Data
```json
[
  {
    "id": 10,
    "name": "Pillar",
    "descr": "Hotine, Vanessa or Stone Pillar",
    "limit_descr": "Pillars only"
  },
  {
    "id": 20,
    "name": "Major mark",
    "descr": "Substantial structures installed by the OS",
    "limit_descr": "Pillars, FBMs, Curry Stools and similar"
  },
  {
    "id": 30,
    "name": "Minor mark",
    "descr": "Small marks installed by the OS",
    "limit_descr": "Pillars, FBMs, Bolts, Blocks etc.  No Intersected."
  }
]
```

### tlog

**Rows:** 468,414

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | MEDIUMINT | No |  | ✅ |
| trig_id | MEDIUMINT | No |  |  |
| user_id | MEDIUMINT | No |  |  |
| date | DATE | No |  |  |
| time | TIME | No |  |  |
| osgb_eastings | MEDIUMINT | No |  |  |
| osgb_northings | MEDIUMINT | No |  |  |
| osgb_gridref | VARCHAR(14) COLLATE "latin1_swedish_ci" | No |  |  |
| fb_number | VARCHAR(10) COLLATE "latin1_swedish_ci" | No |  |  |
| condition | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| comment | TEXT COLLATE "latin1_swedish_ci" | No |  |  |
| score | TINYINT | No |  |  |
| ip_addr | VARCHAR(15) COLLATE "latin1_swedish_ci" | No |  |  |
| source | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "trig_id": 2588,
    "user_id": 1,
    "date": "2002-09-08",
    "time": "20:21:00",
    "osgb_eastings": 434443,
    "osgb_northings": 355423,
    "osgb_gridref": "SK 34443 55423",
    "fb_number": "",
    "condition": "G",
    "comment": "Near to cache GC598C.  The photo on the home page was taken here.",
    "score": 7,
    "ip_addr": "62.49.6.31",
    "source": "W",
    "upd_timestamp": "2003-04-18 12:23:17"
  },
  {
    "id": 2,
    "trig_id": 1406,
    "user_id": 1,
    "date": "2003-03-29",
    "time": "14:00:00",
    "osgb_eastings": 406260,
    "osgb_northings": 377020,
    "osgb_gridref": "SK 06260 77020",
    "fb_number": "S2775",
    "condition": "G",
    "comment": "Shown on landranger maps, but not the more recent Outdoor Leisure series.  It's still there, though!",
    "score": 7,
    "ip_addr": "62.49.6.31",
    "source": "W",
    "upd_timestamp": "2003-04-18 12:36:45"
  },
  {
    "id": 3,
    "trig_id": 3980,
    "user_id": 1,
    "date": "2003-02-07",
    "time": "16:00:00",
    "osgb_eastings": 0,
    "osgb_northings": 0,
    "osgb_gridref": "",
    "fb_number": "",
    "condition": "G",
    "comment": "Delightful bit of bogtrotting!  Did it as geocache GC7D9F.",
    "score": 6,
    "ip_addr": "62.49.6.31",
    "source": "W",
    "upd_timestamp": "2003-04-26 11:55:02"
  }
]
```

### town

**Rows:** 1,915

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| name | CHAR(25) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| wgs_lat | DECIMAL(6, 5) | No |  |  |
| wgs_long | DECIMAL(6, 5) | No |  |  |
| osgb_eastings | MEDIUMINT | No |  |  |
| osgb_northings | MEDIUMINT | No |  |  |
| osgb_gridref | CHAR(14) COLLATE "latin1_swedish_ci" | No |  |  |

#### Sample Data
```json
[
  {
    "name": "ABBY WOOD",
    "wgs_lat": "9.99999",
    "wgs_long": "-0.11310",
    "osgb_eastings": 546799,
    "osgb_northings": 178900,
    "osgb_gridref": "TQ 46799 78900"
  },
  {
    "name": "ABERAERON",
    "wgs_lat": "9.99999",
    "wgs_long": "4.27123",
    "osgb_eastings": 245000,
    "osgb_northings": 261999,
    "osgb_gridref": "SN 45000 61999"
  },
  {
    "name": "ABERCHIRDER",
    "wgs_lat": "9.99999",
    "wgs_long": "2.63668",
    "osgb_eastings": 361999,
    "osgb_northings": 851999,
    "osgb_gridref": "NJ 61999 51999"
  }
]
```

### tphoto

**Rows:** 402,671

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | MEDIUMINT | No |  | ✅ |
| tlog_id | MEDIUMINT | No |  |  |
| server_id | MEDIUMINT | No |  |  |
| type | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| filename | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| filesize | INTEGER | No |  |  |
| height | MEDIUMINT | No |  |  |
| width | MEDIUMINT | No |  |  |
| icon_filename | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| icon_filesize | INTEGER | No |  |  |
| icon_height | MEDIUMINT | No |  |  |
| icon_width | MEDIUMINT | No |  |  |
| name | VARCHAR(80) COLLATE "latin1_swedish_ci" | No |  |  |
| text_desc | TEXT COLLATE "latin1_swedish_ci" | No |  |  |
| ip_addr | VARCHAR(15) COLLATE "latin1_swedish_ci" | No |  |  |
| public_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| deleted_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| source | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| crt_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "tlog_id": 1,
    "server_id": 1,
    "type": "T",
    "filename": "000/P00001.jpg",
    "filesize": 63418,
    "height": 480,
    "width": 640,
    "icon_filename": "000/I00001.jpg",
    "icon_filesize": 6058,
    "icon_height": 90,
    "icon_width": 120,
    "name": "GPSr on the trigpoint",
    "text_desc": "",
    "ip_addr": "62.49.6.31",
    "public_ind": "Y",
    "deleted_ind": "N",
    "source": "W",
    "crt_timestamp": "2009-12-24 10:55:55"
  },
  {
    "id": 2,
    "tlog_id": 6,
    "server_id": 1,
    "type": "O",
    "filename": "000/P00002.jpg",
    "filesize": 96480,
    "height": 480,
    "width": 640,
    "icon_filename": "000/I00002.jpg",
    "icon_filesize": 4538,
    "icon_height": 90,
    "icon_width": 120,
    "name": "Hang gliding at Mam Tor",
    "text_desc": "",
    "ip_addr": "62.49.6.31",
    "public_ind": "Y",
    "deleted_ind": "N",
    "source": "W",
    "crt_timestamp": "2009-12-24 10:55:55"
  },
  {
    "id": 4,
    "tlog_id": 23,
    "server_id": 1,
    "type": "T",
    "filename": "000/P00004.jpg",
    "filesize": 77868,
    "height": 636,
    "width": 482,
    "icon_filename": "000/I00004.jpg",
    "icon_filesize": 8049,
    "icon_height": 120,
    "icon_width": 91,
    "name": "The Pillar",
    "text_desc": "Liverpool in the distance",
    "ip_addr": "81.86.215.227",
    "public_ind": "Y",
    "deleted_ind": "N",
    "source": "W",
    "crt_timestamp": "2009-12-24 10:55:55"
  }
]
```

### tphotoclass

**Rows:** 5,292

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | MEDIUMINT | No |  | ✅ |
| photo_class | TINYINT | No |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "photo_class": 10
  },
  {
    "id": 2,
    "photo_class": 4
  },
  {
    "id": 4,
    "photo_class": 3
  }
]
```

### tphotostats

**Rows:** 0

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | MEDIUMINT | No |  | ✅ |
| score_mean | DECIMAL(5, 2) | No |  |  |
| score_baysian | DECIMAL(5, 2) | No |  |  |
| logged_count | SMALLINT | No |  |  |
### tphotovote

**Rows:** 94,832

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | MEDIUMINT | No |  | ✅ |
| tphoto_id | MEDIUMINT | No |  |  |
| user_id | MEDIUMINT | No |  |  |
| score | TINYINT | No |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "tphoto_id": 3279,
    "user_id": 844,
    "score": 2,
    "upd_timestamp": "2004-09-25 04:51:27"
  },
  {
    "id": 2,
    "tphoto_id": 7784,
    "user_id": 844,
    "score": 4,
    "upd_timestamp": "2004-09-25 04:51:27"
  },
  {
    "id": 3,
    "tphoto_id": 4328,
    "user_id": 844,
    "score": -2,
    "upd_timestamp": "2004-09-25 04:51:27"
  }
]
```

### tquery

**Rows:** 2,456,719

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | MEDIUMINT | No |  | ✅ |
| type | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| text | TEXT COLLATE "latin1_swedish_ci" | No |  |  |
| sql_from | TEXT COLLATE "latin1_swedish_ci" | No |  |  |
| sql_where | TEXT COLLATE "latin1_swedish_ci" | No |  |  |
| sql_having | TEXT COLLATE "latin1_swedish_ci" | No |  |  |
| sql_order | TEXT COLLATE "latin1_swedish_ci" | No |  |  |
| osgb_eastings | MEDIUMINT | No |  |  |
| osgb_northings | MEDIUMINT | No |  |  |
| user_id | MEDIUMINT | Yes |  |  |
| system_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |
| crt_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "type": "T",
    "text": "trigpoints, near to BUXTON",
    "sql_from": "",
    "sql_where": "",
    "sql_having": "",
    "sql_order": " pow(trig.osgb_eastings - 405000,2) + pow(trig.osgb_northings - 372998,2) ",
    "osgb_eastings": 405000,
    "osgb_northings": 372998,
    "user_id": 1,
    "system_ind": "N",
    "upd_timestamp": "2025-03-10 13:30:58",
    "crt_timestamp": "0000-00-00 00:00:00"
  },
  {
    "id": 2,
    "type": "T",
    "text": "highest scored trigpoints",
    "sql_from": " inner join trigstats on trig.id = trigstats.id ",
    "sql_where": "",
    "sql_having": "",
    "sql_order": " trigstats.score_baysian desc",
    "osgb_eastings": 0,
    "osgb_northings": 0,
    "user_id": 1,
    "system_ind": "Y",
    "upd_timestamp": "2025-08-20 02:46:56",
    "crt_timestamp": "0000-00-00 00:00:00"
  },
  {
    "id": 3,
    "type": "T",
    "text": "trigpoint records needing attention from an admin",
    "sql_from": "",
    "sql_where": "trig.needs_attention <> 0",
    "sql_having": "",
    "sql_order": "trig.needs_attention desc, trig.id desc",
    "osgb_eastings": 0,
    "osgb_northings": 0,
    "user_id": 1,
    "system_ind": "Y",
    "upd_timestamp": "2025-08-19 21:36:01",
    "crt_timestamp": "2011-10-10 12:11:54"
  }
]
```

### tquizscores

**Rows:** 3,277

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | MEDIUMINT | No |  | ✅ |
| trig_id | MEDIUMINT | No |  |  |
| photo_id | MEDIUMINT | No |  |  |
| result | VARCHAR(5) COLLATE "latin1_swedish_ci" | No |  |  |
| correct | ENUM | No |  |  |
| user_id | MEDIUMINT | No |  |  |
| Game | CHAR(2) COLLATE "latin1_swedish_ci" | No |  |  |
| crt_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "trig_id": 3428,
    "photo_id": 11627,
    "result": "",
    "correct": "-",
    "user_id": 844,
    "Game": "A3",
    "crt_timestamp": "2005-03-03 16:20:47"
  },
  {
    "id": 2,
    "trig_id": 4216,
    "photo_id": 13413,
    "result": "4216",
    "correct": "Y",
    "user_id": 844,
    "Game": "A3",
    "crt_timestamp": "2005-03-03 16:20:47"
  },
  {
    "id": 3,
    "trig_id": 2492,
    "photo_id": 9609,
    "result": "2492",
    "correct": "Y",
    "user_id": 844,
    "Game": "A3",
    "crt_timestamp": "2005-03-03 16:20:47"
  }
]
```

### trig

**Rows:** 25,810

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | MEDIUMINT | No |  | ✅ |
| waypoint | VARCHAR(8) COLLATE "latin1_swedish_ci" | No |  |  |
| name | VARCHAR(50) COLLATE "latin1_swedish_ci" | No |  |  |
| status_id | INTEGER | No |  |  |
| user_added | TINYINT | No |  |  |
| current_use | VARCHAR(25) COLLATE "latin1_swedish_ci" | No |  |  |
| historic_use | VARCHAR(30) COLLATE "latin1_swedish_ci" | No |  |  |
| physical_type | VARCHAR(25) COLLATE "latin1_swedish_ci" | No |  |  |
| wgs_lat | DECIMAL(7, 5) | No |  |  |
| wgs_long | DECIMAL(7, 5) | No |  |  |
| wgs_height | MEDIUMINT | No |  |  |
| osgb_eastings | MEDIUMINT | No |  |  |
| osgb_northings | MEDIUMINT | No |  |  |
| osgb_gridref | VARCHAR(14) COLLATE "latin1_swedish_ci" | No |  |  |
| osgb_height | MEDIUMINT | No |  |  |
| fb_number | VARCHAR(10) COLLATE "latin1_swedish_ci" | No |  |  |
| stn_number | VARCHAR(20) COLLATE "latin1_swedish_ci" | No |  |  |
| stn_number_active | VARCHAR(20) COLLATE "latin1_swedish_ci" | Yes |  |  |
| stn_number_passive | VARCHAR(20) COLLATE "latin1_swedish_ci" | Yes |  |  |
| stn_number_osgb36 | VARCHAR(20) COLLATE "latin1_swedish_ci" | Yes |  |  |
| os_net_web_id | INTEGER | Yes |  |  |
| permission_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| condition | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| postcode6 | VARCHAR(6) COLLATE "latin1_swedish_ci" | No |  |  |
| county | VARCHAR(20) COLLATE "latin1_swedish_ci" | No |  |  |
| town | VARCHAR(50) COLLATE "latin1_swedish_ci" | No |  |  |
| needs_attention | TINYINT | No |  |  |
| attention_comment | TEXT COLLATE "latin1_swedish_ci" | No |  |  |
| crt_date | DATE | No |  |  |
| crt_time | TIME | No |  |  |
| crt_user_id | MEDIUMINT | No |  |  |
| crt_ip_addr | VARCHAR(15) COLLATE "latin1_swedish_ci" | No |  |  |
| admin_user_id | MEDIUMINT | Yes |  |  |
| admin_timestamp | TIMESTAMP | Yes |  |  |
| admin_ip_addr | VARCHAR(15) COLLATE "latin1_swedish_ci" | Yes |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "waypoint": "TP0001",
    "name": "Fetlar",
    "status_id": 10,
    "user_added": 0,
    "current_use": "Passive station",
    "historic_use": "Primary",
    "physical_type": "Pillar",
    "wgs_lat": "60.62023",
    "wgs_long": "-0.86480",
    "wgs_height": 208,
    "osgb_eastings": 462229,
    "osgb_northings": 1193521,
    "osgb_gridref": "HU 62229 93521",
    "osgb_height": 159,
    "fb_number": "S4928",
    "stn_number": "B1HU6293",
    "stn_number_active": null,
    "stn_number_passive": "B1HU6293",
    "stn_number_osgb36": null,
    "os_net_web_id": 836,
    "permission_ind": "Y",
    "condition": "G",
    "postcode6": "ZE2 9",
    "county": "Shetland",
    "town": "",
    "needs_attention": 0,
    "attention_comment": "",
    "crt_date": "2003-04-02",
    "crt_time": "14:56:28",
    "crt_user_id": 0,
    "crt_ip_addr": "",
    "admin_user_id": null,
    "admin_timestamp": null,
    "admin_ip_addr": null,
    "upd_timestamp": "2014-07-10 11:37:14"
  },
  {
    "id": 2,
    "waypoint": "TP0002",
    "name": "An Cuaidh",
    "status_id": 10,
    "user_added": 0,
    "current_use": "Passive station",
    "historic_use": "Primary",
    "physical_type": "Pillar",
    "wgs_lat": "57.83566",
    "wgs_long": "-5.76663",
    "wgs_height": 352,
    "osgb_eastings": 176500,
    "osgb_northings": 889127,
    "osgb_gridref": "NG 76500 89127",
    "osgb_height": 297,
    "fb_number": "S6119",
    "stn_number": "B1NG7689",
    "stn_number_active": null,
    "stn_number_passive": "B1NG7689",
    "stn_number_osgb36": "PP373",
    "os_net_web_id": 339,
    "permission_ind": "Y",
    "condition": "G",
    "postcode6": "IV21 2",
    "county": "Highland Region",
    "town": "",
    "needs_attention": 0,
    "attention_comment": "15 May 2014 21:06:57 - Teasel - trigpointing@teasel.org - 15 May 2014 20:57:03 - Teasel - trigpointing@teasel.org - fsdafdsfsdfa",
    "crt_date": "2003-04-02",
    "crt_time": "14:56:30",
    "crt_user_id": 0,
    "crt_ip_addr": "",
    "admin_user_id": 1,
    "admin_timestamp": "2014-05-15 21:06:57",
    "admin_ip_addr": "87.127.168.137",
    "upd_timestamp": "2014-06-05 19:12:03"
  },
  {
    "id": 3,
    "waypoint": "TP0003",
    "name": "Barra Differential",
    "status_id": 30,
    "user_added": 0,
    "current_use": "Passive station",
    "historic_use": "Other",
    "physical_type": "Bolt",
    "wgs_lat": "56.96243",
    "wgs_long": "-7.43001",
    "wgs_height": 83,
    "osgb_eastings": 70095,
    "osgb_northings": 798813,
    "osgb_gridref": "NL 70095 98813",
    "osgb_height": 26,
    "fb_number": "",
    "stn_number": "B1NL7098",
    "stn_number_active": null,
    "stn_number_passive": "B1NL7098",
    "stn_number_osgb36": null,
    "os_net_web_id": 342,
    "permission_ind": "Y",
    "condition": "Q",
    "postcode6": "PA80 5",
    "county": "Western Isles",
    "town": "",
    "needs_attention": 0,
    "attention_comment": "",
    "crt_date": "2003-04-02",
    "crt_time": "14:56:32",
    "crt_user_id": 0,
    "crt_ip_addr": "",
    "admin_user_id": 11551,
    "admin_timestamp": "2017-08-20 22:43:24",
    "admin_ip_addr": "86.2.13.81",
    "upd_timestamp": "2017-08-20 22:43:24"
  }
]
```

### trigdata

**Rows:** 7,314

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | INTEGER | No |  | ✅ |
| near1 | INTEGER | No |  |  |
| near2 | INTEGER | No |  |  |
| near3 | INTEGER | No |  |  |
| near4 | INTEGER | No |  |  |
| near5 | INTEGER | No |  |  |
| near10 | INTEGER | No |  |  |
| near15 | INTEGER | No |  |  |
| near20 | INTEGER | No |  |  |
| near100 | INTEGER | No |  |  |
| near1000 | INTEGER | No |  |  |
| mwayjtn | VARCHAR(10) COLLATE "latin1_swedish_ci" | No |  |  |
| mwaydist | INTEGER | No |  |  |
| aroaddist | INTEGER | No |  |  |
| aroade | MEDIUMINT | No |  |  |
| aroadn | MEDIUMINT | No |  |  |
| area_osgb_height | INTEGER | No |  |  |
| osgb_height_dif | INTEGER | No |  |  |
| trackdist | INTEGER | No |  |  |
| tracke | MEDIUMINT | No |  |  |
| trackn | MEDIUMINT | No |  |  |
| broaddist | INTEGER | No |  |  |
| broade | MEDIUMINT | No |  |  |
| broadn | MEDIUMINT | No |  |  |
| croaddist | INTEGER | No |  |  |
| croadn | MEDIUMINT | No |  |  |
| croade | MEDIUMINT | No |  |  |
| countryside | DOUBLE | No |  |  |
| woodland | DOUBLE | No |  |  |
| urban | DOUBLE | No |  |  |
| stndist | INTEGER | No |  |  |
| stne | MEDIUMINT | No |  |  |
| stnn | MEDIUMINT | No |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "near1": 3592,
    "near2": 8553,
    "near3": 14112,
    "near4": 20958,
    "near5": 27839,
    "near10": 84598,
    "near15": 160551,
    "near20": 256716,
    "near100": 7457147,
    "near1000": 356866295,
    "mwayjtn": "M90-11",
    "mwaydist": 495249,
    "aroaddist": 2100,
    "aroade": 461102,
    "aroadn": 1191749,
    "area_osgb_height": 131,
    "osgb_height_dif": 28,
    "trackdist": 271901,
    "tracke": 311279,
    "trackn": 967370,
    "broaddist": 2148,
    "broade": 461500,
    "broadn": 1191500,
    "croaddist": 2659,
    "croadn": 1191500,
    "croade": 460500,
    "countryside": 99.68,
    "woodland": 0.0,
    "urban": 0.0,
    "stndist": 272557,
    "stne": 329156,
    "stnn": 955657
  },
  {
    "id": 2,
    "near1": 5081,
    "near2": 10281,
    "near3": 16477,
    "near4": 24044,
    "near5": 34781,
    "near10": 93405,
    "near15": 169717,
    "near20": 276746,
    "near100": 3761914,
    "near1000": 126580739,
    "mwayjtn": "M90-11",
    "mwaydist": 212216,
    "aroaddist": 3873,
    "aroade": 173991,
    "aroadn": 886176,
    "area_osgb_height": 267,
    "osgb_height_dif": 30,
    "trackdist": 46914,
    "tracke": 199605,
    "trackn": 848296,
    "broaddist": 3301,
    "broade": 174500,
    "broadn": 886500,
    "croaddist": 1067,
    "croadn": 889500,
    "croade": 175500,
    "countryside": 95.27,
    "woodland": 4.73,
    "urban": 0.0,
    "stndist": 47003,
    "stne": 200280,
    "stnn": 848583
  },
  {
    "id": 3,
    "near1": 2363,
    "near2": 7305,
    "near3": 12560,
    "near4": 18777,
    "near5": 26602,
    "near10": 80629,
    "near15": 176161,
    "near20": 321119,
    "near100": 6019782,
    "near1000": 160914688,
    "mwayjtn": "M8-31",
    "mwaydist": 211656,
    "aroaddist": 840,
    "aroade": 69947,
    "aroadn": 799640,
    "area_osgb_height": 1,
    "osgb_height_dif": 25,
    "trackdist": 96546,
    "tracke": 166014,
    "trackn": 787823,
    "broaddist": 16293,
    "broade": 74500,
    "broadn": 814500,
    "croaddist": 672,
    "croadn": 798500,
    "croade": 69500,
    "countryside": 7.85,
    "woodland": 0.0,
    "urban": 0.0,
    "stndist": 98197,
    "stne": 168099,
    "stnn": 792645
  }
]
```

### trigdatafields

**Rows:** 32

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| field | VARCHAR(20) COLLATE "latin1_swedish_ci" | No |  | ✅ |
| field_group | VARCHAR(20) COLLATE "latin1_swedish_ci" | No |  |  |
| field_enabled | ENUM | No |  |  |
| multipler | DOUBLE | No |  |  |
| description | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| description_low | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| description_high | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| includes_position | VARCHAR(20) COLLATE "latin1_swedish_ci" | No |  |  |
| data_source | VARCHAR(10) COLLATE "latin1_swedish_ci" | No |  |  |
| explanation | VARCHAR(64) COLLATE "latin1_swedish_ci" | No |  |  |

#### Sample Data
```json
[
  {
    "field": "area_osgb_height",
    "field_group": "height",
    "field_enabled": "y",
    "multipler": 0.089605735,
    "description": "Height",
    "description_low": "Areas of Low Altitude",
    "description_high": "Areas of High Altitude",
    "includes_position": "",
    "data_source": "os",
    "explanation": "Average Area Height"
  },
  {
    "field": "aroaddist",
    "field_group": "aroad",
    "field_enabled": "y",
    "multipler": 0.001388833,
    "description": "to A Roads",
    "description_low": "Near",
    "description_high": "Far",
    "includes_position": "en",
    "data_source": "dcw",
    "explanation": "Distance to Nearest A Road"
  },
  {
    "field": "aroade",
    "field_group": "",
    "field_enabled": "",
    "multipler": 0.0,
    "description": "",
    "description_low": "",
    "description_high": "",
    "includes_position": "",
    "data_source": "",
    "explanation": ""
  }
]
```

### trigstats

**Rows:** 25,066

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | MEDIUMINT | No |  | ✅ |
| logged_first | DATE | No |  |  |
| logged_last | DATE | No |  |  |
| logged_count | MEDIUMINT | No |  |  |
| found_last | DATE | No |  |  |
| found_count | MEDIUMINT | No |  |  |
| photo_count | MEDIUMINT | No |  |  |
| score_mean | DECIMAL(5, 2) | No |  |  |
| score_baysian | DECIMAL(5, 2) | No |  |  |
| area_osgb_height | SMALLINT | No |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "id": 0,
    "logged_first": "0000-00-00",
    "logged_last": "0000-00-00",
    "logged_count": 0,
    "found_last": "0000-00-00",
    "found_count": 0,
    "photo_count": 0,
    "score_mean": "5.57",
    "score_baysian": "0.00",
    "area_osgb_height": 0,
    "upd_timestamp": "2025-03-18 10:31:33"
  },
  {
    "id": 1,
    "logged_first": "2001-08-20",
    "logged_last": "2024-06-07",
    "logged_count": 22,
    "found_last": "2024-06-07",
    "found_count": 19,
    "photo_count": 23,
    "score_mean": "6.50",
    "score_baysian": "6.46",
    "area_osgb_height": 0,
    "upd_timestamp": "2025-03-08 17:01:41"
  },
  {
    "id": 2,
    "logged_first": "2000-07-04",
    "logged_last": "2025-08-12",
    "logged_count": 31,
    "found_last": "2025-08-12",
    "found_count": 23,
    "photo_count": 16,
    "score_mean": "6.48",
    "score_baysian": "6.46",
    "area_osgb_height": 0,
    "upd_timestamp": "2025-08-16 10:23:39"
  }
]
```

### tuserstats

**Rows:** 0

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| user_id | INTEGER | No |  | ✅ |
| avg_visits | FLOAT | No |  |  |
### twatch

**Rows:** 5

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| user_id | MEDIUMINT | No |  | ✅ |
| trig_id | MEDIUMINT | No |  | ✅ |
| email_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |
| crt_timestamp | TIMESTAMP | Yes |  |  |

#### Sample Data
```json
[
  {
    "user_id": 1,
    "trig_id": 2448,
    "email_ind": "",
    "upd_timestamp": "2004-06-25 21:58:54",
    "crt_timestamp": "2004-06-25 21:41:42"
  },
  {
    "user_id": 1,
    "trig_id": 3229,
    "email_ind": "",
    "upd_timestamp": "2004-06-25 21:39:57",
    "crt_timestamp": "2004-06-25 21:39:57"
  },
  {
    "user_id": 844,
    "trig_id": 577,
    "email_ind": "",
    "upd_timestamp": "2004-08-05 21:23:05",
    "crt_timestamp": "2004-08-05 21:23:05"
  }
]
```

### user

**Rows:** 14,682

#### Columns
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | MEDIUMINT | No |  | ✅ |
| cacher_id | MEDIUMINT | No |  |  |
| name | VARCHAR(30) COLLATE "latin1_swedish_ci" | No |  |  |
| firstname | VARCHAR(30) COLLATE "latin1_swedish_ci" | No |  |  |
| surname | VARCHAR(30) COLLATE "latin1_swedish_ci" | No |  |  |
| email | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| email_challenge | VARCHAR(34) COLLATE "latin1_swedish_ci" | No |  |  |
| email_valid | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| email_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| homepage | VARCHAR(255) COLLATE "latin1_swedish_ci" | No |  |  |
| distance_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| about | TEXT COLLATE "latin1_swedish_ci" | No |  |  |
| status_max | INTEGER | No |  |  |
| home1_name | VARCHAR(20) COLLATE "latin1_swedish_ci" | No |  |  |
| home1_eastings | MEDIUMINT | No |  |  |
| home1_northings | MEDIUMINT | No |  |  |
| home1_gridref | VARCHAR(14) COLLATE "latin1_swedish_ci" | No |  |  |
| home2_name | VARCHAR(20) COLLATE "latin1_swedish_ci" | No |  |  |
| home2_eastings | MEDIUMINT | No |  |  |
| home2_northings | MEDIUMINT | No |  |  |
| home2_gridref | VARCHAR(14) COLLATE "latin1_swedish_ci" | No |  |  |
| home3_name | VARCHAR(20) COLLATE "latin1_swedish_ci" | No |  |  |
| home3_eastings | MEDIUMINT | No |  |  |
| home3_northings | MEDIUMINT | No |  |  |
| home3_gridref | VARCHAR(14) COLLATE "latin1_swedish_ci" | No |  |  |
| album_rows | TINYINT | No |  |  |
| album_cols | TINYINT | No |  |  |
| public_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| sms_number | VARCHAR(12) COLLATE "latin1_swedish_ci" | Yes |  |  |
| sms_credit | MEDIUMINT | No |  |  |
| sms_grace | TINYINT | No |  |  |
| cryptpw | VARCHAR(34) COLLATE "latin1_swedish_ci" | No |  |  |
| cacher_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| trigger_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| admin_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| crt_date | DATE | No |  |  |
| crt_time | TIME | No |  |  |
| upd_timestamp | TIMESTAMP | Yes |  |  |
| disclaimer_ind | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| disclaimer_timestamp | TIMESTAMP | Yes |  |  |
| nearest_max_m | INTEGER | No |  |  |
| online_map_type | VARCHAR(10) COLLATE "latin1_swedish_ci" | No |  |  |
| online_map_type2 | VARCHAR(10) COLLATE "latin1_swedish_ci" | No |  |  |
| trigmap_b | TINYINT | No |  |  |
| trigmap_l | TINYINT | No |  |  |
| trigmap_c | TINYINT | No |  |  |
| showscores | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |
| showhandi | CHAR(1) COLLATE "latin1_swedish_ci" | No |  |  |

#### Sample Data
```json
[
  {
    "id": 1,
    "cacher_id": 43129,
    "name": "Teasel",
    "firstname": "Ian",
    "surname": "Harris",
    "email": "trigpointinguk@teasel.org",
    "email_challenge": "",
    "email_valid": "Y",
    "email_ind": "O",
    "homepage": "http://https://trigpointing.uk",
    "distance_ind": "K",
    "about": "Coder for TrigpointingUK's website",
    "status_max": 20,
    "home1_name": "home",
    "home1_eastings": 534403,
    "home1_northings": 272179,
    "home1_gridref": "TL 34403 72179",
    "home2_name": "Speyside",
    "home2_eastings": 289934,
    "home2_northings": 810748,
    "home2_gridref": "NH 89934 10748",
    "home3_name": "Wittering",
    "home3_eastings": 477984,
    "home3_northings": 98498,
    "home3_gridref": "SZ 77984 98498",
    "album_rows": 2,
    "album_cols": 4,
    "public_ind": "N",
    "sms_number": "447876648764",
    "sms_credit": 9,
    "sms_grace": 5,
    "cryptpw": "$1$mVjX7zy0$kIoKygviJYxgT49FPnuqY.",
    "cacher_ind": "Y",
    "trigger_ind": "Y",
    "admin_ind": "Y",
    "crt_date": "2003-04-18",
    "crt_time": "13:07:49",
    "upd_timestamp": "2022-08-15 21:57:52",
    "disclaimer_ind": "Y",
    "disclaimer_timestamp": "2003-04-18 13:07:49",
    "nearest_max_m": 10,
    "online_map_type": "mm25kl",
    "online_map_type2": "ge",
    "trigmap_b": 0,
    "trigmap_l": 0,
    "trigmap_c": 1,
    "showscores": "Y",
    "showhandi": "Y"
  },
  {
    "id": 2,
    "cacher_id": 2918,
    "name": "John Stead",
    "firstname": "John",
    "surname": "Stead",
    "email": "jstead@bigfoot.com",
    "email_challenge": "",
    "email_valid": "Y",
    "email_ind": "O",
    "homepage": "",
    "distance_ind": "M",
    "about": "",
    "status_max": 0,
    "home1_name": "Home",
    "home1_eastings": 348600,
    "home1_northings": 396000,
    "home1_gridref": "SJ 48600 96000",
    "home2_name": "work",
    "home2_eastings": 0,
    "home2_northings": 0,
    "home2_gridref": "",
    "home3_name": "",
    "home3_eastings": 0,
    "home3_northings": 0,
    "home3_gridref": "",
    "album_rows": 2,
    "album_cols": 4,
    "public_ind": "Y",
    "sms_number": "",
    "sms_credit": 0,
    "sms_grace": 5,
    "cryptpw": "$1$4X7BYm.S$18p8tgau4qDbofjrl89fC1",
    "cacher_ind": "Y",
    "trigger_ind": "Y",
    "admin_ind": "N",
    "crt_date": "2003-04-18",
    "crt_time": "15:47:50",
    "upd_timestamp": "2008-12-26 22:27:01",
    "disclaimer_ind": "Y",
    "disclaimer_timestamp": "2003-04-18 15:47:50",
    "nearest_max_m": 50000,
    "online_map_type": "",
    "online_map_type2": "lla",
    "trigmap_b": 3,
    "trigmap_l": 0,
    "trigmap_c": 0,
    "showscores": "Y",
    "showhandi": "Y"
  },
  {
    "id": 3,
    "cacher_id": 53091,
    "name": "subarite",
    "firstname": "Andy",
    "surname": "",
    "email": "amalbon@enterprise.net",
    "email_challenge": "",
    "email_valid": "Y",
    "email_ind": "N",
    "homepage": "",
    "distance_ind": "M",
    "about": "",
    "status_max": 0,
    "home1_name": "subarite",
    "home1_eastings": 452100,
    "home1_northings": 167972,
    "home1_gridref": "SU 52100 67972",
    "home2_name": "",
    "home2_eastings": 0,
    "home2_northings": 0,
    "home2_gridref": "",
    "home3_name": "",
    "home3_eastings": 0,
    "home3_northings": 0,
    "home3_gridref": "",
    "album_rows": 2,
    "album_cols": 4,
    "public_ind": "",
    "sms_number": null,
    "sms_credit": 0,
    "sms_grace": 5,
    "cryptpw": "$1$H5qbI8/H$cZOhfq5nIbqF1YpDkM8KM0",
    "cacher_ind": "Y",
    "trigger_ind": "Y",
    "admin_ind": "N",
    "crt_date": "2003-04-18",
    "crt_time": "16:35:11",
    "upd_timestamp": "2005-10-04 04:04:26",
    "disclaimer_ind": "Y",
    "disclaimer_timestamp": "2003-04-18 16:35:11",
    "nearest_max_m": 50000,
    "online_map_type": "sm25k",
    "online_map_type2": "lla",
    "trigmap_b": 1,
    "trigmap_l": 0,
    "trigmap_c": 0,
    "showscores": "Y",
    "showhandi": "Y"
  }
]
```
