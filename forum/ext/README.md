# phpBB extensions

Extensions are **baked into the container image** — [`../Dockerfile`](../Dockerfile) does
`COPY ext/ /var/www/html/ext/` and recursively chowns it to `www-data`. There is no Composer
install at runtime, so anything phpBB needs must be committed to this directory.

Shipping an extension in the image does **not** activate it. Each one must be enabled once via
ACP → Customise → Extensions, which runs its migrations against the phpBB MySQL database. That
state lives in the database, not the image, so it survives redeploys.

| Directory | Origin | Pinned at |
| --- | --- | --- |
| `teasel/auth0` | Written in-house | n/a |
| `gfksx/thanksforposts` | [rxu/thanks_for_posts](https://github.com/rxu/thanks_for_posts), branch `develop-3.3.x` | `13a0291536ccec89370dea67f72ca042d9043168` (17 Apr 2026) |

## gfksx/thanksforposts ("Thanks for posts")

Adds a Thanks button to posts — our "like" feature. Version 2.1.1, GPL-2.0-only. Requires
phpBB >= 3.3.11 (we run 3.3.15) and PHP ^8.0 (we run 8.2).

Upstream publishes no tags or releases, hence the pinned commit SHA above. To update: re-download
that repo at a new commit, replace this directory, and drop `.github/`, `tests/` and
`phpunit.xml.dist` again (they are excluded to keep the image small).

### Deliberate configuration: track now, surface later

Thanks are recorded in a single table, `phpbb_thanks` (`post_id`, `poster_id`, `user_id`,
`forum_id`). **Every aggregate view is presentation on top of that table.** The extension was
therefore deployed in August 2026 with all per-user totals suppressed, because the site had
essentially one active contributor at the time and a public leaderboard would have been a
leaderboard of one.

Recording is unaffected by any of the settings below. Reversing them later surfaces the full
history retrospectively — nothing is lost in the meantime.

**Config — ACP → Extensions → Thanks for posts settings:**

| Setting | Upstream default | Ours | Suppresses |
| --- | --- | --- | --- |
| `thanks_counters_view` | 1 | **0** | given/received counts in the post author block |
| `thanks_profilelist_view` | 1 | **0** | full thanks list on a user's profile |
| `thanks_post_reput_view` | 1 | **0** | per-post rating bar |
| `thanks_topic_reput_view` | 1 | **0** | topic rating in forum view |
| `thanks_forum_reput_view` | 0 | 0 | forum rating (already off upstream) |
| `thanks_top_number` | 0 | 0 | index toplist (already off upstream) |

Left at their defaults, because these *are* the like feature: `thanks_postlist_view` (who thanked
this post), `thanks_ajax_enabled` (toggle without page reload), `remove_thanks` (un-thank),
`thanks_number_post` = 10 (cap on names listed per post).

**Permissions — ACP → Permissions.** Two aggregate pages are gated at the controller, not merely
hidden in the template, so revoking these genuinely closes the routes:

| Permission | Gates | Checked in |
| --- | --- | --- |
| `u_viewthanks` | `/thankslist` + its nav link | `controller/thankslist.php:141` |
| `u_viewtoplist` | `/toplist` + its nav link | `controller/toplist.php:147` |

The extension's migrations grant both to REGISTERED and the `ROLE_USER_*` roles on enable. We set
them to **No** on those roles and on the REGISTERED group, and **Yes** on ADMINISTRATORS only.

> Use "No", **not** "Never". phpBB's Never propagates and wins everywhere, so it would override the
> ADMINISTRATORS grant for any admin who is also in REGISTERED — which is all of them.

`f_thanks` (per-forum, drives the button) and `m_thanks` (moderators) are left as the migrations
set them.

### To surface totals later

Reviewable from around **August 2027**, or whenever there are enough active contributors for a
leaderboard to mean something. Set `thanks_counters_view`, `thanks_profilelist_view`,
`thanks_post_reput_view` and `thanks_topic_reput_view` back to 1, and grant `u_viewthanks` /
`u_viewtoplist` to REGISTERED. Optionally set `thanks_top_number` above 0 for an index toplist.
All historical thanks appear immediately.

### Do not touch

ACP → Extensions → Thanks for posts offers "Update thanks counters" and "Clear the list of
thanks". Both are destructive and irreversible: the refresh erases thanks on guest posts, and on
global announcements when "Thanks in Global Announcements" is off.
