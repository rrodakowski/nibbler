# python3 library
import unittest
from unittest.mock import Mock, patch
import logging

# dependency imports
import feedparser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# nibbler imports
from nibbler.nibbler import NibblerConfig
from nibbler.nibbler import HTMLNormalizer
#from nibbler.nibbler import FeedAcquirer
#from nibbler.nibbler import DatabaseAccess
import nibbler.nibbler

class NibblerTestCase(unittest.TestCase):
    """Base class for all Nibbler tests."""
    arguments = {'from_email': 'randall.rodakowski@gmail.com', 'to_email': 'randall.rodakowski@gmail.com', 'log_dir': '/app-data/logs/nibbler-logs', 'sub_dir': '/app-bin', 'smtp_ini': './nibbler/tests/smtp_testdata.ini'}

    def assertCostEqual(self, p, cost):
        """Custom assert here: `p`'s cost is equal to `cost`."""
        self.assertEqual(p.cost(), cost)


class TestNibblerConfig(NibblerTestCase):

    def setUp(self):
        self.config = NibblerConfig(**self.arguments)

    def test_smtp_ini_with_values(self):
        smtp_config = self.config.get_smtp_config()
        self.assertEqual(smtp_config['username'], "sample_username")
        self.assertEqual(smtp_config['password'], "Sample_Password/")
        self.assertEqual(smtp_config['host'], "hostname.test.com")
        self.assertEqual(smtp_config['port'], '587')

    def test_smtp_ini_without_values(self):
        arguments = {'from_email': 'randall.rodakowski@gmail.com', 'to_email': 'randall.rodakowski@gmail.com', 'sub_dir': '/app-bin'}
        no_smtp_config = NibblerConfig(**arguments)
        self.assertEqual(no_smtp_config.get_smtp_config(), None)

    def test_log_dir(self):
        self.assertEqual(self.config.get_log_dir(), "/app-data/logs/nibbler-logs")

    def test_database_connection(self):
        self.assertEqual(self.config.get_database_connection(), "sqlite:///nibbler.db")

    def test_email_image_styles(self):
        values = self.config.get_email_image_styles()
        self.assertEqual(values["width"], 480)
        self.assertEqual(values["height"], 320)
        self.assertEqual(values["border"], 0)

    def tearDown(self):
        pass


class TestHTMLNormalizer(NibblerTestCase):

    def setUp(self):
        self.normalizer = HTMLNormalizer(NibblerConfig(**self.arguments))

    def test_clean_html(self):
        input_html = '<p>I <br/><span id="id-styles-text-to-remove">added some text </span><a class="my-class-to-remove" href="http://www.jamesaltucher.com/2017/03/matt-mullenweg/">joined in for the James Altucher<img width="480" id="id-to-remove" class=" size-full wp-image-47258 aligncenter" src="https://i1.wp.com/ma.tt/files/2017/04/ultralight.gif?resize=500%2C288&amp;ssl=1" alt="ultralight.gif"> podcast in an episode that covered a lot of ground</a>. It just needs to be two-way.</p>'
        clean_html = '<p>I added some text <a href="http://www.jamesaltucher.com/2017/03/matt-mullenweg/">joined in for the James Altucher<img src="https://i1.wp.com/ma.tt/files/2017/04/ultralight.gif?resize=500%2C288&amp;ssl=1" alt="ultralight.gif"> podcast in an episode that covered a lot of ground</a>. It just needs to be two-way.</p>'
        self.assertEqual(clean_html, self.normalizer.clean_html(input_html))

    def test_add_email_markup(self):
        clean_html = '<p>I added some text <a href="http://www.jamesaltucher.com/2017/03/matt-mullenweg/">joined in for the James Altucher<img src="https://i1.wp.com/ma.tt/files/2017/04/ultralight.gif?resize=500%2C288&amp;ssl=1" alt="ultralight.gif"> podcast in an episode that covered a lot of ground</a>. It just needs to be two-way.</p>'
        email_html = '<p>I added some text <a href="http://www.jamesaltucher.com/2017/03/matt-mullenweg/">joined in for the James Altucher<img src="https://i1.wp.com/ma.tt/files/2017/04/ultralight.gif?resize=500%2C288&amp;ssl=1" alt="ultralight.gif" width="480" height="320" border="0"> podcast in an episode that covered a lot of ground</a>. It just needs to be two-way.</p>'
        self.assertEqual(email_html, self.normalizer.add_email_markup(clean_html))

    def test_add_full_image_path(self):
        link = 'https://kottke.org/18/06/the-problem-with-action-scenes-in-dc-movies'
        input_html= '<p><img src="/plus/misc/images/ai-image-iso-02.jpg" alt="AI image in the dark"></p>'
        email_html = '<p><img src="https://kottke.org/plus/misc/images/ai-image-iso-02.jpg" alt="AI image in the dark"></p>'
        self.assertEqual(email_html, self.normalizer.add_full_image_path(input_html, link))


    def tearDown(self):
        pass


class TestFeedAcquirer(NibblerTestCase):

    def setUp(self):
        self.dal = Mock()
        self.feedacquirer = nibbler.nibbler.FeedAcquirer(self.dal, NibblerConfig(**self.arguments))

    def test_parse_rss_post_no_title(self):
        test_feed = """
        <feed xmlns="http://www.w3.org/2005/Atom">
        <title>Daring Fireball</title>
        <entry>
        <link rel="alternate" type="text/html" href="https://secure.actblue.com/donate/great_slate"/>
        <link rel="shorturl" type="text/html" href="http://df4.us/r7j"/>
        <link rel="related" type="text/html" href="https://daringfireball.net/linked/2018/10/25/donate-to-the-great-slate"/>
        <id>tag:daringfireball.net,2018:/linked//6.35263</id>
        <published>2018-10-26T03:59:00Z</published>
        <updated>2018-10-26T04:30:33Z</updated>
        <content type="html" xml:base="https://daringfireball.net/linked/" xml:lang="en">
        <![CDATA[
        <p>The Great Slate:</p> <blockquote> <p>Tech Solidarity is endorsing thirteen candidates for Congress. Each of them is a first-time progressive candidate with no ties to the political establishment, an excellent campaign team, and a clear path to victory in a poor, rural district that is being i
        ]]>
        </content>
        </entry>"""
        rss_feed = feedparser.parse(test_feed)
        title = 'https://secure.actblue.com/donate/great_slate'
        for entry in rss_feed.entries:
            article = self.feedacquirer.parse_rss_post(entry)
            self.assertEqual(title, article.title, msg='{}, {}'.format(title, article.title))

    def test_parse_rss_post_with_title(self):
        test_feed = """
        <feed xmlns="http://www.w3.org/2005/Atom">
        <title>Daring Fireball</title>
        <entry>
        <title>Daring Fireball post</title>
        <link rel="alternate" type="text/html" href="https://secure.actblue.com/donate/great_slate"/>
        <link rel="shorturl" type="text/html" href="http://df4.us/r7j"/>
        <link rel="related" type="text/html" href="https://daringfireball.net/linked/2018/10/25/donate-to-the-great-slate"/>
        <id>tag:daringfireball.net,2018:/linked//6.35263</id>
        <published>2018-10-26T03:59:00Z</published>
        <updated>2018-10-26T04:30:33Z</updated>
        <content type="html" xml:base="https://daringfireball.net/linked/" xml:lang="en">
        <![CDATA[
        <p>The Great Slate:</p> <blockquote> <p>Tech Solidarity is endorsing thirteen candidates for Congress. Each of them is a first-time progressive candidate with no ties to the political establishment, an excellent campaign team, and a clear path to victory in a poor, rural district that is being i
        ]]>
        </content>
        </entry>"""
        rss_feed = feedparser.parse(test_feed)
        title = 'Daring Fireball post'
        for entry in rss_feed.entries:
            article = self.feedacquirer.parse_rss_post(entry)
            self.assertEqual(title, article.title, msg='{}, {}'.format(title, article.title))

    def test_parse_rss_post_no_guid(self):
        test_feed = """
        <feed xmlns="http://www.w3.org/2005/Atom">
        <title>Daring Fireball</title>
        <entry>
        <title>Daring Fireball post</title>
        <link rel="alternate" type="text/html" href="https://secure.actblue.com/donate/great_slate"/>
        <link rel="shorturl" type="text/html" href="http://df4.us/r7j"/>
        <link rel="related" type="text/html" href="https://daringfireball.net/linked/2018/10/25/donate-to-the-great-slate"/>

        <published>2018-10-26T03:59:00Z</published>
        <updated>2018-10-26T04:30:33Z</updated>
        <content type="html" xml:base="https://daringfireball.net/linked/" xml:lang="en">
        <![CDATA[
        <p>The Great Slate:</p> <blockquote> <p>Tech Solidarity is endorsing thirteen candidates for Congress. Each of them is a first-time progressive candidate with no ties to the political establishment, an excellent campaign team, and a clear path to victory in a poor, rural district that is being i
        ]]>
        </content>
        </entry>"""
        rss_feed = feedparser.parse(test_feed)
        guid = 'Daring Fireball post'
        for entry in rss_feed.entries:
            article = self.feedacquirer.parse_rss_post(entry)
            self.assertEqual(guid, article.guid, msg='{}, {}'.format(guid, article.guid))

    def test_parse_rss_post_with_guid(self):
        test_feed = """
        <feed xmlns="http://www.w3.org/2005/Atom">
        <title>Daring Fireball</title>
        <entry>
        <link rel="alternate" type="text/html" href="https://secure.actblue.com/donate/great_slate"/>
        <link rel="shorturl" type="text/html" href="http://df4.us/r7j"/>
        <link rel="related" type="text/html" href="https://daringfireball.net/linked/2018/10/25/donate-to-the-great-slate"/>
        <id>tag:daringfireball.net,2018:/linked//6.35263</id>
        <published>2018-10-26T03:59:00Z</published>
        <updated>2018-10-26T04:30:33Z</updated>
        <content type="html" xml:base="https://daringfireball.net/linked/" xml:lang="en">
        <![CDATA[
        <p>The Great Slate:</p> <blockquote> <p>Tech Solidarity is endorsing thirteen candidates for Congress. Each of them is a first-time progressive candidate with no ties to the political establishment, an excellent campaign team, and a clear path to victory in a poor, rural district that is being i
        ]]>
        </content>
        </entry>"""
        rss_feed = feedparser.parse(test_feed)
        guid = 'tag:daringfireball.net,2018:/linked//6.35263'
        for entry in rss_feed.entries:
            article = self.feedacquirer.parse_rss_post(entry)
            self.assertEqual(guid, article.guid, msg='{}, {}'.format(guid, article.guid))

    def test_parse_rss_post_with_pub_date(self):
        test_feed = """
        <feed xmlns="http://www.w3.org/2005/Atom">
        <title>Daring Fireball</title>
        <entry>
        <link rel="alternate" type="text/html" href="https://secure.actblue.com/donate/great_slate"/>
        <link rel="shorturl" type="text/html" href="http://df4.us/r7j"/>
        <link rel="related" type="text/html" href="https://daringfireball.net/linked/2018/10/25/donate-to-the-great-slate"/>
        <id>tag:daringfireball.net,2018:/linked//6.35263</id>
        <published>2018-10-26T03:59:00Z</published>
        <updated>2018-10-26T04:30:33Z</updated>
        <content type="html" xml:base="https://daringfireball.net/linked/" xml:lang="en">
        <![CDATA[
        <p>The Great Slate:</p> <blockquote> <p>Tech Solidarity is endorsing thirteen candidates for Congress. Each of them is a first-time progressive candidate with no ties to the political establishment, an excellent campaign team, and a clear path to victory in a poor, rural district that is being i
        ]]>
        </content>
        </entry>"""
        rss_feed = feedparser.parse(test_feed)
        pub_date = '2018-10-26T03:59:00Z'
        for entry in rss_feed.entries:
            article = self.feedacquirer.parse_rss_post(entry)
            self.assertEqual(pub_date, article.pub_date, msg='{}, {}'.format(pub_date, article.pub_date))

    #@patch('nibbler.nibbler.DatabaseAccess.is_post_in_db')
    #@patch('nibbler.nibbler.DatabaseAccess.store_post')
    @patch('nibbler.nibbler.DatabaseAccess')
    def test_store_new_content(self, mock_dal):
        feed = Mock()
        feed.xmlUrl = """
        <feed xmlns="http://www.w3.org/2005/Atom">
        <title>Daring Fireball</title>
        <entry>
        <title>Daring post</title>
        <link rel="alternate" type="text/html" href="https://secure.actblue.com/donate/great_slate"/>
        <link rel="shorturl" type="text/html" href="http://df4.us/r7j"/>
        <link rel="related" type="text/html" href="https://daringfireball.net/linked/2018/10/25/donate-to-the-great-slate"/>
        <id>tag:daringfireball.net,2018:/linked//6.35263</id>
        <published>2018-10-26T03:59:00Z</published>
        <updated>2018-10-26T04:30:33Z</updated>
        <content type="html" xml:base="https://daringfireball.net/linked/" xml:lang="en">
        <![CDATA[
        <p>The Great Slate:</p> <blockquote> <p>Tech Solidarity is endorsing thirteen candidates for Congress. Each of them is a first-time progressive candidate with no ties to the political establishment, an excellent campaign team, and a clear path to victory in a poor, rural district that is being i
        ]]>
        </content>
        </entry>"""
        feed.feed_id = 1

        mock_dal.is_post_in_db.return_value = False
        mock_dal.store_post.return_value = True
        #mock_is_post_in_db.return_value.is_post_in_db.return_value = False # means we will add it
        #mock_store_post.return_value = True
        feedacquirer = nibbler.nibbler.FeedAcquirer(mock_dal, NibblerConfig(**self.arguments))
        articles_stored = feedacquirer.store_new_content(feed)
        self.assertEqual("tag:daringfireball.net,2018:/linked//6.35263", articles_stored[0])

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
