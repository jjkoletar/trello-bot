from trello import TrelloClient
from ConfigParser import RawConfigParser
import datetime

# Let's get set up with all our lovely configuration variables.
config = RawConfigParser()
config.read(['bot.cfg', 'dev_secrets.cfg', 'bot_secrets.cfg'])

email_recipient = config.get('email', 'to_address')
email_sender = config.get('email', 'sender_address')
email_smtp_address = config.get('email', 'smtp_hostname')
email_smtp_ssl = config.getboolean('email', 'smtp_use_ssl')
email_smtp_port = config.getint('email', 'smtp_port')
email_smtp_username = config.get('email', 'smtp_username')
email_smtp_password = config.get('email', 'smtp_password')

trello_api_key = config.get('trello', 'api_key')
trello_api_secret = config.get('trello', 'api_secret')
trello_oauth_token = config.get('trello', 'oauth_token')
trello_oauth_secret = config.get('trello', 'oauth_secret')

board_name = config.get('behavior', 'board_name')
backlog_name = config.get('behavior', 'backlog')
today_name = config.get('behavior', 'today')
max_today_cards = config.getint('behavior', 'max_today_cards')

# Credit to Sam Edwards (CFSworks) for the following function, which he wrote for another script.
import re, argparse, datetime
def parse_delay(value):
    match = re.match(r'^((\d+)d)?(([0-5]?\d)h)?(([0-5]?\d)m)?(([0-5]?\d)s)?$', value)
    if not match:
        raise argparse.ArgumentTypeError('invalid delay')

    attributes = {}
    for group, attr in [(2, 'days'), (4, 'hours'), (6, 'minutes'), (8, 'seconds')]:
        if match.group(group):
            attributes[attr] = int(match.group(group))

    return datetime.timedelta(**attributes)

do_today_distance = parse_delay(config.get('behavior', 'do_today_distance'))



client = TrelloClient(api_key=trello_api_key,
    api_secret=trello_api_secret,
    token=trello_oauth_token,
    token_secret=trello_oauth_secret
)

def trello_search(haystack, needle, property='name', thing=''):
    """
    Just a crappy little 'search and match' function.

    Anything other than a single match will result in a RuntimeError
    """
    found = None
    for x in haystack:
        if str(getattr(x, property)).strip() == needle.strip():
            if found is not None:
                raise RuntimeError('%s name is ambiguous! (searching for %s in %s)' % (thing, needle, haystack))

            found = x

    if found is None:
        raise RuntimeError("I was unable to find the %s named '%s'" % (thing, board_name))

    return found

def trello_sort(cards):
    """
    Sort a pythonic list of cards.

    At the top of the list will be all cards which do not have a due date.
    These cards will be in alphabetical order.

    Below that will be all cards with a due date.
    They will be sorted by how soon they are due.
    """
    # Split the cards into dated and undated.
    dated = []
    undated = []

    for x in cards:
        if x.due:
            dated += [x]
        else:
            undated += [x]

    # Alphabetize the undated cards.
    undated.sort(key=lambda x: x.name)

    # Sort the dated cards by due date.
    dated.sort(key=lambda x: x.due_date)

    return undated + dated

def get_backfill_label(board):
    """
    Grab the trello.Label instance for what we call 'backfill'.

    Backfilled cards are cards that would normally be in your Today list,
    but couldn't be moved due to the Today list being too big.
    """
    for x in board.get_labels():
        if x.color == 'red': return x
    raise RuntimeError('could not find backfill label :(')

def ensure_backfill_label(card, present=True):
    """
    Ensure that the backfill label is present (or not).
    """
    backfill_label = get_backfill_label(card.board)

    # OK, so, is the backfill label present or not?
    is_presently_present = None
    labels_on_card = card.list_labels
    if labels_on_card is None:
        # I guess we'll take that as a no then...
        is_presently_present = False
    else:
        is_presently_present = backfill_label.id in [x.id for x in labels_on_card]

    assert is_presently_present is not None
    if is_presently_present == present: return # cool
    if present:
        # We need to add the label.
        card.add_label(backfill_label)
    else:
        # We need to remove the label.
        # HACK: the commit adding remove_label hasn't been pushed to PyPi yet.
        card.client.fetch_json('/cards/' + card.id + '/idLabels/' + backfill_label.id, http_method='DELETE')

board = trello_search(client.list_boards(), board_name, thing='Board')

backlog = trello_search(board.open_lists(), backlog_name, thing='List')
today = trello_search(board.open_lists(), today_name, thing='List')

# Fetch lists of cards.
backlog_cards = backlog.list_cards()
# While we're at it, grab the today list too.
today_cards = today.list_cards()

# Some gunk to work around py-trello being weird.
# call 'fetch' on all cards we'll be playing with (this grabs the due date)
for x in backlog_cards + today_cards: x.fetch()


# Let's work on the backlog. We need to find out what dated cards are ready for you to work on.
now = datetime.datetime.utcnow()
ready_to_work_on = []
for x in backlog_cards:
    if not x.due: continue
    # HACK!!!
    if x.due_date.tzinfo and not now.tzinfo:
        now = datetime.datetime.now(x.due_date.tzinfo)

    if abs(do_today_distance.total_seconds()) > (x.due_date - now).total_seconds():
        # x is ready to be worked on.
        ready_to_work_on += [x]

# Sort ready_to_work_on in order of due soonest to due latest.
ready_to_work_on = trello_sort(ready_to_work_on)

# Now we need to check out the today list. How much should we move in?
today_space = max(0, max_today_cards - len(today_cards)) # clamp the value to 0

# TODO: I wonder if this should be less "well let's just move them right now."
# i.e., maybe we'll want to note the names of all the cards we moved, so we should save that.
if today_space > 0:
    for x in ready_to_work_on[:today_space]:
        x.change_list(today.id)
        # Remove the backfill label, in case the card was previously backfilled.
        ensure_backfill_label(x, present=False)

# For all the cards we would've put into the Today list, but we didn't have room for,
# label them with the backfill label.
for x in ready_to_work_on[today_space:]:
    ensure_backfill_label(x, present=True)


# For newly-archived cards that have the special !recur thing in their description,
# we'll reset them back.
for x in board.closed_cards():
    x.fetch()
    if '!recur' in x.description:
        new_due = None
        try:
            bits = x.description.split()
            td = parse_delay(bits[bits.index('!recur') + 1])
            new_due = x.due_date + td
        except Exception, e:
            email_log += "[-] There was a problem with the recurring card '%s'. It threw this exception: %s\n" % (x.name, e)
        if new_due is not None:
            x.set_due(new_due)
            x.set_closed(False)
            x.change_list(backlog.id)
            # Make sure to reset backfill off
            ensure_backfill_label(x, present=False)

            # Hey, maybe we have an auto-incrementing title, too.
            if '!title' in x.description:
                # Try to re-title the card.
                try:
                    x.fetch()
                    new_index = int(x.name.split()[-1:][0]) + 1
                    title = [y for y in x.description.split('\n') if '!title' in y][0].split()[1:]
                    x.set_name('%s %d' % (' '.join(title), new_index))
                except Exception, e:
                    email_log += "[-] There was a problem re-titling the recurring card '%s'. It threw this exception: %s\n" % (x.name, e)

print email_log
# Now, and this is done last intentionally, it's time to sort all the cards in the
# backlog and today lists by date due/alphabetically.
# We're going to actually start by repopulating our today_cards and backlog_cards lists,
# simply because I don't trust myself to keep up with all the card movement.

backlog_cards = backlog.list_cards()
today_cards = today.list_cards()
for x in backlog_cards + today_cards: x.fetch()

def trello_sort_list(cards):
    """
    Takes an unsorted pythonic list of cards (which all should be from the same trello
    list) and updates their ordering on trello.
    """
    for i, x in enumerate(trello_sort(cards)):
        x.set_pos(i + 1)

trello_sort_list(backlog_cards)
trello_sort_list(today_cards)
