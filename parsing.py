import re
import os
import os.path
import json
from random import random

import table
from globles import veryClose, BET_RATIOS, LOG_DIRECTORY, LOG_YEAR, DUMMY_ACTION
from deck import listify
import iterate_decision_points as idp 

MIN_BET_THRESH = 1
ALL_IN_THRESH = .8

register_pockets = True
printing = False

#want to extract all hands where focus_player=SartreNL is first to act
#ie not the dealer/button
def logs2Nodes( p1, p2,  perm, leave_out_runs, \
                focus_player, focus_position ) :
    #out_filename = "%s/nodes-%d-%s-%s-perm%d-min%d-show%d.csv" % \
                   #(LOG_DIRECTORY, LOG_YEAR, p1, p2, perm, \
                    #min_betting_rounds, must_have_showdown )

    assert focus_player == p1 or focus_player == p2
    #TODO
    #take each node output and write it to the corrent file handle
    handles = {}
    buffers = {}
    if printing :
        for min_betting_rounds in [1,2,3,4] :
            handles[min_betting_rounds] = {}
            buffers[min_betting_rounds] = {}
            for must_have_showdown in [True,False] :
                handles[min_betting_rounds][must_have_showdown] = {}
                buffers[min_betting_rounds][must_have_showdown] = {}
                ss = "no-showdown"
                if must_have_showdown : ss = "showdown"
                for learn_test in ['training','test'] :
                    fout = open("nodes/%s_%s/perm%d/%s_%d-rounds_%s.csv" % \
                                   (p1,p2,perm,learn_test,min_betting_rounds,ss),'w')
                    handles[min_betting_rounds][must_have_showdown][learn_test] = fout
                    buffers[min_betting_rounds][must_have_showdown][learn_test] = []

    for run in range(100) : #range(100)
        #print "Run: %d" % run
        in_filename = "%s/%d-2p-nolimit.%s.%s.run-%d.perm-%d.log" % \
                       (LOG_DIRECTORY, LOG_YEAR, p1, p2, run, perm)
        count = 0
        for ((game_id,rounds,showdown),nodes,amt_exchanged) in \
            log2Nodes( in_filename, focus_player, focus_position ) :
            nodes.append( amt_exchanged )
            nodes.append( game_id )
            nodes = ','.join([str(node) for node in nodes])

            #print "game_id:", game_id, ":", nodes, "goto: " , rounds, showdown
            if printing :
                if run in leave_out_runs :
                    buffers[rounds][showdown]['test'].append( nodes )
                else :
                    buffers[rounds][showdown]['training'].append(nodes)

        if printing :
            total_games_in_run = 0
            for rounds in [1,2,3,4] :
                for showdown in [True,False] :
                    for test_train in ['training','test'] :
                        lines = buffers[rounds][showdown][test_train]
                        l = len(lines)
                        print rounds, showdown, test_train, l
                        total_games_in_run += l
                        if l > 0 :
                            handles[rounds][showdown][test_train].write( \
                              '\n'.join( lines ) +\
                              '\n' \
                            )
                        buffers[rounds][showdown][test_train] = []
            print total_games_in_run

    #TODO close handles

#def parseHandLine( 

def log2Nodes( filename, focus_player, focus_position ) :

    aggActionsMap = idp.buildAAS2I()
    indActionsMap = idp.buildIAS2I()

    print "paring: ", filename
    fin = open(filename)
    #TODO: glean small blind from, or always the same?

    #button is the second player, small blind
    splt = filename.split('.')
    players = [ splt[1], splt[2] ]
    perm = int(splt[4][5:])
    #if perm==1, button/dealer is the first player in the filename
    if perm == 1 : button = 0
    else :         button = 1

    #if street has too many rounds of betting, throw it out
    MAX_MICRO = 2
    n_thrown_out = 0
    #sum of BBs the thrown out hands involved
    amt_thrown_out = 0

    focus_start_on_button = button == players.index(focus_player)
    want_to_be_button = focus_position == "button"
    use_evens = focus_start_on_button == want_to_be_button
    if use_evens :
        if perm == 1 :
            ordered_players = [1,0]
        else :
            ordered_players = [0,1]
    else :
        if perm == 1 :
            ordered_players = [0,1]
        else :
            ordered_players = [1,0]
    preflop_ordered_players = [ordered_players[1],ordered_players[0]]

    #ordered_players defines indices into table.players
    #such that the first to act player shows up on the left
    #side of the network
    focus_player_ix = players.index(focus_player)
    want_to_be_button = int(focus_position == 'button')
    if focus_player_ix == want_to_be_button :
        ordered_players2 = [0,1]
    else :
        ordered_players2 = [1,0]

    assert ordered_players == ordered_players2

    #stacks are always reset to 20000 at the start of every game 
    pockets = [['__','__'],['__','__']]

    #when someone folds, +/-100 is exchanged
    sb = 50 
    tbl = table.Table( small_blind=sb )
    header = fin.readline()
    for i in range(3) : burn = fin.readline()
    for line_num, line in enumerate(fin.readlines()) : 
        #print "LINE NUM:", line_num
        is_even = line_num % 2 == 0
        if( is_even != use_evens ) : continue

        splt = line.strip().split(':')
        if splt[0] == "SCORE" :
            #do something with total score?
            break

        game_id = int(splt[1])
        #print "GAME_ID:", game_id
        #if game_id % 100 == 0 :
            #print "GAME_ID:", game_id

        action_strings = splt[2].strip('/').split('/')
        card_strings = splt[3].strip('/').split('/')

        #amount won/lost, as multiple of BB
        #using pot size instead
        amt = abs(int(splt[4].split('|')[0]))
        amt_exchanged = int( round ( amt / float(sb*2) ) )

        player_order = splt[5].split("|")
        button_player = player_order[1]
        button = players.index(button_player)

        ##hack to make it go faster
        ##we are only interested in 4 round hands
        #has_showdown = 'f' not in action_strings[len(action_strings)-1]
        #if not has_showdown :
            #continue

        tbl.newHand(players, pockets, [20000,20000], button)

        #mark the round where an allin occurred
        allin_round = 42
        prev_act = 'blinds'
        for street, (action_string, card_string) in enumerate(zip( action_strings, card_strings)) :
            #print "Street,action_string,card_stringL ", street, action_string, card_string
            if street > 0 :
                tbl.advanceStreet( listify(card_string) )
            else :
                #force the first two 'calls' 
                #registerAction translates them as the blind posting
                tbl.registerAction('c')
                tbl.registerAction('c')
                tbl.advanceStreet( ['down','cards'] )

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

                    ##correct overbets
                    #stack_amount = tbl.stacks[tbl.action_to]
                    #if bet_amount > stack_amount :
                        #bet_amount = stack_amount
                        #act = 'a'
                        #allin_round = street

                    #if prev_act == 'b' or prev_act == 'r' :
                        #raises are really 'raise the pot to' amts
                    tbl.registerAction( 'rt' , bet_amount )
                    #else :
                        #tbl.registerAction( 'b', bet_amount )


                #true call or fold
                elif act == 'c' or act == 'f' :
                    tbl.registerAction( act )
                    ix += 1

                else :
                    assert False

                prev_act = act

        #all done iterating through the action/card lists
        tbl.advanceStreet(False)


        n_betting_rounds = min( [len(action_strings), allin_round+1] )
        has_showdown = 'f' not in action_strings[n_betting_rounds-1]
        #if has_showdown :
        pockets = [listify(p) for p in card_strings[0].split('|')]
        if register_pockets :
            tbl.registerRevealedPockets( pockets )
        else:
            for i in range(n_betting_rounds) :
                tbl.buckets.append([-1,-1])

        #if has_showdown :
            #assert tbl.pot/2 == amt
        #else :
            #pass

        #TODO
        #end true parsing(), what follows is processing()

        #emit a training instance for each possible network, given
        #the number of rounds in this hand
        #if n_betting_rounds==3, we can emit nodes for pre,flop,and turn
        training_instance = []
        for betting_round in range(1,n_betting_rounds+1) :
            #the order is flipped for the preflop round
            if betting_round == 1 :
                oplayers = preflop_ordered_players
            else :
                oplayers = ordered_players

            street = betting_round - 1

            #attach bucket nodes
            for pix in oplayers :
                training_instance.append( tbl.buckets[street][pix] )

            #attach merged-action node
            too_many_micro_rounds = False
            individual_actions = []

            #check for games with too much back and forth betting
            for pix in oplayers :
                n_micro_rounds = len(tbl.active_actions[street][pix])
                too_many_micro_rounds = n_micro_rounds > MAX_MICRO
                if too_many_micro_rounds : break

            if too_many_micro_rounds :
                #too_many_micro_rounds, go onto next hand/line 
                n_thrown_out += 1
                amt_thrown_out = amt_exchanged
                break

            for micro_round in [0,1] :
                for pix in oplayers :
                    n_micro_rounds = len(tbl.active_actions[street][pix])
                    #the network expects some number of micro rounds
                    #in the final street
                    if micro_round >= n_micro_rounds :
                        aa = DUMMY_ACTION 
                    else :
                        aa = tbl.active_actions[street][pix][micro_round]
                    individual_actions.append(aa)

            action_str = ','.join( individual_actions )
            ID = idp.lookupAggActionID( aggActionsMap, action_str, street )
            training_instance.append( ID )


            #amt_exchanged = int( round (tbl.pot / float(2*sb) ) )
            #TODO yield both belief-layer nodes and action-layer nodes
            yield [(game_id,betting_round,has_showdown),\
                    list(training_instance), \
                   amt_exchanged]
    print "n_thrown_out: " , n_thrown_out
    print "amt_thrown_out: ", amt_thrown_out

#every game has money exchanged
#the amount (as multiples of big blind) is the second to last column (15)
#we want to duplicate the big money hands, once for each BB in amt
#to not blow up the file size, we pick a factor to define which amt gets 
#included only once.  Those with amt < factor only get included with
#prob amt/factor, and discarded otherwise.
#Everything is written out to the _scaled.csv file, the BB amt and game_id 
#suffixes are dropped
def scaleNodes( nodefilename, factor = 3 ) :
    fin = open( "%s.csv" % nodefilename )
    fout = open( "%s_scaled.csv" % nodefilename, 'w' )
    line_buffer = []

    #TODO: when the BB is 0, does not mean an unimportant hand
    #it means the pot was split.  Pot still could have been big,
    #with lots of interesting betting
    #Rather than use their amt, then, can use Table's internal pot size
    #for showdown hands, it gets it right
    #but for noshow hands, it is including the last bet in the pot
    #debatable whether to include this bet or not makes sense
    #I think it does, I am after 'interesting' features
    #but, if I am evaling accuracy by this amount, then could be hacked 
    #by spamming all-ins.  Don't think this is a threat given the data, though


    BB_amt_ix = 15
    nadded = 0
    for line in fin.readlines() :
        splt = line.strip().split(',')
        new_line = ','.join( splt[:BB_amt_ix] )
        nBB = int(splt[BB_amt_ix])
        include_prob = nBB / float(factor)
        if include_prob >= 1 :
            n_dupes = int(include_prob)
            for i in range(n_dupes) :
                nadded += 1
                line_buffer.append( new_line )
            nadded -= 1
        else :
            if random() < include_prob :
                line_buffer.append( new_line )
            else :
                nadded -= 1

    fout.write( '\n'.join(line_buffer) + '\n' )
    fout.close()
    fin.close()
    print "line num change: ", nadded

if __name__ == '__main__' :

    #debugActionStateMappings()
    #scaleNodes("nodes/noshow_4-round_perm0_train_merged")
    #assert False
    
    p1s = []
    p2s = []
    ##3601.pts-4.genomequery
    p1 = "Rembrant"
    p2 = "SartreNL"
    p1s.append(p1)
    p2s.append(p2)

    #p1 = "POMPEIA"
    #p2 = "SartreNL"

    ##10866.pts-4.genomequery
    #p1 = "player_kappa_nl"
    #p2 = "SartreNL"
    #p1s.append(p1)
    #p2s.append(p2)

    ##12508.pts-4.genomequery
    #p1 = "Hyperborean-2011-2p-nolimit-iro"
    #p2 = "SartreNL"
    #p1s.append(p1)
    #p2s.append(p2)

    ##3718.pts-4.genomequery
    #p1 = "Hyperborean-2011-2p-nolimit-tbr"
    #p2 = "SartreNL"
    #p1s.append(p1)
    #p2s.append(p2)

    ##2529.pts-4.genomequery
    #p1 = "Lucky7"
    #p2 = "SartreNL"
    #p1s.append(p1)
    #p2s.append(p2)

    #19148.pts-5.genomequery
    #p1 = "hugh"
    #p2 = "SartreNL"
    #p1s.append(p1)
    #p2s.append(p2)

    perm = 1
    leave_out_runs = range(90,100)
    for p1,p2 in zip(p1s,p2s) :
        logs2Nodes( p1, p2, perm, leave_out_runs, \
                    focus_player="SartreNL", focus_position = "first" )



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

#what is this, deprecated by iterateActionStates?
#yield a dict {"actions", "buckets", "gameid"}
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
                y["actions"] = t.actions
                y["buckets"] = t.buckets
                #TODO, don't we want the previous id?
                y["game_id"] = new_game_match.groups(1)
                yield y 
                #for street in range(len(t.actions)) :
                    #for player in range(num_players) :
                        #tmp = [street] + t.actions[street][player]
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
                            #through the table.actions via 
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
    #yield t.actions

    print "num_games: ", num_games, "num_showdowns: ", num_revealed/2
    fin.close()




