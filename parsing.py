import re

MIN_BET_THRESH = 1
ALL_IN_THRESH = .8

re_game_id = re.compile(r'\*\*\*\*\* Hand History for Game (\d+) \*\*\*\*\*')
re_pip = re.compile(r'(.*) (posts small blind|posts big blind|is all-In|raises|bets|calls) \[\$(\d+)(\.(\d\d))? USD\].*')
re_seat = re.compile(r'Seat \d: (.*) \( \$(\d+)(\.(\d\d))? USD \)')

file_counter = 0
num_files = 10
filename = "histories/knufelbrujk_hotmail_com_PTY_NLH100_3-6plrs_x10k_1badb/pty NLH handhq_%d"
#filename = "histories/knufelbrujk_hotmail_com_PTY_NLH100_2-2plrs_x10k_f8534/pty NLH handhq_%d"

bets = []

class Game :
    def __init__(self, name) :
        self.name = name
        self.pot = 0
        self.big_blind = -1
        self.stacks = {}
        self.active_players = -1
        self.total_players = -1

        #bet/raise
        self.num_aggressive = [-1]*4
        #check/call
        self.num_passive = [-1]*4

        self.all_in_with_call = False
        self.amount_to_call = -1

        self.average_rank = -1
        self.callers_since_last_raise = -1

        self.effective_stack_vs_active = -1
        self.effective_stack_vs_aggressor = -1

        self.high_card_flop = -1
        self.high_card_turn = -1
        self.high_card_river = -1

        self.implied_odds_vs_aggressor = -1



def reGroupsToAmount( dollar_group, cent_group ) :
    dollars = int(dollar_group)
    if cent_group :
        cents = float(cent_group) / 100
    else : cents = 0
    return dollars+cents

while file_counter < num_files :
    fin = open("%s.txt" % filename % file_counter)

    games = []
    game = {"id" : "init", \
            "pot" : 42, \
            "big_blind" : 42, \
            "stacks" : {}, \
            "active_players" : 0}

    line_count = 0
    for line in fin.readlines() :
        line = line.strip()
        #print line
        m = re_game_id.match(line)
        if m :
            #finish processing last game
            #print file_counter
            #print "\ngame: ", game['id'], "pot was: ", game['pot']
            #print "bigblind: " , game['big_blind']
            #print "stacks: ", game['stacks']

            #print "\nnew game: " , m.group(1)
            game = {"id" : int(m.group(1)), \
                    "pot" : 0, \
                    "big_blind" : 42, \
                    "stacks" : {}}

        else :
            mseat = re_seat.match(line)
            mpip = re_pip.match(line)
            if mseat :
                player = mseat.group(1)
                stack = reGroupsToAmount( mseat.group(2), mseat.group(4) )
                game['stacks'][player] = stack

            if mpip :
                player = mpip.group(1)
                is_blind = mpip.group(2) == "posts small blind" or \
                           mpip.group(2) == "posts big blind"

                bet = reGroupsToAmount( mpip.group(3), mpip.group(5) )
                game['pot'] += bet
                try :
                    game['stacks'][player] -= bet
                except KeyError as e :
                    continue
                
                if mpip.group(2) == 'posts big blind' :
                    game['big_blind'] = bet

                #print "bet: ", bet
                #print "ratio: ", bet / game['pot']
                if is_blind :
                    continue
                elif bet <= game['big_blind'] * MIN_BET_THRESH :
                    #print "excluded, too small"
                    continue
                elif mpip.group(2) == 'is all-In' :
                    #print "excluded, all in"
                    continue
                #elif bet >= game['stacks'][player] * ALL_IN_THRESH :
                    ##print "excluded, too big"
                    #continue
                else:
                    bets.append( int(bet / game['pot'] * 100) )


        #if line_count > 100 : break

        line_count += 1
        
    fin.close()
    file_counter += 1

fout = open("%s_bets.txt" % filename % 42, 'w')
fout.write( str(sorted(bets))[1:-1] )
fout.close()
#finish processing last game



