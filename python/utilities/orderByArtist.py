import json

list_artists = {} 

with open('/Users/simonbs/playlist.json') as json_file:
    data = json.load(json_file)
first200 = [data[i] for i in data if data[i]["Index"] < 200]

for p in first200:
    artist = p["Artist"].lower().strip()
    if artist not in list_artists:
        list_artists[artist] = []
    list_artists[artist].append(p)

# for a in sorted (list_artists.keys()):
#     artist = list_artists[a]
#     print("Artist: {}".format(artist[0]["Artist"]))
#     #print(artist)
#     for s in artist:
#         print("\t{}".format(s["Name"]))

for a in sorted (list_artists.keys(), reverse=True, key=lambda x: len(list_artists[x])):
    artist = list_artists[a]
    print("Artist: {} - {}".format(artist[0]["Artist"], len(artist)))
    #print(artist)
    for s in artist:
        print("\t{}".format(s["Name"]))

