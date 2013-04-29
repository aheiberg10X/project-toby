base_names = ["show_4-round_perm0_train", "show_4-round_perm0_test", \
              "noshow_4-round_perm0_train", "noshow_4-round_perm0_test"]

for base_name in base_names :
    funlabeled = open( "%s.csv" % base_name )
    flabeled = open( "belief_labeled/%s.csv" % base_name )
    fmerged = open( "%s_merged.csv" % base_name, 'w')

    belief_columns = set([0,1,3,4,6,7,9,10])
    #[2,5,8,11,12,13,14]
    for unline, line in zip(funlabeled.readlines(), flabeled.readlines()) :
        unsplt = unline.strip().split(',')
        splt = line.strip().split(',')
        assert len(unsplt) == len(splt)
        newsplt = []
        for i in range(len(unsplt)) :
            if i in belief_columns :
                newsplt.append( splt[i] )
            else :
                newsplt.append( unsplt[i] )

        fmerged.write( ','.join( newsplt ) + '\n' )


    funlabeled.close()
    flabeled.close()
    fmerged.close()
