from random import choice, sample
from math import sqrt

#state is a board and a player to move (-1 or 1), and captured pieces
#board is a NxN multidim array (-1,0,1)
#maintain set of open positions coords (to sample randomly from)

BLACK = -1
WHITE = 1
EMPTY = 0
OFFBOARD = -42
PASS = 0

class State :
    def __init__(self,dim,shallow=False) :
        self.dim = dim
        self.board = [EMPTY]*(dim*dim)
        self.open_positions = set(range(dim*dim))
        self.capture_counts = [0,0]
        self.player = BLACK 
        self.action = -1 
        self.allowable_actions = [self.ix2action(ix,self.player) \
                                  for ix \
                                  in range(dim*dim) ]
        if not shallow :
            self.past_states = [State(dim, shallow=True)]*10
#
#
    def togglePlayer(self) :
        self.player = -self.player

    def copy(self, shallow=False) : 
        ns = State(self.dim)
        ns.board = list(self.board)
        ns.open_positions = set(self.open_positions)
        ns.capture_counts = list(self.capture_counts)
        ns.player = self.player
        ns.action = self.action
        if not shallow :
            for ix,ps in enumerate(self.past_states) :
                ns.past_states[ix] = ps.copy(shallow=True)
            #ns.past_states[ix] = (
            #(list(ps[0]),ps[1])
        return ns

    def copyInto( self, state ) :
        state.board = self.board
        state.open_positions = self.open_positions
        state.capture_counts = self.capture_counts
        state.player = self.player
        state.action = self.action

    def sameAs2( self, board, player ) :
        if self.player != player :
            return False
        else :
            for ix in range(self.dim*self.dim) : 
                if self.board[ix] != board[ix] :
                    return False
            return True 

    def sameAs( self, state2 ) :
        #if type(state2) == int : return False
        #assert self.dim == state2.dim
        print "Comparing:"
        print self 
        print "\n and \n"
        print state2
        return self.sameAs2( state2.board, state2.player )
        #if self.player != state2.player :
            #return False
        #else :
            #for ix in range(self.dim*self.dim) : 
                #if self.board[ix] != state2.board[ix] :
                    #return False
            #return True 

    def getNorth(self, ix) :
        if ix < self.dim or ix < 0 :
            return OFFBOARD 
        else :
            return ix - self.dim
    def getSouth(self, ix) :
        if ix >= self.dim*self.dim - self.dim or ix < 0 :
            return OFFBOARD
        else :
            return ix + self.dim
    def getEast(self, ix) :
        if ix % self.dim == self.dim - 1 or ix < 0 :
            return OFFBOARD
        else :
            return ix+1
    def getWest(self, ix) :
        if ix % self.dim == 0 or ix < 0 :
            return OFFBOARD
        else :
            return ix-1

    def getNorthWest(self, ix) :
        return self.getNorth( self.getWest(ix) )

    def getNorthEast(self, ix) :
        return self.getNorth( self.getEast(ix) )

    def getSouthEast(self, ix) :
        return self.getSouth( self.getEast(ix) )

    def getSouthWest(self, ix) :
        return self.getSouth( self.getWest(ix) )

    def action2ix( self, action ) :
        color = self.action2color(action)
        return action*color - 1

    def action2color( self, action ) :
        if action > 0 : return WHITE 
        else          : return BLACK

    def ix2action( self, ix, color=False ) :
        if ix == OFFBOARD : assert False
        if not color :
            return (ix+1)*self.ix2color(ix)
        else :
            return (ix+1)*color

    def ix2color( self, ix ) :
        if ix == OFFBOARD : return OFFBOARD 
        return self.board[ix]

    def setBoard( self, ixs, color ) :
        if type(ixs) == int :
            ixs = [ixs]
        for ix in ixs :
            if color != 0 :
                assert self.board[ix] == 0
                self.open_positions.remove(ix)
            else :
                self.open_positions.add(ix)
            self.board[ix] = color

    def getNeighbors( self, ix, adjacency=4 ) :
        if adjacency == 4 :
            return [self.getNorth(ix), \
                    self.getSouth(ix), \
                    self.getEast(ix), \
                    self.getWest(ix)]
        elif adjacency == 8 :
            return [self.getNorth(ix), \
                    self.getSouth(ix), \
                    self.getEast(ix), \
                    self.getWest(ix), \
                    self.getNorthWest(ix), \
                    self.getNorthEast(ix), \
                    self.getSouthWest(ix), \
                    self.getSouthEast(ix) ]
        else : assert False

    def matching( self, ixs, colors=[BLACK,EMPTY,WHITE] ) :
        return [ix for ix in ixs if ix >= 0 and self.board[ix] in colors]
   
    #returns a function that returns True if one ix in the neighbs list
    #matches one of the colors specified
    def hasNeighbsClosure( self, colors ) :
        def inner( neighbs ) :
            return len( self.matching( neighbs, colors ) ) > 0
        return inner

    def floodFill( self, q, colors, stopper, adjacency=4 ) :
        marked = {}
        while len(q) > 0 :
            #print "q:", q
            ix = q.pop()
            #print "ix:", ix
            marked[ix] = True
            #print "marked:", marked
            neighbs = self.getNeighbors( ix, adjacency=adjacency )
            if stopper(neighbs) :
                #print "had empty neighbs"
                marked = {}
                break
            else :
                for n in self.matching( neighbs, colors ) :
                    if n not in marked or not marked[n] :
                        q.append(n)

        return marked.keys()

    #returns true 
    def neighboredByOneColor( self, ix, adjacency=4 ) :
        neighbs = self.getNeighbors( ix, adjacency=4 )
        has_white = len( self.matching( neighbs, [WHITE] ) ) > 0
        has_black = len( self.matching( neighbs, [BLACK] ) ) > 0

        if has_white and not has_black   : ncolor = WHITE
        elif has_black and not has_white : ncolor = BLACK
        else                             : ncolor = EMPTY
        
        #find the ix of a neighbor stone
        for nix in neighbs :
            if nix != OFFBOARD and self.ix2color( nix ) == ncolor :
                return (ncolor,nix)

        return (ncolor,False)

    def fillsSingleEye( self, action ) :
        color = self.action2color(action)
        ix = self.action2ix(action)

    #returns whether the move will leave the group formed by it's placement
    #no liberties
    def isSuicide( self, action ) :
        color = self.action2color(action)
        ix = self.action2ix(action)
        neighbs = self.getNeighbors(ix)
        same_neighbs = self.matching( neighbs, [color] )
        no_liberties_left = []
        marked = {}
        for q in same_neighbs+[ix] :
            if q in marked : continue
            group = self.floodFill( [q], \
                            colors=[color], \
                            stopper=self.hasNeighbsClosure([0]) )
            for ix in group :
                marked[ix] = True

            no_liberties_left.append( len(group) != 0 )

        suicide_by_definition = any(no_liberties_left)#print no_liberties_left
    
        #TODO move to fillsSingleEye
        non_offboard = self.matching( neighbs, [BLACK,WHITE,EMPTY] )
        useless_eye_move = all( [ self.ix2color(nix) == color \
                                  for nix \
                                  in non_offboard ] )
        return suicide_by_definition or useless_eye_move 

    def __str__(self) :
        rows = []
        rows.append( "Player: %d" % self.player )
        rows.append( "Captured (-1,1): %s" % str(self.capture_counts) )
        #rows.append( "Allowable: %s" % str(self.allowable_actions) )
        for i in range(self.dim) :
            l = []
            for j in range(self.dim) :
                p = self.board[i*self.dim+j]
                if   p == BLACK  : l.append( "x" )
                elif p == WHITE  : l.append( "o" )
                elif p == EMPTY  : l.append( "." )
                #else : assert False
            rows.append( " ".join(l) )

        return "\n".join(rows)
 
#adjacent pieces of the same color
class String :
    def __init__(self,string_id,members,color) :
        self.string_id = string_id
        self.members = members
        self.color = color
        self.territories = []

    def __str__(self) :
        return "\nid: " + str(self.string_id) + \
                "\nmembers: " + str(self.members) + \
                "\ncolor: " + str(self.color) + \
                "\nterritories: " + str(self.territories)

class MCTS_Go :
    def __init__(self,dim) :
        #state.past_states = [State(dim)]*10
        self.dim = dim
        self.start_state = State(dim)
        self.excluded_action = -123

    def copyState( self, state ) :
        if type(state) == int :
            return state
        return state.copy()

    #DEPRECATED
    #def setAllowableActions( self, state ) :
        ##0 is pass
        #possible_actions = [state.ix2action(op, state.player) \
                            #for op \
                            #in state.open_positions]
        #allowable_actions = []
        #for action in possible_actions :
            #is_legal = self.applyAction( state, action, side_effects=False ) 
            #if is_legal :
                #allowable_actions.append( action )
       # 
        #if len(allowable_actions) == 0 : state.allowable_actions = [PASS]
        #else : state.allowable_actions = allowable_actions
   
    #given the color of stone, return the player's index in the score array
    #used in getRewards
    def getScoreIx( self, color ) :
        if color == BLACK :
            return 1
        elif color == WHITE :
            return 0
        else : 
            print "coloR: ",color
            assert False

    ####################################################
    ####Public Interface
    ####################################################
    #def getAllowableActions( self, state ) :
        #return state.allowable_actions
    
    #side_effects to true means updating and returning the state, metadata 
    #otherwise just returns t/f based on whether the move is legal
    def applyAction( self, state, action, side_effects=True ) :
        legal = True

        #freeze and save the current state
        frozen = self.copyState( state )

        if action != 0 :
            ix = state.action2ix(action)
            color = state.action2color(action)
            state.setBoard( ix, color )

            #resolve captures
            neighbs = state.getNeighbors( ix )
            opp_color = -color
            opp_neighbs = state.matching( neighbs, [opp_color] )
            num_removed = 0
            for q in opp_neighbs :
                marked = state.floodFill( 
                             [q], \
                              colors = [opp_color], \
                              stopper = state.hasNeighbsClosure([0])  \
                         )
                state.setBoard( marked, 0 )
                num_removed += len(marked)

                #set capture counts
                if color == -1 : color = 0
                state.capture_counts[color] += len(marked)

            if state.isSuicide( action ) :
                assert num_removed == 0
                #print "ILLEGAL is suicide"
                legal = False
            
        #Proposed changes have been applied to state.  See it this makes
        #state the same as it was a turn ago
        if action != PASS :
            for ix,past_state in enumerate(state.past_states) :
                if state.sameAs2( past_state.board, \
                                 -past_state.player ) :
                    #print "ILLEGAL same as past state"
                    legal = False
                    #if side_effects :
                        #print "ILLEGAL"
                        #for ix in range(len(state.past_states)) :
                            #print "\npast_state", ix
                            #print state.past_states[ix]
                    break

        if legal :
            if side_effects :
                state.action = action
                #print "copying"
                for i in range(len(state.past_states)-1) :
                    state.past_states[i] = state.past_states[i+1]
                    #TODO del the state we are jettisoning?
                    #print "i", state.past_states[i]
                state.togglePlayer()
                state.past_states[-1] = frozen
                #return state
                return True 
            else :
                frozen.copyInto( state )
                return True
        else :
            if side_effects : 
                #check weeding out bad moves should have happened in 
                #getAllowableActions
                print "action:", action
                assert False
            else : 
                frozen.copyInto( state )
                return False 
            

    def getRewards( self, state ) :
        #find dead strings (by virtue of the 2 eye rule)
        #mark the eye-points
        #mark the dames
        #marks regions
        #mark territories
        #mark the regions that are in-seki

        #identify strings
        marked = {}
        string_id = 0
        
        #ix : string_id
        string_lookup = {}
        
        #string_id : String()
        strings = {}

        for ix in range( self.dim*self.dim ) :
            if ix in state.open_positions : continue
            if ix in marked               : continue
            
            color = state.ix2color(ix)
            members = state.floodFill( [ix], \
                                       colors=[color], \
                                       stopper=lambda x:False, \
                                       adjacency=8 )

            if len(members) > 0 :
                string = String( string_id, members, color )
                strings[string_id] = string
                for ix in members :
                    marked[ix] = True
                    string_lookup[ix] = string_id
                string_id += 1


        #TODO: loop this process
        #say we decide a string is dead, that will add some ix's to
        #open_positions and we can start again

        #for now start easy and say every string is alive
        dead_strings_removed = True
        while dead_strings_removed :

            marked = {}
            #TODO: a territory can be bordered by more than one live string
            #how will this factor in?
            #TODO update: no it wont!!?

            #set/list of ixs : string_id
            territories = {}
            terr_id = 0
            for ix in state.open_positions :
                if ix in marked :
                    continue

                color, nix = state.neighboredByOneColor( ix )
                if color :
                    territory = state.floodFill( 
                                  [ix], \
                                  colors = [0], \
                                  stopper = state.hasNeighbsClosure([-color]) \
                                )
                    for ix in territory :
                        marked[ix] = True

                    strings[string_lookup[nix]].territories.append( territory )
                    territories[terr_id] = (territory, string_lookup[nix])
                    terr_id += 1

                    #here we know ixs in group belong to color, are territories
                    
                    #now need to attribute each group to different strings

                else :
                    pass

            dead_strings_removed = False
            #have obviated the need for this by requiring simulated players
            #to make moves when possible.  This means 'dead' strings will get
            #captured automatically

            #for string_id in strings :
                #s = strings[string_id]
                #s_is_dead = len(s.territories) == 1 and \
                            #len( s.territories[0] ) == 1
                #if s_is_dead :
                    #dead_strings_removed = True
                    #state.setBoard( s.members, 0 )
                    #string is dead

        scores = [0,0]
        for stix in strings :
            st = strings[stix]
            score_ix = self.getScoreIx(st.color)
            scores[score_ix] += len(st.members)
            for t in st.territories :
                scores[score_ix] += len(t)

        #TODO: add in 5.5 points to WHITE

        if scores[0] > scores[1] :
            return [1,0]
        elif scores[1] > scores[0] :
            return [0,1]
        else :
            return [0,0]

        #TODO: decide on a reasonable scoring with Fred
        #return [int(sqrt(s)) for s in scores]

       
    #given the state, return the player to act's index in the score array
    def getPlayerIx( self, state ) :
        return self.getScoreIx( state.player )

    #if cannot find action because excluded, return action_excluded
    #if because there are no legal moves, return pass
    #
    def randomAction( self, state, to_exclude=set() ) :
        legal_moves_available = False
        #print "to_excluded", to_exclude
        for candidate in sample( state.open_positions, \
                                 len(state.open_positions) ) :

            #print "candidate", candidate
            action = state.ix2action( candidate, state.player )
            is_legal = self.applyAction( state, action, side_effects=False )
            if is_legal :
                legal_moves_available = True
                if action not in to_exclude :
                    all_legal_excluded = False
                    return action #choice( state.allowable_actions )
        
        if legal_moves_available :
            #print "all exlcud"
            return self.excluded_action
        else :
            #print "pass"
            return PASS

    def fullyExpanded( self, action ) :
        return action == self.excluded_action

    def isChanceAction( self, state ) :
        return False

    def isTerminal( self, state ) :
        return state.action == PASS and state.past_states[-1].action == PASS

def main() :
    dim = 6 

    if True : 
        s = State(dim)
        s.setBoard([0,2,4,7,9,12,14,19],WHITE)
        s.setBoard([5,10,11,15,17,18,20,21,22,24,25,26,27,28,29,31,32,34,35],BLACK)
        g = MCTS_Go(dim)
        g.applyAction( s, -4 )
        g.applyAction( s, 5 )
        #print s
        #for ps in s.past_states :
            #print ps

    #wtf moves not being taken
    if False :
        s = State(dim)
        s.setBoard([3,6,14,15],WHITE)
        s.setBoard([0,1,5,7,8,9,10,12],BLACK)
        
        g = MCTS_Go(dim)
        g.applyAction( s, -14 )
        s.togglePlayer()
        print s
        print "s.action:", s.action
        print "prev action:", g.states[-1].action
        print "terminal?: ",g.isTerminal(s)
    #komi
    if False :
        s = State(dim)
        s.setBoard( [2,5,7,10], 1 )
        s.setBoard( [1,4,9], -1 )
        print ""
        print s
        
        g = MCTS_Go(dim)
        
        g.applyAction( s, -7 )
        print ""
        print s
        for ix, state in enumerate(g.states) :
            print "    |State| ix", ix, state
        
        g.applyAction( s, 6 )
        print ""
        print s
        for ix,state in enumerate(g.states) :
            print "    |State| ix", ix, state

    #capturing
    if False :
        s = State(dim)
        s.setBoard( [0,1,2,3,4,8,12,13,14], 1 )
        s.setBoard( [5,6,7,9,10,15], -1 )
        s.togglePlayer()
        print s
        g = MCTS_Go(dim)
        g.applyAction( s, 12 )
        print s
        #print g.getAllowableActions( s )
        print g.getRewards( s )

    #allowable actions
    if False :
        s = State(dim)
        s.setBoard([1,4],1)
        s.setBoard([2,3,5,6,7,8,9,10,11,12,13], -1)
                   
        s.togglePlayer()
        print s
        g = MCTS_Go(dim)
        #print g.getAllowableActions( s )
        #is_legal = g.applyRandomAction( s )
        #prinat s

    #check for correct passing and allowableMove definition
    if False :
        s = State(dim)
        s.setBoard( [0,2,4,5,6,7,9,10,12,14,15] , 1 )
        g = MCTS_Go(dim)
        
        print s
        
        action = g.randomAction(s)
        print "trying to apply:", action
        g.applyAction( s, action )
        print s
        
        action = g.randomAction(s)
        print "trying to apply:", action
        g.applyAction( s, action )
        print s
        
        #g.applyAction( s, g.randomAction(s) )
        #print s
        #g.applyAction( s, g.randomAction(s) )
        #print s
        #g.applyAction( s, g.randomAction(s) )
        #print s
        #g.applyAction( s, g.randomAction(s) )
        #print s
        #g.applyAction( s, g.randomAction(s) )
        #print s
        #g.applyAction( s, g.randomAction(s) )
        #print s
        #g.applyAction( s, g.randomAction(s) )
        #print s
        #g.applyAction( s, g.randomAction(s) )

#



if __name__ == '__main__' :
    main()
