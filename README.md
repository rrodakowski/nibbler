# Overview

A simple RSS to email application.

Nibbler is a RSS aggregator that collects articles and puts them into a daily email newsletter. It is a command line app and aims to be simple yet flexible to use.

It is designed to run once day and puts new articles in a single email for that previous day. With only required command line arguments supplied, it will put the email in a file on your filesystem. You could write a script to send this as an email if you have a mail transfer agent on that system or potentially show it as a static page. 

If you can configure or have access to a SMTP server to send email, you can pass in smtp configuration to nibbler. Popular free choices for a SMTP server would be:

- gmail
- sendgrid
- mailgun
- aws (free based on usage)

The sender email (from email) should be for a domain or email address which you own. This will help prevent your email from going to spam.

# Requirements

Nibbler is a python application tested on 3.+
I have only run it on Ubuntu Linux and Mac machines.

# Installation / Dependencies

To install: 

pip install nibbler

Until then you can install the required python which are opml ,lxml, feedparser, SQLAlchemy and Jinja2. It stores articles in a sqlite database on your filesystem. 

Then you can run it with this command:

python3 -m nibbler <to_email> <from_email> <dir_to_subscriptions>

The from email should be for a domain on which you are running email. This will help prevent your email from going to spam.

Pass in the directory in which you have a subscriptions.xml (an OPML file) as the third argument.

I recommend using a cron job on your local machine or a server to aggregate rss feeds and send the newsletter daily.

# Help

A simple RSS to email application.

~~~
positional arguments:
to_email              Recipient email address; youremail@example.com
from_email            Sender email address; nibble@example.com
sub_dir               path to subscriptions.xml file

optional arguments:
-h, --help                          show this help message and exit
-l log_dir, --log-dir log_dir       optional path to log dir
-s smtp_ini, --smtp-ini smtp_ini    optional path to smtp ini file
-d db_dir, --db-dir db_dir          optional path to sqlite db dir
-e email_dir, --email-dir email_dir optional path to directory where email file is output before sending
-v, --version                       show program's version number and exit
~~~

## SMTP Notes

A sample smtp.ini file would be:

~~~
[smtp]
username = sample_username
password = Sample_Password
host = hostname.example.com
port = 587
~~~

# License

MIT license, a permissive open-source license.

# Author

Randall Rodakowski
