# Overview

A simple RSS to email application.
Nibbler is a RSS aggregator that sends you a daily email newsletter.
It is headless, simple with minimal configuration.
It is designed to run once day and puts all of your articles in a single email for that previous day.

# Requirements

Nibbler is a python application tested on 3.+
I have only run it on *nix machines.

# Dependencies

Nibbler requires:

* A Mail Transfer Agent on the system, such as Sendmail or Postfix.
* It requires Python packages OPML and sqlalchemy

# Installation

nibbler hopes to be on pypi soon, otherwise, just run:

python3 nibbler <to_email>

I recommend using a cron job to run the aggregator and send the newsletter daily.

# License

MIT license, a permissive open-source license.

# Author

Randall Rodakowski
