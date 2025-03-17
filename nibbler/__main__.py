import argparse

from nibbler.nibbler import run_nibbler


def main():
    parser = argparse.ArgumentParser(prog='nibbler', description='A simple RSS to email application.')
    parser.add_argument('to_email', metavar='to_email', help='Recipient email address; youremail@example.com')
    parser.add_argument('from_email', metavar='from_email', help='Sender email address; nibble@example.com')
    parser.add_argument('sub_dir', metavar='sub_dir', help='path to subscriptions.xml file')
    parser.add_argument('-l', '--log-dir', metavar='log_dir', help='optional path to log dir')
    parser.add_argument('-s', '--smtp-ini', metavar='smtp_ini', help='optional path to smtp ini file')
    parser.add_argument('-d', '--db-dir', metavar='db_dir', help='optional path to sqlite db dir')
    parser.add_argument('-e', '--email-dir', metavar='email_dir', help='optional path to directory where email file is output before sending')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.3')

    args = parser.parse_args()

    run_nibbler(args)


if __name__ == '__main__':
    main()
