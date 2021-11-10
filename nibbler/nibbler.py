#!/usr/bin/python
__author__ = 'Randall'

# system imports
from datetime import datetime
import sqlite3
import logging
import os
import traceback
import configparser

# opml and feedparser
import feedparser
import opml

# email imports
import smtplib  

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
            logger.warning("Nibbler could not find a post with guid: {}".format(guid))
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

    def add_full_image_path(self, article, link):
        domarticle = lxml.html.fromstring(article.encode("utf-8"))
        last_index = link.rindex('.')
        last_index = last_index + 4
        link_prefix = link[0: last_index]
        for img in domarticle.xpath('//img'):
            if 'http' not in img.attrib['src']:
                img.attrib['src'] = link_prefix + img.attrib['src']

        return lxml.html.tostring(domarticle).decode("utf-8")

    def add_email_markup(self, article):
        attrs = self.config.get_email_image_styles()
        domarticle = lxml.html.fromstring(article.encode("utf-8"))

        for img in domarticle.xpath('//img'):
            img.attrib['width'] = str(attrs['width'])
            img.attrib['height'] = str(attrs['height'])
            img.attrib['border'] = str(attrs['border'])
        return lxml.html.tostring(domarticle).decode("utf-8")


class FeedAcquirer(object):
    """ Parses rss feed and stores new posts """

    def __init__(self, dal, appconfig):
        self.dal = dal
        self.config = appconfig
        # move this to dependency injection?
        self.cleaner = HTMLNormalizer(appconfig)

    def parse_rss_post(self, post):
        """ parses rss feed for information this aggregator requires """
        article = Article()

        # Assume that all rss feeds have link populated
        try:
            article.link = post.link
        except:
            logger.error("There was no link in rss post. We need this value to proceed.")
            return None

        # time we acquired this content
        article.time_stamp = datetime.now()
        #time.strftime("%Y%m%d")

        # if there is no title, we will use link (which should always be there) as the title
        if "title" in post:
            article.title = post.title
        else:
            article.title = post.link

        # if there is no guid, we'll use the title as the guid
        # which above we set to have either the title or the link
        if "guid" in post:
            article.guid = post.guid
        else:
            article.guid = article.title

        logger.debug("We are parsing {}".format(article.guid))

        if "published" in post:
            article.pub_date = post.published
        else:
            article.pub_date = datetime.now().strftime("%Y%m%d")

        if "content" in post:
            article.article_text = self.cleaner.clean_html(post.content[0].value)
            article.article_text = self.cleaner.add_full_image_path(article.article_text, article.link)
        else:
            if "description" in post:
                article.article_text = self.cleaner.clean_html(post.description)
            else:
                article.article_text = "No article text is available, go to the site to read this article. "
        return article

    def store_new_content(self, feed):
        """ stores new posts in our database, so we will never send an email with them again """
        # get the feed data from the url
        rss_feed = feedparser.parse(feed.xmlUrl)

        for entry in rss_feed.entries:
            article = self.parse_rss_post(entry)
            if article is not None: # article comes back none if there is an error
                article.feed_id = feed.feed_id
                # if post is already in the database, skip it
                if not self.dal.is_post_in_db(article.guid):
                    posts_to_email.append(article.guid)
                    self.dal.store_post(article)
            else:
                logger.warning("We could not parse an article in feed {} and skipped it.".format(feed.feed_id))
        return posts_to_email

    def load_new_feeds(self):
        """ go through feeds to which we subscribe and add any new feeds to our database """
        sub_file = os.path.join(self.config.sub_dir, 'subscriptions.xml')
        outline = opml.parse(sub_file)
        # if there are feeds in subscription.xml that are not in the database, add them
        for feed in outline:
            if not self.dal.session.query(Feed).filter(Feed.xmlUrl == feed.xmlUrl).all():
                self.dal.session.add(Feed(feed.text, feed.xmlUrl))
                self.dal.session.commit()

    def main(self):
        """ Workflow for the acquring feeds """
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

    def build_html_email(self, from_email, to_email, subject, text, html, images):
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

        return msg_root

    def write_email_to_file(self, filename, email_msg):
        self.write_text_to_file(filename, email_msg.as_string())

    def send_smtp_email(self, sender, recipient, msg, host, port, smtp_username, smtp_password):
        # Try to send the message.
        try:    
            server = smtplib.SMTP(host, port)
            server.ehlo()
            server.starttls()
            #stmplib docs recommend calling ehlo() before & after starttls()
            server.ehlo()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender, recipient, msg.as_string())
            server.close()
        # Display an error message if something goes wrong.
        except Exception as e:
            logger.error("Send email message failed with error: ", e)
        else:
            logger.info("Send email message to: "+recipient)



class NibblerNewsletter(object):

    def __init__(self, dal, appconfig):
        logger.info("Init for BuildNibblerNewsletter")
        self.config = appconfig
        self.resource_dir = os.path.join(self.config.work_dir, "resources")
        self.es = EmailService()
        self.dal = dal

        # move this to dependency injection?
        self.cleaner = HTMLNormalizer(appconfig)

    def build_nibbler_newsletter(self, articles):
        subject = '{} {}'.format("Today's News Nibble -- ", datetime.now().ctime())
        env = Environment(loader=PackageLoader('nibbler', 'templates'))
        template = env.get_template('nibble.html')
        html = template.render(articles=articles)
        text = "Today's News Nibble"
        images = {"image1": os.path.join(self.resource_dir,"system.png"), "image2": os.path.join(self.resource_dir, "GitHub-Mark-Light-32px.png")}

        return self.es.build_html_email(self.config.from_email, self.config.to_email, subject, text, html, images)

    def main(self):
        logger.info("Starting to Build and Send the Nibbler Newsletter.")
        articles = []

        if posts_to_email:
            for guid in posts_to_email:
                article = self.dal.get_post(guid)
                email_html = self.cleaner.add_email_markup(article.article_text)
                article.article_text = email_html
                articles.append(article)
                logger.info("Getting content for post title {} from feed {}.".format(article.title, article.feed_title))

            msg = self.build_nibbler_newsletter(articles)
            smtp = self.config.get_smtp_config()
            email_filename = os.path.join(self.config.get_email_dir(), 'nibbler_{}.eml'.format(datetime.now().strftime('%Y%m%d')))
            if (smtp is None):
                # if no smtp is configured, we must do some output so we'll put it on the file system 
                self.es.write_email_to_file(email_filename, msg)
            else:
                # SMTP is configured, but if email_dir is also configured, let's also output to the file system
                self.es.send_smtp_email(self.config.from_email, self.config.to_email, msg, smtp['host'], smtp['port'], smtp['username'], smtp['password'])
                if (self.config._email_dir is not None):
                    self.es.write_email_to_file(email_filename, msg)
            

        logger.info("Finished the Newsletter.")


class NibblerConfig(object):
    """Processes configuration for Nibbler, current implementaton is to handle it as options on command line"""

    def __init__(self, to_email, from_email, sub_dir, log_dir=None, smtp_ini=None, db_dir=None, email_dir=None):
        logger.info("Initializing configuration")
        # Load configuration
        self.work_dir = os.path.dirname(os.path.abspath(__file__))   # finds the path to where nibbler executable is contained, need this to find resources
        self.cwd = os.getcwd()  # find the current working dir
        self.to_email = to_email
        self.from_email = from_email
        self.sub_dir = sub_dir
        self._log_dir = log_dir
        self._db_dir = db_dir
        self._email_dir = email_dir
        self._smtp_ini=smtp_ini

    def get_log_dir(self):
        if (self._log_dir is None):
            self._log_dir = self.cwd
        logger.debug("log_dir: " + self._log_dir)
        return self._log_dir

    def get_email_dir(self):
        if (self._email_dir is None):
            self._email_dir = self.cwd
        logger.debug("email_dir: " + self._email_dir)
        return self._email_dir

    def get_smtp_config(self):
        smtp_values = None
        if ((self._smtp_ini) is not None):
            logger.debug("smtp ini file provided")
            config = configparser.ConfigParser()
            config.read(self._smtp_ini)
            smtp_values={}
            smtp_values["username"] = config['smtp']['username']
            smtp_values["password"] = config['smtp']['password']
            smtp_values["host"] = config['smtp']['host']
            smtp_values["port"] = config['smtp']['port']
        return smtp_values

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


def run_nibbler(args):
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
    NibblerNewsletter(dal, config).main()
