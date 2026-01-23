--
-- PostgreSQL database dump
--

\restrict hB2nvUvJVxpfMD8vh4QIS29eqfrjdUFhlk1ihBhDWQlaPCAZhy7Y39SghgWSXR5

-- Dumped from database version 16.10
-- Dumped by pg_dump version 17.7 (Ubuntu 17.7-0ubuntu0.25.10.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_cron; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION pg_cron; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_cron IS 'Job scheduler for PostgreSQL';


--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


--
-- Name: set_upd_timestamp_utc(); Type: FUNCTION; Schema: public; Owner: fastapi_production
--

CREATE FUNCTION public.set_upd_timestamp_utc() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NEW.upd_timestamp IS NULL THEN
                    NEW.upd_timestamp := timezone('utc', clock_timestamp());
                END IF;
                RETURN NEW;
            END IF;

            -- TG_OP = 'UPDATE'
            IF NEW.upd_timestamp IS DISTINCT FROM OLD.upd_timestamp THEN
                -- Respect explicit upd_timestamp changes (e.g. data backfills).
                RETURN NEW;
            END IF;

            NEW.upd_timestamp := timezone('utc', clock_timestamp());
            RETURN NEW;
        END;
        $$;


ALTER FUNCTION public.set_upd_timestamp_utc() OWNER TO fastapi_production;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO fastapi_production;

--
-- Name: area; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.area (
    id integer NOT NULL,
    area_type_id integer NOT NULL,
    code character varying(50),
    name character varying(255) NOT NULL,
    boundary public.geography(MultiPolygon,4326) NOT NULL,
    parent_id integer,
    properties text
);


ALTER TABLE public.area OWNER TO fastapi_production;

--
-- Name: area_id_seq; Type: SEQUENCE; Schema: public; Owner: fastapi_production
--

CREATE SEQUENCE public.area_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.area_id_seq OWNER TO fastapi_production;

--
-- Name: area_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: fastapi_production
--

ALTER SEQUENCE public.area_id_seq OWNED BY public.area.id;


--
-- Name: area_type; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.area_type (
    id integer NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    source_url character varying(500),
    parent_type_id integer
);


ALTER TABLE public.area_type OWNER TO fastapi_production;

--
-- Name: area_type_id_seq; Type: SEQUENCE; Schema: public; Owner: fastapi_production
--

CREATE SEQUENCE public.area_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.area_type_id_seq OWNER TO fastapi_production;

--
-- Name: area_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: fastapi_production
--

ALTER SEQUENCE public.area_type_id_seq OWNED BY public.area_type.id;


--
-- Name: attr; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.attr (
    id integer NOT NULL,
    attrsource_id integer,
    name character varying(45),
    description character varying(255),
    mandatory smallint,
    multivalued smallint,
    grouped smallint DEFAULT 1,
    sort_order integer DEFAULT 99,
    style character varying(45),
    url_javaclass character varying(45),
    type character varying(45),
    upd_timestamp timestamp without time zone DEFAULT timezone('utc'::text, clock_timestamp())
);


ALTER TABLE public.attr OWNER TO fastapi_production;

--
-- Name: attr_id_seq; Type: SEQUENCE; Schema: public; Owner: fastapi_production
--

CREATE SEQUENCE public.attr_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.attr_id_seq OWNER TO fastapi_production;

--
-- Name: attr_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: fastapi_production
--

ALTER SEQUENCE public.attr_id_seq OWNED BY public.attr.id;


--
-- Name: attrset; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.attrset (
    id integer NOT NULL,
    trig_id integer,
    attrsource_id integer,
    sort_order integer,
    upd_timestamp timestamp without time zone DEFAULT timezone('utc'::text, clock_timestamp())
);


ALTER TABLE public.attrset OWNER TO fastapi_production;

--
-- Name: attrset_attrval; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.attrset_attrval (
    attrset_id integer NOT NULL,
    attrval_id integer NOT NULL,
    upd_timestamp timestamp without time zone DEFAULT timezone('utc'::text, clock_timestamp())
);


ALTER TABLE public.attrset_attrval OWNER TO fastapi_production;

--
-- Name: attrset_id_seq; Type: SEQUENCE; Schema: public; Owner: fastapi_production
--

CREATE SEQUENCE public.attrset_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.attrset_id_seq OWNER TO fastapi_production;

--
-- Name: attrset_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: fastapi_production
--

ALTER SEQUENCE public.attrset_id_seq OWNED BY public.attrset.id;


--
-- Name: attrsource; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.attrsource (
    id integer NOT NULL,
    name character varying(50),
    descr text,
    url character varying(255),
    sort_order integer,
    crt_timestamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.attrsource OWNER TO fastapi_production;

--
-- Name: attrval; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.attrval (
    id integer NOT NULL,
    attr_id integer,
    value_string character varying(255),
    value_double double precision,
    value_bool smallint,
    value_point text,
    group_name character varying(255),
    upd_timestamp timestamp without time zone DEFAULT timezone('utc'::text, clock_timestamp())
);


ALTER TABLE public.attrval OWNER TO fastapi_production;

--
-- Name: attrval_id_seq; Type: SEQUENCE; Schema: public; Owner: fastapi_production
--

CREATE SEQUENCE public.attrval_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.attrval_id_seq OWNER TO fastapi_production;

--
-- Name: attrval_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: fastapi_production
--

ALTER SEQUENCE public.attrval_id_seq OWNED BY public.attrval.id;


--
-- Name: condition; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.condition (
    code character(1) NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(255),
    icon_file character varying(100),
    trig_colour character varying(20),
    log_colour character varying(20),
    similar_codes character varying(10),
    wiki_url character varying(255),
    sort_order smallint NOT NULL
);


ALTER TABLE public.condition OWNER TO fastapi_production;

--
-- Name: postcodes; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.postcodes (
    code character varying(10) NOT NULL,
    lat numeric(10,7),
    long numeric(11,7),
    location public.geography(Point,4326) NOT NULL
);


ALTER TABLE public.postcodes OWNER TO fastapi_production;

--
-- Name: server; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.server (
    id integer DEFAULT 0 NOT NULL,
    url character varying(255) DEFAULT ''::character varying,
    path character varying(255) DEFAULT ''::character varying,
    name character varying(255) DEFAULT ''::character varying
);


ALTER TABLE public.server OWNER TO fastapi_production;

--
-- Name: status; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.status (
    id integer NOT NULL,
    name character(20),
    descr character varying(50),
    limit_descr character varying(255)
);


ALTER TABLE public.status OWNER TO fastapi_production;

--
-- Name: tlog; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.tlog (
    id integer NOT NULL,
    trig_id integer DEFAULT 0,
    user_id integer DEFAULT 0,
    date date,
    "time" time without time zone,
    osgb_eastings integer,
    osgb_northings integer,
    osgb_gridref character varying(14),
    fb_number character varying(10) DEFAULT ''::character varying,
    condition character(1) DEFAULT ''::bpchar,
    comment text,
    score smallint DEFAULT 5,
    ip_addr character varying(15) DEFAULT ''::character varying,
    source character(1) DEFAULT 'W'::bpchar,
    upd_timestamp timestamp without time zone DEFAULT timezone('utc'::text, clock_timestamp())
);


ALTER TABLE public.tlog OWNER TO fastapi_production;

--
-- Name: tlog_id_seq; Type: SEQUENCE; Schema: public; Owner: fastapi_production
--

CREATE SEQUENCE public.tlog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tlog_id_seq OWNER TO fastapi_production;

--
-- Name: tlog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: fastapi_production
--

ALTER SEQUENCE public.tlog_id_seq OWNED BY public.tlog.id;


--
-- Name: town; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.town (
    name character(25) DEFAULT ''::bpchar NOT NULL,
    wgs_lat numeric(9,6) DEFAULT 0.00000,
    wgs_long numeric(9,6) DEFAULT 0.00000,
    osgb_eastings integer DEFAULT 0,
    osgb_northings integer DEFAULT 0,
    osgb_gridref character(14) DEFAULT ''::bpchar,
    location public.geography(Point,4326)
);


ALTER TABLE public.town OWNER TO fastapi_production;

--
-- Name: tphoto; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.tphoto (
    id integer NOT NULL,
    tlog_id integer DEFAULT 0,
    server_id integer DEFAULT 0,
    type character(1) DEFAULT ''::bpchar,
    filename character varying(255) DEFAULT ''::character varying,
    filesize integer DEFAULT 0,
    height integer DEFAULT 0,
    width integer DEFAULT 0,
    icon_filename character varying(255) DEFAULT ''::character varying,
    icon_filesize integer DEFAULT 0,
    icon_height integer DEFAULT 0,
    icon_width integer DEFAULT 0,
    name character varying(80) DEFAULT ''::character varying,
    text_desc text,
    ip_addr character varying(15) DEFAULT ''::character varying,
    public_ind character(1) DEFAULT 'N'::bpchar,
    deleted_ind character(1) DEFAULT 'N'::bpchar,
    source character(1) DEFAULT 'W'::bpchar,
    crt_timestamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.tphoto OWNER TO fastapi_production;

--
-- Name: tphoto_id_seq; Type: SEQUENCE; Schema: public; Owner: fastapi_production
--

CREATE SEQUENCE public.tphoto_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tphoto_id_seq OWNER TO fastapi_production;

--
-- Name: tphoto_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: fastapi_production
--

ALTER SEQUENCE public.tphoto_id_seq OWNED BY public.tphoto.id;


--
-- Name: tphotovote; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.tphotovote (
    id integer NOT NULL,
    tphoto_id integer DEFAULT 0,
    user_id integer DEFAULT 0,
    score smallint DEFAULT 0,
    upd_timestamp timestamp without time zone DEFAULT timezone('utc'::text, clock_timestamp())
);


ALTER TABLE public.tphotovote OWNER TO fastapi_production;

--
-- Name: tphotovote_id_seq; Type: SEQUENCE; Schema: public; Owner: fastapi_production
--

CREATE SEQUENCE public.tphotovote_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tphotovote_id_seq OWNER TO fastapi_production;

--
-- Name: tphotovote_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: fastapi_production
--

ALTER SEQUENCE public.tphotovote_id_seq OWNED BY public.tphotovote.id;


--
-- Name: trig; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.trig (
    id integer NOT NULL,
    waypoint character varying(8) DEFAULT ''::character varying,
    name character varying(50) DEFAULT ''::character varying,
    status_id integer DEFAULT 0,
    user_added smallint DEFAULT 0,
    current_use character varying(25) DEFAULT ''::character varying,
    historic_use character varying(30) DEFAULT ''::character varying,
    wgs_lat numeric(7,5) DEFAULT 0.00000,
    wgs_long numeric(7,5) DEFAULT 0.00000,
    wgs_height integer DEFAULT '-1'::integer,
    osgb_eastings integer DEFAULT 0,
    osgb_northings integer DEFAULT 0,
    osgb_gridref character varying(14) DEFAULT ''::character varying,
    osgb_height integer DEFAULT '-1'::integer,
    fb_number character varying(10) DEFAULT ''::character varying,
    stn_number character varying(20) DEFAULT ''::character varying,
    stn_number_active character varying(20),
    stn_number_passive character varying(20),
    stn_number_osgb36 character varying(20),
    permission_ind character(1) DEFAULT ''::bpchar,
    condition character(1) DEFAULT ''::bpchar,
    postcode character varying(10),
    county character varying(20) DEFAULT ''::character varying,
    town character varying(50) DEFAULT ''::character varying,
    needs_attention smallint DEFAULT 0,
    attention_comment text,
    crt_date date,
    crt_time time without time zone,
    crt_user_id integer DEFAULT 0,
    crt_ip_addr character varying(15) DEFAULT ''::character varying,
    admin_user_id integer,
    admin_timestamp timestamp without time zone,
    admin_ip_addr character varying(15),
    upd_timestamp timestamp without time zone DEFAULT timezone('utc'::text, clock_timestamp()),
    location public.geography(Point,4326),
    type_id integer,
    legal_message text
);


ALTER TABLE public.trig OWNER TO fastapi_production;

--
-- Name: COLUMN trig.legal_message; Type: COMMENT; Schema: public; Owner: fastapi_production
--

COMMENT ON COLUMN public.trig.legal_message IS 'Optional legal/access message displayed on trig detail page (HTML)';


--
-- Name: trig_area_mv; Type: MATERIALIZED VIEW; Schema: public; Owner: fastapi_production
--

CREATE MATERIALIZED VIEW public.trig_area_mv AS
 SELECT t.id AS trig_id,
    a.id AS area_id,
    at.id AS area_type_id,
    at.code AS area_type_code
   FROM ((public.trig t
     CROSS JOIN public.area a)
     JOIN public.area_type at ON ((a.area_type_id = at.id)))
  WHERE ((t.location IS NOT NULL) AND public.st_covers((a.boundary)::public.geometry, (t.location)::public.geometry))
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.trig_area_mv OWNER TO fastapi_production;

--
-- Name: trig_category; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.trig_category (
    id integer NOT NULL,
    code character varying(20) NOT NULL,
    name character varying(30) NOT NULL,
    description character varying(100),
    wiki_url character varying(255),
    sort_order smallint NOT NULL
);


ALTER TABLE public.trig_category OWNER TO fastapi_production;

--
-- Name: trig_id_seq; Type: SEQUENCE; Schema: public; Owner: fastapi_production
--

CREATE SEQUENCE public.trig_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.trig_id_seq OWNER TO fastapi_production;

--
-- Name: trig_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: fastapi_production
--

ALTER SEQUENCE public.trig_id_seq OWNED BY public.trig.id;


--
-- Name: trig_type; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.trig_type (
    id integer NOT NULL,
    category_id integer NOT NULL,
    code character varying(20) NOT NULL,
    name character varying(30) NOT NULL,
    description character varying(100),
    wiki_url character varying(255),
    sort_order smallint NOT NULL,
    legacy_physical_type character varying(25)
);


ALTER TABLE public.trig_type OWNER TO fastapi_production;

--
-- Name: trig_type_group_id_seq; Type: SEQUENCE; Schema: public; Owner: fastapi_production
--

CREATE SEQUENCE public.trig_type_group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.trig_type_group_id_seq OWNER TO fastapi_production;

--
-- Name: trig_type_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: fastapi_production
--

ALTER SEQUENCE public.trig_type_group_id_seq OWNED BY public.trig_category.id;


--
-- Name: trig_type_id_seq; Type: SEQUENCE; Schema: public; Owner: fastapi_production
--

CREATE SEQUENCE public.trig_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.trig_type_id_seq OWNER TO fastapi_production;

--
-- Name: trig_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: fastapi_production
--

ALTER SEQUENCE public.trig_type_id_seq OWNED BY public.trig_type.id;


--
-- Name: trigstats; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public.trigstats (
    id integer DEFAULT 0 NOT NULL,
    logged_first date,
    logged_last date,
    logged_count integer DEFAULT 0,
    found_last date,
    found_count integer DEFAULT 0,
    photo_count integer DEFAULT 0,
    score_mean numeric(5,2) DEFAULT 0.00,
    score_baysian numeric(5,2) DEFAULT 0.00,
    upd_timestamp timestamp without time zone DEFAULT timezone('utc'::text, clock_timestamp())
);


ALTER TABLE public.trigstats OWNER TO fastapi_production;

--
-- Name: user; Type: TABLE; Schema: public; Owner: fastapi_production
--

CREATE TABLE public."user" (
    id integer NOT NULL,
    name character varying(30) DEFAULT ''::character varying,
    firstname character varying(30) DEFAULT ''::character varying,
    surname character varying(30) DEFAULT ''::character varying,
    email character varying(255) DEFAULT ''::character varying,
    email_valid character(1) DEFAULT 'N'::bpchar,
    email_ind character(1) DEFAULT 'N'::bpchar,
    homepage character varying(255) DEFAULT ''::character varying,
    distance_ind character(1) DEFAULT 'K'::bpchar,
    about text,
    public_ind character(1) DEFAULT 'N'::bpchar,
    cryptpw character varying(100) DEFAULT ''::character varying,
    crt_date date,
    crt_time time without time zone,
    upd_timestamp timestamp without time zone DEFAULT timezone('utc'::text, clock_timestamp()),
    auth0_user_id character varying(50),
    ui_prefs jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public."user" OWNER TO fastapi_production;

--
-- Name: user_activity_summary; Type: MATERIALIZED VIEW; Schema: public; Owner: fastapi_production
--

CREATE MATERIALIZED VIEW public.user_activity_summary AS
 WITH log_stats AS (
         SELECT tlog.user_id,
            count(*) AS total_logs,
            count(DISTINCT tlog.trig_id) AS total_trigs_logged
           FROM public.tlog
          GROUP BY tlog.user_id
        ), photo_counts AS (
         SELECT tl.user_id,
            count(*) AS total_photos
           FROM (public.tphoto tp
             JOIN public.tlog tl ON ((tl.id = tp.tlog_id)))
          WHERE (tp.deleted_ind <> 'Y'::bpchar)
          GROUP BY tl.user_id
        )
 SELECT u.id AS user_id,
    u.crt_date AS member_since,
    COALESCE(log_stats.total_logs, (0)::bigint) AS total_logs,
    COALESCE(log_stats.total_trigs_logged, (0)::bigint) AS total_trigs_logged,
    COALESCE(photo_counts.total_photos, (0)::bigint) AS total_photos
   FROM ((public."user" u
     LEFT JOIN log_stats ON ((log_stats.user_id = u.id)))
     LEFT JOIN photo_counts ON ((photo_counts.user_id = u.id)))
  WHERE ((COALESCE(log_stats.total_logs, (0)::bigint) > 0) OR (COALESCE(log_stats.total_trigs_logged, (0)::bigint) > 0) OR (COALESCE(photo_counts.total_photos, (0)::bigint) > 0))
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.user_activity_summary OWNER TO fastapi_production;

--
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: fastapi_production
--

CREATE SEQUENCE public.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_id_seq OWNER TO fastapi_production;

--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: fastapi_production
--

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;


--
-- Name: area id; Type: DEFAULT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.area ALTER COLUMN id SET DEFAULT nextval('public.area_id_seq'::regclass);


--
-- Name: area_type id; Type: DEFAULT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.area_type ALTER COLUMN id SET DEFAULT nextval('public.area_type_id_seq'::regclass);


--
-- Name: attr id; Type: DEFAULT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.attr ALTER COLUMN id SET DEFAULT nextval('public.attr_id_seq'::regclass);


--
-- Name: attrset id; Type: DEFAULT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.attrset ALTER COLUMN id SET DEFAULT nextval('public.attrset_id_seq'::regclass);


--
-- Name: attrval id; Type: DEFAULT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.attrval ALTER COLUMN id SET DEFAULT nextval('public.attrval_id_seq'::regclass);


--
-- Name: tlog id; Type: DEFAULT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.tlog ALTER COLUMN id SET DEFAULT nextval('public.tlog_id_seq'::regclass);


--
-- Name: tphoto id; Type: DEFAULT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.tphoto ALTER COLUMN id SET DEFAULT nextval('public.tphoto_id_seq'::regclass);


--
-- Name: tphotovote id; Type: DEFAULT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.tphotovote ALTER COLUMN id SET DEFAULT nextval('public.tphotovote_id_seq'::regclass);


--
-- Name: trig id; Type: DEFAULT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trig ALTER COLUMN id SET DEFAULT nextval('public.trig_id_seq'::regclass);


--
-- Name: trig_category id; Type: DEFAULT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trig_category ALTER COLUMN id SET DEFAULT nextval('public.trig_type_group_id_seq'::regclass);


--
-- Name: trig_type id; Type: DEFAULT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trig_type ALTER COLUMN id SET DEFAULT nextval('public.trig_type_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: area area_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.area
    ADD CONSTRAINT area_pkey PRIMARY KEY (id);


--
-- Name: area_type area_type_code_key; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.area_type
    ADD CONSTRAINT area_type_code_key UNIQUE (code);


--
-- Name: area_type area_type_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.area_type
    ADD CONSTRAINT area_type_pkey PRIMARY KEY (id);


--
-- Name: attr attr_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.attr
    ADD CONSTRAINT attr_pkey PRIMARY KEY (id);


--
-- Name: attrset_attrval attrset_attrval_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.attrset_attrval
    ADD CONSTRAINT attrset_attrval_pkey PRIMARY KEY (attrset_id, attrval_id);


--
-- Name: attrset attrset_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.attrset
    ADD CONSTRAINT attrset_pkey PRIMARY KEY (id);


--
-- Name: attrsource attrsource_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.attrsource
    ADD CONSTRAINT attrsource_pkey PRIMARY KEY (id);


--
-- Name: attrval attrval_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.attrval
    ADD CONSTRAINT attrval_pkey PRIMARY KEY (id);


--
-- Name: condition condition_name_key; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.condition
    ADD CONSTRAINT condition_name_key UNIQUE (name);


--
-- Name: condition condition_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.condition
    ADD CONSTRAINT condition_pkey PRIMARY KEY (code);


--
-- Name: postcodes postcodes_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.postcodes
    ADD CONSTRAINT postcodes_pkey PRIMARY KEY (code);


--
-- Name: server server_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.server
    ADD CONSTRAINT server_pkey PRIMARY KEY (id);


--
-- Name: status status_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.status
    ADD CONSTRAINT status_pkey PRIMARY KEY (id);


--
-- Name: tlog tlog_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.tlog
    ADD CONSTRAINT tlog_pkey PRIMARY KEY (id);


--
-- Name: town town_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.town
    ADD CONSTRAINT town_pkey PRIMARY KEY (name);


--
-- Name: tphoto tphoto_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.tphoto
    ADD CONSTRAINT tphoto_pkey PRIMARY KEY (id);


--
-- Name: tphotovote tphotovote_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.tphotovote
    ADD CONSTRAINT tphotovote_pkey PRIMARY KEY (id);


--
-- Name: trig trig_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trig
    ADD CONSTRAINT trig_pkey PRIMARY KEY (id);


--
-- Name: trig_type trig_type_code_key; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trig_type
    ADD CONSTRAINT trig_type_code_key UNIQUE (code);


--
-- Name: trig_category trig_type_group_code_key; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trig_category
    ADD CONSTRAINT trig_type_group_code_key UNIQUE (code);


--
-- Name: trig_category trig_type_group_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trig_category
    ADD CONSTRAINT trig_type_group_pkey PRIMARY KEY (id);


--
-- Name: trig_category trig_type_group_sort_order_key; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trig_category
    ADD CONSTRAINT trig_type_group_sort_order_key UNIQUE (sort_order);


--
-- Name: trig_type trig_type_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trig_type
    ADD CONSTRAINT trig_type_pkey PRIMARY KEY (id);


--
-- Name: trigstats trigstats_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trigstats
    ADD CONSTRAINT trigstats_pkey PRIMARY KEY (id);


--
-- Name: trig_type uq_trig_type_category_sort; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trig_type
    ADD CONSTRAINT uq_trig_type_category_sort UNIQUE (category_id, sort_order);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: attr_value; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX attr_value ON public.attrval USING btree (attr_id, value_string);


--
-- Name: attrsrc_trig; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX attrsrc_trig ON public.attrset USING btree (attrsource_id, trig_id);


--
-- Name: fk_attrval_attr1_idx; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX fk_attrval_attr1_idx ON public.attrval USING btree (attr_id);


--
-- Name: fk_trig_attrval_attrval1_idx; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX fk_trig_attrval_attrval1_idx ON public.attrset_attrval USING btree (attrval_id);


--
-- Name: frontpage_1; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX frontpage_1 ON public.tlog USING btree (trig_id, user_id, date, "time");


--
-- Name: frontpage_2; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX frontpage_2 ON public.tlog USING btree (date, user_id, "time", trig_id);


--
-- Name: id; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX id ON public.trig USING btree (id, name, osgb_gridref, osgb_eastings, osgb_northings);


--
-- Name: idx_code_prefix; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX idx_code_prefix ON public.postcodes USING btree (code);


--
-- Name: idx_postcodes_location; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX idx_postcodes_location ON public.postcodes USING gist (location);


--
-- Name: idx_tlog_upd_timestamp; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX idx_tlog_upd_timestamp ON public.tlog USING btree (upd_timestamp);


--
-- Name: idx_town_location_gist; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX idx_town_location_gist ON public.town USING gist (location);


--
-- Name: idx_tphoto_deleted_ind; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX idx_tphoto_deleted_ind ON public.tphoto USING btree (deleted_ind);


--
-- Name: idx_trig_location_gist; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX idx_trig_location_gist ON public.trig USING gist (location);


--
-- Name: idx_user_activity_summary_member_since_desc; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX idx_user_activity_summary_member_since_desc ON public.user_activity_summary USING btree (member_since DESC, user_id DESC);


--
-- Name: idx_user_activity_summary_photos_desc; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX idx_user_activity_summary_photos_desc ON public.user_activity_summary USING btree (total_photos DESC, user_id DESC);


--
-- Name: idx_user_activity_summary_trigs_desc; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX idx_user_activity_summary_trigs_desc ON public.user_activity_summary USING btree (total_trigs_logged DESC, user_id DESC);


--
-- Name: idx_user_activity_summary_user_id; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE UNIQUE INDEX idx_user_activity_summary_user_id ON public.user_activity_summary USING btree (user_id);


--
-- Name: idx_user_crt_date; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX idx_user_crt_date ON public."user" USING btree (crt_date);


--
-- Name: ix_area_area_type_id; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX ix_area_area_type_id ON public.area USING btree (area_type_id);


--
-- Name: ix_area_boundary_gist; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX ix_area_boundary_gist ON public.area USING gist (boundary);


--
-- Name: ix_area_code; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX ix_area_code ON public.area USING btree (code);


--
-- Name: ix_area_id; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX ix_area_id ON public.area USING btree (id);


--
-- Name: ix_area_name; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX ix_area_name ON public.area USING btree (name);


--
-- Name: ix_area_parent_id; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX ix_area_parent_id ON public.area USING btree (parent_id);


--
-- Name: ix_area_type_code; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX ix_area_type_code ON public.area_type USING btree (code);


--
-- Name: ix_area_type_id; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX ix_area_type_id ON public.area_type USING btree (id);


--
-- Name: ix_condition_sort_order; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX ix_condition_sort_order ON public.condition USING btree (sort_order);


--
-- Name: ix_tlog_user_trig; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX ix_tlog_user_trig ON public.tlog USING btree (user_id, trig_id);


--
-- Name: ix_trig_area_mv_area_id; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX ix_trig_area_mv_area_id ON public.trig_area_mv USING btree (area_id);


--
-- Name: ix_trig_area_mv_area_type_code; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX ix_trig_area_mv_area_type_code ON public.trig_area_mv USING btree (area_type_code);


--
-- Name: ix_trig_area_mv_area_type_id; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX ix_trig_area_mv_area_type_id ON public.trig_area_mv USING btree (area_type_id);


--
-- Name: ix_trig_area_mv_pk; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE UNIQUE INDEX ix_trig_area_mv_pk ON public.trig_area_mv USING btree (trig_id, area_id);


--
-- Name: ix_trig_area_mv_trig_id; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX ix_trig_area_mv_trig_id ON public.trig_area_mv USING btree (trig_id);


--
-- Name: ix_trig_type_category_id; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX ix_trig_type_category_id ON public.trig_type USING btree (category_id);


--
-- Name: ix_trig_type_id; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX ix_trig_type_id ON public.trig USING btree (type_id);


--
-- Name: osgb; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX osgb ON public.town USING btree (osgb_eastings, osgb_northings);


--
-- Name: photoid; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX photoid ON public.tphotovote USING btree (tphoto_id);


--
-- Name: tlog_id; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX tlog_id ON public.tphoto USING btree (tlog_id);


--
-- Name: userid_trigid; Type: INDEX; Schema: public; Owner: fastapi_production
--

CREATE INDEX userid_trigid ON public.tlog USING btree (user_id, trig_id);


--
-- Name: attr set_upd_timestamp_utc; Type: TRIGGER; Schema: public; Owner: fastapi_production
--

CREATE TRIGGER set_upd_timestamp_utc BEFORE INSERT OR UPDATE ON public.attr FOR EACH ROW EXECUTE FUNCTION public.set_upd_timestamp_utc();


--
-- Name: attrset set_upd_timestamp_utc; Type: TRIGGER; Schema: public; Owner: fastapi_production
--

CREATE TRIGGER set_upd_timestamp_utc BEFORE INSERT OR UPDATE ON public.attrset FOR EACH ROW EXECUTE FUNCTION public.set_upd_timestamp_utc();


--
-- Name: attrset_attrval set_upd_timestamp_utc; Type: TRIGGER; Schema: public; Owner: fastapi_production
--

CREATE TRIGGER set_upd_timestamp_utc BEFORE INSERT OR UPDATE ON public.attrset_attrval FOR EACH ROW EXECUTE FUNCTION public.set_upd_timestamp_utc();


--
-- Name: attrval set_upd_timestamp_utc; Type: TRIGGER; Schema: public; Owner: fastapi_production
--

CREATE TRIGGER set_upd_timestamp_utc BEFORE INSERT OR UPDATE ON public.attrval FOR EACH ROW EXECUTE FUNCTION public.set_upd_timestamp_utc();


--
-- Name: tlog set_upd_timestamp_utc; Type: TRIGGER; Schema: public; Owner: fastapi_production
--

CREATE TRIGGER set_upd_timestamp_utc BEFORE INSERT OR UPDATE ON public.tlog FOR EACH ROW EXECUTE FUNCTION public.set_upd_timestamp_utc();


--
-- Name: tphotovote set_upd_timestamp_utc; Type: TRIGGER; Schema: public; Owner: fastapi_production
--

CREATE TRIGGER set_upd_timestamp_utc BEFORE INSERT OR UPDATE ON public.tphotovote FOR EACH ROW EXECUTE FUNCTION public.set_upd_timestamp_utc();


--
-- Name: trig set_upd_timestamp_utc; Type: TRIGGER; Schema: public; Owner: fastapi_production
--

CREATE TRIGGER set_upd_timestamp_utc BEFORE INSERT OR UPDATE ON public.trig FOR EACH ROW EXECUTE FUNCTION public.set_upd_timestamp_utc();


--
-- Name: trigstats set_upd_timestamp_utc; Type: TRIGGER; Schema: public; Owner: fastapi_production
--

CREATE TRIGGER set_upd_timestamp_utc BEFORE INSERT OR UPDATE ON public.trigstats FOR EACH ROW EXECUTE FUNCTION public.set_upd_timestamp_utc();


--
-- Name: user set_upd_timestamp_utc; Type: TRIGGER; Schema: public; Owner: fastapi_production
--

CREATE TRIGGER set_upd_timestamp_utc BEFORE INSERT OR UPDATE ON public."user" FOR EACH ROW EXECUTE FUNCTION public.set_upd_timestamp_utc();


--
-- Name: area area_area_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.area
    ADD CONSTRAINT area_area_type_id_fkey FOREIGN KEY (area_type_id) REFERENCES public.area_type(id);


--
-- Name: area area_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.area
    ADD CONSTRAINT area_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.area(id);


--
-- Name: area_type area_type_parent_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.area_type
    ADD CONSTRAINT area_type_parent_type_id_fkey FOREIGN KEY (parent_type_id) REFERENCES public.area_type(id);


--
-- Name: attr fk_attr_attrsource_id__attrsource_id; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.attr
    ADD CONSTRAINT fk_attr_attrsource_id__attrsource_id FOREIGN KEY (attrsource_id) REFERENCES public.attrsource(id) ON DELETE RESTRICT;


--
-- Name: attrset fk_attrset_attrsource_id__attrsource_id; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.attrset
    ADD CONSTRAINT fk_attrset_attrsource_id__attrsource_id FOREIGN KEY (attrsource_id) REFERENCES public.attrsource(id) ON DELETE RESTRICT;


--
-- Name: attrset_attrval fk_attrset_attrval_attrset_id__attrset_id; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.attrset_attrval
    ADD CONSTRAINT fk_attrset_attrval_attrset_id__attrset_id FOREIGN KEY (attrset_id) REFERENCES public.attrset(id) ON DELETE RESTRICT;


--
-- Name: attrset_attrval fk_attrset_attrval_attrval_id__attrval_id; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.attrset_attrval
    ADD CONSTRAINT fk_attrset_attrval_attrval_id__attrval_id FOREIGN KEY (attrval_id) REFERENCES public.attrval(id) ON DELETE RESTRICT;


--
-- Name: attrset fk_attrset_trig_id__trig_id; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.attrset
    ADD CONSTRAINT fk_attrset_trig_id__trig_id FOREIGN KEY (trig_id) REFERENCES public.trig(id) ON DELETE RESTRICT;


--
-- Name: attrval fk_attrval_attr_id__attr_id; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.attrval
    ADD CONSTRAINT fk_attrval_attr_id__attr_id FOREIGN KEY (attr_id) REFERENCES public.attr(id) ON DELETE RESTRICT;


--
-- Name: tlog fk_tlog_trig_id__trig_id; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.tlog
    ADD CONSTRAINT fk_tlog_trig_id__trig_id FOREIGN KEY (trig_id) REFERENCES public.trig(id) ON DELETE SET NULL;


--
-- Name: tlog fk_tlog_user_id__user_id; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.tlog
    ADD CONSTRAINT fk_tlog_user_id__user_id FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: tphoto fk_tphoto_server_id__server_id; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.tphoto
    ADD CONSTRAINT fk_tphoto_server_id__server_id FOREIGN KEY (server_id) REFERENCES public.server(id) ON DELETE SET NULL;


--
-- Name: tphoto fk_tphoto_tlog_id__tlog_id; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.tphoto
    ADD CONSTRAINT fk_tphoto_tlog_id__tlog_id FOREIGN KEY (tlog_id) REFERENCES public.tlog(id) ON DELETE SET NULL;


--
-- Name: tphotovote fk_tphotovote_tphoto_id__tphoto_id; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.tphotovote
    ADD CONSTRAINT fk_tphotovote_tphoto_id__tphoto_id FOREIGN KEY (tphoto_id) REFERENCES public.tphoto(id) ON DELETE CASCADE;


--
-- Name: tphotovote fk_tphotovote_user_id__user_id; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.tphotovote
    ADD CONSTRAINT fk_tphotovote_user_id__user_id FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: trig fk_trig_admin_user_id__user_id; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trig
    ADD CONSTRAINT fk_trig_admin_user_id__user_id FOREIGN KEY (admin_user_id) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: trig fk_trig_crt_user_id__user_id; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trig
    ADD CONSTRAINT fk_trig_crt_user_id__user_id FOREIGN KEY (crt_user_id) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: trig fk_trig_postcode_postcodes; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trig
    ADD CONSTRAINT fk_trig_postcode_postcodes FOREIGN KEY (postcode) REFERENCES public.postcodes(code) ON DELETE SET NULL;


--
-- Name: trig fk_trig_status_id__status_id; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trig
    ADD CONSTRAINT fk_trig_status_id__status_id FOREIGN KEY (status_id) REFERENCES public.status(id) ON DELETE SET NULL;


--
-- Name: trigstats fk_trigstats_id__trig_id; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trigstats
    ADD CONSTRAINT fk_trigstats_id__trig_id FOREIGN KEY (id) REFERENCES public.trig(id) ON DELETE CASCADE;


--
-- Name: trig_type trig_type_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trig_type
    ADD CONSTRAINT trig_type_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.trig_category(id);


--
-- Name: trig trig_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: fastapi_production
--

ALTER TABLE ONLY public.trig
    ADD CONSTRAINT trig_type_id_fkey FOREIGN KEY (type_id) REFERENCES public.trig_type(id);


--
-- Name: SCHEMA cron; Type: ACL; Schema: -; Owner: rds_superuser
--

GRANT USAGE ON SCHEMA cron TO fastapi_production;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO fastapi_production;
GRANT USAGE ON SCHEMA public TO backups;


--
-- Name: TABLE job; Type: ACL; Schema: cron; Owner: rds_superuser
--

REVOKE SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE cron.job FROM rdsadmin;
REVOKE SELECT ON TABLE cron.job FROM PUBLIC;
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE cron.job TO rds_superuser;
GRANT SELECT ON TABLE cron.job TO PUBLIC;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE cron.job TO fastapi_production;


--
-- Name: TABLE job_run_details; Type: ACL; Schema: cron; Owner: rds_superuser
--

REVOKE SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE cron.job_run_details FROM rdsadmin;
REVOKE SELECT,DELETE ON TABLE cron.job_run_details FROM PUBLIC;
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE cron.job_run_details TO rds_superuser;
GRANT SELECT,DELETE ON TABLE cron.job_run_details TO PUBLIC;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE cron.job_run_details TO fastapi_production;


--
-- Name: TABLE alembic_version; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.alembic_version TO backups;


--
-- Name: TABLE area; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.area TO backups;


--
-- Name: TABLE area_type; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.area_type TO backups;


--
-- Name: TABLE attr; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.attr TO backups;


--
-- Name: TABLE attrset; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.attrset TO backups;


--
-- Name: TABLE attrset_attrval; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.attrset_attrval TO backups;


--
-- Name: TABLE attrsource; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.attrsource TO backups;


--
-- Name: TABLE attrval; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.attrval TO backups;


--
-- Name: TABLE condition; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.condition TO backups;


--
-- Name: TABLE postcodes; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.postcodes TO backups;


--
-- Name: TABLE server; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.server TO backups;


--
-- Name: TABLE status; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.status TO backups;


--
-- Name: TABLE tlog; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.tlog TO backups;


--
-- Name: TABLE town; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.town TO backups;


--
-- Name: TABLE tphoto; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.tphoto TO backups;


--
-- Name: TABLE tphotovote; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.tphotovote TO backups;


--
-- Name: TABLE trig; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.trig TO backups;


--
-- Name: TABLE trig_area_mv; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.trig_area_mv TO backups;


--
-- Name: TABLE trig_category; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.trig_category TO backups;


--
-- Name: TABLE trig_type; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.trig_type TO backups;


--
-- Name: TABLE trigstats; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.trigstats TO backups;


--
-- Name: TABLE "user"; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public."user" TO backups;


--
-- Name: TABLE user_activity_summary; Type: ACL; Schema: public; Owner: fastapi_production
--

GRANT SELECT ON TABLE public.user_activity_summary TO backups;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: fastapi_production
--

ALTER DEFAULT PRIVILEGES FOR ROLE fastapi_production IN SCHEMA public GRANT ALL ON SEQUENCES TO fastapi_production;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: fastapi_production
--

ALTER DEFAULT PRIVILEGES FOR ROLE fastapi_production IN SCHEMA public GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLES TO fastapi_production;
ALTER DEFAULT PRIVILEGES FOR ROLE fastapi_production IN SCHEMA public GRANT SELECT ON TABLES TO backups;


--
-- PostgreSQL database dump complete
--

\unrestrict hB2nvUvJVxpfMD8vh4QIS29eqfrjdUFhlk1ihBhDWQlaPCAZhy7Y39SghgWSXR5

