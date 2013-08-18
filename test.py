from globles import bucketCentroidDistance
import iterate_decision_points as idp
import deck
import inference as inf

#ftest = open("/home/andrew/project-toby/nodes/Rembrant_SartreNL/perm1/test_4-rounds_showdown.csv")
ftest = open("/home/andrew/project-toby/nodes/all_hyper_sartre_4-round_test_showdown.csv")

lookups = inf.setupLookups()


sum_p1_dist_avg = 0
sum_p2_dist_avg = 0
sum_winner_avg = 0

sum_p1_weighted_dist_avg = 0
sum_p2_weighted_dist_avg = 0
sum_weighted_winner_avg = 0

sum_p1_dist_ml = 0
sum_p2_dist_ml = 0
sum_winner_ml = 0

sum_p1_weighted_dist_ml = 0
sum_p2_weighted_dist_ml = 0
sum_weighted_winner_ml = 0

sum_p1_correct_pocket_avg = 0
sum_p2_correct_pocket_avg = 0

sum_p1_correct_pocket_ml = 0
sum_p2_correct_pocket_ml = 0

fwrong = open("wrong_winners.txt", 'w')

p1_true_win = 0

ntotal = 0
for line_num, line in enumerate(ftest.readlines()) :
    #really bad winner prediction from 10000 on: ~.36
    #really good from 20000 on: ~.75
    #if line_num != 1329 : continue

    splt = line.strip().split(',')

    ########################################################################
    ####### Parse
    ########################################################################
    actions = [int(t) for t in [splt[2],splt[5],splt[8],splt[11]]]
    #last is 3, other two aren't
    #if actions[3] != 3 or sum([t == 3 for t in actions[1:3]]) >= 1 :

    #non three
    if sum([t == 3 for t in actions[1:]]) > 0 :

    #if actions[1:] == [3,3,3] : 
        #print "boring all checks"
        continue
    else : 
        print "\n=======================================",line_num
        ntotal += 1

    exchanged = int(splt[12])

    board = deck.listify( splt[14] )

    belief_assmnt = inf.BktAssmnt()
    for street, (kp1,kp2) in enumerate([(0,1),(3,4),(6,7),(9,10)]) :
        belief_assmnt.set( street, (int(splt[kp1]),int(splt[kp2])) )

    print "actions: ", actions
    print "board: ", board
    print "belief assignment: ", belief_assmnt
    print "exchaged: ", exchanged

    evidence = inf.setupEvidence(board,actions)

    ###################################################################
    ##########  Inference / Prediction
    ###################################################################

    street = 3
    ms = [-1,50,50,100]
    justAK_assmnt_probs = inf.justAK( street, evidence, lookups )
    (kp1_ml,kp2_ml,diff_ml) = inf.predictBucketsAndWinner( justAK_assmnt_probs, 'avg' )

    final_assmnt_probs = inf.pf_P_ki_G_evdnc(street, evidence, lookups, ms = ms, no_Z = False )

    (kp1_avg,kp2_avg,diff_avg) = inf.predictBucketsAndWinner( final_assmnt_probs, "avg" )
    (kp1,kp2) = belief_assmnt.get(street)

    ######################################################################
    ########### Exact Pocket Accuracy
    ######################################################################

    if int(round(kp1_avg)) == kp1 :
        sum_p1_correct_pocket_avg += inf.lookupPk( street, kp1 )

    if int(round(kp2_avg)) == kp2 :
        sum_p2_correct_pocket_avg += inf.lookupPk( street, kp2 )

    if int(round(kp1_ml)) == kp1 :
        sum_p1_correct_pocket_ml += inf.lookupPk( street, kp1 )

    if int(round(kp2_ml)) == kp2 : 
        sum_p2_correct_pocket_ml += inf.lookupPk( street, kp2 )

    #####################################################################
    ######  Centroid Distances (w/ and w/o exchange weighting)
    ####################################################################

    print "true buckets 1,2,diff: ", kp1, kp2, kp1-kp2
    print "AVG: "
    print "    ", kp1_avg, kp2_avg, diff_avg
    print "ML: "
    print "    ", kp1_ml, kp2_ml, diff_ml

    p1_dist = bucketCentroidDistance(street,kp1,int(round(kp1_avg)))
    p2_dist = bucketCentroidDistance(street,kp2,int(round(kp2_avg)))
    sum_p1_dist_avg += p1_dist
    sum_p2_dist_avg += p2_dist
    sum_p1_weighted_dist_avg += p1_dist * exchanged
    sum_p2_weighted_dist_avg += p2_dist * exchanged

    p1_dist = bucketCentroidDistance(street,kp1,int(round(kp1_ml)))
    p2_dist = bucketCentroidDistance(street,kp2,int(round(kp2_ml)))
    sum_p1_dist_ml += p1_dist
    sum_p2_dist_ml += p2_dist
    sum_p1_weighted_dist_ml += p1_dist * exchanged
    sum_p2_weighted_dist_ml += p2_dist * exchanged

    ####################################################################
    ##########   Difference Measurement (Winner Prediction)
    ####################################################################

    if abs(diff_avg) < .0001 : diff_avg = 0
    if abs(diff_ml) < .001 : diff_ml = 0
    if kp1 > kp2 :
        p1_true_win += 1
        if diff_avg > 0 : #kp1_avg > kp2_avg :
            sum_winner_avg += 1
            sum_weighted_winner_avg += 1*exchanged
        else :
            fwrong.write("%d\n" % line_num )

        if diff_ml > 0 :
           sum_winner_ml += 1
           sum_weighted_winner_ml += 1*exchanged

        elif diff_ml == 0 :
           sum_winner_ml += .5
           sum_weighted_winner_ml += .5*exchanged

    elif kp1 < kp2 :
        if diff_avg < 0 : #kp1_avg < kp2_avg :
            sum_winner_avg += 1
            sum_weighted_winner_avg += 1*exchanged
        else :
            fwrong.write("%d\n" % line_num )

        if diff_ml < 0 :
            sum_winner_ml += 1
            sum_weighted_winner_ml += 1*exchanged
        elif diff_ml == 0 :
            sum_winner_ml += .5
            sum_weighted_winner_ml += .5*exchanged
    else :
        ##don't count this example
        #if ntotal > 1 :
            #neutral = float(ntotal) * sum_winner_avg / float(ntotal-1) \
                      #- sum_winner_avg 
#
            #sum_winner_avg += neutral
        sum_winner_avg += .5
        sum_winner_ml += .5
        p1_true_win += .5

    ##################################################################
    ##########     Current Averages
    ##################################################################

    fntotal = float(ntotal)
    print "AVG:"
    print "    Exactly Pocket Accuracy:"
    print "        P1: ", sum_p1_correct_pocket_ml / fntotal
    print "        P2: ", sum_p2_correct_pocket_ml / fntotal
    print "    Un Weighted:"
    print "        avg_p1_dist: ", sum_p1_dist_avg / fntotal
    print "        avg_p2_dist: ", sum_p2_dist_avg / fntotal
    print "        percent correct winner: ", sum_winner_avg / fntotal
    print "    Weighted:"
    print "        avg_p1_dist: ", sum_p1_weighted_dist_avg / fntotal
    print "        avg_p2_dist: ", sum_p2_weighted_dist_avg / fntotal
    print "        Winner: ", sum_weighted_winner_avg / fntotal

    print "ML: "
    print "    Exactly Pocket Accuracy:"
    print "        P1: ", sum_p1_correct_pocket_ml / fntotal
    print "        P2: ", sum_p2_correct_pocket_ml / fntotal
    print "    Unweighted:"
    print "        avg_p1_dist: ", sum_p1_dist_ml / fntotal
    print "        avg_p2_dist: ", sum_p2_dist_ml / fntotal
    print "        percent correct winner: ", sum_winner_ml / fntotal
    print "    Weighted: "
    print "        avg_p1_dist: ", sum_p1_weighted_dist_ml / fntotal
    print "        avg_p2_dist: ", sum_p2_weighted_dist_ml / fntotal
    print "        Winner: ", sum_weighted_winner_ml / fntotal

    print "p1 true wins: ", p1_true_win / fntotal
    print "ntotal: ", ntotal
    
    #print "pausing to evaluate, hit any key..."
    #a = raw_input()

ftest.close()



fwrong.close()
