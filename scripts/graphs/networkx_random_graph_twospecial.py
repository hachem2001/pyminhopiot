import networkx as nx
from matplotlib import pyplot as plt
import random

"""

Generating some network graph that befits what we need
We define density the way we want here, though.

"""

density = 2
hearing_distance = 0.0001
n = 500
width = n**0.5 * hearing_distance
height = n**0.5 * hearing_distance

pos = {i: (random.gauss(0, width/density), random.gauss(0, height/density)) for i in range(n)}
G = nx.random_geometric_graph(n, dim=2, radius=hearing_distance, pos=pos)
largest_cc = G.subgraph(max(nx.connected_components(G), key=len)).copy()

pairs_shortest = dict(nx.all_pairs_shortest_path_length(largest_cc))

longest_pair = (-1, -1, -1)
for node, dsnts in pairs_shortest.items():
    for node_2, distance in dsnts.items():
        if distance > longest_pair[2]:
            longest_pair = (node, node_2, distance)

print(pairs_shortest[longest_pair[0]])

first_good_triplet = (longest_pair[0], longest_pair[1], -1, -1)
for node, distance in pairs_shortest[longest_pair[0]].items():
    if node != longest_pair[0] and node != longest_pair[1]:
        distance_1 = longest_pair[2]
        distance_2 = pairs_shortest[first_good_triplet[0]][node]
        distance_3 = pairs_shortest[first_good_triplet[1]][node]
        value = distance_1 + distance_2 + distance_3
        if value > first_good_triplet[3]:
            first_good_triplet = (longest_pair[0], longest_pair[1], node, value)

second_good_triplet = (longest_pair[1], longest_pair[0], -1, -1)
for node, distance in pairs_shortest[longest_pair[0]].items():
    if node != longest_pair[0] and node != longest_pair[1]:
        distance_1 = longest_pair[2]
        distance_2 = pairs_shortest[second_good_triplet[0]][node]
        distance_3 = pairs_shortest[second_good_triplet[1]][node]
        value = distance_1 + distance_2 + distance_3
        if value > second_good_triplet[3]:
            second_good_triplet = (longest_pair[0], longest_pair[1], node, value)

good_pair = first_good_triplet[3] > second_good_triplet[3] and first_good_triplet or second_good_triplet

print(good_pair, pairs_shortest[second_good_triplet[0]][second_good_triplet[1]], pairs_shortest[second_good_triplet[0]][second_good_triplet[2]], pairs_shortest[second_good_triplet[1]][second_good_triplet[2]])

print(largest_cc)
nodes = nx.draw(largest_cc, pos={i: G.nodes[i]['pos'] for i in (largest_cc.nodes)})
plt.show()
