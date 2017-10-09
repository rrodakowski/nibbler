# Overview

A simple RSS to email application.
Nibbler is a RSS aggregator that sends you a daily email newsletter.
It is headless, simple with minimal configuration.
It is designed to run once day and puts all of your articles in a single email for that previous day.

# Requirements

Nibbler is a python application tested on 3.+
I have only run it on Ubuntu Linux and Mac machines.

# Dependencies

Nibbler requires:

* A Mail Transfer Agent on the system, such as Sendmail or Postfix.
* It requires Python packages opml ,lxml, feedparser, SQLAlchemy, Jinja2

# Installation

nibbler hopes to be on pypi soon, otherwise, just run:

python3 nibbler <to_email> <from_email> <dir_to_subscriptions>

The from email should be for a domain on which you are running email. This will help prevent your email from going to spam.

Pass in the directory in which you have a subscriptions.xml (an OPML file) as the third argument.

I recommend using a cron job to run the aggregator and send the newsletter daily.

# License

MIT license, a permissive open-source license.

# Author

Randall Rodakowski
