Migrate Trac Tickets to GitHub Issues
=====================================

The "migrate.py" script copies Trac tickets into GitHub Issues.  It
pulls issues from the sqlite database file used by Trac (or ideally a
copy of that file), and uses the GitHub API to post them.

It will optionaly create and merge "Milestones".

It selects only trac tickets with a given "Component" for migration.

It makes GitHub "Labels" for both trac "Priority" and trac "type"
(where type is "defect", "enhancement", or "task").  It translates
"defect" to "bug", which exists by default on GitHub.

It cannot migrate ticket ownership to GitHub Issue "Assignee" since we
have no way to map customer-specific Trac usernames into global GitHub
usernames.

The new github issue numbers do not match the old Trac ticket numbers,
though the numbers are saved in the description for reference.

Extra metadata added to GitHub issues
-------------------------------------

The script adds the following info to the description of each issue:

 * original owner
 * original reporter
 * original date reported
 * URL of the original trac ticket

The base of the trac ticket URL must be given on the command line.

Testing out migration
---------------------

The GitHub API has no way to DELETE an Issue (you can only close
them), so **it is important to test this first**.

Create a temporary new GitHub repository, like 'yourorg/killme'. Then
push your Trac tickets into it, for example::

  ./migrate.py ~/oldproject-trac.db http://example.com/trac/oldproject yourtraccomponent yourname yourpasswd yourorg/killme

Then verify labels, metadata, back-links and optionally milestones
migrated as expected. Finally, destroy the test repository.

If you make a mistake and migrate a bunch of tickets incorrectly to a
repo which is **not** a test repo, you can still recover to some extent.
(This will lose any issues created within github that aren't in your
trac.)  Ensure you've pulled a current copy of the code repo, then
blow away the github repo and re-create it.  Migrate the tickets
(correctly this time), then finally push your local code repo back
into the code repo.
