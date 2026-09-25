<?php
namespace teasel\auth0\service;

use OAuth\Common\Http\Uri\UriInterface;
use phpbb\auth\provider\oauth\service\base;
use phpbb\config\config;
use phpbb\request\request_interface;

/**
 * Auth0 OAuth provider that reads settings from environment variables:
 *  AUTH0_DOMAIN (e.g. your-tenant.eu.auth0.com)
 *  AUTH0_CLIENT_ID
 *  AUTH0_CLIENT_SECRET
 *  AUTH0_SCOPE (optional, default 'openid email profile')
 */
class provider extends base
{
    /** @var config */
    protected $config;

    /** @var request_interface */
    protected $request;

    /**
     * Constructor
     *
     * @param config $config
     * @param request_interface $request
     */
    public function __construct(config $config, request_interface $request)
    {
        $this->config = $config;
        $this->request = $request;
    }

    /**
     * {@inheritdoc}
     */
    public function get_service_credentials()
    {
        $client_id = getenv('AUTH0_CLIENT_ID') ?: '';
        $client_secret = getenv('AUTH0_CLIENT_SECRET') ?: '';

        return [
            'key'    => $client_id,
            'secret' => $client_secret,
        ];
    }

    /**
     * {@inheritdoc}
     */
    public function get_auth_scope()
    {
        $scope = getenv('AUTH0_SCOPE') ?: 'openid email profile';
        return explode(' ', $scope);
    }

    /**
     * {@inheritdoc}
     */
    public function get_external_service_class()
    {
        return '\\teasel\\auth0\\service\\auth0';
    }

    /**
     * {@inheritdoc}
     */
    public function perform_auth_login()
    {
        if (!($this->service_provider instanceof \OAuth\OAuth2\Service\AbstractService))
        {
            throw new \phpbb\auth\provider\oauth\service\exception('AUTH_PROVIDER_OAUTH_ERROR_INVALID_SERVICE_TYPE');
        }

        $code = $this->request->variable('code', '');
        $this->flog('[auth0] provider.perform_auth_login() code=' . ($code !== '' ? 'present' : 'missing'));
        $this->service_provider->requestAccessToken($code);
        
        // Proactively create/link before phpBB presents link/register
        $success = $this->ensure_oauth_mapping();
        $this->flog('[auth0] provider.perform_auth_login() ensure_oauth_mapping result=' . ($success ? 'true' : 'false'));
        
        // If mapping was created/exists, try to complete the login immediately
        if ($success && isset($GLOBALS['phpbb_container'])) {
            $this->complete_login_if_mapped();
        }
    }
    
    /**
     * Complete the login if a mapping exists
     */
    protected function complete_login_if_mapped()
    {
        try {
            $container = $GLOBALS['phpbb_container'];
            $db = $container->get('dbal.conn');
            $claims = $this->get_user_identity();
            $external = isset($claims['sub']) ? (string)$claims['sub'] : '';
            $provider = $this->get_service_name_safe();
            $table_oauth = defined('OAUTH_ACCOUNTS_TABLE') ? OAUTH_ACCOUNTS_TABLE : 'phpbb_oauth_accounts';
            
            $sql = "SELECT user_id FROM $table_oauth WHERE provider='" . $db->sql_escape($provider) . "' AND oauth_provider_id='" . $db->sql_escape($external) . "'";
            $res = $db->sql_query($sql);
            $row = $db->sql_fetchrow($res);
            $db->sql_freeresult($res);
            
            if ($row && (int)$row['user_id'] > 0) {
                $user_id = (int)$row['user_id'];
                $this->flog('[auth0] provider.complete_login_if_mapped() found user_id=' . $user_id . ', completing login');
                
                // Get user object if not already set
                $user = $container->get('user');
                
                // Create session for the user
                $user->session_begin(false);
                $user->session_create($user_id, false, false, true);
                
                $this->flog('[auth0] provider.complete_login_if_mapped() session created, redirecting');
                
                // Redirect to index
                global $phpbb_root_path, $phpEx;
                if (!function_exists('redirect')) {
                    include_once($phpbb_root_path . 'includes/functions.' . $phpEx);
                }
                $target = append_sid($phpbb_root_path . 'index.' . $phpEx);
                redirect($target);
            }
        } catch (\Exception $e) {
            $this->flog('[auth0] provider.complete_login_if_mapped() error: ' . $e->getMessage());
        }
    }

    /**
     * {@inheritdoc}
     */
    public function perform_token_auth()
    {
        $this->flog('[auth0] provider.perform_token_auth() called');
        if (!($this->service_provider instanceof \OAuth\OAuth2\Service\AbstractService))
        {
            throw new \phpbb\auth\provider\oauth\service\exception('AUTH_PROVIDER_OAUTH_ERROR_INVALID_SERVICE_TYPE');
        }

        $service_name = $this->get_service_name_safe();
        $this->service_provider->refreshAccessToken(
            $this->service_provider->getStorage()->retrieveAccessToken($service_name)->getRefreshToken()
        );
    }

    /**
     * {@inheritdoc}
     */
    protected function get_user_identity()
    {
        $this->flog('[auth0] provider.get_user_identity() called');
        $domain = getenv('AUTH0_DOMAIN') ?: '';

        // Request user info from Auth0
        $uri = new \OAuth\Common\Http\Uri\Uri('https://' . $domain . '/userinfo');
        $response = $this->service_provider->request($uri);

        $data = json_decode($response, true);
        if (!is_array($data)) {
            $data = [];
        }

        // Provide phpBB-friendly aliases but keep all original claims for subscribers
        $data['user_id'] = $data['sub'] ?? '';
        // Prefer nickname, then name, then email to avoid phpBB managing usernames
        $data['username'] = $data['nickname'] ?? ($data['name'] ?? ($data['email'] ?? ''));
        $data['email'] = $data['email'] ?? '';
        $data['name'] = $data['name'] ?? '';

        $this->flog('[auth0] provider.get_user_identity() returning sub=' . ($data['sub'] ?? 'none') . ' email=' . ($data['email'] ?? 'none'));
        return $data;
    }

    /**
     * {@inheritdoc}
     */
    public function get_auth_user_id()
    {
        // Ensure a phpBB user and oauth mapping exist before phpBB decides to show link/register
        $this->flog('[auth0] provider.get_auth_user_id() invoked');
        $user_data = $this->get_user_identity();
        $sub = $user_data['user_id'] ?? '';
        
        // Try to create/link the mapping
        $success = $this->ensure_oauth_mapping();
        $this->flog('[auth0] provider.get_auth_user_id() ensure_oauth_mapping result=' . ($success ? 'true' : 'false'));
        
        // Verify mapping was created successfully
        if (isset($GLOBALS['phpbb_container'])) {
            $container = $GLOBALS['phpbb_container'];
            try {
                $db = $container->get('dbal.conn');
                $table_oauth = defined('OAUTH_ACCOUNTS_TABLE') ? OAUTH_ACCOUNTS_TABLE : 'phpbb_oauth_accounts';
                $provider = $this->get_service_name_safe();
                
                $sql = "SELECT user_id FROM $table_oauth WHERE provider='" . $db->sql_escape($provider) . "' AND oauth_provider_id='" . $db->sql_escape($sub) . "'";
                $res = $db->sql_query($sql);
                $row = $db->sql_fetchrow($res);
                $db->sql_freeresult($res);
                
                if ($row && (int)$row['user_id'] > 0) {
                    $this->flog('[auth0] provider.get_auth_user_id() verified mapping exists for user_id=' . (int)$row['user_id']);
                } else {
                    $this->flog('[auth0] provider.get_auth_user_id() WARNING: mapping not found after ensure_oauth_mapping');
                }
            } catch (\Exception $e) {
                $this->flog('[auth0] provider.get_auth_user_id() verification failed: ' . $e->getMessage());
            }
        }
        
        $this->flog('[auth0] provider.get_auth_user_id() returning sub=' . $sub);
        return $sub;
    }

    /**
     * Ensure the oauth mapping exists; create/link user if needed
     */
    protected function ensure_oauth_mapping()
    {
        $this->flog('[auth0] provider.ensure_oauth_mapping() start');
        // Access services lazily to avoid hard dependency in constructor
        if (!isset($GLOBALS['phpbb_container'])) {
            $this->flog('[auth0] provider.ensure_oauth_mapping() no container');
            return false;
        }
        $container = $GLOBALS['phpbb_container'];
        try {
            $db = $container->get('dbal.conn');
        } catch (\Exception $e) {
            $this->flog('[auth0] provider.ensure_oauth_mapping() failed get db: ' . $e->getMessage());
            return false;
        }

        $claims = $this->get_user_identity();
        $provider = $this->get_service_name_safe(); // Safe method with fallback
        $external = isset($claims['sub']) ? (string)$claims['sub'] : '';
        if ($external === '') {
            $this->flog('[auth0] provider.ensure_oauth_mapping() missing sub');
            return false;
        }
        $this->flog('[auth0] provider.ensure_oauth_mapping() provider=' . $provider . ' sub=' . $external);

        // Already linked?
        $table_oauth = defined('OAUTH_ACCOUNTS_TABLE') ? OAUTH_ACCOUNTS_TABLE : 'phpbb_oauth_accounts';
        $sql = "SELECT user_id FROM $table_oauth WHERE provider='" . $db->sql_escape($provider) . "' AND oauth_provider_id='" . $db->sql_escape($external) . "'";
        $res = $db->sql_query($sql);
        $row = $db->sql_fetchrow($res);
        $db->sql_freeresult($res);
        if ($row && (int)$row['user_id'] > 0) {
            $this->flog('[auth0] provider.ensure_oauth_mapping() mapping exists user_id=' . (int)$row['user_id']);
            return true; // Mapping exists - success!
        }

        $email = isset($claims['email']) ? (string)$claims['email'] : '';
        $user_id = 0;
        if ($email !== '') {
            $table_users = defined('USERS_TABLE') ? USERS_TABLE : 'phpbb_users';
            $sql = "SELECT user_id FROM $table_users WHERE user_email='" . $db->sql_escape($email) . "' AND user_type <> 2"; // exclude anonymous
            $res = $db->sql_query($sql);
            $userRow = $db->sql_fetchrow($res);
            $db->sql_freeresult($res);
            if ($userRow && (int)$userRow['user_id'] > 0) {
                $user_id = (int)$userRow['user_id'];
                $this->flog('[auth0] provider.ensure_oauth_mapping() linked by email user_id=' . $user_id);
            }
        }

        if ($user_id === 0) {
            // Create a new phpBB user using nickname as username
            global $phpbb_root_path, $phpEx;
            if (!function_exists('user_add')) {
                include_once($phpbb_root_path . 'includes/functions_user.' . $phpEx);
            }
            if (!function_exists('phpbb_hash')) {
                include_once($phpbb_root_path . 'includes/functions_user.' . $phpEx);
            }
            
            // Determine base username
            $nickname = isset($claims['nickname']) ? (string)$claims['nickname'] : '';
            $name = isset($claims['name']) ? (string)$claims['name'] : '';
            $baseUsername = $nickname !== '' ? $nickname : ($name !== '' ? $name : $email);
            if ($baseUsername === '') {
                $baseUsername = 'user_' . substr(bin2hex(random_bytes(4)), 0, 8);
            }
            
            // Ensure username is unique
            $username = $this->get_unique_username($baseUsername, $db);
            
            // Generate random password and hash it properly
            $randomPassword = bin2hex(random_bytes(32));
            
            $userData = [
                'username'      => $username,
                'user_password' => phpbb_hash($randomPassword),
                'user_email'    => $email,
                'group_id'      => 2, // REGISTERED
                'user_type'     => 0, // NORMAL
                'user_actkey'   => '', // No activation needed
                'user_inactive_reason' => 0,
                'user_inactive_time' => 0,
                // user_add() defaults this to 0; ucp_register sets it explicitly, so must we,
                // otherwise new users skip the Newly Registered Users group (post moderation)
                'user_new' => ($this->config['new_member_post_limit']) ? 1 : 0,
            ];
            
            $newId = user_add($userData, false); // false = suppress validation error array
            
            if (is_int($newId) && $newId > 0) {
                $user_id = $newId;
                $this->flog('[auth0] provider.ensure_oauth_mapping() created user_id=' . $user_id . ' username=' . $username);
            } else {
                $this->flog('[auth0] provider.ensure_oauth_mapping() user_add FAILED for username=' . $username . ' result=' . var_export($newId, true));
                return false;
            }
        }

        if ($user_id > 0) {
            // Insert mapping (ignore duplicates)
            $sql = "INSERT IGNORE INTO $table_oauth (user_id,provider,oauth_provider_id) VALUES (" . (int)$user_id . ", '" . $db->sql_escape($provider) . "', '" . $db->sql_escape($external) . "')";
            $db->sql_query($sql);
            $affected = $db->sql_affectedrows();
            $this->flog('[auth0] provider.ensure_oauth_mapping() inserted mapping for user_id=' . (int)$user_id . ' affected_rows=' . $affected);
        }
        $this->flog('[auth0] provider.ensure_oauth_mapping() end success=' . ($user_id > 0 ? 'true' : 'false'));
        return ($user_id > 0);
    }

    protected function flog($msg)
    {
        // Log to stdout for Docker/containerized environments
        error_log('[auth0] ' . $msg);
        // Also log to tmp as fallback
        @file_put_contents('/tmp/auth0_debug.log', date('c') . ' ' . $msg . "\n", FILE_APPEND);
    }

    /**
     * Get the service name safely with fallback
     */
    protected function get_service_name_safe()
    {
        // Try to call parent method if it exists
        if (method_exists($this, 'get_service_name')) {
            return $this->get_service_name();
        }
        // Fallback to the expected service name for Auth0
        return 'auth.provider.oauth.service.auth0';
    }

    /**
     * Get unique username by appending numbers if needed
     */
    protected function get_unique_username($base, $db)
    {
        $table_users = defined('USERS_TABLE') ? USERS_TABLE : 'phpbb_users';
        $username = $base;
        $counter = 0;
        
        while (true) {
            $clean = utf8_clean_string($username);
            $sql = "SELECT user_id FROM $table_users WHERE username_clean='" . $db->sql_escape($clean) . "'";
            $res = $db->sql_query($sql);
            $row = $db->sql_fetchrow($res);
            $db->sql_freeresult($res);
            
            if (!$row) {
                return $username; // Username is available
            }
            
            $counter++;
            $username = $base . $counter;
            
            if ($counter > 100) {
                // Fallback to random
                return 'user_' . substr(bin2hex(random_bytes(4)), 0, 8);
            }
        }
    }

    /**
     * Allow auto-linking accounts by email
     */
    public function is_email_verified()
    {
        // Auth0 verifies emails, so we trust them
        $this->flog('[auth0] provider.is_email_verified() called - returning true');
        return true;
    }

    /**
     * {@inheritdoc}
     */
    public function get_auth_user_email()
    {
        $this->flog('[auth0] provider.get_auth_user_email() called');
        $user_data = $this->get_user_identity();
        $email = $user_data['email'] ?? '';
        $this->flog('[auth0] provider.get_auth_user_email() returning ' . $email);
        return $email;
    }

    /**
     * {@inheritdoc}
     */
    public function perform_link()
    {
        // Auto-link account - this is called by phpBB when it wants to link an OAuth account
        $this->flog('[auth0] provider.perform_link() called - ensuring mapping exists');
        $success = $this->ensure_oauth_mapping();
        $this->flog('[auth0] provider.perform_link() result=' . ($success ? 'true' : 'false'));
        // Return an array with 'user_id' key to complete the link, or false to show UI
        if ($success) {
            // Get the mapping to return the user_id
            if (!isset($GLOBALS['phpbb_container'])) {
                return false;
            }
            $container = $GLOBALS['phpbb_container'];
            try {
                $db = $container->get('dbal.conn');
                $claims = $this->get_user_identity();
                $external = isset($claims['sub']) ? (string)$claims['sub'] : '';
                $provider = $this->get_service_name_safe();
                $table_oauth = defined('OAUTH_ACCOUNTS_TABLE') ? OAUTH_ACCOUNTS_TABLE : 'phpbb_oauth_accounts';
                
                $sql = "SELECT user_id FROM $table_oauth WHERE provider='" . $db->sql_escape($provider) . "' AND oauth_provider_id='" . $db->sql_escape($external) . "'";
                $res = $db->sql_query($sql);
                $row = $db->sql_fetchrow($res);
                $db->sql_freeresult($res);
                
                if ($row && (int)$row['user_id'] > 0) {
                    $this->flog('[auth0] provider.perform_link() returning user_id=' . (int)$row['user_id']);
                    return ['user_id' => (int)$row['user_id']];
                }
            } catch (\Exception $e) {
                $this->flog('[auth0] provider.perform_link() error: ' . $e->getMessage());
            }
        }
        return false;
    }

    /**
     * {@inheritdoc}
     */
    public function perform_register()
    {
        // Auto-register new users - this is called by phpBB when it wants to register a new user
        $this->flog('[auth0] provider.perform_register() called - ensuring mapping exists');
        $success = $this->ensure_oauth_mapping();
        $this->flog('[auth0] provider.perform_register() result=' . ($success ? 'true' : 'false'));
        // Return an array with 'user_id' key to complete registration, or false to show UI
        if ($success) {
            // Get the mapping to return the user_id
            if (!isset($GLOBALS['phpbb_container'])) {
                return false;
            }
            $container = $GLOBALS['phpbb_container'];
            try {
                $db = $container->get('dbal.conn');
                $claims = $this->get_user_identity();
                $external = isset($claims['sub']) ? (string)$claims['sub'] : '';
                $provider = $this->get_service_name_safe();
                $table_oauth = defined('OAUTH_ACCOUNTS_TABLE') ? OAUTH_ACCOUNTS_TABLE : 'phpbb_oauth_accounts';
                
                $sql = "SELECT user_id FROM $table_oauth WHERE provider='" . $db->sql_escape($provider) . "' AND oauth_provider_id='" . $db->sql_escape($external) . "'";
                $res = $db->sql_query($sql);
                $row = $db->sql_fetchrow($res);
                $db->sql_freeresult($res);
                
                if ($row && (int)$row['user_id'] > 0) {
                    $this->flog('[auth0] provider.perform_register() returning user_id=' . (int)$row['user_id']);
                    return ['user_id' => (int)$row['user_id']];
                }
            } catch (\Exception $e) {
                $this->flog('[auth0] provider.perform_register() error: ' . $e->getMessage());
            }
        }
        return false;
    }
}
