from history import History
from player import Player
from globles import NA, STREET_NAMES, FOLDED, WILDCARD, POCKET_SIZE
from deck import makeHuman

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

        #self.newHand("init", players, pockets, stacks, button)

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
        self.committed = [0]*self.num_players
        self.pot = 0
        #will worry about this bridge when we come to it
        self.side_pot = {}
        self.board = makeHuman([WILDCARD]*5)
        
        self.streets = iter( STREET_NAMES )
        #extra one to take it out of uninit state
        self.street = self.streets.next()
        self.street = self.streets.next()

        self.aggressor = -1
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
            "was_aggressor" : [False]*4 \
            #features incorporating cards
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

    def updateStack( self, player_ix, amount ) :
        self.pot += amount
        #print "amount: ", amount, "new pot", self.pot
        self.current_bets[player_ix] += amount 
        self.stacks[player_ix]       -= amount
        self.committed[player_ix]    += amount

    def registerAction( self, action, amt=0 ) : #fraction=False ) :
        player_ix = self.action_to

        print self.players[self.action_to], action, amt

        if action == 'k' :
            self.features["num_passive_actions"][self.street] += 1
        elif action == 'f' :
            self.folded[player_ix] = True
            #self.current_bets[player_ix] = -1
        #TODO dealing action, advance self.street at the very least
        elif action == 'd' :
            pass
        else : #b,c,r
            sb_needs_posting = self.street == 0 and not any(self.acted)
            if sb_needs_posting :
                oblig = self.small_blind
            else :
                oblig = self.getObligation(player_ix)
            
            #make the raise  
            if action == 'r' or action =='b' :
                #raise_amt = fraction * self.pot
                #self.updateStack( player_ix, oblig+raise_amt )
                self.updateStack( player_ix, amt )
                assert self.stacks[player_ix] >= 0
                
                #feature bookkeeping
                self.features["num_aggressive_actions"][self.street] += 1
                self.features["callers_since_last_raise"] = 0
                self.aggressor = player_ix
                self.features["num_bets"][self.street] += 1

            else : #action == 'c'
                self.updateStack( player_ix, oblig )
            
                #If player cannot call the required amount, put all in
                #and credit the solvent players the difference
                #TODO: instead of crediting back, put the difference in sidepot
                if self.stacks[player_ix] < 0 :
                    #print "WHOA THERE STACK IS NEGATIVE"
                    #credit the amout back to committed players
                    cur_bet = self.current_bets[player_ix]
                    adj_amt = self.stacks[player_ix]
                    for pix in range(self.num_players) :
                        diff = abs(self.current_bets[pix] - cur_bet)
                        if diff <= .001 :
                            self.updateStack( pix, adj_amt )
                    #TODO: form a side pot
                
                #feature bookkeeping
                self.features["num_passive_actions"][self.street] += 1
                self.features["callers_since_last_raise"] += 1

            assert( self.stacks[player_ix] >= 0 )

            

        if self.logging :
            self.history.update( self.street, (player_ix,action,amount) )
        else :
            self.history[self.street].append( action )

        self.acted[player_ix] = True
        self.action_to = self.nextUnfoldedPlayer( player_ix )

    def extractFeatures( self ) :
        #TODO active to passive ratios
        self.features["all_in_with_call"] = \
            self.stacks[self.action_to] <= self.getObligation( self.action_to )
        self.features["amount_to_call"] = self.getObligation( self.action_to )

        #TODO
        #effective stacks vs agg and actives

        effstacks = self.effectiveStacks( self.action_to )
        oblig = self.getObligation( self.action_to )
        self.features["implied_odds_vs_aggressor"] = \
                oblig / float(oblig + self.pot + effstacks[self.aggressor] )

        #nxt = self.nextUnfoldedPlayer( player_ix )

        positions_between = self.getPositionsBetween( self.action_to, \
                                                      self.button )
        active_between = [pix \
                          for pix \
                          in positions_between
                          if not self.folded[pix] ]

        self.features["in_position_vs_active"] = len(active_between) == 0

        self.features["in_position_vs_aggressor"] = \
                self.aggressor not in positions_between 

        self.features["off_the_button"] = len(active_between)

        

    def getPositionsBetween( self, p1, p2 ) :
        pix = self.ringIncrement( p1, len(self.players) )
        between = []
        while pix != p2 :
            between.append(pix)
            pix = self.ringIncrement( pix )
        return between

    # the minimum of player_ix's stack to all other active players
    # we will use self.stack - obligation, otherwise could make players
    # who hadn't acted yet look artificially stacked
    def effectiveStacks( self, player_ix ) :
        effstacks = []
        player_oblig = self.getObligation( player_ix )
        player_stack = self.stacks[player_ix]
        player_num = max(player_stack-player_oblig, 0)
        for pix in self.players :
            oblig = self.getObligation( pix )
            num = max( self.stacks[pix] - oblig, 0 )
            effstacks.append( min( player_num, num ) )
        return effstacks



    def nextUnfoldedPlayer( self, player_ix ) :
        while True :
            nxt = self.ringIncrement( player_ix, len(self.players) )
            if not self.folded[nxt] :
                break

        assert( nxt != player_ix )
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
                    print "player_ix", player_ix, self.current_bets[player_ix]
                    print "ix: ", ix, self.current_bets[ix]
                    assert False
                return diff
        #everyone has folded
        return 0

    #TODO:
    #side-potting?
    #track burned cards
    #TODO changed self.street to ints, need to reflect name change here
    def advanceStreet( self, cards ) :
        self.current_bets = [0]*self.num_players
        self.acted = [False]*self.num_players
        if self.street == -1 :
            #deal out the hole cards
            cards = iter(cards)
            for pix in range(self.num_seats) :
                if not self.chairEmpty(pix) :
                    self.pockets[pix] = cards.next()
                    #deck.draw(POCKET_SIZE)
            human_pockets = [makeHuman(hc) for hc in self.pockets]
            if self.logging :
                pass
                ##self.history.newHand(self.player_names, human_pockets)
#
        elif self.street == 0    : self.board[:3] = cards
        elif self.street == 1    : self.board[3]  = cards[0]
        elif self.street == 2    : self.board[4]  = cards[0]

        self.street = self.streets.next()
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
