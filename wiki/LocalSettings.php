<?php
# -- Basics --
$wgSitename             = getenv('MW_SITENAME') ?: 'TrigpointingUK Wiki';
$wgServer               = getenv('MW_SERVER')   ?: 'https://wiki.trigpointing.uk';
$wgScriptPath           = "";  // adjust if you deploy under /w
$wgArticlePath          = '/$1';     // emit /PageTitle links instead of /wiki/PageTitle
$wgUsePathInfo          = true;      // (usually true by default)
$wgLogo                 = "https://trigpointing.uk/pics/tuk_logo.gif";
$wgFavicon              = "https://trigpointing.uk/favicon.ico";
$wgLanguageCode         = "en-GB";
$wgLocaltimezone        = "Europe/London";
$wgForceHTTPS           = true;
$wgMainPageIsDomainRoot = true;  // Make / redirect to main page cleanly
$wgMainPage             = "TrigpointingUK";  // Define which page is the main page

# Error handling - suppress display, log to stderr (captured by ECS)
error_reporting( -1 );
ini_set( 'display_errors', 0 );
$wgShowExceptionDetails = false;
$wgShowDBErrorBacktrace = false;
$wgDebugLogFile = 'php://stderr';  // Send debug output to stderr for CloudWatch

# Optional debug settings for troubleshooting (uncomment if needed)
// $wgDebugToolbar = true;
// $wgShowExceptionDetails = true;
// $wgDebugLogGroups['PluggableAuth'] = 'php://stderr';
// $wgDebugLogGroups['OpenIDConnect'] = 'php://stderr';

# -- Rights --
$wgRightsText = "Creative Commons Attribution-ShareAlike";
$wgRightsUrl = "https://creativecommons.org/licenses/by-sa/4.0/";
$wgRightsIcon = "$wgResourceBasePath/resources/assets/licenses/cc-by-sa.png";

# -- DB --
$wgDBtype         = 'mysql';
$wgDBserver       = getenv('MEDIAWIKI_DB_HOST') ?: 'localhost';
$wgDBname         = getenv('MEDIAWIKI_DB_NAME') ?: 'mediawiki';
$wgDBuser         = getenv('MEDIAWIKI_DB_USER') ?: 'wiki';
$wgDBpassword     = getenv('MEDIAWIKI_DB_PASSWORD') ?: '';
$wgDBTableOptions = 'ENGINE=InnoDB, DEFAULT CHARSET=utf8mb4';
$wgDBprefix       = getenv('MEDIAWIKI_DB_PREFIX') ?: '';


# -- Keys (store in Secrets Manager and pass as env) --
$wgSecretKey      = getenv('MW_SECRET_KEY')  ?: 'CHANGE-ME';
$wgUpgradeKey     = getenv('MW_UPGRADE_KEY') ?: 'CHANGE-ME';


# --- Redis / Valkey (ElastiCache) ---
$redisHost        = getenv('CACHE_HOST') ?: 'valkey.trigpointing.local';
$redisPort        = (int)(getenv('CACHE_PORT') ?: 6379);
$useTls           = (getenv('CACHE_TLS') ?: 'true') === 'true';

if ($redisHost !== '') {
    $server = ($useTls ? 'tls://' : '') . $redisHost . ':' . $redisPort;

    $wgObjectCaches['redis'] = [
        'class'           => 'RedisBagOStuff',
        'servers'         => [ $server ],
        'persistent'      => true,
        'connectTimeout'  => 1.0,
    ];

    $wgMainCacheType    = 'redis';
    $wgParserCacheType  = 'redis';
    $wgSessionCacheType = 'redis';

    $wgJobTypeConf['default'] = [
        'class'       => 'JobQueueRedis',
        'redisServer' => $server,
        'redisConfig' => [],
    ];
} else {
    $wgMainCacheType    = 'db';
    $wgParserCacheType  = 'db';
    $wgSessionCacheType = 'db';
}
$wgCacheDirectory = '/tmp/mw-cache'; // Used for localisation cache


# -- Uploads on local storage (EFS) --
$wgEnableUploads    = true;
$wgUploadDirectory  = "/var/www/html/images";
$wgUploadPath       = "/images";
$wgFileExtensions   = ['png', 'gif', 'jpg', 'jpeg', 'pdf', 'svg'];
$wgMaxUploadSize    = 20 * 1024 * 1024; // 20MB


# -- Email with SES SMTP --
$wgEnableEmail      = true;
$wgEnableUserEmail  = true;
$wgEmergencyContact = "admin@trigpointing.uk";
$wgPasswordSender   = "noreply@trigpointing.uk";

$smtpUsername = getenv('SMTP_USERNAME');
$smtpPassword = getenv('SMTP_PASSWORD');

if ($smtpUsername && $smtpPassword) {
    $wgSMTP = [
        'host'     => 'email-smtp.eu-west-1.amazonaws.com',
        'IDHost'   => 'wiki.trigpointing.uk',
        'port'     => 587,
        'auth'     => true,
        'username' => $smtpUsername,
        'password' => $smtpPassword,
    ];
}


# -- Auth0 via PluggableAuth + OpenID Connect --
wfLoadExtension( 'PluggableAuth' );
wfLoadExtension( 'OpenIDConnect' );

# Disable password attempt throttling to prevent DoS attacks
# Since we use Auth0 for authentication, MediaWiki's built-in throttling
# is not needed and creates a vulnerability where bad actors can lock out
# legitimate users by triggering failed login attempts
$wgPasswordAttemptThrottle = false;

$providerURL   = getenv('OIDC_PROVIDER_URL') ?: '';
$clientID      = getenv('OIDC_CLIENT_ID') ?: '';
$clientSecret  = getenv('OIDC_CLIENT_SECRET') ?: '';
$redirectURI   = getenv('OIDC_REDIRECT_URI') ?: ($wgServer . '/wiki/Special:PluggableAuthLogin');

// // Override the end_session_endpoint to use Auth0's native logout
// $wgOpenIDConnect_Config[$providerURL] = [
//   'end_session_endpoint' => 'https://auth.trigpointing.uk/v2/logout?client_id=' . $clientID . '&returnTo=https://wiki.trigpointing.uk/TrigpointingUK',
// ];

$wgOpenIDConnect_ForceReauth                  = true;   // Reauthenticate users with auth0 every time
$wgOpenIDConnect_SingleLogout                 = false;  // Log out of all Auth0 applications
$wgOpenIDConnect_MigrateUsersByEmail          = true;
$wgOpenIDConnect_MigrateUsersByUsername       = true;

$wgGroupPermissions['*']['autocreateaccount'] = true;
$wgGroupPermissions['*']['createaccount']     = false;  // Hide "Create account" link
$wgPluggableAuth_EnableAutoLogin              = false;  // Anonymous access is permitted
$wgPluggableAuth_EnableLocalLogin             = getenv('MW_ENABLE_LOCAL_LOGIN') === 'true';
$wgPluggableAuth_EnableLocalProperties        = false;  // Users cannot edit their email address etc
$wgPluggableAuth_EnableFastLogout             = true;   // Avoid additional logout confirmation page
$wgPluggableAuth_ButtonLabelLogout            = 'Log out';

$wgPluggableAuth_Config = [[
  'plugin' => 'OpenIDConnect',
  'data' => [
    'providerURL'        => $providerURL,
    'clientID'           => $clientID,
    'clientsecret'       => $clientSecret,
    'scope'              => [ 'openid', 'profile', 'email'],
    'preferred_username' => 'nickname',
    'redirectURI'        => $redirectURI,
    'post_logout_redirect_uri' => 'https://wiki.trigpointing.uk',
  ],
  'buttonLabelMessage' => 'auth0-login',
  'groupsyncs' => [
    [
      'type' => 'mapped',
      'map' => [
        'sysop' => ['https://trigpointing.uk/roles' => ['wiki-admin', 'api-admin']],
        // 'bureaucrat' => ['https://trigpointing.uk/roles' => ['tuk-bureaucrat']],
      ],
    ],
  ],
]];




# Auth0 manages all user rights - disable local rights management
unset( $wgGroupPermissions['bureaucrat'] );
unset( $wgRevokePermissions['bureaucrat'] );
unset( $wgAddGroups['bureaucrat'] );
unset( $wgRemoveGroups['bureaucrat'] );
unset( $wgGroupsAddToSelf['bureaucrat'] );
unset( $wgGroupsRemoveFromSelf['bureaucrat'] );
$wgGroupPermissions['sysop']['userrights'] = false;

# Require login to edit (read-only for anonymous users)
$wgGroupPermissions['*']['edit'] = false;           // Anonymous cannot edit
$wgGroupPermissions['*']['createpage'] = false;     // Anonymous cannot create pages
$wgGroupPermissions['*']['createtalk'] = false;     // Anonymous cannot create talk pages
$wgGroupPermissions['user']['edit'] = true;         // Logged-in users can edit
$wgGroupPermissions['user']['createpage'] = true;   // Logged-in users can create
$wgGroupPermissions['user']['createtalk'] = true;   // Logged-in users can create talk

# -- Extensions --
wfLoadExtension( 'ChangeAuthor' );
$wgGroupPermissions['sysop']['changeauthor'] = true;

wfLoadExtension( 'Cite' );
wfLoadExtension( 'SyntaxHighlight_GeSHi' );
wfLoadExtension( 'VisualEditor' );
wfLoadExtension( 'WikiEditor' );


# -- Styles --
// wfLoadSkin( 'MinervaNeue' );
// wfLoadSkin( 'MonoBook' );
// wfLoadSkin( 'Timeless' );
wfLoadSkin( 'Vector' );
$wgDefaultSkin = "Vector";


# Custom Namespace for Book
define("NS_BOOK", 3036);
define("NS_BOOK_TALK", 3037);

$wgExtraNamespaces[NS_BOOK] = "Book";
$wgExtraNamespaces[NS_BOOK_TALK] = "Book_talk";

$wgNamespaceProtection[NS_BOOK] = array( 'editbook' );
$wgNamespacesWithSubpages[NS_BOOK] = true;
$wgGroupPermissions['sysop']['editbook'] = true;
$wgNamespacesToBeSearchedDefault[NS_BOOK] = true;


# Custom Namespaces for Archive
define("NS_ARCHIVE", 3038);
define("NS_ARCHIVE_TALK", 3039);

$wgExtraNamespaces[NS_ARCHIVE] = "Archive";
$wgExtraNamespaces[NS_ARCHIVE_TALK] = "Archive_talk";

$wgNamespaceProtection[NS_ARCHIVE] = array( 'editarchive' );
$wgNamespacesWithSubpages[NS_ARCHIVE] = true;
$wgGroupPermissions['sysop']['editarchive'] = true;
$wgGroupPermissions['user']['editarchive'] = true;
$wgNamespacesToBeSearchedDefault[NS_ARCHIVE] = true;


# Enable subpages in the main and archive namespace
$wgNamespacesWithSubpages[NS_MAIN] = true;
$wgNamespacesWithSubpages[NS_ARCHIVE] = true;
