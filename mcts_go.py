from random import choice

#state is a board and a player to move (-1 or 1), and captured pieces
#board is a NxN multidim array (-1,0,1)
#maintain set of open positions coords (to sample randomly from)

BLACK = -1
WHITE = 1
EMPTY = 0
OFFBOARD = -42
PASS = 0

class State :
    def __init__(self,dim) :
        self.dim = dim
        self.board = [EMPTY]*(dim*dim)
        self.open_positions = set(range(dim*dim))
        self.capture_counts = [0,0]
        self.player = BLACK 
        self.action = 0
        self.allowable_actions = [self.ix2action(ix,self.player) \
                                  for ix \
                                  in range(dim*dim) ]

    def togglePlayer(self) :
        self.player = -self.player

    def copy(self) : 
        ns = State(self.dim)
        ns.board = list(self.board)
        ns.open_positions = set(self.open_positions)
        ns.capture_counts = list(self.capture_counts)
        ns.player = self.player
        return ns

    def copyInto( self, state ) :
        state.board = self.board
        state.open_positions = self.open_positions
        state.capture_counts = self.capture_counts
        state.player = self.player

    def sameAs( self, state2 ) :
        if type(state2) == int : return False
        assert self.dim == state2.dim

        for ix in range(self.dim*self.dim) : 
            if self.board[ix] != state2.board[ix] :
                return False
        return True 

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
        non_offboard = self.matching( neighbs, [BLACK,WHITE,EMPTY] )
        useless_eye_move = all( [ self.ix2color(nix) == color \
                                  for nix \
                                  in non_offboard ] )
        return suicide_by_definition or useless_eye_move 

    def __str__(self) :
        rows = []
        rows.append( "Player: %d" % self.player )
        rows.append( "Captured (-1,1): %s" % str(self.capture_counts) )
        rows.append( "Allowable: %s" % str(self.allowable_actions) )
        for i in range(self.dim) :
            l = []
            for j in range(self.dim) :
                p = self.board[i*self.dim+j]
                if   p == -1 : l.append( "o" )
                elif p == 1  : l.append( "x" )
                elif p == 0  : l.append( "-" )
                else : assert False
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
        self.states = [State(dim)]
        self.dim = dim
        self.root_state = State(dim)

    def copyState( self, state ) :
        if type(state) == int :
            return state
        return state.copy()
 
    def setAllowableActions( self, state ) :
        #0 is pass
        possible_actions = [state.ix2action(op, state.player) \
                            for op \
                            in state.open_positions]
        allowable_actions = []
        for action in possible_actions :
            is_legal = self.applyAction( state, action, side_effects=False ) 
            if is_legal :
                allowable_actions.append( action )
        
        state.allowable_actions = allowable_actions
   
    ####################################################
    ####Public Interface
    ####################################################
    def getAllowableActions( self, state ) :
        return state.allowable_actions
    
    #side_effects to true means updating and returning the state, metadata 
    #otherwise just returns t/f based on whether the move is legal
    def applyAction( self, state, action, side_effects=True ) :
        legal = True
        newstates = []
        for i in range( 1, len(self.states) ) :
            newstates.append( self.copyState( self.states[i] ) )

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
                legal = False
            
        #Proposed changes have been applied to state.  See it this makes
        #state the same as it was a turn ago
        if action != PASS and state.sameAs( self.states[0] ) :
            legal = False

        if legal :
            if side_effects :
                state.togglePlayer()
                newstates.append( frozen )
                self.states = newstates
                self.setAllowableActions( state )
                return state
            else :
                frozen.copyInto( state )
                return True
        else :
            if side_effects : 
                #check weeding out bad moves should have happened in 
                #getAllowableActions
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

            #need to do this list conversion still?
            #op = list(state.open_positions)
            marked = {}
            #TODO: a territory can be bordered by more than one live string
            #how will this factor in?
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

        scores = [0,0,0]
        for six in strings :
            st = strings[six]
            score_ix = st.color + 1
            scores[score_ix] += len(st.members)
            for t in st.territories :
                scores[score_ix] += len(t)

        return scores[0], scores[2]

    def randomAction( self, state ) :
        if len(state.allowable_actions) == 0 : return 0
        else : return choice( state.allowable_actions )
        #is_legal = False
        #allowable = self.getAllowableActions( state )
        #while not is_legal :
            #action = choice( list(allowable) )
            #print "considering", action
            #is_legal = self.applyAction( state, action )
            #allowable.remove( action )


    def isTerminal( self, state ) :
        no_legal_placement = len( self.getAllowableActions(state) ) == 0
        #two_passes = self.states[-1].action == 0 and \
                     #state.action == 0
        return no_legal_placement #or two_passes

def main() :
    dim = 4

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
        print g.getAllowableActions( s )
        print g.getRewards( s )

    #allowable actions
    if False :
        s = State(dim)
        s.setBoard([1,4],1)
        s.setBoard([2,3,5,6,7,8,9,10,11,12,13], -1)
                   
        s.togglePlayer()
        print s
        g = MCTS_Go(dim)
        print g.getAllowableActions( s )
        #is_legal = g.applyRandomAction( s )
        #prinat s

    #check for correct passing and allowableMove definition
    if True :
        s = State(dim)
        s.setBoard( [0,2,4,5,6,7,9,10,12,14,15] , 1 )
        g = MCTS_Go(dim)
        g.setAllowableActions(s)
        
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
