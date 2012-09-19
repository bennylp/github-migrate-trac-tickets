==============================
 GitHub: Migrate Trac Tickets
==============================

GitHub Issues API
=================

Offer a minimal API to work with GitHub's Issues via the v3 API.

It can GET issues, comments, labels, milestones, and can POST data to
create new ones via a simple dictionary.

Migrate Trac Tickets to GitHub Issues
=====================================

A sample program uses this to migrate Trac tickets into GitHub Issues.

It creates and merges "Milestones".

It selects only trac tickets with a given "Component" for migration.

It makes GitHub "Labels" for both trac "Priority" and trac "type"
(where type is "defect", "enhancement", or "task").  It translates
"defect" to "bug", which exists by default on GitHub.

It cannot migrate ticket ownership to GitHub Issue "Assignee" since we
have no way to map customer-specific Trac usernames into global GitHub
usernames.

Extra metadata added to GitHub issues
-------------------------------------

I modified this script for my particular use in a way that probably
won't be useful outside my organization.  This adds the following info
to the description of each issue:
 * original owner
 * original reporter
 * original date reported
 * URL of the original trac ticket

The URL is hard-coded into the script, with only the trac ticket ID
replaced in it.  For us, this is
'http://code.ros.org/trac/ros-pkg/ticket/%d'.  Others here will need
to change ros-pkg to something else, and others in the world at large
will need to change the URL entirely.

Testing out migration
---------------------

The GitHub API has no way to DELETE an Issue (you can only close
them), so you might want to test out the migration first.

Create a temporary new GitHub repository, like 'yourorg/killme'. Then
push your Trac tickets into it, for example:

  ./trac-tickets-to-gh.py ~/oldproject-trac.db yourtraccomponent yourname yourpasswd yourorg/killme

Then verify labels and milestones migrated as expected. Finally,
destroy the test repository.

If you've (cough) already migrated tickets into an existing github with
code, you can ensure you've pulled a current copy of the code repo,
then blow it away and re-create, then migrate the tickets, and finally
push your local code repo back into the code repo.  You'll lose any
tickets that were created within GitHub that aren't in your Trac,
however.
