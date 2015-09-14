from trello import TrelloClient
import os


alert_to_email = os.getenv('BOT_TO_EMAIL')
alert_from_email = os.getenv('BOT_FROM_EMAIL')
email_smtp_addr = os.getenv('BOT_SMTP_ADDR')
email_smtp_port = os.getenv('BOT_SMTP_PORT')
email_smtp_username = os.getenv['BOT_SMTP_USERNAME')
email_smtp_password = os.getenv('BOT_SMTP_PASSWORD')

board_id = os.getenv('BOT_BOARD_ID')
backlog_list_name = os.getenv('BOT_BACKLOG_NAME')
today_list_name = os.getenv('BOT_TODAY_NAME')
max_today_cards = os.getenv('BOT_MAX_TODAY')
max_backlog_move = os.getenv('BOT_MAX_MOVE')


client = TrelloClient(api_key='ea1990cff690e48f71749ef4a32559f9',
  api_secret='4cf7bbe49a67398b4aef37fca57e7509d49c9a95ce5ae911ac1c811492a9902d',
  token='9686a16148fccc263948800641d773dba086595413c5227b144110341731ba7c',
  token_secret='323e9cfc50eae066dc010aa084a2c523')

client.list_boards()
#[<Board Fall 2015>, <Board Welcome Board>]
board =client.list_boards()[0]
board.get_lists('all')
#[<List Exams>, <List Backlog>, <List Get Done Today>, <List Done>]
board.get_lists('open')
#[<List Exams>, <List Backlog>, <List Get Done Today>, <List Done>]
board.get_lists('open')[3]
#<List Done>
board.get_lists('open')[3].list_cards()
#[]
board.get_lists('open')[2].list_cards()
#[<Card Get book>, <Card Get book>]
board.get_lists('open')[2].list_cards()[0]
#<Card Get book>
board.get_lists('open')[1].id
#u'55c3bab34cf3abd5bf9f3b01'
board.get_lists('open')[2].list_cards()[0].change_list(u'55c3bab34cf3abd5bf9f3b01')
board.get_lists('open')[2].list_cards()[0].change_list(u'55c3bab34cf3abd5bf9f3b01')
