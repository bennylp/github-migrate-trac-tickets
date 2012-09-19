#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Migrate trac tickets for a given "component" from DB into GitHub using v3 API.
# Transforms milestones to milestones, priority and type to labels.
# The code does NOT attempt to prevent duplicating tickets so you'll
# get multiples if you run repeatedly.  See API docs:
# http://developer.github.com/v3/issues/

import datetime
import logging
from optparse import OptionParser
import sqlite3

from github import GitHub

class Trac(object):
    # We don't have a way to close (potentially nested) cursors

    def __init__(self, trac_db_path):
        self.trac_db_path = trac_db_path
        try:
            self.conn = sqlite3.connect(self.trac_db_path)
        except sqlite3.OperationalError, e:
            raise RuntimeError("Could not open trac db=%s e=%s" % (self.trac_db_path, e))

    def sql(self, sql_query):
        """Create a new connection, send the SQL query, return response.
        We need unique cursors so queries in context of others work.
        """
        cursor = self.conn.cursor()
        cursor.execute(sql_query)
        return cursor

    def close(self):
        self.conn.close()

# Warning: optparse is deprecated in python-2.7 in favor of argparse
usage = """
  %prog [options] trac_db_path trac_component github_username github_password github_repo

  The path might be something like "/tmp/trac.db"
  The github_repo combines user or organization and specific repo like "myorg/myapp"
"""
parser = OptionParser(usage=usage)
parser.add_option('-q', '--quiet', action="store_true", default=False,
                  help='Decrease logging of activity')

(options, args) = parser.parse_args()
try:
    [trac_db_path, trac_component, github_username, github_password, github_repo] = args
except ValueError:
    parser.error('Wrong number of arguments')
if not '/' in github_repo:
    parser.error('Repo must be specified like "organization/project"')

if options.quiet:
    logging.basicConfig(level=logging.INFO)
else:
    logging.basicConfig(level=logging.DEBUG)

trac = Trac(trac_db_path)
github = GitHub(github_username, github_password, github_repo)

# Show the Trac usernames assigned to tickets as an FYI

logging.info("Getting Trac ticket owners (will NOT be mapped to GitHub username)...")
for (username,) in trac.sql('SELECT DISTINCT owner FROM ticket WHERE component="%s"' % trac_component):
    if username:
        username = username.strip() # username returned is tuple like: ('phred',)
        logging.debug("Trac ticket owner: %s" % username)


# Get GitHub labels; we'll merge Trac priorities and types into them

logging.info("Getting existing GitHub labels...")
gh_labels = {}
for label in github.labels():
    gh_labels[label['name']] = True
    logging.debug("label name=%s" % label['name'])

# Get any existing GitHub milestones so we can merge Trac into them.
# We need to reference them by numeric ID in tickets.
# API returns only 'open' issues by default, have to ask for closed like:
# curl -u 'USER:PASS' https://api.github.com/repos/USERNAME/REPONAME/milestones?state=closed

logging.info("Getting existing GitHub milestones...")
milestone_id = {}
for m in github.milestones():
    milestone_id[m['title']] = m['number']
    logging.debug("milestone (open)   title=%s" % m['title'])
for m in github.milestones(query='state=closed'):
    milestone_id[m['title']] = m['number']
    logging.debug("milestone (closed) title=%s" % m['title'])

# We have no way to set the milestone closed date in GH.
# The 'due' and 'completed' are long ints representing datetimes.

logging.info("Migrating Trac milestones to GitHub...")
milestones = trac.sql('SELECT name, description, due, completed FROM milestone')
for name, description, due, completed in milestones:
    name = name.strip()
    logging.debug("milestone name=%s due=%s completed=%s" % (name, due, completed))
    if name and name not in milestone_id:
        if completed:
            state = 'closed'
        else:
            state = 'open'
        milestone = {'title': name,
                     'state': state,
                     'description': description,
                     }
        if due:
            milestone['due_on'] = datetime.datetime.fromtimestamp( due ).isoformat()
        logging.debug("milestone: %s" % milestone)
        gh_milestone = github.milestones(data=milestone)
        milestone_id['name'] = gh_milestone['number']

# Copy Trac tickets to GitHub issues, keyed to milestones above

tickets = trac.sql('SELECT id, priority, type, summary, description, owner, reporter, milestone, time, status FROM ticket WHERE component="%s" ORDER BY id' % trac_component) # LIMIT 5
for tid, priority, ticket_type, summary, description, owner, reporter, milestone, timestamp, status in tickets:
    summary += "  (ros-pkg ticket #%d)" % tid
    labels = []
    if ticket_type == "defect":
        ticket_type = "bug";
    if ticket_type:
        labels.append( ticket_type )
    if priority:
        labels.append( priority )

    if ticket_type not in gh_labels:
        logging.info( "Adding label %s" % ticket_type )
        github.labels( data = { 'name': ticket_type })
        gh_labels[ ticket_type ] = True
    if priority not in gh_labels:
        logging.info( "Adding label %s" % priority )
        github.labels( data = { 'name': priority })
        gh_labels[ priority ] = True

    logging.info("Ticket %d: %s" % (tid, summary))
    if description:
        description = description.strip()
    if milestone:
        milestone = milestone.strip()
    issue = {'title': summary}
    issue['labels'] = labels
    if description:
        description += "\n\n"
        description += "trac data:\n"
        description += " * Owner: **%s**\n" % owner
        description += " * Reporter: **%s**\n" % reporter
        description += " * Reported at: **%s**\n" % datetime.datetime.fromtimestamp( timestamp ).ctime()
        description += " * URL: http://code.ros.org/trac/ros-pkg/ticket/%d" % tid
        issue['body'] = description
    if milestone:
        m = milestone_id.get(milestone)
        if m:
            issue['milestone'] = m
    # We have to create/map Trac users to GitHub usernames before we can assign
    # them to tickets; don't see how to do that conveniently now.
    # if owner.strip():
    #     ticket['assignee'] = owner.strip()
    gh_issue = github.issues(data=issue)
    # Add comments
    comments = trac.sql('SELECT author, newvalue AS body FROM ticket_change WHERE field="comment" AND ticket=%s' % tid)
    for author, body in comments:
        body = body.strip()
        if body:
            # prefix comment with author as git doesn't keep them separate
            if author:
                body = "[%s] %s" % (author, body)
            logging.debug('issue comment: %s' % body[:40]) # TODO: escape newlines
            github.issue_comments(gh_issue['number'], data={'body': body})
    # Close tickets if they need it.
    # The v3 API says we should use PATCH, but
    # http://developer.github.com/v3/ says POST is supported.
    if status == 'closed':
        github.issues(id_=gh_issue['number'], data={'state': 'closed'})
        logging.debug("close")

trac.close()


