# Database Schema Documentation

**Database:** trigpoin_trigs
**Export Date:** 2025-08-22 00:06:18.288963
**Total Tables:** 21

## Table Overview

- **OSGBIW**: 31,518 rows, 15 columns

- **attr**: 14 rows, 12 columns
- **attrset**: 31,518 rows, 5 columns
- **attrset_attrval**: 441,252 rows, 3 columns
- **attrsource**: 2 rows, 6 columns
- **attrval**: 142,930 rows, 8 columns






- **server**: 3 rows, 4 columns

- **status**: 7 rows, 4 columns
- **tlog**: 468,414 rows, 15 columns
- **town**: 1,915 rows, 6 columns
- **tphoto**: 402,671 rows, 19 columns


- **tphotovote**: 94,832 rows, 5 columns

- **trig**: 25,810 rows, 36 columns


- **trigstats**: 25,066 rows, 11 columns


- **user**: 14,682 rows, 55 columns

## Detailed Table Schemas


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
