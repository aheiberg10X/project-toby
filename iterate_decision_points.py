from globles import BET_RATIOS

def isLegal( action, outstanding ) :
    if outstanding.startswith('r') :
        return action == 'f' or \
               action == 'c' or \
               action.startswith('r')
    elif outstanding == 'k' :
        return not action == 'c' 
               #not action == 'f'
    else :
        print "outstanding: ",outstanding
        return False

def isTerminal( stack, num_players, pix ) :
    #TODO: unnecessary? and only applicable to 2p?
    if stack[pix] == 'f' : return True

    if len(stack) >= num_players :
        if all([a == 'k' for a in stack[-num_players:]]) :
            return True
        elif all([a == 'c' or a == 'f' for a in stack[-num_players+1:]]) :
            return True
        else :
            return False
    else :
        return False

def isFolded( stack, pix, num_players ) :
    if 0 <= pix-num_players < len(stack) :
        return stack[pix-num_players] == 'f'
    else :
        return False

#a heavily customized DFS thru iteration
#max_rounds caps the number of actions a player can take before a conclusion 
# must be reached
#if player_ix >= 0, iterate their decision points
#if player_ix == -1, iterate all terminating betting sequences
def iterateActionStates( num_players, max_rounds, raises=BET_RATIOS, player_ix=-1 ) :
    actions = ['f','k','c']+raises
    final_actions = ['f','k','c'] # to force conclusions

    #the current action sequence taken by the players
    stack = []

    #virtual_player / num_players = the current round
    #virtual_player % num_players = the player in that round
    #the final round players must only choose from final_actions 
    num_virtual = num_players * max_rounds

    #for each player, hold an iterator of actions
    actions_iters = [42]*num_virtual

    #refill the action iters based on the betting round they belong to
    def refill( pix ) :
        #max_rounds = 2, num_players = 3 :
        #0 1 2 | 3 4 5, virtual players 4,5 must take final actions
        if pix >= num_virtual - (num_players-1) :
            actions_iters[pix] = iter(final_actions)
        else :
            actions_iters[pix] = iter(actions)

    #start up fill
    [refill(pix) for pix in range(num_virtual)]

    #(virtual) player index
    pix = 0
    last_to_act = -1

    #the action each player must make their response to (no check after raise)
    outstanding = ['k']*num_virtual

    while True :
        try :
            #if this player was the last to give an action
            if last_to_act == pix :
                stack.pop()

            if isFolded(stack,pix,num_players) :
                #if I folded last round I must fold again
                next_action = 'f'
            else :
                next_action = actions_iters[pix].next()
                while not isLegal(next_action, outstanding[pix]) :
                    next_action = actions_iters[pix].next()

            stack.append( next_action )

            last_to_act = pix

            if isTerminal( stack, num_players, pix ) :
                if player_ix == -1 :
                    yield stack
                else :
                    continue
            else :
                #if not last player, set next player's outstanding action
                #and make it so next player must act next time thru loop
                if pix < num_virtual-1 :
                    if next_action.startswith('r') or \
                       next_action == 'k' :
                        outstanding[pix+1] = next_action
                    else :
                        outstanding[pix+1] = outstanding[pix]

                    pix += 1
                    #if next player is the one we are interested in, 
                    #return the decision history up until this point
                    if player_ix >= 0 and pix % num_players == player_ix :
                        yield stack

        #if a player runs out of moves, refill his moves and jump up to 
        #iterating through prev players actions
        except StopIteration :
            if pix == 0 : break
            else :
                refill(pix)
                last_to_act = pix-1
                pix -= 1


if __name__=='__main__' :
    count = 0
    p1_action_pairs = set([])
    p2_action_pairs = set([])

    for point in iterateActionStates( 2, 2, player_ix=-1 ) :
        count += 1
        full_state = list(point)
        for i in range( 4 - len(point) ) :
            full_state.append('d')

        print full_state
        p1_action_pairs.add( "%s,%s" % (full_state[0],full_state[2]) )
        p2_action_pairs.add( "%s,%s" % (full_state[1],full_state[3]) )

    print "count", count
    print len(p1_action_pairs)
    print len(p2_action_pairs)

