base_names = ["show_4-round_perm0_train", "show_4-round_perm0_test", \
              "noshow_4-round_perm0_train", "noshow_4-round_perm0_test"]

for base_name in base_names :
    funlabeled = open( "%s.csv" % base_name )
    flabeled = open( "belief_labeled/%s.csv" % base_name )
    fmerged = open( "%s_merged.csv" % base_name, 'w')

    belief_columns = set([0,1,6,7,12,13,18,19])
    colmap = {0:0, 1:1, 6:3, 7:4, 12:6, 13:7, 18:9, 19:10}
    #[2,5,8,11,12,13,14]
    for unline, line in zip(funlabeled.readlines(), flabeled.readlines()) :
        unsplt = unline.strip().split(',')
        splt = line.strip().split(',')
        #assert len(unsplt) == len(splt)
        newsplt = []
        for i in range(len(unsplt)) :
            if i in belief_columns :
                newsplt.append( splt[colmap[i]] )
            else :
                newsplt.append( unsplt[i] )

        fmerged.write( ','.join( newsplt ) + '\n' )


    funlabeled.close()
    flabeled.close()
    fmerged.close()
