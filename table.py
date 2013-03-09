from history import History
from player import Player
from globles import NA, STREET_NAMES, FOLDED, WILDCARD, POCKET_SIZE, veryClose, BET_RATIOS, BUCKET_TABLE_PREFIX
from deck import makeHuman, canonicalize, collapseBoard, listify, symmetricComplement
import rollout
import globles

import db

# for storing information about the state of the game

# a Dealer() will arbitrate over the Table() object to direct the game
# have separated these things because when it comes time to gamble, the Dealer()
# class will be out of our control, but we'll want to be keeping track of the 
# game

# basically, assume all alterations to the Table() are valid
# as they are controlled by our Dealer() class, or the poker site client

class Table() :
    def __init__(self, \
                 logging=False, \
                 small_blind=1) :

        self.small_blind = small_blind
        self.logging = logging

        if self.logging :
            self.history = History()
        else :
            self.history = {}
            for s in STREET_NAMES :
                self.history[s] = []

        self.conn = db.Conn("localhost")

    def __str__(self) :
        r = []
        r.append( "Table:" )
        r.append( "    Player Names: %s" % '; '.join(self.players) )
        pocks = [str(makeHuman(p)) for p in self.pockets]
        r.append( "    Pockets: %s" % '; '.join(pocks) )
        r.append( "    Folded: %s" % '; '.join([str(f) for f in self.folded]) )
        r.append( "    Stacks: %s" % '; '.join([str(s) for s in self.stacks]) )
        r.append( "    Button: %s" % self.players[self.button] )
        r.append( "    Street: %s" % self.street )
        r.append( "    Board: %s" % ' '.join(makeHuman(self.board)) )
        r.append( "    Pot: %f" % self.pot )
        r.append( "    Current Bets: %s" % \
                       "; ".join([str(cb) for cb in self.current_bets]) )
        r.append( "    Committed: %s" % \
                       "; ".join([str(c) for c in self.committed]) )
        r.append( "    Action To: %s" % self.players[self.action_to] )
        return "\n".join( r )

    def copy(self) :
        t = Table(players     = self.players, \
                  stacks      = list(self.stacks), \
                  toby_ix     = self.toby_ix, \
                  pockets     = list(self.pockets), \
                  button      = self.button, \
                  logging     = self.logging, \
                  small_blind = self.small_blind \
                  )

        for street in STREET_NAMES :
            t.history[street] = list(self.history[street])

        t.action_to = self.action_to
        t.folded = list(self.folded)
        t.acted = list(self.acted)
        t.current_bets = list(self.current_bets)
        t.committed = list(self.committed)
        t.pot = self.pot
        t.board = list(self.board)
        t.street = self.street
        it = iter(STREET_NAMES)
        for sn in it :
            if sn == t.street :
                break
        t.streets = it

        return t

    def newHand(self,players,pockets,stacks,button) :
        #TODO, probably be setting button, no guarantee of constant player
        #as table progresses in hand histories
        #self.advanceButton()
        self.num_players = len(players)
        self.button = button
        if self.num_players > 2 :
            self.action_to = self.ringIncrement( self.button, self.num_players )
        else :
            self.action_to = self.button
        self.players = players
        self.stacks = stacks
        self.pockets = pockets #[deck.draw(2) for i in range(self.num_players)]
        #self.pockets = [[FOLDED]*POCKET_SIZE]*self.num_players
        self.folded = [False]*self.num_players
        self.acted = [False]*self.num_players
        self.current_bets = [0]*self.num_players
        self.passive_pip = [0]*self.num_players
        self.aggressive_pip = [0]*self.num_players
        self.committed = [0]*self.num_players
        self.pot = 0
        #will worry about this bridge when we come to it
        self.side_pot = {}
        self.board = makeHuman([WILDCARD]*5)
        
        self.streets = iter( STREET_NAMES )
        ##extra one to take it out of uninit state
        self.street = self.streets.next()
        #self.street = self.streets.next()
        #print "new hand, street: ", self.street

        self.aggressor = -1

        #will be multi-dimensional list
        #1st dim = street 0 - 3
        #2nd dim = player 0 - (self.num_players-1)
        #3rd dim = particular feature.  The last one is the EHS2 belief
        self.action_states = []
        self.buckets = [[-1,-1],[-1,-1],[-1,-1],[-1,-1]]

        self.features = { \
            #DONE (defacto)
            "active_players" : len(players), \
            "total_players" : len(players), \
            #done, though these aren't the actual features themselves
            #(they are ratios of passive v active on different streets
            "num_aggressive_actions" : [0]*4, \
            "num_passive_actions" : [0]*4, \
            "all_in_with_call" : False, \
            #TODO: done, but seems not useful.  The implied odds lower down
            #seem much more informative.  We have X to call.  Is that a lot?
            #Who knows? Need vs the blind amount, or something
            "amount_to_call" : -1, \
            #TODO.  Not done. 
            #perhaps instead we could introduce the mean, var of HS2 for board
            #or could give prob to each type of hand being made (hard?)
            #don't like these board features, feel they are very rough
            "average_rank" : -1, \
            "high_card_flop" : -1, \
            "high_card_turn" : -1, \
            "high_card_river" : -1, \
            "max_cards_suited" : [0]*4, \
            "max_cards_same_rank" : -1, \
            "num_different_high_cards" : -1, \
            "straight_possibilties" : [0]*4, \

            #done
            "callers_since_last_raise" : -1, \
            #TODO.  not done.  what good is effective stack.  
            #Just a number, with no
            #way to gauge it's significance or not.  I wanna know how 
            #big/short stacked I am relative to the baddest active, not the 
            #absolute number, right?
            #either way, when compute, make sure to compare the 
            # committed + stack numbers.  If someone hasn't acted yet,
            #it will artificially inflate their stack size
            "effective_stack_vs_active" : -1, \
            "effective_stack_vs_aggressor" : -1, \
            #done
            "implied_odds_vs_aggressor" : -1, \
            "in_position_vs_active" : False, \
            "in_position_vs_aggressor" : False, \
            #done
            "num_bets" : [0]*4, \
            "off_the_button" : -1, \
            #TODO: a little more involved
            "own_previous_action" : -1, \
            "own_previous_action_category" : -1, \
            #TODO easily done, how additionally informative after callers 
            #since last raise? oh, could be useful to know how many have
            #folded vs how many stayed in?  
            "players_acted" : 0, \
            #TODO: isn't this just off_the_button?
            "players_left_to_act" : 0, \
            "pot_odds" : -1, \
            "pot_size" : 0, \
            "stack_size" : self.stacks[self.action_to], \
            "was_aggressor" : [False]*4, \
            # totalPIP/BB, totalPIP/effstack, aggPIP/totalPIP, passPIP/totalPIP
            "summarized_bets" : [[[0]*4]*self.num_players for i in range(4)]


        }
    
    def isDealerAction( self ) :
        has_acted = self.acted[self.action_to]
        oblig_is_zero = self.getObligation(self.action_to) == 0
        return has_acted and oblig_is_zero
        #return self.table.action_to % (self.num_players+1) \
                #== self.num_players

    def playersAlive( self ) :
        alive = []
        for i in range(self.num_players) :
            if not self.folded[i] :
                alive.append(i)
        return alive

    def possibleRaises( self, player_ix, fractions ) :
        possible = []
        for frac in fractions :
            if frac * self.pot + self.getObligation(player_ix) <= \
               self.stacks[player_ix] :
                possible.append(frac)
        return possible

    def updateStack( self, player_ix, amount, mode="passive" ) :
        self.pot += amount
        #print "amount: ", amount, "new pot", self.pot
        self.current_bets[player_ix] += amount 
        #print self.players[player_ix], "current bet: ", self.current_bets[player_ix]
        self.stacks[player_ix]       -= amount
        self.committed[player_ix]    += amount
        if mode == 'passive' :
            self.passive_pip[player_ix] += amount
        elif mode == 'aggressive' :
            self.aggressive_pip[player_ix] += amount
        else : assert False
        #print self.pot
        #print self.current_bets[player_ix], self.aggressive_pip[player_ix], self.passive_pip[player_ix]


    def registerAction( self, action, amt=0 ) : #fraction=False ) :
        player_ix = self.action_to

        #print self.players[self.action_to], action, amt

        if action == 'k' :
            self.features["num_passive_actions"][self.street] += 1
        elif action == 'f' :
            self.folded[player_ix] = True
            #self.current_bets[player_ix] = -1
        #TODO dealing action, advance self.street at the very least
        elif action == 'd' :
            pass
        else : #b,c,r, all-in
            sb_needs_posting = self.street == -1 and not any(self.acted)
            bb_needs_posting = self.street == -1 and sum(self.acted) == 1
            if sb_needs_posting :
                oblig = self.small_blind
            elif bb_needs_posting :
                oblig = self.small_blind*2
            else :
                oblig = self.getObligation(player_ix)
            
            #TODO figure out if raise or call
            if action == 'a' :
                print "registering all in action"
                if amt > oblig : action = 'r'
                else : action = 'c'

            #make the raise  
            if action == 'r' or action =='b' :
                #raise_amt = fraction * self.pot
                #self.updateStack( player_ix, oblig+raise_amt )
                self.updateStack( player_ix, amt, "aggressive" )
                if not self.stacks[player_ix] >= -0.00001 :
                    print self.stacks[player_ix]
                    print self.committed[player_ix]
                    print self.current_bets[player_ix]
                    assert False
                
                #feature bookkeeping
                #self.features["
                self.features["num_aggressive_actions"][self.street] += 1
                self.features["callers_since_last_raise"] = 0
                self.aggressor = player_ix
                self.features["num_bets"][self.street] += 1


            else : #action == 'c'
                self.updateStack( player_ix, oblig, "passive" )
            
                #If player cannot call the required amount, put all in
                #and credit the solvent players the difference
                #TODO: instead of crediting back, put the difference in sidepot
                if self.stacks[player_ix] < 0 :
                    #TODO how to work the mode of updateStack 
                    # into this corrective action

                    #print "WHOA THERE STACK IS NEGATIVE"
                    #credit the amout back to committed players
                    cur_bet = self.current_bets[player_ix]
                    adj_amt = self.stacks[player_ix]
                    for pix in range(self.num_players) :
                        diff = abs(self.current_bets[pix] - cur_bet)
                        if diff <= .001 :
                            if player_ix == pix :
                                self.updateStack( pix, adj_amt, "passive" )
                            else :
                                self.updateStack( pix, adj_amt, "aggressive" )
                    #TODO: form a side pot
                
                #feature bookkeeping
                self.features["num_passive_actions"][self.street] += 1
                self.features["callers_since_last_raise"] += 1

            assert( self.stacks[player_ix] >= -0.00001 )

        if self.logging :
            self.history.update( self.street, (player_ix,action,amount) )
        else :
            self.history[self.street].append( action )

        self.acted[player_ix] = True
        self.action_to = self.nextUnfoldedPlayer( player_ix )

    def registerRevealedPocket( self, player_name, pocket ) :
        pix = self.players.index(player_name)
        #TODO: handle preflop strength via some table
        #print "registerRevealed player:", player_name
        for street in range(len(self.action_states)) :
            if street == 0 :
                street_name = "preflop"
                q = """select memberships 
                       from %s%s
                       where pocket = '%s'""" % \
                               (BUCKET_TABLE_PREFIX,\
                                street_name.upper(),\
                                canonicalize(pocket))
            else :
                if   street == 1 : 
                    board = self.board[:3]
                    street_name = 'flop'
                elif street == 2 : 
                    board = self.board[:4]
                    street_name = 'turn'
                elif street == 3 : 
                    board = self.board
                    street_name = 'river'

                cboard = collapseBoard( board )
                q = """select aboard
                       from REPRESENTATIVES
                       where cboard = '%s'""" % (cboard)
                print q
                [[aboard]] = self.conn.query(q)
                aboard = listify(aboard)

                #pocket:board::apocket:aboard
                print "board",board
                print "aboard", aboard
                apocket = symmetricComplement( board, pocket, aboard )
                print "pocket",pocket
                print "apocket", apocket
                
                #EHS2 = rollout.computeSingleEHS2( pocket, self.board )
                q = """select memberships
                       from %s%s
                       where cboard = '%s' and pocket = '%s'""" % \
                               (BUCKET_TABLE_PREFIX,\
                                street_name.upper(),\
                                cboard,\
                                apocket )

            print  q 
            [[memberships]] = self.conn.query( q )
            #TODO
            #eventually the beliefs should be a continuous node, for now let's just
            #cram it into the closest to the average
            memberships = [float(t) for t in memberships.split(':')]
            #print "membs", memberships
            w = [i*m for i,m in enumerate(memberships)]
            #print "wsum:", wsum
            bucket = int(round(sum(w)))
            #print "bucket,", bucket


            #if street == len(self.buckets)+1 :
                #self.buckets[street][pix] = bucket
            #else:
                #self.buckets.append( [0,0] )
                #self.buckets[street][pix] = bucket
            self.buckets[street][pix] = bucket

            #self.action_states[street][pix].append( EHS2 )
        #print self.action_states

    #TODO: work in progress, not clear if going to be used
    def extractFeatures( self ) :
        #TODO active to passive ratios
        self.features["all_in_with_call"] = \
            self.stacks[self.action_to] <= self.getObligation( self.action_to )
        self.features["amount_to_call"] = self.getObligation( self.action_to )

        #TODO
        #effective stacks vs agg and actives

        players = [self.action_to] + \
                  self.getPositionsBetween( self.action_to, self.action_to )
        effstacks = self.effectiveStacks( players )
        oblig = self.getObligation( self.action_to )
        self.features["implied_odds_vs_aggressor"] = \
                oblig / float(oblig + self.pot + effstacks[self.aggressor] )

        #nxt = self.nextUnfoldedPlayer( player_ix )

        positions_between_button = self.getPositionsBetween( self.action_to, \
                                                             self.button )
        active_between_button = [pix \
                                 for pix \
                                 in positions_between_button
                                 if not self.folded[pix] ]

        self.features["in_position_vs_active"] = len(active_between_button) == 0

        self.features["in_position_vs_aggressor"] = \
                self.aggressor not in positions_between_button

        self.features["off_the_button"] = len(active_between_button)

    def getPositionsBetween( self, p1, p2 ) :
        pix = self.ringIncrement( p1, self.num_players )
        between = []
        while pix != p2 :
            between.append(pix)
            pix = self.ringIncrement( pix, self.num_players )
        return between

    #effective stack of the first player in the list to the rest
    # we will use self.stack - obligation, otherwise could make players
    # who hadn't acted yet look artificially stacked
    def effectiveStack( players ) :
        effstacks = []
        oblig = self.getObligation( players[0] )
        stack = self.stacks[players[0]]
        adjusted_stack = max( stack-oblig, 0 )
        effstacks.append( adjusted_stack )
        for player in players[1:] :
            oblig_b = self.getObligation( player )
            stack_b = self.stacks[player]
            adjusted_stack_b = max( stack_b-oblig_b, 0 )
            effstack.append( min( adjusted_stack, adjusted_stack_b ) )
        return effstacks

    def nextUnfoldedPlayer( self, player_ix ) :
        nxt = player_ix
        while True :
            nxt = self.ringIncrement( nxt, len(self.players) )
            if (not self.folded[nxt]) or (nxt == player_ix) :
                break

        return nxt

    def ringIncrement( self, i, length ) :
        if i == length-1 :
            return 0
        else : return i+1

    #def addPlayer( self, player, ix ) :
        #if not self.players[ix].name == NA :
            #raise Exception( "someone already sitting there")
        #else :
            #self.players[ix] = player
            #self.player_names[ix] = player.name
            #self.num_players += 1

    def chairEmpty( self, ix ) :
        return self.players[ix].name == NA

    def getObligation( self, player_ix ) :
        
        #return the first non-zero current-bet of a non-folded player
        ixs = range( player_ix-1, -1, -1) + \
              range( self.num_players-1, player_ix, -1)
        for ix in ixs :
            is_folded = self.folded[ix]
            if not is_folded :
                diff = self.current_bets[ix] - \
                       self.current_bets[player_ix]
                if not diff >= 0 :
                    print "action_to", self.action_to
                    print "ix: ", ix, self.current_bets[ix]
                    print "player_ix", player_ix, self.current_bets[player_ix]
                    assert False
                return diff
        #everyone has folded
        return 0

    #TODO:
    #side-potting?
    #track burned cards
    def advanceStreet( self, cards ) :
        #if we are out of streets and try to advance, do nothing
        try :
            self.street = self.streets.next()
        except StopIteration :
            return 
        
        #pointless to report actions about automatic blinds
        #(remember self.streets already incremented here)
        if self.street > 0 :
            acted_players = [player \
                              for player \
                              in range(self.num_players) \
                              if self.acted[player]]

            #compute the features we want to emit
            #pip_to_sb_ratios, pip_to_pot_ratios, agg_to_pip_ratios, pass_to_pip  
            ratios = []
            for p in acted_players :
                t = []
                pip_to_pot = self.current_bets[p] / float(self.pot)
                closest_ratio = min( BET_RATIOS, \
                                     key = lambda bet : abs(pip_to_pot-bet) )
                t.append( closest_ratio )

                #1 if in position, last to act
                #TODO: hardcoded for heads up
                #if advancing from preflop
                if self.street == 1 :
                    t.append( int(self.button != p ) )
                else :
                    t.append( int(self.button == p) )

                #1 if aggressive PIP ratio
                if not self.current_bets[p] == 0 :
                    was_aggressive = int( (self.aggressive_pip[p] / \
                                           float(self.current_bets[p])) > .1 )
                    t.append( was_aggressive )
                    #t.append( self.passive_pip[p] / self.current_bets[p] )
                else :
                    t.append(0)
                    #t.append(0)
                ratios.append(t)
         
            #meaningless to register ratios where no one acts
            #this can happend when an all-In is called
            #future streets are dealt but there are no actions to take
            if len(acted_players) > 0 : 
                self.action_states.append( ratios )
        
        #bookkeeping
        if cards :

            #remember self.street has already been advanced by now
                        
            if   self.street == 1    : self.board[:3] = cards
            elif self.street == 2    : self.board[3]  = cards[0]
            elif self.street == 3    : self.board[4]  = cards[0]

            if self.street > 0 :
                self.current_bets = [0]*self.num_players
                self.passive_pip = [0]*self.num_players
                self.aggressive_pip = [0]*self.num_players
                self.acted = [False]*self.num_players
                self.action_to = self.nextUnfoldedPlayer( self.button )
            
            if self.logging :
                self.history.update( self.street, makeHuman(self.board) )
        

    def advanceButton( self ) :
        for pix in range( self.button+1, len(self.players) ) + \
                   range( self.button ) : 
            if not self.players[pix] == NA :
                self.button = pix
                self.action_to = self.ringIncrement( self.button )
                #action_to = self.button+1
                #if action_to == len(self.players) :
                    #self.action_to = 0
                #else :
                    #self.action_to = action_to

    def close(self) :
        if self.logging :
            self.history.writeOut()

def main() :
    t = Table( num_seats=8 )
    p1 = Player("shake")
    p2 = Player("frylock")
    t.addPlayer(p1, 1)
    t.addPlayer(p2, 2)

    #t.newHand()

if __name__ == '__main__' :
    main()
