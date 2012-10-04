import re

re_game_id = re.compile(r'\*\*\*\*\* Hand History for Game (\d+) \*\*\*\*\*')
re_pip = re.compile(r'.*(small blind|big blind|raises|bets|calls) \[\$(\d+)(\.(\d\d))? USD\].*')

fin = open("histories/knufelbrujk_hotmail_com_PTY_NLH100_3-6plrs_x10k_1badb/pty NLH handhq_0.txt")



games = []
game = {"id" : "init", \
        "pot" : 42 }

bets = []

line_count = 0
for line in fin.readlines() :
    line = line.strip()
    #print line
    m = re_game_id.match(line)
    if m :
        #finish processing last game
        print "game: ", game['id'], "pot was: ", game['pot']
        #print "    ratios were: ", str(game['bets'])

        print "new game: " , m.group(1)
        game = {"id" : int(m.group(1)), \
                "pot" : 0 }

    else :
        m = re_pip.match(line)
        if m :
            is_blind = m.group(1) == "small blind" or m.group(1) == "big blind"
            dollars = int(m.group(2))
            if m.group(4) :
                cents = float(m.group(4)) / 100
            else : cents = 0
            bet = dollars+cents
            if not is_blind :
                bets.append( round(bet / game['pot'], 2) )

            game['pot'] += bet

    if line_count > 10000 : break

    line_count += 1

print sorted(bets)
#finish processing last game



fin.close()
