#!/usr/bin/python
__author__ = 'Randall'

# system imports
from datetime import datetime
import sqlite3
import logging
import os
import string
import traceback
import argparse

# opml and feedparser
import feedparser
import opml

# email imports
from subprocess import call

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email import charset

# jinja2 imports
from jinja2 import Environment, PackageLoader

# lxml imports
from lxml.html.clean import Cleaner
import lxml.html

# SqlAlchemy imports
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String, Date, Sequence
from sqlalchemy import ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select
import sqlalchemy



logger = logging.getLogger(__name__)

# figure out which posts to email
posts_to_email = []
base = declarative_base()
config = None


def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


class Feed(base):
    __tablename__ = 'nibbler_feed'
    feed_id = Column(Integer, primary_key=True)
    title = Column(String(64))
    xmlUrl = Column(String(256))
    description = Column(String(256))

    def __init__(self, title, xmlUrl, description=None):
        self.title=title
        self.xmlUrl=xmlUrl
        self.description=description

    def __repr__(self):
        return '<nibbler_feed%r>' % (self.feed_id)


class Article(base):
    __tablename__ = 'nibbler_post'
    post_id = Column(Integer, primary_key=True)
    feed_id = Column(Integer, ForeignKey("nibbler_feed.feed_id"))
    guid = Column(String(64))
    title = Column(String(256))
    link = Column(String(256))
    pub_date = Column(String(128))
    article_text = Column(String(65535))
    time_stamp = Column(Date)
    # we need stuff on all instances, but not in the database.
    feed_title = None # optional value

    def __repr__(self):
        return '<nibbler_post%r>' % (self.post_id)


class DatabaseAccess(object):

    def __init__(self, connection_str):
        logger.debug("Creating Data Access")
        db_engine = None
        db_engine = sqlalchemy.create_engine(connection_str)
        #this line will try to make the tables in database, if they aren't there
        base.metadata.create_all(db_engine)
        logger.debug("Connected to: {}".format(connection_str))
        Session = sessionmaker(bind=db_engine)
        self.session = Session()

    def get_post(self, guid):
        results = self.session.query(Article, Feed).filter(Article.feed_id == Feed.feed_id).filter(Article.guid == guid).all()
        if not results:
            logger.warn("Nibbler could not find a post with guid: {}".format(guid))
        else:
            # convert list of tuples into one article object
            article_info = results[0]
            article = article_info[0]
            article.feed_title = article_info[1].title
            return article

    def store_post(self, post):
        logger.info("Inserting {} in the database".format(post.guid))
        self.session.add(post)
        self.session.commit()

    def is_post_in_db(self, guid):
        logger.debug("determining if post {} is in the database".format(guid))
        article = self.session.query(Article).filter_by(guid=guid).all()
        if not article:
            logger.debug("{} is NOT in the database".format(guid))
            return False
        logger.debug("{} is in the database".format(guid))
        return True


class HTMLNormalizer(object):

    def __init__(self, appconfig):
        self.config = appconfig
        # setup lxml's html cleaner
        self.cleaner = Cleaner()
        self.cleaner.style = True # activate the styles and stylesheet filter
        self.cleaner.javascript = True # activate the javascript filter
        self.cleaner.remove_tags = ['span'] # some spans have text inside we want to keep
        self.cleaner.kill_tags = ['br'] # just axe this altogether, including children nodes

    def clean_html(self, input_html):
        attributes = ['class', 'id', 'style', 'width', 'height', 'border']
        cleaner_html = self.cleaner.clean_html(input_html)

        domhtml = lxml.html.fromstring(cleaner_html)

        for attribute in attributes:
            # xpath for attribute looks like: '//*[@id]'
            for tag in domhtml.xpath('//*[@{}]'.format(attribute)):
                # For each element with a class attribute, remove that class attribute
                tag.attrib.pop(attribute)
        return lxml.html.tostring(domhtml).decode("utf-8")

    def add_email_markup(self, article):
        attrs = self.config.get_email_image_styles()
        domarticle = lxml.html.fromstring(article.encode("utf-8"))

        for img in domarticle.xpath('//img'):
            img.attrib['width']=str(attrs['width'])
            img.attrib['height']=str(attrs['height'])
            img.attrib['border']=str(attrs['border'])
        return lxml.html.tostring(domarticle).decode("utf-8")


class FeedAcquirer(object):

    def __init__(self, dal, appconfig):
        self.dal = dal
        self.config = appconfig
        # move this to dependency injection?
        self.cleaner = HTMLNormalizer(appconfig)

    def parse_rss_post(self, post):
        article = Article()
        # Assume that most rss feeds have title and link populated
        article.title = post.title
        article.link = post.link
        # time we acquired this content
        article.time_stamp = datetime.now()
        #time.strftime("%Y%m%d")
        if "guid" in post:
            article.guid = post.guid
        else:
            article.guid = post.title

        logger.debug("We are parsing {}".format(article.guid))

        if "published" in post:
            article.pub_date = post.published
        else:
            article.pub_date = datetime.now().strftime("%Y%m%d")

        if "content" in post:
            article.article_text = self.cleaner.clean_html(post.content[0].value)
        else:
            if "description" in post:
                article.article_text = self.cleaner.clean_html(post.description)
            else:
                article.article_text = "No article text is available, go to the site to read this article. "
        return article

    def store_new_content(self, feed):
        # get the feed data from the url
        rss_feed = feedparser.parse(feed.xmlUrl)

        for entry in rss_feed.entries:
            article = self.parse_rss_post(entry)
            article.feed_id=feed.feed_id
             # if post is already in the database, skip it
            if not self.dal.is_post_in_db(article.guid):
                posts_to_email.append(article.guid)
                self.dal.store_post(article)

    def load_new_feeds(self):
        sub_file = os.path.join(self.config.get_sub_dir(), 'subscriptions.xml')
        outline = opml.parse(sub_file)
        # if there are feeds in subscription.xml that are not in the database, add them
        for feed in outline:
            if not self.dal.session.query(Feed).filter(Feed.xmlUrl == feed.xmlUrl).all():
                self.dal.session.add(Feed(feed.text, feed.xmlUrl))
                self.dal.session.commit()

    def main(self):
        logger.info("Starting to Acquire Content.")

        self.load_new_feeds()
        # get all the feeds to aggregate
        feeds = self.dal.session.query(Feed).all()

        for feed in feeds:
            logger.info("Getting content for feed_id {} from {}.".format(feed.feed_id, feed.xmlUrl))
            self.store_new_content(feed)

        logger.info("Finished Acquiring Content.")


class EmailService(object):
    """Contains helpful functions related to working with emails"""

    def __init__(self):
        logger.info("Init for EmailService")

    @staticmethod
    def write_text_to_file(filename, text):
        logger.info("Writing the file: "+filename)
        file = open(filename, "w")
        for line in text:
            file.write(line)
        file.close()

    def build_html_email(self, from_email, to_email, subject, text, html, images, output_email_file):
        logger.info("Creating an html email file. ")
        # couldn't figure out how to get the email to display so that it wasn't base64 encoded
        # this post on the interweb pointed out this line
        # http://bugs.python.org/issue12552
        charset.add_charset('utf-8', charset.SHORTEST, charset.QP)

        # Create message container - the correct MIME type is multipart/alternative.
        msg_root = MIMEMultipart('alternative')
        msg_root['Subject'] = subject
        msg_root['From'] = from_email
        msg_root['To'] = to_email

        # Record the MIME types of both parts - text/plain and text/html.
        plain_text = MIMEText(text, 'plain')
        html_text = MIMEText(html, 'html')

        logger.info("Added headers. ")

        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        msg_root.attach(plain_text)
        msg_root.attach(html_text)
        logger.info("Added body. ")

        for image_id in images:
            logger.info("Added image: {} ".format(image_id))
            # This example assumes the image is in the current directory
            image_path = images[image_id]
            try:
                fp = open(image_path, 'rb')
                msg_image = MIMEImage(fp.read())
                fp.close()
            except:
                logger.error("Could not attach image file {}".format(image_path))
                logger.error(traceback.format_exc())

            # Define the image's ID as referenced above
            msg_image.add_header('Content-ID', '<{}>'.format(image_id))
            msg_root.attach(msg_image)

        self.write_text_to_file(output_email_file, msg_root.as_string())

    @staticmethod
    def send_email_file(email_file, to_email_address):
        logger.info("Send email message to: "+to_email_address)
        call('sendmail -v {} < {}'.format(to_email_address, email_file), shell=True)


class Newsletter(object):

    def __init__(self, dal, appconfig):
        logger.info("Init for BuildNewsletter")
        self.config = appconfig
        self.filename = os.path.join(self.config.get_email_dir(), 'nibbler_{}.eml'.format(datetime.now().strftime('%Y%m%d')))
        self.es = EmailService()
        self.dal = dal

        # move this to dependency injection?
        self.cleaner = HTMLNormalizer(appconfig)

    def build_newsletter(self, articles):
        subject = '{} {}'.format("Today's News Nibble -- ", datetime.now().ctime())
        env = Environment(loader=PackageLoader('nibbler', 'templates'))
        template = env.get_template('nibble.html')
        html = template.render(articles=articles)
        text = "Today's News Nibble"
        images = {"image1": "./resources/system.png", "image2": "./resources/GitHub-Mark-Light-32px.png"}

        self.es.build_html_email(self.config.from_email, self.config.to_email, subject, text, html, images, self.filename)

    def main(self):
        logger.info("Starting to Build Newsletter.")
        articles = []

        if posts_to_email:
            for guid in posts_to_email:
                article = self.dal.get_post(guid)
                email_html = self.cleaner.add_email_markup(article.article_text)
                article.article_text = email_html
                articles.append(article)
                logger.info("Getting content for post title {} from feed {}.".format(article.title, article.feed_title))

            self.build_newsletter(articles)
            self.es.send_email_file(self.filename, self.config.to_email)

        logger.info("Finished the Newsletter.")


class NibblerConfig(object):
    """Processes configuration for Nibbler, current implementaton is to handle it as options on command line"""

    def __init__(self, to_email, log_dir=None, sub_dir=None, db_dir=None, email_dir=None, from_email=None):
        logger.info("Initializing configuration")
        # Load configuration
        self.work_dir = os.path.dirname(os.path.abspath(__file__))
        self.to_email = to_email
        self._log_dir = log_dir
        self._sub_dir = sub_dir
        self._db_dir = db_dir
        self._email_dir = email_dir
        if (from_email is None):
            self.from_email = 'nibbler@nibbler.com'

    def get_log_dir(self):
        if (self._log_dir is None):
            self._log_dir = self.work_dir
        logger.debug("log_dir: " + self._log_dir)
        return self._log_dir

    def get_sub_dir(self):
        if (self._sub_dir is None):
            self._sub_dir = self.work_dir
        logger.debug("sub_dir: " +self._sub_dir)
        return self._sub_dir

    def get_email_dir(self):
        if (self._email_dir is None):
            self._email_dir = self.work_dir
        logger.debug("email_dir: " + self._email_dir)
        return self._email_dir

    def get_email_image_styles(self):
        key_values={}
        key_values["height"] = 320
        key_values["width"] = 480
        key_values["border"] = 0
        return key_values

    def get_database_connection(self):
        connection_str = None
        # Setup Database Connection Information
        db_file = "nibbler.db"
        if (self._db_dir is None):
            connection_str = 'sqlite:///{}'.format(db_file)
        else:
            ensure_dir(self._db_dir)
            connection_str = 'sqlite:///{}/{}'.format(self._db_dir, db_file)
        return connection_str


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='nibbler', description='A simple RSS to email application.')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.1')
    parser.add_argument('to_email', metavar='to_email', help='To email address; youremail@example.com')
    parser.add_argument('-l', '--log-dir', metavar='log_dir', help='path to log dir')
    parser.add_argument('-d', '--db-dir', metavar='db_dir', help='path to sqlite db dir')
    parser.add_argument('-s', '--sub-dir', metavar='sub_dir', help='path to subscriptions.xml file')
    parser.add_argument('-e', '--email-dir', metavar='email_dir', help='path to diretory where email file is output before sending')
    parser.add_argument('-f', '--from_email', metavar='from_email', help='From email address; nibble@nibbler.com')
    args = parser.parse_args()

    # Initialize configuration
    arguments = vars(args)
    config = NibblerConfig(**arguments)

    # Setup logging
    ensure_dir(config.get_log_dir())
    logfile = os.path.join(config.get_log_dir(), "nibbler_{}.log".format(datetime.now().strftime('%Y%m%d')))
    logging.basicConfig(filename=logfile, level=logging.DEBUG, format='%(asctime)s %(levelname)s %(module)s %(message)s')

    dal = DatabaseAccess(config.get_database_connection())

    # Get articles
    FeedAcquirer(dal, config).main()

    # Send Newsletter
    Newsletter(dal, config).main()
