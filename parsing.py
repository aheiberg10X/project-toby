import re
import os
import os.path
import json

import table
from globles import veryClose, BET_RATIOS
from deck import listify

MIN_BET_THRESH = 1
ALL_IN_THRESH = .8

def actionState2Str( action_state ) :
    return ','.join( [str(t) for t in action_state] )

#coordinate with table.advanceStreet, which builds the action_states themselvesa
#BET_RATIOS
#1/0 last_to_act
#1/0
actionState2int = {}
count = 0;
for br in BET_RATIOS :
    for last_to_act in [1,0] :
        for aggressivePIP in [1,0] :
            astate_str = actionState2Str( [br,last_to_act,aggressivePIP] )
            actionState2int[ astate_str ] = count
            count += 1



#take entry from table.action_states and map it to an in for MATLAB to crunch
def mapActionState2Int( action_state ) :
    return actionState2int[ actionState2Str( action_state ) ]

def iterateActionStatesACPC( filename, \
                             min_betting_rounds = 1, \
                             must_have_showdown = False ) :

    fin = open(filename)
    #TODO: glean small blind from, or always the same?

    #button is the second player, small blind
    splt = filename.split('.')
    players = [ splt[1], splt[2] ]
    perm = int(splt[4][5:])
    if perm == 1 :
        button = 0
    else :
        button = 1

    #stacks are always reset to 20000 at the start of every game 
    pockets = [['__','__'],['__','__']]

    tbl = table.Table( small_blind=50 )
    header = fin.readline()
    for i in range(3) : burn = fin.readline()
    for line in fin.readlines() : 

        splt = line.strip().split(':')
        if splt[0] == "SCORE" :
            #do something with total score?
            break

        game_id = int(splt[1])
        print "\nGAME_ID:", game_id
        action_strings = splt[2].strip('/').split('/')
        card_strings = splt[3].strip('/').split('/')
        win_lose = splt[4]
        player_order = splt[5].split("|")
        button_player = player_order[1]
        button = players.index(button_player)
 
        n_betting_rounds = len(action_strings)
        has_showdown = False
        if n_betting_rounds == 4 :
            has_showdonw = 'f' not in action_strings[3]
       
        #print "new stacks: ", fresh_stacks
        tbl.newHand(players, pockets, [20000,20000], button)

        for street, (action_string, card_string) in enumerate(zip( action_strings, card_strings)) :
            print "Street,action_string,card_stringL ", street, action_string, card_string
            if street > 0 :
                tbl.advanceStreet( listify(card_string) )
            else :
                #force the first two 'calls' 
                #registerAction translates them as the blind posting
                tbl.registerAction('c')
                tbl.registerAction('c')
                tbl.advanceStreet( ['down','cards'] )
            
            prev_act = 'blinds'
            ix = 0
            while ix < len(action_string) :
                act = action_string[ix]
                #'c' is overloaded, when no prev bet it means chec'k'
                if act == 'c' and (prev_act != 'r' and \
                                   prev_act != 'b' and \
                                   prev_act != 'blinds') :
                    act = 'k'
                    tbl.registerAction( act )
                    ix += 1

                elif act == 'r' :
                    #iterate through string to extract the bet amount
                    ints = []
                    ix += 1
                    while action_string[ix] not in ['r','c','f'] :
                        ints.append( action_string[ix] )
                        ix += 1
                    bet_amount = int(''.join(ints))

                    #correct overbets
                    stack_amount = tbl.stacks[tbl.action_to]
                    if bet_amount > stack_amount :
                        bet_amount = stack_amount
                        act = 'a'

                    if prev_act == 'b' or prev_act == 'r' :
                        act = 'r'
                    else :
                        act = 'b'

                    tbl.registerAction( act, bet_amount )

                #true call or fold
                elif act == 'c' or act == 'f' :
                    tbl.registerAction( act )
                    ix += 1

                else :
                    assert False

                prev_act = act

        #all done iterating through the action/card lists

        tbl.advanceStreet(False)

        #register revealed
        #TODO
        #logic controlling whether or not we want to register...
        #may want to emit the rest of the info about hands when a showdown
        #didn't happen
        pocket_strings = card_strings[0].split('|')
        for player_name, pocket_string in zip(player_order,pocket_strings) :
            tbl.registerRevealedPocket( player_name, listify(pocket_string) )


        #emit the {"action_state", "buckets", "gameid"} dict for the last hand
        if n_betting_rounds >= min_betting_rounds and \
           (not must_have_showdown or (must_have_showdown and has_showdown) ) :
            #TODO yield the data in same order as bnet expects
            #TODO map the action_state tuples to integers, will simplify 
            #     MATLAB processing
            #b11,b12,a11,a12,b21,b22,a21,...
            training_instance = []
            for street in range(0,min_betting_rounds) :
                #print "street: ", street
                #print "    b1: ", tbl.buckets[street][0]
                #print "    b2: " , tbl.buckets[street][1]
                #print "    a1: ", tbl.action_states[street][0]
                #print "    a2: ", tbl.action_states[street][1]
                try :
                    training_instance.append( tbl.buckets[street][0] )
                    training_instance.append( tbl.buckets[street][1] )
                    asint = mapActionState2Int( tbl.action_states[street][0] )
                    training_instance.append( asint )
                    asint = mapActionState2Int( tbl.action_states[street][1] )
                    training_instance.append( asint )
                except IndexError as ie :
                    print ie
                    print tbl.action_states
                    assert False

            yield training_instance
            #yield {"action_states" : tbl.action_states, \
                   #"buckets" : tbl.buckets, \
                   #"game_id" : game_id}
        else :
            pass


if __name__ == '__main__' :

    filename = "/home/andrew/project-toby/histories/acpc/2011/logs/2p_nolimit/2011-2p-nolimit.Rembrant.SartreNL.run-9.perm-1.log"
    #filename = "/home/andrew/project-toby/histories/acpc/2011/logs/2p_nolimit/abc.Rembrant.SartreNL.test.perm-1.log"


    for thing in iterateActionStatesACPC( filename, min_betting_rounds=4 ) :
        print thing



    filename1 = "histories/knufelbrujk_hotmail_com_PTY_NLH100_2-2plrs_x10k_f8534/histories.txt"

    filename2 = "histories/knufelbrujk_hotmail_com_PTY_NLH100_2-2plrs_x10k_f8534/training_data.txt"
 
#############################################################################
##### Party Poker Stuff
#############################################################################
#partypoker logs from handhq.com
re_game_id = re.compile(r'\*\*\*\*\* Hand History for Game (\d+) \*\*\*\*\*')
re_table_name = re.compile(r'Table (.*) \(Real Money\)')
re_button = re.compile(r'Seat (\d) is the button')
re_num_players = re.compile(r'Total number of players : (\d)/(\d)')
re_pip = re.compile(r'(.*) (posts small blind|posts big blind|is all-In|raises|bets|calls) \[\$(\d+)(\.(\d\d))? USD\].*')
re_checkfold = re.compile(r'(.*) (checks|folds)')
re_seat = re.compile(r'Seat (\d): (.*) \( \$(\d+)(\.(\d\d))? USD \)')
re_dealing = re.compile(r'\*\* Dealing (.*) \*\* (.*)')
re_shows = re.compile(r'(\w*) (doesn\'t )?show[s]? \[ (..), (..) \]')
re_end = re.compile(r'(\w*) wins \$(\d+)(\.(\d\d))? USD from the main pot.')


#take all the histories as downloaded from handhq and put them into one file
def concatentateHistories( parent_dir ) :
    fout = open( "%s/histories.txt" % parent_dir, 'wb' )
    fout.write("\n")
    for history_file in os.listdir( parent_dir ) :
        if history_file.startswith("pty") :
            handle = open("%s/%s" % (parent_dir,history_file), 'U' )
            firstline = handle.readline()
            fout.write( firstline.decode('utf-8').encode('ascii','ignore') )
            fout.write( handle.read() )
            #fout.write("\n\n")
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

#convert regexp groups to a float amount
def reGroupsToAmount( dollar_group, cent_group ) :
    dollars = int(dollar_group)
    if cent_group :
        cents = float(cent_group) / 100
    else : cents = 0
    return dollars+cents

#yield a dict {"action_states", "buckets", "gameid"}
def iterateActionStates( filename ) :
    num_games, num_revealed = 0,0

    fin = open( filename )
 
    t = table.Table(small_blind=.5)
    isfirst = True
    line_count = 0
    line = fin.readline()
    new_game_count = 0

    while line :
        line = line.strip()
        new_game_match = re_game_id.match(line)
        if new_game_match :
            num_games += 1
            if not isfirst :
                y = {}
                y["action_states"] = t.action_states
                y["buckets"] = t.buckets
                #TODO, don't we want the previous id?
                y["game_id"] = new_game_match.groups(1)
                yield y 
                #for street in range(len(t.action_states)) :
                    #for player in range(num_players) :
                        #tmp = [street] + t.action_states[street][player]
                        ##print tmp
                        #yield tmp
            
            if new_game_count > 9 :
                pass #assert False
            new_game_count += 1

            isfirst = False
            print "\n\n"
            print new_game_match.group(1)
            
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

            zero_stacked_player = False
            for player in range(1,num_players+1) :
                seat_name_line = fin.readline().strip()
                seat_match = re_seat.match( seat_name_line )
                player_seat = int(seat_match.group(1))
                player_name = seat_match.group(2)
                if player_seat < seat_button :
                    button += 1
                stack = reGroupsToAmount( seat_match.group(3), \
                                         seat_match.group(5) )

                #if player has stack of 0, ignore and fastforward to next hand 
                if stack == 0 :
                    end_match = False
                    while not end_match :
                        line = fin.readline().strip()
                        end_match = re_end.match(line)
                    zero_stacked_player = True
                    break

                players.append( player_name )
                stacks.append( stack )

            if zero_stacked_player : continue
            
            t.newHand(players, pockets, stacks, button)

            #small blind
            match_pip = re_pip.match( fin.readline().strip() )
            bet = reGroupsToAmount( match_pip.group(3), match_pip.group(5) )
            assert( bet == t.small_blind )
            t.registerAction( 'c' )

            #big blind
            match_pip = re_pip.match( fin.readline().strip() )
            bet = reGroupsToAmount( match_pip.group(3), match_pip.group(5) )
            t.registerAction( 'c' )

            assert( fin.readline().strip() == "** Dealing down cards **" )
            t.advanceStreet(["down","cards"])

        else :
            match_pip = re_pip.match(line)
            if match_pip :
                player = match_pip.group(1)
                assert( t.players.index(player) == t.action_to )
                action = match_pip.group(2)
                bet = reGroupsToAmount( match_pip.group(3), match_pip.group(5) )
                #print player, action, bet
                if action == "raises" or action == "bets" :
                    t.registerAction( action[0], bet )
                elif action == "is all-In" :
                    t.registerAction( 'a', bet )
                else : #calls
                    t.registerAction( action )
                #t.extractFeatures()
            else :
                checkfold_match = re_checkfold.match(line)
                if checkfold_match :
                    action = checkfold_match.group(2)
                    if action == 'checks' :
                        t.registerAction( 'k' )
                    else :
                        t.registerAction( 'f' )
                else :
                    dealing_match = re_dealing.match( line )
                    if dealing_match :
                        street = dealing_match.group(1)
                        cards = dealing_match.group(2)
                        cards = cards[1:-1].replace(" ","").split(",")
                        t.advanceStreet(cards)
                        #yield pip_ratios
                    else :
                        show_match = re_shows.match(line)
                        if show_match :
                            #register the river
                            t.advanceStreet(False)
                            num_revealed += 1
                            #propagate the revealed HS2 information back
                            #through the table.action_states via 
                            #registerRevealedPocket
                            player = show_match.group(1)
                            card1 = show_match.group(3)
                            card2 = show_match.group(4)
                            t.registerRevealedPocket( player, [card1,card2] )
                        else :
                            end_match = re_end.match(line)
                            if end_match :
                                t.advanceStreet(False)
                            #winning_pix = t.players.index( end_match.group(1) )
                            #win_amt = reGroupsToAmount( end_match.group(2), \
                                                        #end_match.group(4) )

                                #yield pip_ratios
                                pass
                            else :
                                pass

        line = fin.readline()
        line_count += 1
        
    #TODO
    #process the last hand
    #yield t.action_states

    print "num_games: ", num_games, "num_showdowns: ", num_revealed/2
    fin.close()




