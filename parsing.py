import re
import os
import os.path
import table

MIN_BET_THRESH = 1
ALL_IN_THRESH = .8

re_game_id = re.compile(r'\*\*\*\*\* Hand History for Game (\d+) \*\*\*\*\*')
re_table_name = re.compile(r'Table (.*) \(Real Money\)')
re_button = re.compile(r'Seat (\d) is the button')
re_num_players = re.compile(r'Total number of players : (\d)/(\d)')
re_pip = re.compile(r'(.*) (posts small blind|posts big blind|is all-In|raises|bets|calls) \[\$(\d+)(\.(\d\d))? USD\].*')
re_checkfold = re.compile(r'(.*) (checks|folds)')
re_seat = re.compile(r'Seat (\d): (.*) \( \$(\d+)(\.(\d\d))? USD \)')
re_dealing = re.compile(r'\*\* Dealing (.*) \*\* (.*)')
re_end = re.compile(r'(.*) wins \$(\d) USD from the main pot.')

def concatentateHistories( parent_dir ) :
    fout = open( "%s/histories.txt" % parent_dir, 'w' )
    for history_file in os.listdir( parent_dir ) :
        fout.write( open("%s/%s" % (parent_dir,history_file) ).read() )
        fout.write("\n\n")
    fout.close()


def splitHistoryFileByTable( history_filename ) :
    fin = open("%s.txt" % history_filename)
    if os.path.exists( history_filename ) :
        print "already parsed %s" % filename
        return

    os.mkdir( history_filename ) 
    #tablename : [game_lines1, game_lines2,...]
    table_gamedata = {}
    current_gamedata = []
    current_table = ""

    for line in fin.readlines() :
        line = line.strip()
        new_game_match = re_game_id.match(line)
        if new_game_match :
            if current_table not in table_gamedata :
                table_gamedata[current_table] = []
            table_gamedata[current_table].append("\n".join(current_gamedata))

            current_gamedata = [line]
            current_table = ""
        else :
            current_gamedata.append(line)
            table_match = re_table_name.match(line)
            if table_match :
                current_table = table_match.groups(1)
    
    #add in the last game
    if current_table not in table_gamedata :
        table_gamedata[current_table] = []
    table_gamedata[current_table].append("\n".join(current_gamedata))

    for table_id, table in enumerate(table_gamedata) :
        fout = open( "%s/table-%s.txt" % (history_filename, table_id), 'w' )
        fout.write( "\n\n".join( table_gamedata[table] ) )
        fout.close()

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

def extractFeatures( filename ) :
    fin = open( filename )
 
    t = table.Table(small_blind=.5)
    isfirst = True
    line_count = 0
    line = fin.readline()
    while line :
    #for line in fin.readlines() :
        line = line.strip()
        new_game_match = re_game_id.match(line)
        if new_game_match :
            if not isfirst :
                print t
            
            isfirst = False
            print "\n\n"
            #finish processing last game
            
            #setup hand
            fin.readline().strip()
            fin.readline().strip()
            button_line = fin.readline().strip()
            num_players_line = fin.readline().strip()
            num_players_match = re_num_players.match( num_players_line )
            num_players, num_seats = int(num_players_match.group(1)), \
                                     int(num_players_match.group(2))

            button_match = re_button.match( button_line )
            seat_button = int(button_match.group(1))
            #button = button - num_seats + 1
            #print "button: ", button

            players = []
            pockets = [["__","__"]]*num_players
            stacks = [] 
            button = 0
            for player in range(1,num_players+1) :
                seat_name_line = fin.readline().strip()
                seat_match = re_seat.match( seat_name_line )
                player_seat = int(seat_match.group(1))
                player_name = seat_match.group(2)
                if player_seat < seat_button :
                    button += 1
                stack = reGroupsToAmount( seat_match.group(3), \
                                         seat_match.group(5) )
                players.append( player_name )
                stacks.append( stack )
            
            print players, stacks
            t.newHand(players, pockets, stacks, button)

            #small blind
            match_pip = re_pip.match( fin.readline().strip() )
            bet = reGroupsToAmount( match_pip.group(3), match_pip.group(5) )
            assert( bet == t.small_blind )
            t.registerAction( 'c' )

            #big blind
            match_pip = re_pip.match( fin.readline().strip() )
            bet = reGroupsToAmount( match_pip.group(3), match_pip.group(5) )
            t.registerAction( 'r', 1 )


            assert( fin.readline().strip() == "** Dealing down cards **" )

        else :
            match_pip = re_pip.match(line)
            if match_pip :
                player = match_pip.group(1)
                print player
                assert( t.players.index(player) == t.action_to )
                action = match_pip.group(2)
                bet = reGroupsToAmount( match_pip.group(3), match_pip.group(5) )
                #print player, action, bet
                if action == "raises" or action == "bets" :
                    t.registerAction( action[0], bet )
                else :
                    t.registerAction( action )
                #t.extractFeatures()
            else :
                checkfold_match = re_checkfold.match(line)
                if checkfold_match :
                    action = checkfold_match.group(2)
                    if action == 'checks' :
                        t.registerAction( 'c' )
                    else :
                        t.registerAction( 'f' )
                else :
                    dealing_match = re_dealing.match( line )
                    if dealing_match :
                        street = dealing_match.group(1)
                        cards = dealing_match.group(2)
                        cards = cards[1:-1].replace(" ","").split(",")
                        print cards
                        t.advanceStreet(cards)
                    else :
                        end_match = re_end.match(line)
                        if end_match :
                            print line
                        else :
                            pass



        #if line_count > 100 : break
        line = fin.readline()
        line_count += 1
        
    fin.close()
    #file_counter += 1
#
    #fout = open("%s_bets.txt" % filename % 42, 'w')
    #fout.write( str(sorted(bets))[1:-1] )
    #fout.close()
    ##finish processing last gfdame

if __name__ == '__main__' :
    #filename = "histories/knufelbrujk_hotmail_com_PTY_NLH100_3-6plrs_x10k_1badb/pty NLH handhq_%d"
    #filename = "histories/knufelbrujk_hotmail_com_PTY_NLH100_2-2plrs_x10k_f8534/pty NLH handhq_0"
    filename = "histories/knufelbrujk_hotmail_com_PTY_NLH100_2-2plrs_x10k_f8534/histories"


    #splitHistoryFileByTable(filename)
    #concatentateHistories( "histories/knufelbrujk_hotmail_com_PTY_NLH100_2-2plrs_x10k_f8534" )

    extractFeatures( "%s.txt" % filename )
