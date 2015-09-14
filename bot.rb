require 'trello'
require 'pony'
load 'config.rb'

# Email config
@alert_to_email = ENV['BOT_TO_EMAIL']
@alert_from_email = ENV['BOT_FROM_EMAIL']
@email_smtp_addr = ENV['BOT_SMTP_ADDR']
@email_smtp_port = ENV['BOT_SMTP_PORT']
@email_smtp_username = ENV['BOT_SMTP_USERNAME']
@email_smtp_password = ENV['BOT_SMTP_PASSWORD']

@board_id = ENV['BOT_BOARD_ID']
@backlog_list_name = ENV['BOT_BACKLOG_NAME']
@today_list_name = ENV['BOT_TODAY_NAME']
@max_today_cards = ENV['BOT_MAX_TODAY'].to_i
@max_backlog_move = ENV['BOT_MAX_MOVE'].to_i

Trello.configure do |config|
  config.developer_public_key = ENV['BOT_TRELLO_KEY']
  config.member_token = ENV['BOT_TRELLO_TOKEN']
end

board = Trello::Board.find(@board_id)
# Yes... this library's 'find' function does not work properly...
# Get all of the lists then filter the array. :/
backlog_list = board.lists.find { |s| s.name.include? @backlog_list_name }
today_list = board.lists.find { |s| s.name.include? @today_list_name }

backlog_cards = backlog_list.cards
today_cards = today_list.cards

if today_cards.count > @max_today_cards
  send_mail('[Trello] TODAY LIST FULL!', 'warning. Your list ' + @today_list_name.to_s + ' is full with a max of ' + @max_today_cards.to_s)
  exit
end

now_time = Time.now
then_time = 1.day.from_now.end_of_day
move_count = 0;
moved_cards = Array[]

backlog_cards.each do |card|
  if card.due.between?(now_time, then_time)
    if move_count <= @max_backlog_move
      card.move_to_list(today_list.id)
      moved_cards << card
      move_count += move_count
    else
      send_mail('[Trello] TOO MANY THINGS TOMORROW!', 'warning. Your list ' + @backlog_list_name.to_s + ' has too many things due tomorrow... GOOD LUCK! ')
      break
    end
  end
end

send_mail('[Trello] Moved Stuff to Today', 'I moved ' + move_count.to_s + 'cards')

def send_mail(subject, body)
  Pony.mail(to: @alert_to_email,
            from: @alert_from_email,
            subject: subject,
            body: body,
            via: :smtp,
            via_options: {
              address: @email_smtp_addr,
              port: @email_smtp_port,
              enable_starttls_auto: true,
              user_name: @email_smtp_username,
              password: @email_smtp_password,
              authentication: :plain, # :plain, :login, :cram_md5, no auth by default
              domain: 'localhost.localdomain' # the HELO domain provided by the client to the server
            })
end
